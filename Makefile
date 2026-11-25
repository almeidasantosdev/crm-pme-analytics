PYTHON ?= python3
export PYTHONPATH := .

.PHONY: help install generate analysis test lint dashboard ci

help:
	@echo "make install    instala dependências"
	@echo "make generate   recria a base fictícia (semente 42)"
	@echo "make analysis   figuras e avaliação do modelo de churn"
	@echo "make test       pytest"
	@echo "make lint       ruff"
	@echo "make dashboard  sobe o Streamlit"
	@echo "make ci         lint + testes"

install:
	$(PYTHON) -m pip install -r requirements.txt

generate:
	$(PYTHON) data/generate.py

analysis:
	$(PYTHON) -m analysis.churn_model
	$(PYTHON) -m analysis.report

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

dashboard:
	$(PYTHON) -m streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port $${PORT:-8501}

ci: lint test
