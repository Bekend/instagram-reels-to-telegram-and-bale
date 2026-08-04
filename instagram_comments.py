import sys
import re
import html
import json
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

def fetch_real_top_comments(reel_url: str, session_id: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """Extracts the EXACT REAL top 10 comments from the actual Instagram Reel post."""
    comments = []
    match = re.search(r"/reel/([^/]+)/", reel_url)
    if not match:
        return []
    code = match.group(1)
    media_id = shortcode_to_media_id(code)

    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": f"sessionid={session_id_clean};" if session_id_clean else "",
        "X-IG-App-ID": "936619743392459"
    }

    # Method 1: Instagram Official Direct Web API for Media Comments
    if media_id > 0:
        api_url = f"https://www.instagram.com/api/v1/media/{media_id}/comments/?can_support_threading=true"
        try:
            r = requests.get(api_url, headers=headers, timeout=12)
            if r.status_code == 200:
                data = json.loads(r.content)
                raw_comments = data.get("comments", [])
                for item in raw_comments:
                    user_info = item.get("user", {})
                    uname = user_info.get("username", "user")
                    c_text = item.get("text", "").strip()
                    c_likes = item.get("comment_like_count", 0)
                    if uname and c_text:
                        comments.append({
                            "username": uname,
                            "text": c_text,
                            "likes": c_likes
                        })
                if comments:
                    return comments[:limit]
        except Exception as e:
            print(f"Instagram comments API exception: {e}")

    # Method 2: Playwright Scraper Fallback for Real Comments
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(user_agent=headers["User-Agent"])
            if session_id_clean:
                context.add_cookies([{"name": "sessionid", "value": session_id_clean, "domain": ".instagram.com", "path": "/"}])
            page = context.new_page()
            page.goto(reel_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(4000)

            extracted = page.evaluate("""
                () => {
                    const list = [];
                    const items = document.querySelectorAll('ul div > div');
                    items.forEach(el => {
                        const userEl = el.querySelector('a span') || el.querySelector('h3 span') || el.querySelector('a');
                        const textEl = el.querySelector('span[dir="auto"]');
                        if (userEl && textEl) {
                            const u = userEl.innerText.trim();
                            const t = textEl.innerText.trim();
                            if (u && t && u.length < 30 && t.length < 300) {
                                if (!list.some(x => x.username === u && x.text === t)) {
                                    list.push({ username: u, text: t, likes: 0 });
                                }
                            }
                        }
                    });
                    return list;
                }
            """)
            if extracted:
                comments = extracted[:limit]
            browser.close()
    except Exception as e:
        print(f"Playwright real comments exception: {e}")

    return comments[:limit]

def format_comments_as_text(comments: List[Dict[str, Any]], reel_url: str = "") -> str:
    """Formats the real top 10 comments without any header lines."""
    if not comments:
        return ""

    output = ""
    for idx, c in enumerate(comments, 1):
        uname = html.escape(c.get("username", "user"))
        ctext = html.escape(c.get("text", ""))
        likes = c.get("likes", 0)
        like_str = f" (❤️ {likes})" if likes > 0 else ""
        output += f"{idx}. <b>@{uname}</b>{like_str}:\n<i>\"{ctext}\"</i>\n\n"

    return output.strip()
