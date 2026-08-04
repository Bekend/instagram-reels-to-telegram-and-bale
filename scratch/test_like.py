import re
import requests
import urllib.parse
import database as db

def shortcode_to_media_id(shortcode: str) -> int:
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    media_id = 0
    for letter in shortcode:
        if letter in alphabet:
            media_id = (media_id * 64) + alphabet.index(letter)
    return media_id

def test_ig_like(url: str):
    settings = db.get_settings()
    session_id = settings.get("instagram_session_id", "")
    session_id_clean = urllib.parse.unquote(session_id) if session_id else ""
    
    match = re.search(r"/reel/([^/]+)/|/p/([^/]+)/", url)
    if not match:
        print("Invalid URL format")
        return
    code = match.group(1) or match.group(2)
    media_id = shortcode_to_media_id(code)
    
    print(f"Media ID: {media_id}, SessionID: {session_id_clean[:15]}...")
    
    s = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id_clean};",
        "X-IG-App-ID": "936619743392459",
        "Referer": url,
        "Origin": "https://www.instagram.com"
    }
    s.headers.update(headers)
    
    # 1. Fetch CSRF Token
    r1 = s.get(url, timeout=12)
    csrf = s.cookies.get("csrftoken", "")
    if not csrf:
        csrf_match = re.search(r'"csrf_token":"([^"]+)"', r1.text)
        if csrf_match:
            csrf = csrf_match.group(1)
            
    print(f"Extracted CSRF token: {csrf}")
    s.headers["X-CSRFToken"] = csrf or "missing"
    s.headers["X-Requested-With"] = "XMLHttpRequest"
    
    like_url = f"https://www.instagram.com/api/v1/web/likes/{media_id}/like/"
    r2 = s.post(like_url, timeout=12)
    print("API Like Response Status:", r2.status_code)
    print("API Like Response Text:", r2.text[:300])

if __name__ == "__main__":
    test_ig_like("https://www.instagram.com/reel/DblFwIEpEfn/")
