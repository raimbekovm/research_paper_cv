"""
Скрипт для проверки feasibility проекта PM2.5 estimation
КРИТИЧНО: Проверяет можно ли вообще делать этот проект!
"""

import json
from pathlib import Path


def check_sensor_camera_distances():
    """
    Проверяет расстояния между камерами и датчиками

    Returns:
        bool: True если проект feasible, False если нет
    """
    print("=" * 80)
    print("🔍 FEASIBILITY CHECK: РАССТОЯНИЯ КАМЕРА-ДАТЧИК")
    print("=" * 80)

    # Загружаем данные о датчиках
    sensor_file = Path("data/sensor_locations.json")

    if not sensor_file.exists():
        print("\n❌ FATAL: Файл sensor_locations.json не найден!")
        print("   Запустите: python src/find_sensors.py")
        return False

    with open(sensor_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recommendations = data.get("recommendations", {})

    if not recommendations:
        print("\n❌ FATAL: Нет рекомендаций по парам камера-датчик!")
        return False

    # Подсчёт
    viable_cameras = []
    problematic_cameras = []

    for camera_id, rec in recommendations.items():
        dist = rec["distance_km"]
        use = rec["use_for_paper"]

        if use:
            viable_cameras.append((camera_id, rec["sensor"], dist))
        else:
            problematic_cameras.append((camera_id, rec["sensor"], dist))

    # Результаты
    print(f"\n✅ Пригодные камеры ({len(viable_cameras)}):")
    for cam, sensor, dist in viable_cameras:
        print(f"   • {cam} → {sensor}: {dist:.2f} км")

    if problematic_cameras:
        print(f"\n🔴 Проблемные камеры ({len(problematic_cameras)}):")
        for cam, sensor, dist in problematic_cameras:
            print(f"   • {cam} → {sensor}: {dist:.2f} км (слишком далеко)")

    # Оценка
    print("\n" + "=" * 80)
    print("📊 ОЦЕНКА FEASIBILITY")
    print("=" * 80)

    total = len(viable_cameras) + len(problematic_cameras)

    if len(viable_cameras) == 0:
        print("\n🔴 ПРОЕКТ НЕ FEASIBLE!")
        print("   Причина: Нет камер с близкими датчиками PM2.5")
        print("   Рекомендация: Искать другие датчики или другой город")
        return False

    elif len(viable_cameras) == 1:
        print("\n🟡 ПРОЕКТ КРАЙНЕ ОГРАНИЧЕН")
        print("   Причина: Только 1 камера с близким датчиком")
        print("   Последствия:")
        print("   - Нет возможности для cross-camera validation")
        print("   - Очень малый датасет")
        print("   - Высокий риск overfitting на одну камеру")
        print("\n   Рекомендация: Продолжать с осторожностью")
        print("   ОБЯЗАТЕЛЬНО описать это как major limitation в статье!")
        return True

    elif len(viable_cameras) == 2:
        print("\n🟡 ПРОЕКТ FEASIBLE С ОГРАНИЧЕНИЯМИ")
        print("   Причина: 2 камеры с близкими датчиками")
        print("   Возможности:")
        print("   ✅ Можно делать baseline модель")
        print("   ✅ Можно собрать датасет")
        print("   ⚠️  Ограниченная валидация")
        print("   ⚠️  Нельзя делать полноценный cross-camera test")
        print("\n   Рекомендация: Продолжать проект")
        print("   Описать spatial limitations в статье")
        return True

    else:  # 3+ камеры
        print("\n✅ ПРОЕКТ FEASIBLE")
        print("   Причина: 3+ камер с близкими датчиками")
        print("   Возможности:")
        print("   ✅ Полноценный датасет")
        print("   ✅ Cross-camera validation")
        print("   ✅ Spatial diversity")
        print("\n   Рекомендация: Можно начинать сбор данных")
        return True


def estimate_required_data():
    """Оценивает сколько данных нужно собрать"""
    print("\n" + "=" * 80)
    print("📈 ОЦЕНКА НЕОБХОДИМОГО ДАТАСЕТА")
    print("=" * 80)

    # Минимальные требования для ML
    min_samples_per_camera = 500  # Минимум для обучения с transfer learning
    recommended_samples_per_camera = 1500  # Рекомендуется
    ideal_samples_per_camera = 3000  # Идеально

    # Загружаем данные
    sensor_file = Path("data/sensor_locations.json")
    if sensor_file.exists():
        with open(sensor_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        viable_count = sum(1 for r in data.get("recommendations", {}).values() if r["use_for_paper"])
    else:
        viable_count = 2  # Предполагаем 2 камеры

    print(f"\nКоличество пригодных камер: {viable_count}")
    print(f"\nСбор данных (1 кадр/час, только светлое время 8:00-18:00 = 10 часов/день):")
    print()

    # Расчёты
    hours_per_day = 10
    days_for_min = min_samples_per_camera / hours_per_day
    days_for_rec = recommended_samples_per_camera / hours_per_day
    days_for_ideal = ideal_samples_per_camera / hours_per_day

    print(f"Минимальный датасет ({min_samples_per_camera} кадров/камеру):")
    print(f"  → {days_for_min:.0f} дней ({days_for_min/30:.1f} месяца)")
    print(f"  → Всего кадров: {min_samples_per_camera * viable_count}")
    print()

    print(f"Рекомендуемый датасет ({recommended_samples_per_camera} кадров/камеру):")
    print(f"  → {days_for_rec:.0f} дней ({days_for_rec/30:.1f} месяца)")
    print(f"  → Всего кадров: {recommended_samples_per_camera * viable_count}")
    print()

    print(f"Идеальный датасет ({ideal_samples_per_camera} кадров/камеру):")
    print(f"  → {days_for_ideal:.0f} дней ({days_for_ideal/30:.1f} месяца)")
    print(f"  → Всего кадров: {ideal_samples_per_camera * viable_count}")
    print()

    print("⚠️  КРИТИЧНО:")
    print("  - Нужно собирать данные в разные сезоны (зима/лето)")
    print("  - Зимой в Бишкеке высокий PM2.5 (смог от отопления)")
    print("  - Летом низкий PM2.5 (чистый воздух)")
    print("  - Модель должна работать на обоих режимах!")
    print()
    print("  Рекомендация: Собирать минимум 3 месяца (включая зиму)")


def check_ml_prerequisites():
    """Проверяет что есть всё для ML разработки"""
    print("\n" + "=" * 80)
    print("🔧 ПРОВЕРКА ML ИНФРАСТРУКТУРЫ")
    print("=" * 80)

    # Проверяем Python packages
    required_packages = [
        "torch",
        "torchvision",
        "numpy",
        "pandas",
        "scikit-learn",
        "matplotlib",
        "opencv-python"
    ]

    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg}")
            missing.append(pkg)

    if missing:
        print(f"\n⚠️  Отсутствуют пакеты: {', '.join(missing)}")
        print("   Установите: pip install " + " ".join(missing))
    else:
        print("\n✅ Все необходимые пакеты установлены")

    return len(missing) == 0


def main():
    print("=" * 80)
    print("🎯 FEASIBILITY CHECK: PM2.5 ESTIMATION PROJECT")
    print("=" * 80)
    print()

    # 1. Проверка расстояний
    feasible = check_sensor_camera_distances()

    # 2. Оценка датасета
    estimate_required_data()

    # 3. Проверка ML инфраструктуры
    ml_ready = check_ml_prerequisites()

    # Финальная оценка
    print("\n" + "=" * 80)
    print("🎯 ФИНАЛЬНАЯ ОЦЕНКА")
    print("=" * 80)

    if feasible and ml_ready:
        print("\n✅ ПРОЕКТ МОЖНО НАЧИНАТЬ")
        print("\nСледующие шаги:")
        print("1. Получить API ключи (IQAir, OpenWeatherMap)")
        print("2. Запустить автоматический сбор данных")
        print("3. Собрать минимум 3 месяца данных")
        print("4. Начать разработку baseline модели (метео → PM2.5)")
        print("5. Разработать multimodal модель (изображение + метео)")

    elif feasible and not ml_ready:
        print("\n🟡 ПРОЕКТ FEASIBLE, НО НУЖНА ПОДГОТОВКА")
        print("\nУстановите необходимые ML библиотеки")

    else:
        print("\n🔴 ПРОЕКТ НЕ МОЖЕТ БЫТЬ РЕАЛИЗОВАН")
        print("\nПричина: Нет камер с близкими датчиками PM2.5")
        print("Рекомендация: Искать другие источники данных или другой город")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
