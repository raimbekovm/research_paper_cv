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
        "recommended": True,
        "require_quality_filter": False,
        "description": "Вид на восток вдоль дороги, здания вдали"
    },
    "bishkek_panorama": {
        "name": "Бишкек Панорама",
        "url": "https://stream.kt.kg:5443/live/camera28.m3u8",
        "coordinates": (42.799197, 74.645485),
        "viewing_direction": "~330° NW",
        "viewing_angle": "panoramic-wide",
        "recommended": True,
        "require_quality_filter": False,
        "description": "Панорамный вид на весь город, очень широкий угол обзора"
    },
    "sovmin": {
        "name": "Бишкек Совмин",
        "url": "https://stream.kt.kg:5443/live/camera33.m3u8",
        "coordinates": (42.804394, 74.587977),
        "viewing_direction": "~45° NE",
        "viewing_angle": "elevated-wide",
        "recommended": True,
        "require_quality_filter": False,
        "description": "Вид на северо-восток на жилые районы, высокая точка съёмки"
    },
    "kt_center": {
        "name": "Кыргызтелеком Центр",
        "url": "https://stream.kt.kg:5443/live/camera35.m3u8",
        "coordinates": (42.874689, 74.612241),
        "viewing_direction": "variable (rotating)",
        "viewing_angle": "rotating",
        "recommended": True,
        "require_quality_filter": True,
        "description": "Поворотная камера, меняет направление (требует фильтрацию ~75% кадров полезные)"
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
