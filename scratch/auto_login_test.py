import urllib.parse
import database as db
from playwright.sync_api import sync_playwright

def auto_login_and_update_sessionid():
    settings = db.get_settings()
    username = settings.get("instagram_username", "")
    password = settings.get("instagram_password", "")
    
    print(f"Attempting auto-login for user: {username}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=25000)
        page.wait_for_selector("input[name='username']", timeout=12000)
        
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        
        page.wait_for_timeout(7000)
        print("Post-login URL:", page.url)
        
        cookies = context.cookies()
        found_session = ""
        for c in cookies:
            if c["name"] == "sessionid":
                found_session = c["value"]
                db.update_settings({"instagram_session_id": found_session})
                print(f"SUCCESSFULLY obtained & updated fresh Instagram sessionid: {found_session[:20]}...")
                break
                
        if not found_session:
            print("Login failed or requires 2FA security code. Page body:", page.evaluate("() => document.body.innerText.slice(0, 300)"))
            
        browser.close()
        return bool(found_session)

if __name__ == "__main__":
    auto_login_and_update_sessionid()
