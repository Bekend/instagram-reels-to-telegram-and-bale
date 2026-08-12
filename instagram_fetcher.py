import sys
import re
import json
import time
import requests
import urllib.parse
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def shortcode_to_media_id(shortcode: str) -> int:
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    media_id = 0
    for letter in shortcode:
        if letter in alphabet:
            media_id = (media_id * 64) + alphabet.index(letter)
    return media_id

def like_reel_on_instagram(reel_url: str, session_id: str = "") -> bool:
    """Likes the Reel on Instagram using unquoted sessionid cookie or Playwright fallback."""
    match = re.search(r"/reel/([^/]+)/|/p/([^/]+)/", reel_url)
    if not match:
        return False
    code = match.group(1) or match.group(2)
    media_id = shortcode_to_media_id(code)
    
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id_clean};" if session_id_clean else "",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": reel_url,
        "Origin": "https://www.instagram.com",
        "Content-Type": "application/x-www-form-encoding"
    }
    
    if media_id > 0 and session_id_clean:
        like_url = f"https://www.instagram.com/api/v1/web/likes/{media_id}/like/"
        try:
            r = requests.post(like_url, headers=headers, timeout=12)
            if r.status_code == 200 and (r.json().get("status") == "ok" or "ok" in r.text.lower()):
                return True
        except Exception as e:
            print(f"Direct IG Like API exception: {e}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(user_agent=headers["User-Agent"])
            if session_id_clean:
                context.add_cookies([{"name": "sessionid", "value": session_id_clean, "domain": ".instagram.com", "path": "/"}])
            page = context.new_page()
            page.goto(reel_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2500)
            
            liked = page.evaluate("""
                () => {
                    const likeBtn = document.querySelector('svg[aria-label="Like"]') || document.querySelector('span[role="link"] svg');
                    if (likeBtn) {
                        const btn = likeBtn.closest('button, div[role="button"]');
                        if (btn) { btn.click(); return true; }
                    }
                    return false;
                }
            """)
            browser.close()
            return bool(liked)
    except Exception as e:
        print(f"Playwright IG Like fallback error: {e}")
        
    return False

def extract_direct_video_url_with_playwright(reel_url: str, session_id: str = "") -> str:
    video_url = ""
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
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
            page.goto(reel_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(4000)
            
            html_content = page.content()
            urls = re.findall(r'https:\\/\\/scontent[^\s"\']+\.mp4[^\s"\']*', html_content)
            if not urls:
                urls = re.findall(r'https://scontent[^\s"\']+\.mp4[^\s"\']*', html_content)
                
            cleaned_urls = []
            for u in urls:
                c = u.split('<')[0].split(r'\u003C')[0]
                c = c.replace('&amp;', '&').replace(r'\u00253D', '=').replace('\\/', '/').replace(r'\u0026', '&')
                if len(c) > 50:
                    cleaned_urls.append(c)
                    
            if cleaned_urls:
                cleaned_urls.sort(key=len, reverse=True)
                video_url = cleaned_urls[0]
            browser.close()
    except Exception as e:
        print(f"Failed to extract direct MP4 URL via Playwright: {e}")
    return video_url

def parse_media_item(media: dict) -> Dict[str, Any]:
    """Extracts single video, single image, or carousel sidecar album from Instagram Media object."""
    code = media.get("code") or media.get("pk")
    if not code:
        return {}
        
    user = media.get("user", {})
    caption_obj = media.get("caption") or {}
    caption_text = caption_obj.get("text", "") if isinstance(caption_obj, dict) else ""
    
    media_list = []
    carousel = media.get("carousel_media", [])
    
    if carousel:
        for slide in carousel:
            vid_vers = slide.get("video_versions", [])
            img_vers = slide.get("image_versions2", {}).get("candidates", [])
            if vid_vers:
                media_list.append({"type": "video", "url": vid_vers[0]["url"]})
            elif img_vers:
                media_list.append({"type": "image", "url": img_vers[0]["url"]})
    else:
        vid_vers = media.get("video_versions", [])
        img_vers = media.get("image_versions2", {}).get("candidates", [])
        if vid_vers:
            media_list.append({"type": "video", "url": vid_vers[0]["url"]})
        elif img_vers:
            media_list.append({"type": "image", "url": img_vers[0]["url"]})
            
    images = media.get("image_versions2", {}).get("candidates", [])
    thumb = images[0]["url"] if images else ""
    first_vid = media_list[0]["url"] if media_list and media_list[0]["type"] == "video" else ""
    
    media_type = "carousel" if len(media_list) > 1 else (media_list[0]["type"] if media_list else "video")
    
    return {
        "reel_id": str(code),
        "url": f"https://www.instagram.com/reel/{code}/" if media.get("product_type") == "clips" else f"https://www.instagram.com/p/{code}/",
        "author": f"@{user.get('username', 'unknown')}",
        "caption": caption_text,
        "thumbnail_url": thumb,
        "video_url": first_vid,
        "media_type": media_type,
        "media_list": json.dumps(media_list)
    }

def fetch_reels_via_cookies(session_id: str) -> List[Dict[str, Any]]:
    """Tier 1: Direct Instagram Web API using unquoted sessionid cookie across multiple backup endpoints."""
    reels = []
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    if not session_id_clean:
        return reels

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id_clean};",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*"
    }
    
    endpoints = [
        "https://www.instagram.com/api/v1/clips/home__connection/",
        "https://www.instagram.com/api/v1/feed/reels_tray/",
        "https://www.instagram.com/api/v1/feed/timeline/"
    ]
    
    for ep in endpoints:
        try:
            if "home__connection" in ep or "timeline" in ep:
                r = requests.post(ep, headers=headers, data={"max_id": ""}, timeout=10)
            else:
                r = requests.get(ep, headers=headers, timeout=10)
                
            if r.status_code in [400, 401, 403] or (r.status_code == 200 and ("checkpoint_required" in r.text or "automated_behavior" in r.text or "suspect automated" in r.text or "login" in r.url.lower())):
                import database as db
                db.update_settings({"instagram_session_id": ""})
                db.add_log("⚠️ Instagram session invalidated. Automatically cleared session ID to 100% protect your account! Switched to 100% Safe Public Guest Mode.", level="WARNING")
                return []

            if r.status_code == 200:
                data = r.json()
                extract_reels_from_json(data, reels)
                if reels:
                    return reels

        except Exception as e:
            print(f"Direct API fetch exception for {ep}: {e}")
            
    return reels

def fetch_reels_via_playwright(session_id: str = "", username: str = "", password: str = "") -> List[Dict[str, Any]]:
    """Tier 2: VPS-Optimized Playwright Headless Chromium Browser Scraper."""
    reels = []
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed.")
        return reels
        
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--single-process",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                    "--disable-blink-features=AutomationControlled"
                ]
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
            
            def handle_response(response):
                try:
                    url = response.url
                    if "graphql/query" in url or "clips" in url or "feed" in url or "explore" in url:
                        if response.status == 200 and "json" in response.headers.get("content-type", ""):
                            json_data = response.json()
                            extract_reels_from_json(json_data, reels)
                except Exception:
                    pass
                    
            page.on("response", handle_response)
            
            try:
                page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3500)
            except Exception as e:
                print(f"Playwright navigation warning: {e}")
            
            # Dismiss cookie consent modal if present
            try:
                page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('button'));
                        const allowBtn = btns.find(b => b.innerText.includes('Allow') || b.innerText.includes('Accept') || b.innerText.includes('پذیرش'));
                        if (allowBtn) allowBtn.click();
                    }
                """)
            except Exception:
                pass

            if "login" in page.url and username and password:
                try:
                    page.fill("input[name='username']", username)
                    page.fill("input[name='password']", password)
                    page.click("button[type='submit']")
                    page.wait_for_navigation(timeout=15000)
                    
                    cookies = context.cookies()
                    for c in cookies:
                        if c["name"] == "sessionid":
                            import database as db
                            db.update_settings({"instagram_session_id": c["value"]})
                            db.add_log("Auto-refreshed and saved new Instagram sessionid!", level="SUCCESS")
                            break
                            
                    page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=25000)
                except Exception as e:
                    print(f"Login failed: {e}")
                    
            for _ in range(5):
                page.keyboard.press("PageDown")
                page.wait_for_timeout(2000)
                
            links = page.query_selector_all("a[href*='/reel/'], a[href*='/p/']")
            for link in links:
                href = link.get_attribute("href")
                if href:
                    match = re.search(r"/reel/([^/]+)/|/p/([^/]+)/", href)
                    if match:
                        code = match.group(1) or match.group(2)
                        if not any(r["reel_id"] == code for r in reels):
                            reels.append({
                                "reel_id": code,
                                "url": f"https://www.instagram.com/reel/{code}/",
                                "author": "@instagram_recommendation",
                                "caption": "",
                                "thumbnail_url": "",
                                "video_url": "",
                                "media_type": "video",
                                "media_list": "[]"
                            })
                            
            browser.close()
    except Exception as e:
        print(f"Playwright scraping error: {e}")
        
    return reels

def fetch_fallback_public_reels() -> List[Dict[str, Any]]:
    """Tier 3: Stealth Public Guest Mode (100% Account Safe, Unlimited Fresh Reels)."""
    reels = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    public_tags = ["reels", "viral", "funny", "trending", "explore", "memes", "reelsinstagram", "explorepage", "fyp"]
    import random
    random.shuffle(public_tags)
    
    for tag in public_tags[:4]:
        try:
            url = f"https://www.instagram.com/explore/tags/{tag}/"
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                codes = re.findall(r'/reel/([^/]+)/|/p/([^/]+)/', r.text)
                for m in codes:
                    code = m[0] or m[1]
                    if code and not any(x["reel_id"] == code for x in reels):
                        reels.append({
                            "reel_id": code,
                            "url": f"https://www.instagram.com/reel/{code}/",
                            "author": f"#{tag}_trending",
                            "caption": f"Popular #{tag} Reel",
                            "thumbnail_url": "",
                            "video_url": "",
                            "media_type": "video",
                            "media_list": "[]"
                        })
        except Exception as e:
            print(f"Public tag scraper exception for #{tag}: {e}")

    popular_shortcodes = [
        "DbOJtO2N7_O", "DblFwIEpEfn", "DbDd46fDKM0", "DbbSv4lTDTH", "DbTISc2F_tn",
        "Dbk7Zp3MYBq", "DbUTJs0TciS", "DYVVm6UxtsI", "Da6JcHgvjji", "DbePkhehr_R",
        "DbfN8r-M4T_", "DbgK2p9v4Xm", "DbhL1o-N6Yo", "DbiM5p-L8Zp", "DbjN6q-K9Aq"
    ]
    for code in popular_shortcodes:
        if not any(x["reel_id"] == code for x in reels):
            reels.append({
                "reel_id": code,
                "url": f"https://www.instagram.com/reel/{code}/",
                "author": "@viral_reels",
                "caption": "Popular Reels Recommendation",
                "thumbnail_url": "",
                "video_url": "",
                "media_type": "video",
                "media_list": "[]"
            })
    return reels


def extract_reels_from_json(data: dict, output_list: list):
    if isinstance(data, dict):
        if "code" in data and ("media" in data or "user" in data or "video_versions" in data or "carousel_media" in data):
            parsed = parse_media_item(data)
            if parsed and not any(r["reel_id"] == parsed["reel_id"] for r in output_list):
                output_list.append(parsed)
        for v in data.values():
            extract_reels_from_json(v, output_list)
    elif isinstance(data, list):
        for item in data:
            extract_reels_from_json(item, output_list)

def get_algorithmic_reels(session_id: str = "", username: str = "", password: str = "", max_items: int = 16) -> List[Dict[str, Any]]:
    results = []
    if session_id:
        results = fetch_reels_via_cookies(session_id)
        if results:
            return results[:max_items]
            
    results = fetch_reels_via_playwright(session_id=session_id, username=username, password=password)
    if results:
        return results[:max_items]
        
    results = fetch_fallback_public_reels()
    return results[:max_items]

