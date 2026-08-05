import sys
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import secrets
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

import database as db
import instagram_fetcher as ig
import bale_bot as bale
import telegram_bot as tg

security = HTTPBasic()

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    settings = db.get_settings()
    auth_enabled = settings.get("dashboard_auth_enabled", "true") == "true"
    if not auth_enabled:
        return "anonymous"
        
    expected_user = settings.get("dashboard_username", "admin")
    expected_pass = settings.get("dashboard_password", "admin123")

    correct_username = secrets.compare_digest(credentials.username, expected_user)
    correct_password = secrets.compare_digest(credentials.password, expected_pass)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

app = FastAPI(
    title="Instagram Algorithmic Reels Multi-Platform Forwarder",
    dependencies=[Depends(verify_auth)]
)


scheduler = BackgroundScheduler()

class SettingsUpdate(BaseModel):
    target_platform: Optional[str] = "bale" # 'bale', 'telegram', or 'both'
    dashboard_auth_enabled: Optional[str] = "true"
    dashboard_username: Optional[str] = "admin"
    dashboard_password: Optional[str] = "admin123"
    bale_bot_token: Optional[str] = ""
    bale_chat_ids: Optional[str] = ""
    telegram_bot_token: Optional[str] = ""
    telegram_chat_ids: Optional[str] = ""
    send_to_all_groups: Optional[str] = "false"
    instagram_username: Optional[str] = ""
    instagram_password: Optional[str] = ""
    instagram_session_id: Optional[str] = ""

    auto_send_enabled: Optional[str] = "false"
    filter_keywords: Optional[str] = ""
    min_likes: Optional[str] = "0"
    send_mode: Optional[str] = "video_file"
    send_delay_min_seconds: Optional[str] = "45"
    sleep_schedule_enabled: Optional[str] = "true"
    sleep_start_hour: Optional[str] = "3"
    sleep_end_hour: Optional[str] = "10"
    burst_min_minutes: Optional[str] = "30"
    burst_max_minutes: Optional[str] = "60"
    rest_min_minutes: Optional[str] = "60"
    rest_max_minutes: Optional[str] = "120"


def fetch_and_store_reels(limit: int = 16) -> int:
    """Fetches new Reels from Instagram (default: 16 reels per batch)."""
    settings = db.get_settings()
    if settings.get("auto_send_enabled", "false") != "true":
        return 0
        
    session_id = settings.get("instagram_session_id", "")
    username = settings.get("instagram_username", "")
    password = settings.get("instagram_password", "")
    filter_keywords = [k.strip().lower() for k in settings.get("filter_keywords", "").split(",") if k.strip()]
    
    db.add_log(f"Searching Instagram for {limit} new Reels...", level="INFO")

    try:
        reels = ig.get_algorithmic_reels(session_id=session_id, username=username, password=password, max_items=limit)
        if not reels:
            db.add_log("No new reels retrieved during search.", level="WARNING")
            return 0
            
        added = 0
        for r in reels:
            if filter_keywords:
                caption = r.get("caption", "").lower()
                if not any(kw in caption for kw in filter_keywords):
                    continue
            if db.add_reel(r):
                added += 1
                if added >= limit:
                    break
        db.add_log(f"Queued {added} new Reels in database.", level="SUCCESS")
        return added
    except Exception as e:
        db.add_log(f"Error fetching reels: {str(e)}", level="ERROR")
        return 0

def get_active_target_chats(platform_name: str) -> List[str]:
    """Resolves active target chats for bale or telegram, strictly respecting per-chat /stop (selected = 0)."""
    settings = db.get_settings()
    send_to_all = settings.get("send_to_all_groups", "false") == "true"
    
    known = db.get_known_chats(platform=platform_name)
    stopped_ids = {str(c["chat_id"]) for c in known if c.get("selected") == 0}
    
    if send_to_all:
        targets = [str(c["chat_id"]) for c in known if c.get("selected") == 1]
    else:
        cfg_key = f"{platform_name}_chat_ids"
        configured = [c.strip() for c in settings.get(cfg_key, "").split(",") if c.strip()]
        targets = [cid for cid in configured if cid not in stopped_ids]
        if not targets:
            targets = [str(c["chat_id"]) for c in known if c.get("selected") == 1]
        
    final_targets = [cid for cid in targets if cid not in stopped_ids]
    return list(dict.fromkeys(final_targets))

def process_command_polling():
    """Polls /begin, /stop, /status commands from both Bale and Telegram."""
    settings = db.get_settings()
    bale_token = settings.get("bale_bot_token", "")
    tg_token = settings.get("telegram_bot_token", "")
    
    if bale_token:
        bale.process_bale_commands(bale_token)
    if tg_token:
        tg.process_telegram_commands(tg_token)

def process_scheduler_tick():
    """Checked every 15s. Completely halts searching when auto_send_enabled is false."""
    settings = db.get_settings()
    auto_send = settings.get("auto_send_enabled", "false") == "true"
    
    # CRITICAL REQUIREMENT: When /stop is active, do NOT search or fetch videos at all!
    if not auto_send:
        return

    bale_token = settings.get("bale_bot_token", "")
    tg_token = settings.get("telegram_bot_token", "")
    platform = settings.get("target_platform", "bale")
    send_mode = settings.get("send_mode", "video_file")
    
    now = datetime.now()
    
    # Morning Sleep Schedule check (03:00 AM - 10:00 AM) to mimic natural human behavior
    sleep_enabled = settings.get("sleep_schedule_enabled", "true") == "true"
    sleep_start = int(settings.get("sleep_start_hour", "3"))
    sleep_end = int(settings.get("sleep_end_hour", "10"))
    
    current_hour = now.hour
    is_sleeping = False
    if sleep_enabled:
        if sleep_start < sleep_end:
            is_sleeping = (sleep_start <= current_hour < sleep_end)
        else:
            is_sleeping = (current_hour >= sleep_start or current_hour < sleep_end)

    if is_sleeping:
        return

    
    state = settings.get("burst_mode_state", "active")
    burst_end_str = settings.get("burst_end_time", "")
    rest_end_str = settings.get("rest_end_time", "")
    next_send_str = settings.get("next_send_time", "")
    
    send_delay_min = int(settings.get("send_delay_min_seconds", "45"))
    send_delay_max = int(settings.get("send_delay_max_seconds", "75"))
    burst_min = int(settings.get("burst_min_minutes", "30"))
    burst_max = int(settings.get("burst_max_minutes", "60"))
    rest_min = int(settings.get("rest_min_minutes", "60"))
    rest_max = int(settings.get("rest_max_minutes", "120"))
    
    burst_end = datetime.fromisoformat(burst_end_str) if burst_end_str else None
    rest_end = datetime.fromisoformat(rest_end_str) if rest_end_str else None
    next_send = datetime.fromisoformat(next_send_str) if next_send_str else None
    
    # State Machine Evaluation
    if not burst_end and not rest_end:
        burst_duration = random.randint(burst_min, burst_max)
        burst_end = now + timedelta(minutes=burst_duration)
        state = "active"
        db.update_settings({
            "burst_mode_state": "active",
            "burst_end_time": burst_end.isoformat(),
            "rest_end_time": ""
        })
        db.add_log(f"Initialized Burst Mode state. Active Burst for {burst_duration} mins.", level="INFO")

    if state == "active":
        if burst_end and now >= burst_end:
            rest_duration = random.randint(rest_min, rest_max)
            new_rest_end = now + timedelta(minutes=rest_duration)
            db.update_settings({
                "burst_mode_state": "resting",
                "rest_end_time": new_rest_end.isoformat(),
                "next_send_time": ""
            })
            db.add_log(f"☕ Active Burst complete! Entering Rest Break for {rest_duration} mins.", level="INFO")
            return
        elif now >= burst_end:
             # Fallback if state logic somehow gets desynced
             pass
    elif state == "resting":
        if rest_end and now >= rest_end:
            burst_duration = random.randint(burst_min, burst_max)
            new_burst_end = now + timedelta(minutes=burst_duration)
            db.update_settings({
                "burst_mode_state": "active",
                "burst_end_time": new_burst_end.isoformat(),
                "next_send_time": ""
            })
            db.add_log(f"🚀 Rest Break finished! Starting new Active Burst for {burst_duration} mins.", level="SUCCESS")
            state = "active"
            burst_end = new_burst_end
            next_send = None
        else:
            return

    # Active Burst Mode: Send 1 video file per randomized delay
    if state == "active":
        if next_send and now < next_send:
            return

        reels = db.get_reels(limit=1, status="discovered")
        if not reels:
            fetch_and_store_reels()
            reels = db.get_reels(limit=1, status="discovered")
            
        if not reels:
            db.add_log("Queue is empty. Waiting for next search...", level="WARNING")
            return
            
        target_reel = reels[0]
        session_id = settings.get("instagram_session_id", "")
        
        # Determine target chats across platforms
        targets_bale = []
        targets_tg = []
        
        if platform in ["bale", "both"] and bale_token:
            targets_bale = get_active_target_chats("bale")

        if platform in ["telegram", "both"] and tg_token:
            targets_tg = get_active_target_chats("telegram")
                
        sent_any = False
        
        # Dispatch to Bale targets
        for cid in targets_bale:
            success, msg = bale.send_reel(bale_token, cid, target_reel, send_mode=send_mode, session_id=session_id)
            if success:
                sent_any = True
                db.add_log(f"✅ Video file {target_reel['reel_id']} delivered to Bale group/chat ({cid})", level="SUCCESS")
            else:
                db.add_log(f"❌ Failed to deliver to Bale ({cid}): {msg}", level="ERROR")
                
        # Dispatch to Telegram targets
        for cid in targets_tg:
            success, msg = tg.send_reel(tg_token, cid, target_reel, send_mode=send_mode, session_id=session_id)
            if success:
                sent_any = True
                db.add_log(f"✅ Video file {target_reel['reel_id']} delivered to Telegram ({cid})", level="SUCCESS")
            else:
                db.add_log(f"❌ Failed to deliver to Telegram ({cid}): {msg}", level="ERROR")
                
        delay_seconds = random.randint(send_delay_min, send_delay_max)
        new_next_send = now + timedelta(seconds=delay_seconds)
        db.update_settings({"next_send_time": new_next_send.isoformat()})

        if sent_any:
            db.mark_reel_status(target_reel["reel_id"], "sent")
            rem_mins = int((burst_end - now).total_seconds() // 60) if burst_end else 0
            db.add_log(f"Broadcast complete for Reel {target_reel['reel_id']}. Next video in {delay_seconds}s (Burst ends in {rem_mins}m)", level="SUCCESS")

def setup_scheduler():
    scheduler.remove_all_jobs()
    scheduler.add_job(process_scheduler_tick, 'interval', seconds=15, id="ig_tick_job")
    scheduler.add_job(process_command_polling, 'interval', seconds=5, id="command_poll_job")
    db.add_log("Scheduler active: Polling Bale/Telegram commands (/begin, /stop) & processing broadcasts.", level="INFO")

@app.on_event("startup")
def startup_event():
    db.init_db()
    db.add_log("Application starting up...", level="INFO")
    scheduler.start()
    setup_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

# API Endpoints
@app.get("/api/status")
def get_status():
    settings = db.get_settings()
    reels = db.get_reels(limit=500)
    sent_reels = [r for r in reels if r["status"] == "sent"]
    discovered_reels = [r for r in reels if r["status"] == "discovered"]
    
    now = datetime.now()
    state = settings.get("burst_mode_state", "active")
    burst_end_str = settings.get("burst_end_time", "")
    rest_end_str = settings.get("rest_end_time", "")
    next_send_str = settings.get("next_send_time", "")
    auto_send = settings.get("auto_send_enabled") == "true"
    
    time_info = "Active Burst"
    
    sleep_enabled = settings.get("sleep_schedule_enabled", "true") == "true"
    sleep_start = int(settings.get("sleep_start_hour", "3"))
    sleep_end = int(settings.get("sleep_end_hour", "10"))
    current_hour = now.hour
    
    is_sleeping = False
    if sleep_enabled:
        if sleep_start < sleep_end:
            is_sleeping = (sleep_start <= current_hour < sleep_end)
        else:
            is_sleeping = (current_hour >= sleep_start or current_hour < sleep_end)
            
    if is_sleeping:
        time_info = f"😴 Night Sleep Schedule ({sleep_start:02d}:00 AM - {sleep_end:02d}:00 AM)"
    elif not auto_send:
        time_info = "🔴 STOPPED (Search & Delivery Disabled)"
    elif state == "resting" and rest_end_str:
        try:
            r_end = datetime.fromisoformat(rest_end_str)
            rem = max(0, int((r_end - now).total_seconds() // 60))
            time_info = f"Resting ({rem} mins left)"
        except Exception:
            time_info = "Resting"
    elif state == "active" and burst_end_str:
        try:
            b_end = datetime.fromisoformat(burst_end_str)
            rem = max(0, int((b_end - now).total_seconds() // 60))
            next_delay_info = ""
            if next_send_str:
                n_send = datetime.fromisoformat(next_send_str)
                n_rem = max(0, int((n_send - now).total_seconds()))
                next_delay_info = f" (Next in {n_rem}s)"
            time_info = f"Active Burst ({rem}m left){next_delay_info}"
        except Exception:
            time_info = "Active Burst"

            
    return {
        "status": "online",
        "burst_mode_state": state,
        "schedule_status": time_info,
        "auto_send_enabled": auto_send,
        "target_platform": settings.get("target_platform", "bale"),
        "total_sent": len(sent_reels),
        "total_discovered": len(discovered_reels),
        "bale_configured": bool(settings.get("bale_bot_token")),
        "telegram_configured": bool(settings.get("telegram_bot_token")),
        "instagram_configured": bool(settings.get("instagram_session_id") or settings.get("instagram_username"))
    }

@app.get("/api/settings")
def read_settings():
    return db.get_settings()

@app.post("/api/settings")
def write_settings(payload: SettingsUpdate):
    data = payload.dict(exclude_unset=True)
    db.update_settings(data)
    setup_scheduler()
    db.add_log("Settings updated.", level="SUCCESS")
    return {"status": "success", "message": "Settings saved."}

@app.get("/api/chats")
def list_chats(platform: Optional[str] = None):
    return db.get_known_chats(platform=platform)

@app.post("/api/chats/{chat_id}/toggle")
def toggle_chat(chat_id: str, selected: bool):
    db.update_chat_selection(chat_id, selected)
    return {"status": "success", "message": "Chat selection updated."}

@app.post("/api/reels/clear")
def clear_reels_history_api():
    db.clear_reels_history()
    db.add_log("Wiped all past Reels history stream.", level="WARNING")
    return {"status": "success", "message": "Past reels stream cleared."}

@app.post("/api/schedule/skip-rest")

def skip_rest_break():
    now = datetime.now()
    settings = db.get_settings()
    burst_min = int(settings.get("burst_min_minutes", "30"))
    burst_max = int(settings.get("burst_max_minutes", "60"))
    duration = random.randint(burst_min, burst_max)
    new_burst_end = now + timedelta(minutes=duration)
    
    db.update_settings({
        "auto_send_enabled": "true",
        "burst_mode_state": "active",
        "burst_end_time": new_burst_end.isoformat(),
        "rest_end_time": "",
        "next_send_time": ""
    })
    setup_scheduler()
    db.add_log(f"Rest break skipped from Web UI! Active Burst mode started for {duration} mins.", level="SUCCESS")
    return {"status": "success", "message": f"Rest break skipped. Active Burst started for {duration} mins."}

@app.post("/api/sync")
def sync_now():
    added = fetch_and_store_reels(limit=16)
    return {"status": "success", "message": f"Synced {added} new reels from Instagram."}




@app.get("/api/reels")
def list_reels(limit: int = 50, status: Optional[str] = None):
    return db.get_reels(limit=limit, status=status)

from fastapi.responses import FileResponse, JSONResponse

@app.post("/api/reels/{reel_id}/send")
def send_reel_now(reel_id: str):
    settings = db.get_settings()
    platform = settings.get("target_platform", "bale")
    bale_token = settings.get("bale_bot_token", "")
    tg_token = settings.get("telegram_bot_token", "")
    session_id = settings.get("instagram_session_id", "")
    send_mode = settings.get("send_mode", "video_file")
    send_to_all = settings.get("send_to_all_groups", "false") == "true"
    
    reels = db.get_reels(limit=500)
    target = next((r for r in reels if r["reel_id"] == reel_id), None)
    if not target:
        return JSONResponse(status_code=404, content={"status": "error", "detail": "Reel not found."})
        
    sent = False
    last_err = "No target chat configured."
    
    targets_bale = []
    targets_tg = []
    
    if platform in ["bale", "both"] and bale_token:
        targets_bale = get_active_target_chats("bale")

    if platform in ["telegram", "both"] and tg_token:
        targets_tg = get_active_target_chats("telegram")


    for cid in targets_bale:
        s, m = bale.send_reel(bale_token, cid, target, send_mode=send_mode, session_id=session_id)
        if s: sent = True; last_err = m
        else: last_err = m

    for cid in targets_tg:
        s, m = tg.send_reel(tg_token, cid, target, send_mode=send_mode, session_id=session_id)
        if s: sent = True; last_err = m
        else: last_err = m

    if sent:
        db.mark_reel_status(reel_id, "sent")
        db.add_log(f"Manually sent video file {reel_id}.", level="SUCCESS")
        return {"status": "success", "message": "Video delivered successfully!"}
    else:
        return JSONResponse(status_code=400, content={"status": "error", "detail": f"Failed to send: {last_err}"})


@app.post("/api/bale/test")
def test_bale():
    settings = db.get_settings()
    bot_token = settings.get("bale_bot_token", "")
    chat_id = settings.get("bale_chat_ids", "").split(",")[0].strip()
    
    success, msg = bale.test_bale_connection(bot_token, chat_id)
    if success:
        db.add_log(f"Bale Connection Test Succeeded: {msg}", level="SUCCESS")
        return {"status": "success", "message": msg}
    else:
        db.add_log(f"Bale Connection Test Failed: {msg}", level="ERROR")
        raise HTTPException(status_code=400, detail=msg)

@app.post("/api/telegram/test")
def test_telegram():
    settings = db.get_settings()
    bot_token = settings.get("telegram_bot_token", "")
    chat_id = settings.get("telegram_chat_ids", "").split(",")[0].strip()
    
    success, msg = tg.test_telegram_connection(bot_token, chat_id)
    if success:
        db.add_log(f"Telegram Connection Test Succeeded: {msg}", level="SUCCESS")
        return {"status": "success", "message": msg}
    else:
        db.add_log(f"Telegram Connection Test Failed: {msg}", level="ERROR")
        raise HTTPException(status_code=400, detail=msg)

@app.get("/api/logs")
def get_logs(limit: int = 100):
    return db.get_logs(limit=limit)

# Static Files & Dashboard UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome to Instagram Reels Forwarder API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
