"""
Скрипт для поиска датчиков PM2.5 в Бишкеке и расчёта расстояний до камер
КРИТИЧНО для проекта: нужно знать где находятся датчики!
"""

import requests
import json
from math import radians, cos, sin, asin, sqrt
from camera_config import CAMERAS, get_recommended_cameras


def haversine(lon1, lat1, lon2, lat2):
    """
    Расчёт расстояния между двумя точками на Земле (формула гаверсинусов)

    Returns:
        float: расстояние в километрах
    """
    # Переводим в радианы
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Формула гаверсинусов
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Радиус Земли в километрах
    return c * r


def find_sensors_openaq_v3(lat=42.8746, lon=74.5698, radius_km=20):
    """
    Поиск датчиков PM2.5 в Бишкеке через OpenAQ API v3

    Args:
        lat, lon: координаты центра поиска (центр Бишкека)
        radius_km: радиус поиска в км

    Returns:
        list: список датчиков с координатами
    """
    # OpenAQ API v3 endpoint
    url = "https://api.openaq.org/v3/locations"

    params = {
        "coordinates": f"{lat},{lon}",
        "radius": radius_km * 1000,  # Конвертируем в метры
        "limit": 100,
        "parameter": "pm25"  # Только PM2.5 датчики
    }

    try:
        print(f"🌍 Поиск датчиков PM2.5 в радиусе {radius_km} км от Бишкека...")
        print(f"   Координаты поиска: {lat}, {lon}")
        print(f"   API: OpenAQ v3")
        print("-" * 80)

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            if not results:
                print("⚠️  Датчики не найдены через OpenAQ API v3")
                return []

            sensors = []
            for location in results:
                # Извлекаем данные о датчике
                sensor_info = {
                    "id": location.get("id"),
                    "name": location.get("name"),
                    "locality": location.get("locality"),
                    "country": location.get("country", {}).get("name"),
                    "latitude": location.get("coordinates", {}).get("latitude"),
                    "longitude": location.get("coordinates", {}).get("longitude"),
                    "sensors": location.get("sensors", []),
                    "provider": location.get("provider", {}).get("name"),
                }

                # Проверяем что есть PM2.5
                has_pm25 = any(s.get("parameter", {}).get("name") == "pm25" for s in sensor_info["sensors"])

                if has_pm25 and sensor_info["latitude"] and sensor_info["longitude"]:
                    sensors.append(sensor_info)

            print(f"✅ Найдено {len(sensors)} датчиков PM2.5")
            return sensors

        else:
            print(f"❌ Ошибка OpenAQ API: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return []

    except Exception as e:
        print(f"❌ Ошибка при запросе: {e}")
        return []


def get_known_sensors_manual():
    """
    Известные датчики в Бишкеке (из web search и других источников)
    Используется если OpenAQ API не работает
    """
    return [
        {
            "name": "US Embassy Bishkek",
            "latitude": 42.8746,
            "longitude": 74.6122,
            "source": "US Embassy / AQICN",
            "url": "https://aqicn.org/city/kyrgyzstan/bishkek/us-embassy/"
        },
        {
            "name": "Chuy Avenue",
            "latitude": 42.8756,
            "longitude": 74.6038,
            "source": "AQICN",
            "url": "https://aqicn.org/station/kyrgyzstan-bishkek-chuy-avenue/"
        },
        {
            "name": "UN House Bishkek",
            "latitude": 42.8757,
            "longitude": 74.6036,
            "source": "Purple Air",
            "url": "https://aqicn.org/station/@93670/"
        },
        {
            "name": "Ак-Орго (Ak-Orgo)",
            "latitude": 42.85,
            "longitude": 74.59,
            "source": "AQICN",
            "url": "https://aqicn.org/station/kyrgyzstan/bishkek/ак-орго"
        }
    ]


def calculate_distances_to_cameras(sensors):
    """
    Рассчитывает расстояния от каждого датчика до каждой камеры

    Args:
        sensors: список датчиков с координатами

    Returns:
        dict: расстояния для каждой пары камера-датчик
    """
    cameras = get_recommended_cameras()
    distances = {}

    print("\n" + "=" * 80)
    print("📏 РАССТОЯНИЯ КАМЕРА → ДАТЧИК")
    print("=" * 80)

    for camera_id, camera_info in cameras.items():
        if not camera_info["coordinates"]:
            print(f"\n⚠️  {camera_id}: координаты не известны")
            continue

        cam_lat, cam_lon = camera_info["coordinates"]
        camera_name = camera_info["name"]

        print(f"\n📹 {camera_name}")
        print(f"   Координаты: {cam_lat:.6f}, {cam_lon:.6f}")
        print(f"   Направление: {camera_info.get('viewing_direction', 'N/A')}")
        print()

        distances[camera_id] = []

        for sensor in sensors:
            sensor_lat = sensor["latitude"]
            sensor_lon = sensor["longitude"]

            # Рассчитываем расстояние
            dist_km = haversine(cam_lon, cam_lat, sensor_lon, sensor_lat)

            distances[camera_id].append({
                "sensor_name": sensor["name"],
                "distance_km": dist_km,
                "sensor_coords": (sensor_lat, sensor_lon)
            })

            # Оценка качества (критично для статьи!)
            if dist_km < 1:
                status = "✅ ОТЛИЧНО"
            elif dist_km < 2:
                status = "🟡 ХОРОШО"
            elif dist_km < 5:
                status = "🟠 СРЕДНЕ"
            else:
                status = "🔴 ПРОБЛЕМА"

            print(f"   {status} {sensor['name']}: {dist_km:.2f} км")

        # Сортируем по расстоянию
        distances[camera_id].sort(key=lambda x: x["distance_km"])

    return distances


def recommend_camera_sensor_pairs(distances):
    """
    Рекомендует лучшие пары камера-датчик на основе расстояния

    Args:
        distances: результат calculate_distances_to_cameras()

    Returns:
        dict: рекомендованные пары
    """
    print("\n" + "=" * 80)
    print("🎯 РЕКОМЕНДОВАННЫЕ ПАРЫ КАМЕРА-ДАТЧИК")
    print("=" * 80)

    recommendations = {}

    for camera_id, sensor_list in distances.items():
        if not sensor_list:
            continue

        # Берём ближайший датчик
        closest = sensor_list[0]
        dist = closest["distance_km"]

        if dist < 2:
            quality = "✅ Отличная пара"
            use = True
        elif dist < 5:
            quality = "🟡 Приемлемо (описать как limitation)"
            use = True
        else:
            quality = "🔴 НЕ РЕКОМЕНДУЕТСЯ (слишком далеко)"
            use = False

        recommendations[camera_id] = {
            "sensor": closest["sensor_name"],
            "distance_km": dist,
            "quality": quality,
            "use_for_paper": use
        }

        print(f"\n{camera_id}:")
        print(f"  → {closest['sensor_name']}")
        print(f"  Расстояние: {dist:.2f} км")
        print(f"  Оценка: {quality}")

    return recommendations


def save_sensor_data(sensors, distances, recommendations, filename="data/sensor_locations.json"):
    """Сохраняет данные о датчиках и расстояниях"""
    import os
    os.makedirs("data", exist_ok=True)

    output = {
        "sensors": sensors,
        "distances": distances,
        "recommendations": recommendations,
        "generated_at": str(requests.Session().hooks)  # timestamp
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Данные сохранены: {filename}")


def main():
    print("=" * 80)
    print("🔍 ПОИСК ДАТЧИКОВ PM2.5 В БИШКЕКЕ")
    print("=" * 80)
    print()

    # Пробуем OpenAQ API v3
    sensors = find_sensors_openaq_v3()

    # Если не работает - используем известные датчики
    if not sensors:
        print("\n⚠️  OpenAQ API не вернул результаты")
        print("   Используем известные датчики из других источников")
        sensors = get_known_sensors_manual()
        print(f"✅ Загружено {len(sensors)} известных датчиков")

    if not sensors:
        print("\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Датчики не найдены!")
        print("   Проект НЕ МОЖЕТ продолжаться без датчиков PM2.5")
        return

    # Выводим список датчиков
    print("\n" + "=" * 80)
    print("📍 НАЙДЕННЫЕ ДАТЧИКИ")
    print("=" * 80)
    for sensor in sensors:
        print(f"\n{sensor['name']}")
        print(f"  Координаты: {sensor['latitude']:.6f}, {sensor['longitude']:.6f}")
        if 'source' in sensor:
            print(f"  Источник: {sensor['source']}")
        if 'provider' in sensor:
            print(f"  Провайдер: {sensor['provider']}")

    # Рассчитываем расстояния
    distances = calculate_distances_to_cameras(sensors)

    # Рекомендации
    recommendations = recommend_camera_sensor_pairs(distances)

    # Сохраняем
    save_sensor_data(sensors, distances, recommendations)

    # Критическая оценка
    print("\n" + "=" * 80)
    print("⚠️  КРИТИЧЕСКАЯ ОЦЕНКА ДЛЯ СТАТЬИ")
    print("=" * 80)

    usable_pairs = sum(1 for r in recommendations.values() if r["use_for_paper"])
    total_pairs = len(recommendations)

    print(f"\nПригодных пар камера-датчик: {usable_pairs}/{total_pairs}")

    if usable_pairs == 0:
        print("\n🔴 FATAL: Нет подходящих пар камера-датчик!")
        print("   Все датчики слишком далеко от камер")
        print("   РЕКОМЕНДАЦИЯ: Искать другие источники данных PM2.5")
    elif usable_pairs < total_pairs:
        print(f"\n🟡 ВНИМАНИЕ: {total_pairs - usable_pairs} камер имеют далёкие датчики")
        print("   Нужно описать это как limitation в статье")
    else:
        print("\n✅ Отлично! Все камеры имеют близкие датчики")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
