// ============================================================================
// Lincoln's net - Hotspot Users Module (Complete)
// Includes: Stats, Search, Filter, Auto-Refresh, Time Warnings, Extend, Disconnect
// ============================================================================

let hotspotAutoRefreshInterval = null;
let hotspotCurrentSearch = '';
let hotspotCurrentPlanFilter = '';
let hotspotLastUpdated = null;

// ============================================================================
// MAIN LOADER
// ============================================================================

async function loadHotspotUsers() {
    await Promise.all([
        loadHotspotStats(),
        loadHotspotUsersTable(),
    ]);
    
    // Start auto-refresh if not already running
    startHotspotAutoRefresh();
}

// ============================================================================
// AUTO-REFRESH
// ============================================================================

function startHotspotAutoRefresh() {
    // Clear existing interval
    if (hotspotAutoRefreshInterval) {
        clearInterval(hotspotAutoRefreshInterval);
    }
    
    // Refresh every 30 seconds
    hotspotAutoRefreshInterval = setInterval(() => {
        loadHotspotUsersTable();
        updateHotspotLastUpdated();
    }, 30000);
}

function stopHotspotAutoRefresh() {
    if (hotspotAutoRefreshInterval) {
        clearInterval(hotspotAutoRefreshInterval);
        hotspotAutoRefreshInterval = null;
    }
}

function updateHotspotLastUpdated() {
    hotspotLastUpdated = new Date();
    const element = document.getElementById('hotspotLastUpdated');
    if (element) {
        element.textContent = `Last updated: ${hotspotLastUpdated.toLocaleTimeString()}`;
    }
}

function refreshHotspotNow() {
    loadHotspotUsersTable();
    loadHotspotStats();
    updateHotspotLastUpdated();
    showNotification('Hotspot users refreshed', 'info');
}

// ============================================================================
// HOTSPOT STATS CARDS
// ============================================================================

async function loadHotspotStats() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/hotspot-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('hotspotActiveConnections').textContent = data.active_connections || 0;
            document.getElementById('hotspotTodayConnections').textContent = data.today_connections || 0;
            document.getElementById('hotspotExpiringSoon').textContent = data.expiring_soon || 0;
            document.getElementById('hotspotTodayRevenue').textContent = formatCurrency(data.today_revenue);
        }
    } catch (error) {
        console.error('Error loading hotspot stats:', error);
    }
}

// ============================================================================
// HOTSPOT USERS TABLE
// ============================================================================

async function loadHotspotUsersTable() {
    const token = getAuthToken();
    const tbody = document.getElementById('hotspotUsersBody');
    if (!tbody) return;
    
    try {
        // Build URL with filters
        let url = `${BACKEND_URL}/admin/api/hotspot-users`;
        const params = [];
        
        if (hotspotCurrentSearch) {
            params.push(`search=${encodeURIComponent(hotspotCurrentSearch)}`);
        }
        if (hotspotCurrentPlanFilter) {
            params.push(`plan_filter=${encodeURIComponent(hotspotCurrentPlanFilter)}`);
        }
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        const response = await fetch(url, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.users.length > 0) {
            tbody.innerHTML = data.users.map(user => `
                <tr onclick="viewHotspotUserDetails('${user.mac_address}')" style="cursor: pointer;">
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="user-avatar-sm">${getInitials(user.phone_number)}</div>
                            <span>${user.phone_number}</span>
                        </div>
                    </td>
                    <td>
                        <code style="background:#2d3748;padding:4px 8px;border-radius:4px;color:#e2e8f0;font-size:12px;">
                            ${user.mac_address}
                        </code>
                    </td>
                    <td>
                        <span class="dark-badge ${getPlanBadgeColor(user.package_name)}">
                            <i class="fas fa-wifi"></i> ${user.package_name}
                        </span>
                    </td>
                    <td>${user.download_rate} / ${user.upload_rate}</td>
                    <td>
                        <span class="time-left-badge ${getTimeLeftColor(user.time_left_seconds)}">
                            <i class="fas fa-hourglass-half"></i> ${formatTimeLeft(user.time_left_seconds)}
                        </span>
                    </td>
                    <td>${new Date(user.created_at).toLocaleTimeString()}</td>
                    <td>
                        <span class="dark-badge ${getStatusBadgeColor(user.status)}">
                            <i class="fas fa-circle"></i> ${getStatusLabel(user.status)}
                        </span>
                    </td>
                    <td onclick="event.stopPropagation()">
                        <div style="display:flex;gap:6px;">
                            <button class="btn btn-sm btn-primary" onclick="viewHotspotUserDetails('${user.mac_address}')" title="View">
                                <i class="fas fa-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-success" onclick="extendHotspotUser('${user.mac_address}')" title="Extend 1 Hour">
                                <i class="fas fa-clock"></i>
                            </button>
                            <button class="btn-disconnect" onclick="disconnectHotspotUser('${user.mac_address}')" title="Disconnect">
                                <i class="fas fa-unlink"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
            
            updateHotspotLastUpdated();
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-wifi" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No active connections
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading hotspot users:', error);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:40px;color:#e53e3e;">Error loading data</td></tr>';
    }
}

// ============================================================================
// SEARCH
// ============================================================================

function searchHotspotUsers() {
    const searchInput = document.getElementById('hotspotSearchInput');
    if (!searchInput) return;
    
    hotspotCurrentSearch = searchInput.value.trim();
    loadHotspotUsersTable();
}

let hotspotSearchTimeout;
function onHotspotSearchInput() {
    clearTimeout(hotspotSearchTimeout);
    hotspotSearchTimeout = setTimeout(() => {
        searchHotspotUsers();
    }, 500);
}

// ============================================================================
// FILTER BY PLAN
// ============================================================================

function filterHotspotByPlan() {
    const filterSelect = document.getElementById('hotspotPlanFilter');
    if (!filterSelect) return;
    
    hotspotCurrentPlanFilter = filterSelect.value;
    loadHotspotUsersTable();
}

// ============================================================================
// VIEW USER DETAILS
// ============================================================================

async function viewHotspotUserDetails(macAddress) {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/hotspot-users/${encodeURIComponent(macAddress)}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            const conn = data.connection;
            
            document.getElementById('hotspotUserDetailContent').innerHTML = `
                <div style="text-align:center;margin-bottom:20px;">
                    <div class="user-detail-avatar">${getInitials(conn.phone_number)}</div>
                    <h3 style="color:#e2e8f0;margin:12px 0 4px;">${conn.phone_number}</h3>
                    <span class="dark-badge green"><i class="fas fa-circle"></i> Connected</span>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">MAC Address</small>
                        <div style="color:#e2e8f0;font-size:14px;margin-top:4px;">${conn.mac_address}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Package</small>
                        <div style="color:#e2e8f0;font-size:14px;margin-top:4px;">${conn.package_name}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Connected At</small>
                        <div style="color:#e2e8f0;font-size:14px;margin-top:4px;">${new Date(conn.created_at).toLocaleString()}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Expires At</small>
                        <div style="color:#e2e8f0;font-size:14px;margin-top:4px;">${new Date(conn.expires_at).toLocaleString()}</div>
                    </div>
                </div>
                
                <div style="margin-bottom:16px;">
                    <small style="color:#a0aec0;">TIME REMAINING</small>
                    <div style="margin-top:8px;">
                        <div style="background:#1a1a27;border-radius:20px;height:10px;overflow:hidden;">
                            <div style="background:${getTimeLeftProgressColor(conn.time_left_seconds)};height:100%;width:${getTimeLeftProgressPercent(conn.time_left_seconds)}%;border-radius:20px;"></div>
                        </div>
                        <div style="text-align:center;margin-top:8px;color:#e2e8f0;font-weight:600;">
                            ${formatTimeLeft(conn.time_left_seconds)}
                        </div>
                    </div>
                </div>
                
                <div style="display:flex;gap:12px;">
                    <button class="btn btn-success btn-block" onclick="extendHotspotUser('${conn.mac_address}')">
                        <i class="fas fa-clock"></i> Extend 1 Hour
                    </button>
                    <button class="btn btn-danger btn-block" onclick="disconnectHotspotUser('${conn.mac_address}')">
                        <i class="fas fa-unlink"></i> Disconnect
                    </button>
                </div>
            `;
            
            document.getElementById('hotspotUserDetailModal').classList.add('open');
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        showNotification('Error loading details', 'error');
    }
}

function closeHotspotUserDetailModal() {
    const modal = document.getElementById('hotspotUserDetailModal');
    if (modal) modal.classList.remove('open');
}

// ============================================================================
// DISCONNECT USER
// ============================================================================

async function disconnectHotspotUser(macAddress) {
    if (!confirm('Disconnect this user from hotspot?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/hotspot-users/${encodeURIComponent(macAddress)}/disconnect`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('User disconnected!', 'success');
            closeHotspotUserDetailModal();
            loadHotspotUsersTable();
            loadHotspotStats();
            if (typeof loadDashboardStats === 'function') loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to disconnect', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error disconnecting user', 'error');
    }
}

// ============================================================================
// EXTEND SESSION
// ============================================================================

async function extendHotspotUser(macAddress) {
    if (!confirm('Extend this user\'s session by 1 hour?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/hotspot-users/${encodeURIComponent(macAddress)}/extend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify({ extend_seconds: 3600 }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Session extended by 1 hour!', 'success');
            closeHotspotUserDetailModal();
            loadHotspotUsersTable();
        } else {
            showNotification(data.error || 'Failed to extend session', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error extending session', 'error');
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getInitials(phoneNumber) {
    if (!phoneNumber) return '?';
    const clean = phoneNumber.replace(/^\+?254/, '').replace(/^0/, '');
    return clean.substring(0, 2).toUpperCase();
}

function formatTimeLeft(seconds) {
    if (!seconds || seconds <= 0) return 'Expired';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days}D ${hours % 24}h ${minutes}m`;
    }
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    
    return `${minutes}m ${secs}s`;
}

function getTimeLeftColor(seconds) {
    if (seconds > 3600) return 'green';      // More than 1 hour
    if (seconds > 900) return 'yellow';       // More than 15 minutes
    if (seconds > 300) return 'orange';       // More than 5 minutes
    return 'red';                              // Less than 5 minutes
}

function getTimeLeftProgressPercent(seconds) {
    if (seconds <= 0) return 0;
    // Assuming max session is 24 hours
    const maxSeconds = 86400;
    const percent = (seconds / maxSeconds) * 100;
    return Math.min(Math.max(percent, 0), 100);
}

function getTimeLeftProgressColor(seconds) {
    const color = getTimeLeftColor(seconds);
    switch (color) {
        case 'green': return '#48bb78';
        case 'yellow': return '#ed8936';
        case 'orange': return '#e53e3e';
        default: return '#e53e3e';
    }
}

function getStatusBadgeColor(status) {
    switch (status) {
        case 'active': return 'green';
        case 'expiring': return 'yellow';
        case 'critical': return 'red';
        default: return 'gray';
    }
}

function getStatusLabel(status) {
    switch (status) {
        case 'active': return 'Active';
        case 'expiring': return 'Expiring';
        case 'critical': return 'Critical';
        default: return status;
    }
}

function getPlanBadgeColor(planName) {
    const plans = {
        'Hourly Pass': 'green',
        'Daily Pass': 'yellow',
        'Weekly Pass': 'purple',
        'Monthly Pass': 'pink',
    };
    return plans[planName] || 'green';
}
