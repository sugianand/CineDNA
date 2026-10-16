export function getMovieProfileHref(movie, currentSearch = '') {
  const params = new URLSearchParams(currentSearch)
  params.set('movie', movie.title)
  params.delete('source')
  params.delete('source_id')
  if (movie.source === 'tmdb' && /^\d+$/.test(String(movie.source_id || ''))) {
    params.set('source', 'tmdb')
    params.set('source_id', String(movie.source_id))
  }
  return `?${params.toString()}`
}

export function parseMovieProfileLink(search) {
  const params = new URLSearchParams(search)
  const title = params.get('movie')
  if (!title || !title.trim() || title.length > 200) return null
  const source = params.get('source') === 'tmdb' ? 'tmdb' : 'cinedna'
  const sourceId = params.get('source_id')
  return {
    title: title.trim(),
    source,
    sourceId: source === 'tmdb' && /^\d{1,12}$/.test(sourceId || '') ? sourceId : null,
  }
}
