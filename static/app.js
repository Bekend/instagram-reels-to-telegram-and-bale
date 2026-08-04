document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadStatus();
    loadDashboardData();
    loadSettings();

    // Event listeners
    document.getElementById('btn-quick-sync').addEventListener('click', triggerSync);
    
    const btnSkipRest = document.getElementById('btn-skip-rest');
    if (btnSkipRest) btnSkipRest.addEventListener('click', skipRestBreak);

    document.getElementById('settings-form').addEventListener('submit', saveSettings);

    const btnTestBale = document.getElementById('btn-test-bale');
    if (btnTestBale) btnTestBale.addEventListener('click', testBale);

    const btnTestTg = document.getElementById('btn-test-telegram');
    if (btnTestTg) btnTestTg.addEventListener('click', testTelegram);

    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);

    // Auto refresh status and logs every 15 seconds
    setInterval(() => {
        loadStatus();
        loadLogs();
    }, 15000);
});

async function safeFetchJson(url, options = {}) {
    try {
        const res = await fetch(url, options);
        if (res.status === 401) {
            console.warn('Unauthorized: Enter basic auth credentials (shahab / 5584)');
            return null;
        }
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await res.json();
            return { ok: res.ok, status: res.status, data };
        } else {
            const text = await res.text();
            return { ok: res.ok, status: res.status, text };
        }
    } catch (err) {
        console.error('Fetch error for ' + url, err);
        return null;
    }
}

/* Navigation Logic */
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-item');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchToTab(tabName);
        });
    });

    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filter = btn.getAttribute('data-filter');
            loadReels(filter === 'all' ? null : filter);
        });
    });
}

function switchToTab(tabName) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

    const targetNav = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    const targetTab = document.getElementById(`tab-${tabName}`);

    if (targetNav && targetTab) {
        targetNav.classList.add('active');
        targetTab.classList.add('active');

        const titles = {
            dashboard: ["Dashboard Overview", "Monitor and control your Instagram algorithm feed forwarder"],
            reels: ["Reels Stream", "Browse algorithm-recommended Reels and manage delivery"],
            groups: ["Group Manager", "Manage joined Bale and Telegram groups for multi-chat broadcasting"],
            settings: ["Settings & Auth", "Configure Bale & Telegram Bots, Platform & Instagram Auth"],
            logs: ["Activity Logs", "Real-time system events and transaction logs"]
        };
        if (titles[tabName]) {
            document.getElementById('tab-title').textContent = titles[tabName][0];
            document.getElementById('tab-subtitle').textContent = titles[tabName][1];
        }

        if (tabName === 'reels') loadReels();
        if (tabName === 'groups') loadGroups();
        if (tabName === 'logs') loadLogs();
    }
}

/* API Calls & UI Handlers */
async function loadStatus() {
    const res = await safeFetchJson('/api/status');
    if (!res || !res.ok || !res.data) return;
    const data = res.data;

    document.getElementById('metric-sent').textContent = data.total_sent;
    document.getElementById('metric-discovered').textContent = data.total_discovered;
    document.getElementById('metric-autoforward').textContent = data.auto_send_enabled ? (data.burst_mode_state === 'active' ? 'Active Burst' : 'Rest Break') : '🔴 STOPPED';
    document.getElementById('metric-autoforward').style.color = data.auto_send_enabled ? (data.burst_mode_state === 'active' ? 'var(--accent-green)' : 'var(--accent-orange)') : 'var(--accent-pink)';
    document.getElementById('metric-interval').textContent = data.schedule_status || '45-75s delay';
    document.getElementById('metric-connection').textContent = (data.target_platform || 'bale').toUpperCase();
    document.getElementById('status-text').textContent = data.auto_send_enabled ? 'Auto-Forwarding Active' : 'System Stopped';
}

async function loadDashboardData() {
    loadStatus();
    loadLogs();
    
    const res = await safeFetchJson('/api/reels?limit=4');
    const reels = res && res.data ? res.data : [];
    const container = document.getElementById('dashboard-reels-list');
    
    if (!reels || reels.length === 0) {
        container.innerHTML = '<p class="empty-text">No reels fetched yet.</p>';
        return;
    }

    container.innerHTML = reels.map(r => `
        <div class="glass-card" style="padding: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <strong style="color: var(--accent-pink);">${escapeHtml(r.author)}</strong>
                <p style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(r.caption.substring(0, 60))}...</p>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="sendReelNow('${r.reel_id}')">Forward</button>
        </div>
    `).join('');
}

async function loadGroups() {
    const container = document.getElementById('groups-list-container');
    container.innerHTML = '<p class="empty-text">Loading groups & channels...</p>';
    
    const res = await safeFetchJson('/api/chats');
    const chats = res && res.data ? res.data : [];
    
    if (!chats || chats.length === 0) {
        container.innerHTML = '<p class="empty-text">No groups or channels detected yet. Add your bot to a group or channel on Bale / Telegram and post a message to detect it!</p>';
        return;
    }

    container.innerHTML = chats.map(c => {
        const badgeColor = c.chat_type === 'channel' ? 'background:rgba(0,149,246,0.2); color:#0095f6;' : 'background:rgba(255,255,255,0.1); color:var(--text-muted);';
        return `
        <div class="glass-card" style="padding: 14px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="padding: 4px 8px; border-radius: 4px; ${badgeColor} font-size: 0.75rem; font-weight: 700; text-transform: UPPERCASE;">${c.platform} • ${c.chat_type || 'group'}</span>
                <div>
                    <strong>${escapeHtml(c.title)}</strong>
                    <div style="font-size: 0.75rem; color: var(--text-dim);">ID: ${c.chat_id}</div>
                </div>
            </div>
            <label class="switch">
                <input type="checkbox" ${c.selected ? 'checked' : ''} onchange="toggleGroupSelection('${c.chat_id}', this.checked)">
                <span class="slider round"></span>
            </label>
        </div>
        `;
    }).join('');
}

async function toggleGroupSelection(chatId, isSelected) {
    const res = await safeFetchJson(`/api/chats/${chatId}/toggle?selected=${isSelected}`, { method: 'POST' });
    if (res && res.ok) {
        showToast(isSelected ? 'Group enabled for broadcast' : 'Group disabled');
    } else {
        showToast('Failed to update group selection');
    }
}

async function loadReels(statusFilter = null) {
    const grid = document.getElementById('reels-grid');
    grid.innerHTML = '<p class="empty-text">Loading Reels...</p>';

    let url = '/api/reels?limit=50';
    if (statusFilter) url += `&status=${statusFilter}`;
    
    const res = await safeFetchJson(url);
    const reels = res && res.data ? res.data : [];

    if (!reels || reels.length === 0) {
        grid.innerHTML = '<p class="empty-text">No Reels found matching this filter.</p>';
        return;
    }

    grid.innerHTML = reels.map(r => `
        <div class="reel-card">
            <div class="reel-thumb-wrapper">
                <img class="reel-thumb" src="${r.thumbnail_url || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60'}" alt="Reel thumbnail" onerror="this.src='https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&auto=format&fit=crop&q=60'">
                <span class="reel-badge badge-${r.status}">${r.status}</span>
            </div>
            <div class="reel-body">
                <div class="reel-author">${escapeHtml(r.author)}</div>
                <div class="reel-caption">${escapeHtml(r.caption || 'No caption available')}</div>
                <div class="reel-actions">
                    <a href="${r.url}" target="_blank" class="btn btn-secondary btn-sm flex-1" style="text-decoration:none; justify-content:center;">View IG</a>
                    ${r.status !== 'sent' ? `<button class="btn btn-primary btn-sm flex-1" onclick="sendReelNow('${r.reel_id}')">Send Now</button>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function skipRestBreak() {
    showToast('Skipping rest break...');
    const res = await safeFetchJson('/api/schedule/skip-rest', { method: 'POST' });
    if (res && res.ok && res.data) {
        showToast(res.data.message);
        loadStatus();
    } else {
        showToast('Failed to skip rest break');
    }
}

async function triggerSync() {
    showToast('Finding new Instagram Reels...');
    const res = await safeFetchJson('/api/sync', { method: 'POST' });
    if (res && res.ok && res.data) {
        showToast(res.data.message);
        setTimeout(() => {
            loadDashboardData();
            loadStatus();
        }, 3000);
    } else {
        showToast('Sync request failed');
    }
}

async function sendReelNow(reelId) {
    showToast(`Delivering Reel ${reelId}...`);
    const res = await safeFetchJson(`/api/reels/${reelId}/send`, { method: 'POST' });
    if (res && res.ok) {
        showToast('✅ Video file delivered successfully!');
        loadReels();
        loadStatus();
    } else {
        const msg = res && res.data ? (res.data.detail || res.data.message) : 'Failed to send';
        showToast('❌ ' + msg);
    }
}

async function loadSettings() {
    const res = await safeFetchJson('/api/settings');
    if (!res || !res.ok || !res.data) return;
    const data = res.data;

    for (const [key, value] of Object.entries(data)) {
        const el = document.getElementById(key);
        if (el) {
            if (el.type === 'checkbox') {
                el.checked = value === 'true';
            } else {
                el.value = value;
            }
        }
    }
}

async function saveSettings(e) {
    if (e && e.preventDefault) e.preventDefault();
    const payload = {
        target_platform: document.getElementById('target_platform') ? document.getElementById('target_platform').value : "bale",
        bale_bot_token: document.getElementById('bale_bot_token') ? document.getElementById('bale_bot_token').value : "",
        bale_chat_ids: document.getElementById('bale_chat_ids') ? document.getElementById('bale_chat_ids').value : "",
        telegram_bot_token: document.getElementById('telegram_bot_token') ? document.getElementById('telegram_bot_token').value : "",
        telegram_chat_ids: document.getElementById('telegram_chat_ids') ? document.getElementById('telegram_chat_ids').value : "",
        send_to_all_groups: document.getElementById('send_to_all_groups') && document.getElementById('send_to_all_groups').checked ? 'true' : 'false',
        instagram_session_id: document.getElementById('instagram_session_id') ? document.getElementById('instagram_session_id').value : "",
        instagram_username: document.getElementById('instagram_username') ? document.getElementById('instagram_username').value : "",
        instagram_password: document.getElementById('instagram_password') ? document.getElementById('instagram_password').value : "",
        auto_send_enabled: document.getElementById('auto_send_enabled') && document.getElementById('auto_send_enabled').checked ? 'true' : 'false',
        send_mode: "video_file",
        send_delay_min_seconds: document.getElementById('send_delay_min_seconds') ? document.getElementById('send_delay_min_seconds').value : "45",
        send_delay_max_seconds: document.getElementById('send_delay_max_seconds') ? document.getElementById('send_delay_max_seconds').value : "75",
        burst_min_minutes: document.getElementById('burst_min_minutes') ? document.getElementById('burst_min_minutes').value : "30",
        burst_max_minutes: document.getElementById('burst_max_minutes') ? document.getElementById('burst_max_minutes').value : "60",
        rest_min_minutes: document.getElementById('rest_min_minutes') ? document.getElementById('rest_min_minutes').value : "60",
        rest_max_minutes: document.getElementById('rest_max_minutes') ? document.getElementById('rest_max_minutes').value : "120",
        filter_keywords: document.getElementById('filter_keywords') ? document.getElementById('filter_keywords').value : ""
    };

    const res = await safeFetchJson('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (res && res.ok) {
        showToast('Settings saved successfully!');
        loadStatus();
    } else {
        showToast('Failed to save settings');
    }
}

async function testBale() {
    const resEl = document.getElementById('bale-test-result');
    if (resEl) {
        resEl.textContent = 'Testing connection...';
        resEl.style.color = 'var(--text-muted)';
    }

    await saveSettings();

    const res = await safeFetchJson('/api/bale/test', { method: 'POST' });
    if (res && res.ok && res.data) {
        if (resEl) {
            resEl.textContent = '✅ ' + res.data.message;
            resEl.style.color = 'var(--accent-green)';
        }
        showToast('✅ Test message sent to Bale Group!');
    } else {
        const msg = res && res.data ? (res.data.detail || res.data.message) : 'Test failed';
        if (resEl) {
            resEl.textContent = '❌ ' + msg;
            resEl.style.color = 'var(--accent-pink)';
        }
    }
}

async function testTelegram() {
    const resEl = document.getElementById('telegram-test-result');
    if (resEl) {
        resEl.textContent = 'Testing connection...';
        resEl.style.color = 'var(--text-muted)';
    }

    await saveSettings();

    const res = await safeFetchJson('/api/telegram/test', { method: 'POST' });
    if (res && res.ok && res.data) {
        if (resEl) {
            resEl.textContent = '✅ ' + res.data.message;
            resEl.style.color = 'var(--accent-green)';
        }
        showToast('✅ Test message sent to Telegram!');
    } else {
        const msg = res && res.data ? (res.data.detail || res.data.message) : 'Test failed';
        if (resEl) {
            resEl.textContent = '❌ ' + msg;
            resEl.style.color = 'var(--accent-pink)';
        }
    }
}

async function loadLogs() {
    const res = await safeFetchJson('/api/logs?limit=50');
    const logs = res && res.data ? res.data : [];

    const formatLog = (l) => `<div class="log-item ${l.level}"><span class="log-time">${l.timestamp ? l.timestamp.substring(11, 19) : ''}</span> <span class="log-msg">[${l.level}] ${escapeHtml(l.message)}</span></div>`;

    const fullContainer = document.getElementById('full-logs-list');
    if (fullContainer) fullContainer.innerHTML = logs.map(formatLog).join('');

    const miniContainer = document.getElementById('dashboard-logs');
    if (miniContainer) miniContainer.innerHTML = logs.slice(0, 8).map(formatLog).join('');
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
