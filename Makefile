
SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

.PHONY: help
help: ## Print info about all commands
	@echo "✨ Commands:"
	@echo
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[01;32m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: ## Prepare the development environment
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	npm install
	$(MAKE) instance
	$(MAKE) frontend

.PHONY: dev
dev: ## Run TechNote for development
	npm run dev &
	.venv/bin/python -m flask --app 'technote/server.py' run --debug

.PHONY: run
run: ## Run TechNote without installation
	.venv/bin/python -m technote run -n

.PHONY: test
test: ## Run all tests
	.venv/bin/python -m pytest -v

.PHONY: instance
instance: ## Remove the "instance/" directory, create a new database
	@rm -rf technote/instance/
	@echo "🧹 The instance cleaned up!"
	@.venv/bin/python scripts/init_db.py
	@echo "🗄️ A new database created!"

.PHONY: frontend
frontend: ## Build frontend
	@rm -rf technote/static/dist/
	npm run build

.PHONY: install
install: ## Install the current state of TechNote as a package
	pipx install . --force
	@echo "🥰 Successfully installed!"
	@printf "🚀 Use the \033[01;32m%s\033[0m command to run the app.\n" technote

.PHONY: package
package: ## Create package
	$(MAKE) instance
	$(MAKE) frontend
	@rm -rf build/ *.egg-info/ dist/
	.venv/bin/python -m build
	@echo "📦 Successfully built the package!"

.PHONY: upload
upload: ## Upload the created package to pypi.org
	@.venv/bin/twine upload dist/*
	@echo "🚀 Successfully uploaded!"

.PHONY: upload_test
upload_test: ## Upload the created package to test.pypi.org
	@.venv/bin/twine upload --repository testpypi dist/*
	@echo "🚀 Successfully uploaded!"

.PHONY: install_test
install_test: ## Install the package from test.pypi.org
	@pipx install --index-url https://test.pypi.org/simple/ \
	              --pip-args="--extra-index-url https://pypi.org/simple/" \
				  pytechnote

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
