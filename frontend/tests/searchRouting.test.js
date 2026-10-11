import assert from 'node:assert/strict'
import test from 'node:test'

import { getApiSearchMode, getResponseMode } from '../src/searchRouting.js'

test('default search uses backend auto-routing', () => {
  assert.equal(getApiSearchMode('vibe'), 'auto')
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
