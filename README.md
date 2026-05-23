**Project Status**
- **Implemented:** basic LLM adapters for OpenAI, Anthropic, Groq, Google Gemini, and Ollama; example environment file (`example.env`) and dotenv support.

**Getting API keys and setup**

- **Copy example env:** create a `.env` in the project root by copying `example.env`:

	```powershell
	copy example.env .env
	```

- **Add provider keys:** open the new `.env` and set the following values as needed:

	- `OPENAI_API_KEY` — from your OpenAI account (https://platform.openai.com)
	- `ANTHROPIC_API_KEY` — from your Anthropic account (https://console.anthropic.com)
	- `GEMINI_API_KEY` — from Google Cloud (enable the Gemini API and create credentials)
	- `GROQ_API_KEY` — from Groq/Sanity project settings if using Groq
	- `OLLAMA_BASE_URL` — optional, e.g. `http://localhost:11434` if running Ollama locally

- **Do not commit `.env`:** this repository ignores `.env`; keep secrets private.

**Quick run**

- Activate your virtualenv, install requirements, then run components or tests. Tests and quick scripts will read `.env` via `python-dotenv`.

If you want, I can add a small script to validate required env vars at startup. 

**About `uv`**

- This project shows commands using the `uv` CLI (e.g. `uv add dotenv`, `uv add ipykernel`) which was used to add development/runtime dependencies.
- If you don't have `uv` installed, you can install packages manually. Example equivalents:

	```powershell
	# with pip
	pip install python-dotenv ipykernel

	# or add to your pyproject.toml and install with your preferred tool
	```

- If you want, I can add a short `scripts/` helper to validate and list required env vars at startup.
