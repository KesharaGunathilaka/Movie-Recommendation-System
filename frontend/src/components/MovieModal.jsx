import React, { useEffect } from "react";
import { matchPercent, splitList } from "../lib/movie";

export default function MovieModal({ movie, onClose }) {
    useEffect(() => {
        function onKey(e) {
            if (e.key === "Escape") onClose();
        }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);

    const match = matchPercent(movie.Score);
    const genres = splitList(movie.Genre, 6);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

            <div className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl sm:p-8">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white">{movie.Title}</h2>
                        <p className="mt-1 text-slate-400">
                            {movie.Year || "—"}
                            {match !== null && <span className="text-sky-300"> · {match}% match</span>}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Close"
                        className="rounded-lg border border-slate-700 px-3 py-1 text-slate-400 transition hover:border-slate-500 hover:text-white"
                    >
                        Close
                    </button>
                </div>

                {genres.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                        {genres.map(genre => (
                            <span key={genre} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-200 capitalize">
                                {genre}
                            </span>
                        ))}
                    </div>
                )}

                <dl className="mt-6 space-y-3 text-sm">
                    <div>
                        <dt className="text-slate-500">Director</dt>
                        <dd className="text-slate-200">{movie.Director || "—"}</dd>
                    </div>
                    <div>
                        <dt className="text-slate-500">Cast</dt>
                        <dd className="text-slate-200">{movie.Cast || "—"}</dd>
                    </div>
                </dl>

                <div className="mt-6">
                    <h3 className="text-slate-500">Plot</h3>
                    <p className="mt-2 leading-relaxed text-slate-300">
                        {movie.Plot ? `${movie.Plot.split(" ").slice(0, 120).join(" ")}...` : "—"}
                    </p>
                </div>
            </div>
        </div>
    );
}
