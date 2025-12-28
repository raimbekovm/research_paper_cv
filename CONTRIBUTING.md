# Contributing to AirVision

Thank you for your interest in contributing to AirVision! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Style Guide](#style-guide)
- [Testing](#testing)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/airvision.git
   cd airvision
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/raimbekovm/airvision.git
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   make install-dev
   ```

3. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

4. Copy environment template:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes, following the [Style Guide](#style-guide)

3. Add tests for new functionality

4. Run the test suite:
   ```bash
   make test
   ```

5. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting, etc.)
   - `refactor:` - Code refactoring
   - `test:` - Adding or updating tests
   - `chore:` - Maintenance tasks

## Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Update the CHANGELOG.md if applicable
4. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request against the `main` branch
6. Fill out the PR template with relevant information
7. Wait for review and address any feedback

## Style Guide

### Python Code Style

- Follow [PEP 8](https://pep8.org/) guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting (line length: 100)
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use type hints for function signatures
- Write docstrings for all public functions and classes (Google style)

Example:
```python
def process_frame(
    image: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, float]:
    """
    Process a single frame and extract features.

    Args:
        image: Input image as numpy array (H, W, C)
        threshold: Quality threshold for filtering

    Returns:
        Dictionary containing extracted features

    Raises:
        ValueError: If image dimensions are invalid
    """
    ...
```

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs when relevant

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/test_capture.py -v

# Run specific test
pytest tests/test_capture.py::test_capture_single_frame -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use pytest fixtures for common setup
- Aim for >80% code coverage

Example:
```python
import pytest
from src.capture_frame import capture_single_frame

class TestCaptureFrame:
    def test_capture_single_frame_success(self, mock_camera):
        """Test successful frame capture."""
        result = capture_single_frame(mock_camera)
        assert result is not None
        assert result.shape == (1080, 1920, 3)

    def test_capture_single_frame_timeout(self, mock_camera_timeout):
        """Test frame capture timeout handling."""
        with pytest.raises(TimeoutError):
            capture_single_frame(mock_camera_timeout)
```

## Questions?

If you have questions, feel free to:
- Open an issue on GitHub
- Contact the maintainers

Thank you for contributing!
