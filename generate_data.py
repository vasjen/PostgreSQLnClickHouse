import csv
import random
import uuid
from datetime import datetime, timedelta

# --- Параметры генерации ---
NUM_ROWS = 15_000_000  # Количество строк (например, 15 миллионов)
OUTPUT_FILE = './data/web_logs.csv' # Путь к файлу внутри папки data
START_DATE = datetime(2023, 10, 1)
END_DATE = datetime(2023, 11, 30)
# --------------------------

# Примерные данные для генерации
URLS = [f"/page_{i}.html" for i in range(1, 100)] + \
       [f"/product/{i}" for i in range(1, 50)] + \
       [f"/category/{i}" for i in range(1, 20)] + \
       ["/home", "/cart", "/checkout", "/profile"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0"
]
REFERRERS = ["https://google.com/", "https://bing.com/", "https://direct_traffic.com", "https://some_partner_site.com", ""] * 5 # Добавим пустых
HTTP_STATUSES = [200] * 85 + [404] * 10 + [500] * 3 + [301] * 2 # 85% успеха

print(f"Генерация {NUM_ROWS} строк данных...")

with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['timestamp', 'user_id', 'session_id', 'url', 'ip_address',
                  'user_agent', 'response_time_ms', 'http_status', 'referrer_url']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    time_delta_seconds = int((END_DATE - START_DATE).total_seconds())

    for i in range(NUM_ROWS):
        # Генерируем случайное время в заданном диапазоне
        random_seconds = random.randint(0, time_delta_seconds)
        event_time = START_DATE + timedelta(seconds=random_seconds)

        # Генерируем остальные данные
        user_id = random.randint(1, 500_000) # 500k уникальных юзеров
        session_id = str(uuid.uuid4())
        url = random.choice(URLS)
        ip_address = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        user_agent = random.choice(USER_AGENTS)
        response_time_ms = max(10, int(random.gauss(150, 80))) # Среднее 150мс, разброс
        http_status = random.choice(HTTP_STATUSES)
        referrer_url = random.choice(REFERRERS)

        writer.writerow({
            'timestamp': event_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'session_id': session_id,
            'url': url,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'response_time_ms': response_time_ms,
            'http_status': http_status,
            'referrer_url': referrer_url
        })

        if (i + 1) % 100000 == 0:
            print(f"Сгенерировано {i + 1}/{NUM_ROWS} строк...")

print(f"Данные успешно сгенерированы в файл: {OUTPUT_FILE}")