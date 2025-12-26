"""
Автоматический сбор данных со всех камер Бишкека
Использует многопоточность для одновременного захвата кадров
ВАЖНО: Собирает только в дневное время (визуальные признаки PM2.5 видны только днём)
"""

import cv2
import os
from datetime import datetime, time as dt_time
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from camera_config import CAMERAS, get_recommended_cameras
from frame_quality import get_default_filter


class MultiCameraCapture:
    """Класс для одновременного захвата кадров с нескольких камер"""

    def __init__(self, cameras, output_dir="data/images", daylight_start=8, daylight_end=18):
        """
        Args:
            cameras: dict с данными камер из camera_config.py
            output_dir: Базовая директория для сохранения изображений
            daylight_start: Начало светового дня (час, 0-23)
            daylight_end: Конец светового дня (час, 0-23)
        """
        self.cameras = cameras
        self.output_dir = output_dir
        self.daylight_start = daylight_start
        self.daylight_end = daylight_end

        # Фильтр качества для поворотных камер
        self.quality_filter = get_default_filter()

        # Создаём директории для каждой камеры
        for camera_id in cameras.keys():
            camera_dir = os.path.join(output_dir, camera_id)
            os.makedirs(camera_dir, exist_ok=True)

    def is_daylight(self):
        """
        Проверяет, является ли текущее время дневным

        Returns:
            bool: True если сейчас день, False если ночь
        """
        current_hour = datetime.now().hour
        return self.daylight_start <= current_hour < self.daylight_end

    def capture_single_camera(self, camera_id, camera_info, timestamp):
        """
        Захват кадра с одной камеры

        Returns:
            dict: результат захвата с метаданными
        """
        try:
            # Открываем видеопоток
            cap = cv2.VideoCapture(camera_info["url"])

            if not cap.isOpened():
                return {
                    "camera_id": camera_id,
                    "success": False,
                    "error": "Не удалось открыть поток"
                }

            # Читаем кадр
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return {
                    "camera_id": camera_id,
                    "success": False,
                    "error": "Не удалось захватить кадр"
                }

            # Проверяем качество кадра (для камер с фильтрацией)
            quality_metrics = None
            if camera_info.get("require_quality_filter", False):
                is_useful, quality_metrics = self.quality_filter.filter_frame(frame)
                if not is_useful:
                    return {
                        "camera_id": camera_id,
                        "success": False,
                        "error": f"Кадр отклонён фильтром: {quality_metrics['reason']}",
                        "filtered": True,
                        "quality_metrics": quality_metrics
                    }

            # Формируем путь к файлу
            timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"{camera_id}_{timestamp_str}.jpg"
            camera_dir = os.path.join(self.output_dir, camera_id)
            filepath = os.path.join(camera_dir, filename)

            # Сохраняем изображение
            cv2.imwrite(filepath, frame)

            result = {
                "camera_id": camera_id,
                "camera_name": camera_info["name"],
                "success": True,
                "filepath": filepath,
                "timestamp": timestamp,
                "resolution": (frame.shape[1], frame.shape[0]),
                "coordinates": camera_info["coordinates"],
                "filtered": False
            }

            # Добавляем метрики качества если камера использует фильтрацию
            if quality_metrics:
                result["quality_metrics"] = quality_metrics

            return result

        except Exception as e:
            return {
                "camera_id": camera_id,
                "success": False,
                "error": str(e)
            }

    def capture_all_cameras(self, max_workers=5):
        """
        Одновременный захват кадров со всех камер

        Args:
            max_workers: Максимальное количество потоков

        Returns:
            list: список результатов для каждой камеры
        """
        timestamp = datetime.now()
        results = []

        print(f"🎥 Начинаем захват кадров...")
        print(f"⏰ Время: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📹 Количество камер: {len(self.cameras)}")
        print("-" * 80)

        # Используем ThreadPoolExecutor для параллельного захвата
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем захват для каждой камеры
            future_to_camera = {
                executor.submit(self.capture_single_camera, camera_id, camera_info, timestamp): camera_id
                for camera_id, camera_info in self.cameras.items()
            }

            # Собираем результаты по мере готовности
            for future in as_completed(future_to_camera):
                result = future.result()
                results.append(result)

                # Выводим результат
                if result["success"]:
                    print(f"✅ {result['camera_name']}")
                    print(f"   Файл: {result['filepath']}")
                    print(f"   Разрешение: {result['resolution'][0]}x{result['resolution'][1]}")
                    # Показываем метрики качества если есть
                    if "quality_metrics" in result:
                        qm = result["quality_metrics"]
                        print(f"   Качество: яркость={qm['brightness']:.0f}, контраст={qm['contrast']:.0f}, резкость={qm['sharpness']:.0f}")
                else:
                    # Отфильтрованный кадр vs ошибка
                    if result.get("filtered", False):
                        print(f"🔍 {result['camera_id']} - кадр отфильтрован")
                        print(f"   Причина: {result['error'].split(': ')[1]}")
                    else:
                        print(f"❌ {result['camera_id']}")
                        print(f"   Ошибка: {result['error']}")

        print("-" * 80)
        successful = sum(1 for r in results if r["success"])
        filtered = sum(1 for r in results if r.get("filtered", False))
        print(f"📊 Результат: {successful}/{len(results)} камер успешно", end="")
        if filtered > 0:
            print(f" (🔍 отфильтровано: {filtered})")
        else:
            print()

        return results

    def collect_continuous(self, interval_minutes=60, duration_hours=None, skip_night=True):
        """
        Непрерывный сбор данных с заданным интервалом

        Args:
            interval_minutes: Интервал между сборами в минутах
            duration_hours: Длительность сбора в часах (None = бесконечно)
            skip_night: Пропускать ночное время (рекомендуется True)
        """
        print("=" * 80)
        print("🚀 АВТОМАТИЧЕСКИЙ СБОР ДАННЫХ")
        print("=" * 80)
        print(f"📹 Камер: {len(self.cameras)}")
        print(f"⏱️  Интервал: {interval_minutes} минут")
        if duration_hours:
            print(f"⏰ Длительность: {duration_hours} часов")
        else:
            print(f"⏰ Длительность: бесконечно (Ctrl+C для остановки)")
        print(f"💾 Директория: {self.output_dir}")

        if skip_night:
            print(f"☀️  Дневной режим: {self.daylight_start}:00 - {self.daylight_end}:00")
            print(f"🌙 Ночное время: пропускается (нет визуальных признаков PM2.5)")
        else:
            print(f"⚠️  Режим 24/7: сбор днём и ночью")

        print("=" * 80)
        print()

        start_time = time.time()
        collection_count = 0
        skipped_count = 0

        try:
            while True:
                # Проверяем, светлое ли время суток
                if skip_night and not self.is_daylight():
                    current_time = datetime.now()

                    # Вычисляем время до следующего рассвета
                    next_daylight_hour = self.daylight_start
                    if current_time.hour >= self.daylight_end:
                        # Если уже вечер, ждём до утра
                        hours_until_daylight = (24 - current_time.hour) + next_daylight_hour
                    else:
                        # Если раннее утро
                        hours_until_daylight = next_daylight_hour - current_time.hour

                    print(f"\n🌙 Сейчас {current_time.strftime('%H:%M')} - ночное время")
                    print(f"💤 Пропускаем сбор (визуальные признаки не видны)")
                    print(f"⏰ Следующий сбор в ~{next_daylight_hour}:00")
                    print(f"⏳ Ожидание ~{hours_until_daylight} часов...")

                    skipped_count += 1

                    # Спим до следующего интервала
                    time.sleep(interval_minutes * 60)
                    continue

                collection_count += 1
                print(f"\n{'='*80}")
                print(f"📸 Сбор #{collection_count} (☀️  Дневное время)")
                print(f"{'='*80}")

                # Захватываем кадры со всех камер
                results = self.capture_all_cameras()

                # Сохраняем метаданные
                self._save_metadata(results, collection_count)

                # Проверяем длительность
                if duration_hours:
                    elapsed_hours = (time.time() - start_time) / 3600
                    if elapsed_hours >= duration_hours:
                        print(f"\n✅ Сбор завершён! Всего сборов: {collection_count}")
                        if skip_night:
                            print(f"🌙 Пропущено ночных интервалов: {skipped_count}")
                        break

                # Ждём до следующего сбора
                next_collection_time = datetime.fromtimestamp(time.time() + interval_minutes * 60)
                print(f"\n⏳ Следующий сбор через {interval_minutes} минут...")
                print(f"⏰ Следующий сбор: {next_collection_time.strftime('%H:%M:%S')}")
                print("=" * 80)
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Сбор остановлен пользователем")
            print(f"📊 Всего сборов: {collection_count}")
            if skip_night:
                print(f"🌙 Пропущено ночных интервалов: {skipped_count}")

    def _save_metadata(self, results, collection_count):
        """Сохранение метаданных сбора"""
        metadata_dir = os.path.join(self.output_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_file = os.path.join(metadata_dir, f"collection_{timestamp}.txt")

        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"Сбор #{collection_count}\n")
            f.write(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Камер: {len(results)}\n")
            f.write(f"Успешно: {sum(1 for r in results if r['success'])}\n")
            f.write("\nРезультаты:\n")
            for result in results:
                f.write(f"\n{result['camera_id']}:\n")
                if result['success']:
                    f.write(f"  Файл: {result['filepath']}\n")
                    f.write(f"  Координаты: {result['coordinates']}\n")
                else:
                    f.write(f"  Ошибка: {result['error']}\n")


def main():
    parser = argparse.ArgumentParser(description='Сбор данных с камер Бишкека')
    parser.add_argument('--mode', choices=['test', 'continuous'], default='test',
                        help='Режим работы: test (один снимок) или continuous (непрерывно)')
    parser.add_argument('--interval', type=int, default=60,
                        help='Интервал между снимками в минутах (default: 60)')
    parser.add_argument('--duration', type=int, default=None,
                        help='Длительность сбора в часах (default: бесконечно)')
    parser.add_argument('--all-cameras', action='store_true',
                        help='Использовать ВСЕ камеры (включая нерекомендованные)')
    parser.add_argument('--output', type=str, default='data/images',
                        help='Директория для сохранения (default: data/images)')
    parser.add_argument('--daylight-start', type=int, default=8,
                        help='Начало светового дня, час (default: 8)')
    parser.add_argument('--daylight-end', type=int, default=18,
                        help='Конец светового дня, час (default: 18)')
    parser.add_argument('--24-7', action='store_true',
                        help='Собирать данные 24/7 (включая ночь, не рекомендуется)')

    args = parser.parse_args()

    # Выбираем камеры
    if args.all_cameras:
        cameras = CAMERAS
        print("⚠️  Используются ВСЕ камеры (включая поворотную)")
    else:
        cameras = get_recommended_cameras()
        print("✅ Используются только рекомендованные камеры")

    # Создаём объект для сбора
    collector = MultiCameraCapture(
        cameras,
        output_dir=args.output,
        daylight_start=args.daylight_start,
        daylight_end=args.daylight_end
    )

    if args.mode == 'test':
        print("\n🧪 РЕЖИМ ТЕСТИРОВАНИЯ\n")
        collector.capture_all_cameras()
    else:
        skip_night = not args.__dict__.get('24_7', False)
        collector.collect_continuous(
            interval_minutes=args.interval,
            duration_hours=args.duration,
            skip_night=skip_night
        )


if __name__ == "__main__":
    main()
