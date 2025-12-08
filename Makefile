# Makefile for osay - OpenAI TTS wrapper

PREFIX ?= $(HOME)/.local
BINDIR ?= $(PREFIX)/bin
SRCDIR := $(shell pwd)

.PHONY: all install uninstall check help

all: help

help:
	@echo "osay - OpenAI TTS wrapper installation"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Symlink osay to $(BINDIR)"
	@echo "  make uninstall    Remove symlink from $(BINDIR)"
	@echo "  make check        Verify installation"
	@echo ""
	@echo "Variables:"
	@echo "  PREFIX            Installation prefix (default: $(HOME)/.local)"
	@echo "  BINDIR            Binary directory (default: $(PREFIX)/bin)"
	@echo ""
	@echo "Examples:"
	@echo "  make install                          # Link to ~/.local/bin"
	@echo "  make install PREFIX=/usr/local        # Link to /usr/local/bin (needs sudo)"

install: osay
	@echo "Linking osay to $(BINDIR)..."
	@mkdir -p $(BINDIR)
	@ln -sf $(SRCDIR)/osay $(BINDIR)/osay
	@echo "Done. Make sure $(BINDIR) is in your PATH."
	@echo ""
	@echo "Add to your shell config if needed:"
	@echo '  export PATH="$(BINDIR):$$PATH"'

uninstall:
	@echo "Removing symlink from $(BINDIR)..."
	@rm -f $(BINDIR)/osay
	@echo "Done."
	@echo ""
	@echo "Note: Config file at ~/.config/osay/config was not removed."
	@echo "Run 'rm -rf ~/.config/osay' to remove it manually."

check:
	@echo "Checking installation..."
	@if [ -L "$(BINDIR)/osay" ]; then \
		echo "✓ Symlink exists at $(BINDIR)/osay"; \
		echo "  -> $$(readlink $(BINDIR)/osay)"; \
		if command -v osay >/dev/null 2>&1; then \
			echo "✓ osay is in PATH"; \
		else \
			echo "✗ osay not in PATH - add $(BINDIR) to PATH"; \
		fi; \
	else \
		echo "✗ Symlink not found at $(BINDIR)/osay"; \
		exit 1; \
	fi
