#!/bin/sh

# This script sets up git hooks for the project.
# Run this from the root of the repository.

echo "Setting up git hooks..."

if [ ! -d ".git" ]; then
  echo "Error: .git directory not found. Please run this script from the root of the repository."
  exit 1
fi

# Copy pre-push hook
cp scripts/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

echo "✅ Git hooks set up successfully!"
