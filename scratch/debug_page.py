import urllib.parse
import database as db
from playwright.sync_api import sync_playwright

def debug_ig_page(reel_url: str):
    settings = db.get_settings()
    username = settings.get("instagram_username", "")
    password = settings.get("instagram_password", "")
    session_id = settings.get("instagram_session_id", "")
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        if session_id_clean:
            context.add_cookies([{"name": "sessionid", "value": session_id_clean, "domain": ".instagram.com", "path": "/"}])
        page = context.new_page()
        page.goto(reel_url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3500)
        print("Page URL:", page.url)
        print("Page Title:", page.title())
        text_snippet = page.evaluate("() => document.body.innerText.slice(0, 300)")
        print("Page Body Snippet:", text_snippet)
        browser.close()

if __name__ == "__main__":
    debug_ig_page("https://www.instagram.com/reel/DblFwIEpEfn/")
