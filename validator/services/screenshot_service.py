from playwright.sync_api import sync_playwright

class ScreenshotService:
    @staticmethod
    def disable_animations(page):
        custom_css = """
            *, *::before, *::after {
                transition: none !important;
                animation: none !important;
                scroll-behavior: auto !important;
            }
        """
        page.add_style_tag(content=custom_css)

    @staticmethod
    def capture_screenshot(url, output_path):
        """
        Capture a full page screenshot using Playwright configured for a 1440x900 viewport.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page(viewport={'width': 1440, 'height': 900})
            
            js_errors = []
            
            # Listen for console errors
            page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: js_errors.append(err.message))
            
            try:
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                # Disable animations
                ScreenshotService.disable_animations(page)
                
                # Wait for any potential layout shifts
                page.wait_for_timeout(2000)
                
                # Calculate DOM complexity
                dom_count = page.evaluate("document.querySelectorAll('*').length")
                
                # Take screenshot
                page.screenshot(path=output_path, full_page=True)
                
                return {
                    "js_errors": js_errors,
                    "dom_count": dom_count
                }
            finally:
                browser.close()
