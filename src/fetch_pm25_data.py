"""
Скрипт для получения данных PM2.5 и метеоданных для Бишкека
Использует IQAir, OpenWeatherMap и OpenAQ API
"""

import requests
import json
from datetime import datetime, timedelta
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка API ключей из .env файла
load_dotenv()


class PM25DataCollector:
    """Класс для сбора данных о качестве воздуха"""

    def __init__(self, output_dir="data/pm25"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Координаты Бишкека
        self.bishkek_coords = {
            "lat": 42.8746,
            "lon": 74.5698
        }

    @staticmethod
    def aqi_to_ugm3(aqi):
        """
        Конвертация US AQI в µg/m³ для PM2.5
        Формула из EPA (Environmental Protection Agency)
        """
        if aqi is None:
            return None

        # Breakpoints для PM2.5
        if aqi <= 50:
            return aqi * 12.0 / 50
        elif aqi <= 100:
            return 12.1 + (aqi - 51) * 23.9 / 49
        elif aqi <= 150:
            return 35.5 + (aqi - 101) * 19.4 / 49
        elif aqi <= 200:
            return 55.5 + (aqi - 151) * 94.4 / 49
        elif aqi <= 300:
            return 150.5 + (aqi - 201) * 99.4 / 99
        else:
            return 250.5 + (aqi - 301) * 99.9 / 99

    def fetch_openaq_current(self):
        """
        Получить текущие данные PM2.5 из OpenAQ API
        https://docs.openaq.org/docs
        """
        url = "https://api.openaq.org/v2/latest"

        params = {
            "city": "Bishkek",
            "parameter": "pm25",
            "limit": 100
        }

        try:
            print("🌍 Запрос данных из OpenAQ...")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if not results:
                    print("⚠️  Нет данных для Бишкека в OpenAQ")
                    return None

                print(f"✅ Получено {len(results)} записей от датчиков")

                # Обработка результатов
                processed = []
                for station in results:
                    location = station.get("location", "Unknown")
                    coords = station.get("coordinates", {})
                    measurements = station.get("measurements", [])

                    for measurement in measurements:
                        if measurement.get("parameter") == "pm25":
                            processed.append({
                                "source": "OpenAQ",
                                "location": location,
                                "latitude": coords.get("latitude"),
                                "longitude": coords.get("longitude"),
                                "pm25": measurement.get("value"),
                                "unit": measurement.get("unit"),
                                "timestamp": measurement.get("lastUpdated"),
                                "fetched_at": datetime.now().isoformat()
                            })

                return processed

            else:
                print(f"❌ Ошибка OpenAQ: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Ошибка при запросе OpenAQ: {e}")
            return None

    def fetch_iqair_current(self, api_key=None):
        """
        Получить текущие данные PM2.5 из IQAir API

        ВАЖНО: Требуется бесплатный API ключ с https://www.iqair.com/air-pollution-data-api
        """
        if not api_key:
            print("⚠️  IQAir API ключ не предоставлен")
            print("   Получите бесплатный ключ: https://www.iqair.com/air-pollution-data-api")
            return None

        # Попробуем через координаты (nearest city)
        url = "http://api.airvisual.com/v2/nearest_city"

        params = {
            "lat": self.bishkek_coords["lat"],
            "lon": self.bishkek_coords["lon"],
            "key": api_key
        }

        try:
            print("🌍 Запрос данных из IQAir...")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "success":
                    current = data["data"]["current"]
                    pollution = current["pollution"]
                    weather = current["weather"]

                    pm25_aqi = pollution.get("aqius")
                    pm25_conc = pollution.get("p2", {}).get("conc")

                    # Если концентрация не пришла - конвертируем из AQI
                    if pm25_conc is None and pm25_aqi is not None:
                        pm25_conc = self.aqi_to_ugm3(pm25_aqi)

                    result = {
                        "source": "IQAir",
                        "city": "Bishkek",
                        "pm25_aqi": pm25_aqi,  # US AQI
                        "pm25": pm25_conc,  # µg/m³ (основное значение)
                        "temperature": weather.get("tp"),
                        "humidity": weather.get("hu"),
                        "pressure": weather.get("pr"),
                        "wind_speed": weather.get("ws"),
                        "timestamp": pollution.get("ts"),
                        "fetched_at": datetime.now().isoformat()
                    }

                    print(f"✅ PM2.5: {result['pm25']:.1f} µg/m³ (AQI: {pm25_aqi})")
                    print(f"   Температура: {result['temperature']}°C")
                    print(f"   Влажность: {result['humidity']}%")

                    return result
                else:
                    print(f"❌ IQAir API вернул ошибку: {data}")
                    return None
            else:
                print(f"❌ Ошибка IQAir: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Ошибка при запросе IQAir: {e}")
            return None

    def fetch_openweathermap(self, api_key=None):
        """
        Получить метеоданные из OpenWeatherMap

        API ключ: https://openweathermap.org/api (бесплатно)
        """
        if not api_key:
            print("⚠️  OpenWeatherMap API ключ не предоставлен")
            print("   Получите бесплатный ключ: https://openweathermap.org/api")
            return None

        # Air Pollution API
        pollution_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        weather_url = "https://api.openweathermap.org/data/2.5/weather"

        params = {
            "lat": self.bishkek_coords["lat"],
            "lon": self.bishkek_coords["lon"],
            "appid": api_key
        }

        try:
            print("🌍 Запрос данных из OpenWeatherMap...")

            # Получаем PM2.5
            pollution_response = requests.get(pollution_url, params=params, timeout=10)
            weather_response = requests.get(weather_url, params=params, timeout=10)

            if pollution_response.status_code == 200 and weather_response.status_code == 200:
                pollution_data = pollution_response.json()
                weather_data = weather_response.json()

                pm_components = pollution_data["list"][0]["components"]
                main = weather_data["main"]
                wind = weather_data["wind"]

                result = {
                    "source": "OpenWeatherMap",
                    "pm25": pm_components.get("pm2_5"),
                    "pm10": pm_components.get("pm10"),
                    "temperature": main.get("temp") - 273.15,  # Kelvin → Celsius
                    "humidity": main.get("humidity"),
                    "pressure": main.get("pressure"),
                    "wind_speed": wind.get("speed"),
                    "clouds": weather_data.get("clouds", {}).get("all"),
                    "visibility": weather_data.get("visibility"),
                    "timestamp": datetime.fromtimestamp(pollution_data["list"][0]["dt"]).isoformat(),
                    "fetched_at": datetime.now().isoformat()
                }

                print(f"✅ PM2.5: {result['pm25']} µg/m³")
                print(f"   Температура: {result['temperature']:.1f}°C")
                print(f"   Влажность: {result['humidity']}%")
                print(f"   Видимость: {result['visibility']} m")

                return result
            else:
                print(f"❌ Ошибка: Pollution={pollution_response.status_code}, Weather={weather_response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Ошибка при запросе OpenWeatherMap: {e}")
            return None

    def save_data(self, data, source_name):
        """Сохранение данных в JSON файл"""
        if not data:
            print("⚠️  Нет данных для сохранения")
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{source_name}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"💾 Данные сохранены: {filepath}")

    def collect_all(self, iqair_key=None, openweather_key=None):
        """Сбор данных из всех доступных источников"""
        print("=" * 80)
        print("📊 СБОР ДАННЫХ PM2.5 И МЕТЕОДАННЫХ")
        print("=" * 80)
        print()

        all_data = []

        # OpenAQ (бесплатно, без API ключа)
        print("[1/3] OpenAQ API")
        print("-" * 80)
        openaq_data = self.fetch_openaq_current()
        if openaq_data:
            self.save_data(openaq_data, "openaq")
            all_data.extend(openaq_data)
        print()

        # IQAir (требует бесплатный API ключ)
        print("[2/3] IQAir API")
        print("-" * 80)
        iqair_data = self.fetch_iqair_current(iqair_key)
        if iqair_data:
            self.save_data([iqair_data], "iqair")
            all_data.append(iqair_data)
        print()

        # OpenWeatherMap (требует бесплатный API ключ)
        print("[3/3] OpenWeatherMap API")
        print("-" * 80)
        owm_data = self.fetch_openweathermap(openweather_key)
        if owm_data:
            self.save_data([owm_data], "openweathermap")
            all_data.append(owm_data)
        print()

        print("=" * 80)
        print(f"📊 Всего собрано записей: {len(all_data)}")
        print("=" * 80)

        return all_data


def main():
    """Запуск сбора данных PM2.5"""
    collector = PM25DataCollector()

    # Загрузка API ключей из .env файла
    iqair_key = os.getenv('IQAIR_API_KEY')
    openweather_key = os.getenv('OPENWEATHER_API_KEY')

    # Проверка наличия ключей
    if not iqair_key or iqair_key == 'your_iqair_api_key_here':
        print("⚠️  ВНИМАНИЕ: IQAir API ключ не найден в .env файле")
        print("   Добавьте: IQAIR_API_KEY=ваш_ключ")
        iqair_key = None

    if not openweather_key or openweather_key == 'your_openweather_api_key_here':
        print("⚠️  ВНИМАНИЕ: OpenWeatherMap API ключ не найден в .env файле")
        print("   Добавьте: OPENWEATHER_API_KEY=ваш_ключ")
        openweather_key = None

    print()

    # Сбор данных
    collector.collect_all(
        iqair_key=iqair_key,
        openweather_key=openweather_key
    )


if __name__ == "__main__":
    main()
