import React, { useState } from "react";

// Each example deliberately exercises a different branch of the recommender:
// plain semantic search, title neighbours, person lookup, genre boosting and
// franchise detection.
const SUGGESTIONS = [
    "billionaire superhero",
    "movies like Interstellar",
    "Christopher Nolan movies",
    "space survival thriller",
    "star wars collection",
];

export default function SearchBar({ onSearch, loading = false, initQuery = "" }) {
    const [q, setQ] = useState(initQuery);

    function submit(e) {
        e && e.preventDefault();
        if (!q.trim() || loading) return;
        onSearch(q.trim());
    }

    function runSuggestion(s) {
        if (loading) return;
        setQ(s);
        onSearch(s);
    }

    return (
        <div className="rounded-xl border border-slate-700/60 bg-gradient-to-r from-slate-800/70 to-slate-700/50 p-5 shadow-lg sm:p-6">
            <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
                <input
                    value={q}
                    onChange={e => setQ(e.target.value)}
                    placeholder="Describe a movie, or name a title, actor or director..."
                    aria-label="Search movies"
                    className="flex-1 rounded-lg border border-slate-600 bg-slate-900/50 px-4 py-3 text-white placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
                />
                <button
                    type="submit"
                    disabled={loading || !q.trim()}
                    className="rounded-lg bg-sky-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-400"
                >
                    {loading ? "Searching..." : "Search"}
                </button>
            </form>

            <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-xs tracking-wide text-slate-500 uppercase">Try</span>
                {SUGGESTIONS.map(s => (
                    <button
                        key={s}
                        type="button"
                        onClick={() => runSuggestion(s)}
                        disabled={loading}
                        className="rounded-full border border-slate-600/70 px-3 py-1 text-sm text-slate-300 transition hover:border-sky-400/60 hover:text-sky-300 disabled:opacity-50"
                    >
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}
