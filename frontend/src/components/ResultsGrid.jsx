import React from "react";
import MovieCard from "./MovieCard";

export default function ResultsGrid({ items = [], loading = false, onSelect = () => { } }) {
    if (loading) {
        return (
            <div className="grid grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="rounded bg-slate-700 p-4 animate-pulse" style={{ height: 320 }} />
                ))}
            </div>
        );
    }

    if (!items || items.length === 0) {
        return <div className="text-center text-slate-400 py-24">Search for movies</div>;
    }

    return (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {items.map((m, i) => (
                <MovieCard key={`${m.Title}-${i}`} movie={m} onClick={onSelect} />
            ))}
        </div>
    );
}
