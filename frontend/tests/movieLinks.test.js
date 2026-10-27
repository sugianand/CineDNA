import assert from 'node:assert/strict'
import test from 'node:test'
import {
  getAppHomeHref,
  getMovieProfileExitHref,
  getMovieProfileHref,
  parseMovieProfileLink,
} from '../src/movieLinks.js'

test('local movie links survive reloading and unicode titles', () => {
  const href = getMovieProfileHref({title: 'பொன்னியின் செல்வன்', source: 'cinedna'})
  assert.deepEqual(parseMovieProfileLink(href), {
    title: 'பொன்னியின் செல்வன்', source: 'cinedna', sourceId: null,
  })
})

test('external movie links retain a stable TMDB identity', () => {
  const href = getMovieProfileHref(
    {title: 'Baahubali: The Beginning', source: 'tmdb', source_id: '256040'},
    '?q=action',
  )
  assert.equal(new URLSearchParams(href).get('q'), 'action')
  assert.deepEqual(parseMovieProfileLink(href), {
    title: 'Baahubali: The Beginning', source: 'tmdb', sourceId: '256040',
  })
})

test('malformed movie links do not allow unbounded identifiers', () => {
  assert.equal(parseMovieProfileLink('?movie='), null)
  assert.equal(parseMovieProfileLink('?q=test'), null)
  assert.equal(parseMovieProfileLink('?movie=Dune&source=bogus'), null)
  assert.equal(parseMovieProfileLink('?movie=Dune&source='), null)
  assert.equal(parseMovieProfileLink('?movie=Test&source=tmdb'), null)
  assert.equal(parseMovieProfileLink('?movie=Test&source=tmdb&source_id=../bad'), null)
  assert.equal(parseMovieProfileLink('?movie=Test&source=tmdb&source_id=0'), null)
  assert.equal(
    parseMovieProfileLink('?movie=Test&source=tmdb&source_id=1234567890123'),
    null,
  )
})

test('leaving a movie profile clears only profile parameters', () => {
  const href = getMovieProfileExitHref(
    'https://cinedna.example/discover?campaign=shared&movie=Dune&source=tmdb&source_id=693134#results',
  )

  assert.equal(href, '/discover?campaign=shared#results')
})

test('home links clear profile state and page fragments', () => {
  const href = getAppHomeHref(
    'https://cinedna.example/discover?campaign=shared&movie=Dune&source=tmdb&source_id=693134#results',
  )

  assert.equal(href, '/discover?campaign=shared')
})
