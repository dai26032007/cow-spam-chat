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
# LANG TEXTS
# =====================================================
LANG_TEXTS = {
  "vi": "Hôm nay bạn đã cho bò ăn chưa?\nHôm nay bạn đã cho bò ăn chưa?\nHôm nay bạn đã cho bò ăn chưa?",
  "en": "Have you fed the cows today?\nHave you fed the cows today?\nHave you fed the cows today?",
  "ko": "오늘 소에게 밥을 주셨나요?\n오늘 소에게 밥을 주셨나요?\n오늘 소에게 밥을 주셨나요?"
  # (Đã thu gọn danh sách ngôn ngữ để test cho nhanh, bạn có thể copy full danh sách cũ vào)
}

BUTTON_TEXTS = {
  "vi": "🐮 Mở Nông Trại",
  "en": "🐮 Open Farm",
  "ko": "🐮 농장 열기"
}

# =====================================================
# FIREBASE CREDENTIALS
# =====================================================
cert_dict = json.loads(FIREBASE_CREDENTIALS_JSON)
cred = credentials.Certificate(cert_dict)

try:
    firebase_admin.initialize_app(cred, {
        "databaseURL": DATABASE_URL
    })
except ValueError:
    pass 

API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

# =====================================================
# CHỈ TEST CHO 1 USER
# =====================================================
# Lấy ID của bạn từ ảnh chụp màn hình lúc nãy
TEST_CHAT_ID = "8065435277" 

print(f"Đang tải dữ liệu của ID {TEST_CHAT_ID} từ Firebase...")
user_ref = db.reference(f"users/{TEST_CHAT_ID}")
user_data = user_ref.get()

if not user_data:
    print(f"❌ Không tìm thấy ID {TEST_CHAT_ID} trong Database!")
    exit(0)

# =====================================================
# IN LOG KIỂM TRA
# =====================================================
print("\n" + "="*40)
print("🔍 KIỂM TRA LOG DỮ LIỆU:")

lang = user_data.get("language")
print(f"-> Ngôn ngữ gốc đọc từ Firebase: '{lang}'")

if not lang or lang not in LANG_TEXTS:
    print(f"-> ⚠️ Ngôn ngữ '{lang}' không có trong từ điển, tự động chuyển sang 'en'.")
    lang = "en"

text = LANG_TEXTS[lang]
btnText = BUTTON_TEXTS[lang]

print(f"-> Cụm từ sẽ được gửi: '{text.split(chr(10))[0]}...'")
print("="*40 + "\n")

# =====================================================
# GỬI TIN NHẮN
# =====================================================
payload = {
    "chat_id": int(TEST_CHAT_ID),
    "photo": "https://i.postimg.cc/HsSD3mDc/Chat-GPT-Image-15-46-51-6-thg-9-2026.png",
    "caption": text,
    "parse_mode": "HTML",
    "reply_markup": {
        "inline_keyboard": [
            [
                {
                    "text": btnText,
                    "url": "https://t.me/LuckySheepFarm_bot?start=0"
                }
            ]
        ]
    }
}

print("Đang gửi qua Telegram...")
response = requests.post(API, json=payload, timeout=30)
data = response.json()

if data.get("ok"):
    print(f"✅ THÀNH CÔNG: Đã gửi tin nhắn test bằng ngôn ngữ '{lang}' tới {TEST_CHAT_ID}.")
else:
    print(f"❌ THẤT BẠI: {data.get('description')}")
