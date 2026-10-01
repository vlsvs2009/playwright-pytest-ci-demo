.PHONY: install test test-api test-ui smoke headed serve clean

install:  ## Install Python deps and the Chromium browser
	pip install -r requirements.txt
	python -m playwright install chromium

test:  ## Full suite, in parallel
	pytest -n auto

test-api:  ## API tests only
	pytest -n auto -m api

test-ui:  ## UI tests only
	pytest -n auto -m ui

smoke:  ## Critical-path subset
	pytest -m smoke

headed:  ## Watch the UI tests run in a visible browser
	pytest -m ui --headed --slowmo 300

serve:  ## Run the demo app on http://127.0.0.1:8000
	uvicorn app.main:app --reload

clean:
	rm -rf reports .pytest_cache
