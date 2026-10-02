
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
	.venv/bin/python -m pip install -e ".[dev]"
	npm install
	$(MAKE) frontend

.PHONY: dev
dev: ## Start Flask (debug, port 5000) and Vite dev servers
	npm run dev &
	TECHNOTE_ENV=dev .venv/bin/python -m flask --app 'technote/app.py' run --debug

.PHONY: clean-dev
clean-dev: ## Delete dev data and cache
	@rm -rf .dev

.PHONY: run
run: ## Run TechNote without installation on port 8000
	TECHNOTE_DATA_DIR=".run/data" TECHNOTE_CACHE_DIR=".run/cache" .venv/bin/python -m technote run -n --port 8000

.PHONY: clean-run
clean-run: ## Delete data and cache from `make run`
	@rm -rf .run

.PHONY: test
test: ## Run all tests
	.venv/bin/python -m pytest

.PHONY: frontend
frontend: ## Build frontend
	@rm -rf technote/static/dist/
	npm run build

.PHONY: install
install: ## Install the current state of TechNote as a package
	pipx install . --force
	@echo "🥰 Successfully installed"
	@printf "🚀 Use the \033[01;32m%s\033[0m command to run the app.\n" technote

.PHONY: package
package: ## Create package
	@command -v pyproject-build >/dev/null 2>&1 || { \
		echo "Error: build is not installed."; \
		echo "Install it with: pipx install build"; \
		exit 1; \
	}
	$(MAKE) frontend
	@rm -rf build/ *.egg-info/ dist/
	pyproject-build
	@echo "📦 Package built in dist/"

.PHONY: upload
upload: ## Upload the created package to pypi.org
	@command -v twine >/dev/null 2>&1 || { \
		echo "Error: twine is not installed."; \
		echo "Install it with: pipx install twine"; \
		exit 1; \
	}
	twine upload dist/*
	@echo "🚀 Successfully uploaded"

.PHONY: upload_test
upload_test: ## Upload the created package to test.pypi.org
	@command -v twine >/dev/null 2>&1 || { \
		echo "Error: twine is not installed."; \
		echo "Install it with: pipx install twine"; \
		exit 1; \
	}
	twine upload --repository testpypi dist/*
	@echo "🚀 Successfully uploaded"

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
		.dev/ \
		.run/ \
		technote/static/dist/ \
		build/ \
		*.egg-info/ \
		dist/ \
		.venv/ \
		node_modules/ \
		technote/__pycache__/ \
		tests/__pycache__/ \
		.pytest_cache/
	@echo "🧹 Cleaned up"

# $(1) = bumpver flags, e.g. --patch --tag=dev
define bump
	.venv/bin/python -m bumpver update $(1) --dry
	@printf "Apply this bump? [y/N] "; read ans; [ "$$ans" = "y" ] || { echo "Aborted."; exit 1; }
	.venv/bin/python -m bumpver update $(1)
endef

.PHONY: bump-patch
bump-patch: ## Increment the patch number, then create a commit with a tag
	$(call bump,--patch)

.PHONY: bump-minor
bump-minor: ## Increment the minor version, then create a commit with a tag
	$(call bump,--minor)

.PHONY: bump-major
bump-major: ## Increment the major version, then create a commit with a tag
	$(call bump,--major)

.PHONY: bump-patch-dev
bump-patch-dev: ## Start a patch dev cycle (0.2.1 -> 0.2.2.dev)
	$(call bump,--patch --tag=dev --no-commit --no-tag-commit)

.PHONY: bump-minor-dev
bump-minor-dev: ## Start a minor dev cycle  (0.2.1 -> 0.3.0.dev)
	$(call bump,--minor --tag=dev --no-commit --no-tag-commit)

.PHONY: bump-major-dev
bump-major-dev: ## Start a major dev cycle  (0.2.1 -> 1.0.0.dev)
	$(call bump,--major --tag=dev --no-commit --no-tag-commit)

.PHONY: bump-dev
bump-dev: ## Increment dev number (0.2.2.dev -> 0.2.2.dev1)
	$(call bump,--tag-num --no-commit --no-tag-commit)

.PHONY: bump-dev-final
bump-dev-final: ## Drop the dev suffix (0.2.2.dev1 -> 0.2.2), then create a commit with a tag
	$(call bump,--tag=final)
