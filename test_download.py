import re
import requests
from playwright.sync_api import sync_playwright
import database as db

settings = db.get_settings()
session_id = settings.get('instagram_session_id', '')
reel_url = 'https://www.instagram.com/reel/DblFwIEpEfn/'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    if session_id:
        context.add_cookies([{
            'name': 'sessionid',
            'value': session_id,
            'domain': '.instagram.com',
            'path': '/'
        }])
    page = context.new_page()
    page.goto(reel_url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(4000)
    
    html = page.content()
    
    urls = re.findall(r'https:\\/\\/scontent[^\s"\']+\.mp4[^\s"\']*', html)
    if not urls:
        urls = re.findall(r'https://scontent[^\s"\']+\.mp4[^\s"\']*', html)
        
    cleaned_urls = []
    for u in urls:
        c = u.split('<')[0].split(r'\u003C')[0]
        c = c.replace('&amp;', '&').replace(r'\u00253D', '=').replace('\\/', '/').replace(r'\u0026', '&')
        cleaned_urls.append(c)
        
    print("Found Cleaned MP4 URLs:", len(cleaned_urls))
    if cleaned_urls:
        for idx, u in enumerate(cleaned_urls[:3]):
            print(f"\nURL [{idx}]: {u[:120]}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.instagram.com/'
            }
            res = requests.get(u, headers=headers)
            print(f"Download [{idx}] size: {len(res.content)} bytes, status: {res.status_code}")
        
    browser.close()
