.PHONY: install run test

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(VENV)/bin/streamlit run app.py

test:
	$(VENV)/bin/pytest
