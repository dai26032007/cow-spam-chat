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
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_2")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON_2")
DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL_2",
    "https://db-luckysheepfarm-default-rtdb.asia-southeast1.firebasedatabase.app/"
)

if not BOT_TOKEN:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'TELEGRAM_BOT_TOKEN_2'")
if not FIREBASE_CREDENTIALS_JSON:
    raise ValueError("Lỗi: Không tìm thấy biến môi trường 'FIREBASE_CREDENTIALS_JSON_2'")

# =====================================================
# CẤU HÌNH ĐIỀU TỐC ĐA LUỒNG (TỰ ĐỘNG GIẢM KHI LIMIT)
# =====================================================
MAX_THREADS = 26       # Trần tối đa
START_THREADS = 26     # Bắt đầu ở tốc độ cao để tận dụng lúc vắng user
MIN_THREADS = 5        # Mức sàn tối thiểu khi user cực đông
STEP_DOWN = 4          # Mỗi lần dính 429 sẽ giảm đi 4 luồng
EXTRA_WAIT = 1.5       # Nghỉ dư thêm 1.5 giây so với thời gian Telegram phạt
RECOVERY_BATCHES = 15  # Chạy mượt 15 batch liên tiếp mới nhích lại +1 luồng

PHOTO_SOURCE = "https://i.ibb.co/TBW5KV6Q/Chat-GPT-Image-15-28-12-19-thg-9-2026.png"
GAME_URL = "https://t.me/LuckySheepFarm_bot/play"

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
    raise ValueError("Lỗi: FIREBASE_CREDENTIALS_JSON_2 không phải là một chuỗi JSON hợp lệ.")

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
# 1. TẢI DANH SÁCH USER BẰNG SHALLOW QUERY
# =====================================================
print("Đang tải danh sách UID từ Firebase (Chế độ Shallow siêu nhẹ)...")
users_ref = db.reference("users")
users_shallow = users_ref.get(shallow=True) or {}

chat_ids = list(users_shallow.keys())
total = len(chat_ids)
print(f"Tổng số user sẽ gửi: {total}")

if total == 0:
    print("Không có user nào để gửi!")
    exit(0)

# =====================================================
# CƠ CHẾ ĐỒNG BỘ TẠM DỪNG KHI CÓ LUỒNG CHẠM 429 & CACHE FILE_ID
# =====================================================
rate_limit_lock = threading.Lock()
pause_until = 0.0
cached_file_id = None

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
# HÀM GỬI CHO 1 USER (ĐỌC LANG + BẮN API SONG SONG)
# =====================================================
def send_to_user(index, chat_id):
    global cached_file_id
    uid_str = str(chat_id)

    try:
        chat_id_int = int(uid_str)
    except ValueError:
        return "invalid", uid_str, False, f"[{index}/{total}] ⚠️ ID không hợp lệ: {uid_str}"

    # Chỉ đọc đúng 1 trường language từ nhóm core
    try:
        lang = db.reference(f"users/{uid_str}/core/language").get() or "en"
    except Exception:
        lang = "en"

    text = LANG_TEXTS.get(lang, LANG_TEXTS["en"])
    btn_text = BUTTON_TEXTS.get(lang, BUTTON_TEXTS["en"])
    hit_429 = False

    while True:
        wait_if_paused()

        payload = {
            "chat_id": chat_id_int,
            "photo": cached_file_id or PHOTO_SOURCE,
            "caption": text,
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [[{"text": btn_text, "url": GAME_URL}]]
            }
        }

        try:
            response = session.post(API, json=payload, timeout=30)
            data = response.json()

            if data.get("ok"):
                if not cached_file_id:
                    photos = data.get("result", {}).get("photo")
                    if photos:
                        cached_file_id = photos[-1].get("file_id")
                return "success", uid_str, hit_429, f"[{index}/{total}] ✅ {uid_str} ({lang})"

            error_code = data.get("error_code")
            description = data.get("description", "")

            if error_code == 429:
                hit_429 = True
                retry = data.get("parameters", {}).get("retry_after", 5)
                print(f"[{index}/{total}] ⏳ Rate limit {retry}s -> Dừng toàn bộ luồng {retry + EXTRA_WAIT}s...")
                trigger_global_pause(retry)
                continue

            if error_code == 403:
                return "blocked", uid_str, hit_429, f"[{index}/{total}] 🚫 Blocked {uid_str}"

            # User đã xóa tài khoản -> đánh dấu 'deleted' để dọn khỏi RTDB
            if error_code == 400 and "chat not found" in description.lower():
                return "deleted", uid_str, hit_429, f"[{index}/{total}] 🗑️ Chat not found (Đã xóa khỏi DB) {uid_str}"

            return "failed", uid_str, hit_429, f"[{index}/{total}] ❌ {uid_str} : {description}"

        except Exception as e:
            return "failed", uid_str, hit_429, f"[{index}/{total}] ERROR {uid_str}: {e}"

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

print(f"🚀 Bắt đầu bắn với tốc độ khởi điểm: {current_threads} luồng/giây")

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    while idx < total:
        wait_if_paused()

        batch_t0 = time.time()
        batch_ids = chat_ids[idx : idx + current_threads]
        batch_hit_429 = False
        dead_uids_in_batch = {}

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
                dead_uids_in_batch[uid_str] = None
            elif status == "failed":
                failed += 1

        # Xóa hàng loạt các user 'chat not found' trong batch (nếu có)
        if dead_uids_in_batch:
            try:
                users_ref.update(dead_uids_in_batch)
            except Exception as e:
                print(f"⚠️ Lỗi khi xóa user rác khỏi DB: {e}")

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
# KẾT QUẢ
# =====================================================
elapsed = time.time() - start

print()
print("=" * 60)
print("DONE - KẾT THÚC LẦN CHẠY NÀY")
print("=" * 60)
print("Total                :", total)
print("Success              :", success)
print("Blocked              :", blocked)
print("Deleted (Not found)  :", deleted)
print("Failed               :", failed)
print(f"Time                 : {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
