import os
import json
import firebase_admin
from firebase_admin import credentials, db
import requests
import time

# =====================================================
# LOAD ENVIRONMENT VARIABLES (GITHUB SECRETS)
# =====================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_2")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON_2")
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL_2", "https://lucky-sheep-farm-default-rtdb.asia-southeast1.firebasedatabase.app/")

if not BOT_TOKEN:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'TELEGRAM_BOT_TOKEN_2'")
if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'FIREBASE_CREDENTIALS_JSON_2'")

# =====================================================
# LANG TEXTS
# =====================================================
LANG_TEXTS = {
  "vi": "Hôm nay bạn đã tỉa lông cho cừu chưa?\nHôm nay bạn đã tỉa lông cho cừu chưa?\nHôm nay bạn đã tỉa lông cho cừu chưa?",
  "en": "Have you sheared the sheep today?\nHave you sheared the sheep today?\nHave you sheared the sheep today?",
  "ar": "هل جززت صوف الخراف اليوم؟\nهل جززت صوف الخراف اليوم؟\nهل جززت صوف الخراف اليوم؟",
  "be": "Вы ўжо пастрыглі авечак сёння?\nВы ўжо пастрыглі авечак сёння?\nВы ўжо пастрыглі авечак сёння?",
  "ca": "Ja has esquilat les ovelles avui?\nJa has esquilat les ovelles avui?\nJa has esquilat les ovelles avui?",
  "zh-hans": "今天你给羊剪毛了吗？\n今天你给羊剪毛了吗？\n今天你给羊剪毛了吗？",
  "zh-hant": "今天你給羊剪毛了嗎？\n今天你給羊剪毛了嗎？\n今天你給羊剪毛了嗎？",
  "hr": "Jeste li danas ošišali ovce?\nJeste li danas ošišali ovce?\nJeste li danas ošišali ovce?",
  "cs": "Ostříhali jste dnes ovce?\nOstříhali jste dnes ovce?\nOstříhali jste dnes ovce?",
  "nl": "Heb je de schapen vandaag al geschoren?\nHeb je de schapen vandaag al geschoren?\nHeb je de schapen vandaag al geschoren?",
  "fi": "Oletko jo kerinnyt lampaat tänään?\nOletko jo kerinnyt lampaat tänään?\nOletko jo kerinnyt lampaat tänään?",
  "fr": "Avez-vous tondu les moutons aujourd'hui ?\nAvez-vous tondu les moutons aujourd'hui ?\nAvez-vous tondu les moutons aujourd'hui ?",
  "de": "Hast du die Schafe heute schon geschoren?\nHast du die Schafe heute schon geschoren?\nHast du die Schafe heute schon geschoren?",
  "he": "האם גזזת את הכבשים היום?\nהאם גזזת את הכבשים היום?\nהאם גזזת את הכבשים היום?",
  "hu": "Megnyírtad ma a birkákat?\nMegnyírtad ma a birkákat?\nMegnyírtad ma a birkákat?",
  "id": "Apakah Anda sudah mencukur bulu domba hari ini?\nApakah Anda sudah mencukur bulu domba hari ini?\nApakah Anda sudah mencukur bulu domba hari ini?",
  "it": "Hai tosato le pecore oggi?\nHai tosato le pecore oggi?\nHai tosato le pecore oggi?",
  "kk": "Бүгін қойлардың жүнін қырықтыңыз ба?\nБүгін қойлардың жүнін қырықтыңыз ба?\nБүгін қойлардың жүнін қырықтыңыз ба?",
  "ko": "오늘 양털을 깎으셨나요?\n오늘 양털을 깎으셨나요?\n오늘 양털을 깎으셨나요?",
  "ms": "Adakah anda sudah mencukur bulu biri-biri hari ini?\nAdakah anda sudah mencukur bulu biri-biri hari ini?\nAdakah anda sudah mencukur bulu biri-biri hari ini?",
  "nb": "Har du klippet sauene i dag?\nHar du klippet sauene i dag?\nHar du klippet sauene i dag?",
  "fa": "آیا امروز پشم گوسفندان را چیده‌اید؟\nآیا امروز پشم گوسفندان را چیده‌اید؟\nآیا امروز پشم گوسفندان را چیده‌اید؟",
  "pl": "Czy ostrzygłeś dzisiaj owce?\nCzy ostrzygłeś dzisiaj owce?\nCzy ostrzygłeś dzisiaj owce?",
  "pt-br": "Você já tosquiou as ovelhas hoje?\nVocê já tosquiou as ovelhas hoje?\nVocê já tosquiou as ovelhas hoje?",
  "ro": "Ai tuns oile astăzi?\nAi tuns oile astăzi?\nAi tuns oile astăzi?",
  "ru": "Вы уже подстригли овец сегодня?\nВы уже подстригли овец сегодня?\nВы уже подстригли овец сегодня?",
  "sr": "Да ли сте данас ошишали овце?\nДа ли сте данас ошишали овце?\nДа ли сте данас ошишали овце?",
  "sk": "Ostrihali ste dnes ovce?\nOstrihali ste dnes ovce?\nOstrihali ste dnes ovce?",
  "es": "¿Ya esquilaste a las ovejas hoy?\n¿Ya esquilaste a las ovejas hoy?\n¿Ya esquilaste a las ovejas hoy?",
  "sv": "Har du klippt fåren idag?\nHar du klippt fåren idag?\nHar du klippt fåren idag?",
  "tr": "Bugün koyunları kırktın mı?\nBugün koyunları kırktın mı?\nBugün koyunları kırktın mı?",
  "uk": "Ви вже підстригли овець сьогодні?\nВи вже підстригли овець сьогодні?\nВи вже підстригли овець сьогодні?",
  "uz": "Bugun qo'ylarni qirqdingizmi?\nBugun qo'ylarni qirqdingizmi?\nBugun qo'ylarni qirqdingizmi?"
}

BUTTON_TEXTS = {
  "vi": "🐑 Mở Nông Trại",
  "en": "🐑 Open Farm",
  "ar": "🐑 افتح المزرعة",
  "be": "🐑 Адкрыць ферму",
  "ca": "🐑 Obre la granja",
  "zh-hans": "🐑 开启农场",
  "zh-hant": "🐑 開啟農場",
  "hr": "🐑 Otvori farmu",
  "cs": "🐑 Otevřít farmu",
  "nl": "🐑 Boerderij openen",
  "fi": "🐑 Avaa maatila",
  "fr": "🐑 Ouvrir la ferme",
  "de": "🐑 Farm öffnen",
  "he": "🐑 פתח את החווה",
  "hu": "🐑 Farm megnyitása",
  "id": "🐑 Buka Pertanian",
  "it": "🐑 Apri fattoria",
  "kk": "🐑 Ферманы ашу",
  "ko": "🐑 농장 열기",
  "ms": "🐑 Buka Ladang",
  "nb": "🐑 Åpne gården",
  "fa": "🐑 باز کردن مزرعه",
  "pl": "🐑 Otwórz farmę",
  "pt-br": "🐑 Abrir Fazenda",
  "ro": "🐑 Deschide ferma",
  "ru": "🐑 Открыть ферму",
  "sr": "🐑 Отвори фарму",
  "sk": "🐑 Otvoriť farmu",
  "es": "🐑 Abrir granja",
  "sv": "🐑 Öppna bondgården",
  "tr": "🐑 Çiftliği Aç",
  "uk": "🐑 Відкрити ферму",
  "uz": "🐑 Fermani ochish"
}

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
# GỬI
# =====================================================
for index, chat_id in enumerate(chat_ids_to_run, 1):
    try:
        chat_id_int = int(chat_id)
    except ValueError:
        continue
    user_data = users.get(chat_id, {})
    lang = user_data.get("language", "en")
    
    text = LANG_TEXTS.get(lang, LANG_TEXTS["en"])
    btnText = BUTTON_TEXTS.get(lang, BUTTON_TEXTS["en"])

    payload = {
      "chat_id": chat_id_int,
      "photo": "https://i.ibb.co/TBW5KV6Q/Chat-GPT-Image-15-28-12-19-thg-9-2026.png",
      "caption": text,
      "parse_mode": "HTML",
      "reply_markup": {
          "inline_keyboard": [
              [
                  {
                      "text": btnText,
                      "url": 'https://t.me/LuckySheepFarm_bot/play'
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
