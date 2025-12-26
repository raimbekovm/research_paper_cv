"""
Скрипт для анализа поворотной камеры (camera35)
Цель: определить паттерн поворота и выделить полезные ракурсы
"""

import cv2
import numpy as np
import os
from datetime import datetime
import time


def capture_sequence(stream_url, num_frames=20, interval_seconds=10, output_dir="data/camera_analysis"):
    """
    Захватывает последовательность кадров с интервалом

    Args:
        stream_url: URL потока камеры
        num_frames: Количество кадров для захвата
        interval_seconds: Интервал между кадрами в секундах
        output_dir: Директория для сохранения
    """
    os.makedirs(output_dir, exist_ok=True)

    frames_data = []

    print(f"🎥 Анализ поворотной камеры")
    print(f"📊 Захват {num_frames} кадров с интервалом {interval_seconds} секунд")
    print(f"⏱️  Общее время: ~{num_frames * interval_seconds / 60:.1f} минут")
    print("=" * 80)

    for i in range(num_frames):
        timestamp = datetime.now()

        try:
            # Захватываем кадр
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                print(f"❌ Кадр {i+1}/{num_frames}: не удалось открыть поток")
                time.sleep(interval_seconds)
                continue

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                print(f"❌ Кадр {i+1}/{num_frames}: не удалось захватить")
                time.sleep(interval_seconds)
                continue

            # Сохраняем кадр
            timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"frame_{i+1:03d}_{timestamp_str}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)

            # Анализируем кадр
            analysis = analyze_frame(frame, i+1)

            frames_data.append({
                "index": i+1,
                "timestamp": timestamp,
                "filepath": filepath,
                "analysis": analysis
            })

            # Выводим результат
            print(f"✅ Кадр {i+1}/{num_frames} | {timestamp.strftime('%H:%M:%S')}")
            print(f"   Яркость: {analysis['brightness']:.0f} | Контраст: {analysis['contrast']:.0f}")
            print(f"   Небо: {analysis['sky_ratio']:.1%} | Движение: {analysis['motion_score']:.2f}")
            print(f"   Оценка: {'🟢 ПОЛЕЗНЫЙ' if analysis['is_useful'] else '🔴 БЕСПОЛЕЗНЫЙ'}")
            print("-" * 80)

        except Exception as e:
            print(f"❌ Кадр {i+1}/{num_frames}: ошибка {e}")

        # Ждём до следующего кадра
        if i < num_frames - 1:
            time.sleep(interval_seconds)

    # Сводка
    print("\n" + "=" * 80)
    print("📊 СВОДКА АНАЛИЗА")
    print("=" * 80)

    useful_frames = [f for f in frames_data if f['analysis']['is_useful']]
    print(f"Всего кадров: {len(frames_data)}")
    print(f"Полезных: {len(useful_frames)} ({len(useful_frames)/len(frames_data)*100:.0f}%)")
    print(f"Бесполезных: {len(frames_data) - len(useful_frames)}")

    return frames_data


def analyze_frame(frame, frame_index):
    """
    Анализирует кадр для определения полезности

    Returns:
        dict: метрики анализа
    """
    # Конвертируем в grayscale для анализа
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 1. Яркость (средняя яркость)
    brightness = np.mean(gray)

    # 2. Контраст (стандартное отклонение яркости)
    contrast = np.std(gray)

    # 3. Детектирование неба (верхняя треть изображения)
    height, width = gray.shape
    top_third = gray[:height//3, :]
    sky_brightness = np.mean(top_third)

    # Небо обычно яркое (> 100)
    sky_ratio = np.sum(top_third > 100) / top_third.size

    # 4. Проверка на размытость (от движения камеры)
    # Используем Laplacian для определения резкости
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    motion_score = laplacian_var

    # 5. Определяем полезность кадра
    is_useful = (
        brightness > 50 and  # Не слишком тёмный
        contrast > 30 and    # Есть контраст (не однородная картинка)
        sky_ratio > 0.3 and  # Есть небо в верхней части
        motion_score > 50    # Не размытый от движения
    )

    return {
        "brightness": brightness,
        "contrast": contrast,
        "sky_ratio": sky_ratio,
        "motion_score": motion_score,
        "is_useful": is_useful
    }


def detect_pattern(frames_data):
    """
    Определяет паттерн поворота камеры

    Args:
        frames_data: список данных о кадрах
    """
    print("\n" + "=" * 80)
    print("🔍 ПОИСК ПАТТЕРНА ПОВОРОТА")
    print("=" * 80)

    # Группируем полезные/бесполезные последовательности
    sequences = []
    current_seq = {"type": None, "start": None, "length": 0}

    for i, frame in enumerate(frames_data):
        is_useful = frame['analysis']['is_useful']

        if current_seq["type"] is None:
            # Начало первой последовательности
            current_seq = {"type": is_useful, "start": i, "length": 1}
        elif current_seq["type"] == is_useful:
            # Продолжение текущей последовательности
            current_seq["length"] += 1
        else:
            # Конец последовательности
            sequences.append(current_seq.copy())
            current_seq = {"type": is_useful, "start": i, "length": 1}

    # Добавляем последнюю последовательность
    if current_seq["length"] > 0:
        sequences.append(current_seq)

    # Выводим паттерн
    print("\nПоследовательности:")
    for i, seq in enumerate(sequences):
        seq_type = "🟢 ПОЛЕЗНАЯ" if seq["type"] else "🔴 БЕСПОЛЕЗНАЯ"
        print(f"{i+1}. {seq_type}: кадры {seq['start']+1}-{seq['start']+seq['length']} ({seq['length']} кадров)")

    # Предложение по фильтрации
    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИЯ")
    print("=" * 80)

    useful_seqs = [s for s in sequences if s["type"]]
    if useful_seqs:
        avg_useful_length = np.mean([s["length"] for s in useful_seqs])
        print(f"✅ Камера периодически показывает полезные ракурсы")
        print(f"   Средняя длина полезной последовательности: {avg_useful_length:.1f} кадров")
        print(f"\n   Стратегия:")
        print(f"   1. Захватывать кадры каждые {interval_seconds} секунд")
        print(f"   2. Автоматически фильтровать по критериям:")
        print(f"      - Яркость > 50")
        print(f"      - Контраст > 30")
        print(f"      - Небо в кадре > 30%")
        print(f"      - Резкость > 50 (не размыто)")
        print(f"   3. Сохранять только полезные кадры")
    else:
        print("⚠️  Не обнаружено полезных ракурсов в данной выборке")

    return sequences


if __name__ == "__main__":
    # URL поворотной камеры
    CAMERA_URL = "https://stream.kt.kg:5443/live/camera35.m3u8"

    print("=" * 80)
    print("🔄 АНАЛИЗ ПОВОРОТНОЙ КАМЕРЫ (Кыргызтелеком Центр)")
    print("=" * 80)
    print()

    # Захватываем 20 кадров с интервалом 10 секунд (3.5 минуты)
    frames_data = capture_sequence(
        CAMERA_URL,
        num_frames=20,
        interval_seconds=10,
        output_dir="data/camera_analysis/rotating_camera"
    )

    # Определяем паттерн
    if frames_data:
        sequences = detect_pattern(frames_data)

    print("\n" + "=" * 80)
    print("✅ Анализ завершён!")
    print(f"📁 Кадры сохранены в: data/camera_analysis/rotating_camera/")
    print("=" * 80)
