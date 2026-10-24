export function createRequestTracker() {
  let activeController = null

  return {
    start() {
      activeController?.abort()
      activeController = new AbortController()
      return activeController
    },

    isActive(controller) {
      return activeController === controller
    },

    finish(controller) {
      if (activeController === controller) activeController = null
    },

    cancel() {
      activeController?.abort()
      activeController = null
    },
  }
}
