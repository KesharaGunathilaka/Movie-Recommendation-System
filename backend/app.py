from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
from recommender import SemanticMovieRecommender

app = Flask(__name__)
CORS(app)

# Config via env
DATA_PATH = os.environ.get(
    "MOVIES_CSV", "../data/processed/Movies_Preprocessed.csv")
MODEL_NAME = os.environ.get("MODEL_NAME", "all-mpnet-base-v2")
DEVICE = os.environ.get("DEVICE", None)
TOP_N_DEFAULT = int(os.environ.get("TOP_N", "10"))

print(f"[API] Loading movies from {DATA_PATH}")
df = pd.read_csv(DATA_PATH)  # ensure your CSV exists
recommender = SemanticMovieRecommender(
    df, model_name=MODEL_NAME, device=DEVICE)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "device": recommender.device})


@app.route("/recommend", methods=["POST"])
def recommend():
    """
    POST JSON:
    {
      "query": "billionaire superhero",
      "top_n": 10
    }
    """
    payload = request.get_json(force=True)
    query = payload.get("query", "")
    top_n = int(payload.get("top_n", TOP_N_DEFAULT))
    if not query:
        return jsonify({"error": "query missing"}), 400

    try:
        results = recommender.recommend(query, top_n=top_n)
        return jsonify({"query": query, "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(
        os.environ.get("PORT", 8000)), debug=False)
