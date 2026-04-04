from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
from pathlib import Path
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict
import os

app = FastAPI()

# Enable CORS for Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active runs
active_runs = {}

async def run_persona_test(run_id: str, url: str):
    """Run all personas for a test run"""
    
    from playwright.async_api import async_playwright
    
    output_dir = Path(f"./test_results/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define personas
    personas = [
        {
            "id": 1,
            "name": "Margaret, 72",
            "type": "elderly",
            "avatar": "fa-user-graduate"
        },
        {
            "id": 2,
            "name": "David, Low Vision", 
            "type": "low_vision",
            "avatar": "fa-eye"
        },
        {
            "id": 3,
            "name": "Alex, Impatient",
            "type": "impatient",
            "avatar": "fa-tachometer-alt"
        }
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Set to False to see browsers
        
        tasks = []
        for persona in personas:
            task = run_single_persona(persona, url, output_dir, browser, run_id)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        await browser.close()
    
    # Mark run as complete
    active_runs[run_id]["status"] = "completed"
    active_runs[run_id]["completed_at"] = str(datetime.now())

async def run_single_persona(persona: Dict, url: str, output_dir: Path, browser, run_id: str):
    """Run a single persona test and update status in real-time"""
    
    persona_dir = output_dir / f"persona_{persona['id']}"
    persona_dir.mkdir(exist_ok=True)
    
    # Initial status
    status = {
        "id": persona["id"],
        "name": persona["name"],
        "type": persona["type"],
        "status": "running",
        "progress": 0,
        "current_step": "Starting browser...",
        "pain_points": [],
        "avatar": persona["avatar"]
    }
    
    # Save initial status
    status_file = persona_dir / "status.json"
    
    def update_status(step: str, progress: int, pain_point: str = None):
        status["current_step"] = step
        status["progress"] = progress
        if pain_point:
            status["pain_points"].append(pain_point)
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        # Update master run status
        if run_id in active_runs:
            persona_index = next((i for i, p in enumerate(active_runs[run_id]["personas"]) if p["id"] == persona["id"]), None)
            if persona_index is not None:
                active_runs[run_id]["personas"][persona_index] = status.copy()
    
    try:
        # Create context with video
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(persona_dir)
        )
        
        page = await context.new_page()
        
        # Step 1: Navigate
        update_status(f"Navigating to {url}", 10)
        await page.goto(url, wait_until="networkidle")
        
        # Step 2: Analyze based on persona type
        if persona["type"] == "elderly":
            update_status("Checking text sizes...", 30)
            
            small_text = await page.evaluate('''
                Array.from(document.querySelectorAll('*')).filter(el => {
                    const size = parseInt(getComputedStyle(el).fontSize);
                    return size < 14 && el.innerText && el.innerText.length > 0;
                }).length
            ''')
            
            if small_text > 0:
                update_status("Found text size issues", 50, f"Found {small_text} elements with tiny text (<14px)")
            
            small_buttons = await page.evaluate('''
                Array.from(document.querySelectorAll('button, a[role="button"]')).filter(btn => {
                    const rect = btn.getBoundingClientRect();
                    return rect.height < 40 || rect.width < 100;
                }).length
            ''')
            
            if small_buttons > 0:
                update_status("Found button size issues", 70, f"Found {small_buttons} buttons that are too small")
        
        elif persona["type"] == "low_vision":
            update_status("Checking color contrast...", 30)
            
            low_contrast = await page.evaluate('''
                Array.from(document.querySelectorAll('*')).filter(el => {
                    const bg = getComputedStyle(el).backgroundColor;
                    const color = getComputedStyle(el).color;
                    return bg.includes('255') && color.includes('255');
                }).length
            ''')
            
            if low_contrast > 0:
                update_status("Found contrast issues", 60, f"Found {low_contrast} potential contrast issues")
        
        elif persona["type"] == "impatient":
            update_status("Measuring load time...", 30)
            
            start = datetime.now()
            await page.reload()
            load_time = (datetime.now() - start).total_seconds()
            
            if load_time > 2:
                update_status("Found performance issues", 60, f"Page took {load_time:.1f} seconds to load")
        
        # Take screenshot
        update_status("Capturing screenshot...", 85)
        screenshot_path = persona_dir / "screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        
        # Close and save video
        update_status("Saving recording...", 95)
        await context.close()
        
        # Find video file
        video_files = list(persona_dir.glob("**/*.webm"))
        if video_files:
            status["videoUrl"] = f"/api/runs/{run_id}/{persona['id']}/video"
        
        # Complete
        update_status("Test completed successfully", 100)
        status["status"] = "completed"
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        print(f"✅ {persona['name']} completed with {len(status['pain_points'])} issues")
        
    except Exception as e:
        status["status"] = "failed"
        status["current_step"] = f"Error: {str(e)}"
        status["pain_points"].append(f"Critical error: {str(e)}")
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        print(f"❌ {persona['name']} failed: {str(e)}")

@app.post("/api/start-test")
async def start_test(url: str, background_tasks: BackgroundTasks):
    """Start a new test run"""
    
    run_id = str(uuid.uuid4())[:8]
    
    # Initialize run in memory
    active_runs[run_id] = {
        "run_id": run_id,
        "url": url,
        "status": "running",
        "started_at": str(datetime.now()),
        "personas": [
            {"id": 1, "name": "Margaret, 72", "type": "elderly", "status": "pending", "progress": 0},
            {"id": 2, "name": "David, Low Vision", "type": "low_vision", "status": "pending", "progress": 0},
            {"id": 3, "name": "Alex, Impatient", "type": "impatient", "status": "pending", "progress": 0}
        ]
    }
    
    # Run test in background
    background_tasks.add_task(run_persona_test, run_id, url)
    
    return {"run_id": run_id}

@app.get("/api/runs/{run_id}/status")
async def get_run_status(run_id: str):
    """Get current status of a test run"""
    
    if run_id in active_runs:
        return active_runs[run_id]
    
    # Check if run exists on disk (completed runs)
    output_dir = Path(f"./test_results/{run_id}")
    if output_dir.exists():
        personas = []
        for persona_dir in output_dir.glob("persona_*"):
            status_file = persona_dir / "status.json"
            if status_file.exists():
                with open(status_file, 'r') as f:
                    personas.append(json.load(f))
        
        return {
            "run_id": run_id,
            "status": "completed",
            "personas": personas
        }
    
    return {"error": "Run not found"}

@app.get("/api/runs/{run_id}/{persona_id}/video")
async def get_video(run_id: str, persona_id: int):
    """Serve video file for a persona"""
    
    video_path = Path(f"./test_results/{run_id}/persona_{persona_id}")
    video_files = list(video_path.glob("**/*.webm"))
    
    if video_files:
        return FileResponse(video_files[0], media_type="video/webm")
    
    return {"error": "Video not found"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting PersonaIQ API server...")
    print("📡 API available at http://localhost:8000")
    print("📊 Dashboard should connect to http://localhost:8000/api")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)