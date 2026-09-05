// ============================================================================
// Lincoln's net - Hotspot Users Module
// Manages currently connected users
// ============================================================================

async function loadHotspotUsers() {
    const token = getAuthToken();
    const tbody = document.getElementById('hotspotUsersBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/transactions?status=SUCCESS`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            // Filter only active sessions (not expired)
            const activeUsers = data.transactions.filter(tx => {
                if (!tx.expires_at) return false;
                return new Date(tx.expires_at) > new Date();
            });
            
            if (activeUsers.length > 0) {
                tbody.innerHTML = activeUsers.map(tx => `
                    <tr>
                        <td>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <div class="user-avatar-sm"><i class="fas fa-user"></i></div>
                                <span>${tx.phone_number}</span>
                            </div>
                        </td>
                        <td>${tx.mac_address || '—'}</td>
                        <td>
                            <span class="dark-badge green">
                                <i class="fas fa-wifi"></i> ${getPlanName(tx.package_id)}
                            </span>
                        </td>
                        <td>${getTimeLeft(tx.expires_at)}</td>
                        <td>${new Date(tx.created_at).toLocaleTimeString()}</td>
                        <td>
                            <span class="dark-badge green">
                                <i class="fas fa-circle"></i> Active
                            </span>
                        </td>
                        <td>
                            <button class="btn-disconnect" onclick="disconnectHotspotUser('${tx.mac_address}')">
                                <i class="fas fa-unlink"></i> Disconnect
                            </button>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;"><i class="fas fa-wifi" style="font-size:40px;display:block;margin-bottom:12px;"></i>No active connections</td></tr>';
            }
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">No hotspot users</td></tr>';
        }
    } catch (error) {
        console.error('Error loading hotspot users:', error);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#e53e3e;">Error loading data</td></tr>';
    }
}

function getPlanName(packageId) {
    // Simple mapping - update based on your packages
    const plans = {
        1: '30 mins',
        2: '1 Hour',
        3: '1.5 Hours',
        4: '5 Hours',
        5: '12 Hours',
        6: '1 Day',
        7: '1 Week',
        8: '1 Month',
    };
    return plans[packageId] || 'Unknown';
}

async function disconnectHotspotUser(macAddress) {
    if (!confirm('Disconnect this user from hotspot?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/disconnect-user`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify({ mac_address: macAddress }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('User disconnected from hotspot!', 'success');
            loadHotspotUsers();
            if (typeof loadDashboardStats === 'function') loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to disconnect', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error disconnecting user', 'error');
    }
}
