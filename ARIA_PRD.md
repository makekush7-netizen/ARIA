# ARIA — Product Requirements Document
**Version 1.0 | Team Endeavour | Yantrika 2026**

---

## 1. The One-Liner

ARIA is a desktop companion that lives on your screen, automates your boring tasks, and actually has a personality — built for people who spend 8+ hours a day at a computer and want something better than a chatbot buried in a browser tab.

---

## 2. The Problem

Power users — gamers, students, solo founders, devs — spend hours every day doing repetitive digital work: filling forms, switching between 5 apps, copy-pasting data, managing emails. Automation tools exist but require technical setup. AI assistants exist but are trapped in browser tabs with no awareness of what's on your screen.

**Nobody has built the thing that sits *with* you while you work.**

---

## 3. Target Users

| Segment | Pain | Willingness to Pay |
|---|---|---|
| Gamers / streamers | Want a companion, hate tab-switching for tasks | High — already pay for cosmetics |
| College students | Forms, deadlines, repetitive research tasks | Medium — pay if cheap |
| Solo founders / freelancers | Email, CRM, data entry eats their day | High — time = money |
| "Loners" (their word) | Want ambient presence, not just utility | Medium-high — pay for personality |

---

## 4. Product Vision

ARIA is not a chatbot. She is an **OS-level agent** with a visible presence — a 3D anime-style character who lives in the corner of your desktop, sees your screen, responds to your voice, and handles multi-step tasks across any app. No coding required.

**Core promise:** *"Tell her once. She handles it."*

---

## 5. Core Features (V1)

### 5.1 The Avatar
- VRM-based 3D character, rendered in a transparent always-on-top Tauri window
- Idle breathing animation at rest
- Expression system: happy, sad, surprised, thinking, neutral driven by LLM emotion tags
- Lip sync driven by audio amplitude (Web Audio API → jaw blendshape)
- Auto-blink, subtle head sway — alive even when idle
- **Sits on the edge of your active window** using OS window position polling

### 5.2 Voice + Text Interaction
- Wake word or push-to-talk (Web Speech API)
- Text input fallback
- Gemini 2.0 Flash for response — fast enough for real-time feel
- TTS via browser speechSynthesis (V1) → Kokoro (V2)

### 5.3 Task Automation
- Screen reading via Playwright + DOM parsing
- Form filling with HITL permission card before every sensitive action
- Browser navigation ("open YouTube", "go to Gmail")
- Email drafting and sending
- Calendar events (Outlook/Google Calendar)

### 5.4 Memory
- Local SQLite store — never uploaded
- Remembers: name, college/workplace, email, preferences, past tasks
- Conversation history per session

### 5.5 Skill Marketplace (V2)
- Developers publish automation modules
- One-click install, like browser extensions
- Revenue share: 70% dev / 30% ARIA platform

---

## 6. Technical Architecture

```
┌─────────────────────────────────┐
│   Tauri Window (transparent)    │
│   React + Three.js + three-vrm  │
│   VRM avatar | Voice I/O | UI   │
└──────────────┬──────────────────┘
               │ HTTP / WebSocket
               │ localhost:8000
┌──────────────▼──────────────────┐
│   FastAPI + Uvicorn (sidecar)   │
│   Gemini 2.0 Flash              │
│   Playwright RPA engine         │
│   SQLite memory store           │
└─────────────────────────────────┘
```

**Stack:**
- Frontend: React + TypeScript, Three.js, @pixiv/three-vrm, Tauri
- Backend: FastAPI, Uvicorn, google-generativeai, Playwright, SQLite
- Packaging: PyInstaller (backend → .exe sidecar) + Tauri bundler → single installer
- Avatar: VRM0.0 from VRoid Studio, FBX animations from Mixamo retargeted at runtime

---

## 7. Design System

### 7.1 Philosophy
Not neon. Not gradient blue. Not "AI startup" purple glow.
ARIA's aesthetic is **warm dark** — like a dimly lit room at 2am when you're deep in a session. Comfortable, focused, slightly intimate. Think: a desk lamp, not a billboard.

### 7.2 Color Palette

```
Background (deepest)    #0E0D0C
Surface (cards/panels)  #1A1917
Surface raised          #242220
Border                  #2E2C29
Border subtle           #1F1E1C

Text primary            #F0EDE8
Text secondary          #9E9B96
Text tertiary           #5C5A56
Text disabled           #3A3835

Accent (primary)        #C8956C   ← warm amber, not orange
Accent hover            #D4A882
Accent muted            #3D2E24

Success                 #6A9E72
Warning                 #C8A84B
Danger                  #A85C5C
Info                    #5C82A8
```

### 7.3 Typography

```
Display / Hero    "Syne" — geometric, slightly editorial
Body / UI         "Inter" — clean, readable at small sizes
Mono / Code       "JetBrains Mono"

Scale:
  xs    11px / 1.4
  sm    12px / 1.5
  base  14px / 1.6
  md    16px / 1.5
  lg    20px / 1.4
  xl    28px / 1.3
  2xl   40px / 1.2
```

### 7.4 Spacing & Radius

```
Spacing: 4px base unit — 4, 8, 12, 16, 24, 32, 48, 64
Radius:  sm 4px | md 8px | lg 12px | xl 20px | pill 999px
```

### 7.5 Component Patterns

**ARIA window (the avatar panel)**
- Fully transparent background, no border, no shadow
- Avatar rendered at bottom-right or bottom-left, user configurable
- Minimal HUD: thin pill showing current task status, auto-hides after 3s

**Chat / command panel** (slides in from side on trigger)
- Background: `#1A1917` with 90% opacity + subtle blur
- Input bar at bottom: `#242220`, `border-radius: 20px`, accent border on focus
- Message bubbles: user → `#3D2E24` | ARIA → `#242220`
- No heavy drop shadows — use 1px borders instead

**Permission card** (HITL approval)
- Floats center screen
- Background `#1A1917`, border `#C8956C`
- Action title bold, description secondary text
- Two buttons: Deny (`#2E2C29`) | Allow (`#C8956C`)
- 30s timeout progress bar in accent color, auto-denies

**Skill/store cards**
- `#1A1917` surface, `#2E2C29` border
- Hover: border becomes `#C8956C`, slight lift (translateY -2px)
- Price tag: accent background pill

### 7.6 Motion

```
Transition default   200ms ease
Transition slow      400ms ease
Avatar crossfade     300ms (AnimationMixer.crossFadeTo)
Panel slide in       250ms cubic-bezier(0.16, 1, 0.3, 1)
Permission card      scale(0.95)→scale(1), 200ms
```

No bounce. No spring physics in UI (only in avatar). Calm, purposeful motion.

### 7.7 Avatar Visual Style
- Toon/cel-shaded VRM — hard shadow edge, not realistic
- No post-processing bloom or glow on avatar
- Drop a very soft real-time shadow on the "floor" plane (optional, subtle)
- Avatar outline: 0.8px dark stroke via VRM outline material

---

## 8. User Flows

### 8.1 First Launch
```
Install → ARIA appears bottom-right → 
Onboarding voice: "Hi, I'm ARIA. What's your name?" → 
User responds → stored to memory → 
Quick tutorial: 3 example commands shown → done
```

### 8.2 Task Execution
```
User: "Fill the hackathon form at this URL"
→ ARIA: opens browser, reads form fields via DOM
→ Permission card: "Fill Name field with Kush Yadav?" → Allow
→ Permission card: "Fill Email field with ___?" → Allow  
→ ARIA: "Done! Form submitted." → happy expression
```

### 8.3 Emotion Loop
```
Gemini response JSON: { "text": "...", "emotion": "happy" }
→ Frontend: vrm.expressionManager.setValue('happy', 1.0)
→ Smooth lerp back to neutral after 3s
```

---

## 9. Business Model

| Stream | How | Price |
|---|---|---|
| Consumer SaaS | Monthly sub | ₹299/mo or $4.99/mo |
| Power tier | More memory, more skills, priority | ₹799/mo or $12/mo |
| Marketplace cut | 30% of paid skill sales | — |
| Enterprise | White-label, SSO, team memory | Custom |

**TAM:** $25B+ RPA market by 2030. 500M+ knowledge workers globally.
**Beachhead:** Indian college students + early-career professionals. Low CAC, high retention if product has personality.

---

## 10. V1 Scope (Hackathon Demo)

| Feature | In Demo |
|---|---|
| VRM avatar with animations | ✅ |
| Emotion expressions | ✅ |
| Voice input + TTS | ✅ |
| Gemini 2.0 Flash responses | ✅ |
| Form filling (one demo form) | ✅ |
| Local memory (name, email) | ✅ |
| Transparent desktop window | ✅ |
| Marketplace | ❌ V2 |
| Window-sitting behavior | ❌ V2 |
| PyInstaller packaging | ❌ V2 |

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Playwright breaks on some sites | Fallback to screenshot + vision |
| VRM animation retargeting bugs | Pre-test 3 clips before demo |
| Gemini latency feels slow | Use Flash, stream response tokens |
| Users scared of screen access | HITL permission card on every action |

---

## 12. The Pitch Line for Tomorrow

> "Every productivity tool makes you go to it. ARIA comes to you. She lives on your desktop, sees what you see, and handles the work you hate — without you switching a single tab."
