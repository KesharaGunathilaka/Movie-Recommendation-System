import React, { useState } from "react";

export default function SearchBar({ onSearch, initQuery = "" }) {
    const [q, setQ] = useState(initQuery);

    const suggestions = [
    ];

    function submit(e) {
        e && e.preventDefault();
        if (!q.trim()) return;
        onSearch(q.trim());
    }

    return (
        <div className="bg-gradient-to-r from-slate-800/60 to-slate-700/50 rounded-lg p-6 shadow-lg">
            <form onSubmit={submit} className="flex gap-3">
                <input value={q} onChange={e => setQ(e.target.value)} className="flex-1 px-4 py-3 bg-transparent border border-slate-600 rounded focus:outline-none" />
                <button type="submit" className="px-5 py-2 bg-accent rounded text-amber-400 font-semibold">Search</button>
            </form>

            <div className="mt-3 flex gap-2">
                {suggestions.map(s => (
                    <button key={s} onClick={() => { setQ(s); onSearch(s); }} className="text-sm px-3 py-1 bg-slate-700/60 rounded hover:bg-slate-700/80">
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}
