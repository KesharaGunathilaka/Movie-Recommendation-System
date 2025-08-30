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
  const [selected, setSelected] = useState(null);
  const [topN, setTopN] = useState(12);

  async function onSearch(q) {
    setQuery(q);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/recommend`, { query: q, top_n: topN });
      setResults(res.data.results || []);
    } catch (e) {
      console.error(e);
      alert("Recommendation error - check backend console");
    }
    setLoading(false);
  }

  return (
    <div className="min-h-screen p-6">
      <header className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-extrabold">Movie Recommender</h1>
            <p className="text-slate-300">Find movies by title, franchise, actor, director or natural language.</p>
          </div>
          {/* <div className="text-right">
            <span className="inline-block px-3 py-1 bg-slate-700/50 rounded-full text-sm">Semantic + TF-IDF hybrid</span>
          </div> */}
        </div>

        <SearchBar onSearch={onSearch} initQuery="" />

        <div className="mt-4 flex items-center gap-3">
          <label className="text-sm text-slate-300">Results</label>
          <select value={topN} onChange={(e) => setTopN(Number(e.target.value))} className="bg-slate-700/40 rounded px-2 py-1">
            <option value={6}>6</option>
            <option value={12}>12</option>
            <option value={24}>24</option>
          </select>
        </div>

      </header>

      <main className="max-w-6xl mx-auto mt-8">
        <ResultsGrid items={results} loading={loading} onSelect={(m) => setSelected(m)} />
      </main>

      {selected && <MovieModal movie={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
