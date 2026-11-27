import assert from 'node:assert/strict'
import test from 'node:test'

import {
  focusFirstDialogControl,
  handleDialogKeyDown,
  restoreDialogFocus,
} from '../src/dialogFocus.js'

function createDialog(elementOptions = [{}, {}]) {
  const ownerDocument = { activeElement: null }
  const elements = elementOptions.map(({ disabled = false, ariaHidden = null } = {}) => ({
    hasAttribute: (name) => name === 'disabled' && disabled,
    getAttribute: (name) => (name === 'aria-hidden' ? ariaHidden : null),
    focus() {
      ownerDocument.activeElement = this
    },
  }))
  const container = {
    ownerDocument,
    querySelectorAll: () => elements,
    contains: (element) => elements.includes(element),
  }

  return { container, elements, ownerDocument }
}

function createKeyEvent(key, shiftKey = false) {
  return {
    key,
    shiftKey,
    prevented: false,
    preventDefault() {
      this.prevented = true
    },
  }
}

test('opening a dialog focuses its first usable control', () => {
  const { container, elements, ownerDocument } = createDialog([
    { disabled: true },
    { ariaHidden: 'true' },
    {},
  ])

  assert.equal(focusFirstDialogControl(container), true)
  assert.equal(ownerDocument.activeElement, elements[2])
  assert.equal(focusFirstDialogControl(null), false)
})

test('closing a dialog restores focus only when the opener still exists', () => {
  let focuses = 0
  const opener = { isConnected: true, focus: () => { focuses += 1 } }
  const removedOpener = { isConnected: false, focus: () => { focuses += 1 } }

  assert.equal(restoreDialogFocus(opener), true)
  assert.equal(restoreDialogFocus(removedOpener), false)
  assert.equal(restoreDialogFocus(null), false)
  assert.equal(focuses, 1)
})

test('Tab and Shift+Tab wrap focus inside the dialog', () => {
  const { container, elements, ownerDocument } = createDialog([{}, {}, {}])

  ownerDocument.activeElement = elements[2]
  const forward = createKeyEvent('Tab')
  assert.equal(handleDialogKeyDown(forward, container, () => {}), true)
  assert.equal(forward.prevented, true)
  assert.equal(ownerDocument.activeElement, elements[0])

  const backward = createKeyEvent('Tab', true)
  assert.equal(handleDialogKeyDown(backward, container, () => {}), true)
  assert.equal(backward.prevented, true)
  assert.equal(ownerDocument.activeElement, elements[2])
})

test('Tab recovers focus that moved outside the dialog', () => {
  const { container, elements, ownerDocument } = createDialog([{}, {}])
  ownerDocument.activeElement = {}

  const event = createKeyEvent('Tab')
  handleDialogKeyDown(event, container, () => {})

  assert.equal(event.prevented, true)
  assert.equal(ownerDocument.activeElement, elements[0])
})

test('Escape closes every dialog state', () => {
  const { container } = createDialog()
  const event = createKeyEvent('Escape')
  let closes = 0

  assert.equal(handleDialogKeyDown(event, container, () => { closes += 1 }), true)
  assert.equal(event.prevented, true)
  assert.equal(closes, 1)
  assert.equal(handleDialogKeyDown(createKeyEvent('Enter'), container, () => {}), false)
})
