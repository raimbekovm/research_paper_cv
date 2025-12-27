"""
Конфигурация камер для проекта PM2.5 estimation
"""

CAMERAS = {
    "ala_too_square": {
        "name": "Бишкек площадь Ала-Тоо",
        "url": "https://stream.kt.kg:5443/live/camera25.m3u8",
        "coordinates": (42.875576, 74.603629),
        "viewing_direction": "10-12° N",
        "viewing_angle": "downward",
        "recommended": False,
        "require_quality_filter": False,
        "description": "Вид вниз на площадь (много переднего плана, мало горизонта)"
    },
    "ala_too_square_2": {
        "name": "Площадь Ала-Тоо (камера 2)",
        "url": "https://stream.kt.kg:5443/live/camera27.m3u8",
        "coordinates": (42.875767, 74.604619),
        "viewing_direction": "~90° E",
        "viewing_angle": "horizontal-wide",
        "recommended": False,  # ⚠️ ПЛОХАЯ для атмосферной видимости
        "require_quality_filter": False,
        "pm25_sensor_distance_km": 0.07,
        "nearest_sensor": "Chuy Avenue",
        "visual_quality_score": 3,  # Слабо - слишком много переднего плана
        "description": "ПРОБЛЕМА: слишком много переднего плана (площадь, дорога, памятник, люди), мало дальних объектов, мало неба. Датчик в 70 м - хорошо, но визуальное качество для атмосферной видимости - ПЛОХОЕ. Не рекомендуется."
    },
    "bishkek_panorama": {
        "name": "Бишкек Панорама",
        "url": "https://stream.kt.kg:5443/live/camera28.m3u8",
        "coordinates": (42.799197, 74.645485),
        "viewing_direction": "~330° NW",
        "viewing_angle": "panoramic-wide",
        "recommended": True,  # ⭐⭐⭐ ЛУЧШАЯ КАМЕРА для PM2.5 estimation
        "require_quality_filter": False,
        "pm25_sensor_distance_km": 7.24,
        "nearest_sensor": "Ак-Орго (Ak-Orgo)",
        "visual_quality_score": 10,  # Идеальная панорама для атмосферной видимости
        "description": "ИДЕАЛЬНАЯ панорама на весь город - атмосферная дымка видна отлично, 50% неба, depth 10+ км. Расстояние до датчика 7.24 км НЕ КРИТИЧНО - видимость интегрируется вдоль всей линии зрения!"
    },
    "sovmin": {
        "name": "Бишкек Совмин",
        "url": "https://stream.kt.kg:5443/live/camera33.m3u8",
        "coordinates": (42.804394, 74.587977),
        "viewing_direction": "~45° NE",
        "viewing_angle": "elevated-wide",
        "recommended": True,  # ⭐⭐⭐ ОТЛИЧНАЯ КАМЕРА для PM2.5 estimation
        "require_quality_filter": False,
        "pm25_sensor_distance_km": 5.07,
        "nearest_sensor": "Ак-Орго (Ak-Orgo)",
        "visual_quality_score": 9,  # Отличный вид на южный район
        "description": "ОТЛИЧНАЯ панорама на весь южный район города - атмосферная дымка видна вдали, много неба, depth 5+ км. Расстояние до датчика 5.07 км приемлемо для городского масштаба PM2.5"
    },
    "kt_center": {
        "name": "Кыргызтелеком Центр",
        "url": "https://stream.kt.kg:5443/live/camera35.m3u8",
        "coordinates": (42.874689, 74.612241),
        "viewing_direction": "variable (rotating)",
        "viewing_angle": "rotating",
        "recommended": True,  # ⭐⭐ ХОРОШАЯ КАМЕРА (с фильтрацией)
        "require_quality_filter": True,
        "pm25_sensor_distance_km": 0.01,
        "nearest_sensor": "US Embassy Bishkek",
        "visual_quality_score": 7,  # Хорошо, но много близких зданий
        "description": "Поворотная камера с фильтрацией (~75% кадров полезные). Датчик в 10 м - отлично. Визуально: горы вдали видны, но много близких зданий в кадре. Приемлемо для ML."
    }
}


def get_recommended_cameras():
    """Возвращает список рекомендуемых камер для проекта"""
    return {k: v for k, v in CAMERAS.items() if v["recommended"]}


def get_camera_by_id(camera_id):
    """Получить данные камеры по ID"""
    return CAMERAS.get(camera_id)


def list_all_cameras():
    """Вывести список всех камер"""
    print("Доступные камеры:")
    print("=" * 80)
    for camera_id, info in CAMERAS.items():
        status = "✅ Рекомендуется" if info["recommended"] else "⚠️  Не рекомендуется"
        coords = f"{info['coordinates']}" if info['coordinates'] else "Неизвестно"
        filter_required = "🔍 Фильтрация" if info.get("require_quality_filter", False) else "Нет"
        print(f"\n[{camera_id}]")
        print(f"  Название: {info['name']}")
        print(f"  Координаты: {coords}")
        print(f"  Направление: {info.get('viewing_direction', 'N/A')}")
        print(f"  Угол обзора: {info.get('viewing_angle', 'N/A')}")
        print(f"  URL: {info['url']}")
        print(f"  Статус: {status}")
        print(f"  Фильтрация: {filter_required}")
        print(f"  Описание: {info['description']}")
    print("=" * 80)


if __name__ == "__main__":
    list_all_cameras()
    print(f"\nВсего камер: {len(CAMERAS)}")
    print(f"Рекомендуется использовать: {len(get_recommended_cameras())}")
