# Backend Testing & Git Hook Integration Setup

This guide provides instructions on how backend testing is structured, how to run tests locally, and how to initialize the Git pre-push hooks on a new machine.

---

## 📋 System Requirements
- **Python**: `>=3.13`
- **uv**: The project uses the `uv` package manager. If not installed, you can install it using:
  - **Windows (PowerShell)**: `irm https://astral.sh/uv/install.ps1 | iex`
  - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## 🛠️ Hook Installation on a New Machine

Git hooks reside inside the local `.git/hooks/` directory, which is excluded from Git version control. Consequently, **every time you clone this repository onto a new machine**, you must initialize the pre-push hook using one of the helper scripts provided in the `scripts/` folder:

### Option A: Windows (PowerShell)
Open a PowerShell terminal in the repository root directory and run:
```powershell
.\scripts\setup-git-hooks.ps1
```

### Option B: macOS / Linux / Git Bash
Open a terminal in the repository root directory and run:
```bash
chmod +x scripts/setup-git-hooks.sh
./scripts/setup-git-hooks.sh
```

These scripts copy the version-controlled pre-push template [scripts/pre-push](file:///d:/Github-Projects/Autonomous-Multi-Agent/scripts/pre-push) into `.git/hooks/pre-push` and ensure it is marked executable.

---

## 🏃 Running Tests Locally

All tests are configured using `pytest` and defined under the [orchestrator_agent/agent_test/](file:///d:/Github-Projects/Autonomous-Multi-Agent/orchestrator_agent/agent_test) folder.

To install dependencies and run all tests, simply run:
```bash
uv run pytest
```

### Running Specific Test Suites
You can run any specific test file directly:
```bash
# Test memory checkpointers & LangGraph state persistence
uv run pytest orchestrator_agent/agent_test/test_backend_memory.py

# Test schema conversions and API formats
uv run pytest orchestrator_agent/agent_test/test_services.py

# Test session creation, listing, renaming, and deletion
uv run pytest orchestrator_agent/agent_test/test_session_manager.py
```

---

## 🔍 Implementation Architecture

### 1. Pytest Configuration
To prevent test runs from invoking live LLM API calls or requiring Ollama to run locally, the `[tool.pytest.ini_options]` in [pyproject.toml](file:///d:/Github-Projects/Autonomous-Multi-Agent/pyproject.toml) restricts test discovery:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
python_files = ["test_*.py"] # Runs test_backend_memory.py, ignores llm_test.py
asyncio_mode = "auto"
```
By selecting `test_*.py`, ad-hoc scripts like `llm_test.py` are ignored during standard CI and pre-push runs.

### 2. Git Pre-Push Hook Workflow
The pre-push hook intercepts `git push` commands. 
- When `git push` is invoked, Git automatically runs `.git/hooks/pre-push`.
- The hook runs the local test suite using `uv run pytest`.
- If tests pass (exit code `0`), Git continues with the push.
- If any test fails (non-zero exit code), the script displays an error message and exit status `1`, causing Git to abort the push.

### 3. GitHub Actions CI/CD Pipeline
Every pull request or push targeting `main` or `master` triggers the workflow configured in [.github/workflows/ci.yml](file:///d:/Github-Projects/Autonomous-Multi-Agent/.github/workflows/ci.yml). This pipeline:
1. Provisions an `ubuntu-latest` runner.
2. Installs Python 3.13.
3. Installs `uv` and synchronizes the project environment.
4. Executes the pytest suite (`uv run pytest`).
