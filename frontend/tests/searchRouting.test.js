import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getApiSearchMode,
  getEmptyResultsCopy,
  getIntentHighlights,
  getResponseMode,
  MAX_SEARCH_QUERY_LENGTH,
  validateSearchQuery,
} from '../src/searchRouting.js'

test('search validation normalizes whitespace before enforcing limits', () => {
  assert.deepEqual(validateSearchQuery('  dark   mystery  ', 'vibe'), {
    query: 'dark mystery',
    error: '',
  })
  assert.deepEqual(validateSearchQuery(' x ', 'title'), {
    query: 'x',
    error: '',
  })
})

test('search validation explains mode-specific minimum lengths', () => {
  assert.match(validateSearchQuery('  x  ', 'vibe').error, /at least 3 characters/)
  assert.match(validateSearchQuery('   ', 'title').error, /movie title/)
})

test('search validation rejects queries beyond the API limit', () => {
  assert.equal(validateSearchQuery('x'.repeat(MAX_SEARCH_QUERY_LENGTH), 'vibe').error, '')
  assert.match(
    validateSearchQuery('x'.repeat(MAX_SEARCH_QUERY_LENGTH + 1), 'vibe').error,
    /500 characters or fewer/,
  )
})

test('explicit search modes stay explicit', () => {
  assert.equal(getApiSearchMode('vibe'), 'vibe')
  assert.equal(getApiSearchMode('title'), 'title')
})

test('similarity searches preserve explicit vibe routing', () => {
  assert.equal(getApiSearchMode('vibe', { title: 'Interstellar' }), 'vibe')
})

test('catalog responses render as title results', () => {
  assert.equal(getResponseMode('vibe', 'cinedna-title-catalog'), 'title')
  assert.equal(getResponseMode('vibe', 'tmdb-catalog+heuristic-dna'), 'title')
  assert.equal(getResponseMode('vibe', 'rule-based-v0.1'), 'vibe')
})

test('intent highlights summarize filters before strongest DNA targets', () => {
  const highlights = getIntentHighlights({
    target_dimensions: { humor: 45, darkness: 80, emotional_intensity: 65 },
    include_themes: ['dark_comedy'],
    exclude_themes: ['horror'],
    preferred_countries: ['India'],
    excluded_countries: ['Japan'],
    min_year: 2010,
    max_year: 2019,
  })

  assert.deepEqual(highlights, [
    { label: 'Released 2010\u20132019', kind: 'filter' },
    { label: 'From India', kind: 'filter' },
    { label: 'Not from Japan', kind: 'exclude' },
    { label: 'Dark Comedy', kind: 'filter' },
    { label: 'No Horror', kind: 'exclude' },
    { label: 'Darkness 80', kind: 'target' },
    { label: 'Emotional Intensity 65', kind: 'target' },
    { label: 'Humor 45', kind: 'target' },
  ])
})

test('intent highlights cap noisy responses and ignore malformed values', () => {
  const highlights = getIntentHighlights({
    target_dimensions: {
      action: 70,
      darkness: 60,
      humor: 50,
      mystery: 40,
      romance: 30,
      spectacle: 20,
      invalid: 'high',
    },
    include_themes: [' thriller ', 'thriller', '', null],
    preferred_countries: 'India',
    min_year: 2020,
  })

  assert.equal(highlights.length, 8)
  assert.deepEqual(highlights.slice(0, 2), [
    { label: 'Released since 2020', kind: 'filter' },
    { label: 'Thriller', kind: 'filter' },
  ])
  assert.equal(highlights.some(({ label }) => label.includes('Invalid')), false)
})

test('intent highlights explain exact and upper-bound release years', () => {
  assert.deepEqual(getIntentHighlights({ min_year: 1999, max_year: 1999 }), [
    { label: 'Released 1999', kind: 'filter' },
  ])
  assert.deepEqual(getIntentHighlights({ max_year: 1970 }), [
    { label: 'Released through 1970', kind: 'filter' },
  ])
})

test('empty vibe results explain which strict constraints can be widened', () => {
  const copy = getEmptyResultsCopy('vibe', {
    preferred_countries: ['India'],
    min_year: 1990,
    max_year: 1999,
    include_themes: ['mystery'],
    exclude_themes: ['horror'],
    excluded_titles: ['Titanic'],
  })

  assert.equal(copy.heading, 'No movies matched every filter.')
  assert.match(copy.description, /country \(India\)/)
  assert.match(copy.description, /release years \(1990\u20131999\)/)
  assert.match(copy.description, /excluded genres or themes \(horror\)/)
  assert.match(copy.description, /excluded movies \(Titanic\)/)
  assert.doesNotMatch(copy.description, /mystery/)
  assert.equal(copy.action, 'Edit this search')
})

test('positive themes are not misrepresented as strict filters', () => {
  const copy = getEmptyResultsCopy('vibe', {
    include_themes: ['mystery'],
  })

  assert.equal(copy.heading, 'No strong matches yet.')
  assert.doesNotMatch(copy.description, /strict/)
})

test('one-sided release filters explain their boundary', () => {
  const newerCopy = getEmptyResultsCopy('vibe', { min_year: 2020 })
  const olderCopy = getEmptyResultsCopy('vibe', { max_year: 1970 })

  assert.match(newerCopy.description, /release year \(2020 or later\)/)
  assert.match(olderCopy.description, /release year \(1970 or earlier\)/)
})

test('empty vibe results without hard constraints suggest a more specific query', () => {
  const copy = getEmptyResultsCopy('vibe', {})

  assert.equal(copy.heading, 'No strong matches yet.')
  assert.match(copy.description, /adding a mood, genre, country/)
})

test('empty title results retain title-specific recovery guidance', () => {
  const copy = getEmptyResultsCopy('title', {})

  assert.match(copy.heading, /movie title/)
  assert.equal(copy.action, 'Describe a vibe')
})
