const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function getFocusableElements(container) {
  if (!container?.querySelectorAll) return []

  return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter((element) => (
      !element.hasAttribute?.('disabled')
      && element.getAttribute?.('aria-hidden') !== 'true'
    ))
}

export function focusFirstDialogControl(container) {
  const [first] = getFocusableElements(container)
  first?.focus()
  return Boolean(first)
}

export function restoreDialogFocus(element) {
  if (!element?.isConnected) return false
  element.focus()
  return true
}

export function handleDialogKeyDown(event, container, closeDialog) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeDialog()
    return true
  }

  if (event.key !== 'Tab') return false

  const focusable = getFocusableElements(container)
  if (focusable.length === 0) {
    event.preventDefault()
    return true
  }

  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  const active = container.ownerDocument?.activeElement
  const focusOutside = !container.contains?.(active)

  if (event.shiftKey && (active === first || focusOutside)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (active === last || focusOutside)) {
    event.preventDefault()
    first.focus()
  }

  return true
}
