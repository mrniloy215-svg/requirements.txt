# প্রয়োজনীয় লাইব্রেরি: pytelegrambotapi, openpyxl
# pip install pyTelegramBotAPI openpyxl

import telebot
from telebot import types
import json
import os
from datetime import datetime
from openpyxl import Workbook
import tempfile

# ================== CONFIG ==================
TOKEN = '8390865878:AAEIH_oVbfYTRpzZCvH5EZMZqR6PTyeiqSU' 
ADMIN_CHAT_ID = 6807305596
BKASH_NUMBER = '01902557331'
NAGAD_NUMBER = '01795994245'
DATA_FILE = 'data.json'
COST_PER_GMAIL = 12
# ============================================

bot = telebot.TeleBot(TOKEN)

# লোড / সেভ ডাটা
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "user_balance": {},
            "gmail_store": [],
            "orders": []
        }
        save_data(data)
        return data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ছোট হেলপার
def main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('রিচার্জ', 'Order 📑')
    markup.row('ব্যালেন্স', 'সাহায্য')
    markup.row('Language 🌐')
    return markup

# ========== /start ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    welcome = """Bot Online🟢
👋 আপনাকে স্বাগতম। 🌹♥️ 
অনুগ্রহ করে নিচের সিস্টেমগুলো অনুসরণ করুন, 
আপনার পছন্দমত যতখুশি Gmail অর্ডার করুন, 
উপভোগ করুন আমাদের সেরা সার্ভিস। 
ধন্যবাদ 💝"""
    bot.send_message(chat_id, welcome, reply_markup=main_menu(chat_id))

# ========== ADD GMAIL ==========
@bot.message_handler(commands=['addgmail'])
def addgmail_cmd(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ এই কমান্ড শুধুমাত্র অ্যাডমিনের জন্য।")
        return
    payload = message.text[len('/addgmail'):].strip()
    if payload:
        process_addgmail_text(message.chat.id, payload)
    else:
        msg = bot.reply_to(message, "📥 Gmail+Password লাইনবাইলে পেস্ট করো (email|password)\nপেস্টের পর Send করো।")
        bot.register_next_step_handler(msg, admin_paste_gmails)

def admin_paste_gmails(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    text = message.text or ""
    process_addgmail_text(message.chat.id, text)

def process_addgmail_text(chat_id, text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    added = 0
    bad_lines = []
    for ln in lines:
        if '|' in ln:
            parts = ln.split('|', 1)
        else:
            parts = ln.split()
        if len(parts) >= 2:
            email = parts[0].strip()
            pwd = parts[1].strip()
            data['gmail_store'].append(f"{email}|{pwd}")
            added += 1
        else:
            bad_lines.append(ln)
    save_data(data)
    resp = f"✅ {added} টি Gmail সফলভাবে যোগ করা হয়েছে।"
    if bad_lines:
        resp += "\n❗ নিম্ন লাইনগুলো পড়া যায়নি:\n" + "\n".join(bad_lines)
    bot.send_message(chat_id, resp)

# ========== ORDER ==========
@bot.message_handler(func=lambda m: m.text in ['Order 📑', 'Order'])
def order_start(message):
    chat_id = message.chat.id
    stock = len(data['gmail_store'])
    if stock == 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add('Notify', 'Main Menu')
        bot.send_message(chat_id, "⚠️ স্টকে কোনো Gmail নেই। পরে চেষ্টা করুন।", reply_markup=markup)
        return
    max_buy = min(10, stock)
    markup = types.ReplyKeyboardMarkup(row_width=5, resize_keyboard=True, one_time_keyboard=True)
    markup.add(*[types.KeyboardButton(str(i)) for i in range(1, max_buy+1)])
    bot.send_message(chat_id, f"🎯 কতটি Gmail নিতে চান? (১ - {max_buy})", reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, order_process)

def order_process(message):
    chat_id = message.chat.id
    try:
        count = int(message.text)
    except:
        bot.send_message(chat_id, "❌ সঠিক সংখ্যা লিখুন।", reply_markup=main_menu(chat_id))
        return
    stock = len(data['gmail_store'])
    if count < 1 or count > min(10, stock):
        bot.send_message(chat_id, f"❌ সংখ্যা ১ - {min(10,stock)} এর মধ্যে দিন।", reply_markup=main_menu(chat_id))
        return
    cost = count * COST_PER_GMAIL
    user_bal = data['user_balance'].get(str(chat_id), 0)
    if user_bal < cost:
        bot.send_message(chat_id, f"⚠️ আপনার ব্যালেন্স {user_bal} টাকা, প্রয়োজন {cost} টাকা। আগে রিচার্জ করুন।", reply_markup=main_menu(chat_id))
        return

    data['user_balance'][str(chat_id)] = user_bal - cost
    gmails_to_send = data['gmail_store'][:count]
    data['gmail_store'] = data['gmail_store'][count:]

    order = {
        "uid": chat_id,
        "count": count,
        "amount": cost,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "gmails": gmails_to_send
    }
    data['orders'].append(order)
    save_data(data)

    try:
        file_path = create_xlsx_for_order(chat_id, gmails_to_send)
        with open(file_path, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"✅ আপনার {count} টি Gmail (Order) — মোট {cost} টাকা।", reply_markup=main_menu(chat_id))
        os.remove(file_path)
    except Exception as e:
        data['user_balance'][str(chat_id)] += cost
        save_data(data)
        bot.send_message(chat_id, "❌ ফাইল তৈরি/পাঠানোতে সমস্যা হয়েছে। টাকা ফেরত দেওয়া হয়েছে।", reply_markup=main_menu(chat_id))
        bot.send_message(ADMIN_CHAT_ID, f"Error creating/sending xlsx for UID {chat_id}: {e}")
        return

    bot.send_message(ADMIN_CHAT_ID, f"🛒 New Order:\nUID: {chat_id}\nCount: {count}\nAmount: {cost}\nTime(UTC): {order['timestamp']}")

def create_xlsx_for_order(uid, gmails):
    wb = Workbook()
    ws = wb.active
    ws.title = "Gmails"
    ws.append(["Gmail", "Password"])
    for entry in gmails:
        if '|' in entry:
            email, pwd = entry.split('|', 1)
        else:
            parts = entry.split()
            email = parts[0]
            pwd = parts[1] if len(parts) > 1 else ""
        ws.append([email, pwd])
    tmp = os.path.join(tempfile.gettempdir(), f"Order-{uid}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.xlsx")
    wb.save(tmp)
    return tmp

# ========== Recharge ==========
recharge_sessions = {}

@bot.message_handler(func=lambda m: m.text in ['রিচার্জ', 'Recharge'])
def recharge_start(message):
    chat_id = message.chat.id
    text = f"💸 রিচার্জ করতে পাঠান:\nবিকাশ: {BKASH_NUMBER}\nনগদ: {NAGAD_NUMBER}\n\nTransaction ID পাঠান:"
    bot.send_message(chat_id, text, reply_markup=types.ReplyKeyboardRemove())
    recharge_sessions[chat_id] = {'step': 1, 'data': {}}

@bot.message_handler(func=lambda m: m.chat.id in recharge_sessions)
def recharge_process(message):
    chat_id = message.chat.id
    session = recharge_sessions.get(chat_id)
    if not session:
        return
    step = session['step']
    text = (message.text or "").strip()

    if step == 1:
        session['data']['transaction_id'] = text
        session['step'] = 2
        bot.send_message(chat_id, "💰 এমাউন্ট দিন:")

    elif step == 2:
        if not text.isdigit():
            bot.send_message(chat_id, "❌ শুধুমাত্র সংখ্যা দিন।")
            return
        session['data']['amount'] = int(text)
        session['step'] = 3
        bot.send_message(chat_id, "🆔 আপনার টেলিগ্রাম ইউআইডি পাঠান (@userinfobot থেকে):")

    elif step == 3:
        if not text.isdigit():
            bot.send_message(chat_id, "❌ ভুল UID, শুধু সংখ্যা দিন:")
            return
        session['data']['telegram_uid'] = int(text)
        session['step'] = 4
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Done ✅")
        bot.send_message(chat_id, "✅ সব তথ্য পেয়েছি। Done ✅ ক্লিক করুন।", reply_markup=markup)

    elif step == 4:
        if text.lower() in ['done ✅', 'done']:
            d = session['data']
            username = message.from_user.username or "NotSet"
            bot.send_message(
                ADMIN_CHAT_ID,
                f"💳 নতুন রিচার্জ অনুরোধ:\n"
                f"👤 Username: @{username}\n"
                f"🆔 Telegram ID: {d['telegram_uid']}\n"
                f"🔖 Transaction ID: {d['transaction_id']}\n"
                f"💰 Amount: {d['amount']} টাকা\n\n"
                f"/approve {d['telegram_uid']} {d['amount']}\n"
                f"/cancel {d['telegram_uid']}"
            )
            bot.send_message(chat_id, "⏳ তথ্য এডমিনের কাছে পাঠানো হয়েছে।", reply_markup=main_menu(chat_id))
            recharge_sessions.pop(chat_id, None)
        else:
            bot.send_message(chat_id, "❌ Done ✅ বাটনে ক্লিক করুন।")

# ========== Approve/Cancel ==========
@bot.message_handler(commands=['approve'])
def approve(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    try:
        _, uid_s, amount_s = message.text.split()
        uid = int(uid_s)
        amount = int(amount_s)
        data['user_balance'][str(uid)] = data['user_balance'].get(str(uid), 0) + amount
        save_data(data)
        bot.send_message(uid, f"✅ আপনার {amount} টাকা রিচার্জ এপ্রুভ হয়েছে।")
        bot.send_message(ADMIN_CHAT_ID, f"✅ রিচার্জ এপ্রুভ করা হয়েছে (UID: {uid})")
    except:
        bot.send_message(message.chat.id, "❌ কমান্ড ভুল! উদাহরণ:\n/approve 123456789 50")

@bot.message_handler(commands=['cancel'])
def cancel(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    try:
        _, uid_s = message.text.split()
        uid = int(uid_s)
        bot.send_message(uid, "❌ আপনার রিচার্জ বাতিল হয়েছে।")
        bot.send_message(ADMIN_CHAT_ID, f"❌ UID {uid}-এর রিচার্জ বাতিল হয়েছে।")
    except:
        bot.send_message(message.chat.id, "❌ কমান্ড ভুল! উদাহরণ:\n/cancel 123456789")

# ========== Balance & Help ==========
@bot.message_handler(func=lambda m: m.text in ['ব্যালেন্স','Balance'])
def balance(message):
    chat_id = message.chat.id
    bal = data['user_balance'].get(str(chat_id), 0)
    bot.send_message(chat_id, f"💰 আপনার ব্যালেন্স: {bal} টাকা।", reply_markup=main_menu(chat_id))

@bot.message_handler(func=lambda m: m.text in ['সাহায্য','Help'])
def help_msg(message):
    bot.send_message(
        message.chat.id,
        "🛠 কমান্ড:\n"
        "রিচার্জ - ব্যালেন্স রিচার্জ\n"
        "Order 📑 - Gmail অর্ডার\n"
        "ব্যালেন্স - বর্তমান ব্যালেন্স দেখুন\n"
        "অ্যাডমিন যোগাযোগ: @mrniloy1122",
        reply_markup=main_menu(message.chat.id)
    )

# ========== Notify ==========
@bot.message_handler(func=lambda m: m.text == 'Notify')
def notify_request(message):
    chat_id = message.chat.id
    bot.send_message(ADMIN_CHAT_ID, f"🔔 User {chat_id} wants to be notified.")
    bot.send_message(chat_id, "✅ অনুরোধ গ্রহণ হয়েছে। স্টক এলে জানানো হবে।", reply_markup=main_menu(chat_id))

# ========== /listgmail & /removegmail ==========
@bot.message_handler(commands=['listgmail'])
def listgmail(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ শুধুমাত্র অ্যাডমিনের জন্য।")
        return
    lines = data['gmail_store']
    if not lines:
        bot.reply_to(message, "স্টকে কোনো Gmail নেই।")
        return
    preview = "\n".join(lines[:50])
    bot.reply_to(message, f"স্টকের প্রথম {min(len(lines),50)} টি:\n{preview}")

@bot.message_handler(commands=['removegmail'])
def removegmail(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ শুধুমাত্র অ্যাডমিনের জন্য।")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "ব্যবহার: /removegmail email@gmail.com")
        return
    target = parts[1].strip()
    before = len(data['gmail_store'])
    data['gmail_store'] = [e for e in data['gmail_store'] if not e.startswith(target + "|")]
    save_data(data)
    bot.reply_to(message, f"✅ মুছে ফেলা হয়েছে: {before - len(data['gmail_store'])} টি এন্ট্রি।")

# ========== Run Bot ==========
if __name__ == '__main__':
    print("🤖 Bot is running...")
    bot.infinity_polling()