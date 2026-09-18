
SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

.PHONY: help
help: ## Print info about all commands
	@echo "✨ Commands:"
	@echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: dev
dev: ## Run the development servers
	$(MAKE) backend_requirements
	$(MAKE) db
	$(MAKE) frontend_requirements
	npm run dev &
	.venv/bin/flask --app 'technote/server.py' run --debug

.PHONY: test
test: ## Run all tests
	$(MAKE) backend_requirements
	.venv/bin/python -m pytest -v

.PHONY: db
db: ## Ensure the database is ready
	@if [ ! -d "technote/instance/*.db" ]; then \
		$(MAKE) backend_requirements; \
		.venv/bin/python scripts/init_db.py; \
	fi

.PHONY: fresh_instance
fresh_instance: ## Remove the "instance/" directory, create a new database
	@rm -rf technote/instance/
	@echo "🧹 The instance cleaned up!"
	$(MAKE) backend_requirements
	@.venv/bin/python scripts/init_db.py
	@echo "🗄️ A new database created!"

.PHONY: run
run: ## Run without installation
	$(MAKE) backend_requirements
	$(MAKE) db
	$(MAKE) build_web
	.venv/bin/python -m technote

.PHONY: install
install: ## Install as a package
	$(MAKE) db
	$(MAKE) build_web
	pipx install . --force
	@echo "🥰 Successfully installed!"
	@printf "🚀 Use the \033[01;32m%s\033[0m command to run the app.\n" technote

.PHONY: package
package: ## Create package
	$(MAKE) fresh_instance
	$(MAKE) build_web
	@rm -rf build/ *.egg-info/ dist/
	.venv/bin/python -m build
	@echo "📦 Successfully built the package!"

.PHONY: install_package
install_package: ## Install and run the created package to test it
	@pipx install dist/*.whl --force
	@technote

.PHONY: upload
upload: ## Upload the created package to PyPI
	$(MAKE) backend_requirements
	@.venv/bin/twine upload dist/*
	@echo "🚀 Successfully uploaded!"

.PHONY: upload_test
upload_test: ## Upload the created package to test.pypi.org
	$(MAKE) backend_requirements
	@.venv/bin/twine upload --repository testpypi dist/*
	@echo "🚀 Successfully uploaded!"

.PHONY: install_test
install_test: ## Install the package from test.pypi.org
	@pipx install --index-url https://test.pypi.org/simple/ \
	              --pip-args="--extra-index-url https://pypi.org/simple/" \
				  pytechnote

.PHONY: build_web
build_web: ## Build the web client
	$(MAKE) frontend_requirements
	@rm -rf technote/static/dist/
	npm run build

.PHONY: backend_requirements
backend_requirements: ## Ensure the required Python packages have installed
	@if [ ! -d ".venv" ]; then \
		python3 -m venv .venv; \
		.venv/bin/pip install -r requirements.txt; \
	fi

.PHONY: frontend_requirements
frontend_requirements: ## Ensure the required node modules have installed
	@if [ ! -d "node_modules" ]; then \
		npm install; \
	fi

.PHONY: clean
clean: ## Remove build files, cache files, packages, and the database
	@ read -p "Confirm clean? (y/N) " ans; \
	if [ "$$ans" != "y" ]; then \
		echo "Operation aborted."; \
		exit 1; \
	fi
	@rm -rf \
		technote/instance/ \
		technote/static/dist/ \
		build/ \
		*.egg-info/ \
		dist/ \
		.venv/ \
		node_modules/ \
		technote/__pycache__/ \
		tests/__pycache__/ \
		.pytest_cache/
	@echo "🧹 Cleaned up!"
