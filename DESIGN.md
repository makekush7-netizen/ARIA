# ARIA – Design System
Reference image: Aurora UI (dark charcoal, warm gold glow, RPM avatar on platform)

---

## Colors

```css
--bg-primary: #111318        /* main background */
--bg-card: #1a1d24           /* frosted panels */
--bg-card-border: #2a2d35    /* card borders */
--accent-gold: #c9a84c       /* platform glow, active states */
--accent-gold-dim: #8a6f2e   /* secondary gold */
--accent-green: #4caf7d      /* online dot, success */
--text-primary: #f0ece4      /* warm white, main text */
--text-secondary: #8a8a9a    /* subtitles, timestamps */
--user-bubble: #2a2d3a       /* user message bg */
--agent-bubble: #1e2128      /* agent message bg */
--waveform: #c9a84c          /* mic waveform bars */
--platform-glow: radial-gradient(ellipse, #c9a84c33 0%, transparent 70%)
```

---

## Typography

```css
font-family: 'Inter', system-ui, sans-serif
--font-logo: 600, 1.2rem, letter-spacing: 0.08em
--font-nav: 400, 0.8rem
--font-chat: 400, 0.92rem, line-height: 1.6
--font-label: 500, 0.75rem, text-transform: uppercase, letter-spacing: 0.1em
--font-timestamp: 400, 0.7rem, color: var(--text-secondary)
```

---

## Layout

```
┌─────────────────────────────────────────────────────┐
│  [ARIA logo]          [Home] [Memory] [Store] [⚙]   │  ← 56px topbar
├────────────────────────┬────────────────────────────┤
│                        │                            │
│   LEFT ZONE (50%)      │   RIGHT ZONE (50%)         │
│                        │                            │
│   Good morning, {name} │  ┌──────────────────────┐  │
│                        │  │ ARIA  ● Online    ··· │  │
│   [avatar 3D]          │  │                      │  │
│                        │  │  [chat messages]     │  │
│   ──────────────────   │  │                      │  │
│   ○ Focus Mode  On     │  │                      │  │
│   ○ Active Task  –     │  └──────────────────────┘  │
│   ○ Memory  3 items    │                            │
│                        │                            │
├────────────────────────┴────────────────────────────┤
│  Voice Mode: Active  [~~~~🎤~~~~]  Press to speak   │  ← 64px bottom bar
└─────────────────────────────────────────────────────┘
```

---

## Components

### Avatar Platform
```css
.platform {
  width: 220px; height: 20px;
  background: radial-gradient(ellipse, #c9a84c55 0%, transparent 70%);
  border-radius: 50%;
  box-shadow: 0 0 40px #c9a84c33;
  /* subtle pulse animation 3s ease-in-out infinite */
}
```

### Chat Bubbles
```css
.bubble-user {
  background: #2a2d3a;
  border-radius: 18px 18px 4px 18px;
  padding: 10px 14px;
  max-width: 75%;
  align-self: flex-end;
}
.bubble-agent {
  background: #1e2128;
  border: 1px solid #2a2d35;
  border-radius: 18px 18px 18px 4px;
  padding: 10px 14px;
  max-width: 80%;
}
```

### Bottom Voice Bar
```css
.voice-bar {
  background: #1a1d24;
  border-top: 1px solid #2a2d35;
  height: 64px;
  display: flex; align-items: center;
  padding: 0 24px; gap: 16px;
}
.mic-button {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: #c9a84c22;
  border: 1px solid #c9a84c66;
  /* pulse ring animation when active */
}
/* Waveform: 40 bars, height animated with AudioAnalyser data */
```

### Nav Bar
```css
.nav-item {
  display: flex; flex-direction: column;
  align-items: center; gap: 4px;
  font-size: 0.75rem; color: var(--text-secondary);
  padding: 8px 16px;
  cursor: pointer;
}
.nav-item.active {
  color: var(--accent-gold);
  border-bottom: 2px solid var(--accent-gold);
}
```

### HITL Permission Modal
```css
.hitl-modal {
  position: fixed; bottom: 90px; left: 50%;
  transform: translateX(-50%);
  background: #1a1d24;
  border: 1px solid #c9a84c66;
  border-radius: 16px;
  padding: 20px 24px;
  min-width: 360px;
  box-shadow: 0 8px 32px #00000066;
}
/* Shows: action description + [Allow] [Deny] buttons */
/* [Allow]: gold bg, [Deny]: transparent with border */
```

### Store Cards — Skill
```css
.skill-card {
  background: #1a1d24;
  border: 1px solid #2a2d35;
  border-radius: 12px;
  padding: 16px;
  display: flex; flex-direction: column; gap: 8px;
}
.skill-card:hover { border-color: #c9a84c55; }
.skill-badge-installed { 
  background: #4caf7d22; color: #4caf7d;
  border-radius: 99px; font-size: 0.7rem; padding: 2px 8px;
}
```

### Bubble Mode Orb
```css
.orb {
  width: 120px; height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, #c9a84c 0%, #7c5c2a 50%, transparent 70%);
  box-shadow: 0 0 60px #c9a84c44;
  /* scale animation tied to audio frequency: scale(1 + amplitude * 0.3) */
}
/* States: idle → blue tint, listening → cyan, thinking → purple, speaking → gold */
```

---

## Animations

```css
@keyframes platform-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}
@keyframes orb-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
@keyframes mic-ring {
  0% { box-shadow: 0 0 0 0 #c9a84c44; }
  100% { box-shadow: 0 0 0 16px transparent; }
}
```

---

## Status Cards (Left Panel)

Three pill-shaped cards below the avatar greeting:
```
[○]  Focus Mode        On
[□]  Active Task       Filling form...
[◇]  Memory            3 items stored
```
Each: `background: #1a1d2488`, `border: 1px solid #2a2d35`, `border-radius: 99px`, `padding: 8px 16px`

---

## Responsive Notes

This is a desktop app (Electron or localhost:3000 fullscreen). Minimum width: 1280px. No mobile layout needed for demo.
