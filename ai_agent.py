import os
import time
import threading
import html  # <--- Обязательно импортируем для экранирования HTML
import requests
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Kwork Bot is alive and running!"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
KWORK_URL = "https://kwork.ru/projects?c=11"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

seen_projects = set()

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Ошибка: TELEGRAM_TOKEN или CHAT_ID не настроены в Environment Variables!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            # Выводим точный текст ошибки от Telegram API в логи Render
            print(f"❌ Ошибка отправки Telegram (код {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Исключение при отправке в Telegram: {e}")

def check_kwork_loop():
    print("🔎 Фоновый парсер Kwork запущен!")
    
    while True:
        try:
            response = requests.get(KWORK_URL, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.select(".project-card")
                
                for card in cards:
                    link_tag = card.select_one("a[href*='/projects/']")
                    if not link_tag:
                        continue
                    
                    project_url = link_tag.get("href")
                    if project_url.startswith("/"):
                        project_url = "https://kwork.ru" + project_url
                        
                    try:
                        project_id = project_url.split("/projects/")[1].split("/")[0]
                    except Exception:
                        project_id = project_url

                    if project_id in seen_projects:
                        continue
                    
                    # 🛡 Экранируем спецсимволы HTML, чтобы Telegram не выдавал ошибку
                    title = html.escape(link_tag.text.strip())
                    
                    price_tag = card.select_one(".project-card__price")
                    price = html.escape(price_tag.text.strip()) if price_tag else "Договорная"
                    
                    text_tag = card.select_one(".project-card__description")
                    description = html.escape(text_tag.text.strip()[:200]) + "..." if text_tag else "Без описания"

                    message = (
                        f"🚨 <b>Новый заказ на Kwork!</b>\n\n"
                        f"📌 <b>{title}</b>\n"
                        f"💰 <b>Бюджет:</b> {price}\n\n"
                        f"📝 {description}\n\n"
                        f"🔗 <a href='{project_url}'>Перейти и откликнуться</a>"
                    )
                    
                    send_telegram_message(message)
                    seen_projects.add(project_id)
                    print(f"✅ Отправлено уведомление по заказу #{project_id}")
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            
        time.sleep(30)

parser_thread = threading.Thread(target=check_kwork_loop, daemon=True)
parser_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
