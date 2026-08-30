# -*- coding: utf-8 -*-
import os
import logging
import threading
from flask import Flask
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 🌐 МИНИ-СЕРВЕР ДЛЯ ОБХОДА PORT SCAN TIMEOUT НА RENDER
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# Запускаем сервер мгновенно в фоновом потоке
threading.Thread(target=run_web, daemon=True).start()

# ==========================================
# 🔑 НАСТРОЙКИ И ЛОГИРОВАНИЕ
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-1003786532521")

# Инициализируем клиента ИИ Google Gemini
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ==========================================
# 🧠 ИНСТРУКЦИИ ДЛЯ ИИ-АГЕНТОВ
# ==========================================

PROMPT_SALES = """
Ты — вежливый ИИ-консультант телемастерской «Армавиртелеремонт» (г. Армавир, ул. Туапсинская, 503).
Твоя задача — отвечать на вопросы клиентов, выявлять симптомы поломки и ориентировать по стоимости ремонта.

--- БАЗА ЗНАНИЙ И ПРАЙС-ЛИСТ ---
- Мастер: Александр Парфилов (опыт работы более 25 лет).
- Адрес: г. Армавир, ул. Туапсинская, 503.
- Телефон / WhatsApp / MAX: +7 (929) 850-19-93.
- Сайт: https://armavirteleremont.github.io/remontledtv/

ЧАСТЫЕ ПОЛОМКИ, ПРИЧИНЫ И ЦЕНЫ:
1. Симптом: Звук есть, а изображения нет (экран темный, но при фонарике виден силуэт).
   Причина: Сгорела LED-подсветка матрицы.
   Ориентировочная стоимость:
   - 32" — от 2 500 до 5 000 руб.
   - 40"-43" — от 4 000 до 7 000 руб.
   - 49"-50" — от 6 000 до 9 000 руб.
   - 55"+ — от 9 000 руб.
2. Не включается: Проблема с блоком питания.
3. Зависает на логотипе: Сбой прошивки.

ПРАВИЛА ОБЩЕНИЯ:
- ЗАПРЕЩЕНО использовать слово «бесплатно».
- Будь вежливым, пиши коротко и по делу.
- Задавай уточняющие вопросы (марка/модель, диагональ).
- Указывай контакты: 📞 +7 (929) 850-19-93
"""

PROMPT_COPYWRITER = """
Ты — профессиональный SMM-копирайтер телемастерской «Армавиртелеремонт» (г. Армавир, ул. Туапсинская, 503).
Пиши короткие, вовлекающие и продающие посты для Telegram-канала.
В постах:
- Объясняй причины частых поломок (сгорела подсветка, сбой прошивки, проблемы с блоком питания).
- Используй эмодзи и красивую структуру.
- Указывай контакты:
  📍 **Адрес:** г. Армавир, ул. Туапсинская, 503
  📞 **Телефон / WhatsApp / MAX:** +7 (929) 850-19-93
  🌐 **Наш сайт:** https://armavirteleremont.github.io/remontledtv/
"""

# ==========================================
# ⚙️ ОБРАБОТЧИКИ СООБЩЕНИЙ СЕРВИСА
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует мастерская «Армавиртелеремонт».**\n\n"
        "Я ИИ-консультант мастера Александра Парфилова. "
        "Опишите, что случилось с вашим телевизором, и я подскажу возможную причину и ориентировочную цену!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"📩 Входящее сообщение: {user_text}")
    
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            await update.message.reply_text("❌ Ошибка: В Render не задана переменная GEMINI_API_KEY!")
            return

        client = genai.Client(api_key=api_key)
        
        # Используем обновленную модель gemini-3.6-flash
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=user_text,
            config={'system_instruction': PROMPT_SALES}
        )
        
        if response and response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Подскажите, пожалуйста, марку и диагональ вашего телевизора?")
            
    except Exception as e:
        logging.error(f"❌ Ошибка Gemini API: {e}", exc_info=True)
        await update.message.reply_text("Извините, произошел временный сбой. Пожалуйста, позвоните нам напрямую: +7 (929) 850-19-93.")

async def generate_and_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else "Замена подсветки телевизора"
    await update.message.reply_text(f"⏳ **Генерирую пост на тему:** «{topic}»...")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Напиши рекламный пост на тему: {topic}",
            config={'system_instruction': PROMPT_COPYWRITER}
        )
        post_text = response.text
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Написать мастеру / Узнать цену", url="https://t.me/parfiloffbot")]
        ])
        
        await context.bot.send_message(
            chat_id=int(CHANNEL_ID), 
            text=post_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await update.message.reply_text("✅ **Пост с кнопкой опубликован в канале!**")
    except Exception as e:
        logging.error(f"❌ Ошибка публикации: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка отправки: {e}")

# ==========================================
# 🚀 ЗАПУСК БОТА
# ==========================================
if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logging.error("ОШИБКА: TELEGRAM_BOT_TOKEN не задан!")
    else:
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("post", generate_and_post))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_message))
        
        logging.info("🤖 Бот «Армавиртелеремонт» успешно запущен!")
        app.run_polling()
