// ============================================================================
// Lincoln's net - Admin Panel JavaScript (Complete)
// Dark Mode Dashboard with Charts and Connected Users
// ============================================================================

const BACKEND_URL = 'https://lincolns-net-backend.onrender.com';
const CURRENCY = 'KES';

// Chart instances (global)
let userConnectionsChart = null;
let usersByPlanChart = null;

// ============================================================================
// AUTHENTICATION FUNCTIONS
// ============================================================================

function getAuthToken() {
    return localStorage.getItem('adminAuth');
}

function isLoggedIn() {
    return !!getAuthToken();
}

function setAuthToken(username, password) {
    const token = btoa(username + ':' + password);
    localStorage.setItem('adminAuth', token);
}

function logout() {
    localStorage.removeItem('adminAuth');
    showLogin();
    showNotification('You have been logged out', 'info');
}

function showLogin() {
    document.getElementById('loginView').style.display = 'flex';
    document.getElementById('dashboardView').style.display = 'none';
    
    const passwordField = document.getElementById('password');
    if (passwordField) passwordField.value = '';
    
    const usernameField = document.getElementById('username');
    if (usernameField) usernameField.focus();
}

function showDashboard() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'flex';
    document.getElementById('dashboardView').classList.add('dark-mode');
    
    loadDashboardData();
}

// ============================================================================
// PASSWORD TOGGLE
// ============================================================================

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (!passwordInput || !eyeIcon) return;
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.classList.remove('fa-eye');
        eyeIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        eyeIcon.classList.remove('fa-eye-slash');
        eyeIcon.classList.add('fa-eye');
    }
}

// ============================================================================
// LOGIN HANDLER
// ============================================================================

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorElement = document.getElementById('loginError');
    const errorText = document.getElementById('loginErrorText');
    const loginButton = document.getElementById('loginButton');
    
    errorElement.style.display = 'none';
    
    if (!username || !password) {
        errorText.textContent = 'Please enter both username and password';
        errorElement.style.display = 'flex';
        return;
    }
    
    loginButton.disabled = true;
    loginButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            setAuthToken(username, password);
            showNotification('Login successful!', 'success');
            showDashboard();
        } else {
            errorText.textContent = data.message || 'Invalid username or password';
            errorElement.style.display = 'flex';
        }
    } catch (error) {
        console.error('Login error:', error);
        errorText.textContent = 'Error connecting to server. Please try again.';
        errorElement.style.display = 'flex';
    } finally {
        loginButton.disabled = false;
        loginButton.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
    }
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) notification.remove();
    }, 3000);
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// ============================================================================
// DASHBOARD DATA LOADING
// ============================================================================

async function loadDashboardData() {
    await Promise.all([
        loadDashboardStats(),
        loadConnectedUsers(),
        loadUserConnectionsChart(),
        loadUsersByPlanChart(),
        loadPackages(),
        loadTransactions(),
    ]);
}

// ============================================================================
// DASHBOARD STATS (Metric Cards)
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
            document.getElementById('todayRevenue').textContent = `${CURRENCY} ${(data.today_revenue || 0).toLocaleString()}`;
            document.getElementById('totalRevenue').textContent = `${CURRENCY} ${(data.total_revenue || 0).toLocaleString()}`;
            
            // Update sidebar system info
            document.getElementById('sidebarTotalUsers').textContent = data.total_customers || 0;
            document.getElementById('sidebarActiveConnections').textContent = data.active_customers || 0;
            document.getElementById('sidebarTotalRevenue').textContent = `${CURRENCY} ${(data.total_revenue || 0).toLocaleString()}`;
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// ============================================================================
// CONNECTED USERS TABLE
// ============================================================================

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
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div class="user-avatar-sm">
                                <i class="fas fa-user"></i>
                            </div>
                            <span>${tx.phone_number}</span>
                        </div>
                    </td>
                    <td>${tx.mac_address || '—'}</td>
                    <td>
                        <span class="dark-badge green">
                            <i class="fas fa-wifi"></i> ${tx.package?.name || 'Unknown'}
                        </span>
                    </td>
                    <td>${getTimeLeft(tx.expires_at)}</td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                    <td>
                        <span class="dark-badge green">
                            <i class="fas fa-circle"></i> Active
                        </span>
                    </td>
                    <td>
                        <button class="btn-disconnect" onclick="disconnectUser('${tx.mac_address}')">
                            <i class="fas fa-unlink"></i> Disconnect
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center; padding:40px; color:#a0aec0;">
                        <i class="fas fa-users" style="font-size:40px; display:block; margin-bottom:12px;"></i>
                        No connected users
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading connected users:', error);
    }
}

function getTimeLeft(expiresAt) {
    if (!expiresAt) return '—';
    
    const now = new Date();
    const expires = new Date(expiresAt);
    const diff = expires - now;
    
    if (diff <= 0) return 'Expired';
    
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days}D ${hours % 24}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
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
        } else {
            showNotification(data.error || 'Failed to disconnect', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error disconnecting user', 'error');
    }
}

// ============================================================================
// CHARTS
// ============================================================================

async function loadUserConnectionsChart() {
    const canvas = document.getElementById('userConnectionsChart');
    if (!canvas) return;
    
    // Destroy existing chart
    if (userConnectionsChart) {
        userConnectionsChart.destroy();
    }
    
    // Sample data for 24 hours
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
                pointHoverRadius: 5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#a0aec0', maxTicksLimit: 12 },
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#a0aec0' },
                },
            },
        },
    });
}

async function loadUsersByPlanChart() {
    const canvas = document.getElementById('usersByPlanChart');
    if (!canvas) return;
    
    // Destroy existing chart
    if (usersByPlanChart) {
        usersByPlanChart.destroy();
    }
    
    // Sample data
    const data = {
        labels: ['1 Hour', '3 Hours', '1 Day', '1 Week', '1 Month'],
        datasets: [{
            data: [41, 39, 28, 14, 8],
            backgroundColor: ['#007bff', '#48bb78', '#ed8936', '#9f7aea', '#e53e3e'],
            borderWidth: 0,
        }]
    };
    
    usersByPlanChart = new Chart(canvas, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#a0aec0',
                        padding: 10,
                        font: { size: 12 },
                    },
                },
            },
            cutout: '60%',
        },
    });
}

// ============================================================================
// PACKAGE MANAGEMENT (Same as before)
// ============================================================================

async function loadPackages() {
    const token = getAuthToken();
    const tbody = document.getElementById('packagesTableBody');
    
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.packages.length > 0) {
            tbody.innerHTML = data.packages.map(pkg => `
                <tr>
                    <td><strong>${pkg.name}</strong></td>
                    <td>${CURRENCY} ${parseFloat(pkg.price).toLocaleString()}</td>
                    <td>${formatDuration(pkg.duration_seconds)}</td>
                    <td>${pkg.download_rate_limit} / ${pkg.upload_rate_limit}</td>
                    <td>${pkg.max_users || 1}</td>
                    <td>${pkg.supports_tv ? 'Yes' : '—'}</td>
                    <td>
                        <span class="status-badge ${pkg.is_active ? 'status-success' : 'status-failed'}">
                            ${pkg.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editPackage(${pkg.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading packages:', error);
    }
}

function openPackageModal(packageData = null) {
    const modal = document.getElementById('packageModal');
    modal.classList.add('open');
    
    if (packageData) {
        document.getElementById('packageId').value = packageData.id;
        document.getElementById('packageName').value = packageData.name;
        document.getElementById('packageDescription').value = packageData.description || '';
        document.getElementById('packagePrice').value = packageData.price;
        document.getElementById('packageDuration').value = packageData.duration_seconds;
        document.getElementById('packageDownload').value = packageData.download_rate_limit;
        document.getElementById('packageUpload').value = packageData.upload_rate_limit;
        document.getElementById('packageMaxUsers').value = packageData.max_users || 1;
        document.getElementById('packageSupportsTv').checked = packageData.supports_tv || false;
    } else {
        document.getElementById('packageForm').reset();
        document.getElementById('packageId').value = '';
        document.getElementById('packageMaxUsers').value = 1;
    }
}

function closePackageModal() {
    document.getElementById('packageModal').classList.remove('open');
}

async function editPackage(packageId) {
    const token = getAuthToken();
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const data = await response.json();
        if (data.success) {
            openPackageModal(data.package);
            document.getElementById('packageForm').dataset.packageId = packageId;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function deletePackage(packageId) {
    if (!confirm('Deactivate this package?')) return;
    const token = getAuthToken();
    try {
        await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Basic ' + token },
        });
        showNotification('Package deactivated!', 'success');
        loadPackages();
        loadDashboardStats();
    } catch (error) {
        console.error('Error:', error);
    }
}

// ============================================================================
// TRANSACTIONS (Same as before)
// ============================================================================

async function loadTransactions() {
    const token = getAuthToken();
    const tbody = document.getElementById('transactionsTableBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/transactions`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>${tx.transaction_id ? tx.transaction_id.substring(0, 12) + '...' : '-'}</td>
                    <td>${tx.phone_number}</td>
                    <td>${CURRENCY} ${parseFloat(tx.amount).toLocaleString()}</td>
                    <td>${tx.device_type || 'phone'}</td>
                    <td><span class="status-badge status-${tx.status.toLowerCase()}">${tx.status}</span></td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// ============================================================================
// SETTINGS (Same as before)
// ============================================================================

async function loadSettings() {
    const token = getAuthToken();
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const data = await response.json();
        
        if (data.success && data.settings.length > 0) {
            settingsContent.innerHTML = data.settings.map(setting => `
                <div class="form-group">
                    <label class="form-label">
                        <i class="fas fa-cog"></i> ${setting.description || setting.setting_key}
                    </label>
                    <input type="text" class="form-input" name="${setting.setting_key}" 
                           value="${setting.setting_value}" data-setting-key="${setting.setting_key}">
                </div>
            `).join('') + `
                <button class="btn btn-primary" onclick="saveSettings()">
                    <i class="fas fa-save"></i> Save Settings
                </button>
            `;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    const token = getAuthToken();
    const settingsInputs = document.querySelectorAll('[data-setting-key]');
    
    try {
        for (const input of settingsInputs) {
            await fetch(`${BACKEND_URL}/admin/api/settings`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + token,
                },
                body: JSON.stringify({
                    setting_key: input.dataset.settingKey,
                    setting_value: input.value,
                }),
            });
        }
        showNotification('Settings saved!', 'success');
    } catch (error) {
        console.error('Error:', error);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatDuration(seconds) {
    if (!seconds) return '-';
    seconds = parseInt(seconds);
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) {
        const hours = Math.floor(seconds / 3600);
        return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
    }
    if (seconds < 604800) {
        const days = Math.floor(seconds / 86400);
        return `${days} ${days === 1 ? 'day' : 'days'}`;
    }
    if (seconds < 2592000) {
        const days = Math.floor(seconds / 86400);
        if (days % 7 === 0) {
            const weeks = days / 7;
            return `${weeks} ${weeks === 1 ? 'week' : 'weeks'}`;
        }
        return `${days} days`;
    }
    const months = Math.floor(seconds / 2592000);
    return `${months} ${months === 1 ? 'month' : 'months'}`;
}

function showSection(section) {
    document.querySelectorAll('[id$="-section"]').forEach(el => {
        el.style.display = 'none';
    });
    
    const sectionElement = document.getElementById(section + '-section');
    if (sectionElement) sectionElement.style.display = 'block';
    
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    
    if (event && event.target) {
        const navLink = event.target.closest('.nav-link');
        if (navLink) navLink.classList.add('active');
    }
    
    switch (section) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'packages':
            loadPackages();
            break;
        case 'transactions':
            loadTransactions();
            break;
        case 'settings':
            loadSettings();
            break;
    }
    
    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const packageForm = document.getElementById('packageForm');
    if (packageForm) {
        packageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const packageId = this.dataset.packageId;
            const formData = {
                name: document.getElementById('packageName').value.trim(),
                description: document.getElementById('packageDescription').value.trim(),
                price: parseFloat(document.getElementById('packagePrice').value),
                duration_seconds: parseInt(document.getElementById('packageDuration').value),
                download_rate_limit: document.getElementById('packageDownload').value.trim(),
                upload_rate_limit: document.getElementById('packageUpload').value.trim(),
                max_users: parseInt(document.getElementById('packageMaxUsers').value) || 1,
                supports_tv: document.getElementById('packageSupportsTv').checked,
            };
            
            if (packageId) {
                updatePackage(packageId, formData);
            } else {
                createPackage(formData);
            }
        });
    }
    
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('open');
        }
    });
    
    if (isLoggedIn()) {
        showDashboard();
    } else {
        showLogin();
    }
});

// ============================================================================
// CREATE & UPDATE PACKAGE
// ============================================================================

async function createPackage(formData) {
    const token = getAuthToken();
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify(formData),
        });
        const data = await response.json();
        if (data.success) {
            showNotification('Package created!', 'success');
            closePackageModal();
            loadPackages();
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function updatePackage(packageId, formData) {
    const token = getAuthToken();
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify(formData),
        });
        const data = await response.json();
        if (data.success) {
            showNotification('Package updated!', 'success');
            closePackageModal();
            loadPackages();
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
