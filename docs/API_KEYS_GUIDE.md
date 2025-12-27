# Инструкция по получению API ключей для PM2.5 данных

**Дата:** 27 декабря 2025
**Цель:** Получить бесплатные API ключи для сбора данных PM2.5 и метеоданных

---

## 1. IQAir API (рекомендую начать с него)

### Регистрация

1. Открой: https://www.iqair.com/air-pollution-data-api
2. Нажми **"Get Started"** или **"Sign Up"**
3. Выбери **Community Edition** (бесплатный план)
4. Заполни форму:
   - Email
   - Password
   - Use case: "Academic research on air quality monitoring"
5. Подтверди email (придет письмо)

### Получение API ключа

1. Войди в аккаунт: https://www.iqair.com/dashboard/api
2. Скопируй **API Key** (формат: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
3. Сохрани ключ в файл `.env` (создам ниже)

### Лимиты

- **1000 запросов/месяц** (бесплатно)
- Для нашего проекта: 1 запрос/час × 10 часов/день × 30 дней = **300 запросов/месяц** на камеру
- С 3 камерами: 900 запросов/месяц - **впритык, но хватит**

### Тестирование

```bash
# Проверь что работает (замени YOUR_API_KEY)
curl "https://api.airvisual.com/v2/city?city=Bishkek&state=Chuy&country=Kyrgyzstan&key=YOUR_API_KEY"
```

Должен вернуть JSON с данными PM2.5 для Бишкека.

---

## 2. OpenWeatherMap API (основной источник)

### Регистрация

1. Открой: https://openweathermap.org/api
2. Нажми **"Sign Up"** (правый верхний угол)
3. Заполни форму:
   - Username
   - Email
   - Password
   - Согласись с Terms
4. Подтверди email

### Получение API ключа

1. Войди в аккаунт
2. Перейди: https://home.openweathermap.org/api_keys
3. Скопируй **Default API key** (или создай новый)
4. Формат ключа: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (32 символа)

**Важно:** Новый API ключ активируется в течение **2-3 часов**. Если сразу не работает - подожди.

### Лимиты

- **1000 запросов/день** (бесплатно)
- Для нашего проекта: 3 камеры × 10 часов/день = **30 запросов/день** - более чем достаточно

### Тестирование

Air Pollution API (PM2.5 + PM10):
```bash
# Проверь (замени YOUR_API_KEY)
# Координаты Бишкека: 42.8746, 74.5698
curl "http://api.openweathermap.org/data/2.5/air_pollution?lat=42.8746&lon=74.5698&appid=YOUR_API_KEY"
```

Должен вернуть:
```json
{
  "list": [
    {
      "main": {"aqi": 3},
      "components": {
        "pm2_5": 25.5,
        "pm10": 45.2,
        ...
      }
    }
  ]
}
```

Текущая погода (температура, влажность, ветер):
```bash
curl "http://api.openweathermap.org/data/2.5/weather?lat=42.8746&lon=74.5698&appid=YOUR_API_KEY&units=metric"
```

---

## 3. AQICN API (опциональный, для резерва)

### Регистрация

1. Открй: https://aqicn.org/data-platform/token/
2. Заполни форму:
   - Email
   - Username
   - Project description: "Academic research on air quality in Bishkek"
3. Нажми **"Request Token"**
4. Получишь токен на email (может занять 1-2 дня для ручного одобрения)

### Получение данных

API token формат: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Тестирование

```bash
# Данные с датчика US Embassy в Бишкеке
curl "https://api.waqi.info/feed/bishkek/?token=YOUR_TOKEN"
```

### Лимиты

- Бесплатно, но есть rate limiting
- Обычно достаточно для исследовательских целей

---

## 4. Сохранение API ключей

Создай файл `.env` в корне проекта:

```bash
cd /Users/admin/PycharmProjects/research_paper_cv
nano .env
```

Добавь:
```
# API Keys for PM2.5 data collection
IQAIR_API_KEY=your_iqair_key_here
OPENWEATHER_API_KEY=your_openweather_key_here
AQICN_API_TOKEN=your_aqicn_token_here
```

Сохрани (Ctrl+O, Enter, Ctrl+X в nano).

**Важно:** Файл `.env` уже в `.gitignore`, поэтому не попадет в git.

---

## 5. Проверка что `.env` в gitignore

```bash
cat .gitignore | grep .env
```

Должно быть:
```
.env
*.env
```

Если нет - добавь:
```bash
echo ".env" >> .gitignore
```

---

## Какой API использовать?

### Приоритет (рекомендую):

**1. OpenWeatherMap (основной)**
- Лучший лимит: 1000 запросов/день
- Официальный и стабильный
- Данные PM2.5 + погода в одном месте

**2. IQAir (резервный)**
- Если OpenWeatherMap недоступен
- Лимит 1000/месяц - мало для 3 камер на долгий срок

**3. AQICN (дополнительный)**
- Для кросс-валидации данных
- Медленное одобрение токена

### Стратегия:

Начни с **OpenWeatherMap**. Если будут проблемы или закончится лимит - переключайся на IQAir.

---

## После получения ключей

1. Сохрани в `.env`
2. Сообщи мне - я обновлю `fetch_pm25_data.py` для работы с реальными API
3. Протестируем получение данных
4. Запустим полный сбор

---

## Проблемы и решения

### OpenWeatherMap: "Invalid API key"

**Причина:** Новый ключ еще не активировался

**Решение:** Подожди 2-3 часа после создания ключа

### IQAir: "Exceeded quota"

**Причина:** Превышен лимит 1000 запросов/месяц

**Решение:** Используй OpenWeatherMap как основной

### AQICN: Не пришел токен

**Причина:** Ручное одобрение может занять 1-2 дня

**Решение:** Начни с OpenWeatherMap и IQAir, AQICN - опциональный

---

## Время получения ключей

- **OpenWeatherMap:** 5 минут (+ 2-3 часа активация)
- **IQAir:** 5-10 минут (instant)
- **AQICN:** 5 минут запрос, 1-2 дня одобрение

**Итого:** Можешь начать работу через 3 часа (пока активируется OpenWeatherMap, используй IQAir).

---

## Следующий шаг

После получения хотя бы одного ключа (IQAir или OpenWeatherMap):
1. Сохрани в `.env`
2. Дай знать - я обновлю код для работы с API
3. Протестируем сбор данных

Удачи! Пиши если будут вопросы.
