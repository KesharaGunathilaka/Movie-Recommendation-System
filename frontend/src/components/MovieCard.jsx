import React from "react";
import dummyPoster from "../assets/Dummy.jpg";

export default function MovieCard({ movie, onClick }) {
    const poster = movie.Poster || dummyPoster;
    return (
        <div onClick={() => onClick(movie)} className="cursor-pointer rounded overflow-hidden bg-slate-800 hover:scale-[1.01] transition transform">
            <img src={poster} alt={movie.Title} className="w-full h-64 object-cover" loading="lazy" />
            <div className="p-3">
                <h3 className="font-semibold text-lg">{movie.Title}</h3>
                <p className="text-sm text-slate-300 truncate">{movie.Director || ""}</p>
                <div className="mt-2 flex items-center justify-between text-sm">
                    <span className="px-2 py-1 bg-slate-700/50 rounded">{movie.Genre?.split(",")?.[0] || "—"}</span>
                    <span className="text-slate-400">{movie.Year || ""}</span>
                </div>
            </div>
        </div>
    );
}
