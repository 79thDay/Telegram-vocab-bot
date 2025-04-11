import logging
import sqlite3
import random
import threading
import time
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

TOKEN = "8196646866:AAGeaxWS2zWhG7953FTw-mjhnQgbzk7T7D4"
DB_PATH = "/storage/emulated/0/Download/mybot/5110words.db"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("لغت روز", callback_data='word')],
        [InlineKeyboardButton("لغت بعدی", callback_data='next_word')],
        [InlineKeyboardButton("ترجمه", callback_data='translate')],
        [InlineKeyboardButton("۱۳ لغت تصادفی", callback_data='13words')],
        [InlineKeyboardButton("شروع دوباره", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("به ربات آموزش زبان خوش آمدید!", reply_markup=reply_markup)

def get_random_word():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM words WHERE used=0 ORDER BY RANDOM() LIMIT 1")
    word = cursor.fetchone()
    if word:
        cursor.execute("UPDATE words SET used=1 WHERE id=?", (word[0],))
        conn.commit()
    conn.close()
    return word

def word_handler(update: Update, context: CallbackContext):
    word = get_random_word()
    if word:
        msg = f"**{word[1]}** ({word[3]}, {word[4]})\nمعنی: {word[2]}\nمثال: {word[5]}"
        update.message.reply_text(msg, parse_mode='Markdown')
    else:
        update.message.reply_text("همه لغات استفاده شده‌اند.")

def next_word_handler(update: Update, context: CallbackContext):
    word_handler(update, context)

def translate_handler(update: Update, context: CallbackContext):
    if context.args:
        text = " ".join(context.args)
        lang = "en" if all('\u0600' <= c <= '\u06FF' for c in text) else "fa"
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={'en' if lang=='fa' else 'fa'}&dt=t&q={text}"
        res = requests.get(url)
        try:
            translated = res.json()[0][0][0]
            update.message.reply_text(f"ترجمه: {translated}")
        except:
            update.message.reply_text("ترجمه پیدا نشد.")
    else:
        update.message.reply_text("لطفاً متنی برای ترجمه وارد کنید.")

def words_13_handler(update: Update, context: CallbackContext):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM words ORDER BY RANDOM() LIMIT 13")
    words = cursor.fetchall()
    conn.close()

    msg = ""
    for i, word in enumerate(words, 1):
        msg += f"{i}. **{word[1]}** ({word[3]}, {word[4]})\nمعنی: {word[2]}\nمثال: {word[5]}\n\n"
    update.message.reply_text(msg, parse_mode='Markdown')

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    command = query.data
    fake_update = Update(update.update_id, message=query.message)
    if command == "word":
        word_handler(fake_update, context)
    elif command == "next_word":
        next_word_handler(fake_update, context)
    elif command == "translate":
        query.edit_message_text("لطفاً از دستور /translate استفاده کنید.")
    elif command == "13words":
        words_13_handler(fake_update, context)
    elif command == "start":
        start(fake_update, context)

def daily_sender(context: CallbackContext):
    chat_id = context.job.context
    word = get_random_word()
    if word:
        msg = f"**{word[1]}** ({word[3]}, {word[4]})\nمعنی: {word[2]}\nمثال: {word[5]}"
        context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

def schedule_daily(bot):
    def job():
        while True:
            time.sleep(86400)
            # در صورت نیاز می‌تونید آیدی خودتون یا گروه رو اینجا بذارید:
            bot.send_message(chat_id="YOUR_CHAT_ID", text="در اینجا می‌توانید لغت روز را بفرستید.")

    threading.Thread(target=job, daemon=True).start()

def main():
    updater = Updater(TOKEN, use_context=True)
    bot = updater.bot

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("word", word_handler))
    updater.dispatcher.add_handler(CommandHandler("next_word", next_word_handler))
    updater.dispatcher.add_handler(CommandHandler("translate", translate_handler))
    updater.dispatcher.add_handler(CommandHandler("13words", words_13_handler))
    updater.dispatcher.add_handler(CallbackQueryHandler(button_handler))

    bot.set_my_commands([
        BotCommand("start", "شروع"),
        BotCommand("word", "لغت روز"),
        BotCommand("next_word", "لغت بعدی"),
        BotCommand("translate", "ترجمه"),
        BotCommand("13words", "۱۳ لغت تصادفی")
    ])

    schedule_daily(bot)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
