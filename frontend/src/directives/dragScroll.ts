import type { ObjectDirective } from 'vue'

type DragScrollElement = HTMLElement & {
  __dragScrollCleanup__?: () => void
}

const dragScroll: ObjectDirective<DragScrollElement> = {
  mounted(el) {
    let pointerId: number | null = null
    let startX = 0
    let startY = 0
    let startLeft = 0
    let startTop = 0
    let moved = false

    const interactiveSelector = 'button, input, select, textarea, a, label, summary'

    const clearDragState = () => {
      if (pointerId !== null && el.hasPointerCapture(pointerId)) {
        el.releasePointerCapture(pointerId)
      }
      pointerId = null
      el.classList.remove('drag-scroll-active')
    }

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) {
        return
      }

      if ((event.target as HTMLElement | null)?.closest(interactiveSelector)) {
        return
      }

      pointerId = event.pointerId
      startX = event.clientX
      startY = event.clientY
      startLeft = el.scrollLeft
      startTop = el.scrollTop
      moved = false

      el.setPointerCapture(pointerId)
      el.classList.add('drag-scroll-active')
    }

    const onPointerMove = (event: PointerEvent) => {
      if (pointerId !== event.pointerId) {
        return
      }

      const deltaX = event.clientX - startX
      const deltaY = event.clientY - startY

      if (!moved && (Math.abs(deltaX) > 4 || Math.abs(deltaY) > 4)) {
        moved = true
      }

      if (!moved) {
        return
      }

      el.scrollLeft = startLeft - deltaX
      el.scrollTop = startTop - deltaY
      event.preventDefault()
    }

    const onPointerEnd = (event: PointerEvent) => {
      if (pointerId !== event.pointerId) {
        return
      }

      window.requestAnimationFrame(() => {
        moved = false
      })
      clearDragState()
    }

    const onClickCapture = (event: MouseEvent) => {
      if (!moved) {
        return
      }

      event.preventDefault()
      event.stopImmediatePropagation()
      moved = false
    }

    el.classList.add('drag-scroll-surface')
    el.addEventListener('pointerdown', onPointerDown)
    el.addEventListener('pointermove', onPointerMove)
    el.addEventListener('pointerup', onPointerEnd)
    el.addEventListener('pointercancel', onPointerEnd)
    el.addEventListener('lostpointercapture', onPointerEnd)
    el.addEventListener('click', onClickCapture, true)

    el.__dragScrollCleanup__ = () => {
      clearDragState()
      el.classList.remove('drag-scroll-surface')
      el.removeEventListener('pointerdown', onPointerDown)
      el.removeEventListener('pointermove', onPointerMove)
      el.removeEventListener('pointerup', onPointerEnd)
      el.removeEventListener('pointercancel', onPointerEnd)
      el.removeEventListener('lostpointercapture', onPointerEnd)
      el.removeEventListener('click', onClickCapture, true)
    }
  },
  unmounted(el) {
    el.__dragScrollCleanup__?.()
    delete el.__dragScrollCleanup__
  }
}

export default dragScroll