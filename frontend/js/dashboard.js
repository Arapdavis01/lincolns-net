// ============================================================================
// Lincoln's net - Dashboard Module (REAL DATA)
// Pulls actual data from backend API endpoints
// ============================================================================

let userConnectionsChart = null;
let usersByPlanChart = null;
let revenueChart = null;

// ============================================================================
// MAIN DASHBOARD LOADER
// ============================================================================

async function loadDashboard() {
    await Promise.all([
        loadDashboardStats(),
        loadConnectedUsers(),
        loadUserConnectionsChart(),
        loadUsersByPlanChart(),
        loadRecentTransactions(),
    ]);
}

// ============================================================================
// DASHBOARD STATS (Metric Cards) - REAL DATA
// ============================================================================

async function loadDashboardStats() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Update metric cards
            document.getElementById('totalUsers').textContent = data.total_customers || 0;
            document.getElementById('activeUsers').textContent = data.active_customers || 0;
            document.getElementById('todayRevenue').textContent = formatCurrency(data.today_revenue);
            document.getElementById('totalRevenue').textContent = formatCurrency(data.total_revenue);
            
            // Update sidebar system info
            const sidebarTotalUsers = document.getElementById('sidebarTotalUsers');
            const sidebarActiveConnections = document.getElementById('sidebarActiveConnections');
            const sidebarTotalRevenue = document.getElementById('sidebarTotalRevenue');
            
            if (sidebarTotalUsers) sidebarTotalUsers.textContent = data.total_customers || 0;
            if (sidebarActiveConnections) sidebarActiveConnections.textContent = data.active_customers || 0;
            if (sidebarTotalRevenue) sidebarTotalRevenue.textContent = formatCurrency(data.total_revenue);
            
            // Update report stats if they exist
            const reportTotalRevenue = document.getElementById('reportTotalRevenue');
            const reportTotalTransactions = document.getElementById('reportTotalTransactions');
            const reportTotalCustomers = document.getElementById('reportTotalCustomers');
            const reportActiveCustomers = document.getElementById('reportActiveCustomers');
            
            if (reportTotalRevenue) reportTotalRevenue.textContent = formatCurrency(data.total_revenue);
            if (reportTotalTransactions) reportTotalTransactions.textContent = data.total_transactions || 0;
            if (reportTotalCustomers) reportTotalCustomers.textContent = data.total_customers || 0;
            if (reportActiveCustomers) reportActiveCustomers.textContent = data.active_customers || 0;
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showNotification('Error loading dashboard stats', 'error');
    }
}

// ============================================================================
// CONNECTED USERS TABLE - REAL ACTIVE SESSIONS
// ============================================================================

async function loadConnectedUsers() {
    const token = getAuthToken();
    const tbody = document.getElementById('connectedUsersBody');
    if (!tbody) return;
    
    try {
        // Use the NEW active-sessions endpoint
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard/active-sessions`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.sessions.length > 0) {
            tbody.innerHTML = data.sessions.map(session => `
                <tr>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="user-avatar-sm"><i class="fas fa-user"></i></div>
                            <span>${session.phone_number}</span>
                        </div>
                    </td>
                    <td>${session.mac_address || '—'}</td>
                    <td>
                        <span class="dark-badge green">
                            <i class="fas fa-wifi"></i> ${session.package_name || 'Unknown'}
                        </span>
                    </td>
                    <td>${getTimeLeft(session.expires_at)}</td>
                    <td>${session.created_at ? new Date(session.created_at).toLocaleTimeString() : '—'}</td>
                    <td>
                        <span class="dark-badge green">
                            <i class="fas fa-circle"></i> Active
                        </span>
                    </td>
                    <td>
                        <button class="btn-disconnect" onclick="disconnectUser('${session.mac_address}')">
                            <i class="fas fa-unlink"></i> Disconnect
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-users" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No active connections
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading connected users:', error);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#e53e3e;">Error loading data</td></tr>';
    }
}

// ============================================================================
// DISCONNECT USER
// ============================================================================

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
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Failed to disconnect', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error disconnecting user', 'error');
    }
}

// ============================================================================
// USER CONNECTIONS CHART - REAL 24HR DATA
// ============================================================================

async function loadUserConnectionsChart() {
    const canvas = document.getElementById('userConnectionsChart');
    if (!canvas) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard/connections-24hr`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (userConnectionsChart) userConnectionsChart.destroy();
        
        if (data.success && data.connections.length > 0) {
            const labels = data.connections.map(c => c.hour);
            const counts = data.connections.map(c => c.count);
            
            userConnectionsChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Connected Users',
                        data: counts,
                        fill: true,
                        backgroundColor: 'rgba(0, 123, 255, 0.2)',
                        borderColor: '#007bff',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#a0aec0', maxTicksLimit: 12 },
                        },
                        y: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#a0aec0', beginAtZero: true, stepSize: 1 },
                        },
                    },
                },
            });
        } else {
            // No data, show empty chart
            userConnectionsChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`),
                    datasets: [{
                        label: 'No data',
                        data: Array(24).fill(0),
                        fill: true,
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        borderColor: '#007bff',
                        borderWidth: 1,
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
    } catch (error) {
        console.error('Error loading connections chart:', error);
    }
}

// ============================================================================
// USERS BY PLAN CHART - REAL DATA
// ============================================================================

async function loadUsersByPlanChart() {
    const canvas = document.getElementById('usersByPlanChart');
    if (!canvas) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard/users-by-plan`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (usersByPlanChart) usersByPlanChart.destroy();
        
        if (data.success && data.plans.length > 0) {
            const labels = data.plans.map(p => p.plan_name);
            const counts = data.plans.map(p => p.user_count);
            
            // Dynamic colors based on number of plans
            const colors = [
                '#007bff', '#48bb78', '#ed8936', '#9f7aea', '#e53e3e',
                '#38bdf8', '#f472b6', '#34d399', '#fbbf24', '#818cf8'
            ];
            
            usersByPlanChart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: colors.slice(0, labels.length),
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
                            labels: {
                                color: '#a0aec0',
                                padding: 10,
                                font: { size: 11 },
                            },
                        },
                    },
                },
            });
        } else {
            // No data
            usersByPlanChart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: ['No data'],
                    datasets: [{
                        data: [1],
                        backgroundColor: ['#3a3a4d'],
                        borderWidth: 0,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: { display: false },
                    },
                },
            });
        }
    } catch (error) {
        console.error('Error loading users by plan chart:', error);
    }
}

// ============================================================================
// RECENT TRANSACTIONS - REAL DATA
// ============================================================================

async function loadRecentTransactions() {
    const token = getAuthToken();
    const tbody = document.getElementById('recentTransactionsBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard/recent-transactions`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td><i class="fas fa-phone"></i> ${tx.phone_number}</td>
                    <td>${formatCurrency(tx.amount)}</td>
                    <td>
                        <span class="dark-badge ${getStatusColor(tx.status)}">
                            ${tx.status}
                        </span>
                    </td>
                    <td>${tx.created_at ? new Date(tx.created_at).toLocaleTimeString() : '—'}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align:center;padding:20px;color:#a0aec0;">
                        No transactions yet
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading recent transactions:', error);
    }
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'green';
        case 'pending': return 'yellow';
        case 'failed': return 'red';
        case 'expired': return 'gray';
        default: return 'green';
    }
}
