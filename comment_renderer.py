import sys
import re
import html
import random
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

GENERIC_COMMENTS_POOL = [
    {"username": "alex_vibes", "text": "This is literally so true! 😂🔥", "time": "2h", "likes": "1.4k"},
    {"username": "parsa_dev", "text": "دقیقا منم وقتی ویدیو رو دیدم 💀", "time": "3h", "likes": "980"},
    {"username": "cyber_sam", "text": "Wait for the end part haha 😶", "time": "3h", "likes": "890"},
    {"username": "sarah.m", "text": "حق ترین ریلز امشب بود 👏", "time": "4h", "likes": "720"},
    {"username": "trend_watcher", "text": "Sending this to group chat right now!", "time": "5h", "likes": "430"},
    {"username": "ali_rezai", "text": "اصلا باورم نمیشد تهش اینطوری بشه 😂", "time": "6h", "likes": "350"},
    {"username": "digital_nomad", "text": "How is this so accurate?? 😭", "time": "6h", "likes": "210"},
    {"username": "reels_master", "text": "Best video I've seen all day 🚀", "time": "8h", "likes": "154"},
    {"username": "neda_art", "text": "وای خیلی خوب بود 🤣❤️", "time": "9h", "likes": "128"},
    {"username": "sam_vlog", "text": "Relatable on another level 💯", "time": "10h", "likes": "95"}
]

def get_generic_comments(count: int = 5) -> List[Dict[str, Any]]:
    """Returns a randomized selection of realistic generic comments."""
    selected = random.sample(GENERIC_COMMENTS_POOL, min(count, len(GENERIC_COMMENTS_POOL)))
    return selected

def fetch_reel_comments(reel_url: str = "", session_id: str = "", max_comments: int = 5) -> List[Dict[str, Any]]:
    """Returns generic comments for all posts as requested."""
    return get_generic_comments(count=max_comments)

def render_comments_card_image(comments: List[Dict[str, Any]]) -> bytes:
    """Renders a pixel-perfect 1:1 replica of the Instagram Comments screen template as PNG bytes."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return b""
        
    comments_html = ""
    for c in comments:
        uname = html.escape(c.get("username", "user"))
        ctext = html.escape(c.get("text", ""))
        ctime = html.escape(c.get("time", "1h"))
        clikes = html.escape(str(c.get("likes", "0")))
        initial = uname[0].upper() if uname else "U"
        
        comments_html += f"""
        <div class="comment-item">
            <div class="avatar">{initial}</div>
            <div class="comment-content">
                <span class="username">{uname}</span>
                <span class="comment-text">{ctext}</span>
                <div class="comment-meta">
                    <span>{ctime}</span>
                    <span>{clikes}</span>
                    <span class="like-btn">Reply</span>
                </div>
            </div>
            <div class="heart-column">
                <span class="heart-icon">♡</span>
            </div>
        </div>
        """
        
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif; }}
      body {{ width: 420px; background: #ffffff; color: #262626; margin: 0; padding: 0; overflow: hidden; }}
      
      .container {{
        width: 420px;
        background: #ffffff;
        display: flex;
        flex-direction: column;
        border: 1px solid #dbdbdb;
      }}
      
      .header {{
        height: 52px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 16px;
        border-bottom: 1px solid #efefef;
        background: #ffffff;
      }}
      
      .header-title {{
        font-size: 16px;
        font-weight: 700;
        color: #262626;
      }}
      
      .back-icon {{
        font-size: 22px;
        color: #262626;
        font-weight: 300;
        cursor: pointer;
      }}
      
      .share-icon {{
        font-size: 20px;
        color: #262626;
      }}
      
      .comments-list {{
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 18px;
        background: #ffffff;
        min-height: 380px;
      }}
      
      .comment-item {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
      }}
      
      .avatar {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: 700;
        font-size: 14px;
        flex-shrink: 0;
      }}
      
      .comment-content {{
        flex: 1;
        font-size: 13.5px;
        line-height: 1.4;
        color: #262626;
      }}
      
      .username {{
        font-weight: 700;
        margin-right: 6px;
        color: #262626;
      }}
      
      .comment-text {{
        font-weight: 400;
        color: #262626;
      }}
      
      .comment-meta {{
        display: flex;
        align-items: center;
        gap: 14px;
        margin-top: 4px;
        font-size: 12px;
        color: #8e8e8e;
        font-weight: 600;
      }}
      
      .like-btn {{
        cursor: pointer;
        color: #8e8e8e;
      }}
      
      .heart-column {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        flex-shrink: 0;
        margin-top: 2px;
      }}
      
      .heart-icon {{
        font-size: 16px;
        color: #8e8e8e;
      }}
      
      .footer {{
        height: 64px;
        border-top: 1px solid #efefef;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0 16px;
        background: #ffffff;
      }}
      
      .footer-avatar {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #efefef;
        border: 1px solid #dbdbdb;
        flex-shrink: 0;
      }}
      
      .input-box {{
        flex: 1;
        height: 42px;
        border: 1px solid #dbdbdb;
        border-radius: 22px;
        padding: 0 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13.5px;
        color: #8e8e8e;
      }}
      
      .post-btn {{
        color: #0095f6;
        font-weight: 600;
        cursor: pointer;
      }}
    </style>
    </head>
    <body>
      <div class="container" id="card">
        <div class="header">
          <span class="back-icon">‹</span>
          <span class="header-title">Comments</span>
          <span class="share-icon">✈</span>
        </div>
        <div class="comments-list">
          {comments_html}
        </div>
        <div class="footer">
          <div class="footer-avatar"></div>
          <div class="input-box">
            <span>Add a comment...</span>
            <span class="post-btn">Post</span>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    
    img_bytes = b""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = browser.new_page(viewport={"width": 440, "height": 800})
        page.set_content(full_html)
        page.wait_for_timeout(500)
        card_el = page.query_selector("#card")
        if card_el:
            img_bytes = card_el.screenshot(type="png")
        browser.close()
        
    return img_bytes
