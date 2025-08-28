import re
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import process, fuzz


def _nz(x):
    return "" if pd.isna(x) else str(x)


class SemanticMovieRecommender:
    def __init__(self, df: pd.DataFrame, model_name="all-mpnet-base-v2", device=None, batch_size=64):

        self.df = df.reset_index(drop=True).copy()
        if "Title" not in self.df.columns:
            raise ValueError("DataFrame must have a 'Title' column.")
        # detect device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        print(f"[Recommender] Using device: {self.device}")

        # Build rich search text (emphasize plot & keywords)
        self.df["_search_text"] = self.df.apply(
            self._row_to_search_text, axis=1)

        # load the model on device
        self.model = SentenceTransformer(model_name, device=self.device)

        # encode corpus (batched)
        # convert_to_tensor True uses PyTorch tensors on device
        self.embeddings = self.model.encode(
            self.df["_search_text"].tolist(),
            convert_to_tensor=True,
            show_progress_bar=True,
            batch_size=batch_size,
            normalize_embeddings=True
        )

        # lower titles for lookup
        self.titles = self.df["Title"].astype(str)
        self.titles_lower = self.titles.str.lower().str.strip().tolist()

    # ---- text building ----
    def _row_to_search_text(self, row):
        title = _nz(row.get("Title", ""))
        director = _nz(row.get("Director", ""))
        cast = _nz(row.get("Cast", ""))
        genre = _nz(row.get("Genre", ""))
        keywords = _nz(row.get("Keywords", ""))
        plot = _nz(row.get("Plot", ""))
        year = _nz(row.get("Year", row.get("Year Binned", "")))

        # emphasize title & plot/keywords
        text = (
            f"{title}. "
            f"Director: {director}. "
            f"Cast: {cast}. "
            f"Genres: {genre}. "
            f"Keywords: {keywords}. {keywords}. "
            f"Plot: {plot}. {plot}. "
            f"Year: {year}. "
            f"{title}."
        )
        return text.strip()

    # ---- fuzzy title find ----
    def fuzzy_title_index(self, query, cutoff=80):
        res = process.extractOne(query.lower().strip(
        ), self.titles_lower, scorer=fuzz.WRatio, score_cutoff=cutoff)
        if res:
            title_matched, score, idx = res
            return idx, title_matched, score
        return None, None, None

    # ---- role masks ----
    def role_masks(self, person):
        p = person.lower().strip()
        dir_mask = self.df.get("Director", pd.Series(
            [""]*len(self.df))).astype(str).str.lower().str.contains(p, na=False)
        cast_mask = self.df.get("Cast", pd.Series(
            [""]*len(self.df))).astype(str).str.lower().str.contains(p, na=False)
        return dir_mask, cast_mask

    # ---- semantic search helpers ----
    def _semantic_query_scores(self, query):
        q_emb = self.model.encode(
            [query], convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(q_emb, self.embeddings)[0]  # tensor
        return sims.cpu().numpy()  # 1D array

    # ---- public recommend ----
    def recommend(self, query, top_n=10, fuzzy_title_cutoff=85):
        """
        Returns list of dicts: {Title, Director, Cast, Genre, Score, Poster?, Year?, Plot?}
        """
        text = str(query).strip()
        low = text.lower()

        # intent heuristics
        # collection/franchise detection (e.g. "star wars collection")
        coll_m = re.search(
            r"(.+?)\s+(collection|series|saga|universe|filmography|set)\b", low)
        if coll_m:
            phrase = coll_m.group(1).strip()
            mask = self.df["Title"].str.lower().str.contains(re.escape(phrase))
            if mask.sum() > 0:
                subset = self.df[mask].copy()
                # try sort by Year if present
                if "Year" in subset.columns:
                    try:
                        subset["__yr"] = pd.to_numeric(
                            subset["Year"], errors="coerce")
                        subset = subset.sort_values(
                            "__yr").drop(columns="__yr")
                    except:
                        subset = subset.sort_values("Title")
                return subset.head(top_n).to_dict(orient="records")

        # 1) Exact / fuzzy title: "movies like <title>" or user inputs title
        # check if query matches a title strongly
        idx, _, score = self.fuzzy_title_index(text, cutoff=fuzzy_title_cutoff)
        if idx is not None:
            # neighbor search: find top similar embeddings to movie idx
            target_emb = self.embeddings[idx]
            sims = util.cos_sim(target_emb, self.embeddings)[0].cpu().numpy()
            sims[idx] = -1.0  # exclude itself
            top_idxs = np.argsort(-sims)[: top_n]
            return self._rows_from_idxs(top_idxs, sims[top_idxs])

        # 2) Person-based queries: "Christopher Nolan movies", "Tom Holland action movie"
        # Basic pattern detection: "<person> movies|films", "movies with <person>", "directed by <person>"
        person_m = re.search(
            r"(?:movies|films|films?)\s+(?:with|featuring)\s+([a-z .'-]+)", low)
        if not person_m:
            person_m = re.search(r"([a-z .'-]+)\s+(?:movies|films)(.*)$", low)
        if not person_m:
            person_m = re.search(
                r"(?:directed by|by)\s+([a-z .'-]+)(.*)$", low)
        if person_m:
            person = person_m.group(1).strip()
            rest = (person_m.group(2).strip() if len(
                person_m.groups()) > 1 and person_m.group(2) else "")
            # semantic search on full query
            sims = self._semantic_query_scores(text)
            top_idxs = np.argsort(-sims)[: top_n*3]
            dir_mask, cast_mask = self.role_masks(person)
            boost = (dir_mask | cast_mask).astype(float).values * 0.25
            reranked = sorted([(i, float(sims[i] + boost[i]))
                              for i in top_idxs], key=lambda x: x[1], reverse=True)[:top_n]
            idxs = [i for i, _ in reranked]
            scores = np.array([s for _, s in reranked])
            return self._rows_from_idxs(idxs, scores)

        # 3) General natural language semantic search
        sims = self._semantic_query_scores(text)
        top_idxs = np.argsort(-sims)[: top_n * 3]

        # genre detection boosts
        boosts = np.zeros(len(self.df))
        for g in ["action", "comedy", "drama", "thriller", "romance", "sci-fi", "science fiction",
                  "fantasy", "horror", "animation", "adventure", "crime", "mystery", "superhero"]:
            if re.search(rf"\b{re.escape(g)}\b", low):
                mask = self.df.get("Genre", pd.Series(
                    [""]*len(self.df))).astype(str).str.lower().str.contains(g)
                boosts += mask.astype(float).values * 0.07

        # title-like inside query e.g. "like iron man"
        m = re.search(r"(?:like|similar to)\s+(.+)$", low)
        if m:
            maybe_title = m.group(1).strip()
            idx2, _, _ = self.fuzzy_title_index(maybe_title, cutoff=75)
            if idx2 is not None:
                n_sims = util.cos_sim(self.embeddings[idx2], self.embeddings)[
                    0].cpu().numpy()
                boosts += n_sims * 0.1

        reranked = sorted([(i, float(sims[i] + boosts[i]))
                          for i in top_idxs], key=lambda x: x[1], reverse=True)[:top_n]
        idxs = [i for i, _ in reranked]
        scores = np.array([s for _, s in reranked])
        return self._rows_from_idxs(idxs, scores)

    def _rows_from_idxs(self, idxs, scores):
        rows = []
        for i, s in zip(idxs, scores):
            r = self.df.iloc[i].to_dict()
            r["_score"] = float(s)
            # keep a few fields normalized
            rows.append({
                "Title": r.get("Title"),
                "Director": r.get("Director"),
                "Cast": r.get("Cast"),
                "Genre": r.get("Genre"),
                "Year": r.get("Year", r.get("Year Binned")),
                "Poster": r.get("Poster", None),
                "Plot": r.get("Plot", None),
                "Score": r.get("_score")
            })
        return rows
