# Homework 13: Productization

A `LinearRegression` trained on `sklearn.datasets.make_regression(n_samples=100, n_features=2,
noise=0.1, random_state=42)`, saved with `joblib`, and served behind a small Flask API with two
routes.

## Running it

```bash
python app.py
```

The model loads once, at import time, when the server starts, not on every request.

## Calling it

**POST /predict**

```bash
curl -X POST http://127.0.0.1:5050/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [-1.1913035, 0.65655361]}'
```

```json
{"prediction": -55.863238621216084}
```

**GET /predict/<f1>/<f2>**

```bash
curl http://127.0.0.1:5050/predict/-1.1913035/0.65655361
```

```json
{"prediction": -55.863238621216084}
```

## Bad input

Both routes return a JSON error and HTTP 400 instead of a traceback:

```bash
curl -X POST http://127.0.0.1:5050/predict -H "Content-Type: application/json" -d '{"features": [1.0]}'
# 400 {"error": "'features' must be a list of exactly 2 numbers"}

curl http://127.0.0.1:5050/predict/abc/0.2
# 400 {"error": "path parameters must both be numbers"}
```

The submission notebook trains the model, saves and reloads it, then starts `app.py` as a
subprocess and makes all three calls above with `requests`, output left visible.
