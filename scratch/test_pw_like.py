import re
import urllib.parse
import database as db
from playwright.sync_api import sync_playwright

def test_playwright_like(reel_url: str):
    settings = db.get_settings()
    session_id = settings.get("instagram_session_id", "")
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    
    print(f"Testing Playwright Like on {reel_url}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        if session_id_clean:
            context.add_cookies([{
                "name": "sessionid",
                "value": session_id_clean,
                "domain": ".instagram.com",
                "path": "/"
            }])
        page = context.new_page()
        page.goto(reel_url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3500)
        
        result = page.evaluate("""
            () => {
                const svgs = Array.from(document.querySelectorAll('svg'));
                const likeSvg = svgs.find(s => {
                    const label = s.getAttribute('aria-label') || '';
                    return label.includes('Like') || label.includes('پسندیدن');
                });
                if (likeSvg) {
                    const btn = likeSvg.closest('button, div[role="button"]');
                    if (btn) {
                        btn.click();
                        return "SUCCESSFULLY_CLICKED_LIKE";
                    }
                }
                return "LIKE_BUTTON_NOT_FOUND";
            }
        """)
        print("Playwright Like Result:", result)
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    test_playwright_like("https://www.instagram.com/reel/DblFwIEpEfn/")
