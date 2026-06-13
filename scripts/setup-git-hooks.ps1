Write-Host "Setting up git hooks..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Error "Error: .git directory not found. Please run this script from the root of the repository."
    exit 1
}

# Copy pre-push hook
Copy-Item -Path "scripts/pre-push" -Destination ".git/hooks/pre-push" -Force

Write-Host "✅ Git hooks set up successfully!" -ForegroundColor Green
