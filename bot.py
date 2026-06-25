import sqlite3
import datetime
import logging
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler

logging.basicConfig(level=logging.INFO)

TOKEN = "6411235489:AAGBVw5jHOQvlfOnQAUouKsYi0MtDfmJSzY"
ADMIN_ID = 741361382
KARTA_RAQAM = "9860 1606 0775 6576"
KARTA_EGASI = "Sevinch Ergasheva"
NARX = "100 000 so'm"
GURUH_LINK = "https://t.me/+PujFAoCdY85kMDQy"
GURUH_ID = -1004397770642

def init_db():
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        start_date TEXT, end_date TEXT, active INTEGER DEFAULT 1)""")
    conn.commit(); conn.close()

def add_subscriber(user_id, username, full_name):
    conn = sqlite3.connect("subscribers.db"); c = conn.cursor()
    start = datetime.date.today(); end = start + datetime.timedelta(days=30)
    c.execute("INSERT OR REPLACE INTO subscribers (user_id,username,full_name,start_date,end_date,active) VALUES (?,?,?,?,?,1)",
              (user_id, username or "", full_name, str(start), str(end)))
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

main_keyboard = ReplyKeyboardMarkup([
    ["Xizmatlar"],
    ["Muammoyingiz nimada", "Bog'lanish"],
    ["Ko'p beriladigan savollar", "Qabulga yozilish"],
    ["💳 Yopiq guruhga kirish"]
], resize_keyboard=True)

xizmat_keyboard = ReplyKeyboardMarkup([
    ["🧠 Individual suhbat"],
    ["🌐 Onlayn konsultatsiya"],
    ["📚 10 kunlik kurs"],
    ["🎥 Nevroz videolari"],
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
        "😟 Xavotir\n\n"
        "Xavotir — ichki bezovtalik, nimadandir yomon narsa kutish va ortiqcha o'ylash bilan kechadigan holat.\n\n"
        "✅ Belgilari:\n"
        "• Ichki siqilish\n"
        "• Tinchlana olmaslik\n"
        "• Yurak tez urishi\n"
        "• Bezovtalik\n"
        "• Xayollarning to'xtamasligi\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def vahima_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😰 Vahima xuruji\n\n"
        "Vahima xuruji — to'satdan kuchli qo'rquv, yurak urishi, nafas qisishi va nazoratni yo'qotayotgandek hissiyot bilan kechadigan holat.\n\n"
        "✅ Belgilari:\n"
        "• Yurak tez urishi\n"
        "• Nafas qisishi\n"
        "• Qo'l-oyoqlarda titroq\n"
        "• Kuchli qo'rquv\n"
        "• O'lib qolayotgandek hissiyot\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def tushkunlik_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌫 Tushkunlik\n\n"
        "Tushkunlik — kayfiyat pasayishi, hayotga qiziqish kamayishi va ichki bo'shliq hissi bilan kechadigan holat.\n\n"
        "✅ Belgilari:\n"
        "• Kayfiyatning pasayishi\n"
        "• Qiziqish yo'qolishi\n"
        "• Charchoq\n"
        "• Umidsizlik\n"
        "• Yolg'izlik hissi\n\n"
        "📌 Bu holatda Depressiyada kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def yopishqoq_xayollar_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔄 Yopishqoq xayollar\n\n"
        "Yopishqoq xayollar — ongga qayta-qayta kelaveradigan, bezovta qiladigan va to'xtatish qiyin bo'lgan fikrlar.\n\n"
        "✅ Belgilari:\n"
        "• Bir xil fikrlarning qayta qayta takrorlanishi\n"
        "• Bezovtalik\n"
        "• Xayollarni qutulib bo'lmaslik\n"
        "• Ichki zo'riqish\n\n"
        "📌 Bu holat ko'pincha Obsessiv Kompulsiv Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def uyqu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌙 Uyqu muammolari\n\n"
        "Uyqu muammolari — uxlab qolish qiyinligi yoki ko'p uxlash, tez uyg'onish yoki uyqudan keyin dam olmagandek hissiyot bo'lish bilan kechadi.\n\n"
        "✅ Belgilari:\n"
        "• Uxlash qiyin bo'lishi yoki ba'zilarda ko'p uxlash\n"
        "• Sal narsaga uyg'onib ketish\n"
        "• Uyqudan charchoq bilan turish\n"
        "• Kunduzi uyquchanlik\n\n"
        "📌 Bunga stress, xavotir va ruhiy zo'riqish sabab bo'lishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def yurak_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❤️ Yurak tez urib ketishi\n\n"
        "Yurakning tez urib ketishi ko'pincha xavotir, vahima yoki ichki zo'riqish bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Yurakning kuchli urishi\n"
        "• Ichki qo'rquv, xuddi yuragi to'xtab o'lib qoladiganday bo'lish\n"
        "• Bezovtalik\n"
        "• Yurak tez urishidan qo'rqib pulsni tez-tez o'lchash\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def nafas_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "😮‍💨 Nafas qisishi\n\n"
        "Nafas qisishi hissi ba'zan xavotir, vahima yoki ichki zo'riqish fonida paydo bo'ladi.\n\n"
        "✅ Belgilari:\n"
        "• To'liq nafas ololmaslik hissi\n"
        "• Ko'krakda siqilish\n"
        "• Qo'rquv\n"
        "• Tez-tez chuqur nafas olishga urinish\n\n"
        "📌 Bu holat Nevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def tomoqqa_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🫢 Tomoqqa tiqilish hissi\n\n"
        "Tomoqqa tiqilish hissi ko'pincha xavotir va ichki zo'riqish bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Yutinish qiyin bo'lgandek tuyulishi\n"
        "• Tomoqda nimadir bordek hissiyot\n"
        "• Bezovtalik kuchayishi\n\n"
        "📌 Organik sabablar bo'lmasa, bu holat psixosomatik bo'lishi mumkin. Ko'pincha Nevroz yoki Depressiyada kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def bosh_ogriq_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤕 Bosh og'rig'i\n\n"
        "Bosh og'rig'i stress, xavotir va ruhiy zo'riqish bilan kuchayishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Boshda bosim hissi\n"
        "• Peshona yoki ensa og'rig'i, og'riqlar ko'pincha ko'chib yuradi\n"
        "• Stress bilan og'riqning kuchayishi\n\n"
        "📌 Ruhiy holat barqarorlashsa, boshdagi og'riqlar ham kamayishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def bosh_aylanish_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💫 Bosh aylanishi\n\n"
        "Bosh aylanishi ba'zan xavotir, qo'rquv va ichki zo'riqish bilan birga kuzatiladi.\n\n"
        "✅ Belgilari:\n"
        "• Bosh aylangandek bo'lishi\n"
        "• Muvozanat buzilgandek tuyulishi\n"
        "• Qo'rquv bilan kuchayishi\n\n"
        "📌 Organik sabablar bo'lmasa, bu holat psixosomatik bo'lishi mumkin. Ko'pincha Nevroz yoki Depressiyada kuzatiladi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def ich_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚽 Ich kelishidagi muammolar\n\n"
        "Ichaklar faoliyatidagi o'zgarishlar stress, xavotir va ruhiy zo'riqish bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Ich qotishi yoki ich ketishi\n"
        "• Qorin dam bo'lishi\n"
        "• Ichakda noqulaylik\n\n"
        "📌 Ichak faoliyatidagi muammo ko'pincha xavotir hissi paydo bo'lganda kuchayadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def peshob_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚻 Peshob qilish hissi\n\n"
        "Tez-tez peshob qilish hissi ham ba'zan xavotir va ichki zo'riqish bilan kuchayadi.\n\n"
        "✅ Belgilari:\n"
        "• Tez-tez hojatga borish hissi\n"
        "• Bezovtalik bilan kuchayishi\n"
        "• Muhim paytda ko'proq sezilishi\n\n"
        "📌 Organik sabablar bo'lmasa, bu ham psixosomatik ko'rinish bo'lishi mumkin.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def qaltirash_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🪨 Tanadagi qaltirashlar\n\n"
        "Tanadagi qaltirashlar xavotir, vahima va kuchli ichki zo'riqish paytida kuzatilishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Qo'l-oyoqlarda titroq\n"
        "• Ichki qaltirash\n"
        "• Qo'rquv bilan kuchayishi\n\n"
        "📌 Bu holat asabiy zo'riqish bilan bog'liq bo'lishi mumkin, ko'pincha Nevrozda kuchayadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def vazn_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚖️ Ozib ketish yoki semirish\n\n"
        "Vaznning o'zgarishi ruhiy holat, stress, xavotir yoki tushkunlik bilan bog'liq bo'lishi mumkin.\n\n"
        "✅ Belgilari:\n"
        "• Ishtahaning kamayishi yoki oshishi\n"
        "• Tez ozish\n"
        "• Ortiqcha ovqat yeyish\n"
        "• Emotsional ovqatlanish\n\n"
        "📌 Ruhiy holatni to'g'rilansa insondagi ishtaha o'zgarishi ham o'z o'rniga tushadi.\n\n"
        "❗ Eslatma: Sizda bu muammo bilan birga tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def boglanish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Bog'lanish ma'lumotlari\n\n"
        "📱 Telefon:\n"
        "+998 88 306 06 95\n\n"
        "📸 Instagram:\n"
        "https://www.instagram.com/doktor.ergashev?igsh=MXc5eTN2NjF1NGZqaw==\n\n"
        "🎥 YouTube:\n"
        "https://youtube.com/@doktor_ergashev?si=s939zn1cW_N7BLu-")

async def savollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Ko'p beriladigan savollar\n\n"
        "1️⃣ Psixoterapiya nima?\n"
        "Psixoterapiya — bu ruhiy muammolarni suhbat orqali davolash usuli.\n\n"
        "2️⃣ Bir marta kelish yetarlimi?\n"
        "Ayrim insonlarda bitta konsultatsiya yetarli bo'lishi mumkin, lekin ko'pchilikda bir necha seans yoki 10 kunlik onlayn kurs samaraliroq bo'ladi.\n\n"
        "3️⃣ Dorilar majburiymi?\n"
        "Yo'q, har doim ham emas. Lekin ko'p hollarda (taxminan 70–80%) holatga qarab yoziladi.\n\n"
        "4️⃣ Qancha vaqtda natija bo'ladi?\n"
        "Bu sizning holatingizga bog'liq. Ba'zida tez (1 oy ichida), lekin odatda 2–3 oyda natija bo'ladi.\n\n"
        "5️⃣ Onlayn davolanish ham samaralimi?\n"
        "Ha, to'g'ri olib borilsa onlayn psixoterapiya ham juda yaxshi natija beradi.\n\n"
        "6️⃣ Bu sehr yoki jin tegish kasalligi emasmi?\n"
        "Yo'q! Nevroz yoki depressiya bu tibbiy-psixologik holat hisoblanadi.\n\n"
        "7️⃣ Bu kasallikdan butunlay sog'ayish mumkinmi?\n"
        "Ha, ko'p hollarda (taxminan 70%) insonlar to'liq sog'ayadi.\n\n"
        "8️⃣ Bu kasallikdan o'lib qolish yoki jinni bo'lib qolish mumkinmi?\n"
        "Yo'q, xavotir olmang. Bu holat hayot uchun xavfli emas va insonni jinni qilib qo'ymaydi.\n\n"
        "9️⃣ Bu shizofreniya emasmi?\n"
        "Yo'q. Shizofreniya jiddiy psixik kasallik bo'lib, u bilan psixiatrlar shug'ullanadi.\n\n"
        "🔟 Doktor Ergashev kim?\n"
        "Doktor Ergashev — Toshkent Tibbiyot Akademiyasi Tibbiy psixologiya yo'nalishi magistr bitiruvchisi. "
        "2023-yildan beri faoliyat yuritadi va 3000 dan ortiq bemorlar bilan ishlab, nevroz va depressiv holatlarni davolab kelmoqda.")

async def qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["holat"] = "ism"
    await update.message.reply_text(
        "📝 Qabulga yozilish\n\n"
        "Iltimos, ism va familiyangizni yozing.")

async def manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manzil_keyboard = ReplyKeyboardMarkup([["ALBATTA BORAMAN"], ["⬅️ Ortga"]], resize_keyboard=True)
    await update.message.reply_text(
        "⚠️ DIQQAT!\n\n"
        "QABULGA YOZILIB KELISHINGIZ SHART, CHUNKI BU ODDIY DORI YOZIB BERISH EMAS, "
        "PSIXOTERAPIYA HISOBLANADI!\n\n"
        "YOZILMASDAN KELSANGIZ, QABULGA KIRMASDAN KETISHINGIZ MUMKIN.\n\n"
        "AGAR KELISHINGIZ ANIQ BO'LMASA, ILTIMOS, SIZNING O'RNINGIZGA BOSHQA INSON KELISHI MUMKIN. "
        "SHUNING UCHUN SHUNCHAKI YOL'G'ONDAN 'KELAMAN' DEB O'ZINGIZNING, DOKTORNING VA BOSHQALARNING "
        "VAQTINI O'G'IRLAMANG!",
        reply_markup=manzil_keyboard)

async def manzilni_korsat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏥 SOSH MEDICAL klinikasi\n\n"
        "📍 Manzil: Yunusobod tumani, 13-mavze, Yangishahar ko'chasi 64a uy\n\n"
        "🗺 LOKATSIYA:\n"
        "https://yandex.com/navi/?whatshere%5Bzoom%5D=18&whatshere%5Bpoint%5D=69.296029%2C41.364923&lang=uz&from=navi")

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
        "Obuna bo'lish uchun quyidagi karta raqamiga to'lov qiling:")
    await update.message.reply_text(
        "💳 To'lov ma'lumotlari\n\n"
        "💰 Narxi: " + NARX + " / oy\n\n"
        "Karta raqami:\n" + KARTA_RAQAM + "\n"
        "Karta egasi: " + KARTA_EGASI + "\n\n"
        "To'lovni amalga oshirgach, to'lov chekining rasmini shu chatga yuboring.\n"
        "Admin 5-10 daqiqa ichida guruh linkini yuboradi.",
        reply_markup=tolov_keyboard)
    context.user_data["holat"] = "tolov_kutish"

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

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data = query.data
    try:
        if data.startswith("t:"):
            user_id = int(data.split(":")[1])
            # Ism olish
            try:
                chat = await context.bot.get_chat(user_id)
                full_name = chat.full_name or "Noma'lum"
                username = chat.username
            except Exception:
                full_name = "Noma'lum"; username = None
            # DB ga yozish
            end_date = add_subscriber(user_id, username, full_name)
            # Guruh linki olish
            try:
                invite = await context.bot.create_chat_invite_link(
                    chat_id=GURUH_ID, member_limit=1, name=str(full_name)[:30])
                link = invite.invite_link
            except Exception as e:
                logging.warning("Invite link error: " + str(e))
                link = GURUH_LINK
            # Foydalanuvchiga xabar yuborish
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
            # Adminning xabarini yangilash
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
            await context.bot.send_message(
                chat_id=ADMIN_ID, text="🔴 Xatolik yuz berdi:\n" + str(e))
        except Exception:
            pass

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

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
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
    elif text in ("⬅️ Ortga", "Ortga"): await start(update, context)
    else: await update.message.reply_text("Kerakli bo'limni tanlang.", reply_markup=main_keyboard)

def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("xizmatlar", xizmatlar))
    app.add_handler(CommandHandler("boglanish", boglanish))
    app.add_handler(CommandHandler("savollar", savollar))
    app.add_handler(CommandHandler("qabul", qabul))
    app.add_handler(CommandHandler("guruh_id", guruh_id_cmd))
    app.add_handler(CommandHandler("tasdiqlash", tasdiqlash))
    app.add_handler(CommandHandler("rad", rad_etish))
    app.add_handler(CommandHandler("azolar", azolar))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_payment_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.job_queue.run_daily(check_expired_subscriptions, time=datetime.time(hour=9, minute=0))
    app.job_queue.run_daily(warn_expiring_subscriptions, time=datetime.time(hour=9, minute=5))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
