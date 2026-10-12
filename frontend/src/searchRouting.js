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

function formatConstraintList(constraints) {
  if (constraints.length === 1) return constraints[0]
  if (constraints.length === 2) return `${constraints[0]} and ${constraints[1]}`
  return `${constraints.slice(0, -1).join(', ')}, and ${constraints.at(-1)}`
}

export function getEmptyResultsCopy(responseMode, intent = {}) {
  if (responseMode === 'title') {
    return {
      heading: 'We could not find that movie title.',
      description: 'Check the spelling, try an alternate title, or switch to vibe discovery.',
      action: 'Describe a vibe',
    }
  }

  const constraints = []
  if (intent.preferred_countries?.length || intent.excluded_countries?.length) {
    constraints.push('country')
  }
  if (intent.min_year != null || intent.max_year != null) {
    constraints.push('release period')
  }
  if (intent.include_themes?.length || intent.exclude_themes?.length) {
    constraints.push('genre or theme')
  }

  return {
    heading: constraints.length
      ? 'No movies matched every filter.'
      : 'No strong matches yet.',
    description: constraints.length
      ? `CineDNA kept your ${formatConstraintList(constraints)} filters strict. Edit one constraint to widen the results.`
      : 'Try adding a mood, genre, country, or a movie you already love.',
    action: 'Edit this search',
  }
}
