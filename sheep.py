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
  "vi": "Luckey Sheep Farm nay đã có thể chơi trên cả điện thoại và máy tính.\nChơi ngay: @LuckySheepFarm_bot",
  "en": "Luckey Sheep Farm can now be played on both mobile and PC.\nPlay now: @LuckySheepFarm_bot",
  "ar": "يمكن الآن لعب Luckey Sheep Farm على كلٍ من الهاتف والكمبيوتر.\nالعب الآن: @LuckySheepFarm_bot",
  "be": "У Luckey Sheep Farm цяпер можна гуляць як на тэлефоне, так і на камп'ютары.\nГуляць цяпер: @LuckySheepFarm_bot",
  "ca": "Luckey Sheep Farm ara es pot jugar tant al mòbil com a l'ordinador.\nJuga ara: @LuckySheepFarm_bot",
  "zh-hans": "Luckey Sheep Farm 现已支持手机和电脑双端畅玩。\n立即游玩：@LuckySheepFarm_bot",
  "zh-hant": "Luckey Sheep Farm 現已支援手機與電腦雙平台遊玩。\n立即遊玩：@LuckySheepFarm_bot",
  "hr": "Luckey Sheep Farm sada se može igrati i na mobitelu i na računalu.\nIgraj odmah: @LuckySheepFarm_bot",
  "cs": "Luckey Sheep Farm lze nyní hrát na mobilu i na počítači.\nHrát hned: @LuckySheepFarm_bot",
  "nl": "Luckey Sheep Farm kan nu worden gespeeld op zowel mobiel als computer.\nSpeel nu: @LuckySheepFarm_bot",
  "fi": "Luckey Sheep Farmia voi nyt pelata sekä puhelimella että tietokoneella.\nPelaa nyt: @LuckySheepFarm_bot",
  "fr": "Luckey Sheep Farm est désormais jouable sur mobile et sur ordinateur.\nJouer maintenant : @LuckySheepFarm_bot",
  "de": "Luckey Sheep Farm kann jetzt sowohl auf dem Handy als auch auf dem PC gespielt werden.\nJetzt spielen: @LuckySheepFarm_bot",
  "he": "כעת ניתן לשחק ב-Luckey Sheep Farm גם בטלפון הנייד וגם במחשב.\nשחק עכשיו: @LuckySheepFarm_bot",
  "hu": "A Luckey Sheep Farm mostantól telefonon és számítógépen is játszható.\nJátssz most: @LuckySheepFarm_bot",
  "id": "Luckey Sheep Farm kini sudah bisa dimainkan di ponsel maupun komputer.\nMain sekarang: @LuckySheepFarm_bot",
  "it": "Luckey Sheep Farm è ora disponibile sia su smartphone che su computer.\nGioca ora: @LuckySheepFarm_bot",
  "kk": "Luckey Sheep Farm ойынын енді телефонда да, компьютерде де ойнауға болады.\nҚазір ойнау: @LuckySheepFarm_bot",
  "ko": "이제 모바일과 PC 모두에서 Luckey Sheep Farm을 즐기실 수 있습니다.\n지금 플레이: @LuckySheepFarm_bot",
  "ms": "Luckey Sheep Farm kini boleh dimainkan pada telefon pintar dan komputer.\nMain sekarang: @LuckySheepFarm_bot",
  "nb": "Luckey Sheep Farm kan nå spilles på både mobil og PC.\nSpill nå: @LuckySheepFarm_bot",
  "fa": "اکنون می‌توانید Luckey Sheep Farm را هم روی تلفن همراه و هم روی رایانه بازی کنید.\nهمین حالا بازی کنید: @LuckySheepFarm_bot",
  "pl": "W Luckey Sheep Farm można teraz grać zarówno na telefonie, jak i na komputerze.\nZagraj teraz: @LuckySheepFarm_bot",
  "pt-br": "Luckey Sheep Farm agora pode ser jogado tanto no celular quanto no computador.\nJogue agora: @LuckySheepFarm_bot",
  "ro": "Luckey Sheep Farm poate fi jucat acum atât pe telefon, cât și pe computer.\nJoacă acum: @LuckySheepFarm_bot",
  "ru": "В Luckey Sheep Farm теперь можно играть как на телефоне, так и на компьютере.\nИграть сейчас: @LuckySheepFarm_bot",
  "sr": "Luckey Sheep Farm се сада може играти и на телефону и на рачунару.\nИграј одмах: @LuckySheepFarm_bot",
  "sk": "Luckey Sheep Farm sa teraz dá hrať na telefóne aj na počítači.\nHrať hneď: @LuckySheepFarm_bot",
  "es": "Luckey Sheep Farm ahora se puede jugar tanto en el móvil como en el ordenador.\nJugar ahora: @LuckySheepFarm_bot",
  "sv": "Luckey Sheep Farm kan nu spelas på både mobil och dator.\nSpela nu: @LuckySheepFarm_bot",
  "tr": "Luckey Sheep Farm artık hem telefonda hem de bilgisayarda oynanabilir.\nŞimdi oyna: @LuckySheepFarm_bot",
  "uk": "У Luckey Sheep Farm тепер можна грати як на телефоні, так і на комп'ютері.\nГрати зараз: @LuckySheepFarm_bot",
  "uz": "Luckey Sheep Farm endi telefon va kompyuterda ham o'ynalishi mumkin.\nHozir o'ynang: @LuckySheepFarm_bot"
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
      "photo": "https://i.postimg.cc/xdqzqMLV/Chat-GPT-Image-17-05-39-6-thg-9-2026.png",
      "caption": text,
      "parse_mode": "HTML",
      "reply_markup": {
          "inline_keyboard": [
              [
                  {
                      "text": btnText,
                      "web_app": {
                          "url": "https://luckysheepfarm.vercel.app/"
                      }
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
