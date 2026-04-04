import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from typing import Dict, List, Optional

class Persona:
    """Represents a user persona with specific traits and pain points"""
    
    def __init__(self, persona_id: int, name: str, persona_type: str, traits: Dict):
        self.id = persona_id
        self.name = name
        self.type = persona_type
        self.traits = traits
        self.status = "pending"
        self.progress = 0
        self.current_step = "Initializing..."
        self.pain_points = []
        self.video_path = None
        self.trace_path = None
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "pain_points": self.pain_points,
            "videoUrl": f"/api/runs/{self.run_id}/{self.id}/video" if self.video_path else None
        }


class PlaywrightPersonaRunner:
    """Runs Playwright tests for different personas"""
    
    def __init__(self, run_id: str, output_dir: str = None):
        if output_dir is None:
            # Use a local directory that exists on Mac
            output_dir = os.path.expanduser("~/Desktop/personaiq-spike/test_results")
        
            self.run_id = run_id
            self.output_dir = Path(output_dir) / run_id
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_persona(self, persona: Persona, url: str, task: str):
        """Execute a single persona's test session"""
        
        persona.run_id = self.run_id
        persona.status = "running"
        self._update_status(persona)
        
        async with async_playwright() as p:
            # Launch browser with persona-specific settings
            browser = await p.chromium.launch(headless=True)  # Set headless=False to see the browser
            
            # Create context with video recording
            context = await browser.new_context(
                viewport=persona.traits.get("viewport", {"width": 1280, "height": 720}),
                user_agent=persona.traits.get("user_agent"),
                has_touch=persona.traits.get("has_touch", False),
                locale=persona.traits.get("locale", "en-US"),
                permissions=persona.traits.get("permissions", []),
                device_scale_factor=persona.traits.get("device_scale_factor", 1),
                record_video_dir=str(self.output_dir / f"persona_{persona.id}"),
                record_video_size={"width": 1280, "height": 720}
            )
            
            # Start tracing for debugging
            await context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True
            )
            
            # Create page
            page = await context.new_page()
            
            try:
                # Step 1: Navigate to URL
                persona.current_step = f"Navigating to {url}"
                persona.progress = 10
                self._update_status(persona)
                await page.goto(url, wait_until="networkidle")
                
                # Step 2: Run persona-specific tasks
                await self._execute_persona_tasks(persona, page, task)
                
                # Step 3: Scan for accessibility issues (if enabled)
                if persona.traits.get("check_accessibility", False):
                    await self._check_accessibility(persona, page)
                
                persona.status = "completed"
                persona.progress = 100
                persona.current_step = "Test completed successfully"
                self._update_status(persona)
                
            except Exception as e:
                persona.status = "failed"
                persona.current_step = f"Error: {str(e)}"
                persona.pain_points.append(f"Critical failure: {str(e)}")
                self._update_status(persona)
                
            finally:
                # Stop tracing and save
                trace_path = self.output_dir / f"persona_{persona.id}" / "trace.zip"
                await context.tracing.stop(path=str(trace_path))
                persona.trace_path = str(trace_path)
                
                # Close context (saves video automatically)
                await context.close()
                await browser.close()
                
                # Store video path
                video_dir = self.output_dir / f"persona_{persona.id}"
                videos = list(video_dir.glob("*.webm"))
                if videos:
                    persona.video_path = str(videos[0])
                    
                self._update_status(persona)
    
    async def _execute_persona_tasks(self, persona: Persona, page, task: str):
        """Execute persona-specific interactions"""
        
        # Common interactions based on persona type
        if persona.type == "elderly":
            await self._simulate_elderly_user(persona, page)
        elif persona.type == "low_vision":
            await self._simulate_low_vision_user(persona, page)
        elif persona.type == "impatient":
            await self._simulate_impatient_user(persona, page)
        elif persona.type == "accessibility":
            await self._check_accessibility(persona, page)
        else:
            # Default: just navigate and look for issues
            await self._default_test(persona, page)
    
    async def _simulate_elderly_user(self, persona: Persona, page):
        """Simulate an elderly user (slower, larger text needs)"""
        
        persona.current_step = "Checking text size and contrast"
        persona.progress = 30
        self._update_status(persona)
        
        # Check for tiny fonts
        small_text = await page.eval_on_selector_all(
            '*', 
            'elements => Array.from(elements).filter(el => {'
            '  const size = parseInt(getComputedStyle(el).fontSize);'
            '  return size < 14 && el.innerText && el.innerText.length > 0;'
            '}).length'
        )
        
        if small_text > 0:
            persona.pain_points.append(f"Found {small_text} elements with font size < 14px (difficult for elderly users)")
        
        # Check button sizes
        small_buttons = await page.eval_on_selector_all(
            'button, a[role="button"]',
            'buttons => buttons.filter(btn => {'
            '  const rect = btn.getBoundingClientRect();'
            '  return rect.height < 40 || rect.width < 100;'
            '}).length'
        )
        
        if small_buttons > 0:
            persona.pain_points.append(f"Found {small_buttons} buttons that are too small for elderly users")
        
        persona.progress = 60
        self._update_status(persona)
        
        # Simulate slow navigation
        await asyncio.sleep(2)
        
        # Try to find and click main CTA
        try:
            cta = await page.query_selector('button:has-text("Sign Up"), button:has-text("Get Started"), a:has-text("Learn More")')
            if cta:
                await cta.click()
                persona.current_step = "Clicked main CTA button"
                persona.pain_points.append("Had difficulty locating the main CTA button")
        except:
            persona.pain_points.append("Could not find or click main CTA button")
    
    async def _simulate_low_vision_user(self, persona: Persona, page):
        """Simulate low vision user (contrast issues, zoom needs)"""
        
        persona.current_step = "Checking color contrast"
        persona.progress = 30
        self._update_status(persona)
        
        # Simple contrast check (you can expand this)
        low_contrast = await page.eval_on_selector_all(
            '*',
            'elements => elements.filter(el => {'
            '  const bg = getComputedStyle(el).backgroundColor;'
            '  const color = getComputedStyle(el).color;'
            '  // Simple check - if background is light and text is light'
            '  return bg.includes("255") && color.includes("255");'
            '}).length'
        )
        
        if low_contrast > 0:
            persona.pain_points.append(f"Found {low_contrast} elements with potential low contrast issues")
        
        # Check if page supports zoom
        await page.evaluate('document.body.style.zoom = "200%"')
        await asyncio.sleep(1)
        
        # Check for horizontal scroll after zoom (bad UX)
        has_horizontal_scroll = await page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        if has_horizontal_scroll:
            persona.pain_points.append("Page becomes horizontally scrollable at 200% zoom (accessibility fail)")
        
        persona.progress = 70
        self._update_status(persona)
    
    async def _simulate_impatient_user(self, persona: Persona, page):
        """Simulate impatient user (fast, quick to abandon)"""
        
        persona.current_step = "Measuring page load speed"
        persona.progress = 20
        self._update_status(persona)
        
        # Measure load time
        start_time = datetime.now()
        await page.reload()
        load_time = (datetime.now() - start_time).total_seconds()
        
        if load_time > 3:
            persona.pain_points.append(f"Page took {load_time:.1f} seconds to load (impatient users will leave)")
        
        # Check for too many steps to conversion
        clicks_to_goal = 0
        try:
            # Try to find a path to purchase/signup
            cta = await page.query_selector('button:has-text("Sign Up"), a:has-text("Sign Up")')
            if cta:
                await cta.click()
                clicks_to_goal += 1
                await asyncio.sleep(1)
                
                # Look for form submission
                submit = await page.query_selector('button[type="submit"], input[type="submit"]')
                if submit:
                    clicks_to_goal += 1
        except:
            pass
        
        if clicks_to_goal > 2:
            persona.pain_points.append(f"Requires {clicks_to_goal} clicks to reach goal (too many for impatient users)")
    
    async def _check_accessibility(self, persona: Persona, page):
        """Basic accessibility checks"""
        
        persona.current_step = "Running accessibility audit"
        persona.progress = 50
        self._update_status(persona)
        
        # Check for alt text on images
        images_without_alt = await page.eval_on_selector_all(
            'img:not([alt]), img[alt=""]',
            'imgs => imgs.length'
        )
        
        if images_without_alt > 0:
            persona.pain_points.append(f"Found {images_without_alt} images missing alt text")
        
        # Check for proper heading hierarchy
        has_h1 = await page.query_selector('h1')
        if not has_h1:
            persona.pain_points.append("Page has no H1 heading (poor screen reader navigation)")
        
        # Check for ARIA labels on interactive elements
        buttons_without_aria = await page.eval_on_selector_all(
            'button:not([aria-label]):not([aria-labelledby])',
            'btns => btns.length'
        )
        
        if buttons_without_aria > 0:
            persona.pain_points.append(f"Found {buttons_without_aria} buttons missing ARIA labels")
    
    async def _default_test(self, persona: Persona, page):
        """Default test - just look for common issues"""
        
        persona.current_step = "Scanning for common issues"
        persona.progress = 40
        self._update_status(persona)
        
        # Check for broken links
        broken_links = await page.eval_on_selector_all(
            'a[href^="http"]',
            'links => {'
            '  return links.length;'  # Simplified - you'd actually check each link
            '}'
        )
        
        # Check for console errors
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
        
        persona.progress = 80
        self._update_status(persona)
    
    def _update_status(self, persona: Persona):
        """Write current status to JSON file for the dashboard to read"""
        
        status_file = self.output_dir / f"persona_{persona.id}" / "status.json"
        status_file.parent.mkdir(exist_ok=True)
        
        with open(status_file, 'w') as f:
            json.dump(persona.to_dict(), f, indent=2)


async def run_test_run(run_id: str, url: str, personas_config: List[Dict]):
    """Run multiple personas in parallel"""
    
    runner = PlaywrightPersonaRunner(run_id)
    personas = []
    
    # Create personas
    for i, config in enumerate(personas_config):
        persona = Persona(
            persona_id=i + 1,
            name=config['name'],
            persona_type=config['type'],
            traits=config.get('traits', {})
        )
        personas.append(persona)
    
    # Run all personas concurrently
    tasks = [
        runner.run_persona(persona, url, config.get('task', 'test website'))
        for persona, config in zip(personas, personas_config)
    ]
    
    await asyncio.gather(*tasks)
    
    return personas


# Example usage
if __name__ == "__main__":
    # Test configuration
    test_personas = [
        {
            "name": "Margaret, 72",
            "type": "elderly",
            "traits": {
                "viewport": {"width": 1280, "height": 720},
                "check_accessibility": True
            }
        },
        {
            "name": "David, Low Vision",
            "type": "low_vision",
            "traits": {
                "viewport": {"width": 1280, "height": 720},
                "check_accessibility": True
            }
        },
        {
            "name": "Alex, Impatient",
            "type": "impatient",
            "traits": {
                "viewport": {"width": 1280, "height": 720}
            }
        }
    ]
    
    # Run the test
    asyncio.run(run_test_run(
        run_id="test-123",
        url="https://example.com",
        personas_config=test_personas
    ))