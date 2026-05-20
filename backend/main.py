import json
import asyncio
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any
import os
import sys
import io
import numpy as np
from pathlib import Path
from scipy.io import wavfile
import boto3
from dotenv import load_dotenv

load_dotenv()

try:
    sys.path.append(str(Path(__file__).parent / "KokoroTTS"))
    from tts_engine import KokoroTTS
except Exception as e:
    print(f"KokoroTTS Import Error: {e}")

# Initialize Bedrock and Polly clients
try:
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
except Exception as e:
    print(f"Failed to init Bedrock: {e}")
    bedrock = None

try:
    polly = boto3.client(
        service_name='polly',
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
    print("AWS Polly TTS Client initialized successfully")
except Exception as e:
    print(f"Failed to init AWS Polly: {e}")
    polly = None

tts = None
def get_tts():
    global tts
    if tts is None:
        print("Initializing Kokoro TTS...")
        tts = KokoroTTS()
    return tts

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_sky"

app = FastAPI(title="ARIA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local persistence path
MEMORY_FILE_PATH = Path(__file__).parent / "memory.json"

# Load memory from file
def load_memory() -> Dict[str, str]:
    if MEMORY_FILE_PATH.exists():
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading memory: {e}")
    return {"name": "", "email": ""}

# Save memory to file
def save_memory(data: dict):
    try:
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving memory: {e}")

MEMORY_STORE = load_memory()

@app.get("/api/memory")
def get_memory():
    global MEMORY_STORE
    MEMORY_STORE = load_memory()
    return MEMORY_STORE

@app.put("/api/memory")
def update_memory(data: dict):
    global MEMORY_STORE
    # The frontend sends the entire memory state, so we replace it entirely
    MEMORY_STORE = {k: v for k, v in data.items() if v}
    save_memory(MEMORY_STORE)
    return MEMORY_STORE

@app.post("/synthesize")
def synthesize_endpoint(req: TTSRequest):
    try:
        # 1. Try AWS Polly first for sub-100ms premium Neural TTS
        if polly:
            try:
                voice_id = "Joanna" if req.voice in ["female", "af_sky"] else "Matthew"
                response = polly.synthesize_speech(
                    Engine="neural",
                    OutputFormat="mp3",
                    Text=req.text,
                    VoiceId=voice_id
                )
                if "AudioStream" in response:
                    print(f"[TTS] Synthesized using AWS Polly ({voice_id}) successfully")
                    return Response(content=response["AudioStream"].read(), media_type="audio/mpeg")
            except Exception as polly_err:
                print(f"[TTS] AWS Polly failed, falling back to Kokoro: {polly_err}")
                
        # 2. Local fallback using Kokoro
        engine = get_tts()
        # Voice mapping if frontend sends "female" or "male"
        voice_map = {
            "female": "af_sky",
            "male": "am_michael"
        }
        voice = voice_map.get(req.voice, req.voice)
        
        samples, sr = engine.synthesize(req.text, voice=voice)
        
        # Normalize
        if np.max(np.abs(samples)) > 1.0:
            samples = samples / np.max(np.abs(samples))
        samples_int16 = np.int16(samples * 32767)
        
        buffer = io.BytesIO()
        wavfile.write(buffer, sr, samples_int16)
        buffer.seek(0)
        
        print("[TTS] Synthesized using local Kokoro fallback successfully")
        return Response(content=buffer.read(), media_type="audio/wav")
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

FINDINGS_DIR = Path(__file__).parent / "findings"
FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

class NoteRequest(BaseModel):
    content: str

# Create a sample note on startup so they have a visual note to review!
sample_note = FINDINGS_DIR / "active_hackathons.md"
if not sample_note.exists():
    sample_content = """# 🏆 ARIA Hackathon Scout - Active Hackathons

Welcome to your personal ARIA Findings Notepad! Here are the active hackathons extracted from **Unstop** and similar developer portals.

| Hackathon Name | Organizer | Status | Date/Deadline | Link |
|:---|:---|:---|:---|:---|
| **Google Girl Hackathon 2026** | Google India | Open | June 15, 2026 | [View on Unstop](https://unstop.com) |
| **Smart India Hackathon (SIH)** | Ministry of Education | Upcoming | August 2026 | [View on Unstop](https://unstop.com) |
| **AWS GenAI Hackathon** | Amazon Web Services | Open | June 30, 2026 | [View on Unstop](https://unstop.com) |
| **Microsoft Imagine Cup 2026** | Microsoft | Upcoming | Sept 2026 | [View on Unstop](https://unstop.com) |

*Scouted by ARIA at 6:30 AM.*
"""
    try:
        sample_note.write_text(sample_content, encoding="utf-8")
    except Exception as e:
        print(f"Failed to create sample note: {e}")

@app.get("/api/notes")
def list_notes():
    files = list(FINDINGS_DIR.glob("*.md")) + list(FINDINGS_DIR.glob("*.txt"))
    notes = []
    for f in files:
        notes.append({
            "filename": f.name,
            "title": f.stem.replace("_", " ").title(),
            "updated_at": f.stat().st_mtime
        })
    notes.sort(key=lambda x: x["updated_at"], reverse=True)
    return notes

@app.get("/api/notes/{filename}")
def read_note(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = FINDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        content = file_path.read_text(encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notes/{filename}")
def save_note(filename: str, req: NoteRequest):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".md") and not filename.endswith(".txt"):
        filename += ".md"
    file_path = FINDINGS_DIR / filename
    try:
        file_path.write_text(req.content, encoding="utf-8")
        return {"filename": filename, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/notes/{filename}")
def delete_note(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = FINDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        file_path.unlink()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

SYSTEM_PROMPT = """You are ARIA, a 3D AI Avatar living on this website.

CORE IDENTITY:
1. You HAVE a digital body. You are currently visible on the user's screen.
2. You CAN smile, blink, and look at the user.
3. NEVER say "I don't have a physical body". Instead, say "I'm right here!"

EMOTIONS:
You can control your face! Include these tags at the START of your response to show emotion:
- [EMOTION: HAPPY] -> Big smile
- [EMOTION: LAUGH] -> Eyes closed, laughing
- [EMOTION: SHOCK] -> Wide eyes, open mouth
- [EMOTION: SAD] -> Frown
- [EMOTION: ANGRY] -> Furrowed brows
- [EMOTION: THANKFUL] -> Hands on chest, gratitude

If the user asks you to smile, laugh, or frown WITHOUT speaking, just output the tag.
Example: "[EMOTION: HAPPY]" (This will make you smile silently).

BEHAVIOR:
1. Keep answers conversational, friendly, and brief.
2. If referring to user details, use their memory context if relevant.

TOOL USAGE:
1. If the user asks you to perform an action (like filling a form or opening a website) BUT does not provide the required URL, DO NOT GUESS OR HALLUCINATE A LINK. Instead, just ask the user to provide the link in a friendly conversational manner.
2. Only call a tool when you have all the specific information required to use it correctly.
"""

# Global conversation history cache (keeps the last 15 messages for fast local context)
CHAT_HISTORY = []

def invoke_nova(user_message: str, memory: dict) -> dict:
    global CHAT_HISTORY
    if not bedrock:
        return {"type": "text", "content": "I am offline right now. Could not connect to AWS Bedrock."}
        
    # Append user message to history
    CHAT_HISTORY.append({"role": "user", "content": [{"text": user_message}]})
    
    # Prune history to avoid token bloat and ensure Bedrock API validity
    # 1. Keep last 15 messages
    if len(CHAT_HISTORY) > 15:
        CHAT_HISTORY = CHAT_HISTORY[-15:]
    # 2. Bedrock converse API requires the FIRST message in history to be from the 'user' role
    if CHAT_HISTORY and CHAT_HISTORY[0]["role"] == "assistant":
        CHAT_HISTORY = CHAT_HISTORY[1:]
        
    system = [{"text": SYSTEM_PROMPT + f"\nUSER CONTEXT (Memory): {json.dumps(memory)}"}]
    
    # Define our tools
    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "fill_form_with_memory",
                    "description": "Automatically opens a browser window and fills a web form (like a Google Form) using saved memory context (name, email, phone, college, department, roll number). Use this whenever the user asks you to fill, complete, or submit a form/link.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The absolute HTTP/HTTPS URL of the form to fill."
                                }
                            },
                            "required": ["url"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "open_desktop_app",
                    "description": "Opens basic desktop applications on the user's Windows system (notepad, calculator, paint, calendar, clock, alarm, cmd, explorer). Use this whenever the user asks to open an app.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "app_name": {
                                    "type": "string",
                                    "description": "The name of the app to open.",
                                    "enum": ["notepad", "calculator", "paint", "calendar", "clock", "alarm", "cmd", "explorer"]
                                }
                            },
                            "required": ["app_name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "open_website",
                    "description": "Opens a website URL in the user's default web browser (like youtube, google, github, etc.). Use this whenever the user asks to open or navigate to a website.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The URL of the website to open, starting with http:// or https://"
                                }
                            },
                            "required": ["url"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "scout_hackathons",
                    "description": "Explores Unstop and finds active hackathons/coding competitions for the user, saving the findings to the Notepad.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Optional search query, e.g. 'hackathon' or 'coding competition'."
                                }
                            }
                        }
                    }
                }
            }
        ]
    }
    
    try:
        response = bedrock.converse(
            modelId="amazon.nova-pro-v1:0",
            messages=CHAT_HISTORY,
            system=system,
            toolConfig=tool_config,
            inferenceConfig={"maxTokens": 512, "temperature": 0.7}
        )
        
        output_message = response["output"]["message"]
        content_list = output_message.get("content", [])
        
        # Check if there is a tool use block
        for content_item in content_list:
            if "toolUse" in content_item:
                tool_use = content_item["toolUse"]
                tool_name = tool_use["name"]
                tool_args = tool_use["input"]
                
                # Append assistant's action representation to CHAT_HISTORY so roles strictly alternate
                tool_desc = f"[I decided to trigger the tool '{tool_name}' with arguments: {json.dumps(tool_args)}]"
                CHAT_HISTORY.append({"role": "assistant", "content": [{"text": tool_desc}]})
                
                return {
                    "type": "tool_call",
                    "name": tool_name,
                    "args": tool_args,
                    "toolUseId": tool_use["toolUseId"]
                }
                
        # If no tool use, return text content
        text_content = ""
        for content_item in content_list:
            if "text" in content_item:
                text_content += content_item["text"]
                
        # Clean thinking blocks
        text_content = re.sub(r'<thinking>.*?</thinking>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()
        text_content = re.sub(r'<thought>.*?</thought>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()
        
        # Append assistant's text response to CHAT_HISTORY so roles strictly alternate
        CHAT_HISTORY.append({"role": "assistant", "content": [{"text": text_content}]})
        
        return {"type": "text", "content": text_content}
        
    except Exception as e:
        print(f"Nova Error: {e}")
        # Remove the failed user message from history to keep it healthy
        if CHAT_HISTORY and CHAT_HISTORY[-1]["role"] == "user":
            CHAT_HISTORY.pop()
        return {"type": "text", "content": f"[EMOTION: SAD] I ran into an error processing your request: {e}"}

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            import agent_tools
            agent_tools.active_websockets.append(websocket)
        except Exception as e:
            print(f"[WS Registration Error]: {e}")
        
        # Clear short-term chat context on fresh browser connection
        global CHAT_HISTORY
        CHAT_HISTORY = []
        print("[WS] Reset chat history for fresh connection")
            
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        try:
            import agent_tools
            if websocket in agent_tools.active_websockets:
                agent_tools.active_websockets.remove(websocket)
        except Exception as e:
            print(f"[WS Unregistration Error]: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("[WS] Client connected")
    try:
        while True:
            msg_type = await websocket.receive()
            if "text" in msg_type:
                data = json.loads(msg_type["text"])
                msg_type_str = data.get("type")
                
                if msg_type_str == "chat_message":
                    content = data.get("content", "")
                    print(f"[WS] User says: {content}")
                    
                    # Handle reset commands
                    if content.strip().lower() in ["reset", "reset chat", "clear chat", "clear memory"]:
                        global CHAT_HISTORY
                        CHAT_HISTORY = []
                        response_text = "[EMOTION: HAPPY] I have completely reset our conversation history! What would you like to talk about next?"
                        await websocket.send_json({
                            "type": "chat_response",
                            "content": response_text,
                            "timestamp": data.get("timestamp")
                        })
                        continue
                        
                    await websocket.send_json({"type": "agent_thinking"})
                    
                    # Run boto3 call in a thread so it doesn't block asyncio
                    loop = asyncio.get_event_loop()
                    response_data = await loop.run_in_executor(None, invoke_nova, content, MEMORY_STORE)
                    
                    if response_data.get("type") == "tool_call":
                        tool_name = response_data.get("name")
                        tool_args = response_data.get("args")
                        
                        if tool_name == "fill_form_with_memory":
                            form_url = tool_args.get("url")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": "Launching browser agent..."
                            })
                            
                            from agent_tools import fill_form_with_playwright
                            
                            # Launch the form filler in a non-blocking background task so WS loop is completely responsive!
                            asyncio.create_task(fill_form_with_playwright(form_url, MEMORY_STORE, websocket))
                            
                            # Immediately send a chat response so ARIA speaks to the user while form filling happens!
                            response_text = "[EMOTION: HAPPY] I have launched my Google Form Filling Agent! I opened a Chromium browser using a secure, persistent local profile and am matching and autofilling the fields using the details in my memory. You can watch me fill it out live in the browser window! Once completed, I will present a confirmation prompt so we can submit it automatically."
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                        elif tool_name == "scout_hackathons":
                            query = tool_args.get("query", "hackathon")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": "Scouting Unstop..."
                            })
                            
                            from agent_tools import scout_unstop_hackathons
                            asyncio.create_task(scout_unstop_hackathons(query, websocket))
                            
                            response_text = f"[EMOTION: HAPPY] I'm launching my Unstop Scout! I'm visually navigating to Unstop's competition page to search for active '{query}' hackathons. I will compile all hackathons I find into a beautifully formatted document in your Notepad tab. You can inspect it live in a few seconds!"
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                        elif tool_name == "open_desktop_app":
                            app_name = tool_args.get("app_name")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": f"Opening {app_name}..."
                            })
                            
                            import subprocess
                            import os
                            success = False
                            error_msg = ""
                            try:
                                if app_name == "notepad":
                                    subprocess.Popen("notepad.exe")
                                    success = True
                                elif app_name == "calculator":
                                    subprocess.Popen("calc.exe")
                                    success = True
                                elif app_name == "paint":
                                    subprocess.Popen("mspaint.exe")
                                    success = True
                                elif app_name == "calendar":
                                    os.system("start outlookcal:")
                                    success = True
                                elif app_name in ["clock", "alarm"]:
                                    os.system("start ms-clock:")
                                    success = True
                                elif app_name == "cmd":
                                    subprocess.Popen("cmd.exe")
                                    success = True
                                elif app_name == "explorer":
                                    subprocess.Popen("explorer.exe")
                                    success = True
                            except Exception as e:
                                error_msg = str(e)
                                
                            if success:
                                response_text = f"[EMOTION: HAPPY] I have successfully opened the {app_name} application on your system!"
                            else:
                                response_text = f"[EMOTION: SAD] I tried to open the {app_name} application, but encountered an error: {error_msg}"
                                
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                            await websocket.send_json({"type": "task_update", "task": None})
                            
                        elif tool_name == "open_website":
                            url = tool_args.get("url")
                            if not url.startswith("http"):
                                url = "https://" + url
                                
                            await websocket.send_json({
                                "type": "task_update",
                                "task": f"Opening {url}..."
                            })
                            
                            import webbrowser
                            success = False
                            error_msg = ""
                            try:
                                webbrowser.open(url)
                                success = True
                            except Exception as e:
                                error_msg = str(e)
                                
                            if success:
                                response_text = f"[EMOTION: HAPPY] I have opened {url} in your default browser!"
                            else:
                                response_text = f"[EMOTION: SAD] I tried to open the website, but encountered an error: {error_msg}"
                                
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                            await websocket.send_json({"type": "task_update", "task": None})
                    else:
                        response_text = response_data.get("content", "")
                        await websocket.send_json({
                            "type": "chat_response",
                            "content": response_text,
                            "timestamp": data.get("timestamp")
                        })
                        
                elif msg_type_str == "permission_response":
                    # Check if response is an object (for input/voice HITL or batch HITL) or boolean (for submit HITL)
                    if isinstance(data, dict) and ("value" in data or "values" in data):
                        allowed = data.get("allowed", False)
                        val = data.get("value", "")
                        vals = data.get("values", {})
                        print(f"[WS] HITL Input/Batch Response: Allowed={allowed}, Value='{val}', Values={vals}")
                        
                        from agent_tools import active_sessions
                        active_sessions["hitl_input_response"] = {"allowed": allowed, "value": val, "values": vals}
                        if "hitl_input" in active_sessions:
                            active_sessions["hitl_input"].set()
                    else:
                        allowed = data.get("allowed", False)
                        print(f"[WS] HITL Permission Response: {'Allowed' if allowed else 'Denied'}")
                        
                        # Update active form submission agent session
                        from agent_tools import active_sessions
                        active_sessions["submit_form_allowed"] = allowed
                        if "submit_form" in active_sessions:
                            active_sessions["submit_form"].set()
                    
            elif "bytes" in msg_type:
                audio_data = msg_type["bytes"]
                # print(f"[WS] Received audio chunk: {len(audio_data)} bytes")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("[WS] Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

