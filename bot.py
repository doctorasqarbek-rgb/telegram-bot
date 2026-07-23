import sqlite3
import datetime
import logging
import os
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "6411235489:AAEqW4eNu04qOsEmnwDImZrBvKUIhtm1TSE")
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
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        start_date TEXT, end_date TEXT, active INTEGER DEFAULT 1)""")
    # Har bir foydalanuvchining test o'tkazgan vaqtini saqlaydi
    c.execute("""CREATE TABLE IF NOT EXISTS test_history (
        user_id INTEGER,
        test_turi TEXT,
        oxirgi_sana TEXT,
        PRIMARY KEY (user_id, test_turi))""")
    conn.commit(); conn.close()


def can_take_test(user_id, test_turi):
    """Foydalanuvchi bu haftada testni o'tkazganmi? (True, None) = o'tkazsa bo'ladi."""
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
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
    """Test o'tkazilgan sanani bazaga yozish."""
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO test_history (user_id, test_turi, oxirgi_sana) VALUES (?,?,?)",
              (user_id, test_turi, str(datetime.date.today())))
    conn.commit(); conn.close()


def add_subscriber(user_id, username, full_name):
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    today = datetime.date.today()
    c.execute("SELECT end_date, active FROM subscribers WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[1] == 1:
        current_end = datetime.date.fromisoformat(row[0])
        base = current_end if current_end > today else today
    else:
        base = today
    end = base + datetime.timedelta(days=30)
    c.execute("INSERT OR REPLACE INTO subscribers (user_id,username,full_name,start_date,end_date,active) VALUES (?,?,?,?,?,1)",
              (user_id, username or "", full_name, str(today), str(end)))
    conn.commit(); conn.close(); return end


def get_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE user_id=?", (user_id,))
    row = c.fetchone(); conn.close(); return row


def get_all_active():
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE active=1")
    rows = c.fetchall(); conn.close(); return rows


def get_expired():
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    today = str(datetime.date.today())
    c.execute("SELECT * FROM subscribers WHERE active=1 AND end_date<?", (today,))
    rows = c.fetchall(); conn.close(); return rows


def get_expiring_soon(days=7):
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    target = str(datetime.date.today() + datetime.timedelta(days=days))
    c.execute("SELECT * FROM subscribers WHERE active=1 AND end_date=?", (target,))
    rows = c.fetchall(); conn.close(); return rows


def deactivate(user_id):
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("UPDATE subscribers SET active=0 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()

# ==========================================================
# PSIXOLOGIK TESTLAR — SAVOLLAR VA BAHOLASH
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
    """0-3 ball uchun inline tugmalar."""
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
    ["🧪 Psixologik testlar"],        # ← YANGI
], resize_keyboard=True)

xizmat_keyboard = ReplyKeyboardMarkup([
    ["🧠 Individual suhbat"],
    ["🌐 Onlayn konsultatsiya"],
    ["📚 10 kunlik kurs"],
    ["🎥 Nevroz videolari"],
    ["⬅️ Ortga"]
], resize_keyboard=True)

test_keyboard = ReplyKeyboardMarkup([    # ← YANGI
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


async def individual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 Individual psixologik suhbat\n\n"
        "Bu xizmatda siz bilan jonli formatda individual ishlanadi.\n"
        "Suhbat davomida holatingiz tahlil qilinadi, muammoning sabablari aniqlanadi, "
        "sizga mos tavsiyalar beriladi va vaziyatga qarab dorilar ham yozib beriladi.\n\n"
        "✅ Kimlar uchun:\n"
        "• Nevroz, xavotir, vahima, tushkunlik holatlari bo'lsa\n"
        "• Psixologik jonli suhbat xohlovchilar uchun\n"
        "• Ruhiy zo'riqish, asabiylik bo'lsa\n\n"
        "⏱ Davomiyligi: 30-60 daqiqa\n"
        "📍 Format: Jonli qabul\n"
        "💰 Narxi: 600 ming so'm",
        reply_markup=muammo_keyboard())


async def onlayn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌐 Onlayn individual konsultatsiya\n\n"
        "Bu xizmat masofadan turib suhbat qilish uchun mo'ljallangan.\n"
        "Telegram yoki boshqa qulay ilova orqali olib boriladi va vaziyatga qarab dorilar ham yozib beriladi.\n\n"
        "✅ Kimlar uchun:\n"
        "• Uzoqda yashaydiganlar\n"
        "• Vaqti cheklanganlar\n"
        "• Uy sharoitida maslahat olishni xohlaydiganlar\n\n"
        "⏱ Davomiyligi: 30-60 daqiqa\n"
        "📱 Format: Onlayn\n"
        "💰 Narxi: 500 ming so'm",
        reply_markup=muammo_keyboard())


async def kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 10 kunlik onlayn davolash kursi\n\n"
        "Bu kurs nevroz, xavotir va depressiya bilan ishlash uchun bosqichma-bosqich tuzilgan.\n"
        "Unda jonli tarzda tushuntirish, topshiriq va amaliy tavsiyalar beriladi.\n\n"
        "✅ Kurs ichida:\n"
        "• Har kungi yangi mavzular\n"
        "• Dorilar yozib berish\n"
        "• Amaliy mashqlar\n"
        "• Mustaqil ishlash uchun tavsiyalar\n\n"
        "📅 Davomiyligi: 10 kun\n"
        "📱 Format: Onlayn\n"
        "💰 Narxi: 1 mln so'm",
        reply_markup=muammo_keyboard())


async def videolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 Nevroz bo'yicha darslik videolari\n\n"
        "Bunda nevroz, xavotir va tushkunlikni tushunishga yordam beruvchi videolar to'plami beriladi.\n"
        "Mustaqil o'rganish uchun qulay va arzon format.\n\n"
        "✅ Nimalarni o'rganasiz:\n"
        "• Nevroz va depressiya nima ekanini\n"
        "• Belgilarini\n"
        "• Rivojlanishini\n"
        "• Undan qutulish yo'llarini\n\n"
        "📹 Format: Video darslar\n"
        "💰 Narxi: 480 ming so'm",
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
    context.user_data["holat"] = "ism"
    await update.message.reply_text("📝 Qabulga yozilish\n\nIltimos, ism va familiyangizni yozing.")


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


async def guruhga_kirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sub = get_subscriber(user.id)
    if sub and sub[5] == 1:
        await update.message.reply_text(
            "Siz allaqachon faol a'zo siz!\n\nObuna tugash sanasi: " + str(sub[4]) + "\n\nGuruh linki:\n" + GURUH_LINK,
            reply_markup=main_keyboard)
        return

    await update.message.reply_text(
        "🔒 Yopiq guruh haqida\n\n"
        "Bu guruhda inson ruhiyati, ruhiy buzilish va kasalliklar haqidagi "
        "qimmatli ma'lumotlarni atigi 100 ming so'm evaziga oylik obuna bo'lish orqali o'rganib borasiz.\n\n"
        "🎬 Qanday kirish kerakligi haqida videoqo'llanma:\n" + VIDEO_QOLLANMA_LINK + "\n\n"
        "To'lov QR-kod orqali amalga oshiriladi:")

    mumkin_boigan_yollar = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), XOLIS_QR_FAYL),
        os.path.join(os.getcwd(), XOLIS_QR_FAYL),
        XOLIS_QR_FAYL,
    ]
    qr_path = None
    for yol in mumkin_boigan_yollar:
        if os.path.exists(yol):
            qr_path = yol
            break

    if qr_path:
        with open(qr_path, "rb") as qr_photo:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=qr_photo,
                caption=(
                    "📱 QR-kod orqali to'lash\n\n"
                    "Ushbu QR-kodni istalgan bank yoki to'lov ilovasi orqali skanerlang.\n\n"
                    "💡 Agar bitta telefon ishlatsangiz: rasmni saqlab, "
                    "to'lov ilovasidagi QR skaner bo'limida \"Galereyadan tanlash\" orqali yuklashingiz mumkin.\n\n"
                    "💰 To'lanishi kerak summa: " + NARX
                ))

    await update.message.reply_text(
        "❗️ To'lovni amalga oshirgach, to'lov tasdig'i (chek yoki skrinshot) rasmini "
        "shu chatga yuboring.\nAdmin 5-10 daqiqa ichida guruh linkini yuboradi.",
        reply_markup=tolov_keyboard)
    context.user_data["holat"] = "tolov_kutish"


# ==========================================================
# PSIXOLOGIK TEST HANDLERLARI  ← YANGI
# ==========================================================

async def psixologik_testlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test menyusini ko'rsatish."""
    context.user_data.pop("holat", None)
    await update.message.reply_text(
        "🧪 Psixologik testlar\n\n"
        "Quyidagi testlar so'nggi 2 hafta ichidagi holatingizni baholaydi.\n\n"
        "⚠️ Bu testlar tibbiy tashxis emas — faqat dastlabki baholash uchun.\n\n"
        "Qaysi testni o'tkazmoqchisiz?",
        reply_markup=test_keyboard)


async def start_gad7(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GAD-7 testini boshlash."""
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
    """PHQ-9 testini boshlash."""
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
    """Joriy savolni yuborish."""
    test_turi = context.user_data["test_turi"]
    q_index = context.user_data["test_savol"]

    questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
    test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
    total = len(questions)

    # Progress
    filled = int((q_index / total) * 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    await message.reply_text(
        f"📋 *{test_nomi}*\n"
        f"{bar}  {q_index}/{total}\n\n"
        f"*{questions[q_index]}*\n\n"
        f"_So'nggi 2 hafta ichida:_",
        parse_mode="Markdown",
        reply_markup=build_answer_keyboard()
    )


async def handle_payment_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return
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
# CALLBACK HANDLER (to'lov + test javoblari)
# ==========================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── TEST JAVOBLARI ────────────────────────────────────
    if data.startswith("ta:"):
        ball = int(data.split(":")[1])
        context.user_data["test_ballar"].append(ball)
        context.user_data["test_savol"] += 1

        test_turi = context.user_data["test_turi"]
        q_index = context.user_data["test_savol"]
        questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
        total = len(questions)

        if q_index >= total:
            # Test tugadi — sanani bazaga yozish va natijani ko'rsatish
            jami = sum(context.user_data["test_ballar"])
            context.user_data["holat"] = None
            record_test(query.from_user.id, test_turi)   # ← haftalik cheklov uchun

            if test_turi == "gad7":
                test_nomi = "GAD-7 – Xavotir testi"
                max_ball = 21
                daraja, maslahat = get_gad7_result(jami)
            else:
                test_nomi = "PHQ-9 – Depressiya testi"
                max_ball = 27
                daraja, maslahat = get_phq9_result(jami)

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
                f"📢 *Yopiq kanalimiz haqida:*\n"
                f"Oyiga *100 000 so'm* evaziga xavotir va tushkunlikdan "
                f"chiqish yo'llarini yopiq kanalimizdan o'rganing! 👇",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 Yopiq kanalga kirish", url=GURUH_LINK)],
                    [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="ta:menu")],
                ])
            )
        elif data == "ta:menu":
            await query.edit_message_text("Asosiy menyuga qaytdingiz.")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Kerakli bo'limni tanlang:",
                reply_markup=main_keyboard)
        elif data.startswith("ta:restart_"):
            # Haftalik cheklovni tekshirib qayta boshlash
            test_turi = data.split("_")[1]
            mumkin, qolgan_kun = can_take_test(query.from_user.id, test_turi)
            if not mumkin:
                test_nomi = "GAD-7" if test_turi == "gad7" else "PHQ-9"
                await query.edit_message_text(
                    f"⏳ *{test_nomi}* testini qayta o'tkazish uchun "
                    f"*{qolgan_kun} kun* kutishingiz kerak.\n\n"
                    f"Test natijalarini kuzatib borish uchun haftada bir marta o'tkazish tavsiya etiladi.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="ta:menu")]
                    ])
                )
                return
            context.user_data["test_turi"] = test_turi
            context.user_data["test_savol"] = 0
            context.user_data["test_ballar"] = []
            context.user_data["holat"] = "test_javob"
            questions = GAD7_QUESTIONS if test_turi == "gad7" else PHQ9_QUESTIONS
            test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
            bar = "⬜" * 10
            await query.edit_message_text(
                f"📋 *{test_nomi}*\n{bar}  0/{len(questions)}\n\n"
                f"*{questions[0]}*\n\n_So'nggi 2 hafta ichida:_",
                parse_mode="Markdown",
                reply_markup=build_answer_keyboard()
            )
        else:
            # Keyingi savolni inline xabarda ko'rsatish
            filled = int((q_index / total) * 10)
            bar = "🟩" * filled + "⬜" * (10 - filled)
            test_nomi = "GAD-7 – Xavotir testi" if test_turi == "gad7" else "PHQ-9 – Depressiya testi"
            await query.edit_message_text(
                f"📋 *{test_nomi}*\n"
                f"{bar}  {q_index}/{total}\n\n"
                f"*{questions[q_index]}*\n\n_So'nggi 2 hafta ichida:_",
                parse_mode="Markdown",
                reply_markup=build_answer_keyboard()
            )
        return

    # ── TO'LOV TASDIQLASH / RAD (admin) ───────────────────
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


async def azolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rows = get_all_active()
    if not rows:
        await update.message.reply_text("Hozircha faol a'zolar yo'q."); return
    text = "👥 Faol obunachlar: " + str(len(rows)) + " ta\n\n"
    for row in rows:
        uid, uname, fname, sd, ed, act = row
        text += "👤 " + fname + "\n🆔 " + str(uid)
        if uname: text += " | @" + uname
        text += "\n📅 " + str(sd) + " → " + str(ed) + "\n\n"
    await update.message.reply_text(text)


async def guruh_id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("Guruh ID: " + str(update.effective_chat.id))


# ==========================================================
# SCHEDULER
# ==========================================================

async def warn_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    for row in get_expiring_soon(days=7):
        uid, uname, fname, sd, ed, act = row
        try:
            await context.bot.send_message(chat_id=uid, text=
                "⏰ Obuna muddatingiz tugashiga 7 kun qoldi!\n\n"
                "📅 Muddat: " + str(ed) + "\n\n"
                "Guruhda qolish uchun qayta to'lov qiling:\n\n"
                "💳 Karta: " + KARTA_RAQAM + "\n"
                "👤 Egasi: " + KARTA_EGASI + "\n"
                "💰 Narxi: " + NARX + "\n\n"
                "To'lovdan so'ng chekni botga yuboring — admin tasdiqlaydi va obunangiz uzaytiriladi.")
        except Exception as e:
            logging.error("Warn error: " + str(e))


async def check_expired_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    for row in get_expired():
        uid, uname, fname, sd, ed, act = row
        if GURUH_ID:
            try:
                await context.bot.ban_chat_member(chat_id=GURUH_ID, user_id=uid)
                await context.bot.unban_chat_member(chat_id=GURUH_ID, user_id=uid)
            except Exception as e:
                logging.error("Kick error: " + str(e))
        try:
            await context.bot.send_message(chat_id=uid, text=
                "❌ Obuna muddatingiz tugadi!\n\nGuruhdan chiqarildingiz.\n\nQayta obuna bo'lish uchun /start dan Yopiq guruhga kirish tugmasini bosing.")
        except Exception as e:
            logging.error("Notify error: " + str(e))
        deactivate(uid)
        await context.bot.send_message(chat_id=ADMIN_ID, text="📤 Obuna tugadi: " + str(fname) + " (ID: " + str(uid) + ") guruhdan chiqarildi.")


# ==========================================================
# MATN TUGMALAR HANDLERI
# ==========================================================

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Qabul uchun holat machiners
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

    # Asosiy va xizmat tugmalari
    if text == "Xizmatlar": await xizmatlar(update, context)
    elif text == "Muammoyingiz nimada": await muammolar(update, context)
    elif text == "Bog'lanish": await boglanish(update, context)
    elif text == "Ko'p beriladigan savollar": await savollar(update, context)
    elif text in ("Qabulga yozilish", "🟢 Qabulga yozilish"): await qabul(update, context)
    elif text == "💳 Yopiq guruhga kirish": await guruhga_kirish(update, context)
    elif text == "✅ To'lovni tasdiqlayman":
        if context.user_data.get("holat") == "tolov_kutish":
            await update.message.reply_text("📸 To'lov chekining rasmini yuboring.")
        else:
            await guruhga_kirish(update, context)
    elif text == "🧠 Individual suhbat": await individual(update, context)
    elif text == "🌐 Onlayn konsultatsiya": await onlayn(update, context)
    elif text == "📚 10 kunlik kurs": await kurs(update, context)
    elif text == "🎥 Nevroz videolari": await videolar(update, context)
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
    elif text == "ALBATTA BORAMAN": await manzilni_korsat(update, context)
    # ── TEST TUGMALARI ────────────────────────────────────
    elif text == "🧪 Psixologik testlar": await psixologik_testlar(update, context)
    elif text == "😰 Xavotirni baholash (GAD-7)": await start_gad7(update, context)
    elif text == "😔 Depressiyani baholash (PHQ-9)": await start_phq9(update, context)
    # ─────────────────────────────────────────────────────
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

    # Buyruqlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("xizmatlar", xizmatlar))
    app.add_handler(CommandHandler("boglanish", boglanish))
    app.add_handler(CommandHandler("savollar", savollar))
    app.add_handler(CommandHandler("qabul", qabul))
    app.add_handler(CommandHandler("guruh_id", guruh_id_cmd))
    app.add_handler(CommandHandler("tasdiqlash", tasdiqlash))
    app.add_handler(CommandHandler("rad", rad_etish))
    app.add_handler(CommandHandler("azolar", azolar))

    # Callback va media
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_payment_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    # Kunlik vazifalar
    app.job_queue.run_daily(check_expired_subscriptions, time=datetime.time(hour=9, minute=0))
    app.job_queue.run_daily(warn_expiring_subscriptions, time=datetime.time(hour=9, minute=5))

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
