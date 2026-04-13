#!/bin/bash
# Install git hooks for this repo.
# Run once after cloning: bash scripts/hooks/install.sh

REPO_ROOT="$(git rev-parse --show-toplevel)"
cp "$REPO_ROOT/scripts/hooks/pre-commit" "$REPO_ROOT/.git/hooks/pre-commit"
chmod +x "$REPO_ROOT/.git/hooks/pre-commit"
echo "Installed pre-commit hook (auto-bumps plugin.json version)"
