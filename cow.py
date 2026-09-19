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
  "ar": "هل أطعمت الأبقار اليوم؟\nهل أطعمت الأبقار اليوم؟\nهل أطعمت الأبقار اليوم؟",
  "be": "Вы ўжо пакармілі кароў сёння?\nВы ўжо пакармілі кароў сёння?\nВы ўжо пакармілі кароў сёння?",
  "ca": "Ja has alimentat les vaques avui?\nJa has alimentat les vaques avui?\nJa has alimentat les vaques avui?",
  "zh-hans": "今天你喂牛了吗？\n今天你喂牛了吗？\n今天你喂牛了吗？",
  "zh-hant": "今天你餵牛了嗎？\n今天你餵牛了嗎？\n今天你餵牛了嗎？",
  "hr": "Jeste li danas nahranili krave?\nJeste li danas nahranili krave?\nJeste li danas nahranili krave?",
  "cs": "Nakrmili jste dnes krávy?\nNakrmili jste dnes krávy?\nNakrmili jste dnes krávy?",
  "nl": "Heb je de koeien vandaag al gevoerd?\nHeb je de koeien vandaag al gevoerd?\nHeb je de koeien vandaag al gevoerd?",
  "fi": "Oletko jo ruokkinut lehmät tänään?\nOletko jo ruokkinut lehmät tänään?\nOletko jo ruokkinut lehmät tänään?",
  "fr": "Avez-vous nourri les vaches aujourd'hui ?\nAvez-vous nourri les vaches aujourd'hui ?\nAvez-vous nourri les vaches aujourd'hui ?",
  "de": "Hast du die Kühe heute schon gefüttert?\nHast du die Kühe heute schon gefüttert?\nHast du die Kühe heute schon gefüttert?",
  "he": "האם האכלת את הפרות היום?\nהאם האכלת את הפרות היום?\nהאם האכלת את הפרות היום?",
  "hu": "Megetetted ma a teheneket?\nMegetetted ma a teheneket?\nMegetetted ma a teheneket?",
  "id": "Apakah Anda sudah memberi makan sapi hari ini?\nApakah Anda sudah memberi makan sapi hari ini?\nApakah Anda sudah memberi makan sapi hari ini?",
  "it": "Hai dato da mangiare alle mucche oggi?\nHai dato da mangiare alle mucche oggi?\nHai dato da mangiare alle mucche oggi?",
  "kk": "Бүгін сиырларды тамақтандырдыңыз ба?\nБүгін сиырларды тамақтандырдыңыз ба?\nБүгін сиырларды тамақтандырдыңыз ба?",
  "ko": "오늘 소에게 밥을 주셨나요?\n오늘 소에게 밥을 주셨나요?\n오늘 소에게 밥을 주셨나요?",
  "ms": "Adakah anda sudah memberi makan lembu hari ini?\nAdakah anda sudah memberi makan lembu hari ini?\nAdakah anda sudah memberi makan lembu hari ini?",
  "nb": "Har du matet kuene i dag?\nHar du matet kuene i dag?\nHar du matet kuene i dag?",
  "fa": "آیا امروز به گاوها غذا داده‌اید؟\nآیا امروز به گاوها غذا داده‌اید؟\nآیا امروز به گاوها غذا داده‌اید؟",
  "pl": "Czy nakarmiłeś dzisiaj krowy?\nCzy nakarmiłeś dzisiaj krowy?\nCzy nakarmiłeś dzisiaj krowy?",
  "pt-br": "Você já alimentou as vacas hoje?\nVocê já alimentou as vacas hoje?\nVocê já alimentou as vacas hoje?",
  "ro": "Ai hrănit vacile astăzi?\nAi hrănit vacile astăzi?\nAi hrănit vacile astăzi?",
  "ru": "Вы уже покормили коров сегодня?\nВы уже покормили коров сегодня?\nВы уже покормили коров сегодня?",
  "sr": "Да ли сте данас нахранили краве?\nДа ли сте данас нахранили краве?\nДа ли сте данас нахранили краве?",
  "sk": "Nakŕmili ste dnes kravy?\nNakŕmili ste dnes kravy?\nNakŕmili ste dnes kravy?",
  "es": "¿Ya alimentaste a las vacas hoy?\n¿Ya alimentaste a las vacas hoy?\n¿Ya alimentaste a las vacas hoy?",
  "sv": "Har du matat korna idag?\nHar du matat korna idag?\nHar du matat korna idag?",
  "tr": "Bugün inekleri besledin mi?\nBugün inekleri besledin mi?\nBugün inekleri besledin mi?",
  "uk": "Ви вже погодували корів сьогодні?\nВи вже погодували корів сьогодні?\nВи вже погодували корів сьогодні?",
  "uz": "Bugun sigirlarni boqdingizmi?\nBugun sigirlarni boqdingizmi?\nBugun sigirlarni boqdingizmi?"
}

BUTTON_TEXTS = {
  "vi": "🐮 Mở Nông Trại",
  "en": "🐮 Open Farm",
  "ar": "🐮 افتح المزرعة",
  "be": "🐮 Адкрыць ферму",
  "ca": "🐮 Obre la granja",
  "zh-hans": "🐮 开启农场",
  "zh-hant": "🐮 開啟農場",
  "hr": "🐮 Otvori farmu",
  "cs": "🐮 Otevřít farmu",
  "nl": "🐮 Boerderij openen",
  "fi": "🐮 Avaa maatila",
  "fr": "🐮 Ouvrir la ferme",
  "de": "🐮 Farm öffnen",
  "he": "🐮 פתח את החווה",
  "hu": "🐮 Farm megnyitása",
  "id": "🐮 Buka Pertanian",
  "it": "🐮 Apri fattoria",
  "kk": "🐮 Ферманы ашу",
  "ko": "🐮 농장 열기",
  "ms": "🐮 Buka Ladang",
  "nb": "🐮 Åpne gården",
  "fa": "🐮 باز کردن مزرعه",
  "pl": "🐮 Otwórz farmę",
  "pt-br": "🐮 Abrir Fazenda",
  "ro": "🐮 Deschide ferma",
  "ru": "🐮 Открыть ферму",
  "sr": "🐮 Отвори фарму",
  "sk": "🐮 Otvoriť farmu",
  "es": "🐮 Abrir granja",
  "sv": "🐮 Öppna bondgården",
  "tr": "🐮 Çiftliği Aç",
  "uk": "🐮 Відкрити ферму",
  "uz": "🐮 Fermani ochish"
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
      "photo": "https://sf-static.upanhlaylink.com/img/image_20260816300ee21410086e35b8bc8ac0ec157dc9.jpg",
      "caption": text,
      "parse_mode": "HTML",
      "reply_markup": {
          "inline_keyboard": [
            [
                {
                    "text": btnText,
                    "url": "https://t.me/HappyCowFarm_bot/play"
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
