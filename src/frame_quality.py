"""
Модуль для оценки качества кадров с камер
Используется для фильтрации бесполезных кадров (размытых, слишком тёмных, без неба и т.д.)
"""

import cv2
import numpy as np


class FrameQualityFilter:
    """Фильтр для оценки качества кадров"""

    def __init__(
        self,
        min_brightness=50,
        max_brightness=250,
        min_contrast=30,
        min_sharpness=50,
        min_sky_ratio=0.3
    ):
        """
        Args:
            min_brightness: Минимальная яркость (0-255)
            max_brightness: Максимальная яркость (0-255)
            min_contrast: Минимальный контраст (стандартное отклонение)
            min_sharpness: Минимальная резкость (Laplacian variance)
            min_sky_ratio: Минимальная доля неба в верхней трети (0-1)
        """
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast
        self.min_sharpness = min_sharpness
        self.min_sky_ratio = min_sky_ratio

    def analyze_frame(self, frame):
        """
        Анализирует кадр и возвращает метрики качества

        Args:
            frame: numpy array (BGR изображение)

        Returns:
            dict: метрики качества и решение о полезности
        """
        # Конвертируем в grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Яркость (средняя яркость)
        brightness = float(np.mean(gray))

        # 2. Контраст (стандартное отклонение яркости)
        contrast = float(np.std(gray))

        # 3. Резкость (Laplacian variance - детектирует размытость)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = float(laplacian_var)

        # 4. Детектирование неба (верхняя треть изображения)
        height, width = gray.shape
        top_third = gray[:height//3, :]
        # Небо обычно яркое (> 100)
        sky_pixels = np.sum(top_third > 100)
        sky_ratio = float(sky_pixels / top_third.size)

        # 5. Оценка полезности кадра
        is_useful = self.is_frame_useful(brightness, contrast, sharpness, sky_ratio)

        return {
            "brightness": brightness,
            "contrast": contrast,
            "sharpness": sharpness,
            "sky_ratio": sky_ratio,
            "is_useful": is_useful,
            "reason": self._get_rejection_reason(brightness, contrast, sharpness, sky_ratio)
        }

    def is_frame_useful(self, brightness, contrast, sharpness, sky_ratio):
        """
        Определяет полезность кадра по метрикам

        Returns:
            bool: True если кадр полезный
        """
        return (
            self.min_brightness <= brightness <= self.max_brightness and
            contrast >= self.min_contrast and
            sharpness >= self.min_sharpness and
            sky_ratio >= self.min_sky_ratio
        )

    def _get_rejection_reason(self, brightness, contrast, sharpness, sky_ratio):
        """Возвращает причину отклонения кадра (если отклонён)"""
        if brightness < self.min_brightness:
            return f"Слишком тёмный ({brightness:.0f} < {self.min_brightness})"
        elif brightness > self.max_brightness:
            return f"Слишком светлый ({brightness:.0f} > {self.max_brightness})"
        elif contrast < self.min_contrast:
            return f"Низкий контраст ({contrast:.0f} < {self.min_contrast})"
        elif sharpness < self.min_sharpness:
            return f"Размытый/движение ({sharpness:.0f} < {self.min_sharpness})"
        elif sky_ratio < self.min_sky_ratio:
            return f"Мало неба ({sky_ratio:.1%} < {self.min_sky_ratio:.0%})"
        else:
            return "OK"

    def filter_frame(self, frame):
        """
        Проверяет кадр и возвращает результат фильтрации

        Args:
            frame: numpy array (BGR изображение)

        Returns:
            tuple: (is_useful, metrics)
        """
        metrics = self.analyze_frame(frame)
        return metrics["is_useful"], metrics


# Предустановленные фильтры для разных сценариев

def get_default_filter():
    """Стандартный фильтр (средняя строгость)"""
    return FrameQualityFilter(
        min_brightness=50,
        max_brightness=250,
        min_contrast=30,
        min_sharpness=50,
        min_sky_ratio=0.3
    )


def get_strict_filter():
    """Строгий фильтр (высокое качество)"""
    return FrameQualityFilter(
        min_brightness=60,
        max_brightness=240,
        min_contrast=40,
        min_sharpness=100,
        min_sky_ratio=0.4
    )


def get_lenient_filter():
    """Мягкий фильтр (максимальное количество кадров)"""
    return FrameQualityFilter(
        min_brightness=40,
        max_brightness=255,
        min_contrast=20,
        min_sharpness=30,
        min_sky_ratio=0.2
    )


def test_filter():
    """Тестирование фильтра на примере"""
    import os

    # Ищем тестовые изображения
    test_dir = "data/camera_analysis/rotating_camera"
    if not os.path.exists(test_dir):
        print("⚠️  Нет тестовых изображений. Запустите сначала analyze_rotating_camera.py")
        return

    filter = get_default_filter()

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ФИЛЬТРА КАЧЕСТВА КАДРОВ")
    print("=" * 80)
    print(f"\nПараметры фильтра:")
    print(f"  Яркость: {filter.min_brightness}-{filter.max_brightness}")
    print(f"  Контраст: >= {filter.min_contrast}")
    print(f"  Резкость: >= {filter.min_sharpness}")
    print(f"  Небо: >= {filter.min_sky_ratio:.0%}")
    print("\n" + "=" * 80)

    # Анализируем все изображения
    useful_count = 0
    total_count = 0

    for filename in sorted(os.listdir(test_dir)):
        if not filename.endswith('.jpg'):
            continue

        filepath = os.path.join(test_dir, filename)
        frame = cv2.imread(filepath)

        if frame is None:
            continue

        is_useful, metrics = filter.filter_frame(frame)
        total_count += 1

        if is_useful:
            useful_count += 1
            status = "🟢 ПОЛЕЗНЫЙ"
        else:
            status = "🔴 ОТКЛОНЁН"

        print(f"\n{filename}")
        print(f"  {status}")
        print(f"  Яркость: {metrics['brightness']:.0f}")
        print(f"  Контраст: {metrics['contrast']:.0f}")
        print(f"  Резкость: {metrics['sharpness']:.0f}")
        print(f"  Небо: {metrics['sky_ratio']:.1%}")
        print(f"  Причина: {metrics['reason']}")

    print("\n" + "=" * 80)
    print(f"РЕЗУЛЬТАТ: {useful_count}/{total_count} кадров прошли фильтр ({useful_count/total_count*100:.0f}%)")
    print("=" * 80)


if __name__ == "__main__":
    test_filter()
