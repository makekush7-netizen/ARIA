import sys
import os
import asyncio
from pathlib import Path
import re
from typing import Dict, Any

# We'll use sync or async playwright. Since uvicorn runs in asyncio, let's use async Playwright.
from playwright.async_api import async_playwright

PROFILE_PATH = Path(__file__).parent / "browser_profile"

# Global list to track active WebSocket connections without circular imports
active_websockets = []

async def broadcast_status(websocket, text: str):
    """Utility to send task updates to the frontend websocket if open"""
    # Always include the passed websocket if not already in list
    targets = list(active_websockets)
    if websocket and websocket not in targets:
        targets.append(websocket)
        
    for ws in targets:
        try:
            await ws.send_json({
                "type": "task_update",
                "task": text
            })
        except Exception:
            pass

def clean_label(text: str) -> str:
    """Normalize label text for matching"""
    if not text:
        return ""
    # Strip asterisks (required fields) and clean whitespace
    return re.sub(r'[*:\s]+', ' ', text).strip().lower()

def match_field_key(label: str, placeholder: str, name_attr: str) -> str:
    """Match form field labels/meta to memory keys"""
    combined = f"{label} {placeholder} {name_attr}".lower()
    
    # 1. Email matching
    if any(x in combined for x in ["email", "e-mail", "mail id"]):
        return "email"
        
    # 2. Phone matching
    if any(x in combined for x in ["phone", "mobile", "contact", "tel", "number"]) and not any(x in combined for x in ["roll"]):
        return "phone"
        
    # 3. Roll No matching
    if any(x in combined for x in ["roll", "reg", "registration", "id number"]):
        return "rollNo"
        
    # 4. College matching
    if any(x in combined for x in ["college", "university", "institute", "school"]):
        return "college"
        
    # 5. Department matching
    if any(x in combined for x in ["dept", "department", "branch", "course"]):
        return "department"
        
    # 6. Name matching
    if any(x in combined for x in ["name", "full name", "first name", "last name"]):
        return "name"
        
    return ""

# Global store for active agent sessions (concurrency and HITL approvals)
active_sessions: Dict[str, Any] = {}

async def fill_form_with_playwright(url: str, memory: Dict[str, str], websocket=None) -> str:
    """
    Launches Chromium with a persistent profile, navigates to url,
    and runs a reactive loop that automatically fills out fields as soon as they appear.
    """
    await broadcast_status(websocket, f"Launching Google-linked browser profile...")
    
    # Make sure profile path exists
    PROFILE_PATH.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch persistent context so user stays signed in to Google
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]  # Bypass basic bot checks
        )
        
        page = await context.new_page()
        
        await broadcast_status(websocket, f"Navigating to form...")
        await page.goto(url, wait_until="load")
        
        # Reactive state variables
        filled = False
        last_status = ""
        
        while not page.is_closed():
            try:
                # 1. Detect if we are on a Google Sign-In page or modal is visible
                current_url = page.url.lower()
                sign_in_modal = await page.query_selector('text="Sign in to continue", text="SIGN IN", role="dialog"')
                
                if sign_in_modal or "accounts.google" in current_url or "signin" in current_url:
                    status_text = "Google Sign-In required! Please securely enter your credentials in the browser window..."
                    if last_status != status_text:
                        await broadcast_status(websocket, status_text)
                        last_status = status_text
                    
                    # Auto-click SIGN IN modal if present
                    sign_in_btn = await page.query_selector('text="SIGN IN", text="Sign in", [role="button"]')
                    if sign_in_btn:
                        try:
                            await sign_in_btn.click()
                        except Exception:
                            pass
                    
                    await asyncio.sleep(2)
                    continue
                
                # 2. Query visible form input fields
                inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], textarea')
                
                if len(inputs) > 0 and not filled:
                    status_text = "Form fields detected! Automatically filling your details..."
                    await broadcast_status(websocket, status_text)
                    last_status = status_text
                    
                    filled_count = 0
                    filled_fields = []
                    
                    for input_el in inputs:
                        placeholder = await input_el.get_attribute("placeholder") or ""
                        name_attr = await input_el.get_attribute("name") or ""
                        id_attr = await input_el.get_attribute("id") or ""
                        aria_label = await input_el.get_attribute("aria-label") or ""
                        aria_labelledby = await input_el.get_attribute("aria-labelledby") or ""
                        
                        label_text = ""
                        
                        # 1. Try aria-label directly
                        if aria_label:
                            label_text += " " + aria_label
                            
                        # 2. Try aria-labelledby references
                        if aria_labelledby:
                            for label_id in aria_labelledby.split():
                                if label_id:
                                    try:
                                        label_el = await page.query_selector(f'#{label_id}')
                                        if label_el:
                                            text = await label_el.inner_text()
                                            if text:
                                                label_text += " " + text
                                    except Exception:
                                        pass
                                        
                        # 3. Try finding closest question block ancestor (for Google Forms)
                        try:
                            question_block = await input_el.evaluate_handle(
                                "el => el.closest('.Qr7Oae, [role=\"listitem\"], .freebirdFormviewerComponentsQuestionBaseRoot')"
                            )
                            if question_block and question_block.as_element():
                                title_el = await question_block.as_element().query_selector('.M7e36, [role=\"heading\"], label, .Ho3o1')
                                if title_el:
                                    text = await title_el.inner_text()
                                    if text:
                                        label_text += " " + text
                        except Exception as e:
                            print(f"[Form Agent closest block debug error]: {e}")
                            
                        # 4. Fallback: Search parent tree
                        if not label_text.strip():
                            parent = await input_el.evaluate_handle("el => el.parentElement")
                            for _ in range(5):
                                if not parent or not parent.as_element():
                                    break
                                label_el = await parent.as_element().query_selector('label, [role=\"heading\"], .M7e36, .Ho3o1')
                                if label_el:
                                    text = await label_el.inner_text()
                                    if text:
                                        label_text += " " + text
                                        break
                                parent = await parent.evaluate_handle("el => el.parentElement")
                                
                        # 5. Fallback: Search label[for="id"]
                        if not label_text.strip() and id_attr:
                            label_el = await page.query_selector(f'label[for="{id_attr}"]')
                            if label_el:
                                text = await label_el.inner_text()
                                if text:
                                    label_text += " " + text
                                    
                        # Clean up text
                        label_text = clean_label(label_text)
                        placeholder = clean_label(placeholder)
                        
                        # Match field to memory key
                        matched_key = match_field_key(label_text, placeholder, name_attr)
                        
                        # LOG DEBUG TO CONSOLE FOR EASY DIAGNOSIS
                        print(f"[Form Agent DEBUG] input found: id='{id_attr}', name='{name_attr}', aria-label='{aria_label}', label_extracted='{label_text}', matched_key='{matched_key}'")
                        
                        if matched_key and memory.get(matched_key):
                            val = memory[matched_key]
                            await input_el.focus()
                            await input_el.fill("")
                            await page.keyboard.type(val, delay=40)
                            filled_count += 1
                            filled_fields.append(f"{matched_key} -> '{label_text or name_attr}'")
                            await asyncio.sleep(0.3)
                    
                    if filled_count > 0:
                        filled = True
                        status_msg = f"Successfully filled {filled_count} fields: {', '.join(filled_fields)}!"
                        await broadcast_status(websocket, status_msg)
                        last_status = status_msg
                        
                        # Request HITL permission to submit
                        await broadcast_status(websocket, "Requesting submission permission...")
                        active_sessions["submit_form_allowed"] = False
                        event = asyncio.Event()
                        active_sessions["submit_form"] = event
                        
                        try:
                            targets = list(active_websockets)
                            if websocket and websocket not in targets:
                                targets.append(websocket)
                                
                            for ws in targets:
                                try:
                                    await ws.send_json({
                                        "type": "permission_request",
                                        "title": "Confirm Form Submission",
                                        "description": f"I have successfully matched and filled out all {filled_count} fields on the form. Would you like me to click the 'Submit' button automatically for you?",
                                        "id": "submit_form"
                                    })
                                except Exception:
                                    pass
                            
                            # Wait for user's response (30 seconds timeout)
                            await asyncio.wait_for(event.wait(), timeout=30.0)
                            allowed = active_sessions.get("submit_form_allowed", False)
                        except Exception as e:
                            print(f"[Form Agent Submit Wait Error]: {e}")
                            allowed = False
                            
                        if allowed:
                            await broadcast_status(websocket, "Submitting form automatically...")
                            submit_selectors = [
                                'div[role="button"]:has-text("Submit")',
                                'div[role="button"]:has-text("SUBMIT")',
                                'span:has-text("Submit")',
                                'span:has-text("SUBMIT")',
                                'text="Submit"',
                                'text="SUBMIT"',
                                '[type="submit"]'
                            ]
                            clicked = False
                            for selector in submit_selectors:
                                try:
                                    btn = await page.query_selector(selector)
                                    if btn and await btn.is_visible():
                                        await btn.focus()
                                        await btn.click()
                                        clicked = True
                                        await broadcast_status(websocket, "Form submitted successfully!")
                                        print(f"[Form Agent Submit DEBUG]: Successfully clicked submit button using selector '{selector}'")
                                        break
                                except Exception as e:
                                    print(f"[Form Agent Submit DEBUG]: Failed clicking selector '{selector}': {e}")
                            
                            if not clicked:
                                await broadcast_status(websocket, "Could not find the Submit button on the page.")
                            else:
                                await asyncio.sleep(4)
                        else:
                            await broadcast_status(websocket, "Submission declined. Keeping the form open for your manual submission.")
                        
                        # Keep window open so user can inspect
                        await broadcast_status(websocket, "Form is ready. Close browser when done.")
                    else:
                        await broadcast_status(websocket, "No matching fields found in form yet. Close browser when done.")
                        await asyncio.sleep(3)
                        
                elif len(inputs) == 0:
                    status_text = "Waiting for form fields to load..."
                    if last_status != status_text:
                        await broadcast_status(websocket, status_text)
                        last_status = status_text
                
                await asyncio.sleep(2)
                
            except Exception as e:
                # Silently catch exceptions during browser transitions
                print(f"[Form Agent Loop Exception]: {e}")
                await asyncio.sleep(2)
                
        await context.close()
        
    return "Form filling task complete!"
