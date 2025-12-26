"""
Конфигурация камер для проекта PM2.5 estimation
"""

CAMERAS = {
    "ala_too_square": {
        "name": "Бишкек площадь Ала-Тоо",
        "url": "https://stream.kt.kg:5443/live/camera25.m3u8",
        "coordinates": (42.875576, 74.603629),
        "recommended": True,
        "require_quality_filter": False,
        "description": "Панорамный вид на площадь Ала-Тоо"
    },
    "ala_too_square_2": {
        "name": "Площадь Ала-Тоо (камера 2)",
        "url": "https://stream.kt.kg:5443/live/camera27.m3u8",
        "coordinates": (42.875767, 74.604619),
        "recommended": True,
        "require_quality_filter": False,
        "description": "Альтернативный ракурс площади Ала-Тоо"
    },
    "bishkek_panorama": {
        "name": "Бишкек Панорама",
        "url": "https://stream.kt.kg:5443/live/camera28.m3u8",
        "coordinates": None,  # Координаты требуют уточнения
        "recommended": True,
        "require_quality_filter": False,
        "description": "Панорамный вид на город"
    },
    "sovmin": {
        "name": "Бишкек Совмин",
        "url": "https://stream.kt.kg:5443/live/camera33.m3u8",
        "coordinates": (42.804394, 74.587977),
        "recommended": True,
        "require_quality_filter": False,
        "description": "Вид на район Совмина"
    },
    "kt_center": {
        "name": "Кыргызтелеком Центр",
        "url": "https://stream.kt.kg:5443/live/camera35.m3u8",
        "coordinates": (42.874689, 74.612241),
        "recommended": True,
        "require_quality_filter": True,
        "description": "Поворотная камера (требует фильтрацию ~75% кадров полезные)"
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
        print(f"  URL: {info['url']}")
        print(f"  Статус: {status}")
        print(f"  Фильтрация: {filter_required}")
        print(f"  Описание: {info['description']}")
    print("=" * 80)


if __name__ == "__main__":
    list_all_cameras()
    print(f"\nВсего камер: {len(CAMERAS)}")
    print(f"Рекомендуется использовать: {len(get_recommended_cameras())}")
