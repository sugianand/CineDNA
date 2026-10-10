import assert from 'node:assert/strict'
import test from 'node:test'

import { parseRecentSearches, updateRecentSearches } from '../src/searchHistory.js'

test('parseRecentSearches safely rejects malformed storage', () => {
  assert.deepEqual(parseRecentSearches('{broken'), [])
  assert.deepEqual(parseRecentSearches('{"query":"Dune"}'), [])
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
