import React from "react";
import dummyPoster from "../assets/Dummy.jpg";

export default function MovieModal({ movie, onClose }) {
    const poster = movie.Poster || dummyPoster;
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/60" onClick={onClose}></div>
            <div className="relative bg-slate-900 rounded-lg max-w-4xl mx-4 shadow-lg overflow-hidden grid grid-cols-1 md:grid-cols-3">
                <img src={poster} className="w-full h-96 object-cover md:col-span-1" alt={movie.Title} />
                <div className="p-6 md:col-span-2">
                    <div className="flex items-start justify-between">
                        <div>
                            <h2 className="text-2xl font-bold">{movie.Title}</h2>
                            <p className="text-slate-400">{movie.Year} • {movie.Genre}</p>
                        </div>
                        <button onClick={onClose} className="text-slate-300">Close</button>
                    </div>

                    <div className="mt-4 text-slate-300">
                        <p><strong>Director:</strong> {movie.Director}</p>
                        <p className="mt-2"><strong>Cast:</strong> {movie.Cast}</p>
                        <p className="mt-4"><strong>Plot:</strong> {movie.Plot ? movie.Plot.split(' ').slice(0, 80).join(' ') + '...' : "—"}</p>
                        <p className="mt-4 text-sm text-slate-400">Score: {Number(movie.Score || movie._score || 0).toFixed(3)}</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
