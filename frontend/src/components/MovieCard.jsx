import React from "react";
import { matchPercent, splitList } from "../lib/movie";

const MAX_GENRES = 3;
const MAX_CAST = 3;

export default function MovieCard({ movie, rank, onClick }) {
    const match = matchPercent(movie.Score);
    const genres = splitList(movie.Genre, MAX_GENRES);
    const cast = splitList(movie.Cast, MAX_CAST).join(", ");

    return (
        <button
            type="button"
            onClick={() => onClick(movie)}
            className="group flex h-full w-full flex-col rounded-xl border border-slate-700/60 bg-slate-800/40 p-5 text-left transition hover:-translate-y-1 hover:border-sky-400/60 hover:bg-slate-800/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        >
            <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="font-semibold">#{rank}</span>
                <span>{movie.Year || "—"}</span>
            </div>

            <h3 className="mt-2 text-lg leading-snug font-semibold text-white group-hover:text-sky-300">
                {movie.Title}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-400">
                {movie.Director || "Unknown director"}
            </p>

            {genres.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                    {genres.map(genre => (
                        <span key={genre} className="rounded-full bg-slate-700/60 px-2.5 py-0.5 text-xs text-slate-200 capitalize">
                            {genre}
                        </span>
                    ))}
                </div>
            )}

            {cast && (
                <p className="mt-3 line-clamp-2 text-sm text-slate-400">
                    <span className="text-slate-500">Starring </span>{cast}
                </p>
            )}

            {movie.Plot && (
                <p className="mt-2 line-clamp-3 text-sm text-slate-500">{movie.Plot}</p>
            )}

            {match !== null && (
                <div className="mt-auto flex items-center gap-3 pt-4">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700">
                        <div
                            className="h-full rounded-full bg-gradient-to-r from-sky-400 to-emerald-400"
                            style={{ width: `${match}%` }}
                        />
                    </div>
                    <span className="text-xs font-medium tabular-nums text-sky-300">{match}% match</span>
                </div>
            )}
        </button>
    );
}
