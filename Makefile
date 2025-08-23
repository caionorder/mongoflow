.PHONY: help install test lint format clean build publish docs

help:
	@echo "MongoFlow Development Commands"
	@echo "=============================="
	@echo "install    - Install package in development mode"
	@echo "test       - Run tests with coverage"
	@echo "lint       - Run code linters"
	@echo "format     - Format code with black and isort"
	@echo "clean      - Clean build artifacts"
	@echo "build      - Build distribution packages"
	@echo "publish    - Publish to PyPI"
	@echo "docs       - Build documentation"

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=mongoflow --cov-report=term-missing --cov-report=html

lint:
	flake8 src/mongoflow tests/
	mypy src/mongoflow
	pylint src/mongoflow

format:
	black src/mongoflow tests/
	isort src/mongoflow tests/

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

test-publish: build
	python -m twine upload --repository testpypi dist/*

docs:
	cd docs && make clean && make html
	@echo "Documentation built in docs/_build/html"

dev-server:
	python examples/basic_usage.py

check: format lint test
	@echo "All checks passed!"
