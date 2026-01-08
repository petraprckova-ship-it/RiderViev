# Makefile pro Person Tracker

.PHONY: help install test lint format clean run docker

help:
	@echo "Person Tracker - Makefile příkazy:"
	@echo ""
	@echo "  make install       - Instalace závislostí"
	@echo "  make test          - Spuštění testů"
	@echo "  make test-cov      - Testy s coverage reportem"
	@echo "  make lint          - Code linting"
	@echo "  make format        - Code formatting (black, isort)"
	@echo "  make clean         - Vyčištění cache a build souborů"
	@echo "  make run           - Spuštění aplikace"
	@echo "  make run-robot     - Spuštění robot service"
	@echo "  make docs          - Generování dokumentace"
	@echo ""

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/
	pylint src/
	mypy src/ --ignore-missing-imports

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

run:
	python main.py

run-robot:
	cd robot && python robot_service.py --mock

docs:
	cd docs && make html

# Docker targets
docker-build:
	docker build -t person-tracker:latest .

docker-run:
	docker run -it --rm \
		--device=/dev/video0 \
		-e DISPLAY=$$DISPLAY \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		person-tracker:latest
