import assert from 'node:assert/strict'
import test from 'node:test'

import { parseRecentSearches, updateRecentSearches } from '../src/searchHistory.js'

test('parseRecentSearches safely rejects malformed storage', () => {
  assert.deepEqual(parseRecentSearches('{broken'), [])
  assert.deepEqual(parseRecentSearches('{"query":"Dune"}'), [])
  assert.deepEqual(parseRecentSearches(JSON.stringify([
    { query: 'Like Broken', mode: 'vibe', referenceMovie: { title: 'Broken' } },
  ])), [])
})

test('parseRecentSearches preserves modes and migrates legacy entries', () => {
  const stored = JSON.stringify([
    { query: '  Dune  ', mode: 'title' },
    { query: 'dark   mystery', mode: 'vibe' },
    'Up',
    'Indian thriller',
    { query: 'Invalid', mode: 'other' },
    null,
    { query: 'Sixth entry', mode: 'vibe' },
  ])

  assert.deepEqual(parseRecentSearches(stored), [
    { query: 'Dune', mode: 'title' },
    { query: 'dark mystery', mode: 'vibe' },
    { query: 'Up', mode: 'title' },
    { query: 'Indian thriller', mode: 'vibe' },
    { query: 'Sixth entry', mode: 'vibe' },
  ])
})

test('updateRecentSearches promotes a query with its latest mode', () => {
  const current = [
    { query: 'Dune', mode: 'title' },
    { query: 'Dark mystery', mode: 'vibe' },
  ]

  assert.deepEqual(updateRecentSearches(current, '  dune ', 'vibe'), [
    { query: 'dune', mode: 'vibe' },
    { query: 'Dark mystery', mode: 'vibe' },
  ])
})

test('updateRecentSearches retains only five entries', () => {
  const current = ['one', 'two', 'three', 'four', 'five'].map((query) => ({ query, mode: 'vibe' }))
  const updated = updateRecentSearches(current, 'six', 'vibe')

  assert.deepEqual(updated.map(({ query }) => query), ['six', 'one', 'two', 'three', 'four'])
})

test('similarity searches preserve reference DNA when stored and replayed', () => {
  const referenceMovie = {
    title: 'Remote Space Story',
    year: 2026,
    country: 'International',
    genres: ['Science Fiction'],
    themes: ['space', 'family'],
    dimensions: { pacing: 72, world_building: 94 },
    summary: 'An expanded-catalog test movie.',
    source: 'tmdb',
    source_id: '987654',
  }
  const updated = updateRecentSearches(
    [],
    'Like Remote Space Story, but show me a different movie with similar DNA',
    'vibe',
    referenceMovie,
  )

  assert.deepEqual(parseRecentSearches(JSON.stringify(updated)), updated)
  assert.deepEqual(updated[0].referenceMovie, referenceMovie)
})
