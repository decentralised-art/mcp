PYTHON ?= python3
ROOT_DIR := $(CURDIR)
VENV_DIR := $(ROOT_DIR)/.venv
VENV_PYTHON := $(shell "$(PYTHON)" -c "import os; root=r'''$(VENV_DIR)'''; sub='Scripts' if os.name == 'nt' else 'bin'; exe='python.exe' if os.name == 'nt' else 'python'; print(os.path.join(root, sub, exe))")
STAMP := $(VENV_DIR)/.bootstrap-complete

.DEFAULT_GOAL := help

.PHONY: help install smoke test stdio mcpb sync-docs list-tools list-resources read-core-primer invoke-example

help:
	@echo "decentralised.art MCP targets:"
	@echo "  make install        Create/update the local .venv and install decentralised-art-mcp"
	@echo "  make smoke          Run the repo smoke test"
	@echo "  make test           Run the full test suite"
	@echo "  make stdio          Run the real MCP stdio server"
	@echo "  make mcpb           Build a Claude Desktop .mcpb bundle in dist/"
	@echo "  make sync-docs      Refresh bundled platform Markdown documentation"
	@echo "  make list-tools     List local tool metadata"
	@echo "  make list-resources List local resource metadata"
	@echo "  make read-core-primer Read the core primer resource"
	@echo "  make invoke-example Run a sample local tool invocation"

$(STAMP): pyproject.toml scripts/bootstrap_venv.py
	"$(PYTHON)" scripts/bootstrap_venv.py

install: $(STAMP)
	@echo "decentralised-art-mcp is installed in $(VENV_DIR)"

smoke: $(STAMP)
	"$(VENV_PYTHON)" scripts/smoke_test.py

test: $(STAMP)
	"$(VENV_PYTHON)" scripts/generate_api_contracts.py --check
	"$(VENV_PYTHON)" -m unittest discover -s tests -v

stdio: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.server stdio

mcpb: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.mcpb

sync-docs: $(STAMP)
	"$(VENV_PYTHON)" scripts/sync_documentation.py

list-tools: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.server list-tools

list-resources: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.server list-resources

read-core-primer: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.server read-resource core.primer

invoke-example: $(STAMP)
	"$(VENV_PYTHON)" -m decentralised_art_mcp.server invoke core.build_parent_connector '{"name":"piece","child_names":["a","b"]}'
