from flask import Flask, jsonify, request
import joblib

app = Flask(__name__)
model = joblib.load("model/model.pkl")


def predict_from_features(features):
    return float(model.predict([features])[0])


@app.route("/predict", methods=["POST"])
def predict_post():
    body = request.get_json(silent=True)
    if not body or "features" not in body:
        return jsonify({"error": "request body must be JSON with a 'features' key"}), 400

    features = body["features"]
    if not isinstance(features, list) or len(features) != 2:
        return jsonify({"error": "'features' must be a list of exactly 2 numbers"}), 400

    try:
        features = [float(f) for f in features]
    except (TypeError, ValueError):
        return jsonify({"error": "'features' must all be numbers"}), 400

    return jsonify({"prediction": predict_from_features(features)})


@app.route("/predict/<f1>/<f2>", methods=["GET"])
def predict_get(f1, f2):
    try:
        features = [float(f1), float(f2)]
    except ValueError:
        return jsonify({"error": "path parameters must both be numbers"}), 400

    return jsonify({"prediction": predict_from_features(features)})


if __name__ == "__main__":
    app.run(port=5050)
