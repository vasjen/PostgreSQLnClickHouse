
**Бизнес-кейс: Аналитика посещений веб-сайта**

Представим, что мы работаем в компании, у которой есть популярный веб-сайт (например, новостной портал или интернет-магазин). Нам нужно анализировать логи посещений, чтобы понимать поведение пользователей, популярность контента, эффективность рекламных кампаний и т.д.

*   **Данные:** Каждый раз, когда пользователь заходит на страницу, генерируется запись в логе со следующей информацией:
    *   `timestamp`: Время события (точность до секунды)
    *   `user_id`: Идентификатор пользователя (числовой)
    *   `session_id`: Идентификатор сессии (UUID или строка)
    *   `url`: Посещенный URL (строка)
    *   `ip_address`: IP-адрес пользователя (строка)
    *   `user_agent`: User Agent браузера (строка)
    *   `response_time_ms`: Время ответа сервера в миллисекундах (числовое)
    *   `http_status`: HTTP-статус ответа (числовое, например, 200, 404, 500)
    *   `referrer_url`: URL, с которого пришел пользователь (строка, может быть пустой)
*   **Объем данных:** Сайт генерирует миллионы таких событий в день. Для нашего демо сгенерируем ~10-20 миллионов записей, чтобы разница была ощутимой.
*   **Задачи аналитики (типичные OLAP-запросы):**
    1.  Посчитать количество уникальных посетителей за последний месяц.
    2.  Найти топ-10 самых посещаемых URL за вчерашний день.
    3.  Рассчитать среднее время ответа сервера (`response_time_ms`) для страниц, вернувших статус 200, сгруппированное по часам за последние 3 дня.
    4.  Найти все события для конкретной сессии (`session_id`). (Этот запрос больше похож на OLTP).

**Почему это хороший пример?**

Аналитические запросы (1, 2, 3) обычно затрагивают **много строк**, но **мало столбцов**. Например, для подсчета уникальных посетителей (задача 1) нам нужен только столбец `user_id` и `timestamp`. Для топ-10 URL (задача 2) нужны `url` и `timestamp`. Для среднего времени ответа (задача 3) нужны `response_time_ms`, `http_status` и `timestamp`.

**Основное Техническое Различие (Напоминание)**

*   **PostgreSQL (Строковая/Row-oriented):** Хранит данные строками. `[row1_col1, row1_col2, ...], [row2_col1, row2_col2, ...]` . Чтобы прочитать значение одного столбца для многих строк, СУБД приходится считывать с диска *все* столбцы этих строк, даже если они не нужны для запроса.
*   **ClickHouse (Колоночная/Columnar):** Хранит данные столбцами. `[row1_col1, row2_col1, ...], [row1_col2, row2_col2, ...]` . Чтобы прочитать значения одного столбца для многих строк, СУБД считывает только данные этого столбца. Это значительно сокращает объем чтения с диска (I/O). Кроме того, данные в одном столбце обычно однотипны и хорошо сжимаются.

**Демонстрационный Сценарий**

**1. Необходимые Условия:**

*   Установленный Docker и Docker Compose.
*   Достаточно свободного места на диске (~5-10 ГБ для данных и контейнеров).
*   Python 3 для генерации данных.
*   Клиенты командной строки для PostgreSQL (`psql`) и ClickHouse (`clickhouse-client`). Их можно запустить из контейнеров.

**2. Настройка Окружения (Docker Compose):**

Создай файл `docker-compose.yml`:

```yaml
version: '3.7'

services:
  postgres_db:
    image: postgres:15 # Используем актуальную версию PostgreSQL
    container_name: postgres_analytics_demo
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: web_analytics
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # Можно добавить volume для загрузки данных
      - ./data:/data_load 

  clickhouse_db:
    image: clickhouse/clickhouse-server:latest # Используем актуальную версию ClickHouse
    container_name: clickhouse_analytics_demo
    environment:
      CLICKHOUSE_USER: user
      CLICKHOUSE_PASSWORD: password
      CLICKHOUSE_DB: web_analytics
    ports:
      - "8123:8123" # HTTP-интерфейс
      - "9000:9000" # Нативный TCP-интерфейс
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      # Можно добавить volume для загрузки данных
      - ./data:/data_load 
    ulimits: # Рекомендуется для ClickHouse
      nofile:
        soft: 262144
        hard: 262144

volumes:
  postgres_data:
  clickhouse_data:
```

**3. Генерация Демо-Данных:**

Создай директорию `data` рядом с `docker-compose.yml`.
Создай Python-скрипт `generate_data.py` (положи его *вне* папки `data`):

```python
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
```

Запусти скрипт: `python generate_data.py`. Это займет некоторое время.

**4. Запуск Контейнеров и Создание Схем:**

Запусти контейнеры: `docker-compose up -d`

**Создание таблицы в PostgreSQL:**

Подключись к контейнеру PostgreSQL:
`docker exec -it postgres_analytics_demo psql -U user -d web_analytics`

Выполни SQL-запрос для создания таблицы:

```sql
CREATE TABLE web_logs (
    timestamp TIMESTAMP,
    user_id BIGINT,
    session_id VARCHAR(36),
    url TEXT,
    ip_address VARCHAR(45), -- Достаточно для IPv6 в теории, но для IPv4 хватит и VARCHAR(15)
    user_agent TEXT,
    response_time_ms INTEGER,
    http_status SMALLINT,
    referrer_url TEXT
);

-- Добавим индекс на время, т.к. часто фильтруем по нему
CREATE INDEX idx_web_logs_timestamp ON web_logs (timestamp);

-- Можно добавить и другие индексы, но для чистоты эксперимента начнем с одного
-- CREATE INDEX idx_web_logs_url ON web_logs (url);
-- CREATE INDEX idx_web_logs_user_id ON web_logs (user_id);
```

Выйди из `psql` командой `\q`.

**Создание таблицы в ClickHouse:**

Подключись к контейнеру ClickHouse:
`docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics`

Выполни SQL-запрос для создания таблицы (синтаксис немного отличается):

```sql
CREATE TABLE web_logs (
    timestamp DateTime,
    user_id UInt64,
    session_id String, -- UUID можно хранить как String или FixedString(36)
    url String,
    ip_address String, -- ClickHouse имеет тип IPv4/IPv6, но для простоты используем String
    user_agent String,
    response_time_ms UInt32,
    http_status UInt16,
    referrer_url String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp) -- Партиционируем по месяцам для эффективности
ORDER BY (timestamp, url, user_id); -- Ключ сортировки важен для производительности!
                                    -- Выбираем поля, по которым часто фильтруем/группируем
```

Выйди из `clickhouse-client` командой `exit` или `Ctrl+D`.

**5. Загрузка Данных:**

**Загрузка в PostgreSQL:**

```bash
# Запускаем из хост-машины, где лежит docker-compose.yml и папка data
echo "Загрузка данных в PostgreSQL..."
time docker exec -i postgres_analytics_demo psql -U user -d web_analytics -c "\COPY web_logs FROM '/data_load/web_logs.csv' CSV HEADER;"
echo "Загрузка в PostgreSQL завершена."
```
*Примечание:* Загрузка в PostgreSQL может быть довольно медленной для такого объема данных.

**Загрузка в ClickHouse:**

```bash
# Запускаем из хост-машины
echo "Загрузка данных в ClickHouse..."
# Используем нативный формат CSVWithNames, который ожидает заголовки
time docker exec -i clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="INSERT INTO web_logs FORMAT CSVWithNames" < ./data/web_logs.csv
echo "Загрузка в ClickHouse завершена."
```
*Примечание:* ClickHouse обычно загружает данные значительно быстрее.

**6. Выполнение Тестовых Запросов и Сравнение:**

Теперь самое интересное! Выполним наши аналитические запросы в обеих базах и замерим время. Используй `time` перед командами `docker exec ...` для замера времени выполнения.

**Запрос 1: Количество уникальных посетителей за Ноябрь 2023:**

*   **PostgreSQL:**
    ```bash
    time docker exec -it postgres_analytics_demo psql -U user -d web_analytics -c "SELECT COUNT(DISTINCT user_id) FROM web_logs WHERE timestamp >= '2023-11-01' AND timestamp < '2023-12-01';"
    ```
*   **ClickHouse:**
    ```bash
    time docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="SELECT uniqExact(user_id) FROM web_logs WHERE timestamp >= '2023-11-01' AND timestamp < '2023-12-01';"
    ```
    *Ожидание:* ClickHouse должен быть значительно быстрее. Ему нужно прочитать только столбцы `user_id` и `timestamp`. PostgreSQL придется прочитать все столбцы для строк, попадающих в диапазон дат.

**Запрос 2: Топ-10 самых посещаемых URL за 29 Ноября 2023:**

*   **PostgreSQL:**
    ```bash
    time docker exec -it postgres_analytics_demo psql -U user -d web_analytics -c "SELECT url, COUNT(*) as hits FROM web_logs WHERE timestamp >= '2023-11-29 00:00:00' AND timestamp < '2023-11-30 00:00:00' GROUP BY url ORDER BY hits DESC LIMIT 10;"
    ```
*   **ClickHouse:**
    ```bash
    time docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="SELECT url, count() AS hits FROM web_logs WHERE timestamp >= '2023-11-29 00:00:00' AND timestamp < '2023-11-30 00:00:00' GROUP BY url ORDER BY hits DESC LIMIT 10;"
    ```
    *Ожидание:* ClickHouse снова должен быть быстрее. Читаются только `url` и `timestamp`. Группировка и агрегация в колоночных СУБД часто оптимизированы.

**Запрос 3: Среднее время ответа (статус 200) по часам за последние 3 дня (27-29 Ноября):**

*   **PostgreSQL:**
    ```sql
    -- В psql для удобства
    SELECT
        date_trunc('hour', timestamp) AS hour_slice,
        AVG(response_time_ms) AS avg_response
    FROM web_logs
    WHERE http_status = 200
      AND timestamp >= '2023-11-27 00:00:00'
      AND timestamp < '2023-11-30 00:00:00'
    GROUP BY hour_slice
    ORDER BY hour_slice;
    ```
    ```bash
    # Команда для запуска
    time docker exec -it postgres_analytics_demo psql -U user -d web_analytics -c "SELECT date_trunc('hour', timestamp) AS hour_slice, AVG(response_time_ms) AS avg_response FROM web_logs WHERE http_status = 200 AND timestamp >= '2023-11-27 00:00:00' AND timestamp < '2023-11-30 00:00:00' GROUP BY hour_slice ORDER BY hour_slice;"
    ```
*   **ClickHouse:**
    ```sql
    -- В clickhouse-client для удобства
    SELECT
        toStartOfHour(timestamp) AS hour_slice,
        avg(response_time_ms) AS avg_response
    FROM web_logs
    WHERE http_status = 200
      AND timestamp >= '2023-11-27 00:00:00'
      AND timestamp < '2023-11-30 00:00:00'
    GROUP BY hour_slice
    ORDER BY hour_slice;
    ```
    ```bash
    # Команда для запуска
    time docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="SELECT toStartOfHour(timestamp) AS hour_slice, avg(response_time_ms) AS avg_response FROM web_logs WHERE http_status = 200 AND timestamp >= '2023-11-27 00:00:00' AND timestamp < '2023-11-30 00:00:00' GROUP BY hour_slice ORDER BY hour_slice;"
    ```
    *Ожидание:* ClickHouse опять должен показать значительное преимущество. Читаются столбцы `timestamp`, `http_status`, `response_time_ms`.

**Запрос 4: Найти все события для конкретной сессии (OLTP-подобный запрос):**

Сначала найдем какую-нибудь `session_id` для теста:
```bash
# В ClickHouse (быстрее найдет)
docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="SELECT session_id FROM web_logs LIMIT 1"
# Скопируй полученный ID
```
Пусть мы получили `SESSION_ID_TO_FIND`.

*   **PostgreSQL:**
    ```bash
    # Сначала создадим индекс для ускорения этого типа запросов в Postgres
    docker exec -it postgres_analytics_demo psql -U user -d web_analytics -c "CREATE INDEX idx_web_logs_session_id ON web_logs (session_id);"
    # Теперь сам запрос
    time docker exec -it postgres_analytics_demo psql -U user -d web_analytics -c "SELECT * FROM web_logs WHERE session_id = 'SESSION_ID_TO_FIND';" 
    ```
*   **ClickHouse:**
    ```bash
    time docker exec -it clickhouse_analytics_demo clickhouse-client -u user --password password --database web_analytics --query="SELECT * FROM web_logs WHERE session_id = 'SESSION_ID_TO_FIND';"
    ```
    *Ожидание:* Здесь PostgreSQL (особенно с индексом по `session_id`) может оказаться *быстрее* или сравнимым по скорости. Ему нужно найти строки по индексу и прочитать их целиком, что он делает эффективно. ClickHouse придется "собирать" строки из разных столбцов, что не является его самой сильной стороной для запросов типа `SELECT *` по неключевому полю для небольшого числа строк.

**7. Анализ Результатов:**

После выполнения запросов сравни время (значение `real` в выводе команды `time`). Ты должен увидеть, что:

1.  **Аналитические запросы (1, 2, 3):** ClickHouse выполняет их на порядок (или даже на несколько порядков) быстрее, чем PostgreSQL. Это происходит потому, что ClickHouse читает с диска только те столбцы, которые участвуют в запросе, и делает это очень эффективно благодаря колоночному хранению и сжатию. PostgreSQL вынужден читать строки целиком, даже если 90% данных из строки не нужны, что приводит к огромному количеству лишних операций I/O.
2.  **Запрос одной записи (4):** PostgreSQL с индексом, скорее всего, будет быстрее или сравним. Это показывает, что для OLTP-операций (выборка, обновление, удаление *конкретных* строк) строковые базы данных остаются очень эффективными.

**Выводы:**

*   **Колоночные СУБД (ClickHouse):** Идеальны для **OLAP (Online Analytical Processing)**. Когда нужно быстро агрегировать, фильтровать, анализировать большие объемы данных по нескольким колонкам. Они экономят I/O и отлично сжимают данные. Скорость аналитических запросов – их главный козырь.
*   **Строковые СУБД (PostgreSQL):** Идеальны для **OLTP (Online Transaction Processing)**. Когда важны транзакции, целостность данных, быстрое добавление/изменение/удаление отдельных строк, выборка всей информации по конкретной записи (например, показать профиль пользователя по его ID).
*   **Выбор инструмента:** Зависит от задачи. Для бэкенда приложения, где нужны CRUD-операции над отдельными объектами, PostgreSQL – отличный выбор. Для построения аналитических отчетов, дашбордов, систем мониторинга поверх больших объемов данных – ClickHouse будет гораздо производительнее. Часто используют гибридный подход: основное приложение работает с PostgreSQL, а данные для аналитики периодически выгружаются в ClickHouse.
