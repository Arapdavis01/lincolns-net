// ============================================================================
// Lincoln's net - Admin Core Module
// Handles: Authentication, Navigation, Sidebar, Notifications, Utilities
// Includes: Manual RADIUS Sync for failed auto-syncs
// ============================================================================

const BACKEND_URL = 'https://lincolns-net-backend.onrender.com';
const CURRENCY = 'KES';

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

async function showDashboard() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'flex';
    document.getElementById('dashboardView').classList.add('dark-mode');
    
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) {
        await loadSidebar();
    }
    
    loadNotifications();
    loadSection('dashboard');
}

// ============================================================================
// SIDEBAR LOADING
// ============================================================================

async function loadSidebar() {
    try {
        const response = await fetch('../components/sidebar.html');
        const html = await response.text();
        
        const dashboardView = document.getElementById('dashboardView');
        if (dashboardView) {
            dashboardView.insertAdjacentHTML('afterbegin', html);
        }
    } catch (error) {
        console.error('Error loading sidebar:', error);
    }
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
// TOAST NOTIFICATION SYSTEM
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
// NOTIFICATION BELL WITH DROPDOWN PANEL
// ============================================================================

async function loadNotifications() {
    const token = getAuthToken();
    const badge = document.getElementById('notificationBadge');
    
    if (!badge) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard/recent-transactions?limit=10`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            badge.textContent = data.transactions.length;
            badge.style.display = 'block';
            window.pendingNotifications = data.transactions;
        } else {
            badge.style.display = 'none';
            window.pendingNotifications = [];
        }
    } catch (error) {
        badge.style.display = 'none';
        window.pendingNotifications = [];
    }
}

function toggleNotificationsPanel(event) {
    event.stopPropagation();
    
    let panel = document.getElementById('notificationsPanel');
    
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'notificationsPanel';
        panel.className = 'notifications-panel';
        document.body.appendChild(panel);
    }
    
    if (panel.classList.contains('open')) {
        panel.classList.remove('open');
    } else {
        panel.classList.add('open');
        renderNotificationsContent();
    }
}

function renderNotificationsContent() {
    const panel = document.getElementById('notificationsPanel');
    if (!panel) return;
    
    const notifications = window.pendingNotifications || [];
    
    if (notifications.length === 0) {
        panel.innerHTML = `
            <div class="notifications-header">
                <h3><i class="fas fa-bell"></i> Notifications</h3>
                <button onclick="closeNotificationsPanel()"><i class="fas fa-times"></i></button>
            </div>
            <div class="notifications-empty">
                <i class="fas fa-bell-slash"></i>
                <p>No new notifications</p>
                <small>You're all caught up!</small>
            </div>
        `;
    } else {
        panel.innerHTML = `
            <div class="notifications-header">
                <h3><i class="fas fa-bell"></i> Notifications</h3>
                <button onclick="closeNotificationsPanel()"><i class="fas fa-times"></i></button>
            </div>
            <div class="notifications-list">
                ${notifications.map((tx) => `
                    <div class="notification-item">
                        <div class="notification-icon ${getStatusColor(tx.status)}">
                            <i class="fas fa-${getStatusIcon(tx.status)}"></i>
                        </div>
                        <div class="notification-content">
                            <p class="notification-message">
                                <strong>${tx.phone_number}</strong> paid 
                                <strong>${formatCurrency(tx.amount)}</strong>
                            </p>
                            <small class="notification-time">${new Date(tx.created_at).toLocaleTimeString()}</small>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div class="notifications-footer">
                <button onclick="markAllRead()"><i class="fas fa-check-double"></i> Mark all as read</button>
            </div>
        `;
    }
}

function closeNotificationsPanel() {
    const panel = document.getElementById('notificationsPanel');
    if (panel) panel.classList.remove('open');
}

function markAllRead() {
    const badge = document.getElementById('notificationBadge');
    if (badge) badge.style.display = 'none';
    window.pendingNotifications = [];
    closeNotificationsPanel();
    showNotification('All notifications marked as read', 'success');
}

function getStatusIcon(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'check-circle';
        case 'pending': return 'clock';
        case 'failed': return 'times-circle';
        default: return 'info-circle';
    }
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'green';
        case 'pending': return 'yellow';
        case 'failed': return 'red';
        default: return 'gray';
    }
}

document.addEventListener('click', function(event) {
    const panel = document.getElementById('notificationsPanel');
    const bell = document.querySelector('.notification-bell');
    
    if (panel && panel.classList.contains('open') && 
        !panel.contains(event.target) && 
        bell && !bell.contains(event.target)) {
        panel.classList.remove('open');
    }
});

// ============================================================================
// NAVIGATION SYSTEM
// ============================================================================

function showSection(section) {
    document.querySelectorAll('[id$="-section"]').forEach(el => {
        el.style.display = 'none';
    });
    
    const sectionElement = document.getElementById(section + '-section');
    if (sectionElement) sectionElement.style.display = 'block';
    
    const pageTitle = document.getElementById('pageTitle');
    if (pageTitle) {
        pageTitle.textContent = section.charAt(0).toUpperCase() + section.slice(1).replace(/-/g, ' ');
    }
    
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    
    if (event && event.target) {
        const navLink = event.target.closest('.nav-link');
        if (navLink) navLink.classList.add('active');
    }
    
    loadSection(section);
    
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.remove('open');
    }
}

function loadSection(section) {
    switch (section) {
        case 'dashboard': if (typeof loadDashboard === 'function') loadDashboard(); break;
        case 'users': if (typeof loadUsers === 'function') loadUsers(); break;
        case 'hotspot-users': if (typeof loadHotspotUsers === 'function') loadHotspotUsers(); break;
        case 'vouchers': if (typeof loadVouchers === 'function') loadVouchers(); break;
        case 'plans': if (typeof loadPlans === 'function') loadPlans(); break;
        case 'payments': if (typeof loadPayments === 'function') loadPayments(); break;
        case 'reports': if (typeof loadReports === 'function') loadReports(); break;
        case 'settings': if (typeof loadSettings === 'function') loadSettings(); break;
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatDuration(seconds) {
    if (!seconds) return '-';
    seconds = parseInt(seconds);
    if (seconds < 60) return `${seconds} seconds`;
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
        if (days % 7 === 0) return `${days / 7} ${days / 7 === 1 ? 'week' : 'weeks'}`;
        return `${days} days`;
    }
    const months = Math.floor(seconds / 2592000);
    const remainingDays = Math.floor((seconds % 2592000) / 86400);
    if (remainingDays === 0) return `${months} ${months === 1 ? 'month' : 'months'}`;
    return `${months} ${months === 1 ? 'month' : 'months'} ${remainingDays} days`;
}

function formatCurrency(amount) {
    return `${CURRENCY} ${parseFloat(amount || 0).toLocaleString()}`;
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
    
    if (hours > 24) return `${Math.floor(hours / 24)}D ${hours % 24}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// ============================================================================
// PACKAGE MODAL FUNCTIONS (Shared)
// ============================================================================

function openPackageModal(packageData = null) {
    const modal = document.getElementById('packageModal');
    if (!modal) return;
    modal.classList.add('open');
    
    if (packageData) {
        document.getElementById('packageModalTitle').innerHTML = '<i class="fas fa-edit"></i> Edit Plan';
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
        document.getElementById('packageModalTitle').innerHTML = '<i class="fas fa-plus-circle"></i> Add Plan';
        document.getElementById('packageForm').reset();
        document.getElementById('packageId').value = '';
        document.getElementById('packageMaxUsers').value = 1;
        document.getElementById('packageSupportsTv').checked = false;
    }
}

function closePackageModal() {
    const modal = document.getElementById('packageModal');
    if (modal) modal.classList.remove('open');
}

// ============================================================================
// MANUAL RADIUS SYNC FUNCTION (NEW)
// ============================================================================

/**
 * Manually sync a transaction to RADIUS.
 * Used when auto-sync failed after payment.
 * @param {string} transactionId - The transaction ID to sync
 */
async function manualRadiusSync(transactionId) {
    if (!transactionId) {
        showNotification('Transaction ID required', 'error');
        return;
    }
    
    if (!confirm('Manually sync this transaction to RADIUS?')) return;
    
    const token = getAuthToken();
    
    showNotification('Syncing to RADIUS...', 'info');
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/manual-radius-sync`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify({ transaction_id: transactionId }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`RADIUS sync successful for ${data.mac_address}`, 'success');
            
            // Reload dashboard data
            if (typeof loadDashboard === 'function') loadDashboard();
            if (typeof loadPayments === 'function') loadPayments();
        } else {
            showNotification(data.error || 'RADIUS sync failed', 'error');
        }
    } catch (error) {
        console.error('Manual sync error:', error);
        showNotification('Error syncing to RADIUS', 'error');
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    
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
            
            if (typeof createPackage === 'function' && !packageId) {
                createPackage(formData);
            } else if (typeof updatePackage === 'function' && packageId) {
                updatePackage(packageId, formData);
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
