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

def _strip_labels(series, pattern):
    """Drop a leading "Label:" block from a column and flatten its newlines."""
    return (series.fillna("").astype(str)
            .str.replace(pattern, "", regex=True)
            .str.replace(r"\s*\r?\n\s*", " ", regex=True)
            .str.strip())


def prepare(df):
    """Clean up known quirks of the source dataset before anything is embedded."""
    df = df.copy()
    df["Title"] = df["Title"].fillna("").astype(str).str.strip()
    # ~100 titles arrive doubled, as "Avengers, TheThe Avengers"
    df["Title"] = df["Title"].str.replace(
        r"^(?P<base>.+), (?P<art>The|A|An)\W*(?P=art) (?P=base)$",
        lambda m: f"{m.group('art')} {m.group('base')}", regex=True)
    # ~580 rows carry a leftover "Director:" label from the source wiki tables
    df["Director"] = _strip_labels(df["Director"], r"^\s*Directors?:\s*")
    # ~620 cast fields hold an entire labelled block instead of a cast list:
    # "Director: Roger Christian<newline>Cast: Christian Slater, ..."
    df["Cast"] = _strip_labels(df["Cast"], r"(?s)^.*?\bCast:\s*")
    # the same film is listed once per origin/ethnicity, so titles repeat
    before = len(df)
    df = df.drop_duplicates(
        subset=["Title", "Release Year"], keep="first").reset_index(drop=True)
    print(f"[API] {before} rows loaded, {len(df)} after removing duplicates")
    return df


print(f"[API] Loading movies from {DATA_PATH}")
df = prepare(pd.read_csv(DATA_PATH))  # ensure your CSV exists
recommender = SemanticMovieRecommender(
    df, model_name=MODEL_NAME, device=DEVICE)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "device": recommender.device,
        "model": MODEL_NAME,
        "movies": len(df),
    })


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
