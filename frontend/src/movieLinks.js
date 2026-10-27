function isValidTmdbSourceId(value) {
  const sourceId = String(value || '')
  return /^\d{1,12}$/.test(sourceId) && /[1-9]/.test(sourceId)
}

export function getMovieProfileHref(movie, currentSearch = '') {
  const params = new URLSearchParams(currentSearch)
  params.set('movie', movie.title)
  params.delete('source')
  params.delete('source_id')
  if (movie.source === 'tmdb' && isValidTmdbSourceId(movie.source_id)) {
    params.set('source', 'tmdb')
    params.set('source_id', String(movie.source_id))
  }
  return `?${params.toString()}`
}

export function getMovieProfileExitHref(currentHref) {
  const url = new URL(currentHref, 'http://localhost')
  url.searchParams.delete('movie')
  url.searchParams.delete('source')
  url.searchParams.delete('source_id')
  return `${url.pathname}${url.search}${url.hash}`
}

export function getAppHomeHref(currentHref) {
  const url = new URL(currentHref, 'http://localhost')
  url.searchParams.delete('movie')
  url.searchParams.delete('source')
  url.searchParams.delete('source_id')
  return `${url.pathname}${url.search}`
}

export function parseMovieProfileLink(search) {
  const params = new URLSearchParams(search)
  const title = params.get('movie')
  if (!title || !title.trim() || title.length > 200) return null
  const sourceParam = params.get('source')
  if (sourceParam !== null && sourceParam !== 'cinedna' && sourceParam !== 'tmdb') {
    return null
  }
  const source = sourceParam || 'cinedna'
  const sourceId = params.get('source_id')
  if (source === 'tmdb' && !isValidTmdbSourceId(sourceId)) return null
  return {
    title: title.trim(),
    source,
    sourceId: source === 'tmdb' ? sourceId : null,
  }
}
