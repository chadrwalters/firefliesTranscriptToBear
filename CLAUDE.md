# Fireflies to Bear - Claude Assistant Guide

## Build Commands
```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run application
fireflies-to-bear

# Run tests
pytest                            # All tests
pytest tests/test_app.py          # Single test file  
pytest -xvs tests/test_app.py     # Verbose single test
pytest -xvs tests/test_app.py::test_function  # Single test function

# Code quality
black src/ tests/                 # Format code
isort src/ tests/                 # Sort imports
ruff check .                      # Lint code
mypy src/                         # Type checking
pre-commit run --all-files        # Run all checks
```

## Code Style Guidelines
- **Typing**: Use strict typing (disallow_untyped_defs = true)
- **Line length**: 88 characters max (Black default)
- **Imports**: Sort with isort (Black profile)
- **Formatting**: Black with Python 3.8 target
- **Error handling**: Use specific exceptions, proper logging
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Documentation**: Docstrings for all functions/classes with Args/Returns
- **Organization**: Modular architecture with clear separation of concerns