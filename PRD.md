# ARIA – Product Requirements Document
**Agentic RPA Interface Assistant**
Version: Demo MVP | Hackathon: YANTRIKA 2026

---

## 1. What This Is

ARIA is a desktop-class web app (runs on localhost) where a user interacts with a 3D AI companion that can BOTH chat naturally AND autonomously perform real computer tasks on their behalf — filling forms, reading emails, controlling software — using screen vision + browser automation. Built on top of the existing `makekush7-netizen/aura` GitHub repo.

---

## 2. Repo Context (READ FIRST)

Base repo: `https://github.com/makekush7-netizen/aura`

Structure:
```
aura/
├── aura_frontend/     # React app, has RPM avatar, R3F, animations
├── aura_backend/      # FastAPI, Gemini agent, Kokoro TTS, RAG
```

**Critical:** The frontend already has Ready Player Me GLB avatar with animations (blink, idle, mouth movement). Do NOT replace this. Extend it. Read `aura_frontend/src` carefully before touching any avatar/animation code.

---

## 3. Tech Stack (Final)

| Layer | Tech |
|---|---|
| Frontend | React + React Three Fiber (existing) + Tailwind CSS |
| Avatar | Ready Player Me GLB (existing in repo) |
| Voice In | Browser Web Speech API → Nova Sonic (AWS Bedrock) |
| Voice Out | AWS Nova Sonic bidirectional stream (replaces Kokoro) |
| Agent Brain | AWS Nova (Bedrock) `amazon.nova-pro-v1:0` |
| Browser Agent | Python Playwright (chromium) |
| Screen Capture | `mss` + `Pillow` for screenshots |
| Memory | Local JSON file `~/.aria/memory.json` |
| Backend | FastAPI + WebSocket |
| Cloud | AWS (160$ credits, us-east-1) |

---

## 4. Pages / Views

### 4.1 Home (Main View)
- Left 50%: Avatar zone — RPM 3D character on warm-glow platform
- Right 50%: Chat panel — frosted dark glass, message bubbles
- Bottom bar: mic button + waveform visualizer + text input
- Top nav: Home | Memory | Store | Settings
- Top left: ARIA logo + wordmark
- Left panel below avatar: status cards (Focus Mode, Active Task, Memory count)
- Toggle button: switch between 3D mode and Bubble mode

### 4.2 Bubble Mode
- Fullscreen dark overlay
- Central animated orb — pulses with mic frequency
- Color: idle=soft blue, listening=cyan pulse, thinking=purple breathe, speaking=warm white
- Pull-up chat drawer from bottom

### 4.3 Memory Panel
- List of stored key-value pairs from `memory.json`
- Fields: Name, Email, Phone, College, Department, Roll No, Preferences
- Each row: editable inline, delete button
- Footer note: "Stored locally on your device only"

### 4.4 Store Page
Two tabs:

**Skins tab** — grid of avatar cards:
- Default ARIA (equipped)
- Cyber Samurai (locked, ₹299)
- Minimalist (locked, ₹199)
- Neon Goddess (locked, ₹399)

**Skills tab** — grid of skill cards with icon, name, dev name, stars, price:
- Gmail Reader (free, installed)
- Form Filler (free, installed)
- Blender Agent (₹0, install button)
- Photoshop Assistant (₹149)
- Unity Dev Helper (₹199)
- Cold Email Sender (free)
- Unreal Engine Skill (₹249)

### 4.5 Settings
- Voice: Nova Sonic / Browser TTS toggle
- Compute: Cloud / Local / Hybrid
- Agent permission level: Ask always / Ask for critical / Auto
- Theme: Dark Warm / Dark Cool
- Clear memory button

---

## 5. Agent Capabilities (Demo Scope)

### 5.1 Conversational Mode
Normal chat with memory. Agent knows user's stored info and references it naturally.

### 5.2 Agentic Task: Form Fill
Trigger: user says "fill the [form name] for me"
Flow:
1. Agent reads memory for required fields
2. Opens URL in playwright browser (visible window)
3. Takes screenshot, identifies fields via Nova vision
4. For each field: asks human permission if sensitive ("Should I fill your phone number?")
5. Types values, submits only after final user confirm
6. Reports done with summary

### 5.3 Agentic Task: Email Check
Trigger: "check my emails" / "read my new emails"
Flow:
1. Opens Gmail in playwright
2. Screenshots inbox
3. Nova reads visible emails, summarizes top 5
4. Speaks summary back via Nova Sonic

### 5.4 Skill: Blender (Demo Only)
- Pre-scripted: opens Blender, creates a cube, renders it
- Shows agent "using" the software live on screen
- Just for visual wow factor in presentation

---

## 6. Human-in-the-Loop (HITL) Protocol

Every agentic action must:
1. Send a `permission_request` event via WebSocket to frontend
2. Frontend shows a modal: action description + Yes/No buttons
3. Backend waits (timeout 30s)
4. Only proceeds on explicit Yes
5. Critical actions (form submit, send email, file delete): ALWAYS ask
6. Read-only actions (screenshot, read page): can auto-proceed if settings allow

---

## 7. Memory System

File: `~/.aria/memory.json`
```json
{
  "name": "",
  "email": "",
  "phone": "",
  "college": "",
  "department": "",
  "roll_no": "",
  "preferences": {},
  "conversation_summary": ""
}
```
- Agent reads this at session start
- Updates it when user shares new info naturally in conversation
- Frontend Memory panel reads/writes same file via `/memory` API endpoint

---

## 8. Nova Sonic Integration

Model: `amazon.nova-sonic-v1:0` (us-east-1)
Protocol: Bidirectional WebSocket stream via `boto3` `invoke_model_with_bidirectional_stream`

Flow:
1. Frontend captures mic audio (PCM 16kHz mono)
2. Sends audio chunks via WebSocket to `/ws/voice`
3. Backend streams to Nova Sonic
4. Nova Sonic returns: transcript + audio response
5. Backend streams audio back to frontend
6. Frontend plays audio + triggers avatar mouth animation

Key: Nova Sonic handles BOTH STT and TTS in one stream. No separate Whisper or Kokoro needed.

---

## 9. Build Priority Order

1. Frontend restyle + Store + Memory UI (no backend changes)
2. Nova Sonic voice pipeline
3. Screen agent (playwright + screenshot)
4. Form fill skill end-to-end
5. Email check skill
6. HITL modal system
7. Blender demo script

---

## 10. Demo Script for Presentation (May 20)

1. Open app → ARIA greets user by name (from memory)
2. User speaks: "What do you know about me?" → ARIA lists memory
3. User speaks: "Fill the hackathon registration form for me" → HITL flow live
4. Agent opens browser visibly, fills form field by field, asks permission
5. Switch to bubble mode → show orb pulsing with voice
6. Open Store → show skin/skill marketplace
7. Optional: "Open Blender and make a cube" → Blender skill fires

Total demo time: ~4 minutes
