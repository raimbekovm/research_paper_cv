"""
Скрипт для извлечения кадров из HLS-потоков камер Бишкека
Использует OpenCV для захвата кадров из .m3u8 потоков
"""

import cv2
import os
from datetime import datetime
import time


class CameraFrameCapture:
    """Класс для захвата кадров с онлайн-камер"""

    def __init__(self, stream_url, camera_name, output_dir="data/images"):
        """
        Args:
            stream_url: URL HLS-потока (.m3u8)
            camera_name: Название камеры для именования файлов
            output_dir: Директория для сохранения изображений
        """
        self.stream_url = stream_url
        self.camera_name = camera_name
        self.output_dir = output_dir

        # Создаём директорию если её нет
        os.makedirs(output_dir, exist_ok=True)

    def capture_frame(self, save=True):
        """
        Захватывает один кадр из видеопотока

        Returns:
            tuple: (success, frame, timestamp, filename)
        """
        try:
            # Открываем видеопоток
            cap = cv2.VideoCapture(self.stream_url)

            if not cap.isOpened():
                print(f"❌ Не удалось открыть поток: {self.stream_url}")
                return False, None, None, None

            # Читаем кадр
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                print(f"❌ Не удалось захватить кадр")
                return False, None, None, None

            # Генерируем timestamp и имя файла
            timestamp = datetime.now()
            filename = f"{self.camera_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(self.output_dir, filename)

            if save:
                # Сохраняем изображение
                cv2.imwrite(filepath, frame)
                print(f"✅ Кадр сохранён: {filepath}")
                print(f"   Размер: {frame.shape[1]}x{frame.shape[0]}")
                print(f"   Время: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            return True, frame, timestamp, filepath

        except Exception as e:
            print(f"❌ Ошибка при захвате кадра: {e}")
            return False, None, None, None

    def capture_continuous(self, interval_minutes=60, duration_hours=None):
        """
        Непрерывный захват кадров с заданным интервалом

        Args:
            interval_minutes: Интервал между кадрами в минутах
            duration_hours: Длительность сбора в часах (None = бесконечно)
        """
        print(f"🎥 Начинаем захват кадров с камеры: {self.camera_name}")
        print(f"📍 Интервал: {interval_minutes} минут")
        if duration_hours:
            print(f"⏱️  Длительность: {duration_hours} часов")
        print(f"💾 Сохранение в: {self.output_dir}")
        print("-" * 60)

        start_time = time.time()
        frame_count = 0

        while True:
            # Захватываем кадр
            success, _, timestamp, filepath = self.capture_frame()

            if success:
                frame_count += 1
                print(f"📊 Всего кадров: {frame_count}")

            # Проверяем длительность
            if duration_hours:
                elapsed_hours = (time.time() - start_time) / 3600
                if elapsed_hours >= duration_hours:
                    print(f"\n✅ Завершено! Собрано {frame_count} кадров за {duration_hours} часов")
                    break

            # Ждём до следующего захвата
            print(f"⏳ Следующий кадр через {interval_minutes} минут...")
            print("-" * 60)
            time.sleep(interval_minutes * 60)


def test_camera(stream_url, camera_name):
    """Тестирование захвата одного кадра"""
    print(f"🧪 Тестирование камеры: {camera_name}")
    print(f"🔗 URL: {stream_url}")
    print("-" * 60)

    capture = CameraFrameCapture(stream_url, camera_name, output_dir="data/test_images")
    success, frame, timestamp, filepath = capture.capture_frame()

    if success:
        print("\n✅ Тест успешен! Камера работает корректно.")
        return True
    else:
        print("\n❌ Тест не пройден. Проверьте URL потока.")
        return False


if __name__ == "__main__":
    # Тестирование камеры Площадь Ала-Тоо
    CAMERA_URL = "https://stream.kt.kg:5443/live/camera25.m3u8"
    CAMERA_NAME = "ala_too_square"

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАХВАТА КАДРОВ С КАМЕРЫ")
    print("=" * 60)
    print()

    # Сначала тестируем захват одного кадра
    if test_camera(CAMERA_URL, CAMERA_NAME):
        print("\n" + "=" * 60)
        print("Хотите начать непрерывный сбор данных?")
        print("Раскомментируйте следующие строки и запустите скрипт снова:")
        print()
        print("# capture = CameraFrameCapture(CAMERA_URL, CAMERA_NAME)")
        print("# capture.capture_continuous(interval_minutes=60, duration_hours=24)")
        print("=" * 60)

        # Раскомментируйте для непрерывного сбора:
        # capture = CameraFrameCapture(CAMERA_URL, CAMERA_NAME)
        # capture.capture_continuous(interval_minutes=60, duration_hours=24)
