import React from "react";
import { matchPercent, splitList } from "../lib/movie";

const MAX_GENRES = 3;
const MAX_CAST = 3;

export default function MovieCard({ movie, rank, onClick, onRefine, index = 0 }) {
    const match = matchPercent(movie.Score);
    const genres = splitList(movie.Genre, MAX_GENRES);
    const cast = splitList(movie.Cast, MAX_CAST).join(", ");

    // Refinements search a new query instead of opening the film, so stop the
    // click from also triggering the card.
    function refine(e, query) {
        e.stopPropagation();
        onRefine(query);
    }

    return (
        <div
            role="button"
            tabIndex={0}
            onClick={() => onClick(movie)}
            onKeyDown={e => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onClick(movie);
                }
            }}
            style={{ animationDelay: `${Math.min(index, 11) * 35}ms` }}
            className="card-in card-lift group flex h-full cursor-pointer flex-col rounded-xl border border-ink-700 bg-ink-900 p-5 text-left hover:border-ink-600 hover:bg-ink-850 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-dim"
        >
            <div className="flex items-center justify-between text-xs text-ink-500">
                <span className="font-medium">#{rank}</span>
                <span>{movie.Year || "—"}</span>
            </div>

            <h3 className="mt-2 text-lg leading-snug font-semibold text-ink-100 transition-colors group-hover:text-accent-soft">
                {movie.Title}
            </h3>

            {movie.Director && (
                <button
                    type="button"
                    onClick={e => refine(e, `${movie.Director} movies`)}
                    title={`Find more by ${movie.Director}`}
                    className="mt-1 truncate text-left text-sm text-ink-400 underline-offset-4 transition hover:text-accent hover:underline"
                >
                    {movie.Director}
                </button>
            )}

            {genres.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {genres.map(genre => (
                        <button
                            key={genre}
                            type="button"
                            onClick={e => refine(e, genre)}
                            title={`Search ${genre}`}
                            className="rounded-full border border-ink-700 bg-ink-800 px-2.5 py-0.5 text-xs text-ink-300 capitalize transition hover:border-ink-500 hover:text-ink-100"
                        >
                            {genre}
                        </button>
                    ))}
                </div>
            )}

            {cast && (
                <p className="mt-3 line-clamp-2 text-sm text-ink-400">
                    <span className="text-ink-500">Starring </span>{cast}
                </p>
            )}

            {movie.Plot && (
                <p className="mt-2 line-clamp-3 text-sm text-ink-500">{movie.Plot}</p>
            )}

            {match !== null && (
                <div className="mt-auto flex items-center gap-3 pt-4">
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-ink-700">
                        <div className="h-full rounded-full bg-accent-dim transition-all duration-500 group-hover:bg-accent-soft"
                            style={{ width: `${match}%` }} />
                    </div>
                    <span className="text-xs tabular-nums text-accent">{match}%</span>
                </div>
            )}
        </div>
    );
}
