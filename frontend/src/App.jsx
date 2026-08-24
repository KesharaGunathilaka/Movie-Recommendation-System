import React, { useCallback, useEffect, useState } from "react";
import SearchBar from "./components/SearchBar";
import ResultsGrid from "./components/ResultsGrid";
import MovieModal from "./components/MovieModal";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function queryFromUrl() {
  return new URLSearchParams(window.location.search).get("q") || "";
}

export default function App() {
  const [input, setInput] = useState(queryFromUrl);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState(null);
  const [topN, setTopN] = useState(12);

  const runSearch = useCallback(async (q, n) => {
    const count = n ?? topN;
    setInput(q);
    setQuery(q);
    setLoading(true);
    setError("");
    setSelected(null);

    // Keep the query in the URL so a search can be shared or reloaded.
    const url = new URL(window.location);
    url.searchParams.set("q", q);
    window.history.replaceState({}, "", url);

    try {
      const res = await axios.post(`${API_BASE}/recommend`, { query: q, top_n: count });
      setResults(res.data.results || []);
      setSearched(true);
    } catch (e) {
      console.error(e);
      setResults([]);
      setError(
        e.response?.data?.error ||
        `Could not reach the recommendation API at ${API_BASE}. Is the backend running?`
      );
    }
    setLoading(false);
  }, [topN]);

  // Run the query in the URL on first load, so shared links work.
  useEffect(() => {
    const q = queryFromUrl();
    if (q) runSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function changeCount(n) {
    setTopN(n);
    if (query) runSearch(query, n);
  }

  return (
    <div className="min-h-screen px-6 py-10">
      <header className="mx-auto max-w-6xl">
        <h1 className="text-4xl font-semibold tracking-tight text-ink-100 sm:text-5xl">
          Movie <span className="text-accent">Recommender</span>
        </h1>
        <p className="mt-2 max-w-2xl text-ink-400">
          Semantic search over 12,327 films. Describe a plot in your own words, or
          search by title, franchise, actor or director.
        </p>

        <div className="mt-8">
          <SearchBar
            value={input}
            onChange={setInput}
            onSearch={runSearch}
            loading={loading}
          />
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="topN" className="text-sm text-ink-500">Results</label>
            <select
              id="topN"
              value={topN}
              onChange={e => changeCount(Number(e.target.value))}
              className="rounded border border-ink-700 bg-ink-900 px-2 py-1 text-sm text-ink-200 focus:border-ink-500 focus:outline-none"
            >
              <option value={6}>6</option>
              <option value={12}>12</option>
              <option value={24}>24</option>
            </select>
          </div>

          {!loading && results.length > 0 && (
            <p className="text-sm text-ink-500">
              Top {results.length} for <span className="text-ink-200">"{query}"</span>
            </p>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        <ResultsGrid
          items={results}
          loading={loading}
          searched={searched}
          onSelect={setSelected}
          onRefine={runSearch}
        />
      </main>

      <footer className="mx-auto mt-12 max-w-6xl text-xs text-ink-400">
        Click a director or genre to search it. Press <span className="kbd">/</span> to search.
      </footer>

      {selected && (
        <MovieModal
          movie={selected}
          onClose={() => setSelected(null)}
          onRefine={runSearch}
        />
      )}
    </div>
  );
}
