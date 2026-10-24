import assert from 'node:assert/strict'
import test from 'node:test'

import { createRequestTracker } from '../src/requestTracker.js'

test('starting a new request aborts and replaces the previous request', () => {
  const tracker = createRequestTracker()
  const first = tracker.start()
  const second = tracker.start()

  assert.equal(first.signal.aborted, true)
  assert.equal(tracker.isActive(first), false)
  assert.equal(tracker.isActive(second), true)
})

test('cancel prevents a pending request from being treated as active', () => {
  const tracker = createRequestTracker()
  const request = tracker.start()

  tracker.cancel()

  assert.equal(request.signal.aborted, true)
  assert.equal(tracker.isActive(request), false)
})

test('finishing an old request does not clear the current request', () => {
  const tracker = createRequestTracker()
  const first = tracker.start()
  const second = tracker.start()

  tracker.finish(first)

  assert.equal(tracker.isActive(second), true)
})

test('cancelled async work cannot commit a late result', async () => {
  const tracker = createRequestTracker()
  const request = tracker.start()
  let release
  let committed = false
  const pending = new Promise((resolve) => {
    release = resolve
  }).then(() => {
    if (tracker.isActive(request)) committed = true
  })

  tracker.cancel()
  release()
  await pending

  assert.equal(committed, false)
})
