import os
import json
import firebase_admin
from firebase_admin import credentials, db
import requests
import time

# =====================================================
# LOAD ENVIRONMENT VARIABLES (GITHUB SECRETS)
# =====================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON")
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "https://happycowfarm-default-rtdb.asia-southeast1.firebasedatabase.app/")

if not BOT_TOKEN:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'TELEGRAM_BOT_TOKEN'")
if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'FIREBASE_CREDENTIALS_JSON'")

# =====================================================
# FIREBASE CREDENTIALS
# =====================================================
try:
    cert_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
except json.JSONDecodeError:
    raise ValueError("Lỗi: FIREBASE_CREDENTIALS_JSON không phải là một chuỗi JSON hợp lệ.")

cred = credentials.Certificate(cert_dict)

try:
    firebase_admin.initialize_app(cred, {
        "databaseURL": DATABASE_URL
    })
except ValueError:
    pass # Bỏ qua nếu app đã được initialize trước đó

# =====================================================
# TELEGRAM
# =====================================================
API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

# =====================================================
# LẤY DANH SÁCH USER (Giữ nguyên thứ tự của Firebase)
# =====================================================
print("Đang tải danh sách người dùng từ Firebase...")
users = db.reference("users").get() or {}

chat_ids = list(users.keys())
total_all = len(chat_ids)
print(f"Tổng số user trong Database: {total_all}")

# =====================================================
# ĐỌC TIẾN ĐỘ TỪ FIREBASE (RESUME BẰNG INDEX)
# =====================================================
progress_ref = db.reference("broadcast_progress/last_chat_uid")
last_chat_uid = progress_ref.get()

if not last_chat_uid:
    print("Chưa có mốc tiến độ trên db, bắt đầu chạy từ đầu danh sách!")
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
print(f"Số lượng user sẽ được xử lý trong lần chạy này: {total}")

if total == 0:
    print("Đã gửi xong toàn bộ danh sách. Không còn ai để gửi!")
    progress_ref.delete()
    exit(0)

# =====================================================
# THỐNG KÊ
# =====================================================
success = 0
blocked = 0
failed = 0
skipped = 0
start = time.time()

# =====================================================
# GỬI
# =====================================================
for index, chat_id in enumerate(chat_ids_to_run, 1):
    try:
        chat_id_int = int(chat_id)
    except ValueError:
        continue
        
    user_data = users.get(chat_id, {})
    lang = user_data.get("language", "en")
    
    # CHỈ GỬI CHO USER TIẾNG VIỆT
    if lang != "vi":
        skipped += 1
        # Vẫn cần lưu tiến độ dù bỏ qua
        try:
            progress_ref.set(str(chat_id))
        except Exception:
            pass
        continue

    payload = {
      "chat_id": chat_id_int,
      "photo": "https://app9006949357.tgcloud.ai/ref.png",
      "reply_markup": {
          "inline_keyboard": [
            [
                {
                    "text": "🌟 THAM GIA NGAY 🌟",
                    "url": "https://t.me/BeThoMo_bot?start=0"
                }
            ]
         ]
      }
    }
    
    while True:
        try:
            response = requests.post(
                API,
                json=payload,
                timeout=30
            )

            data = response.json()

            if data.get("ok"):
                success += 1
                print(f"[{index}/{total}] ✅ {chat_id}")
                break

            error_code = data.get("error_code")
            description = data.get("description", "")

            if error_code == 429:
                retry = data.get("parameters", {}).get("retry_after", 5)
                print(f"[{index}/{total}] ⏳ Rate limit, chờ {retry}s...")
                time.sleep(retry)
                continue

            if error_code == 403:
                blocked += 1
                print(f"[{index}/{total}] 🚫 Blocked {chat_id}")
                break

            failed += 1
            print(f"[{index}/{total}] ❌ {chat_id} : {description}")
            break

        except Exception as e:
            failed += 1
            print(f"[{index}/{total}] ERROR {chat_id}: {e}")
            break

    # Ghi tiến độ
    try:
        progress_ref.set(str(chat_id))
    except Exception as e:
        print(f"Không thể lưu tiến độ cho ID {chat_id}: {e}")

    time.sleep(0.1)

# =====================================================
# KẾT QUẢ VÀ XÓA MỐC KHI HOÀN THÀNH
# =====================================================
try:
    progress_ref.delete()
    print("✨ Đã xử lý hết danh sách. Xóa mốc tiến độ trên Firebase thành công!")
except Exception as e:
    print(f"⚠️ Lỗi khi xóa mốc tiến độ: {e}")

elapsed = time.time() - start

print()
print("=" * 60)
print("DONE - KẾT THÚC LẦN CHẠY NÀY")
print("=" * 60)
print("Total processed      :", total)
print("Success (Sent vi)    :", success)
print("Skipped (Not vi)     :", skipped)
print("Blocked              :", blocked)
print("Failed               :", failed)
print(f"Time                 : {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
