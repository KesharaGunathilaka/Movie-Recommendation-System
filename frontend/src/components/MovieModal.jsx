import React, { useEffect } from "react";
import { matchPercent, splitList } from "../lib/movie";

export default function MovieModal({ movie, onClose, onRefine }) {
    useEffect(() => {
        function onKey(e) {
            if (e.key === "Escape") onClose();
        }
        window.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            window.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [onClose]);

    const match = matchPercent(movie.Score);
    const genres = splitList(movie.Genre, 6);
    const plotWords = movie.Plot ? movie.Plot.split(" ").slice(0, 120).join(" ") : "";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

            <div className="card-in relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-ink-700 bg-ink-900 p-6 shadow-2xl sm:p-8">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-ink-100">{movie.Title}</h2>
                        <p className="mt-1 text-sm text-ink-400">
                            {movie.Year || "—"}
                            {match !== null && <span className="text-accent"> · {match}% match</span>}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Close"
                        className="rounded-md border border-ink-700 px-3 py-1 text-sm text-ink-400 transition hover:border-ink-500 hover:text-ink-100"
                    >
                        Esc
                    </button>
                </div>

                {genres.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                        {genres.map(genre => (
                            <button
                                key={genre}
                                type="button"
                                onClick={() => onRefine(genre)}
                                className="rounded-full border border-ink-700 bg-ink-800 px-3 py-1 text-xs text-ink-300 capitalize transition hover:border-ink-500 hover:text-ink-100"
                            >
                                {genre}
                            </button>
                        ))}
                    </div>
                )}

                <dl className="mt-6 space-y-3 text-sm">
                    <div>
                        <dt className="text-ink-500">Director</dt>
                        <dd>
                            {movie.Director ? (
                                <button
                                    type="button"
                                    onClick={() => onRefine(movie.Director + " movies")}
                                    className="text-ink-200 underline-offset-4 transition hover:text-accent hover:underline"
                                >
                                    {movie.Director}
                                </button>
                            ) : (
                                <span className="text-ink-200">—</span>
                            )}
                        </dd>
                    </div>
                    <div>
                        <dt className="text-ink-500">Cast</dt>
                        <dd className="text-ink-200">{movie.Cast || "—"}</dd>
                    </div>
                </dl>

                <div className="mt-6">
                    <h3 className="text-sm text-ink-500">Plot</h3>
                    <p className="mt-2 leading-relaxed text-ink-300">
                        {plotWords ? plotWords + "..." : "—"}
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => onRefine("movies like " + movie.Title)}
                    className="mt-6 w-full rounded-md border border-ink-700 py-2.5 text-sm text-ink-300 transition hover:border-ink-500 hover:text-ink-100"
                >
                    Find films like {movie.Title}
                </button>
            </div>
        </div>
    );
}
