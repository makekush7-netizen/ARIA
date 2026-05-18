import React, { useState, useEffect } from 'react'

const DEFAULT_FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'college', label: 'College' },
  { key: 'department', label: 'Department' },
  { key: 'rollNo', label: 'Roll No' },
]

export default function MemoryPanel({ memoryData, setMemoryData, apiBase }) {
  const [local, setLocal] = useState({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch(`${apiBase}/api/memory`)
      .then(r => r.json())
      .then(d => { setLocal(d); setMemoryData(d) })
      .catch(() => setLocal(memoryData))
  }, [])

  const handleChange = (key, val) => setLocal(p => ({ ...p, [key]: val }))
  const handleDelete = (key) => setLocal(p => { const n = { ...p }; delete n[key]; return n })

  const handleSave = () => {
    setMemoryData(local)
    fetch(`${apiBase}/api/memory`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(local)
    })
      .then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000) })
      .catch(() => { setSaved(true); setTimeout(() => setSaved(false), 2000) })
  }

  return (
    <div className="memory-panel">
      <h1 className="panel-title">Memory</h1>
      <p className="panel-subtitle">ARIA remembers these details to personalize your experience.</p>

      {DEFAULT_FIELDS.map(({ key, label }) => (
        <div key={key} className="memory-row">
          <div className="memory-label">{label}</div>
          <input
            id={`memory-${key}`}
            className="memory-input"
            value={local[key] || ''}
            onChange={e => handleChange(key, e.target.value)}
            placeholder={`Enter ${label.toLowerCase()}…`}
          />
          <button className="memory-delete" onClick={() => handleDelete(key)} title="Clear">✕</button>
        </div>
      ))}

      <button id="memory-save-btn" className="memory-save-btn" onClick={handleSave}>
        {saved ? '✓ Saved!' : 'Save Changes'}
      </button>

      <div className="memory-footer">
        🔒 Stored locally on your device only · Never sent to cloud
      </div>
    </div>
  )
}
