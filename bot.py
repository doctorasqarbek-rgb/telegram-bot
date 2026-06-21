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
        ["Xavotir", "Vahima xuruji"], ["Tushkunlik", "Yopishqoq xayollar"],
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
        "Assalomu alaykum.\n\nMen Doktor Ergashevning rasmiy ma'lumot beruvchi botiman.\nKerakli bo'limni tanlang:",
        reply_markup=main_keyboard)

async def xizmatlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Kerakli xizmatni tanlang:", reply_markup=xizmat_keyboard)

async def individual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Individual psixologik suhbat\n\nJonli formatda individual suhbat. Holat tahlil qilinadi, muammo sabablari aniqlanadi, tavsiyalar beriladi, zarur bo'lsa dorilar yozib beriladi.\n\nDavomiyligi: 30-60 daqiqa\nFormat: Jonli qabul\nNarxi: 600 ming so'm",
        reply_markup=muammo_keyboard())

async def onlayn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Onlayn individual konsultatsiya\n\nMasofadan turib suhbat. Telegram orqali olib boriladi, zarur bo'lsa dorilar yozib beriladi.\n\nDavomiyligi: 30-60 daqiqa\nFormat: Onlayn\nNarxi: 500 ming so'm",
        reply_markup=muammo_keyboard())

async def kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "10 kunlik onlayn davolash kursi\n\nNevroz, xavotir va depressiya bilan ishlash uchun bosqichma-bosqich kurs.\n\nKurs ichida:\n- Har kungi yangi mavzular\n- Dorilar yozib berish\n- Amaliy mashqlar\n\nDavomiyligi: 10 kun\nFormat: Onlayn\nNarxi: 1 mln so'm",
        reply_markup=muammo_keyboard())

async def videolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Nevroz bo'yicha darslik videolari\n\nNevroz, xavotir va tushkunlikni tushunishga yordam beruvchi videolar.\n\nNimalarni o'rganasiz:\n- Nevroz va depressiya nima ekanini\n- Belgilarini va rivojlanishini\n- Undan qutulish yo'llarini\n\nFormat: Video darslar\nNarxi: 480 ming so'm",
        reply_markup=muammo_keyboard())

async def muammolar_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Muammoyingizni tanlang:", reply_markup=muammolar_keyboard())

async def xavotir_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xavotir\n\nIchki bezovtalik, nimadandir yomon narsa kutish va ortiqcha o'ylash bilan kechadigan holat.\n\nBelgilari: ichki siqilish, tinchlana olmaslik, yurak tez urishi, bezovtalik, xayollarning to'xtamasligi.\n\nNevroz kasalligida kuzatiladi, suhbat va dorilar yordamida davolanadi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def vahima_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Vahima xuruji\n\nTo'satdan kuchli qo'rquv, yurak urishi, nafas qisishi.\n\nBelgilari: yurak tez urishi, nafas qisishi, titroq, kuchli qo'rquv.\n\nNevroz kasalligida kuzatiladi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def tushkunlik_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tushkunlik\n\nKayfiyat pasayishi, hayotga qiziqish kamayishi va ichki bo'shliq hissi.\n\nBelgilari: kayfiyat pasayishi, qiziqish yo'qolishi, charchoq, umidsizlik.\n\nDepressiyada kuzatiladi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def yopishqoq_xayollar_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Yopishqoq xayollar\n\nOngga qayta-qayta kelaveradigan, bezovta qiladigan fikrlar.\n\nBelgilari: bir xil fikrlarning takrorlanishi, bezovtalik, ichki zo'riqish.\n\nObsessiv Kompulsiv Nevrozda kuzatiladi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def uyqu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Uyqu muammolari\n\nUxlab qolish qiyinligi, tez uyg'onish.\n\nBelgilari: uxlash qiyin bo'lishi, sal narsaga uyg'onib ketish, kunduzi uyquchanlik.\n\nBunga stress, xavotir va ruhiy zo'riqish sabab bo'lishi mumkin.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def yurak_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Yurak tez urib ketishi\n\nKo'pincha xavotir, vahima yoki ichki zo'riqish bilan bog'liq.\n\nBelgilari: yurakning kuchli urishi, ichki qo'rquv, bezovtalik, pulsni tez-tez o'lchash.\n\nNevroz kasalligida kuzatiladi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def nafas_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Nafas qisishi\n\nXavotir, vahima yoki ichki zo'riqish fonida paydo bo'ladi.\n\nBelgilari: to'liq nafas ololmaslik, ko'krakda siqilish, qo'rquv.\n\nNevroz kasalligida kuzatiladi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def tomoqqa_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tomoqqa tiqilish hissi\n\nKo'pincha xavotir va ichki zo'riqish bilan bog'liq.\n\nBelgilari: yutinish qiyin bo'lgandek tuyulishi, tomoqda nimadir bordek hissiyot.\n\nOrganik sabablar bo'lmasa psixosomatik.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def bosh_ogriq_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bosh og'rig'i\n\nStress, xavotir va ruhiy zo'riqish bilan kuchayishi mumkin.\n\nBelgilari: boshda bosim hissi, peshona yoki ensa ogrigi, stress bilan kuchayishi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def bosh_aylanish_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bosh aylanishi\n\nXavotir, qo'rquv va ichki zo'riqish bilan birga kuzatiladi.\n\nBelgilari: bosh aylangandek bo'lishi, muvozanat buzilgandek tuyulishi.\n\nOrganik sabablar bo'lmasa psixosomatik.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def ich_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ich kelishidagi muammolar\n\nStress, xavotir va ruhiy zo'riqish bilan bog'liq bo'lishi mumkin.\n\nBelgilari: ich qotishi yoki ich ketishi, qorin dam bo'lishi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def peshob_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Peshob qilish hissi\n\nXavotir va ichki zo'riqish bilan kuchayadi.\n\nBelgilari: tez-tez hojatga borish hissi, bezovtalik bilan kuchayishi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def qaltirash_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tanadagi qaltirashlar\n\nXavotir, vahima va kuchli ichki zo'riqish paytida kuzatiladi.\n\nBelgilari: qo'l-oyoqlarda titroq, ichki qaltirash.\n\nKo'pincha Nevrozda kuchayadi.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def vazn_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ozib ketish yoki semirish\n\nRuhiy holat, stress, xavotir yoki tushkunlik bilan bog'liq.\n\nBelgilari: ishtahaning kamayishi yoki oshishi, tez ozish, ortiqcha ovqat yeyish.\n\nEslatma: Tibbiy tekshiruvlarda hech narsa aniqlanmasligi kerak!",
        reply_markup=muammo_keyboard())

async def boglanish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bog'lanish ma'lumotlari\n\nTelefon:\n+998 88 306 06 95\n\nInstagram:\nhttps://www.instagram.com/doktor.ergashev?igsh=MXc5eTN2NjF1NGZqaw==\n\nYouTube:\nhttps://youtube.com/@doktor_ergashev?si=s939zn1cW_N7BLu-")

async def savollar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ko'p beriladigan savollar\n\n"
        "1. Psixoterapiya nima?\nRuhiy muammolarni suhbat orqali davolash usuli.\n\n"
        "2. Bir marta kelish yetarlimi?\nAyrim insonlarda yetarli, lekin ko'pchilikda bir necha seans samaraliroq.\n\n"
        "3. Dorilar majburiymi?\nYo'q, lekin ko'p hollarda (70-80%) yoziladi.\n\n"
        "4. Qancha vaqtda natija bo'ladi?\nBa'zida 1 oy, odatda 2-3 oyda natija bo'ladi.\n\n"
        "5. Onlayn davolanish samaralimi?\nHa, to'g'ri olib borilsa juda yaxshi natija beradi.\n\n"
        "6. Bu sehr yoki jin tegish kasalligi emasmi?\nYo'q! Bu tibbiy-psixologik holat.\n\n"
        "7. Butunlay sog'ayish mumkinmi?\nHa, ko'p hollarda (70%) to'liq sog'ayadi.\n\n"
        "8. O'lib qolish yoki jinni bo'lib qolish mumkinmi?\nYo'q, bu holat hayot uchun xavfli emas.\n\n"
        "9. Bu shizofreniya emasmi?\nYo'q. Shizofreniya boshqa kasallik.\n\n"
        "10. Doktor Ergashev kim?\nToshkent Tibbiyot Akademiyasi magistr bitiruvchisi. 2023-yildan beri 3000+ bemor bilan ishlaydi.")

async def qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["holat"] = "ism"
    await update.message.reply_text("Qabulga yozilish\n\nIltimos, ism va familiyangizni yozing.")

async def manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([["ALBATTA BORAMAN"], ["⬅️ Ortga"]], resize_keyboard=True)
    await update.message.reply_text("DIQQAT!\n\nQABULGA YOZILIB KELISHINGIZ SHART!\nYOZILMASDA KELSANGIZ, QABULGA KIRMASDAN KETISHINGIZ MUMKIN.", reply_markup=kb)

async def manzilni_korsat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "SOSH MEDICAL klinikasi\n\nManzil: Yunusobod tumani, 13-mavze, Yangishahar ko'chasi 64a uy\n\nLOKATSIYA:\nhttps://yandex.com/navi/?whatshere%5Bzoom%5D=18&whatshere%5Bpoint%5D=69.296029%2C41.364923&lang=uz&from=navi")

async def guruhga_kirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sub = get_subscriber(user.id)
    if sub and sub[5] == 1:
        await update.message.reply_text(
            "Siz allaqachon faol a'zo siz!\n\nObuna tugash sanasi: " + str(sub[4]) + "\n\nGuruh linki:\n" + GURUH_LINK,
            reply_markup=main_keyboard)
        return
    await update.message.reply_text(
        "Yopiq guruh haqida\n\n"
        "Bu guruhda inson ruhiyati, ruhiy buzilish va kasalliklar haqidagi "
        "qimmatli ma'lumotlarni atigi 100 ming so'm evaziga oylik obuna bo'lish orqali o'rganib borasiz.\n\n"
        "Obuna bo'lish uchun quyidagi karta raqamiga to'lov qiling:")
    await update.message.reply_text(
        "To'lov ma'lumotlari\n\nNarxi: " + NARX + " / oy\n\nKarta raqami:\n" + KARTA_RAQAM +
        "\nKarta egasi: " + KARTA_EGASI + "\n\nTo'lovni amalga oshirgach, to'lov chekining rasmini shu chatga yuboring.\nAdmin 5-10 daqiqa ichida guruh linkini yuboradi.",
        reply_markup=tolov_keyboard)
    context.user_data["holat"] = "tolov_kutish"

async def handle_payment_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    holat = context.user_data.get("holat")
    if holat not in ("tolov_kutish", None, "tolov_yuborildi"):
        return
    user = update.effective_user
    uname = "@" + user.username if user.username else "yo'q"
    caption = "Yangi to'lov so'rovi!\n\nIsm: " + str(user.full_name) + "\nID: " + str(user.id) + "\nUsername: " + uname
    inline_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="t:" + str(user.id) + ":" + str(user.full_name)),
        InlineKeyboardButton("❌ Rad etish", callback_data="r:" + str(user.id))
    ]])
    if update.message.photo:
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=inline_kb)
    elif update.message.document:
        await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=caption, reply_markup=inline_kb)
    context.user_data["holat"] = "tolov_yuborildi"
    await update.message.reply_text("To'lov chekingiz adminga yuborildi.\n5-10 daqiqa ichida guruh linki yuboriladi. Sabr biling!", reply_markup=main_keyboard)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data = query.data
    if data.startswith("t:"):
        parts = data.split(":", 2)
        user_id = int(parts[1])
        full_name = parts[2] if len(parts) > 2 else "Noma'lum"
        sub = get_subscriber(user_id)
        username = sub[1] if sub else None
        end_date = add_subscriber(user_id, username, full_name)
        try:
            invite = await context.bot.create_chat_invite_link(chat_id=GURUH_ID, member_limit=1, name=str(full_name)[:30])
            link = invite.invite_link
        except Exception:
            link = GURUH_LINK
        try:
            await context.bot.send_message(chat_id=user_id, text=
                "To'lovingiz tasdiqlandi!\n\nTabriklaymiz!\n\nObuna muddati: 1 oy (" + str(end_date) + " gacha)\n\n"
                "Guruh linki (faqat siz uchun, 1 martalik):\n" + link + "\n\nMuddat tugagach, qayta to'lov qiling.")
            await query.edit_message_caption(caption="Tasdiqlandi: " + str(full_name) + "\n" + str(end_date) + " gacha")
        except Exception as e:
            await query.edit_message_caption(caption="Xatolik: " + str(e))
    elif data.startswith("r:"):
        user_id = int(data.split(":")[1])
        try:
            await context.bot.send_message(chat_id=user_id, text="Kechirasiz, to'lovingiz tasdiqlanmadi.\nQayta to'lov qilib chek yuboring.")
            await query.edit_message_caption(caption="Rad etildi (ID: " + str(user_id) + ")")
        except Exception as e:
            await query.edit_message_caption(caption="Xatolik: " + str(e))

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
            "To'lovingiz tasdiqlandi!\n\nTabriklaymiz!\n\nObuna muddati: 1 oy (" + str(end_date) + " gacha)\n\n"
            "Guruh linki (faqat siz uchun, 1 martalik):\n" + link + "\n\nMuddat tugagach, qayta to'lov qiling.")
        await update.message.reply_text(str(full_name) + " tasdiqlandi. Guruh linki yuborildi.")
    except Exception as e:
        await update.message.reply_text("Xatolik: " + str(e))

async def rad_etish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Foydalanish: /rad <user_id>"); return
    try: user_id = int(context.args[0])
    except: await update.message.reply_text("Noto'g'ri user_id"); return
    try:
        await context.bot.send_message(chat_id=user_id, text="Kechirasiz, to'lovingiz tasdiqlanmadi.\nQayta to'lov qilib chek yuboring.")
        await update.message.reply_text("User " + str(user_id) + " rad etildi.")
    except Exception as e:
        await update.message.reply_text("Xatolik: " + str(e))

async def azolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    rows = get_all_active()
    if not rows:
        await update.message.reply_text("Hozircha faol a'zolar yo'q."); return
    text = "Faol obunachlar: " + str(len(rows)) + " ta\n\n"
    for row in rows:
        uid, uname, fname, sd, ed, act = row
        text += fname + "\nID: " + str(uid)
        if uname: text += " | @" + uname
        text += "\n" + str(sd) + " - " + str(ed) + "\n\n"
    await update.message.reply_text(text)

async def guruh_id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("Guruh ID: " + str(update.effective_chat.id))

async def warn_expiring_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    for row in get_expiring_soon(days=7):
        uid, uname, fname, sd, ed, act = row
        try:
            await context.bot.send_message(chat_id=uid, text=
                "Obuna muddatingiz tugashiga 7 kun qoldi!\n\nMuddat: " + str(ed) + "\n\n"
                "Guruhda qolish uchun qayta to'lov qiling:\n\nKarta: " + KARTA_RAQAM +
                "\nEgasi: " + KARTA_EGASI + "\nNarxi: " + NARX +
                "\n\nTo'lovdan so'ng chekni botga yuboring - admin tasdiqlaydi va obunangiz uzaytiriladi.")
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
                "Obuna muddatingiz tugadi!\n\nGuruhdan chiqarildingiz.\n\nQayta obuna bo'lish uchun:\n/start - Yopiq guruhga kirish")
        except Exception as e:
            logging.error("Notify error: " + str(e))
        deactivate(uid)
        await context.bot.send_message(chat_id=ADMIN_ID, text="Obuna tugadi: " + str(fname) + " (ID: " + str(uid) + ") guruhdan chiqarildi.")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if context.user_data.get("holat") == "ism":
        context.user_data["ism"] = text; context.user_data["holat"] = "telefon"
        await update.message.reply_text("Telefon raqamingizni yozing:"); return
    if context.user_data.get("holat") == "telefon":
        context.user_data["telefon"] = text; context.user_data["holat"] = "muammo"
        await update.message.reply_text("Muammoingizni yozing:"); return
    if context.user_data.get("holat") == "muammo":
        ism = context.user_data.get("ism"); telefon = context.user_data.get("telefon")
        context.user_data["holat"] = None
        await update.message.reply_text("So'rovingiz qabul qilindi, tez orada bog'lanamiz!", reply_markup=main_keyboard)
        await context.bot.send_message(chat_id=ADMIN_ID, text="Yangi qabul:\nIsm: "+str(ism)+"\nTelefon: "+str(telefon)+"\nMuammo: "+str(text))
        return
    if text == "Xizmatlar": await xizmatlar(update, context)
    elif text == "Muammoyingiz nimada": await muammolar_fn(update, context)
    elif text == "Bog'lanish": await boglanish(update, context)
    elif text == "Ko'p beriladigan savollar": await savollar(update, context)
    elif text in ("Qabulga yozilish", "🟢 Qabulga yozilish"): await qabul(update, context)
    elif text == "💳 Yopiq guruhga kirish": await guruhga_kirish(update, context)
    elif text == "✅ To'lovni tasdiqlayman":
        if context.user_data.get("holat") == "tolov_kutish":
            await update.message.reply_text("To'lov chekining rasmini yuboring.")
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
