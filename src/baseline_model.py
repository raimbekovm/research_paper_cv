"""
Baseline model for PM2.5 prediction using weather data only.

This module implements a weather-only baseline model for PM2.5 prediction,
which serves as a lower bound for comparison with image-based and multimodal
approaches in the AirVision system.

The baseline uses only meteorological features:
    - Temperature (°C)
    - Humidity (%)
    - Wind speed (m/s)
    - Hour of day (0-23)
    - Day of year (1-366)
    - Winter flag (December-February)

Example:
    >>> from src.baseline_model import WeatherBaselineModel, train_baseline
    >>> model = WeatherBaselineModel()
    >>> model.fit(X_train, y_train)
    >>> metrics = model.evaluate(X_test, y_test)
    >>> print(f"MAE: {metrics.mae:.2f} µg/m³")
"""

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from src.utils.io import ensure_dir
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Attempt to import sklearn
try:
    from sklearn.base import BaseEstimator, RegressorMixin
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed. Install with: pip install scikit-learn")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ModelMetrics:
    """
    Evaluation metrics for regression model.

    Attributes:
        mae: Mean Absolute Error (µg/m³)
        rmse: Root Mean Squared Error (µg/m³)
        r2: Coefficient of determination (0-1)
        n_samples: Number of samples evaluated
    """

    mae: float
    rmse: float
    r2: float
    n_samples: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "r2": round(self.r2, 4),
            "n_samples": self.n_samples,
        }

    def __str__(self) -> str:
        return (
            f"MAE: {self.mae:.2f} µg/m³ | "
            f"RMSE: {self.rmse:.2f} µg/m³ | "
            f"R²: {self.r2:.3f}"
        )


@dataclass
class TrainingResult:
    """
    Result of model training.

    Attributes:
        train_metrics: Metrics on training set
        test_metrics: Metrics on test set (if available)
        cv_scores: Cross-validation scores (if performed)
        feature_importances: Feature importance scores (if available)
    """

    train_metrics: ModelMetrics
    test_metrics: Optional[ModelMetrics] = None
    cv_scores: Optional[np.ndarray] = None
    feature_importances: Optional[Dict[str, float]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "train_metrics": self.train_metrics.to_dict(),
        }
        if self.test_metrics:
            result["test_metrics"] = self.test_metrics.to_dict()
        if self.cv_scores is not None:
            result["cv_scores"] = {
                "mean": float(np.mean(self.cv_scores)),
                "std": float(np.std(self.cv_scores)),
                "scores": self.cv_scores.tolist(),
            }
        if self.feature_importances:
            result["feature_importances"] = self.feature_importances
        return result


@dataclass
class WeatherFeatures:
    """
    Weather features for PM2.5 prediction.

    These features represent meteorological conditions that influence
    PM2.5 concentrations, particularly during winter thermal inversions.
    """

    temperature: float  # Celsius
    humidity: float  # Percent
    wind_speed: float  # m/s
    hour: int  # 0-23
    day_of_year: int  # 1-366
    is_winter: int  # Binary: 1 if Dec-Feb, else 0

    @classmethod
    def from_dict(cls, data: dict, timestamp: Optional[datetime] = None) -> "WeatherFeatures":
        """
        Create WeatherFeatures from dictionary.

        Args:
            data: Dictionary with weather data
            timestamp: Optional timestamp (defaults to now)

        Returns:
            WeatherFeatures instance
        """
        if timestamp is None:
            ts_raw = data.get("timestamp")
            if isinstance(ts_raw, str):
                timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            elif isinstance(ts_raw, datetime):
                timestamp = ts_raw
            else:
                timestamp = datetime.now()

        return cls(
            temperature=data.get("temperature", 0.0),
            humidity=data.get("humidity", 50.0),
            wind_speed=data.get("wind_speed", 0.0),
            hour=timestamp.hour,
            day_of_year=timestamp.timetuple().tm_yday,
            is_winter=1 if timestamp.month in [12, 1, 2] else 0,
        )

    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input."""
        return np.array([
            self.temperature,
            self.humidity,
            self.wind_speed,
            self.hour,
            self.day_of_year,
            self.is_winter,
        ])

    @staticmethod
    def feature_names() -> List[str]:
        """Return list of feature names."""
        return [
            "temperature",
            "humidity",
            "wind_speed",
            "hour",
            "day_of_year",
            "is_winter",
        ]


# =============================================================================
# Model Implementation
# =============================================================================


class WeatherBaselineModel:
    """
    Weather-only baseline model for PM2.5 prediction.

    This model uses only meteorological features to predict PM2.5
    concentrations, serving as a baseline for comparison with
    image-based approaches.

    The model supports multiple regression algorithms:
        - ridge: Ridge regression (default, fast and robust)
        - rf: Random Forest (captures non-linear patterns)
        - gbm: Gradient Boosting (best accuracy, slower)

    Args:
        algorithm: Algorithm to use ('ridge', 'rf', or 'gbm')
        random_state: Random seed for reproducibility

    Example:
        >>> model = WeatherBaselineModel(algorithm='ridge')
        >>> model.fit(X_train, y_train)
        >>> predictions = model.predict(X_test)
        >>> metrics = model.evaluate(X_test, y_test)
    """

    ALGORITHMS = {
        "ridge": lambda: Ridge(alpha=1.0),
        "rf": lambda: RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        ),
        "gbm": lambda: GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        ),
    }

    def __init__(
        self,
        algorithm: str = "ridge",
        random_state: int = 42,
    ):
        if not SKLEARN_AVAILABLE:
            raise ImportError(
                "scikit-learn is required. Install with: pip install scikit-learn"
            )

        if algorithm not in self.ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm: {algorithm}. "
                f"Choose from: {list(self.ALGORITHMS.keys())}"
            )

        self.algorithm = algorithm
        self.random_state = random_state
        self.feature_names = WeatherFeatures.feature_names()

        # Create pipeline with scaling
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("regressor", self.ALGORITHMS[algorithm]()),
        ])

        self._is_fitted = False
        logger.debug(f"Initialized WeatherBaselineModel with algorithm={algorithm}")

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cross_validate: bool = True,
        cv_folds: int = 5,
    ) -> TrainingResult:
        """
        Train the model on weather data.

        Args:
            X: Feature matrix (n_samples, 6)
            y: Target values (n_samples,) - PM2.5 in µg/m³
            cross_validate: Whether to perform cross-validation
            cv_folds: Number of CV folds

        Returns:
            TrainingResult with training metrics
        """
        X = np.asarray(X)
        y = np.asarray(y)

        logger.info(f"Training {self.algorithm} model on {len(X)} samples")

        # Cross-validation
        cv_scores = None
        if cross_validate and len(X) >= cv_folds * 2:
            cv_scores = cross_val_score(
                self.pipeline, X, y,
                cv=cv_folds,
                scoring="neg_mean_absolute_error",
            )
            cv_scores = -cv_scores  # Convert to positive MAE
            logger.info(f"CV MAE: {np.mean(cv_scores):.2f} ± {np.std(cv_scores):.2f}")

        # Fit pipeline
        self.pipeline.fit(X, y)
        self._is_fitted = True

        # Calculate training metrics
        train_metrics = self._calculate_metrics(X, y)

        # Extract feature importances if available
        feature_importances = self._get_feature_importances()

        return TrainingResult(
            train_metrics=train_metrics,
            cv_scores=cv_scores,
            feature_importances=feature_importances,
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict PM2.5 concentrations.

        Args:
            X: Feature matrix (n_samples, 6)

        Returns:
            Predicted PM2.5 values (n_samples,)

        Raises:
            ValueError: If model is not fitted
        """
        if not self._is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        X = np.asarray(X)
        return self.pipeline.predict(X)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> ModelMetrics:
        """
        Evaluate model on test data.

        Args:
            X: Feature matrix (n_samples, 6)
            y: True PM2.5 values (n_samples,)

        Returns:
            ModelMetrics with MAE, RMSE, and R²
        """
        return self._calculate_metrics(X, y)

    def _calculate_metrics(self, X: np.ndarray, y: np.ndarray) -> ModelMetrics:
        """Calculate regression metrics."""
        y_pred = self.predict(X)

        return ModelMetrics(
            mae=mean_absolute_error(y, y_pred),
            rmse=np.sqrt(mean_squared_error(y, y_pred)),
            r2=r2_score(y, y_pred),
            n_samples=len(y),
        )

    def _get_feature_importances(self) -> Optional[Dict[str, float]]:
        """Extract feature importances from fitted model."""
        regressor = self.pipeline.named_steps["regressor"]

        if hasattr(regressor, "feature_importances_"):
            importances = regressor.feature_importances_
            return dict(zip(self.feature_names, importances.tolist()))
        elif hasattr(regressor, "coef_"):
            # For linear models, use absolute coefficients
            coefs = np.abs(regressor.coef_)
            coefs = coefs / coefs.sum()  # Normalize
            return dict(zip(self.feature_names, coefs.tolist()))

        return None

    def save(self, filepath: Union[str, Path]) -> None:
        """
        Save model to file.

        Args:
            filepath: Path to save model (.pkl extension)
        """
        if not self._is_fitted:
            raise ValueError("Cannot save unfitted model")

        filepath = Path(filepath)
        ensure_dir(filepath.parent)

        with open(filepath, "wb") as f:
            pickle.dump({
                "pipeline": self.pipeline,
                "algorithm": self.algorithm,
                "feature_names": self.feature_names,
            }, f)

        logger.info(f"Model saved to {filepath}")

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "WeatherBaselineModel":
        """
        Load model from file.

        Args:
            filepath: Path to saved model

        Returns:
            Loaded WeatherBaselineModel instance
        """
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        model = cls(algorithm=data["algorithm"])
        model.pipeline = data["pipeline"]
        model.feature_names = data["feature_names"]
        model._is_fitted = True

        logger.info(f"Model loaded from {filepath}")
        return model


# =============================================================================
# Dataset Loading
# =============================================================================


def load_dataset(
    data_dir: Union[str, Path] = "data",
) -> Optional[Tuple[np.ndarray, np.ndarray, List[dict]]]:
    """
    Load dataset from collected data files.

    Expects metadata files with 'pm25' and 'weather' fields.

    Args:
        data_dir: Directory containing data/metadata folder

    Returns:
        Tuple of (X, y, samples) or None if no data found

    Example:
        >>> X, y, samples = load_dataset()
        >>> print(f"Loaded {len(samples)} samples")
    """
    data_path = Path(data_dir)
    metadata_dir = data_path / "metadata"

    if not metadata_dir.exists():
        logger.warning(f"Metadata directory not found: {metadata_dir}")
        return None

    metadata_files = list(metadata_dir.glob("*.json"))

    if not metadata_files:
        logger.warning("No metadata files found")
        return None

    logger.info(f"Found {len(metadata_files)} metadata files")

    samples = []
    X_list = []
    y_list = []

    for meta_file in metadata_files:
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            # Check required fields
            pm25 = meta.get("pm25")
            weather = meta.get("weather")

            if pm25 is None or weather is None:
                continue

            # Extract features
            features = WeatherFeatures.from_dict(weather, None)

            samples.append(meta)
            X_list.append(features.to_array())
            y_list.append(pm25)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"Skipping {meta_file.name}: {e}")
            continue

    if not samples:
        logger.warning("No valid samples found with PM2.5 and weather data")
        return None

    X = np.array(X_list)
    y = np.array(y_list)

    logger.info(f"Loaded {len(samples)} samples with PM2.5 data")
    logger.info(f"PM2.5 range: {y.min():.1f} - {y.max():.1f} µg/m³")

    return X, y, samples


# =============================================================================
# Training Functions
# =============================================================================


def train_baseline(
    algorithm: str = "ridge",
    test_size: float = 0.2,
    data_dir: Union[str, Path] = "data",
    save_model: bool = True,
) -> Optional[TrainingResult]:
    """
    Train and evaluate baseline model.

    Args:
        algorithm: Algorithm to use ('ridge', 'rf', 'gbm')
        test_size: Fraction of data for testing
        data_dir: Directory containing data
        save_model: Whether to save trained model

    Returns:
        TrainingResult or None if training fails

    Example:
        >>> result = train_baseline(algorithm='rf')
        >>> print(result.test_metrics)
    """
    if not SKLEARN_AVAILABLE:
        logger.error("scikit-learn not available")
        return None

    # Load data
    dataset = load_dataset(data_dir)
    if dataset is None:
        logger.error("Failed to load dataset")
        return None

    X, y, samples = dataset

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=42,
    )

    logger.info(f"Train: {len(X_train)} samples | Test: {len(X_test)} samples")

    # Train model
    model = WeatherBaselineModel(algorithm=algorithm)
    result = model.fit(X_train, y_train)

    # Evaluate on test set
    result.test_metrics = model.evaluate(X_test, y_test)

    logger.info(f"Test metrics: {result.test_metrics}")

    # Save model
    if save_model:
        model_path = Path(data_dir) / "models" / f"baseline_{algorithm}.pkl"
        model.save(model_path)

    return result


def compare_algorithms(
    data_dir: Union[str, Path] = "data",
) -> Dict[str, ModelMetrics]:
    """
    Compare all available algorithms.

    Args:
        data_dir: Directory containing data

    Returns:
        Dictionary mapping algorithm names to test metrics
    """
    results = {}

    for algorithm in WeatherBaselineModel.ALGORITHMS.keys():
        logger.info(f"Training {algorithm}...")
        result = train_baseline(algorithm=algorithm, save_model=False, data_dir=data_dir)

        if result and result.test_metrics:
            results[algorithm] = result.test_metrics

    return results


# =============================================================================
# Interpretation
# =============================================================================


def interpret_results(metrics: ModelMetrics) -> str:
    """
    Interpret model performance for research context.

    Args:
        metrics: Model evaluation metrics

    Returns:
        Interpretation string
    """
    r2 = metrics.r2

    if r2 < 0.3:
        return (
            "R² < 0.3: Weather alone has weak predictive power.\n"
            "This suggests that visual features from images may provide\n"
            "significant additional information for PM2.5 estimation."
        )
    elif r2 < 0.5:
        return (
            "R² = 0.3-0.5: Moderate correlation with weather.\n"
            "Multimodal approach should show meaningful improvement\n"
            "over this weather-only baseline."
        )
    elif r2 < 0.7:
        return (
            "R² = 0.5-0.7: Good weather-PM2.5 correlation.\n"
            "Images should still provide complementary information\n"
            "about atmospheric visibility."
        )
    else:
        return (
            "R² > 0.7: Strong baseline performance.\n"
            "Check for potential data leakage.\n"
            "Image-based improvement may be more modest but still valuable."
        )


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Main entry point for baseline model training."""
    print("=" * 80)
    print("AirVision Baseline Model: Weather → PM2.5")
    print("=" * 80)

    if not SKLEARN_AVAILABLE:
        print("\nError: scikit-learn not installed")
        print("Install with: pip install scikit-learn")
        return

    # Load dataset
    print("\nLoading dataset...")
    dataset = load_dataset()

    if dataset is None:
        print("\nNo data found. Run data collection first:")
        print("  python -m src.collect_data --mode continuous")
        return

    X, y, samples = dataset

    print(f"\nDataset:")
    print(f"  Samples: {len(samples)}")
    print(f"  Features: {X.shape[1]}")
    print(f"  PM2.5 range: {y.min():.1f} - {y.max():.1f} µg/m³")
    print(f"  PM2.5 mean: {y.mean():.1f} µg/m³")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"\nSplit:")
    print(f"  Train: {len(X_train)} samples")
    print(f"  Test: {len(X_test)} samples")

    # Train model
    print("\n" + "-" * 80)
    print("Training Ridge Regression baseline...")
    print("-" * 80)

    model = WeatherBaselineModel(algorithm="ridge")
    result = model.fit(X_train, y_train)

    print(f"\nTrain: {result.train_metrics}")

    if result.cv_scores is not None:
        print(f"CV MAE: {np.mean(result.cv_scores):.2f} ± {np.std(result.cv_scores):.2f} µg/m³")

    # Test evaluation
    result.test_metrics = model.evaluate(X_test, y_test)
    print(f"Test:  {result.test_metrics}")

    # Feature importances
    if result.feature_importances:
        print("\nFeature Importances:")
        sorted_features = sorted(
            result.feature_importances.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for name, importance in sorted_features:
            bar = "█" * int(importance * 50)
            print(f"  {name:15s} {importance:.3f} {bar}")

    # Interpretation
    print("\n" + "-" * 80)
    print("Interpretation")
    print("-" * 80)
    print(interpret_results(result.test_metrics))

    # Save results
    print("\n" + "-" * 80)
    print("For Publication")
    print("-" * 80)
    print(f"Baseline MAE:  {result.test_metrics.mae:.2f} µg/m³")
    print(f"Baseline RMSE: {result.test_metrics.rmse:.2f} µg/m³")
    print(f"Baseline R²:   {result.test_metrics.r2:.3f}")
    print("\nCompare with:")
    print("  - Image-only model (CNN → PM2.5)")
    print("  - Multimodal model (CNN + Weather → PM2.5)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
