import logging
import sqlite3
import random
import datetime
import threading
import time
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# توکن ربات
TOKEN = '8196646866:AAGeaxWS2zWhG7953FTw-mjhnQgbzk7T7D4'

# مسیر دیتابیس
DB_PATH = '/storage/emulated/0/Download/mybot/5110words.db'

# لیست chat_id ها برای ارسال روزانه
subscribed_users = set()

# تنظیم لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# اتصال به دیتابیس
def get_word(used_only=False, unused_only=False, limit=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT english, persian, type, category, example FROM words"
    conditions = []
    if used_only:
        conditions.append("used = 1")
    elif unused_only:
        conditions.append("used = 0")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY RANDOM() LIMIT {limit}"
    cursor.execute(query)
    results = cursor.fetchall()

    if unused_only and results:
        for word in results:
            cursor.execute("UPDATE words SET used = 1 WHERE english = ?", (word[0],))
        conn.commit()

    conn.close()
    return results

def format_word(word):
    english, persian, type_, category, example = word
    return f"**{english}**\nمعنی: {persian}\nنوع: {type_}\nدسته: {category}\nمثال: {example}"

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    subscribed_users.add(chat_id)

    keyboard = [[InlineKeyboardButton("دریافت لغت", callback_data='get_word')],
                [InlineKeyboardButton("ترجمه", callback_data='translate')],
                [InlineKeyboardButton("۱۳ لغت", callback_data='get_13words')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(f"سلام {user.first_name}!\nبه ربات آموزش لغت خوش اومدی.", reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == 'get_word':
        send_word(query.message.chat_id, context)
    elif query.data == 'translate':
        query.edit_message_text("لطفاً دستور /translate را همراه با یک لغت ارسال کنید.")
    elif query.data == 'get_13words':
        send_13_words(query.message.chat_id, context)

def send_word(chat_id, context: CallbackContext):
    words = get_word(unused_only=True)
    if words:
        text = format_word(words[0])
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    else:
        context.bot.send_message(chat_id=chat_id, text="تمام لغات استفاده شده‌اند!")

def next_word(update: Update, context: CallbackContext):
    send_word(update.message.chat_id, context)

def send_13_words(chat_id, context: CallbackContext):
    words = get_word(unused_only=True, limit=13)
    if words:
        text = "\n\n".join([format_word(w) for w in words])
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    else:
        context.bot.send_message(chat_id=chat_id, text="لغتی یافت نشد!")

def word(update: Update, context: CallbackContext):
    send_word(update.message.chat_id, context)

def translate(update: Update, context: CallbackContext):
    if context.args:
        query = ' '.join(context.args)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=fa&dt=t&q={query}"
        try:
            response = requests.get(url)
            result = response.json()[0][0][0]
            update.message.reply_text(f"ترجمه: {result}")
        except:
            update.message.reply_text("خطا در ترجمه.")
    else:
        update.message.reply_text("لطفاً یک کلمه برای ترجمه بنویسید. مثال:\n/translate hello")

def send_daily_word(context: CallbackContext):
    words = get_word(unused_only=True)
    if not words:
        return
    word = format_word(words[0])
    for user_id in subscribed_users:
        context.bot.send_message(chat_id=user_id, text=f"لغت امروز:\n{word}", parse_mode="Markdown")

def daily_scheduler(context: CallbackContext):
    while True:
        now = datetime.datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now > target:
            target += datetime.timedelta(days=1)
        time.sleep((target - now).seconds)
        send_daily_word(context)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("word", word))
    dp.add_handler(CommandHandler("next_word", next_word))
    dp.add_handler(CommandHandler("13words", lambda update, context: send_13_words(update.message.chat_id, context)))
    dp.add_handler(CommandHandler("translate", translate))
    dp.add_handler(CallbackQueryHandler(button_handler))

    threading.Thread(target=daily_scheduler, args=(updater.bot,), daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
