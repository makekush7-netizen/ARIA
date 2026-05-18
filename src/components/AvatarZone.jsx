import React, { Suspense, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import AvatarModel from '../AvatarModel'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false } }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch(e) { console.error('[ARIA] Avatar:', e) }
  render() { return this.state.hasError ? null : this.props.children }
}

function PlatformGlow() {
  const disc = useRef(); const ring = useRef()
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    if (disc.current) disc.current.material.opacity = 0.22 + Math.sin(t * 2) * 0.1
    if (ring.current) ring.current.material.opacity = 0.55 + Math.sin(t * 2) * 0.2
  })
  return (
    <group position={[0, -0.01, 0]}>
      <mesh ref={disc} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.7, 64]} />
        <meshBasicMaterial color="#e6ceaa" transparent opacity={0.3} />
      </mesh>
      <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.68, 0.8, 64]} />
        <meshBasicMaterial color="#e6ceaa" transparent opacity={0.4} />
      </mesh>
    </group>
  )
}

export default function AvatarZone({ greeting, activeTask, memoryData, agentState, onToggleBubble }) {
  const fullName = memoryData?.name || 'there'
  const firstName = fullName.split(' ')[0]
  const memCount = Object.keys(memoryData).filter(k => memoryData[k]).length

  return (
    <div className="avatar-zone">
      <div className="avatar-greeting">
        <h2>
          {greeting},<br />
          {firstName}
        </h2>
        <p>How can I help you today?</p>
      </div>

      <div className="avatar-canvas-wrap">
        <button id="bubble-toggle-btn" className="bubble-toggle" onClick={onToggleBubble} title="Bubble mode">⊙</button>
        <Canvas
          camera={{ position: [0, 0.95, 2.6], fov: 40 }}
          onCreated={({ camera }) => camera.lookAt(0, 0.9, 0)}
          style={{ background: 'transparent' }}
        >
          <ambientLight intensity={0.6} />
          <directionalLight position={[3, 4, 3]} intensity={0.7} color="#fffcf5" />
          <directionalLight position={[-2, 2, -1]} intensity={0.5} color="#e5cc9f" />
          <directionalLight position={[0, -1, 2]} intensity={0.4} color="#e6ceaa" />
          <ErrorBoundary>
            <Suspense fallback={null}>
              <AvatarModel modelUrl="/model_female.glb" scale={1} position={[0, 0, 0]} />
            </Suspense>
          </ErrorBoundary>
          <PlatformGlow />
        </Canvas>
      </div>

      <div className="status-cards">
        <div className="status-card">
          <div className="status-card-icon">✓</div>
          <div className="status-card-info">
            <div className="status-card-label">Focus Mode</div>
            <div className="status-card-value">On</div>
          </div>
        </div>
        <div className="status-card">
          <div className="status-card-icon">▶</div>
          <div className="status-card-info">
            <div className="status-card-label">Active Task</div>
            <div className="status-card-value">{activeTask || 'Idle'}</div>
          </div>
        </div>
        <div className="status-card">
          <div className="status-card-icon">◈</div>
          <div className="status-card-info">
            <div className="status-card-label">Memory</div>
            <div className="status-card-value">{memCount} stored</div>
          </div>
        </div>
      </div>
    </div>
  )
}
