// ============================================================================
// Lincoln's net - Dashboard Module
// ============================================================================

let userConnectionsChart = null;
let usersByPlanChart = null;

async function loadDashboard() {
    await Promise.all([
        loadDashboardStats(),
        loadConnectedUsers(),
        loadUserConnectionsChart(),
        loadUsersByPlanChart(),
    ]);
}

async function loadDashboardStats() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('totalUsers').textContent = data.total_customers || 0;
            document.getElementById('activeUsers').textContent = data.active_customers || 0;
            document.getElementById('todayRevenue').textContent = formatCurrency(data.today_revenue);
            document.getElementById('totalRevenue').textContent = formatCurrency(data.total_revenue);
            
            document.getElementById('sidebarTotalUsers').textContent = data.total_customers || 0;
            document.getElementById('sidebarActiveConnections').textContent = data.active_customers || 0;
            document.getElementById('sidebarTotalRevenue').textContent = formatCurrency(data.total_revenue);
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadConnectedUsers() {
    const token = getAuthToken();
    const tbody = document.getElementById('connectedUsersBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/transactions?status=SUCCESS&limit=10`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="user-avatar-sm"><i class="fas fa-user"></i></div>
                            <span>${tx.phone_number}</span>
                        </div>
                    </td>
                    <td>${tx.mac_address || '—'}</td>
                    <td><span class="dark-badge green">${tx.package?.name || 'Unknown'}</span></td>
                    <td>${getTimeLeft(tx.expires_at)}</td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                    <td><span class="dark-badge green"><i class="fas fa-circle"></i> Active</span></td>
                    <td>
                        <button class="btn-disconnect" onclick="disconnectUser('${tx.mac_address}')">
                            <i class="fas fa-unlink"></i> Disconnect
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">No connected users</td></tr>';
        }
    } catch (error) {
        console.error('Error loading connected users:', error);
    }
}

async function disconnectUser(macAddress) {
    if (!confirm('Disconnect this user?')) return;
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
            showNotification('User disconnected!', 'success');
            loadConnectedUsers();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadUserConnectionsChart() {
    const canvas = document.getElementById('userConnectionsChart');
    if (!canvas) return;
    
    if (userConnectionsChart) userConnectionsChart.destroy();
    
    const labels = Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`);
    const data = [5, 3, 2, 1, 1, 2, 4, 6, 8, 10, 12, 14, 15, 16, 18, 20, 22, 23, 21, 18, 15, 12, 8, 6];
    
    userConnectionsChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Connected Users',
                data: data,
                fill: true,
                backgroundColor: 'rgba(0, 123, 255, 0.2)',
                borderColor: '#007bff',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a0aec0' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a0aec0' } },
            },
        },
    });
}

async function loadUsersByPlanChart() {
    const canvas = document.getElementById('usersByPlanChart');
    if (!canvas) return;
    
    if (usersByPlanChart) usersByPlanChart.destroy();
    
    usersByPlanChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['1 Hour', '3 Hours', '1 Day', '1 Week', '1 Month'],
            datasets: [{
                data: [41, 39, 28, 14, 8],
                backgroundColor: ['#007bff', '#48bb78', '#ed8936', '#9f7aea', '#e53e3e'],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#a0aec0', padding: 10, font: { size: 11 } },
                },
            },
        },
    });
}
