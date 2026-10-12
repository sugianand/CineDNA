import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getApiSearchMode,
  getEmptyResultsCopy,
  getResponseMode,
} from '../src/searchRouting.js'

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

test('empty vibe results explain which strict constraints can be widened', () => {
  const copy = getEmptyResultsCopy('vibe', {
    preferred_countries: ['India'],
    min_year: 1990,
    max_year: 1999,
    include_themes: ['mystery'],
  })

  assert.equal(copy.heading, 'No movies matched every filter.')
  assert.match(copy.description, /country, release period, and genre or theme filters strict/)
  assert.equal(copy.action, 'Edit this search')
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
