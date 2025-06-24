# Step 01 — Project setup and first endpoint

## What
A Python project with its own private toolbox, and one working web endpoint.

## Why
Every project needs its dependencies described in a file, not installed by hand. Otherwise nobody else can reproduce your setup.

---

## Create the project

```bash
mkdir -p ~/Documents/Vyshali/erag && cd ~/Documents/Vyshali/erag && git init
```

## `pyproject.toml`

```toml
[project]
name = "erag"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
]

[dependency-groups]
dev = [
    "ruff>=0.9",
    "mypy>=1.14",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/erag"]

[tool.ruff]
line-length = 88
src = ["src"]
extend-exclude = ["migrations"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "S", "N", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "src"
```

### Section by section

| Section | Job |
|---|---|
| `[project]` | The name tag. Needs Python 3.12+. |
| `dependencies` | What the running app needs. |
| `dev` | What only you need while building. Excluded from the production image. |
| `[build-system]` | How to package it. |
| `packages` | Where the code lives. |
| `[tool.ruff]` | Lint rules. |
| `[tool.mypy]` | Type-check rules. |

### The lint rule letters

| Letter | Catches |
|---|---|
| `E` | messy formatting |
| `F` | real errors, like using a name that does not exist |
| `I` | unsorted imports |
| `B` | common traps |
| `UP` | outdated syntax |
| `S` | **security problems** |
| `N` | bad names |

`S` is why a hardcoded password gets flagged. That rule caught a genuine problem in this project.

`strict = true` for mypy means every function must declare its types, and mypy checks you kept the promise.

---

## Install

```bash
uv sync
```

`uv` reads the file, downloads the tools, and creates a private `.venv` folder. Nothing else on your computer is touched.

---

## First endpoint

```bash
mkdir -p src/erag && touch src/erag/__init__.py
```

`src/erag/main.py`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}
```

| Line | Meaning |
|---|---|
| `app = FastAPI()` | make the app |
| `@app.get("/health/live")` | when someone visits this address, run the function below |
| `-> dict[str, str]` | promise: returns a dictionary of text to text |

---

## Run

```bash
uv run uvicorn erag.main:app --reload --port 8001
```

`erag.main:app` means: in the file `erag/main.py`, use the thing named `app`.

**FastAPI vs uvicorn:** FastAPI is the chef, deciding what the answer is. Uvicorn is the waiter, carrying it in and out.

## Test

```bash
curl localhost:8001/health/live
```

```json
{"status":"ok"}
```

Also visit **http://localhost:8001/docs** — FastAPI builds that page for free.

---

## Gotchas

**Always use `uv run`.** Typing `uvicorn` alone may run a different Python (Anaconda's) that knows nothing about your project.

**If the venv misbehaves, delete and rebuild it.** It is a throwaway folder:

```bash
rm -rf .venv && uv sync
```
