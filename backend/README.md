# Magic API

Python 3.12 Lambda API for the Magic serverless MVP.

Local checks:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
ruff check .
```
