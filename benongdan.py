import os
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import firebase_admin
from firebase_admin import credentials, db

# =====================================================
# LOAD ENVIRONMENT VARIABLES (GITHUB SECRETS)
# =====================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_4")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON_4")
DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL_4",
    "https://benongdan-default-rtdb.asia-southeast1.firebasedatabase.app/"
)

if not BOT_TOKEN:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'TELEGRAM_BOT_TOKEN_4'")
if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'FIREBASE_CREDENTIALS_JSON_4'")

# =====================================================
# CẤU HÌNH ĐIỀU TỐC ĐA LUỒNG (TỰ ĐỘNG GIẢM KHI LIMIT)
# =====================================================
MAX_THREADS = 26       # Trần tối đa
START_THREADS = 26     # Bắt đầu ở tốc độ cao để tận dụng lúc vắng user
MIN_THREADS = 5        # Mức sàn tối thiểu khi user cực đông
STEP_DOWN = 4          # Mỗi lần dính 429 sẽ giảm đi 4 luồng
EXTRA_WAIT = 1.5       # Nghỉ dư thêm 1.5 giây so với thời gian Telegram phạt
RECOVERY_BATCHES = 15  # Chạy mượt 15 batch liên tiếp mới nhích lại +1 luồng

# =====================================================
# NỘI DUNG TIN NHẮN & NÚT BẤM
# =====================================================
PHOTO = "AgACAgUAAxkBAAFYaNdrCXyukghkGx5f7QEchLhgihjmQAACoBRrG6m8UFRUbnE9--k9swEAAwIAA3kAAz0E"

CAPTION_TEXT = """
"""

BUTTON_TEXT = "🍎 Mở Vườn Táo"
BUTTON_URL = "https://t.me/BeNongDan_bot?start=0"

# =====================================================
# FIREBASE CREDENTIALS
# =====================================================
try:
    cert_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
except json.JSONDecodeError:
    raise ValueError("Lỗi: FIREBASE_CREDENTIALS_JSON_4 không phải là một chuỗi JSON hợp lệ.")

cred = credentials.Certificate(cert_dict)

try:
    firebase_admin.initialize_app(cred, {
        "databaseURL": DATABASE_URL
    })
except ValueError:
    pass

# =====================================================
# TELEGRAM SESSION (TÁI SỬ DỤNG KẾT NỐI HTTP)
# =====================================================
API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_THREADS, pool_maxsize=MAX_THREADS)
session.mount("https://", adapter)

# =====================================================
# 1. TẢI DANH SÁCH UID BẰNG SHALLOW QUERY
# =====================================================
print("Đang tải danh sách UID từ Firebase (Chế độ Shallow chỉ lấy key)...")
users_shallow = db.reference("users").get(shallow=True) or {}

chat_ids = list(users_shallow.keys())
chat_ids.sort()

total_all = len(chat_ids)
print(f"Tổng số user trong Database: {total_all}")

# =====================================================
# ĐỌC TIẾN ĐỘ TỪ FIREBASE (RESUME BẰNG INDEX)
# =====================================================
progress_ref = db.reference("broadcast_progress/last_chat_uid")
last_chat_uid = progress_ref.get()

if not last_chat_uid:
    print("Chưa có mốc tiến độ trên DB, bắt đầu chạy từ đầu danh sách!")
    chat_ids_to_run = chat_ids
else:
    last_chat_uid = str(last_chat_uid)
    print(f"Tìm thấy tiến độ cũ trên Database. Mốc ID cuối là: {last_chat_uid}")

    if last_chat_uid in chat_ids:
        last_index = chat_ids.index(last_chat_uid)
        chat_ids_to_run = chat_ids[last_index + 1:]
        print(f"Đã tìm thấy ID {last_chat_uid} ở vị trí {last_index + 1}/{total_all}.")
    else:
        print(f"Không tìm thấy ID {last_chat_uid} trong danh sách, chạy lại từ đầu!")
        chat_ids_to_run = chat_ids

total = len(chat_ids_to_run)
print(f"Số lượng user sẽ được gửi trong lần chạy này: {total}")

if total == 0:
    print("Đã gửi xong toàn bộ danh sách. Không còn ai để gửi!")
    progress_ref.delete()
    exit(0)

# =====================================================
# CƠ CHẾ ĐỒNG BỘ TẠM DỪNG KHI CÓ LUỒNG CHẠM 429
# =====================================================
rate_limit_lock = threading.Lock()
pause_until = 0.0

def wait_if_paused():
    while True:
        now = time.time()
        if now >= pause_until:
            break
        time.sleep(pause_until - now)

def trigger_global_pause(retry_after):
    global pause_until
    with rate_limit_lock:
        wait_time = retry_after + EXTRA_WAIT
        target_time = time.time() + wait_time
        if target_time > pause_until:
            pause_until = target_time

# =====================================================
# HÀM GỬI CHO 1 USER
# =====================================================
def send_to_user(index, chat_id):
    try:
        chat_id_int = int(chat_id)
    except ValueError:
        return "invalid", str(chat_id), False, f"[{index}/{total}] ⚠️ ID không hợp lệ: {chat_id}"

    payload = {
        "chat_id": chat_id_int,
        "photo": PHOTO,
        "caption": CAPTION_TEXT,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[{"text": BUTTON_TEXT, "url": BUTTON_URL}]]
        }
    }

    hit_429 = False

    while True:
        wait_if_paused()

        try:
            response = session.post(API, json=payload, timeout=30)
            data = response.json()

            if data.get("ok"):
                return "success", str(chat_id), hit_429, f"[{index}/{total}] ✅ {chat_id}"

            error_code = data.get("error_code")
            description = data.get("description", "")

            if error_code == 429:
                hit_429 = True
                retry = data.get("parameters", {}).get("retry_after", 5)
                print(f"[{index}/{total}] ⏳ Rate limit {retry}s -> Dừng toàn bộ luồng {retry + EXTRA_WAIT}s...")
                trigger_global_pause(retry)
                continue

            if error_code == 403:
                return "blocked", str(chat_id), hit_429, f"[{index}/{total}] 🚫 Blocked {chat_id}"

            # User đã xóa tài khoản -> đánh dấu 'deleted' để dọn khỏi RTDB
            if error_code == 400 and "chat not found" in description.lower():
                return "deleted", str(chat_id), hit_429, f"[{index}/{total}] 🗑️ Chat not found (Đã xóa khỏi DB) {chat_id}"

            return "failed", str(chat_id), hit_429, f"[{index}/{total}] ❌ {chat_id} : {description}"

        except Exception as e:
            return "failed", str(chat_id), hit_429, f"[{index}/{total}] ERROR {chat_id}: {e}"

# =====================================================
# VÒNG LẶP CHẠY BATCH TỰ ĐIỀU CHỈNH SỐ LUỒNG
# =====================================================
success = 0
blocked = 0
deleted = 0
failed = 0
start = time.time()

current_threads = START_THREADS
clean_batches_streak = 0
idx = 0
root_ref = db.reference()

print(f"🚀 Bắt đầu bắn với tốc độ khởi điểm: {current_threads} luồng/giây")

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    while idx < total:
        wait_if_paused()

        batch_t0 = time.time()
        batch_ids = chat_ids_to_run[idx : idx + current_threads]
        batch_hit_429 = False
        dead_uids_in_batch = []

        futures = [
            executor.submit(send_to_user, idx + i + 1, cid)
            for i, cid in enumerate(batch_ids)
        ]

        for future in as_completed(futures):
            status, uid_str, hit_429, log_msg = future.result()
            print(log_msg)
            if hit_429:
                batch_hit_429 = True
            if status == "success":
                success += 1
            elif status == "blocked":
                blocked += 1
            elif status == "deleted":
                deleted += 1
                dead_uids_in_batch.append(uid_str)
            elif status == "failed":
                failed += 1

        # Gộp cập nhật tiến độ + xóa các user 'chat not found' trong 1 lần gọi Firebase
        last_batch_cid = str(batch_ids[-1])
        firebase_updates = {
            "broadcast_progress/last_chat_uid": last_batch_cid
        }
        for dead_uid in dead_uids_in_batch:
            firebase_updates[f"users/{dead_uid}"] = None

        try:
            root_ref.update(firebase_updates)
        except Exception as e:
            print(f"⚠️ Lỗi khi cập nhật tiến độ / xóa user tại {last_batch_cid}: {e}")

        idx += len(batch_ids)

        # ĐIỀU CHỈNH SỐ LUỒNG DỰA TRÊN TÌNH TRẠNG LIMIT
        if batch_hit_429:
            clean_batches_streak = 0
            old_threads = current_threads
            current_threads = max(MIN_THREADS, current_threads - STEP_DOWN)
            if current_threads < old_threads:
                print(f"📉 Dính limit! Giảm tốc độ từ {old_threads} -> {current_threads} luồng/giây")
            else:
                print(f"📉 Dính limit! Đang giữ mức sàn tối thiểu {current_threads} luồng/giây")
        else:
            clean_batches_streak += 1
            if clean_batches_streak >= RECOVERY_BATCHES and current_threads < MAX_THREADS:
                current_threads += 1
                clean_batches_streak = 0
                print(f"📈 Hệ thống thông thoáng, nhích nhẹ tốc độ lên {current_threads} luồng/giây")

        batch_elapsed = time.time() - batch_t0
        if batch_elapsed < 1.0:
            time.sleep(1.0 - batch_elapsed)

# =====================================================
# KẾT QUẢ VÀ XÓA MỐC KHI HOÀN THÀNH
# =====================================================
try:
    progress_ref.delete()
    print("✨ Đã gửi hết danh sách. Xóa mốc tiến độ trên Firebase thành công!")
except Exception as e:
    print(f"⚠️ Lỗi khi xóa mốc tiến độ: {e}")

elapsed = time.time() - start

print()
print("=" * 60)
print("DONE - KẾT THÚC LẦN CHẠY NÀY")
print("=" * 60)
print("Total (lần chạy này) :", total)
print("Success              :", success)
print("Blocked              :", blocked)
print("Deleted (Not found)  :", deleted)
print("Failed               :", failed)
print(f"Time                 : {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
