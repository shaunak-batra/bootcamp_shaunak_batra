# Homework 02: Tooling Setup

This practices the reproducible-environment scaffold used everywhere else in the course. A Python environment with pinned dependencies, secrets kept out of source control via `.env`/`.env.example` and read through a small `src/config.py` helper, and a Jupyter notebook (`notebooks/00_project_setup.ipynb`) that checks all of it end to end: interpreter, `.env` loading, `API_KEY`/`DATA_DIR` access, and a NumPy sanity check. The same `data/raw/`, `data/processed/`, `notebooks/`, `src/`, `docs/`, `reports/`, `model/` scaffold gets built for real in `project/` in this same stage.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # already done here, with the dummy values the sheet asks for
jupyter nbconvert --to notebook --execute --inplace notebooks/00_project_setup.ipynb
```

## Files

- `src/config.py`: `load_env()` and `get_key()`, the config-access pattern every later homework's `src/` modules follow.
- `.env.example` is the committed template. `.env` has the real (dummy) values and is gitignored.
- `notebooks/00_project_setup.ipynb` is executed and confirms `API_KEY present: True`.
- `requirements.txt` is frozen from the environment this notebook actually runs in.
