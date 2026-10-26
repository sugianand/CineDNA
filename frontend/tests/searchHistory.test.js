import assert from 'node:assert/strict'
import test from 'node:test'

import { parseRecentSearches, updateRecentSearches } from '../src/searchHistory.js'
import { MAX_SEARCH_QUERY_LENGTH } from '../src/searchRouting.js'

test('parseRecentSearches safely rejects malformed storage', () => {
  assert.deepEqual(parseRecentSearches('{broken'), [])
  assert.deepEqual(parseRecentSearches('{"query":"Dune"}'), [])
  assert.deepEqual(parseRecentSearches(JSON.stringify([
    { query: 'Like Broken', mode: 'vibe', referenceMovie: { title: 'Broken' } },
  ])), [])
})

test('parseRecentSearches rejects reference DNA dimensions outside the scoring scale', () => {
  const referenceMovie = {
    title: 'Corrupt Movie',
    year: 2026,
    country: 'USA',
    genres: ['Drama'],
    themes: ['family'],
    dimensions: { action: 101 },
    summary: 'A malformed persisted reference movie.',
  }

  assert.deepEqual(parseRecentSearches(JSON.stringify([
    { query: 'Like Corrupt Movie', mode: 'vibe', referenceMovie },
  ])), [])
})

test('parseRecentSearches rejects malformed reference movie field types', () => {
  const referenceMovie = {
    title: 'Corrupt Movie',
    year: 2026,
    country: 'USA',
    genres: ['Drama'],
    themes: ['family'],
    dimensions: { action: 42 },
    summary: 'A malformed persisted reference movie.',
    source: 'tmdb',
    source_id: '123',
    original_title: null,
    poster_url: null,
  }
  const malformedFields = [
    { genres: ['Drama', 42] },
    { themes: ['family', null] },
    { source: null },
    { source_id: 123 },
    { original_title: 123 },
    { poster_url: {} },
  ]

  for (const malformedField of malformedFields) {
    assert.deepEqual(parseRecentSearches(JSON.stringify([
      {
        query: 'Like Corrupt Movie',
        mode: 'vibe',
        referenceMovie: { ...referenceMovie, ...malformedField },
      },
    ])), [])
  }
})

test('parseRecentSearches discards queries that exceed the API limit', () => {
  const overlongQuery = 'x'.repeat(MAX_SEARCH_QUERY_LENGTH + 1)

  assert.deepEqual(parseRecentSearches(JSON.stringify([
    { query: overlongQuery, mode: 'title' },
    overlongQuery,
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
