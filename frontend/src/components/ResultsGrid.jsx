import React from "react";
import MovieCard from "./MovieCard";

const GRID = "grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

export default function ResultsGrid({ items = [], loading = false, searched = false,
    onSelect = () => { }, onRefine = () => { } }) {
    if (loading) {
        return (
            <div className={GRID}>
                {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className="loading-skeleton h-60 rounded-lg border border-ink-800" />
                ))}
            </div>
        );
    }

    if (!items || items.length === 0) {
        return (
            <div className="rounded-lg border border-dashed border-ink-700 py-20 text-center">
                <p className="text-ink-300">
                    {searched ? "No matches for that search." : "Search for a film to get started"}
                </p>
                <p className="mt-2 text-sm text-ink-500">
                    {searched
                        ? "Try describing the plot instead, or pick one of the examples above."
                        : "Describe a plot in your own words, or name a title, actor or director."}
                </p>
            </div>
        );
    }

    return (
        <div className={GRID}>
            {items.map((m, i) => (
                <MovieCard key={`${m.Title}-${i}`} movie={m} rank={i + 1} index={i}
                    onClick={onSelect} onRefine={onRefine} />
            ))}
        </div>
    );
}
