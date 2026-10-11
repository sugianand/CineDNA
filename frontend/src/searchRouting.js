const TITLE_PROVIDERS = new Set([
  'cinedna-title-catalog',
  'tmdb-catalog+heuristic-dna',
])

export function getApiSearchMode(displayMode, referenceMovie = null) {
  if (referenceMovie) return 'vibe'
  return displayMode === 'vibe' ? 'auto' : displayMode
}

export function getResponseMode(displayMode, provider) {
  return TITLE_PROVIDERS.has(provider) ? 'title' : displayMode
}
