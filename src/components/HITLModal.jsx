import React, { useState, useEffect, useRef } from 'react'

const TIMEOUT = 30

export default function HITLModal({ request, onRespond }) {
  const [countdown, setCountdown] = useState(TIMEOUT)
  const timerRef = useRef(null)

  useEffect(() => {
    setCountdown(TIMEOUT)
    timerRef.current = setInterval(() => {
      setCountdown(p => {
        if (p <= 1) {
          clearInterval(timerRef.current)
          onRespond(false) // auto-deny
          return 0
        }
        return p - 1
      })
    }, 1000)
    return () => clearInterval(timerRef.current)
  }, [request])

  return (
    <div id="hitl-modal" className="hitl-overlay">
      <div className="hitl-header">
        <div className="hitl-title">⚡ {request?.title || 'Permission Request'}</div>
        <div className="hitl-countdown">Auto-deny in {countdown}s</div>
      </div>
      <div className="hitl-desc">
        {request?.description || 'ARIA is requesting permission to perform an action on your behalf.'}
      </div>
      <div className="hitl-actions">
        <button id="hitl-allow-btn" className="hitl-allow" onClick={() => { clearInterval(timerRef.current); onRespond(true) }}>
          Allow
        </button>
        <button id="hitl-deny-btn" className="hitl-deny" onClick={() => { clearInterval(timerRef.current); onRespond(false) }}>
          Deny
        </button>
      </div>
    </div>
  )
}
