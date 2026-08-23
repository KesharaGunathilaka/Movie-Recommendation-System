// Helpers for turning raw API fields into something displayable.

// Scores are cosine similarities, optionally nudged by the intent boosts in the
// backend, so clamp before showing them as a percentage.
export function matchPercent(score) {
    const value = Number(score);
    if (!Number.isFinite(value)) return null;
    return Math.max(0, Math.min(100, Math.round(value * 100)));
}

// Comma-separated fields (genre, cast) arrive with stray blanks and "unknown".
export function splitList(value, limit) {
    return String(value || "")
        .split(",")
        .map(item => item.trim())
        .filter(item => item && item.toLowerCase() !== "unknown")
        .slice(0, limit);
}
