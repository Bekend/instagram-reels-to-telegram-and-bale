import sys
import os
import json
import requests
import html
import tempfile
from typing import Dict, Any, Tuple, List
import database as db
import instagram_fetcher as ig
import instagram_comments as ic

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TG_BASE_URL = "https://api.telegram.org/bot"

def get_tg_url(token: str, method: str) -> str:
    return f"{TG_BASE_URL}{token}/{method}"

def get_glass_buttons_reply_markup(reel_id: str = "") -> str:
    """Returns glass inline keyboard buttons for Liking and Requesting Top Comments with encoded reel_id."""
    like_data = f"like:{reel_id}" if reel_id else "like_reel"
    comments_data = f"comments:{reel_id}" if reel_id else "get_comments"
    return json.dumps({
        "inline_keyboard": [
            [
                {"text": "❤️ Like", "callback_data": like_data},
                {"text": "💬 Top 10 Comments", "callback_data": comments_data}
            ]
        ]
    })

def test_telegram_connection(bot_token: str, chat_id: str) -> Tuple[bool, str]:
    if not bot_token or not chat_id:
        return False, "Telegram Bot Token and Chat ID are required."
    
    me_url = get_tg_url(bot_token, "getMe")
    try:
        res = requests.get(me_url, timeout=10)
        res_data = res.json()
        if not res_data.get("ok"):
            return False, f"Invalid Telegram Bot Token: {res_data.get('description', 'Unknown error')}"
        bot_name = res_data["result"].get("first_name", "Telegram Bot")
    except Exception as e:
        return False, f"Failed to connect to Telegram API: {str(e)}"
    
    msg_url = get_tg_url(bot_token, "sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": f"🚀 <b>Telegram Reels Bot Active!</b>",
        "parse_mode": "HTML"
    }
    
    try:
        msg_res = requests.post(msg_url, json=payload, timeout=10)
        msg_data = msg_res.json()
        if msg_data.get("ok"):
            return True, f"Successfully sent test message via @{res_data['result'].get('username', bot_name)}!"
        else:
            return False, f"Failed to send test message: {msg_data.get('description', 'Check Chat ID')}"
    except Exception as e:
        return False, f"Failed to send message to Telegram: {str(e)}"

def send_real_comments_text_to_telegram(bot_token: str, chat_id: str, reel_url: str, session_id: str = "", reply_to_message_id: int = None) -> Tuple[bool, str]:
    """Fetches the REAL top 10 comments from the actual post and sends them as a direct reply message."""
    try:
        comments = ic.fetch_real_top_comments(reel_url, session_id=session_id, limit=10)
        msg_text = ic.format_comments_as_text(comments, reel_url=reel_url)
        
        if not msg_text:
            msg_text = "⚠️ Error: No comments found or comments are disabled for this post."
            
        send_msg_url = get_tg_url(bot_token, "sendMessage")
        payload = {
            "chat_id": chat_id,
            "text": msg_text,
            "parse_mode": "HTML"
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
            
        r = requests.post(send_msg_url, json=payload, timeout=15)
        if r.json().get("ok"):
            return True, "Comments sent!"
    except Exception as e:
        err_text = f"⚠️ Error fetching comments: {str(e)}"
        send_msg_url = get_tg_url(bot_token, "sendMessage")
        payload = {"chat_id": chat_id, "text": err_text}
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        requests.post(send_msg_url, json=payload)
        return False, str(e)
            
    return False, "Failed to send comments."

def send_reel(bot_token: str, chat_id: str, reel: Dict[str, Any], send_mode: str = "video_file", session_id: str = "") -> Tuple[bool, str]:
    """Sends single video, single photo, or carousel album to a Telegram Chat, Channel, or Group with Glass Buttons."""
    if not bot_token or not chat_id:
        return False, "Telegram configuration missing."
    
    reel_id = reel.get("reel_id", "")
    url = reel.get("url", "")
    caption = reel.get("caption", "").strip()
    thumbnail_url = reel.get("thumbnail_url", "")
    video_url = reel.get("video_url", "")
    media_type = reel.get("media_type", "video")
    media_list_json = reel.get("media_list", "[]")
    
    try:
        media_list = json.loads(media_list_json) if isinstance(media_list_json, str) else media_list_json
    except Exception:
        media_list = []
        
    max_cap_len = 800
    if len(caption) > max_cap_len:
        caption = caption[:max_cap_len] + "..."
    
    formatted_caption = html.escape(caption) if caption else ""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/"
    }

    reply_markup = get_glass_buttons_reply_markup(reel_id)

    # Handle Image Post or Thumbnail Photo Fallback
    if media_type == "image" or (not video_url and thumbnail_url):
        photo_target = media_list[0]["url"] if (media_list and media_list[0]["type"] == "image") else thumbnail_url
        if photo_target:
            try:
                r_img = requests.get(photo_target, headers=headers, timeout=20)
                if r_img.status_code == 200 and len(r_img.content) > 1000:
                    send_photo_endpoint = get_tg_url(bot_token, "sendPhoto")
                    payload = {"chat_id": chat_id, "caption": formatted_caption, "parse_mode": "HTML", "reply_markup": reply_markup}
                    files = {"photo": ("image.jpg", r_img.content, "image/jpeg")}
                    r_send = requests.post(send_photo_endpoint, data=payload, files=files, timeout=40)
                    if r_send.json().get("ok"):
                        return True, "Image post sent to Telegram!"
            except Exception as e:
                print(f"Error sending photo to Telegram: {e}")

    # Handle Video Post
    video_bytes = b""
    if video_url:
        try:
            res = requests.get(video_url, headers=headers, timeout=25)
            if res.status_code == 200 and len(res.content) > 10000:
                video_bytes = res.content
        except Exception:
            pass

    if not video_bytes and url:
        try:
            live_vid_url = ig.extract_direct_video_url_with_playwright(url, session_id=session_id)
            if live_vid_url:
                res = requests.get(live_vid_url, headers=headers, timeout=25)
                if res.status_code == 200 and len(res.content) > 10000:
                    video_bytes = res.content
        except Exception:
            pass

    if video_bytes and len(video_bytes) > 5000:
        send_vid_endpoint = get_tg_url(bot_token, "sendVideo")
        payload = {
            "chat_id": chat_id,
            "caption": formatted_caption,
            "parse_mode": "HTML",
            "supports_streaming": True,
            "reply_markup": reply_markup
        }
        files = {
            "video": ("reel.mp4", video_bytes, "video/mp4")
        }
        try:
            r = requests.post(send_vid_endpoint, data=payload, files=files, timeout=90)
            r_data = r.json()
            if r_data.get("ok"):
                return True, "Reel video file uploaded and sent successfully to Telegram!"
        except Exception as e:
            print(f"Error uploading video to Telegram: {e}")

    # Send Photo Thumbnail if video payload fails
    if thumbnail_url:
        try:
            r_img = requests.get(thumbnail_url, headers=headers, timeout=20)
            if r_img.status_code == 200:
                send_photo_endpoint = get_tg_url(bot_token, "sendPhoto")
                payload = {"chat_id": chat_id, "caption": formatted_caption, "parse_mode": "HTML", "reply_markup": reply_markup}
                files = {"photo": ("thumb.jpg", r_img.content, "image/jpeg")}
                r_send = requests.post(send_photo_endpoint, data=payload, files=files, timeout=40)
                if r_send.json().get("ok"):
                    return True, "Post thumbnail sent to Telegram Channel/Group!"
        except Exception:
            pass

    err_text = f"⚠️ Error sending post to Telegram channel/group {chat_id}."
    requests.post(get_tg_url(bot_token, "sendMessage"), json={"chat_id": chat_id, "text": err_text})
    return False, err_text

def process_telegram_commands(bot_token: str):
    """Polls Telegram updates for commands and callback query glass button clicks."""
    if not bot_token:
        return
        
    settings = db.get_settings()
    last_update_id = int(settings.get("telegram_last_update_id", "0"))
    
    url = get_tg_url(bot_token, "getUpdates")
    params = {"offset": last_update_id + 1, "timeout": 5}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return
            
        data = r.json()
        if not data.get("ok"):
            return
            
        updates = data.get("result", [])
        max_id = last_update_id
        
        for u in updates:
            update_id = u.get("update_id", 0)
            if update_id > max_id:
                max_id = update_id
                
            msg = u.get("message") or u.get("edited_message") or u.get("channel_post") or u.get("edited_channel_post")
            cb = u.get("callback_query")
            reaction_obj = u.get("message_reaction") or u.get("reaction")
            
            chat_id = ""
            msg_id = None
            text = ""
            
            # Handle Glass Button Callback Clicks
            if cb:
                cb_id = cb.get("id")
                cb_data = str(cb.get("data", ""))
                cb_msg = cb.get("message", {})
                chat_id = str(cb_msg.get("chat", {}).get("id", ""))
                msg_id = cb_msg.get("message_id")
                
                current_settings = db.get_settings()
                session_id = current_settings.get("instagram_session_id", "")
                
                target_reel_id = ""
                if ":" in cb_data:
                    target_reel_id = cb_data.split(":", 1)[1]
                    
                reel_obj = db.get_reel_by_id(target_reel_id) if target_reel_id else None
                if not reel_obj:
                    sent_reels = db.get_reels(limit=1, status="sent")
                    reel_obj = sent_reels[0] if sent_reels else None
                    
                target_url = reel_obj["url"] if reel_obj else ""
                reel_id = reel_obj.get("reel_id", "") if reel_obj else target_reel_id

                if cb_data.startswith("like") or cb_data == "like_reel":
                    if target_url and reel_id:
                        if db.is_reel_liked(reel_id):
                            ans_text = "❤️ Post already liked"
                        else:
                            ig.like_reel_on_instagram(target_url, session_id=session_id)
                            db.mark_reel_as_liked(reel_id)
                            ans_text = "❤️ Liked"
                        requests.post(get_tg_url(bot_token, "answerCallbackQuery"), json={"callback_query_id": cb_id, "text": ans_text})
                        requests.post(get_tg_url(bot_token, "sendMessage"), json={"chat_id": chat_id, "text": ans_text, "reply_to_message_id": msg_id})
                    continue
                elif cb_data.startswith("comments") or cb_data == "get_comments":
                    if target_url:
                        requests.post(get_tg_url(bot_token, "answerCallbackQuery"), json={"callback_query_id": cb_id, "text": "Fetching comments..."})
                        send_real_comments_text_to_telegram(bot_token, chat_id, target_url, session_id=session_id, reply_to_message_id=msg_id)
                    continue

            if msg:
                text = (msg.get("text") or msg.get("caption") or "").strip().lower()
                chat = msg.get("chat", {})
                chat_id = str(chat.get("id", ""))
                chat_title = chat.get("title") or chat.get("username") or f"Chat {chat_id}"
                chat_type = chat.get("type", "group")
                msg_id = msg.get("message_id")
                db.add_known_chat(chat_id, chat_title, platform="telegram", chat_type=chat_type)
            elif reaction_obj:
                chat = reaction_obj.get("chat", {})
                chat_id = str(chat.get("id", ""))
                msg_id = reaction_obj.get("message_id")
            
            # Check for message reactions (e.g. 🙏 or ❤️ reaction on message)
            if reaction_obj:
                new_reactions = reaction_obj.get("new_reaction", [])
                for r_item in new_reactions:
                    emoji_val = r_item.get("emoji") if isinstance(r_item, dict) else str(r_item)
                    current_settings = db.get_settings()
                    session_id = current_settings.get("instagram_session_id", "")
                    reels = db.get_reels(limit=1, status="sent")
                    target_url = reels[0]["url"] if reels else ""
                    reel_id = reels[0].get("reel_id", "") if reels else ""
                    
                    if emoji_val in ["🙏", "💬", "📝"]:
                        if target_url:
                            db.add_log(f"Telegram 🙏 reaction trigger in chat {chat_id} (msg {msg_id})", level="INFO")
                            send_real_comments_text_to_telegram(bot_token, chat_id, target_url, session_id=session_id, reply_to_message_id=msg_id)
                        else:
                            requests.post(get_tg_url(bot_token, "sendMessage"), json={"chat_id": chat_id, "text": "⚠️ Error: No sent reels found in history to fetch comments for.", "reply_to_message_id": msg_id})
                        break
                    elif emoji_val in ["❤️", "💖", "👍"]:
                        if target_url and reel_id:
                            if db.is_reel_liked(reel_id):
                                requests.post(get_tg_url(bot_token, "sendMessage"), json={"chat_id": chat_id, "text": "❤️ Post already liked", "reply_to_message_id": msg_id})
                            else:
                                ig.like_reel_on_instagram(target_url, session_id=session_id)
                                db.mark_reel_as_liked(reel_id)
                                requests.post(get_tg_url(bot_token, "sendMessage"), json={"chat_id": chat_id, "text": "❤️ Liked", "reply_to_message_id": msg_id})
                        break

            if not text:
                continue
                
            if text in ["/help", "help", "راهنما"]:
                reply_url = get_tg_url(bot_token, "sendMessage")
                help_text = (
                    "📖 <b>Telegram Bot Commands Help</b>\n\n"
                    "• <b>Glass Buttons</b>: Click ❤️ Like or 💬 Top 10 Comments below any post\n"
                    "• <b>/begin</b>: Start auto-forwarding & Instagram searching\n"
                    "• <b>/stop</b>: Fully stop auto-forwarding & Instagram searching\n"
                    "• <b>/send</b>: Force send 1 new Reel immediately\n"
                    "• <b>/skip</b>: Skip rest break and resume active sending\n"
                    "• <b>/comments</b> or 🙏: Reply with real top 10 comments\n"
                    "• <b>/like</b> or ❤️: Like the Reel on Instagram\n"
                    "• <b>/status</b>: View system status & metrics\n"
                    "• <b>/help</b>: Display this help message"
                )
                payload = {"chat_id": chat_id, "text": help_text, "parse_mode": "HTML"}
                if msg_id: payload["reply_to_message_id"] = msg_id
                requests.post(reply_url, json=payload)

            elif text in ["/begin", "/start", "begin", "start"]:
                db.update_settings({"auto_send_enabled": "true"})
                if chat_id:
                    db.update_chat_selection(chat_id, True)
                db.add_log(f"Telegram command /begin received for chat {chat_id}.", level="SUCCESS")
                
                reply_url = get_tg_url(bot_token, "sendMessage")
                reply_text = "✅ <b>Broadcast enabled for this chat!</b>"
                payload = {"chat_id": chat_id, "text": reply_text, "parse_mode": "HTML"}
                if msg_id: payload["reply_to_message_id"] = msg_id
                requests.post(reply_url, json=payload)

            elif text in ["/stop", "/pause", "stop", "pause"]:
                if chat_id:
                    db.update_chat_selection(chat_id, False)
                db.add_log(f"Telegram command /stop received for chat {chat_id} (per-chat stop).", level="WARNING")
                
                reply_url = get_tg_url(bot_token, "sendMessage")
                reply_text = "⏹️ <b>Broadcast stopped for this chat only (other chats remain active).</b>"
                payload = {"chat_id": chat_id, "text": reply_text, "parse_mode": "HTML"}
                if msg_id: payload["reply_to_message_id"] = msg_id
                requests.post(reply_url, json=payload)


            elif text in ["/send", "/force", "send", "force"]:
                current_settings = db.get_settings()
                session_id = current_settings.get("instagram_session_id", "")
                username = current_settings.get("instagram_username", "")
                password = current_settings.get("instagram_password", "")
                send_mode = current_settings.get("send_mode", "video_file")
                
                reels = db.get_reels(limit=1, status="discovered")
                if not reels:
                    db.add_log("Queue empty during /send command. Fetching 16 new reels directly from Instagram...", level="INFO")
                    ig.get_algorithmic_reels(session_id=session_id, username=username, password=password, max_items=16)
                    reels = db.get_reels(limit=1, status="discovered")
                    
                if reels:
                    target_reel = reels[0]
                    success, m = send_reel(bot_token, chat_id, target_reel, send_mode=send_mode, session_id=session_id)
                    if success:
                        db.mark_reel_status(target_reel["reel_id"], "sent")
                        db.add_log(f"Telegram command /send forced video {target_reel['reel_id']} to chat {chat_id}.", level="SUCCESS")
                    else:
                        reply_url = get_tg_url(bot_token, "sendMessage")
                        payload = {"chat_id": chat_id, "text": f"⚠️ Error sending video: {m}"}
                        if msg_id: payload["reply_to_message_id"] = msg_id
                        requests.post(reply_url, json=payload)
                else:
                    reply_url = get_tg_url(bot_token, "sendMessage")
                    payload = {"chat_id": chat_id, "text": "⚠️ Error: Instagram search could not find a new Reel at this time."}
                    if msg_id: payload["reply_to_message_id"] = msg_id
                    requests.post(reply_url, json=payload)

            elif text in ["/skip", "/skiprest", "skip"]:
                import random
                from datetime import datetime, timedelta
                now = datetime.now()
                burst_min = int(db.get_settings().get("burst_min_minutes", "30"))
                burst_max = int(db.get_settings().get("burst_max_minutes", "60"))
                duration = random.randint(burst_min, burst_max)
                new_burst_end = now + timedelta(minutes=duration)
                
                db.update_settings({
                    "auto_send_enabled": "true",
                    "burst_mode_state": "active",
                    "burst_end_time": new_burst_end.isoformat(),
                    "rest_end_time": "",
                    "next_send_time": ""
                })
                db.add_log(f"Telegram command /skip executed.", level="SUCCESS")
                
                reply_url = get_tg_url(bot_token, "sendMessage")
                reply_text = f"⚡ <b>Rest break skipped!</b>"
                payload = {"chat_id": chat_id, "text": reply_text, "parse_mode": "HTML"}
                if msg_id: payload["reply_to_message_id"] = msg_id
                requests.post(reply_url, json=payload)

            elif text in ["/comments", "comments", "💬", "📝", "💭", "🙏"]:
                current_settings = db.get_settings()
                session_id = current_settings.get("instagram_session_id", "")
                reels = db.get_reels(limit=1, status="sent")
                target_url = reels[0]["url"] if reels else ""
                
                if target_url:
                    db.add_log(f"Fetching real top 10 comments text for Telegram chat {chat_id}...", level="INFO")
                    send_real_comments_text_to_telegram(bot_token, chat_id, target_url, session_id=session_id, reply_to_message_id=msg_id)
                else:
                    reply_url = get_tg_url(bot_token, "sendMessage")
                    payload = {"chat_id": chat_id, "text": "⚠️ Error: No sent reels found in history to fetch comments for."}
                    if msg_id: payload["reply_to_message_id"] = msg_id
                    requests.post(reply_url, json=payload)

            elif text in ["/like", "like", "لایک", "❤️", "💖", "👍", "❤️‍🔥"]:
                current_settings = db.get_settings()
                session_id = current_settings.get("instagram_session_id", "")
                reels = db.get_reels(limit=1, status="sent")
                target_url = reels[0]["url"] if reels else ""
                reel_id = reels[0].get("reel_id", "") if reels else ""
                
                if target_url and reel_id:
                    reply_url = get_tg_url(bot_token, "sendMessage")
                    if db.is_reel_liked(reel_id):
                        payload = {"chat_id": chat_id, "text": "❤️ Post already liked"}
                    else:
                        db.add_log(f"Liking Instagram Reel {target_url}...", level="INFO")
                        ig.like_reel_on_instagram(target_url, session_id=session_id)
                        db.mark_reel_as_liked(reel_id)
                        payload = {"chat_id": chat_id, "text": "❤️ Liked"}
                    if msg_id: payload["reply_to_message_id"] = msg_id
                    requests.post(reply_url, json=payload)
                else:
                    reply_url = get_tg_url(bot_token, "sendMessage")
                    payload = {"chat_id": chat_id, "text": "⚠️ Error: No sent reels found to like."}
                    if msg_id: payload["reply_to_message_id"] = msg_id
                    requests.post(reply_url, json=payload)

            elif text in ["/status", "status"]:
                current_settings = db.get_settings()
                is_on = current_settings.get("auto_send_enabled") == "true"
                state = current_settings.get("burst_mode_state", "active")
                
                reels = db.get_reels(limit=500)
                sent_cnt = len([r for r in reels if r["status"] == "sent"])
                
                reply_url = get_tg_url(bot_token, "sendMessage")
                status_emoji = "🟢 ON" if is_on else "🔴 OFF"
                reply_text = f"📊 Status: {status_emoji} | State: {state.upper()} | Sent: {sent_cnt}"
                payload = {"chat_id": chat_id, "text": reply_text}
                if msg_id: payload["reply_to_message_id"] = msg_id
                requests.post(reply_url, json=payload)
                
        if max_id > last_update_id:
            db.update_settings({"telegram_last_update_id": str(max_id)})
    except Exception as e:
        print(f"Error polling Telegram updates: {e}")
