import re
import urllib.parse
import database as db
from playwright.sync_api import sync_playwright

def login_and_like_reel(reel_url: str) -> bool:
    settings = db.get_settings()
    username = settings.get("instagram_username", "")
    password = settings.get("instagram_password", "")
    session_id = settings.get("instagram_session_id", "")
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    
    print(f"Logging in & liking reel {reel_url}...")
    
    try:
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
            page.wait_for_timeout(3000)
            
            if "login" in page.url or page.query_selector("input[name='username']"):
                print("Session expired or invalid. Performing automated Instagram login...")
                try:
                    if "login" not in page.url:
                        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=20000)
                        
                    page.wait_for_selector("input[name='username']", timeout=10000)
                    page.fill("input[name='username']", username)
                    page.fill("input[name='password']", password)
                    page.click("button[type='submit']")
                    page.wait_for_timeout(6000)
                    
                    cookies = context.cookies()
                    for c in cookies:
                        if c["name"] == "sessionid":
                            db.update_settings({"instagram_session_id": c["value"]})
                            print("SUCCESSFULLY logged in & saved fresh sessionid to DB:", c["value"][:15])
                            break
                    page.goto(reel_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3500)
                except Exception as e:
                    print("Login exception:", e)
                    
            liked = page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                    const likeBtn = btns.find(b => {
                        const txt = b.innerText || '';
                        const aria = b.getAttribute('aria-label') || '';
                        return aria.includes('Like') || aria.includes('پسندیدن') || txt.includes('Like');
                    });
                    if (likeBtn) {
                        likeBtn.click();
                        return true;
                    }
                    return false;
                }
            """)
            print("Playwright Like click status:", liked)
            page.wait_for_timeout(2000)
            browser.close()
            return bool(liked)
    except Exception as e:
        print("Playwright like exception:", e)
        return False

if __name__ == "__main__":
    login_and_like_reel("https://www.instagram.com/reel/DblFwIEpEfn/")
