"""
Автоматический сбор данных со всех камер Бишкека
Использует многопоточность для одновременного захвата кадров
"""

import cv2
import os
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from camera_config import CAMERAS, get_recommended_cameras


class MultiCameraCapture:
    """Класс для одновременного захвата кадров с нескольких камер"""

    def __init__(self, cameras, output_dir="data/images"):
        """
        Args:
            cameras: dict с данными камер из camera_config.py
            output_dir: Базовая директория для сохранения изображений
        """
        self.cameras = cameras
        self.output_dir = output_dir

        # Создаём директории для каждой камеры
        for camera_id in cameras.keys():
            camera_dir = os.path.join(output_dir, camera_id)
            os.makedirs(camera_dir, exist_ok=True)

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

            # Формируем путь к файлу
            timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"{camera_id}_{timestamp_str}.jpg"
            camera_dir = os.path.join(self.output_dir, camera_id)
            filepath = os.path.join(camera_dir, filename)

            # Сохраняем изображение
            cv2.imwrite(filepath, frame)

            return {
                "camera_id": camera_id,
                "camera_name": camera_info["name"],
                "success": True,
                "filepath": filepath,
                "timestamp": timestamp,
                "resolution": (frame.shape[1], frame.shape[0]),
                "coordinates": camera_info["coordinates"]
            }

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
                else:
                    print(f"❌ {result['camera_id']}")
                    print(f"   Ошибка: {result['error']}")

        print("-" * 80)
        successful = sum(1 for r in results if r["success"])
        print(f"📊 Результат: {successful}/{len(results)} камер успешно")

        return results

    def collect_continuous(self, interval_minutes=60, duration_hours=None):
        """
        Непрерывный сбор данных с заданным интервалом

        Args:
            interval_minutes: Интервал между сборами в минутах
            duration_hours: Длительность сбора в часах (None = бесконечно)
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
        print("=" * 80)
        print()

        start_time = time.time()
        collection_count = 0

        try:
            while True:
                collection_count += 1
                print(f"\n{'='*80}")
                print(f"📸 Сбор #{collection_count}")
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
                        break

                # Ждём до следующего сбора
                print(f"\n⏳ Следующий сбор через {interval_minutes} минут...")
                print(f"⏰ Следующий сбор: {datetime.fromtimestamp(time.time() + interval_minutes * 60).strftime('%H:%M:%S')}")
                print("=" * 80)
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Сбор остановлен пользователем")
            print(f"📊 Всего сборов: {collection_count}")

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

    args = parser.parse_args()

    # Выбираем камеры
    if args.all_cameras:
        cameras = CAMERAS
        print("⚠️  Используются ВСЕ камеры (включая поворотную)")
    else:
        cameras = get_recommended_cameras()
        print("✅ Используются только рекомендованные камеры")

    # Создаём объект для сбора
    collector = MultiCameraCapture(cameras, output_dir=args.output)

    if args.mode == 'test':
        print("\n🧪 РЕЖИМ ТЕСТИРОВАНИЯ\n")
        collector.capture_all_cameras()
    else:
        collector.collect_continuous(
            interval_minutes=args.interval,
            duration_hours=args.duration
        )


if __name__ == "__main__":
    main()
