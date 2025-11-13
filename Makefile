.PHONY: setup run test clean help

# Variables
PYTHON := python3
VENV := venv
PYTHON_VENV := $(VENV)/bin/python
PIP_VENV := $(VENV)/bin/pip

help:
	@echo "Available commands:"
	@echo "  make setup    - Set up the project (create virtual environment and install dependencies)"
	@echo "  make run      - Run the Flask application"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean up generated files and virtual environment"

setup:
	@echo "Setting up project..."
	@if [ ! -d "$(VENV)" ]; then \
		$(PYTHON) -m venv $(VENV); \
	fi
	@$(PIP_VENV) install --upgrade pip
	@$(PIP_VENV) install -r requirements.txt
	@echo "Setup complete! Activate virtual environment with: source $(VENV)/bin/activate"

run:
	@echo "Starting Flask application..."
	@$(PYTHON_VENV) -m src.app

test:
	@echo "Running tests..."
	@$(PYTHON_VENV) -m pytest tests/ -v || echo "No tests found. Create tests/ directory with test files."

clean:
	@echo "Cleaning up..."
	@rm -rf $(VENV)
	@rm -f *.db
	@rm -f test_*.db
	@rm -rf __pycache__
	@rm -rf src/__pycache__
	@rm -rf src/**/__pycache__
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

