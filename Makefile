.PHONY: help install install-dev clean lint format test coverage collect train docs

# Default target
help:
	@echo "AirVision - Image-Based PM2.5 Estimation"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  setup          Complete project setup"
	@echo ""
	@echo "Development:"
	@echo "  lint           Run linters (flake8, mypy)"
	@echo "  format         Format code (black, isort)"
	@echo "  test           Run tests"
	@echo "  coverage       Run tests with coverage report"
	@echo ""
	@echo "Data Collection:"
	@echo "  collect        Start data collection (daylight mode)"
	@echo "  collect-24h    Start 24/7 data collection"
	@echo "  status         Check collection status"
	@echo ""
	@echo "Model:"
	@echo "  train          Train the model"
	@echo "  evaluate       Evaluate model performance"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Remove build artifacts"
	@echo "  docs           Build documentation"

# ============================================================================
# Setup
# ============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

setup: install-dev
	@echo "Creating data directories..."
	mkdir -p data/images data/pm25 data/weather data/metadata logs outputs
	@echo "Setup complete!"

# ============================================================================
# Development
# ============================================================================

lint:
	@echo "Running flake8..."
	flake8 src tests --max-line-length=100 --ignore=E501,W503
	@echo "Running mypy..."
	mypy src --ignore-missing-imports

format:
	@echo "Running isort..."
	isort src tests
	@echo "Running black..."
	black src tests

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

# ============================================================================
# Data Collection
# ============================================================================

collect:
	@echo "Starting daylight data collection..."
	caffeinate -i python -u src/collect_data.py --mode continuous --interval 30 --duration 12

collect-24h:
	@echo "Starting 24/7 data collection..."
	caffeinate -i python -u src/collect_data.py --mode continuous --interval 30 --duration 24 --24-7

collect-background:
	@echo "Starting background collection..."
	nohup caffeinate -i python -u src/collect_data.py --mode continuous --interval 30 --duration 12 > logs/collection.log 2>&1 &
	@echo "Collection started in background. Check logs/collection.log"

status:
	@echo "Collection Status:"
	@ps aux | grep collect_data | grep -v grep || echo "No collection running"
	@echo ""
	@echo "Images collected:"
	@find data/images -name "*.jpg" 2>/dev/null | wc -l | xargs echo "Total:"
	@echo ""
	@echo "Latest log entries:"
	@tail -20 logs/collection.log 2>/dev/null || echo "No log file found"

stop:
	@echo "Stopping collection..."
	@pkill -f "collect_data.py" || echo "No collection process found"

# ============================================================================
# Model Training
# ============================================================================

train:
	@echo "Starting model training..."
	python src/train.py --config configs/default.yaml

evaluate:
	@echo "Evaluating model..."
	python src/evaluate.py --config configs/default.yaml

# ============================================================================
# Utilities
# ============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete!"

docs:
	@echo "Building documentation..."
	cd docs && make html

# ============================================================================
# Docker (optional)
# ============================================================================

docker-build:
	docker build -t airvision:latest .

docker-run:
	docker run -v $(PWD)/data:/app/data airvision:latest
