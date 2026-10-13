const TITLE_PROVIDERS = new Set([
  'cinedna-title-catalog',
  'tmdb-catalog+heuristic-dna',
])

export function getApiSearchMode(displayMode, referenceMovie = null) {
  if (referenceMovie) return 'vibe'
  return displayMode
}

export function getResponseMode(displayMode, provider) {
  return TITLE_PROVIDERS.has(provider) ? 'title' : displayMode
}

function formatValues(values) {
  return values.join(', ')
}

function getStrictConstraints(intent) {
  const constraints = []

  if (intent.preferred_countries?.length) {
    constraints.push(`country (${formatValues(intent.preferred_countries)})`)
  }
  if (intent.excluded_countries?.length) {
    constraints.push(`excluded countries (${formatValues(intent.excluded_countries)})`)
  }

  if (intent.min_year != null && intent.max_year != null) {
    constraints.push(intent.min_year === intent.max_year
      ? `release year (${intent.min_year})`
      : `release years (${intent.min_year}\u2013${intent.max_year})`)
  } else if (intent.min_year != null) {
    constraints.push(`release year (${intent.min_year} or later)`)
  } else if (intent.max_year != null) {
    constraints.push(`release year (${intent.max_year} or earlier)`)
  }

  if (intent.exclude_themes?.length) {
    constraints.push(`excluded genres or themes (${formatValues(intent.exclude_themes)})`)
  }

  return constraints
}

export function getEmptyResultsCopy(responseMode, intent = {}) {
  if (responseMode === 'title') {
    return {
      heading: 'We could not find that movie title.',
      description: 'Check the spelling, try an alternate title, or switch to vibe discovery.',
      action: 'Describe a vibe',
    }
  }

  const constraints = getStrictConstraints(intent)

  return {
    heading: constraints.length
      ? 'No movies matched every filter.'
      : 'No strong matches yet.',
    description: constraints.length
      ? `CineDNA kept these filters strict: ${constraints.join('; ')}. Edit one constraint to widen the results.`
      : 'Try adding a mood, genre, country, or a movie you already love.',
    action: 'Edit this search',
  }
}
