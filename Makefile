# ==========================================================================
# verifier — operator workflow
# Usage: make <target>   (see `make help`)
# ==========================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help setup check-guard check-commits

help: ## Show this help message
	@echo "verifier — operator workflow"
	@echo "Usage: make <target>"
	@grep -E '^[a-zA-Z_:.-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## ---- Bootstrap ------------------------------------------------------------

setup: ## Install guard hooks + run the guard self-test
	bash scripts/setup.sh

## ---- Conformity -----------------------------------------------------------

check-guard: ## Self-test the attribution guard (reject foreign, allow owner)
	bash scripts/setup.sh

check-commits: ## Re-run the message guard over the last commit message
	bash .githooks/commit-msg .git/COMMIT_EDITMSG 2>/dev/null || true
