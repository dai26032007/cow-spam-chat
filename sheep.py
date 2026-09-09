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
  "vi": "Có thể bạn đã biết: Click vào quảng cáo sẽ giúp bạn nhận được nhiều len hơn!",
  "en": "Did you know: Clicking on ads helps you get more wool!",
  "ar": "قد تكون على علم بالفعل: النقر على الإعلانات يساعدك في الحصول على المزيد من الصوف!",
  "be": "Магчыма, вы ўжо ведаеце: клік па рэкламе дапаможа вам атрымаць больш воўны!",
  "ca": "Potser ja ho saps: fer clic als anuncis t'ajudarà a aconseguir més llana!",
  "zh-hans": "您可能已经知道：点击广告可以帮您获得更多羊毛！",
  "zh-hant": "您可能已經知道：點擊廣告可以幫您獲得更多羊毛！",
  "hr": "Možda već znate: Klik na oglase pomoći će vam da dobijete više vune!",
  "cs": "Možná už víte: Kliknutí na reklamu vám pomůže získat více vlny!",
  "nl": "Wist je dat al: op advertenties klikken helpt je om meer wol te krijgen!",
  "fi": "Ehkä tiesitkin jo: mainosten klikkaaminen auttaa saamaan enemmän villaa!",
  "fr": "Le saviez-vous : cliquer sur les publicités vous aide à obtenir plus de laine !",
  "de": "Wusstest du schon: Durch das Klicken auf Anzeigen erhältst du mehr Wolle!",
  "he": "אולי כבר ידעת: לחיצה על מודעות תעזור לך לקבל יותר צמר!",
  "hu": "Lehet, hogy már tudod: a hirdetésekre kattintva több gyapjút szerezhetsz!",
  "id": "Mungkin Anda sudah tahu: Mengklik iklan akan membantu Anda mendapatkan lebih banyak wol!",
  "it": "Forse lo sai già: cliccare sugli annunci ti aiuta a ottenere più lana!",
  "kk": "Білген боларсыз: Жарнаманы басу көбірек жүн алуға көмектеседі!",
  "ko": "알고 계셨나요? 광고를 클릭하면 더 많은 양털을 얻을 수 있습니다!",
  "ms": "Mungkin anda sudah tahu: Klik pada iklan akan membantu anda memperoleh lebih banyak bulu!",
  "nb": "Kanskje visste du det allerede: Å klikke på annonser hjelper deg å få mer ull!",
  "fa": "شاید از قبل بدانید: کلیک روی تبلیغات به شما کمک می‌کند پشم بیشتری دریافت کنید!",
  "pl": "Być może już wiesz: klikanie w reklamy pomoże ci zdobyć więcej wełny!",
  "pt-br": "Você sabia? Clicar nos anúncios ajuda você a conseguir mais lã!",
  "ro": "Poate știai deja: dând clic pe reclame vei primi mai multă lână!",
  "ru": "Возможно, вы уже знаете: клик по рекламе поможет получить больше шерсти!",
  "sr": "Можда већ знате: Клик на огласе помоћи ће вам да добијете више вуне!",
  "sk": "Možno už viete: Kliknutie na reklamy vám pomôže získať viac vlny!",
  "es": "Quizás ya lo sepas: ¡hacer clic en los anuncios te ayudará a conseguir más lana!",
  "sv": "Visste du att: att klicka på annonser hjälper dig att få mer ull!",
  "tr": "Biliyor muydunuz: Reklamlara tıklamak daha fazla yün kazanmanıza yardımcı olur!",
  "uk": "Можливо, ви вже знаєте: клік по рекламі допоможе вам отримати більше вовни!",
  "uz": "Balki bilsangiz kerak: Reklamalarni bosish ko'proq jun olishingizga yordam beradi!"
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
      "photo": "https://i.ibb.co/RG8RXW1N/Chat-GPT-Image-20-03-20-9-thg-9-2026.png",
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
