import hashlib
import os
import re

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
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
        chunk_texts, owners = [], []
        for pos, (_, row) in enumerate(self.df.iterrows()):
            for chunk in self._row_to_chunks(row):
                chunk_texts.append(chunk)
                owners.append(pos)
        self.chunk_owner = np.asarray(owners, dtype=np.int64)

        cache_path = self._cache_path(cache_dir, model_name, chunk_texts)
        cached = self._load_cached_embeddings(cache_path)

        if cached is not None:
            print(f"[Recommender] Loaded cached embeddings: "
                  f"{len(chunk_texts)} chunks over {len(texts)} movies")
            self.chunk_embeddings = cached.to(self.device)
        else:
            print(f"[Recommender] Encoding {len(chunk_texts)} chunks over "
                  f"{len(texts)} movies (one-off, cached for later runs)")
            self.chunk_embeddings = self.model.encode(
                chunk_texts,
                convert_to_tensor=True,
                show_progress_bar=True,
                batch_size=batch_size,
                normalize_embeddings=True
            )
            self._save_embeddings(cache_path, self.chunk_embeddings)
            print(f"[Recommender] Cached embeddings to {cache_path}")

        # A film-level vector (mean of its chunks) is still needed for
        # film-to-film neighbour search.
        self.embeddings = self._film_embeddings(len(texts))

        # Sparse lexical index over the *full* text. The dense encoder only ever
        # sees the first 384 tokens, so a rare word buried deep in a plot
        # ("billionaire" in Iron Man) is invisible to it. TF-IDF catches those,
        # and the two signals are combined at query time.
        self.vectorizer = TfidfVectorizer(
            stop_words="english", sublinear_tf=True, min_df=2)
        self.lexical_matrix = self.vectorizer.fit_transform(texts)

        # lower titles for lookup
        self.titles = self.df["Title"].astype(str)
        self.titles_lower = self.titles.str.lower().str.strip().tolist()

    # ---- chunking ----
    # A whole film compressed into one vector loses specifics: Iron Man's plot
    # opens "Genius, billionaire, and playboy Tony Stark", but that phrase is
    # diluted across ~2000 tokens, of which the encoder only reads 384. So each
    # film is split into a short profile plus a few plot windows, and a film
    # scores as its single best-matching piece.
    PLOT_WORDS_PER_CHUNK = 120
    MAX_PLOT_CHUNKS = 4

    def _row_to_chunks(self, row):
        title = _nz(row.get("Title", ""))
        year = _nz(row.get("Year", row.get("Release Year", "")))
        genre = _nz(row.get("Genre", ""))
        keywords = re.sub(r"[\[\]'\"]", "", _nz(row.get("Keywords", "")))
        director = _nz(row.get("Director", ""))
        cast = _nz(row.get("Cast", ""))
        plot = _nz(row.get("Plot", ""))

        head = f"{title} ({year})" if year else title
        profile = ". ".join(p for p in [
            head,
            f"Genres: {genre}" if genre.strip() else "",
            f"Keywords: {keywords}" if keywords.strip() else "",
            f"Directed by {director}" if director.strip() else "",
            f"Starring {cast}" if cast.strip() else "",
        ] if p)
        chunks = [profile]

        words = plot.split()
        step = self.PLOT_WORDS_PER_CHUNK
        for i in range(0, min(len(words), step * self.MAX_PLOT_CHUNKS), step):
            window = " ".join(words[i:i + step])
            if window.strip():
                # prefix the title so a bare plot window keeps its subject
                chunks.append(f"{head}. {window}")
        return chunks

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
        """One searchable document per film.

        The encoder truncates at 384 tokens but these documents run to ~2000, so
        ordering matters: lead with the fields that identify a film and let the
        tail of the plot fall off the end. The previous template repeated both
        keywords and plot, which spent most of that small window on duplicates.
        """
        title = _nz(row.get("Title", ""))
        director = _nz(row.get("Director", ""))
        cast = _nz(row.get("Cast", ""))
        genre = _nz(row.get("Genre", ""))
        # Keywords are stored as a stringified list: "['magical', 'queen']"
        keywords = re.sub(r"[\[\]'\"]", "", _nz(row.get("Keywords", "")))
        plot = _nz(row.get("Plot", ""))
        year = _nz(row.get("Year", row.get("Release Year", "")))

        parts = [f"{title} ({year})" if year else title]
        for label, value in (("Genres", genre), ("Keywords", keywords),
                             ("Directed by", director), ("Starring", cast),
                             ("Plot", plot)):
            value = value.strip()
            if value:
                sep = ":" if label in ("Genres", "Keywords", "Plot") else ""
                parts.append(f"{label}{sep} {value}")
        return ". ".join(p.strip(" .") for p in parts)

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
    # How much the lexical signal counts relative to the dense one. Both are
    # cosine similarities, but lexical scores are far sparser, so it needs
    # weighting up to matter.
    LEXICAL_WEIGHT = 0.5

    def _film_embeddings(self, n_films):
        """Mean of each film's chunk vectors, renormalised."""
        owner = torch.as_tensor(self.chunk_owner, device=self.chunk_embeddings.device)
        dim = self.chunk_embeddings.shape[1]
        summed = torch.zeros((n_films, dim), device=self.chunk_embeddings.device,
                             dtype=self.chunk_embeddings.dtype)
        summed.index_add_(0, owner, self.chunk_embeddings)
        counts = torch.zeros(n_films, device=summed.device, dtype=summed.dtype)
        counts.index_add_(0, owner, torch.ones_like(owner, dtype=summed.dtype))
        return torch.nn.functional.normalize(summed / counts.unsqueeze(1), dim=1)

    def _semantic_query_scores(self, query):
        """Best-matching chunk per film, rather than one diluted whole-film vector."""
        q_emb = self.model.encode(
            [query], convert_to_tensor=True, normalize_embeddings=True)
        chunk_sims = util.cos_sim(q_emb, self.chunk_embeddings)[0]
        owner = torch.as_tensor(self.chunk_owner, device=chunk_sims.device)
        best = torch.full((len(self.df),), -1.0, device=chunk_sims.device,
                          dtype=chunk_sims.dtype)
        best.scatter_reduce_(0, owner, chunk_sims, reduce="amax", include_self=True)
        return best.cpu().numpy()

    def _lexical_query_scores(self, query):
        q_vec = self.vectorizer.transform([query])
        # TfidfVectorizer L2-normalises rows, so this dot product is a cosine
        return (self.lexical_matrix @ q_vec.T).toarray().ravel()

    def _query_scores(self, query):
        """Dense meaning + sparse keyword match."""
        return (self._semantic_query_scores(query)
                + self.LEXICAL_WEIGHT * self._lexical_query_scores(query))

    def _neighbors(self, idx, top_n):
        """Films closest to the film at `idx`.

        Compared chunk-to-chunk rather than through the averaged film vectors:
        averaging re-introduces exactly the dilution that chunking removes, and
        made "movies like Interstellar" rank obscure titles above The Martian.
        """
        owner = torch.as_tensor(self.chunk_owner, device=self.chunk_embeddings.device)
        target = self.chunk_embeddings[owner == idx]
        # best pairing between any chunk of the target and any chunk of a candidate
        pair = util.cos_sim(target, self.chunk_embeddings).max(dim=0).values
        best = torch.full((len(self.df),), -1.0, device=pair.device, dtype=pair.dtype)
        best.scatter_reduce_(0, owner, pair, reduce="amax", include_self=True)
        sims = best.cpu().numpy()
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
                sims = self._query_scores(text)
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
                sims = self._query_scores(text)
                candidates = np.where(role_mask)[0]
                order = candidates[np.argsort(-sims[candidates])][:top_n]
                return self._rows_from_idxs(order, sims[order])
            # unknown person - fall through to plain semantic search below

        # 4) General natural language semantic search
        sims = self._query_scores(text)
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
