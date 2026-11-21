import os
import json
import firebase_admin
from firebase_admin import credentials, db
import requests
import time

# =====================================================
# LOAD ENVIRONMENT VARIABLES (GITHUB SECRETS)
# =====================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_3")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON_3")
DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL_3",
    "https://be-tho-mo-default-rtdb.asia-southeast1.firebasedatabase.app/"
)

if not BOT_TOKEN:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'TELEGRAM_BOT_TOKEN_3'")
if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'FIREBASE_CREDENTIALS_JSON_3'")

# =====================================================
# NỘI DUNG TIN NHẮN & NÚT BẤM (1 NGÔN NGỮ DUY NHẤT)
# =====================================================
PHOTO_URL = "https://i.ibb.co/ycBRBf65/N-ng-C-p-Anti-Cheat-Trong-Hang-Pha-L.png"

CAPTION_TEXT = """🚨 <b>KÍCH HOẠT LÁ CHẮN ANTI-CHEAT AI 24/7</b> 🚨

Hệ thống <b>Bé Thợ Mỏ</b> chính thức vận hành <b>AI phân tích hành vi chuyên sâu</b>, tự động quét Real-time và <b>BAN TỨC THÌ</b> không cần báo cáo thủ công đối với: <b>Tool – Giả lập – Auto Click – Clone nhiều tài khoản</b>.

⚡ <b>Cơ chế xử phạt lũy tiến:</b>
Mọi vi phạm đều được AI ghi nhận vào hồ sơ thiết bị và nâng cấp hình phạt theo số lần tái phạm:
👉 <b>1 ngày ➔ 3 ngày ➔ 7 ngày ➔ 30 ngày ➔ 3 năm ➔ 10 năm.</b>

🛡️ <b>Cơ chế hoàn lương:</b> Tài khoản từng vi phạm nếu hoạt động trong sạch, không tái phạm trong thời gian dài sẽ được AI tự động <b>giảm dần và reset mốc phạt</b>.

⚠️ <b>Đừng thử thách AI.</b> Chơi Fair Play để bảo vệ tài khoản của bạn!"""

BUTTON_TEXT = "⛏️ Vào Đào Vàng Ngay"
BUTTON_URL = "https://t.me/BeThoMo_bot/play"

# =====================================================
# FIREBASE CREDENTIALS
# =====================================================
try:
    cert_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
except json.JSONDecodeError:
    raise ValueError("Lỗi: FIREBASE_CREDENTIALS_JSON_3 không phải là một chuỗi JSON hợp lệ.")

cred = credentials.Certificate(cert_dict)

try:
    firebase_admin.initialize_app(cred, {
        "databaseURL": DATABASE_URL
    })
except ValueError:
    pass  # Bỏ qua nếu app đã được initialize trước đó

# =====================================================
# TELEGRAM API
# =====================================================
API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

# =====================================================
# 1. TẢI DANH SÁCH UID BẰNG SHALLOW QUERY (CHỈ LẤY KEY)
# =====================================================
print("Đang tải danh sách UID từ Firebase (Chế độ Shallow chỉ lấy key)...")
users_shallow = db.reference("users").get(shallow=True) or {}

chat_ids = list(users_shallow.keys())
# Sort() để tính năng resume ghi mốc ID hoạt động chính xác
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
# THỐNG KÊ
# =====================================================
success = 0
blocked = 0
failed = 0
start = time.time()

# =====================================================
# VÒNG LẶP GỬI TIN NHẮN (KHÔNG ĐỌC THÊM DB)
# =====================================================
for index, chat_id in enumerate(chat_ids_to_run, 1):
    try:
        chat_id_int = int(chat_id)
    except ValueError:
        continue

    payload = {
        "chat_id": chat_id_int,
        "photo": PHOTO_URL,
        "caption": CAPTION_TEXT,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": BUTTON_TEXT,
                        "url": BUTTON_URL
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

    # GHI MÙ TIẾN ĐỘ (BLIND WRITE)
    try:
        progress_ref.set(str(chat_id))
    except Exception as e:
        print(f"Không thể lưu tiến độ cho ID {chat_id}: {e}")

    # Nghỉ 0.1s tránh vượt quá limit 30 tin nhắn/giây của Telegram
    time.sleep(0.1)

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
print("Failed               :", failed)
print(f"Time                 : {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
