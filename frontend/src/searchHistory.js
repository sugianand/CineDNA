const VALID_SEARCH_MODES = new Set(['vibe', 'title'])
const MAX_RECENT_SEARCHES = 5

function isValidReferenceMovie(movie) {
  return Boolean(
    movie
    && typeof movie === 'object'
    && typeof movie.title === 'string'
    && Number.isInteger(movie.year)
    && typeof movie.country === 'string'
    && Array.isArray(movie.genres)
    && Array.isArray(movie.themes)
    && movie.dimensions
    && typeof movie.dimensions === 'object'
    && !Array.isArray(movie.dimensions)
    && Object.values(movie.dimensions).every((value) => Number.isInteger(value))
    && typeof movie.summary === 'string'
  )
}

function normalizeSearch(entry) {
  if (typeof entry === 'string') {
    const query = entry.trim().replace(/\s+/g, ' ')
    if (!query) return null

    // Legacy entries did not record their mode. Searches shorter than three
    // characters could only have succeeded as title searches.
    return { query, mode: query.length < 3 ? 'title' : 'vibe' }
  }

  if (!entry || typeof entry.query !== 'string' || !VALID_SEARCH_MODES.has(entry.mode)) {
    return null
  }

  const query = entry.query.trim().replace(/\s+/g, ' ')
  if (!query) return null

  if ('referenceMovie' in entry) {
    if (!isValidReferenceMovie(entry.referenceMovie)) return null
    return { query, mode: entry.mode, referenceMovie: entry.referenceMovie }
  }

  return { query, mode: entry.mode }
}

export function parseRecentSearches(serialized) {
  try {
    const entries = JSON.parse(serialized || '[]')
    if (!Array.isArray(entries)) return []

    return entries
      .map(normalizeSearch)
      .filter(Boolean)
      .slice(0, MAX_RECENT_SEARCHES)
  } catch {
    return []
  }
}

export function updateRecentSearches(current, query, mode, referenceMovie = null) {
  const nextSearch = normalizeSearch({
    query,
    mode,
    ...(referenceMovie ? { referenceMovie } : {}),
  })
  if (!nextSearch) return current

  return [
    nextSearch,
    ...current.filter((entry) => entry.query.toLowerCase() !== nextSearch.query.toLowerCase()),
  ].slice(0, MAX_RECENT_SEARCHES)
}
