import hashlib
import os
import re

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import process, fuzz


def _nz(x):
    return "" if pd.isna(x) else str(x)


class SemanticMovieRecommender:
    def __init__(self, df: pd.DataFrame, model_name="all-mpnet-base-v2", device=None, batch_size=64,
                 cache_dir=None):

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
        texts = self.df["_search_text"].tolist()

        # load the model on device
        self.model = SentenceTransformer(model_name, device=self.device)

        # Encoding the whole corpus costs minutes, so keep the result on disk and
        # reuse it whenever the same texts are encoded with the same model.
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), ".embeddings_cache")
        cache_path = self._cache_path(cache_dir, model_name, texts)
        cached = self._load_cached_embeddings(cache_path)

        if cached is not None:
            print(f"[Recommender] Loaded cached embeddings for {len(texts)} movies")
            self.embeddings = cached.to(self.device)
        else:
            print(f"[Recommender] Encoding {len(texts)} movies "
                  f"(one-off, the result is cached for later runs)")
            # encode corpus (batched)
            # convert_to_tensor True uses PyTorch tensors on device
            self.embeddings = self.model.encode(
                texts,
                convert_to_tensor=True,
                show_progress_bar=True,
                batch_size=batch_size,
                normalize_embeddings=True
            )
            self._save_embeddings(cache_path, self.embeddings)
            print(f"[Recommender] Cached embeddings to {cache_path}")

        # lower titles for lookup
        self.titles = self.df["Title"].astype(str)
        self.titles_lower = self.titles.str.lower().str.strip().tolist()

    # ---- embedding cache ----
    @staticmethod
    def _cache_path(cache_dir, model_name, texts):
        """Cache file name derived from the model and the exact corpus text."""
        digest = hashlib.sha256()
        digest.update(model_name.encode("utf-8"))
        digest.update(str(len(texts)).encode("utf-8"))
        for text in texts:
            digest.update(text.encode("utf-8", "ignore"))
        return os.path.join(cache_dir, f"{digest.hexdigest()[:16]}.npy")

    @staticmethod
    def _load_cached_embeddings(path):
        if not os.path.exists(path):
            return None
        try:
            return torch.from_numpy(np.load(path))
        except Exception as e:
            print(f"[Recommender] Ignoring unreadable cache {path}: {e}")
            return None

    @staticmethod
    def _save_embeddings(path, embeddings):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.save(path, embeddings.cpu().numpy())

    # ---- text building ----
    def _row_to_search_text(self, row):
        title = _nz(row.get("Title", ""))
        director = _nz(row.get("Director", ""))
        cast = _nz(row.get("Cast", ""))
        genre = _nz(row.get("Genre", ""))
        keywords = _nz(row.get("Keywords", ""))
        plot = _nz(row.get("Plot", ""))
        year = _nz(row.get("Year", row.get("Year Binned", "")))
        ryear = _nz(row.get("Year", row.get("Release Year", "")))

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
    def fuzzy_title_index(self, query, cutoff=80, min_length_ratio=0.6):
        """Find the title a query is referring to, if it is referring to one.

        WRatio scores a short title highly whenever it appears anywhere inside a
        longer string, so "christopher nolan movies" matches the film "Her" and
        "space survival thriller" matches "Urvi". Requiring the matched title to
        be a comparable length keeps real (and misspelled) title lookups working
        while letting descriptive queries fall through to semantic search.
        """
        q = query.lower().strip()
        res = process.extractOne(
            q, self.titles_lower, scorer=fuzz.WRatio, score_cutoff=cutoff)
        if not res:
            return None, None, None

        title_matched, score, idx = res
        if len(title_matched) < min_length_ratio * len(q):
            return None, None, None
        return idx, title_matched, score

    # ---- role masks ----
    def role_masks(self, person):
        p = person.lower().strip()
        # regex=False: names contain "." and "-" which would otherwise be
        # interpreted as pattern syntax (e.g. "m. night shyamalan")
        dir_mask = self.df.get("Director", pd.Series(
            [""]*len(self.df))).astype(str).str.lower().str.contains(p, na=False, regex=False)
        cast_mask = self.df.get("Cast", pd.Series(
            [""]*len(self.df))).astype(str).str.lower().str.contains(p, na=False, regex=False)
        return dir_mask, cast_mask

    # ---- semantic search helpers ----
    def _semantic_query_scores(self, query):
        q_emb = self.model.encode(
            [query], convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(q_emb, self.embeddings)[0]  # tensor
        return sims.cpu().numpy()  # 1D array

    def _neighbors(self, idx, top_n):
        """Films whose embeddings sit closest to the film at `idx`."""
        sims = util.cos_sim(self.embeddings[idx], self.embeddings)[
            0].cpu().numpy()
        sims[idx] = -1.0  # exclude the film itself
        top_idxs = np.argsort(-sims)[: top_n]
        return self._rows_from_idxs(top_idxs, sims[top_idxs])

    # ---- public recommend ----
    def recommend(self, query, top_n=10, fuzzy_title_cutoff=85):
        """
        Returns list of dicts: {Title, Director, Cast, Genre, Year, Plot, Score}
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
                # try sort by release year if present, so a franchise reads in order
                year_col = next(
                    (c for c in ("Year", "Release Year") if c in subset.columns), None)
                if year_col:
                    subset["__yr"] = pd.to_numeric(
                        subset[year_col], errors="coerce")
                    subset = subset.sort_values("__yr").drop(columns="__yr")
                else:
                    subset = subset.sort_values("Title")
                # go through _rows_from_idxs so this branch returns the same
                # shape (and a score) as every other branch
                idxs = subset.head(top_n).index.tolist()
                sims = self._semantic_query_scores(text)
                return self._rows_from_idxs(idxs, sims[idxs])

        # 1) Explicit similarity request: "movies like <title>", "similar to <title>".
        # Handled before the whole-query title check, because the surrounding
        # words make the query too long to match the title on its own.
        like_m = re.search(r"(?:like|similar to)\s+(.+)$", low)
        if like_m:
            idx, _, _ = self.fuzzy_title_index(
                like_m.group(1).strip(), cutoff=75)
            if idx is not None:
                return self._neighbors(idx, top_n)

        # 2) The query is itself a title: return that film's nearest neighbours
        idx, _, score = self.fuzzy_title_index(text, cutoff=fuzzy_title_cutoff)
        if idx is not None:
            return self._neighbors(idx, top_n)

        # 3) Person-based queries: "Christopher Nolan movies", "Tom Holland action movie"
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
            dir_mask, cast_mask = self.role_masks(person)
            role_mask = (dir_mask | cast_mask).values
            # Restrict to that person's filmography first, then rank it
            # semantically. Boosting inside an already-chosen candidate list
            # cannot surface their films if none made the shortlist to start
            # with, which is why "Christopher Nolan movies" used to return none.
            if role_mask.sum() > 0:
                sims = self._semantic_query_scores(text)
                candidates = np.where(role_mask)[0]
                order = candidates[np.argsort(-sims[candidates])][:top_n]
                return self._rows_from_idxs(order, sims[order])
            # unknown person - fall through to plain semantic search below

        # 4) General natural language semantic search
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

        reranked = sorted([(i, float(sims[i] + boosts[i]))
                          for i in top_idxs], key=lambda x: x[1], reverse=True)[:top_n]
        idxs = [i for i, _ in reranked]
        scores = np.array([s for _, s in reranked])
        return self._rows_from_idxs(idxs, scores)

    # Plots run to several thousand characters, but the UI only shows a snippet,
    # so trim them rather than shipping ~4 KB per result.
    PLOT_CHARS = 1200

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
                "Year": r.get("Year", r.get("Release Year")),
                "Plot": self._trim_plot(r.get("Plot")),
                "Score": r.get("_score")
            })
        return rows

    @classmethod
    def _trim_plot(cls, plot):
        if not isinstance(plot, str):
            return None
        plot = plot.strip()
        if len(plot) <= cls.PLOT_CHARS:
            return plot
        return plot[:cls.PLOT_CHARS].rsplit(" ", 1)[0] + "..."
