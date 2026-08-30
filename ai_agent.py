# -*- coding: utf-8 -*-
import os
import logging
import threading
from flask import Flask
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# 🌐 МИНИ-СЕРВЕР ДЛЯ ОБХОДА ОШИБКИ PORT НА RENDER
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Армавиртелеремонт Bot is live!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# Запускаем веб-сервер сразу в фоновом потоке
threading.Thread(target=run_web, daemon=True).start()

# ==========================================
# 🔑 НАСТРОЙКИ И КЛЮЧИ ДОСТУПА
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-1003786532521")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# 🧠 СИСТЕМНЫЕ ИНСТРУКЦИИ ДЛЯ АГЕНТОВ
# ==========================================

# 1. АГЕНТ-КОПИРАЙТЕР (SMM)
PROMPT_COPYWRITER = """
Ты — профессиональный SMM-копирайтер телемастерской «Армавиртелеремонт» (г. Армавир, ул. Туапсинская, 503).
Пиши короткие, вовлекающие и продающие посты для Telegram-канала.
В постах:
- Объясняй причины частых поломок (сгорела подсветка, сбой прошивки, проблемы с блоком питания).
- Используй эмодзи и структурированный текст.
- Указывай контакты строго в формате:
  📍 **Адрес:** г. Армавир, ул. Туапсинская, 503
  📞 **Телефон / WhatsApp / MAX:** +7 (929) 850-19-93
  🌐 **Наш сайт:** https://armavirteleremont.github.io/remontledtv/
- Призывай обращаться к мастеру Александру Парфилову.
"""

# 2. АГЕНТ-ПРОДАВЕЦ (Консультант)
PROMPT_SALES = """
Ты — вежливый ИИ-консультант телемастерской «Армавиртелеремонт» (г. Армавир, ул. Туапсинская, 503).
Твоя задача — отвечать на вопросы клиентов, выявлять симптомы поломки и ориентировать по стоимости ремонта.

--- БАЗА ЗНАНИЙ И ПРАЙС-ЛИСТ ---
- Мастер: Александр Парфилов (опыт работы более 25 лет).
- Адрес: г. Армавир, ул. Туапсинская, 503.
- Телефон / WhatsApp / MAX: +7 (929) 850-19-93.
- Сайт: https://armavirteleremont.github.io/remontledtv/

ЧАСТЫЕ ПОЛОМКИ, ПРИЧИНЫ И ЦЕНЫ:
1. Симптом: Звук есть, а изображения нет (или экран темный, но при фонарике виден силуэт).
   Причина: Сгорела LED-подсветка матрицы.
   Решение: Замена комплекта планок подсветки.
   Ориентировочная стоимость (работа + планки):
   - Диагональ 32" (81 см) — от 2 500 до 5 000 руб.
   - Диагональ 40" - 43" (102–109 см) — от 4 000 до 7 000 руб.
   - Диагональ 49" - 50" (124–127 см) — от 5 000 до 9 000 руб.
   - Диагональ 55" (140 см) и выше — от 9 000 руб.

2. Симптом: Телевизор не включается, индикатор не горит или мигает.
   Причина: Проблема в блоке питания (конденсаторы, предохранители, транзисторы).

3. Симптом: Зависает на логотипе, перезагружается сам.
   Причина: Сбой прошивки (память EMMC / SPI Flash).

4. Симптом: Полосы на экране после удара или попадания воды.
   Причина: Повреждение матрицы или шлейфов. (Предупреждай вежливо, что разбитые матрицы менять часто невыгодно).

ПРАВИЛА ОБЩЕНИЯ И СТРОГИЕ ОГРАНИЧЕНИЯ:
- КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать слова «бесплатная диагностика», «бесплатный осмотр», «бесплатно».
- Будь вежливым, пиши коротко и по делу.
- Задавай уточняющие вопросы (марка/модель ТВ, диагональ, симптомы).
- Называй вероятную причину поломки и ориентировочную вилку цен.
- Напоминай, что точную цену мастер называет только после осмотра техники на верстаке в мастерской.
- Не повторяй призывы привезти ТВ, если уже говорил об этом выше в диалоге.
- В контактах указывай строго: 📞 **Телефон / WhatsApp / MAX:** +7 (929) 850-19-93, сайт: https://armavirteleremont.github.io/remontledtv/
"""

# ==========================================
# ⚙️ ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Здравствуйте! Вас приветствует мастерская «Армавиртелеремонт».**\n\n"
        "Я ИИ-консультант мастера Александра Парфилова. "
        "Опишите, что случилось с вашим телевизором (например: *«Звук есть, а изображения нет»*), "
        "и я подскажу возможную причину и сориентирую по цене!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"📩 Входящее сообщение: {user_text}")
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=user_text,
            config={'system_instruction': PROMPT_SALES}
        )
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Подскажите, пожалуйста, марку и диагональ вашего телевизора?")
            
    except Exception as e:
        logging.error(f"❌ Ошибка Gemini API: {e}")
        await update.message.reply_text("Извините, произошел временный сбой. Пожалуйста, позвоните нам напрямую: +7 (929) 850-19-93.")

async def generate_and_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else "Замена подсветки телевизора LG и Samsung"
    await update.message.reply_text(f"⏳ **Агент-Копирайтер генерирует пост на тему:** «{topic}»...")
    
    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=f"Напиши отличный рекламный пост на тему: {topic}",
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
        await update.message.reply_text("✅ **Пост с кнопкой успешно опубликован в канале!**")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")
        await update.message.reply_text(f"❌ Ошибка при отправке в канал: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.warning(f"⚠️ Сетевая пауза Telegram: {context.error}")

# ==========================================
# 🚀 ЗАПУСК БОТА
# ==========================================
if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        logging.error("ОШИБКА: Не заданы переменные окружения TELEGRAM_BOT_TOKEN или GEMINI_API_KEY!")
    else:
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("post", generate_and_post))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_customer_message))
        
        app.add_error_handler(error_handler)
        
        logging.info("🤖 Мультиагентная система «Армавиртелеремонт» запущен!")
        app.run_polling()