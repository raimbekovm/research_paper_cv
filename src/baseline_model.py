"""
Baseline модель для предсказания PM2.5 только по метеоданным
КРИТИЧНО: Это baseline для сравнения с multimodal моделью!
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import json


class BaselineWeatherModel:
    """
    Простая baseline модель: метеоданные → PM2.5

    Использует только:
    - temperature (°C)
    - humidity (%)
    - wind_speed (m/s)
    - time_of_day (hour)
    - day_of_year (для сезонности)

    БЕЗ изображений!
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            'temperature',
            'humidity',
            'wind_speed',
            'hour',
            'day_of_year',
            'is_winter'  # Бинарный признак для зимнего сезона
        ]

    def prepare_features(self, weather_data):
        """
        Подготовка признаков из метеоданных

        Args:
            weather_data: dict с метеоданными

        Returns:
            np.array: вектор признаков
        """
        timestamp = weather_data.get('timestamp')

        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = timestamp

        hour = dt.hour
        day_of_year = dt.timetuple().tm_yday

        # Зима в Бишкеке: декабрь-февраль (основной сезон смога)
        is_winter = 1 if dt.month in [12, 1, 2] else 0

        features = [
            weather_data.get('temperature', 0),
            weather_data.get('humidity', 50),
            weather_data.get('wind_speed', 0),
            hour,
            day_of_year,
            is_winter
        ]

        return np.array(features)

    def train(self, X, y):
        """
        Обучение модели

        Args:
            X: np.array (N, 6) - признаки
            y: np.array (N,) - PM2.5 values
        """
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.linear_model import Ridge
            from sklearn.ensemble import RandomForestRegressor
        except ImportError:
            print("❌ Требуется scikit-learn: pip install scikit-learn")
            return False

        # Нормализация признаков
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Простая Ridge regression как baseline
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_scaled, y)

        # Можно также попробовать RandomForest для нелинейных зависимостей
        # self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        # self.model.fit(X_scaled, y)

        return True

    def predict(self, X):
        """
        Предсказание PM2.5

        Args:
            X: np.array (N, 6) - признаки

        Returns:
            np.array (N,) - предсказанные значения PM2.5
        """
        if self.model is None or self.scaler is None:
            raise ValueError("Модель не обучена! Вызовите train() сначала")

        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def evaluate(self, X, y_true):
        """
        Оценка качества модели

        Args:
            X: признаки
            y_true: истинные значения PM2.5

        Returns:
            dict: метрики (MAE, RMSE, R²)
        """
        y_pred = self.predict(X)

        mae = np.mean(np.abs(y_true - y_pred))
        rmse = np.sqrt(np.mean((y_true - y_pred)**2))

        # R² (coefficient of determination)
        ss_res = np.sum((y_true - y_pred)**2)
        ss_tot = np.sum((y_true - np.mean(y_true))**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'n_samples': len(y_true)
        }


def load_dataset(data_dir="data"):
    """
    Загрузка датасета из собранных данных

    Returns:
        tuple: (X, y, metadata)
    """
    data_path = Path(data_dir)

    # Ищем метаданные сборов
    metadata_files = list(data_path.glob("metadata/*.json"))

    if not metadata_files:
        print("❌ Нет собранных данных! Запустите сбор данных сначала")
        return None, None, None

    print(f"📂 Найдено {len(metadata_files)} файлов метаданных")

    # Загружаем данные
    samples = []

    for meta_file in metadata_files:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        # Проверяем что есть все необходимые данные
        if 'pm25' not in meta or meta['pm25'] is None:
            continue

        if 'weather' not in meta:
            continue

        sample = {
            'timestamp': meta['timestamp'],
            'camera_id': meta['camera_id'],
            'pm25': meta['pm25'],
            'weather': meta['weather'],
            'image_path': meta.get('image_path')
        }

        samples.append(sample)

    if not samples:
        print("❌ Нет образцов с PM2.5 данными!")
        return None, None, None

    print(f"✅ Загружено {len(samples)} образцов с PM2.5 данными")

    return samples


def train_and_evaluate_baseline():
    """
    Полный цикл обучения и оценки baseline модели
    """
    print("=" * 80)
    print("🤖 BASELINE MODEL: WEATHER → PM2.5")
    print("=" * 80)
    print()

    # Загрузка данных
    print("📂 Загрузка датасета...")
    samples = load_dataset()

    if samples is None:
        print("\n⚠️  Нет данных для обучения!")
        print("   Запустите сбор данных: python src/collect_data.py")
        return

    # Подготовка данных
    print(f"\n📊 Подготовка {len(samples)} образцов...")

    model = BaselineWeatherModel()

    X = []
    y = []

    for sample in samples:
        features = model.prepare_features(sample['weather'])
        X.append(features)
        y.append(sample['pm25'])

    X = np.array(X)
    y = np.array(y)

    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    print(f"   PM2.5 range: {y.min():.1f} - {y.max():.1f} µg/m³")
    print(f"   PM2.5 mean: {y.mean():.1f} µg/m³")

    # Train/test split (80/20)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"\n📊 Split:")
    print(f"   Train: {len(X_train)} образцов")
    print(f"   Test: {len(X_test)} образцов")

    # Обучение
    print("\n🏋️  Обучение модели...")
    success = model.train(X_train, y_train)

    if not success:
        return

    # Оценка на train
    print("\n📈 Оценка на Train set:")
    train_metrics = model.evaluate(X_train, y_train)
    print(f"   MAE:  {train_metrics['mae']:.2f} µg/m³")
    print(f"   RMSE: {train_metrics['rmse']:.2f} µg/m³")
    print(f"   R²:   {train_metrics['r2']:.3f}")

    # Оценка на test
    print("\n📈 Оценка на Test set:")
    test_metrics = model.evaluate(X_test, y_test)
    print(f"   MAE:  {test_metrics['mae']:.2f} µg/m³")
    print(f"   RMSE: {test_metrics['rmse']:.2f} µg/m³")
    print(f"   R²:   {test_metrics['r2']:.3f}")

    # Интерпретация
    print("\n" + "=" * 80)
    print("💡 ИНТЕРПРЕТАЦИЯ BASELINE РЕЗУЛЬТАТОВ")
    print("=" * 80)

    if test_metrics['r2'] < 0.3:
        print("\n🔴 R² < 0.3: Модель практически не работает")
        print("   Причины:")
        print("   - Метеоданные слабо коррелируют с PM2.5")
        print("   - Нужны дополнительные признаки (например, изображения!)")
        print("   - Возможно мало данных для обучения")

    elif test_metrics['r2'] < 0.5:
        print("\n🟡 R² = 0.3-0.5: Слабая предсказательная способность")
        print("   Метеоданные дают некоторую информацию, но недостаточно")
        print("   Изображения должны улучшить результат!")

    elif test_metrics['r2'] < 0.7:
        print("\n🟢 R² = 0.5-0.7: Умеренная предсказательная способность")
        print("   Baseline работает прилично")
        print("   Multimodal модель должна показать улучшение")

    else:
        print("\n✅ R² > 0.7: Хороший baseline!")
        print("   ⚠️  Проверьте нет ли data leakage!")
        print("   Multimodal модель должна показать небольшое, но значимое улучшение")

    print("\n📝 Для статьи:")
    print(f"   Baseline MAE: {test_metrics['mae']:.2f} µg/m³")
    print(f"   Baseline RMSE: {test_metrics['rmse']:.2f} µg/m³")
    print(f"   Baseline R²: {test_metrics['r2']:.3f}")
    print()
    print("   Это будет сравниваться с:")
    print("   - Image-only model (CNN → PM2.5)")
    print("   - Multimodal model (CNN + Weather → PM2.5)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Проверяем наличие scikit-learn
    try:
        import sklearn
        train_and_evaluate_baseline()
    except ImportError:
        print("=" * 80)
        print("❌ ТРЕБУЕТСЯ SCIKIT-LEARN")
        print("=" * 80)
        print()
        print("Установите: pip install scikit-learn pandas")
        print()
        print("После установки запустите:")
        print("python src/baseline_model.py")
        print("=" * 80)
