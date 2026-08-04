# 🎬 Instagram Algorithmic Reels → Telegram & Bale Forwarder

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-red.svg)](https://playwright.dev/)
[![Platforms](https://img.shields.io/badge/Platforms-Telegram%20%7C%20Bale-2CA5E0.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)

An enterprise-grade, multi-platform autonomous content engine that curates, extracts, and delivers **Instagram Algorithmic Reels, Carousel Media, and Photos** directly into **Telegram Channels/Groups** and **Bale Messenger**. 

Featuring a modern **FastAPI Web Dashboard**, **Per-Chat Operational Control**, **Interactive Glass Inline Keyboards**, and a **Human-like Circadian Sleep Schedule**, this application is designed for seamless, automated community management.

---

## 🌟 Key Features

### 📡 Multi-Platform Broadcasting Engine
- **Simultaneous Delivery**: Broadcasts high-definition Reels and Carousel albums to **Bale Messenger** and **Telegram** channels and groups simultaneously.
- **Glass Inline Keyboards**: Every delivered post features dynamic, interactive glass buttons directly attached beneath the media:
  - **`[ ❤️ Like ]` / `[ ❤️ لایک ]`**: Likes the post directly on Instagram and prevents duplicate API likes via SQLite database tracking.
  - **`[ 💬 Top 10 Comments ]` / `[ 💬 ۱۰ کامنت برتر ]`**: Fetches real-time top comments from Instagram and posts them as a formatted text reply.
- **Media Support**: Robustly handles single videos, high-resolution photo posts, and swipable multi-media carousel albums (`carousel_media`).

### 🛡️ 3-Tier Multi-Fallback Fetching Engine
- **Tier 1 (Direct Web API)**: Authenticates requests using Session ID and CSRF tokens across active Instagram Web endpoints.
- **Tier 2 (VPS-Optimized Playwright Browser)**: Headless Chromium browser automation with stealth flags (`--no-sandbox`, `--disable-dev-shm-usage`) to bypass datacenter IP rate limits.
- **Tier 3 (Public Backup Stream)**: Fallback discovery mechanism ensuring the delivery queue **never runs empty**.

### 🌙 Human-like Sleep Schedule & Humanization
- **Circadian Sleep Window (03:00 AM – 10:00 AM)**: Automatically pauses content scraping and broadcasting during early morning hours to mimic natural human activity and protect account longevity.
- **Burst & Rest Mode**: Operates in randomized active delivery bursts followed by natural rest breaks.

### 🎛️ Per-Chat Control & Command Routing
- **Independent Chat Scope**: Typing `/stop` in a specific group or channel pauses delivery **only for that specific chat**, keeping all other Telegram and Bale channels actively broadcasting.
- **Full Bot Commands**: Control the system directly from Telegram or Bale using `/begin`, `/stop`, `/send`, `/skip`, `/comments`, `/like`, `/status`, and `/help`.

### 🔒 Modern Web Dashboard UI
- **Real-Time Control Panel**: A glassmorphism Web UI to monitor system status, view active queues, toggle broadcast targets, and manage logs.
- **HTTP Basic Authentication**: Secured access requiring username (`shahab`) and password (`5584`).

---

## 🏗️ Architecture Overview

```
                     +---------------------------------------+
                     |    Instagram Web / GraphQL API        |
                     +-------------------+-------------------+
                                         |
                                         v
                     +-------------------+-------------------+
                     |   3-Tier Multi-Fallback Fetcher       |
                     |   (Direct API / Playwright / Backup)   |
                     +-------------------+-------------------+
                                         |
                                         v
                     +-------------------+-------------------+
                     |      SQLite Database (app.db)         |
                     |  (Reels Stream / Likes / Known Chats)  |
                     +-------------------+-------------------+
                                         |
           +-----------------------------+-----------------------------+
           |                                                           |
           v                                                           v
+----------+----------+                                     +----------+----------+
|   Bale Bot Handler  |                                     | Telegram Bot Handler|
| (Glass Buttons / UI)|                                     | (Glass Buttons / UI)|
+----------+----------+                                     +----------+----------+
           |                                                           |
           v                                                           v
+----------+----------+                                     +----------+----------+
|  Bale Groups/Channels|                                    | Telegram Groups/Chats|
+---------------------+                                     +---------------------+
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- Python 3.9+
- Node.js & Playwright Chromium (for VPS headlessness)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Bale Bot Token ([@BotFather on Bale](https://bale.ai))

### 2. Clone & Setup Repository
```bash
git clone https://github.com/Bekend/instagram-reels-to-telegram-and-bale.git
cd instagram-reels-to-telegram-and-bale

# Install Python Dependencies
pip install -r requirements.txt

# Install Playwright Headless Chromium Browsers
playwright install chromium
playwright install-deps
```

### 3. Run Locally or on VPS
```bash
python main.py
```
The FastAPI web server will start at **`http://localhost:8000`**.

---

## 🔐 Web Dashboard & Authentication

Access the web dashboard at `http://localhost:8000` (or `http://YOUR_VPS_IP/`):

- **Default Username**: `admin`
- **Default Password**: `admin123` *(Configurable in Dashboard Settings)*


From the Dashboard, you can:
- View live delivery counts and system status.
- Trigger immediate Reel synchronization.
- Enable or disable target groups and channels.
- Configure Instagram session credentials and auto-sending parameters.

---

## 🤖 Bot Commands Reference

Commands can be typed directly into any Telegram or Bale group or channel:

| Command (English) | Command (Persian) | Description |
| :--- | :--- | :--- |
| `/begin` / `/start` | `شروع` | Enables automatic broadcasting for **this specific chat**. |
| `/stop` / `/pause` | `توقف` | Stops automatic broadcasting for **this specific chat only**. |
| `/send` / `/force` | `ارسال` | Immediately fetches and sends 1 new Reel to the chat. |
| `/skip` | `عبور` | Skips an active rest break and resumes active burst sending. |
| `/comments` | `کامنت` | Fetches and replies with the **Real Top 10 Instagram Comments**. |
| `/like` | `لایک` | Likes the Reel directly on Instagram. |
| `/status` | `وضعیت` | Displays active status, state machine metrics, and sent counts. |
| `/help` | `راهنما` | Displays the command guide. |

---

## 👨‍💻 Authors & Acknowledgments

- **Product Concept & Requirements Lead**: **Shahab** ([@Bekend](https://github.com/Bekend)) — Defined system architecture, functional requirements, and multi-platform specifications.
- **Lead AI Software Engineer**: **Google DeepMind Antigravity AI** — Architected, implemented, and verified the complete Python/FastAPI codebase, Playwright fallback engine, and database persistence layers.

---

## 📜 License

This project is open-source software licensed under the [MIT License](LICENSE).
