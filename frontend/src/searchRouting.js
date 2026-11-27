const TITLE_PROVIDERS = new Set([
  'cinedna-title-catalog',
  'tmdb-catalog+heuristic-dna',
])

export const MAX_SEARCH_QUERY_LENGTH = 500
const MAX_INTENT_HIGHLIGHTS = 8

function titleCase(value) {
  return value
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function stringValues(values) {
  return Array.isArray(values)
    ? values
      .filter((value) => typeof value === 'string' && value.trim())
      .map((value) => value.trim())
    : []
}

export function validateSearchQuery(query, displayMode) {
  const normalized = typeof query === 'string'
    ? query.trim().replace(/\s+/g, ' ')
    : ''
  const minimumLength = displayMode === 'vibe' ? 3 : 1

  if (normalized.length < minimumLength) {
    return {
      query: normalized,
      error: displayMode === 'vibe'
        ? 'Describe your movie vibe in at least 3 characters.'
        : 'Enter a movie title to search.',
    }
  }

  if (normalized.length > MAX_SEARCH_QUERY_LENGTH) {
    return {
      query: normalized,
      error: `Keep your search to ${MAX_SEARCH_QUERY_LENGTH} characters or fewer.`,
    }
  }

  return { query: normalized, error: '' }
}

export function getApiSearchMode(displayMode, referenceMovie = null) {
  if (referenceMovie) return 'vibe'
  return displayMode
}

export function getResponseMode(displayMode, provider) {
  return TITLE_PROVIDERS.has(provider) ? 'title' : displayMode
}

export function getIntentHighlights(intent = {}) {
  const highlights = []
  const seen = new Set()
  const add = (label, kind = 'filter') => {
    const key = `${kind}-${label}`
    if (highlights.length < MAX_INTENT_HIGHLIGHTS && !seen.has(key)) {
      seen.add(key)
      highlights.push({ label, kind })
    }
  }

  if (intent.min_year != null && intent.max_year != null) {
    add(intent.min_year === intent.max_year
      ? `Released ${intent.min_year}`
      : `Released ${intent.min_year}\u2013${intent.max_year}`)
  } else if (intent.min_year != null) {
    add(`Released since ${intent.min_year}`)
  } else if (intent.max_year != null) {
    add(`Released through ${intent.max_year}`)
  }

  stringValues(intent.preferred_countries)
    .forEach((country) => add(`From ${country}`))
  stringValues(intent.excluded_countries)
    .forEach((country) => add(`Not from ${country}`, 'exclude'))
  stringValues(intent.include_themes)
    .forEach((theme) => add(titleCase(theme)))
  stringValues(intent.exclude_themes)
    .forEach((theme) => add(`No ${titleCase(theme)}`, 'exclude'))

  Object.entries(intent.target_dimensions ?? {})
    .filter(([, score]) => Number.isFinite(score))
    .sort(([nameA, scoreA], [nameB, scoreB]) => (
      scoreB - scoreA || nameA.localeCompare(nameB)
    ))
    .forEach(([name, score]) => add(`${titleCase(name)} ${Math.round(score)}`, 'target'))

  return highlights
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
  if (intent.excluded_titles?.length) {
    constraints.push(`excluded movies (${formatValues(intent.excluded_titles)})`)
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
