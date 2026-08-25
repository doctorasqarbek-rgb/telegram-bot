import sqlite3
import datetime
import logging
import os
import asyncio
import tempfile
from zoneinfo import ZoneInfo

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

DB_PATH = os.environ.get("DB_PATH", "subscribers.db")

from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "6411235489:AAHZSB-0cOLOLI4LjF61CUPGmU-xtG2xgP4")
ADMIN_ID = 741361382
KARTA_RAQAM = "9860 1606 0775 6576"
KARTA_EGASI = "Sevinch Ergasheva"
NARX = "100 000 so'm"
GURUH_LINK = "https://t.me/+PujFAoCdY85kMDQy"
GURUH_ID = -1004397770642
VIDEO_QOLLANMA_LINK = "https://t.me/doktor_ergashev_psixoterapevt/756"
XOLIS_QR_FAYL = "xolis_qr.jpg"

# ==========================================================
# MA'LUMOTLAR BAZASI
# ==========================================================

def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        start_date TEXT, end_date TEXT, active INTEGER DEFAULT 1, warned INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS all_users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, first_seen TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS test_history (
        user_id INTEGER, test_turi TEXT, oxirgi_sana TEXT,
        PRIMARY KEY (user_id, test_turi))""")
    conn.commit()
    try:
        c.execute("ALTER TABLE subscribers ADD COLUMN warned INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def log_all_user(user_id, username, full_name):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO all_users (user_id, username, full_name, first_seen) VALUES (?,?,?,?)",
              (user_id, username or "", full_name or "", str(datetime.date.today())))
    c.execute("UPDATE all_users SET username=?, full_name=? WHERE user_id=?",
              (username or "", full_name or "", user_id))
    conn.commit(); conn.close()


def get_all_users():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT user_id, username, full_name FROM all_users")
    rows = c.fetchall(); conn.close(); return rows


def add_subscriber(user_id, username, full_name):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.date.today()
    c.execute("SELECT end_date, active FROM subscribers WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[1] == 1:
        current_end = datetime.date.fromisoformat(row[0])
        base = current_end if current_end > today else today
    else:
        base = today
    end = base + datetime.timedelta(days=30)
    c.execute("INSERT OR REPLACE INTO subscribers (user_id,username,full_name,start_date,end_date,active,warned) VALUES (?,?,?,?,?,1,0)",
              (user_id, username or "", full_name, str(today), str(end)))
    conn.commit(); conn.close(); return end


def add_subscriber_with_date(user_id, username, full_name, end_date):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.date.today()
    c.execute("INSERT OR REPLACE INTO subscribers (user_id,username,full_name,start_date,end_date,active,warned) VALUES (?,?,?,?,?,1,0)",
              (user_id, username or "", full_name, str(today), str(end_date)))
    conn.commit(); conn.close()


def get_subscriber(user_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE user_id=?", (user_id,))
    row = c.fetchone(); conn.close(); return row


def get_all_active():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE active=1")
    rows = c.fetchall(); conn.close(); return rows


def get_expired():
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = str(datetime.date.today())
    c.execute("SELECT * FROM subscribers WHERE active=1 AND end_date<?", (today,))
    rows = c.fetchall(); conn.close(); return rows


def get_expiring_soon(days=7):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    today = datetime.date.today()
    target = str(today + datetime.timedelta(days=days))
    c.execute("SELECT * FROM subscribers WHERE active=1 AND warned=0 AND end_date<=? AND end_date>=?",
              (target, str(today)))
    rows = c.fetchall(); conn.close(); return rows


def mark_warned(user_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE subscribers SET warned=1 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()


def deactivate(user_id):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("UPDATE subscribers SET active=0 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()


def can_take_test(user_id, test_turi):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT oxirgi_sana FROM test_history WHERE user_id=? AND test_turi=?",
              (user_id, test_turi))
    row = c.fetchone(); conn.close()
    if not row:
        return True, None
    oxirgi = datetime.date.fromisoformat(row[0])
    kunlar = (datetime.date.today() - oxirgi).days
    if kunlar >= 7:
        return True, None
    return False, 7 - kunlar


def record_test(user_id, test_turi):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO test_history (user_id, test_turi, oxirgi_sana) VALUES (?,?,?)",
              (user_id, test_turi, str(datetime.date.today())))
    conn.commit(); conn.close()

# ==========================================================
# PSIXOLOGIK TESTLAR
# ==========================================================

PHQ9_QUESTIONS = [
    "Ishga, dam olishga yoki boshqa faoliyatlarga qiziqishingiz kamayib qolganmi?",
    "Kayfiyatingiz tushkun, umidsiz yoki g'amgin bo'lib qolganmi?",
    "Uxlashda qiyinchilik yoki aksincha haddan ziyod uxlash kuzatiladimi?",
    "Charchash yoki kuch-quvvat yo'qligi sezilayaptimi?",
    "Ishtahangiz kamayib yoki aksincha haddan ortiq ovqat yeyayapsizmi?",
    "O'zingizni yomon his qilyapsizmi – muvaffaqiyatsiz yoki oilangizni umidsizlantirganday?",
    "Gazetani o'qish yoki TV ko'rish kabi ishlarga diqqatingizni jamlashda qiyinchilik bo'lyaptimi?",
    "Boshqalar sezadigan darajada sekin harakat qilyapsizmi yoki aksincha juda bezovtalanyapsizmi?",
    "O'zingizga zarar yetkazish yoki o'lim haqida o'ylar kelyaptimi?",
]

GAD7_QUESTIONS = [
    "O'zingizni bezovta, asabiylashgan yoki haddan ziyod xavotirli his qilyapsizmi?",
    "Xavotirni nazorat qila olmaslik sezilayaptimi?",
    "Turli narsalar haqida haddan ziyod xavotirlanayapsizmi?",
    "Dam olish yoki tinchlanishda qiyinchilik sezayapsizmi?",
    "Shunchalik bezovtasizki, bir joyda tura olmayapsizmi?",
    "Tez jahlingiz chiqib, asabiy bo'lib qolayapsizmi?",
    "Yomon narsa sodir bo'lib qolishidan qo'rqayapsizmi?",
]

ANSWER_OPTIONS = [
    ("Umuman yo'q — 0", "0"),
    ("Bir necha kun — 1", "1"),
    ("Kunlarning yarmidan ko'pi — 2", "2"),
    ("Deyarli har kuni — 3", "3"),
]


def get_phq9_result(score):
    if score <= 4:
        return "✅ Minimal yoki yo'q", "Ruhiy holatingiz yaxshi. Davom eting!"
    elif score <= 9:
        return "🟡 Engil depressiya", "Engil belgilar bor. Jismoniy faollik, yetarli uyqu va ijtimoiy muloqot yordam beradi."
    elif score <= 14:
        return "🟠 O'rtacha depressiya", "O'rtacha belgilar aniqlanmoqda. Psixolog bilan maslahatlashish tavsiya etiladi."
    elif score <= 19:
        return "🔴 O'rtacha-og'ir depressiya", "Tezroq psixolog yoki psixiatrga murojaat qiling."
    else:
        return "🚨 Og'ir depressiya", "Darhol mutaxassisga murojaat qilish zarur!"


def get_gad7_result(score):
    if score <= 4:
        return "✅ Minimal yoki yo'q", "Xavotir darajangiz normal. Yaxshi ahvoldasiz!"
    elif score <= 9:
        return "🟡 Engil xavotir", "Engil belgilar bor. Nafas mashqlari, meditatsiya va sport yordam beradi."
    elif score <= 14:
        return "🟠 O'rtacha xavotir", "O'rtacha belgilar aniqlanmoqda. Psixolog bilan maslahatlashish foydali bo'ladi."
    else:
        return "🔴 Og'ir xavotir", "Og'ir belgilar bor. Psixolog yoki psixiatrga murojaat qiling."


def build_answer_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="ta:" + val)]
        for label, val in ANSWER_OPTIONS
    ])

# ==========================================================
# KLAVIATURALAR
# ==========================================================

main_keyboard = ReplyKeyboardMarkup([
    ["Xizmatlar"],
    ["Muammoyingiz nimada", "Bog'lanish"],
    ["Ko'p beriladigan savollar", "Qabulga yozilish"],
    ["💳 Yopiq guruhga kirish"],
    ["🧪 Psixologik testlar"],
], resize_keyboard=True)

xizmat_keyboard = ReplyKeyboardMarkup([
    ["🏥 Jonli qabul"],
    ["📚 10 kunlik onlayn kurs"],
    ["🔐 Yopiq kanal"],
    ["⬅️ Ortga"]
], resize_keyboard=True)

test_keyboard = ReplyKeyboardMarkup([
    ["😰 Xavotirni baholash (GAD-7)"],
    ["😔 Depressiyani baholash (PHQ-9)"],
    ["⬅️ Ortga"]
], resize_keyboard=True)


def muammo_keyboard():
    return ReplyKeyboardMarkup([["🟢 Qabulga yozilish"], ["⬅️ Ortga"]], resize_keyboard=True)


def muammolar_keyboard():
    return ReplyKeyboardMarkup([
        ["Xavotir", "Vahima xuruji"],
        ["Tushkunlik", "Yopishqoq xayollar"],
        ["Uyqu muammolari", "Yurak tez urib ketishi"],
        ["Nafas qisishi", "Tomoqqa tiqilish hissi"],
        ["Bosh og'rig'i", "Bosh aylanishi"],
        ["Ich kelishidagi muammolar", "Peshob qilish hissi"],
        ["Tanadagi qaltirashlar", "Ozib ketish yoki semirish"],
        ["⬅️ Ortga"]
    ], resize_keyboard=True)


tolov_keyboard = ReplyKeyboardMarkup([["✅ To'lovni tasdiqlayman"], ["⬅️ Ortga"]], resize_keyboard=True)

# ==========================================================
# MIDDLEWARE
# ==========================================================

async def log_user_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None or user.is_bot:
        return
    try:
        log_all_user(user.id, user.username, user.full_name)
    except Exception as e:
        logging.error("log_user_middleware xatosi: " + str(e))

# ==========================================================
# ASOSIY HANDLERLAR
# ==========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Assalomu alaykum.\n\n"
        "Men Doktor Ergashevning rasmiy ma'lumot beruvchi botiman.\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_keyboard)


async def xizmatlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Kerakli xizmatni tanlang:", reply_markup=xizmat_keyboard)


async def jonli_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏥 Jonli qabul\n\n"
        "👥 Bu guruhli va individual tarzda bo'ladi, ya'ni Doktor Ergashev boshida umumiy guruhli "
        "2-3 soatlik dars o'tib siz va boshqalarga kasallik rivojlanish sababi va tuzalish "
        "yo'llari usullarini o'rgatadilar.\n\n"
        "🧑‍⚕️ So'ngra bemorlar yakka alohida o'zlari dori yozdirish uchun kirganda 10-15 daqiqada "
        "o'zlarini qiziqtirgan barcha savollariga individual tarzda javob oladilar.\n\n"
        "💡 Lekin Doktorni o'zi mavzuni tushuntirish mobaynida sizning 90% foiz savollaringizga "
        "javob berib bo'ladilar — qolgan uyalgan yoki muhim savolingizni dori yozdirib olish "
        "mobaynida bemalol berishingiz mumkin.",
        reply_markup=muammo_keyboard())


async def kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 10 kunlik onlayn davolash kursi\n\n"
        "📱 Bu onlayn tarzda guruhli formatda Telegramda bo'ladi.\n\n"
        "🧠 Bunda Doktor 10 kun mobaynida ishtirokchilarga Nevrotik va Depressiv kasalliklarning "
        "kelib chiqish sabablari, mexanizmlari, xarakter ustida ishlash yo'llari va tuzalish "
        "yo'llarini o'rgatadilar — va bundan ham tashqari albatta dorilar ham tavsiya qilinadi.\n\n"
        "🔒 Kursda faqat Doktorni o'zlari ko'rinadilar, qolgan ishtirokchilar faqat ovozli tarzda "
        "Doktor bilan gaplashishlari mumkin bo'ladi. Sababi — har bir bemorning shaxsini sir "
        "saqlash hisoblanadi.\n\n"
        "🎁 Bonus sifatida darslik o'zingiz bilan qoladi, ular o'chirib yuborilmaydi.",
        reply_markup=muammo_keyboard())


async def yopiq_kanal_xizmat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 Yopiq kanal\n\n"
        "💎 Bu guruhda inson ruhiyati, ruhiy buzilish va kasalliklar haqidagi qimmatli "
        "ma'lumotlarni atigi 100 ming so'm evaziga oylik obuna bo'lish orqali o'rganib borasiz.\n\n"
        "📖 Yopiq guruhda inson ruhiyati, kasalliklar turlari, qanday chiqish yo'llari haqida "
        "qimmatli ma'lumotlar berib boriladi.\n\n"
        "🚀 Bundan tashqari yangi kitob tahlili, ovozli chatlar kabi yangi loyihalar qo'shilishi "
        "kutilmoqda — va bularning barchasi atigi *100 MING SO'M*!",
        parse_mode="Markdown",
        reply_markup=muammo_keyboard())


async def muammolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Muammoyingizni tanlang:", reply_markup=muammolar_keyboard())


async def xavotir_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😟 Xavotir\n\nXavotir — ichki bezovtalik, nimadandir yomon narsa kutish va ortiqcha o'ylash bilan kechadigan holat.\n\n"
        "✅ Belgilari:\n• Ichki siqilish\n• Tinchlana olmaslik\n• Yurak tez urishi\n• Bezovtalik\n• Xayollarning to'xtamasligi\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def vahima_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😰 Vahima xuruji\n\nVahima xuruji — to'satdan kuchli qo'rquv, yurak urishi, nafas qisishi va nazoratni yo'qotayotgandek hissiyot.\n\n"
        "✅ Belgilari:\n• Yurak tez urishi\n• Nafas qisishi\n• Qo'l-oyoqlarda titroq\n• Kuchli qo'rquv\n• O'lib qolayotgandek hissiyot\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def tushkunlik_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌫 Tushkunlik\n\nTushkunlik — kayfiyat pasayishi, hayotga qiziqish kamayishi va ichki bo'shliq hissi.\n\n"
        "✅ Belgilari:\n• Kayfiyatning pasayishi\n• Qiziqish yo'qolishi\n• Charchoq\n• Umidsizlik\n• Yolg'izlik hissi\n\n"
        "📌 Bu holatda Depressiyada kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def yopishqoq_xayollar_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔄 Yopishqoq xayollar\n\nYopishqoq xayollar — ongga qayta-qayta kelaveradigan, bezovta qiladigan fikrlar.\n\n"
        "✅ Belgilari:\n• Bir xil fikrlarning takrorlanishi\n• Bezovtalik\n• Xayollardan qutulib bo'lmaslik\n• Ichki zo'riqish\n\n"
        "📌 Ko'pincha Obsessiv Kompulsiv Nevroz kasalligida kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def uyqu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌙 Uyqu muammolari\n\nUyqu muammolari — uxlab qolish qiyinligi yoki ko'p uxlash, tez uyg'onish.\n\n"
        "✅ Belgilari:\n• Uxlash qiyin bo'lishi\n• Sal narsaga uyg'onib ketish\n• Uyqudan charchoq bilan turish\n• Kunduzi uyquchanlik\n\n"
        "📌 Bunga stress, xavotir va ruhiy zo'riqish sabab bo'lishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def yurak_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❤️ Yurak tez urib ketishi\n\nYurakning tez urib ketishi ko'pincha xavotir, vahima yoki ichki zo'riqish bilan bog'liq.\n\n"
        "✅ Belgilari:\n• Yurakning kuchli urishi\n• Ichki qo'rquv\n• Bezovtalik\n• Pulsni tez-tez o'lchash\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def nafas_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😮‍💨 Nafas qisishi\n\nNafas qisishi hissi ba'zan xavotir, vahima yoki ichki zo'riqish fonida paydo bo'ladi.\n\n"
        "✅ Belgilari:\n• To'liq nafas ololmaslik hissi\n• Ko'krakda siqilish\n• Qo'rquv\n• Tez-tez chuqur nafas olishga urinish\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def tomoqqa_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🫢 Tomoqqa tiqilish hissi\n\nTomoqqa tiqilish hissi ko'pincha xavotir va ichki zo'riqish bilan bog'liq.\n\n"
        "✅ Belgilari:\n• Yutinish qiyin bo'lgandek tuyulishi\n• Tomoqda nimadir bordek hissiyot\n• Bezovtalik kuchayishi\n\n"
        "📌 Ko'pincha Nevroz yoki Depressiyada kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def bosh_ogriq_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤕 Bosh og'rig'i\n\nBosh og'rig'i stress, xavotir va ruhiy zo'riqish bilan kuchayishi mumkin.\n\n"
        "✅ Belgilari:\n• Boshda bosim hissi\n• Peshona yoki ensa og'rig'i\n• Stress bilan og'riqning kuchayishi\n\n"
        "📌 Ruhiy holat barqarorlashsa, boshdagi og'riqlar ham kamayishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def bosh_aylanish_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💫 Bosh aylanishi\n\nBosh aylanishi ba'zan xavotir, qo'rquv va ichki zo'riqish bilan birga kuzatiladi.\n\n"
        "✅ Belgilari:\n• Bosh aylangandek bo'lishi\n• Muvozanat buzilgandek tuyulishi\n• Qo'rquv bilan kuchayishi\n\n"
        "📌 Ko'pincha Nevroz yoki Depressiyada kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def ich_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚽 Ich kelishidagi muammolar\n\nIchaklar faoliyatidagi o'zgarishlar stress va xavotir bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n• Ich qotishi yoki ich ketishi\n• Qorin dam bo'lishi\n• Ichakda noqulaylik\n\n"
        "📌 Xavotir hissi paydo bo'lganda muammo kuchayadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def peshob_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚻 Peshob qilish hissi\n\nTez-tez peshob qilish hissi ham ba'zan xavotir va ichki zo'riqish bilan kuchayadi.\n\n"
        "✅ Belgilari:\n• Tez-tez hojatga borish hissi\n• Bezovtalik bilan kuchayishi\n• Muhim paytda ko'proq sezilishi\n\n"
        "📌 Organik sabablar bo'lmasa, bu ham psixosomatik ko'rinish bo'lishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def qaltirash_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🪨 Tanadagi qaltirashlar\n\nTanadagi qaltirashlar xavotir, vahima va kuchli ichki zo'riqish paytida kuzatilishi mumkin.\n\n"
        "✅ Belgilari:\n• Qo'l-oyoqlarda titroq\n• Ichki qaltirash\n• Qo'rquv bilan kuchayishi\n\n"
        "📌 Bu holat asabiy zo'riqish bilan bog'liq, ko'pincha Nevrozda kuchayadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def vazn_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚖️ Ozib ketish yoki semirish\n\nVaznning o'zgarishi ruhiy holat, stress, xavotir yoki tushkunlik bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n• Ishtahaning kamayishi yoki oshishi\n• Tez ozish\n• Ortiqcha ovqat yeyish\n\n"
        "📌 Ruhiy holatni to'g'rilansa ishtaha ham o'z o'rniga tushadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())


async def boglanish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Bog'lanish ma'lumotlari\n\n"
        "📱 Telefon:\n+998 88 306 06 95\n\n"
        "📸 Instagram:\nhttps://www.instagram.com/doktor.ergashev?igsh=MXc5eTN2NjF1NGZqaw==\n\n"
        "🎥 YouTube:\nhttps://youtube.com/@doktor_ergashev?si=s939zn1cW_N7BLu-")


async def savollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Ko'p beriladigan savollar\n\n"
        "1️⃣ Psixoterapiya nima?\nPsixoterapiya — bu ruhiy muammolarni suhbat orqali davolash usuli.\n\n"
        "2️⃣ Bir marta kelish yetarlimi?\nAyrim insonlarda bitta konsultatsiya yetarli bo'lishi mumkin, lekin ko'pchilikda bir necha seans yoki 10 kunlik onlayn kurs samaraliroq bo'ladi.\n\n"
        "3️⃣ Dorilar majburiymi?\nYo'q, har doim ham emas. Lekin ko'p hollarda (taxminan 70–80%) holatga qarab yoziladi.\n\n"
        "4️⃣ Qancha vaqtda natija bo'ladi?\nBu sizning holatingizga bog'liq. Ba'zida tez (1 oy ichida), lekin odatda 2–3 oyda natija bo'ladi.\n\n"
        "5️⃣ Onlayn davolanish ham samaralimi?\nHa, to'g'ri olib borilsa onlayn psixoterapiya ham juda yaxshi natija beradi.\n\n"
        "6️⃣ Bu sehr yoki jin tegish kasalligi emasmi?\nYo'q! Nevroz yoki depressiya bu tibbiy-psixologik holat hisoblanadi.\n\n"
        "7️⃣ Bu kasallikdan butunlay sog'ayish mumkinmi?\nHa, ko'p hollarda (taxminan 70%) insonlar to'liq sog'ayadi.\n\n"
        "8️⃣ Bu kasallikdan o'lib qolish yoki jinni bo'lib qolish mumkinmi?\nYo'q, xavotir olmang. Bu holat hayot uchun xavfli emas.\n\n"
        "9️⃣ Bu shizofreniya emasmi?\nYo'q. Shizofreniya jiddiy psixik kasallik bo'lib, u bilan psixiatrlar shug'ullanadi.\n\n"
        "🔟 Doktor Ergashev kim?\nDoktor Ergashev — Toshkent Tibbiyot Akademiyasi Tibbiy psixologiya yo'nalishi magistr bitiruvchisi. "
        "2023-yildan beri faoliyat yuritadi va 3000 dan ortiq bemorlar bilan ishlab, nevroz va depressiv holatlarni davolab kelmoqda.")


async def qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ *DIQQAT — O'qib chiqing!*\n\n"
        "Doktor Nevroz, Depressiya, Fobiya, Uyqusizlik, Xavotir buzilishlari va "
        "Xarakterdagi muammolar bilan shug'ulladilar.\n\n"
        "Buning uchun *bemorning o'zi tuzalishni xohlashi* kerak.\n"
        "❌ Iltimos, bemorni majburlab yoki aldab olib kelmang!\n\n"
        "─────────────────\n"
        "Bundan tashqari biz quyidagi kasalliklar bilan *ishlamaymiz:*\n\n"
        "🚫 Shizofreniya\n"
        "🚫 Epilepsiya (tutqanoq)\n"
        "🚫 Parkinson\n"
        "🚫 Demensiya\n\n"
        "Agar bemorida bunday holat kuzatilayotgan bo'lsa — "
        "*Psixiatr yoki Nevropatologga* murojaat qiling.\n\n"
        "─────────────────\n"
        "Qabulga yozilishni davom ettirasizmi?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Ha, tushundim — yozilaman"], ["⬅️ Ortga"]],
            resize_keyboard=True))


async def qabul_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["holat"] = "ism"
    await update.message.reply_text(
        "📝 *Qabulga yozilish*\n\nIltimos, ism va familiyangizni yozing.",
        parse_mode="Markdown")


async def manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manzil_keyboard = ReplyKeyboardMarkup([["ALBATTA BORAMAN"], ["⬅️ Ortga"]], resize_keyboard=True)
    await update.message.reply_text(
        "⚠️ DIQQAT!\n\nQABULGA YOZILIB KELISHINGIZ SHART, CHUNKI BU ODDIY DORI YOZIB BERISH EMAS, "
        "PSIXOTERAPIYA HISOBLANADI!\n\nYOZILMASDANS KELSANGIZ, QABULGA KIRMASDAN KETISHINGIZ MUMKIN.\n\n"
        "AGAR KELISHINGIZ ANIQ BO'LMASA, ILTIMOS, SIZNING O'RNINGIZGA BOSHQA INSON KELISHI MUMKIN. "
        "SHUNING UCHUN SHUNCHAKI YOL'G'ONDAN 'KELAMAN' DEB O'ZINGIZNING, DOKTORNING VA BOSHQALARNING "
        "VAQTINI O'G'IRLAMANG!",
        reply_markup=manzil_keyboard)


async def manzilni_korsat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏥 SOSH MEDICAL klinikasi\n\n"
        "📍 Manzil: Yunusobod tumani, 13-mavze, Yangishahar ko'chasi 64a uy\n\n"
        "🗺 LOKATSIYA:\nhttps://yandex.com/navi/?whatshere%5Bzoom%5D=18&whatshere%5Bpoint%5D=69.296029%2C41.364923&lang=uz&from=navi")


# ==========================================================
# YOPIQ GURUH — KIRISH / OBUNANI UZAYTIRISH
# ==========================================================

async def guruhga_kirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Yopiq guruhga kirish tugmasi bosilganda ishlaydi.
    Foydalanuvchi hali FAOL a'zo bo'lsa — uni bloklamaydi,
    balki "Obunani uzaytirish" imkoniyatini taklif qiladi.
    """
    user = update.effective_user
    sub = get_subscriber(user.id)

    if sub and sub[5] == 1:
        await update.message.reply_text(
            "✅ Siz allaqachon faol a'zosiz!\n\n"
            "📅 Obuna tugash sanasi: " + str(sub[4]) + "\n\n"
            "Muddatingiz tugashidan oldin ham to'lov qilib, obunangizni "
            "shu sanadan boshlab uzaytirishingiz mumkin.",
            reply_markup=ReplyKeyboardMarkup(
                [["🔄 Obunani uzaytirish"], ["⬅️ Ortga"]],
                resize_keyboard=True))
        return

    await tolov_korsat(update, context)


def find_qr_path():
    """QR-kod fayli joylashgan yo'lni qidiradi. Topilmasa None qaytaradi."""
    mumkin_boigan_yollar = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), XOLIS_QR_FAYL),
        os.path.join(os.getcwd(), XOLIS_QR_FAYL),
        XOLIS_QR_FAYL,
    ]
    for yol in mumkin_boigan_yollar:
        logging.info(f"QR fayl qidirilmoqda: {yol} -> mavjud: {os.path.exists(yol)}")
        if os.path.exists(yol):
            return yol
    logging.warning(f"QR fayl topilmadi. Tekshirilgan yo'llar: {mumkin_boigan_yollar}")
    return None


async def send_qr_code(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    Berilgan chat_id ga QR-kod rasmini yuboradi.
    Yangi obuna oqimida ham, uzaytirish oqimida ham,
    muddat tugashi haqidagi ogohlantirish xabarida ham ishlatiladi.
    Qaytaruvchi qiymat: QR muvaffaqiyatli yuborilgan bo'lsa True, aks holda False.
    """
    qr_path = find_qr_path()
    if not qr_path:
        return False
    try:
        with open(qr_path, "rb") as qr_photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=qr_photo,
                caption=(
                    "📱 QR-kod orqali to'lash\n\n"
                    "Ushbu QR-kodni istalgan bank yoki to'lov ilovasi "
                    "(Payme, Click, biror bank ilovasi va h.k.) orqali skanerlang.\n\n"
                    "💡 Agar bitta telefon ishlatsangiz: rasmni saqlab, "
                    "to'lov ilovasidagi QR skaner bo'limida \"Galereyadan tanlash\" "
                    "orqali yuklashingiz mumkin.\n\n"
                    "💰 To'lanishi kerak summa: " + NARX))
        return True
    except Exception as e:
        logging.error("QR yuborishda xatolik: " + str(e))
        return False


async def tolov_korsat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    QR-kod va to'lov ko'rsatmalarini chiqaradi.
    Yangi obuna bo'lish uchun ham, mavjud obunani uzaytirish uchun ham
    shu funksiya ishlatiladi.
    """
    await update.message.reply_text(
        "🔐 Yopiq kanal\n\n"
        "💎 Bu guruhda inson ruhiyati, ruhiy buzilish va kasalliklar haqidagi qimmatli "
        "ma'lumotlarni atigi 100 ming so'm evaziga oylik obuna bo'lish orqali o'rganib borasiz.\n\n"
        "📖 Yopiq guruhda inson ruhiyati, kasalliklar turlari, qanday chiqish yo'llari haqida "
        "qimmatli ma'lumotlar berib boriladi.\n\n"
        "🚀 Bundan tashqari yangi kitob tahlili, ovozli chatlar kabi yangi loyihalar qo'shilishi "
        "kutilmoqda — va bularning barchasi atigi 100 MING SO'M!\n\n"
        "🎬 Qanday kirish kerakligi haqida videoqo'llanma:\n" + VIDEO_QOLLANMA_LINK + "\n\n"
        "💳 To'lov QR-kod orqali amalga oshiriladi:")

    qr_yuborildi = await send_qr_code(context, update.effective_chat.id)
    if not qr_yuborildi:
        await update.message.reply_text(
            "💳 Karta orqali to'lash\n\n"
            "Karta raqami: " + KARTA_RAQAM + "\n"
            "Karta egasi: " + KARTA_EGASI + "\n"
            "Summa: " + NARX)

    await update.message.reply_text(
        "❗️ To'lovni amalga oshirgach, to'lov tasdig'i (chek yoki skrinshot) rasmini "
        "shu chatga yuboring.\nAdmin 5-10 daqiqa ichida to'lovingizni tasdiqlaydi.",
        reply_markup=tolov_keyboard)
    context.user_data["holat"] = "tolov_kutish"

# ==========================================================
# PSIXOLOGIK TEST HANDLERLARI
# ==========================================================

async def psixologik_testlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("holat", None)
    await update.message.reply_text(
        "🧪 Psixologik testlar\n\n"
        "Quyidagi testlar so'nggi 2 hafta ichidagi holatingizni baholaydi.\n\n"
        "⚠️ Bu testlar tibbiy tashxis emas — faqat dastlabki baholash uchun.\n\n"
        "Qaysi testni o'tkazmoqchisiz?",
        reply_markup=test_keyboard)


async def start_gad7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mumkin, qolgan_kun = can_take_test(user_id, "gad7")
    if not mumkin:
        await update.message.reply_text(
            f"⏳ Siz bu testni allaqachon o'tkazgansiz.\n\n"
            f"GAD-7 testini qayta o'tkazish uchun *{qolgan_kun} kun* kutishingiz kerak.\n\n"
            f"Test natijalarini kuzatib borish uchun haftada bir marta o'tkazish tavsiya etiladi.",
            parse_mode="Markdown",
            reply_markup=test_keyboard)
        return
    context.user_data["test_turi"] = "gad7"
    context.user_data["test_savol"] = 0
    context.user_data["test_ballar"] = []
    context.user_data["holat"] = "test_javob"
    await _send_test_question(update.message, context)


async def start_phq9(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mumkin, qolgan_kun = can_take_test(user_id, "phq9")
    if not mumkin:
        await update.message.reply_text(
            f"⏳ Siz bu testni allaqachon o'tkazgansiz.\n\n"
            f"PHQ-9 testini qayta o'tkazish uchun *{qolgan_kun} kun* kutishingiz kerak.\n\n"
            f"Test natijalarini kuzatib borish uchun haftada bir marta o'tkazish tavsiya etiladi.",
            parse_mode="Markdown",
            reply_markup=test_keyboard)
        return
    context.user_data["test_turi"] = "phq9"
    context.user_data["test_savol"] = 0
    context.user_data["test_ballar"] = []
    context.user_data["holat"] = "test_javob"
    await _send_test_question(update.message, context)


async def _send_test_question(message, context: ContextTypes.DEFAULT_TYPE):
    test_turi = context.user_data["test_turi"]
    q_index = context.user_data["test_savol"]
    questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
    test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
    total = len(questions)
    filled = int((q_index / total) * 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)
    await message.reply_text(
        f"📋 *{test_nomi}*\n"
        f"{bar}  {q_index}/{total}\n\n"
        f"*{questions[q_index]}*\n\n"
        f"_So'nggi 2 hafta ichida:_",
        parse_mode="Markdown",
        reply_markup=build_answer_keyboard())

# ==========================================================
# MEDIA HANDLER
# ==========================================================

async def handle_payment_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Admin — reklama rasmi
    if user.id == ADMIN_ID and context.user_data.get("holat") == "reklama_kutish":
        await reklama_tayyorlash(update, context)
        return

    # Admin — .txt fayl orqali ommaviy qo'shish
    if user.id == ADMIN_ID and context.user_data.get("holat") == "bulk_add":
        doc = update.message.document
        if doc and (doc.mime_type == "text/plain" or doc.file_name.endswith(".txt")):
            await update.message.reply_text("📂 Fayl qabul qilindi, ishlanmoqda...")
            fayl = await context.bot.get_file(doc.file_id)
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                tmp_path = tmp.name
            await fayl.download_to_drive(tmp_path)
            matn = open(tmp_path, encoding="utf-8", errors="ignore").read()
            os.unlink(tmp_path)
            await bulk_add_process(update, context, matn)
        else:
            await update.message.reply_text("❗ Faqat .txt fayl yuboring.")
        return

    # Admin — boshqa fayl (e'tiborsiz)
    if user.id == ADMIN_ID:
        return

    # Oddiy foydalanuvchi — to'lov cheki
    holat = context.user_data.get("holat")
    if holat not in ("tolov_kutish", None, "tolov_yuborildi"):
        return
    uname = "@" + user.username if user.username else "yo'q"
    caption = "📥 Yangi to'lov so'rovi!\n\n👤 Ism: " + str(user.full_name) + "\n🆔 ID: " + str(user.id) + "\n📎 Username: " + uname
    inline_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="t:" + str(user.id)),
        InlineKeyboardButton("❌ Rad etish", callback_data="r:" + str(user.id))
    ]])
    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=inline_kb)
    elif update.message.document:
        await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=caption, reply_markup=inline_kb)
    context.user_data["holat"] = "tolov_yuborildi"
    await update.message.reply_text("✅ To'lov chekingiz adminga yuborildi.\n5-10 daqiqa ichida guruh linki yuboriladi. Sabr biling!", reply_markup=main_keyboard)

# ==========================================================
# CALLBACK HANDLER (to'lov + reklama + test javoblari)
# ==========================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── TEST JAVOBLARI ────────────────────────────────────
    if data.startswith("ta:"):
        if data == "ta:menu":
            await query.edit_message_text("Asosiy menyuga qaytdingiz.")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Kerakli bo'limni tanlang:",
                reply_markup=main_keyboard)
            return

        if data.startswith("ta:restart_"):
            test_turi = data.split("_")[1]
            mumkin, qolgan_kun = can_take_test(query.from_user.id, test_turi)
            if not mumkin:
                test_nomi = "GAD-7" if test_turi == "gad7" else "PHQ-9"
                await query.edit_message_text(
                    f"⏳ *{test_nomi}* testini qayta o'tkazish uchun "
                    f"*{qolgan_kun} kun* kutishingiz kerak.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="ta:menu")]
                    ]))
                return
            context.user_data["test_turi"] = test_turi
            context.user_data["test_savol"] = 0
            context.user_data["test_ballar"] = []
            context.user_data["holat"] = "test_javob"
            questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
            test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
            await query.edit_message_text(
                f"📋 *{test_nomi}*\n{'⬜' * 10}  0/{len(questions)}\n\n"
                f"*{questions[0]}*\n\n_So'nggi 2 hafta ichida:_",
                parse_mode="Markdown",
                reply_markup=build_answer_keyboard())
            return

        # Savol javobi (0-3 ball)
        ball = int(data.split(":")[1])
        context.user_data["test_ballar"].append(ball)
        context.user_data["test_savol"] += 1

        test_turi = context.user_data["test_turi"]
        q_index = context.user_data["test_savol"]
        questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
        total = len(questions)

        if q_index >= total:
            jami = sum(context.user_data["test_ballar"])
            context.user_data["holat"] = None
            record_test(query.from_user.id, test_turi)

            if test_turi == "gad7":
                test_nomi = "GAD-7 – Xavotir testi"
                max_ball = 21
                daraja, maslahat = get_gad7_result(jami)
            else:
                test_nomi = "PHQ-9 – Depressiya testi"
                max_ball = 27
                daraja, maslahat = get_phq9_result(jami)

            keyingi_sana = datetime.date.today() + datetime.timedelta(days=7)
            await query.edit_message_text(
                f"✅ *{test_nomi} yakunlandi!*\n\n"
                f"📊 Sizning ballingiz: *{jami}/{max_ball}*\n"
                f"📌 Daraja: *{daraja}*\n\n"
                f"{maslahat}\n\n"
                f"─────────────────\n"
                f"⚠️ _Bu natija tibbiy tashxis emas._\n"
                f"Qiynalayotgan bo'lsangiz, mutaxassis bilan maslahatlashing.\n\n"
                f"📞 Yordam: +998 88 306 06 95\n\n"
                f"─────────────────\n"
                f"🗓 Qaytadan tekshirmoqchi bo'lsangiz, *1 haftadan so'ng* — "
                f"*{keyingi_sana.strftime('%d.%m.%Y')} dan* boshlab tekshirishingiz mumkin.\n\n"
                f"─────────────────\n"
                f"📢 *Yopiq kanalimiz haqida:*\n"
                f"Oyiga *100 000 so'm* evaziga xavotir va tushkunlikdan "
                f"chiqish yo'llarini yopiq kanalimizdan o'rganing! 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Yopiq kanalga kirish", url=GURUH_LINK)],
                    [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="ta:menu")],
                ]))
        else:
            filled = int((q_index / total) * 10)
            bar = "🟩" * filled + "⬜" * (10 - filled)
            test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
            await query.edit_message_text(
                f"📋 *{test_nomi}*\n"
                f"{bar}  {q_index}/{total}\n\n"
                f"*{questions[q_index]}*\n\n_So'nggi 2 hafta ichida:_",
                parse_mode="Markdown",
                reply_markup=build_answer_keyboard())
        return

    # ── REKLAMA (faqat admin) ─────────────────────────────
    if query.from_user.id == ADMIN_ID:
        if data == "reklama_tasdiq":
            await query.edit_message_text("⏳ Yuborilmoqda, kuting...")
            await reklama_yuborish(context)
            return
        elif data == "reklama_bekor":
            context.user_data.pop("reklama_type", None)
            context.user_data.pop("reklama_text", None)
            context.user_data.pop("reklama_photo_id", None)
            await query.edit_message_text("❌ Reklama yuborish bekor qilindi.")
            return

    # ── TO'LOV TASDIQLASH / RAD (faqat admin) ─────────────
    if query.from_user.id != ADMIN_ID:
        return

    try:
        if data.startswith("t:"):
            user_id = int(data.split(":")[1])
            try:
                chat = await context.bot.get_chat(user_id)
                full_name = chat.full_name or "Noma'lum"
                username = chat.username
            except Exception:
                full_name = "Noma'lum"; username = None
            end_date = add_subscriber(user_id, username, full_name)
            try:
                invite = await context.bot.create_chat_invite_link(
                    chat_id=GURUH_ID, member_limit=1, name=str(full_name)[:30])
                link = invite.invite_link
            except Exception as e:
                logging.warning("Invite link error: " + str(e))
                link = GURUH_LINK
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ To'lovingiz tasdiqlandi!\n\nTabriklaymiz! 🎉\n\n"
                         "Obuna muddati: 1 oy (" + str(end_date) + " gacha)\n\n"
                         "🔗 Guruh linki (faqat siz uchun, 1 martalik):\n" + link +
                         "\n\nMuddat tugagach, qayta to'lov qiling.")
            except Exception as e:
                logging.error("Send to user error: " + str(e))
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text="⚠️ Foydalanuvchiga xabar yuborilmadi!\nUser ID: " + str(user_id) +
                         "\nSabab: " + str(e) + "\n\nGuruh linki: " + link)
            try:
                await query.edit_message_caption(
                    caption="✅ Tasdiqlandi: " + str(full_name) + "\n📅 " + str(end_date) + " gacha")
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="✅ Tasdiqlandi!\n👤 " + str(full_name) + "\n🆔 " + str(user_id) +
                     "\n📅 " + str(end_date) + " gacha\n🔗 " + link)

        elif data.startswith("r:"):
            user_id = int(data.split(":")[1])
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Kechirasiz, to'lovingiz tasdiqlanmadi.\nQayta to'lov qilib chek yuboring.")
            except Exception as e:
                logging.error("Rad send error: " + str(e))
            try:
                await query.edit_message_caption(caption="❌ Rad etildi (ID: " + str(user_id) + ")")
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=ADMIN_ID, text="❌ Rad etildi. User ID: " + str(user_id))

    except Exception as e:
        logging.error("Callback error: " + str(e))
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text="🔴 Xatolik yuz berdi:\n" + str(e))
        except Exception:
            pass

# ==========================================================
# ADMIN BUYRUQLARI
# ==========================================================

async def tasdiqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Foydalanish: /tasdiqlash <user_id>"); return
    try: user_id = int(context.args[0])
    except: await update.message.reply_text("Noto'g'ri user_id"); return
    try:
        chat = await context.bot.get_chat(user_id)
        full_name = chat.full_name; username = chat.username
    except:
        full_name = "Noma'lum"; username = None
    end_date = add_subscriber(user_id, username, full_name)
    try:
        invite = await context.bot.create_chat_invite_link(chat_id=GURUH_ID, member_limit=1, name=str(full_name)[:30])
        link = invite.invite_link
    except:
        link = GURUH_LINK
    try:
        await context.bot.send_message(chat_id=user_id, text=
            "✅ To'lovingiz tasdiqlandi!\n\nTabriklaymiz! 🎉\n\nObuna muddati: 1 oy (" + str(end_date) + " gacha)\n\n"
            "🔗 Guruh linki (faqat siz uchun, 1 martalik):\n" + link + "\n\nMuddat tugagach, qayta to'lov qiling.")
        await update.message.reply_text("✅ " + str(full_name) + " tasdiqlandi. Guruh linki yuborildi.")
    except Exception as e:
        await update.message.reply_text("Xatolik: " + str(e))


async def rad_etish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Foydalanish: /rad <user_id>"); return
    try: user_id = int(context.args[0])
    except: await update.message.reply_text("Noto'g'ri user_id"); return
    try:
        await context.bot.send_message(chat_id=user_id, text="❌ Kechirasiz, to'lovingiz tasdiqlanmadi.\nQayta to'lov qilib chek yuboring.")
        await update.message.reply_text("❌ User " + str(user_id) + " rad etildi.")
    except Exception as e:
        await update.message.reply_text("Xatolik: " + str(e))


async def royxat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sub = get_subscriber(user.id)
    if sub and sub[5] == 1:
        await update.message.reply_text("Siz allaqachon ro'yxatdasiz.\nObuna muddati: " + str(sub[4]) + " gacha.")
        return
    end_date = add_subscriber(user.id, user.username, user.full_name)
    await update.message.reply_text("✅ Siz muvaffaqiyatli ro'yxatdan o'tkazildingiz!\nObuna muddati: " + str(end_date) + " gacha.")
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="🆕 /royxat orqali qo'shildi:\n👤 " + str(user.full_name) +
                 " (@" + (user.username or "yo'q") + ")\n🆔 " + str(user.id) +
                 "\n📅 " + str(end_date) + " gacha")
    except Exception as e:
        logging.error("Royxat admin xabari yuborilmadi: " + str(e))


async def reklama_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data["holat"] = "reklama_kutish"
    await update.message.reply_text(
        "📢 Reklama xabari\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing.\n"
        "Rasm bilan birga yubormoqchi bo'lsangiz — rasmni tavsif (caption) matni bilan birga yuboring.\n\n"
        "Bekor qilish uchun /bekor yozing.")


async def reklama_tayyorlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["reklama_type"] = "photo"
        context.user_data["reklama_photo_id"] = update.message.photo[-1].file_id
        context.user_data["reklama_text"] = update.message.caption or ""
    else:
        context.user_data["reklama_type"] = "text"
        context.user_data["reklama_text"] = update.message.text or ""
    context.user_data["holat"] = None
    users_soni = len(get_all_users())
    tasdiq_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yuborish", callback_data="reklama_tasdiq"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="reklama_bekor")
    ]])
    await update.message.reply_text(
        "👆 Ushbu xabar " + str(users_soni) + " ta foydalanuvchiga yuboriladi.\n\nTasdiqlaysizmi?",
        reply_markup=tasdiq_kb)


async def reklama_yuborish(context: ContextTypes.DEFAULT_TYPE):
    reklama_type = context.user_data.get("reklama_type")
    reklama_text = context.user_data.get("reklama_text", "")
    reklama_photo_id = context.user_data.get("reklama_photo_id")
    users = get_all_users()
    yuborildi = 0; yuborilmadi = 0
    for uid, uname, fname in users:
        try:
            if reklama_type == "photo":
                await context.bot.send_photo(chat_id=uid, photo=reklama_photo_id, caption=reklama_text)
            else:
                await context.bot.send_message(chat_id=uid, text=reklama_text)
            yuborildi += 1
        except Exception as e:
            yuborilmadi += 1
            logging.warning("Reklama yuborilmadi (ID: " + str(uid) + "): " + str(e))
        await asyncio.sleep(0.05)
    context.user_data.pop("reklama_type", None)
    context.user_data.pop("reklama_text", None)
    context.user_data.pop("reklama_photo_id", None)
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="📊 Reklama yuborish yakunlandi!\n\n✅ Yuborildi: " + str(yuborildi) +
             "\n❌ Yuborilmadi: " + str(yuborilmadi))


async def kirit_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data["holat"] = "bulk_add"
    await update.message.reply_text(
        "📋 *Ommaviy qo'shish*\n\n"
        "Quyidagi usullardan birini tanlang:\n\n"
        "━━━━━━━━━━━━━━━\n"
        "*1️⃣ Chatga yozib yuborish:*\n"
        "Har bir a'zoni alohida qatorda yuboring:\n\n"
        "@username\n"
        "@username 2026-09-01\n"
        "123456789\n"
        "123456789 2026-09-01\n\n"
        "━━━━━━━━━━━━━━━\n"
        "*2️⃣ .txt fayl yuklash:*\n"
        "Xuddi shu formatda .txt fayl tayyorlab yuboring — bot avtomatik o'qiydi.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📌 Sana ko'rsatilmasa — bugundan *30 kun* avtomatik qo'shiladi.\n"
        "Sana formati: YYYY-MM-DD (masalan 2026-09-01)\n\n"
        "Bekor qilish uchun /bekor yozing.",
        parse_mode="Markdown"
    )


async def bekor_qilish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    context.user_data["holat"] = None
    await update.message.reply_text("Bekor qilindi.")


async def bulk_add_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    lines = [ln.strip() for ln in text.strip().split("\n")
             if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        await update.message.reply_text("❗ Fayl bo'sh yoki noto'g'ri format.")
        context.user_data["holat"] = None
        return

    jami = len(lines)
    muvaffaq = 0
    xato = 0
    natija_muvaffaq = []
    natija_xato = []

    # Progress xabari
    progress_msg = await update.message.reply_text(
        f"⏳ Ishlanmoqda: 0/{jami}...")

    for i, line in enumerate(lines):
        parts = line.split()
        identifikator = parts[0]
        sana_str = parts[1] if len(parts) > 1 else None

        # Sana tekshirish
        try:
            end_date = (datetime.date.fromisoformat(sana_str)
                        if sana_str
                        else datetime.date.today() + datetime.timedelta(days=30))
        except ValueError:
            natija_xato.append(f"❌ {identifikator} — sana noto'g'ri (YYYY-MM-DD kerak)")
            xato += 1
            continue

        # Foydalanuvchini topish
        try:
            if identifikator.lstrip("-").isdigit():
                # Raqamli ID — get_chat ishlatmasdan to'g'ridan bazaga yozamiz
                uid = int(identifikator)
                add_subscriber_with_date(uid, None, str(uid), end_date)
                natija_muvaffaq.append(f"✅ {identifikator} → {end_date} gacha")
            else:
                # Username — get_chat kerak (lekin sekin)
                uname = identifikator.lstrip("@")
                chat = await context.bot.get_chat("@" + uname)
                add_subscriber_with_date(chat.id, chat.username, chat.full_name or uname, end_date)
                natija_muvaffaq.append(
                    f"✅ @{uname} → {chat.full_name or uname} ({end_date} gacha)")
            muvaffaq += 1
        except Exception as e:
            xatolar = str(e)
            natija_xato.append(f"❌ {identifikator} — topilmadi")
            xato += 1

        # Har 5 ta'da progress yangilaymiz
        if (i + 1) % 5 == 0 or (i + 1) == jami:
            try:
                await progress_msg.edit_text(
                    f"⏳ Ishlanmoqda: {i+1}/{jami}...\n"
                    f"✅ Muvaffaqiyatli: {muvaffaq} | ❌ Xato: {xato}")
            except Exception:
                pass

        # Rate limit uchun kutish (username bo'lsa)
        if not identifikator.lstrip("-").isdigit():
            await asyncio.sleep(0.3)

    # Yakuniy natija
    context.user_data["holat"] = None

    xulosa = f"📊 *Yakuniy natija:*\n✅ Qo'shildi: {muvaffaq} ta\n❌ Xato: {xato} ta\n\n"

    if natija_muvaffaq:
        xulosa += "*Muvaffaqiyatli:*\n" + "\n".join(natija_muvaffaq[:30])
        if len(natija_muvaffaq) > 30:
            xulosa += f"\n...va yana {len(natija_muvaffaq)-30} ta"

    if natija_xato:
        xulosa += "\n\n*Xatolar:*\n" + "\n".join(natija_xato[:20])

    # Xabar uzun bo'lsa faylga yozib yuboramiz
    if len(xulosa) > 3500:
        fayl_matn = f"Muvaffaqiyatli ({muvaffaq} ta):\n"
        fayl_matn += "\n".join(natija_muvaffaq)
        fayl_matn += f"\n\nXatolar ({xato} ta):\n"
        fayl_matn += "\n".join(natija_xato)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                          delete=False, encoding="utf-8") as f:
            f.write(fayl_matn)
            tmp_path = f.name
        with open(tmp_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename="natija.txt",
                caption=f"✅ Qo'shildi: {muvaffaq} ta | ❌ Xato: {xato} ta")
        os.unlink(tmp_path)
    else:
        await update.message.reply_text(xulosa, parse_mode="Markdown")


async def azolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rows = get_all_active()
    if not rows:
        await update.message.reply_text("Hozircha faol a'zolar yo'q."); return
    text = "👥 Faol obunachlar: " + str(len(rows)) + " ta\n\n"
    for row in rows:
        uid, uname, fname, sd, ed, act, warned = row
        text += "👤 " + fname + "\n🆔 " + str(uid)
        if uname: text += " | @" + uname
        text += "\n📅 " + str(sd) + " → " + str(ed) + "\n\n"
    await update.message.reply_text(text)


async def guruh_id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("Guruh ID: " + str(update.effective_chat.id))


async def foydalanuvchilar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botga kirgan barcha foydalanuvchilar ro'yxati (admin uchun)."""
    if update.effective_user.id != ADMIN_ID: return
    rows = get_all_users()
    if not rows:
        await update.message.reply_text("Hozircha hech kim botga kirmagan."); return

    jami = len(rows)
    faol = len(get_all_active())

    # Ro'yxat 50 tadan oshsa, faylga yozib yuboramiz
    if jami > 50:
        lines = [f"Jami: {jami} ta foydalanuvchi | Faol obunachi: {faol} ta\n"]
        for uid, uname, fname in rows:
            qator = f"👤 {fname} | 🆔 {uid}"
            if uname:
                qator += f" | @{uname}"
            lines.append(qator)
        content = "\n".join(lines)
        file_path = "/tmp/foydalanuvchilar.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        with open(file_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename="foydalanuvchilar.txt",
                caption=f"👥 Jami: *{jami}* ta foydalanuvchi\n💳 Faol obunachi: *{faol}* ta",
                parse_mode="Markdown")
    else:
        text = f"👥 Jami foydalanuvchilar: *{jami}* ta\n💳 Faol obunachi: *{faol}* ta\n\n"
        for uid, uname, fname in rows:
            text += f"👤 {fname} | 🆔 {uid}"
            if uname:
                text += f" | @{uname}"
            text += "\n"
        await update.message.reply_text(text, parse_mode="Markdown")

# ==========================================================
# SCHEDULER
# ==========================================================

async def warn_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    rows = get_expiring_soon(days=7)
    logging.info(f"warn_expiring_subscriptions: ogohlantiriladigan mijozlar: {len(rows)}")
    for row in rows:
        uid, uname, fname, sd, ed, act, warned = row
        try:
            await context.bot.send_message(chat_id=uid, text=
                "⏰ Obuna muddatingiz tugashiga bir necha kun qoldi!\n\n"
                "📅 Muddat: " + str(ed) + "\n\n"
                "Guruhda qolish uchun qayta to'lov qiling — QR-kodni skanerlang "
                "yoki quyidagi karta raqamiga o'tkazing:")

            qr_yuborildi = await send_qr_code(context, uid)
            if not qr_yuborildi:
                await context.bot.send_message(chat_id=uid, text=
                    "💳 Karta: " + KARTA_RAQAM + "\n"
                    "👤 Egasi: " + KARTA_EGASI + "\n"
                    "💰 Narxi: " + NARX)

            await context.bot.send_message(chat_id=uid, text=
                "To'lovdan so'ng chekni botga yuboring — admin tasdiqlaydi va obunangiz uzaytiriladi.")
            mark_warned(uid)
        except Exception as e:
            logging.error("Warn error: " + str(e))


async def check_expired_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    for row in get_expired():
        uid, uname, fname, sd, ed, act, warned = row
        if GURUH_ID:
            try:
                await context.bot.ban_chat_member(chat_id=GURUH_ID, user_id=uid)
                await context.bot.unban_chat_member(chat_id=GURUH_ID, user_id=uid)
            except Exception as e:
                logging.error("Kick error: " + str(e))
        try:
            await context.bot.send_message(chat_id=uid, text=
                "❌ Obuna muddatingiz tugadi!\n\nGuruhdan chiqarildingiz.\n\n"
                "Qayta obuna bo'lish uchun /start dan Yopiq guruhga kirish tugmasini bosing.")
        except Exception as e:
            logging.error("Notify error: " + str(e))
        deactivate(uid)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="📤 Obuna tugadi: " + str(fname) + " (ID: " + str(uid) + ") guruhdan chiqarildi.")

# ==========================================================
# MATN TUGMALAR HANDLERI
# ==========================================================

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Admin maxsus holatlari
    if update.effective_user.id == ADMIN_ID and context.user_data.get("holat") == "reklama_kutish":
        await reklama_tayyorlash(update, context); return
    if update.effective_user.id == ADMIN_ID and context.user_data.get("holat") == "bulk_add":
        await bulk_add_process(update, context, text); return

    # Qabul so'rovnomasi holatlari
    if context.user_data.get("holat") == "ism":
        context.user_data["ism"] = text; context.user_data["holat"] = "telefon"
        await update.message.reply_text("📞 Telefon raqamingizni yozing:"); return
    if context.user_data.get("holat") == "telefon":
        context.user_data["telefon"] = text; context.user_data["holat"] = "muammo"
        await update.message.reply_text("💬 Muammoingizni yozing:"); return
    if context.user_data.get("holat") == "muammo":
        ism = context.user_data.get("ism"); telefon = context.user_data.get("telefon")
        context.user_data["holat"] = None
        await update.message.reply_text("✅ So'rovingiz qabul qilindi, tez orada siz bilan bog'lanamiz!", reply_markup=main_keyboard)
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📥 Yangi qabul:\n\n👤 {ism}\n📞 {telefon}\n💬 {text}")
        return

    # Asosiy tugmalar
    if text == "Xizmatlar": await xizmatlar(update, context)
    elif text == "Muammoyingiz nimada": await muammolar(update, context)
    elif text == "Bog'lanish": await boglanish(update, context)
    elif text == "Ko'p beriladigan savollar": await savollar(update, context)
    elif text in ("Qabulga yozilish", "🟢 Qabulga yozilish"): await qabul(update, context)
    elif text == "✅ Ha, tushundim — yozilaman": await qabul_boshlash(update, context)
    elif text == "💳 Yopiq guruhga kirish": await guruhga_kirish(update, context)
    elif text == "🔄 Obunani uzaytirish": await tolov_korsat(update, context)
    elif text == "✅ To'lovni tasdiqlayman":
        if context.user_data.get("holat") == "tolov_kutish":
            await update.message.reply_text("📸 To'lov chekining rasmini yuboring.")
        else:
            await guruhga_kirish(update, context)
    # Xizmatlar
    elif text == "🏥 Jonli qabul": await jonli_qabul(update, context)
    elif text == "📚 10 kunlik onlayn kurs": await kurs(update, context)
    elif text == "🔐 Yopiq kanal": await yopiq_kanal_xizmat(update, context)
    # Muammolar
    elif text == "Xavotir": await xavotir_info(update, context)
    elif text == "Vahima xuruji": await vahima_info(update, context)
    elif text == "Tushkunlik": await tushkunlik_info(update, context)
    elif text == "Yopishqoq xayollar": await yopishqoq_xayollar_info(update, context)
    elif text == "Uyqu muammolari": await uyqu_info(update, context)
    elif text == "Yurak tez urib ketishi": await yurak_info(update, context)
    elif text == "Nafas qisishi": await nafas_info(update, context)
    elif text == "Tomoqqa tiqilish hissi": await tomoqqa_info(update, context)
    elif text == "Bosh og'rig'i": await bosh_ogriq_info(update, context)
    elif text == "Bosh aylanishi": await bosh_aylanish_info(update, context)
    elif text == "Ich kelishidagi muammolar": await ich_info(update, context)
    elif text == "Peshob qilish hissi": await peshob_info(update, context)
    elif text == "Tanadagi qaltirashlar": await qaltirash_info(update, context)
    elif text == "Ozib ketish yoki semirish": await vazn_info(update, context)
    # Psixologik testlar
    elif text == "🧪 Psixologik testlar": await psixologik_testlar(update, context)
    elif text == "😰 Xavotirni baholash (GAD-7)": await start_gad7(update, context)
    elif text == "😔 Depressiyani baholash (PHQ-9)": await start_phq9(update, context)
    # Boshqa
    elif text == "ALBATTA BORAMAN": await manzilni_korsat(update, context)
    elif text in ("⬅️ Ortga", "Ortga"): await start(update, context)
    else: await update.message.reply_text("Kerakli bo'limni tanlang.", reply_markup=main_keyboard)

# ==========================================================
# MAIN
# ==========================================================

def main():
    init_db()

    joriy_papka = os.path.dirname(os.path.abspath(__file__))
    try:
        fayllar = os.listdir(joriy_papka)
        logging.info(f"DIAGNOSTIKA - joriy papka: {joriy_papka}")
        logging.info(f"DIAGNOSTIKA - papkadagi fayllar: {fayllar}")
    except Exception as e:
        logging.error(f"DIAGNOSTIKA xatosi: {e}")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, log_user_middleware), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("xizmatlar", xizmatlar))
    app.add_handler(CommandHandler("boglanish", boglanish))
    app.add_handler(CommandHandler("savollar", savollar))
    app.add_handler(CommandHandler("qabul", qabul))
    app.add_handler(CommandHandler("guruh_id", guruh_id_cmd))
    app.add_handler(CommandHandler("tasdiqlash", tasdiqlash))
    app.add_handler(CommandHandler("rad", rad_etish))
    app.add_handler(CommandHandler("azolar", azolar))
    app.add_handler(CommandHandler("royxat", royxat))
    app.add_handler(CommandHandler("kirit", kirit_boshlash))
    app.add_handler(CommandHandler("bekor", bekor_qilish))
    app.add_handler(CommandHandler("reklama", reklama_boshlash))
    app.add_handler(CommandHandler("foydalanuvchilar", foydalanuvchilar))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_payment_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.job_queue.run_daily(check_expired_subscriptions, time=datetime.time(hour=9, minute=0, tzinfo=TASHKENT_TZ))
    app.job_queue.run_daily(warn_expiring_subscriptions, time=datetime.time(hour=9, minute=5, tzinfo=TASHKENT_TZ))

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
