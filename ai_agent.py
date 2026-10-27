import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

# 1. Минимальный веб-сервер Flask для поддержания работы на бесплатном тарифе Render (Web Service)
app = Flask(__name__)

@app.route('/')
def home():
    return "Kwork Bot is alive and running!"

# 2. Настройки и переменные
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
KWORK_URL = "https://kwork.ru/projects?c=11"  # Лента заказов «Разработка и IT»

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
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Ошибка отправки Telegram: {response.text}")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# 3. Фоновый цикл парсинга Kwork
def check_kwork_loop():
    print("🔎 Фоновый парсер Kwork запущен!")
    
    # 🧪 ТЕСТ ПАРСЕРА ПРИ СТАРТЕ: заходим на Kwork и присылаем первый заказ
    try:
        response = requests.get(KWORK_URL, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select(".project-card")
            
            if cards:
                first_card = cards[0]
                title_elem = first_card.select_one(".project-card__title")
                title = title_elem.get_text(strip=True) if title_elem else "Без названия"
                
                link_elem = first_card.select_one("a")
                link = link_elem["href"] if link_elem and "href" in link_elem.attrs else "https://kwork.ru"
                if not link.startswith("http"):
                    link = "https://kwork.ru" + link
                
                send_telegram_message(
                    f"🧪 <b>Тест парсера Kwork успешен!</b>\n\n"
                    f"📊 Найдено заказов на странице: <b>{len(cards)}</b>\n"
                    f"📌 <b>Свежий заказ:</b> {title}\n"
                    f"🔗 <a href='{link}'>Открыть заказ на Kwork</a>"
                )
            else:
                send_telegram_message("⚠️ Kwork открылся (200 OK), но селектор `.project-card` не нашёл карточек.")
        else:
            send_telegram_message(f"⚠️ Ошибка доступа к Kwork! Код ответа: {response.status_code}")
    except Exception as e:
        send_telegram_message(f"❌ Исключение при тесте парсера: {e}")

    # Основной бессрочный цикл мониторингановости
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
                    
                    title = link_tag.text.strip()
                    price_tag = card.select_one(".project-card__price")
                    price = price_tag.text.strip() if price_tag else "Договорная"
                    
                    text_tag = card.select_one(".project-card__description")
                    description = text_tag.text.strip()[:200] + "..." if text_tag else "Без описания"

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
            
        time.sleep(30)  # Проверка каждые 30 секунд

# Запускаем парсер в фоновом потоке
parser_thread = threading.Thread(target=check_kwork_loop, daemon=True)
parser_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
