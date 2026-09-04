# List available recipes
default:
    @just --list

# Format, lint with autofix, and type-check
check: format lint typecheck

# Format Python sources
format:
    ruff format

# Lint Python sources and apply fixes
lint:
    ruff check --fix

# Type-check with pyright
typecheck:
    pyright
