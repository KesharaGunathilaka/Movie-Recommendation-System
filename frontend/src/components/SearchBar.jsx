import React, { useEffect, useRef } from "react";

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

export default function SearchBar({ value, onChange, onSearch, loading = false }) {
    const inputRef = useRef(null);

    // "/" focuses the search box from anywhere, the way most search UIs behave.
    useEffect(() => {
        function onKey(e) {
            if (e.key === "/" && document.activeElement !== inputRef.current) {
                e.preventDefault();
                inputRef.current?.focus();
            }
        }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, []);

    function submit(e) {
        e && e.preventDefault();
        if (!value.trim() || loading) return;
        onSearch(value.trim());
    }

    function chipClass(active) {
        const base = "rounded-full border px-3 py-1 text-sm transition disabled:opacity-50 ";
        return base + (active
            ? "border-accent-dim bg-ink-800 text-accent-soft"
            : "border-ink-700 text-ink-400 hover:border-ink-500 hover:text-ink-100");
    }

    return (
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
            <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                    <input
                        ref={inputRef}
                        value={value}
                        onChange={e => onChange(e.target.value)}
                        onKeyDown={e => { if (e.key === "Escape") onChange(""); }}
                        placeholder="Describe a film, or name a title, actor or director..."
                        aria-label="Search films"
                        className="w-full rounded-lg border border-ink-700 bg-ink-950 px-4 py-3 pr-16 text-ink-100 placeholder:text-ink-500 focus:border-accent-dim focus:outline-none"
                    />
                    {value ? (
                        <button
                            type="button"
                            onClick={() => { onChange(""); inputRef.current?.focus(); }}
                            aria-label="Clear search"
                            className="absolute top-1/2 right-3 -translate-y-1/2 rounded px-2 text-ink-500 transition hover:text-ink-100"
                        >
                            ✕
                        </button>
                    ) : (
                        <span className="kbd absolute top-1/2 right-3 hidden -translate-y-1/2 sm:block">/</span>
                    )}
                </div>
                <button
                    type="submit"
                    disabled={loading || !value.trim()}
                    className="rounded-lg bg-accent px-6 py-3 font-semibold text-ink-950 transition hover:bg-accent-soft disabled:cursor-not-allowed disabled:bg-ink-700 disabled:text-ink-400"
                >
                    {loading ? "Searching..." : "Search"}
                </button>
            </form>

            <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-xs tracking-wide text-ink-500 uppercase">Try</span>
                {SUGGESTIONS.map(s => (
                    <button
                        key={s}
                        type="button"
                        onClick={() => !loading && onSearch(s)}
                        disabled={loading}
                        className={chipClass(value === s)}
                    >
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}
