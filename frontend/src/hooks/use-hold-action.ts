import { useCallback, useEffect, useRef, useState } from 'react'

export function useHoldAction(onComplete: () => void, durationMs = 1_500) {
  const timer = useRef<number | null>(null)
  const [holding, setHolding] = useState(false)

  const cancel = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
    setHolding(false)
  }, [])

  const start = useCallback(() => {
    cancel()
    setHolding(true)
    timer.current = window.setTimeout(() => {
      timer.current = null
      setHolding(false)
      onComplete()
    }, durationMs)
  }, [cancel, durationMs, onComplete])

  useEffect(() => cancel, [cancel])
  return { holding, start, cancel }
}
