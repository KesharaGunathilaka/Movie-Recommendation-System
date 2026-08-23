import React, { useState } from "react";
import SearchBar from "./components/SearchBar";
import ResultsGrid from "./components/ResultsGrid";
import MovieModal from "./components/MovieModal";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState(null);
  const [topN, setTopN] = useState(12);

  async function onSearch(q) {
    setQuery(q);
    setLoading(true);
    setError("");
    try {
      const res = await axios.post(`${API_BASE}/recommend`, { query: q, top_n: topN });
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
  }

  return (
    <div className="min-h-screen px-6 py-10">
      <header className="mx-auto max-w-6xl">
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          Movie <span className="text-sky-400">Recommender</span>
        </h1>
        <p className="mt-2 max-w-2xl text-slate-400">
          Semantic search over 12,327 films. Describe a plot in your own words, or
          search by title, franchise, actor or director.
        </p>

        <div className="mt-8">
          <SearchBar onSearch={onSearch} loading={loading} initQuery="" />
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="topN" className="text-sm text-slate-400">Results</label>
            <select
              id="topN"
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-200"
            >
              <option value={6}>6</option>
              <option value={12}>12</option>
              <option value={24}>24</option>
            </select>
          </div>

          {!loading && results.length > 0 && (
            <p className="text-sm text-slate-400">
              Top {results.length} for <span className="text-slate-200">"{query}"</span>
            </p>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}
      </header>

      <main className="mx-auto mt-8 max-w-6xl">
        <ResultsGrid
          items={results}
          loading={loading}
          searched={searched}
          onSelect={(m) => setSelected(m)}
        />
      </main>

      {selected && <MovieModal movie={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
