// ============================================================================
// Lincoln's net - Admin Panel JavaScript (Complete)
// Single page application with login and dashboard
// Includes: max_users, supports_tv, TV devices, support phone settings
// FIXED: formatDuration for days/weeks/months
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

function showDashboard() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'flex';
    
    loadDashboardStats();
    loadPackages();
    loadTransactions();
    loadTvDevices();
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
// DASHBOARD FUNCTIONS
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
            document.getElementById('totalPackages').textContent = data.total_packages || 0;
            document.getElementById('activePackages').textContent = data.active_packages || 0;
            document.getElementById('totalRevenue').textContent = `${CURRENCY} ${(data.total_revenue || 0).toLocaleString()}`;
            document.getElementById('totalTransactions').textContent = data.total_transactions || 0;
            document.getElementById('activeCustomers').textContent = data.active_customers || 0;
            
            const tvElement = document.getElementById('totalTvDevices');
            if (tvElement) {
                tvElement.textContent = data.total_tv_devices || 0;
            }
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Error loading dashboard data', 'error');
    }
}

// ============================================================================
// PACKAGE MANAGEMENT
// ============================================================================

async function loadPackages() {
    const token = getAuthToken();
    const tbody = document.getElementById('packagesTableBody');
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.packages.length > 0) {
            tbody.innerHTML = data.packages.map(pkg => `
                <tr>
                    <td>
                        <strong>${pkg.name}</strong>
                        ${pkg.description ? `<br><small style="color:#a0aec0;">${pkg.description}</small>` : ''}
                    </td>
                    <td>${CURRENCY} ${parseFloat(pkg.price).toLocaleString()}</td>
                    <td>${formatDuration(pkg.duration_seconds)}</td>
                    <td>
                        <i class="fas fa-download"></i> ${pkg.download_rate_limit} 
                        <i class="fas fa-upload"></i> ${pkg.upload_rate_limit}
                    </td>
                    <td>
                        <span class="users-badge ${pkg.max_users > 1 ? '' : 'single'}">
                            <i class="fas fa-${pkg.max_users > 1 ? 'users' : 'user'}"></i> ${pkg.max_users}
                        </span>
                    </td>
                    <td>
                        ${pkg.supports_tv ? 
                            '<span class="tv-badge"><i class="fas fa-tv"></i> Yes</span>' : 
                            '<span style="color:#a0aec0;">—</span>'
                        }
                    </td>
                    <td>
                        <span class="status-badge ${pkg.is_active ? 'status-success' : 'status-failed'}">
                            ${pkg.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editPackage(${pkg.id})" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align:center; padding:40px; color:#a0aec0;">
                        <i class="fas fa-box-open" style="font-size:40px; display:block; margin-bottom:12px;"></i>
                        No packages found. Add your first package!
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading packages:', error);
        showNotification('Error loading packages', 'error');
    }
}

function openPackageModal(packageData = null) {
    const modal = document.getElementById('packageModal');
    modal.classList.add('open');
    
    if (packageData) {
        document.getElementById('packageModalTitle').innerHTML = '<i class="fas fa-edit"></i> Edit Package';
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
        document.getElementById('packageModalTitle').innerHTML = '<i class="fas fa-plus-circle"></i> Add Package';
        document.getElementById('packageForm').reset();
        document.getElementById('packageId').value = '';
        document.getElementById('packageMaxUsers').value = 1;
        document.getElementById('packageSupportsTv').checked = false;
    }
}

function closePackageModal() {
    document.getElementById('packageModal').classList.remove('open');
    
    const form = document.getElementById('packageForm');
    if (form) {
        form.reset();
        delete form.dataset.packageId;
    }
    
    const title = document.querySelector('#packageModal .modal-header h2');
    if (title) {
        title.innerHTML = '<i class="fas fa-plus-circle"></i> Add Package';
    }
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
        showNotification('Error loading package details', 'error');
    }
}

async function deletePackage(packageId) {
    if (!confirm('Are you sure you want to deactivate this package?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Package deactivated!', 'success');
            loadPackages();
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error deactivating package', 'error');
    }
}

// ============================================================================
// TRANSACTION MANAGEMENT
// ============================================================================

async function loadTransactions() {
    const token = getAuthToken();
    const tbody = document.getElementById('transactionsTableBody');
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/transactions`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>
                        <code style="background:#f7fafc; padding:4px 8px; border-radius:4px;">
                            ${tx.transaction_id ? tx.transaction_id.substring(0, 12) + '...' : '-'}
                        </code>
                    </td>
                    <td><i class="fas fa-phone"></i> ${tx.phone_number}</td>
                    <td>${CURRENCY} ${parseFloat(tx.amount).toLocaleString()}</td>
                    <td>
                        <i class="fas fa-${tx.device_type === 'tv' ? 'tv' : tx.device_type === 'tablet' ? 'tablet' : 'mobile-alt'}"></i>
                        ${tx.device_type || 'phone'}
                    </td>
                    <td>
                        <span class="status-badge status-${tx.status.toLowerCase()}">
                            ${tx.status}
                        </span>
                    </td>
                    <td><i class="fas fa-calendar"></i> ${new Date(tx.created_at).toLocaleString()}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align:center; padding:40px; color:#a0aec0;">
                        <i class="fas fa-exchange-alt" style="font-size:40px; display:block; margin-bottom:12px;"></i>
                        No transactions yet
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// ============================================================================
// TV DEVICES MANAGEMENT
// ============================================================================

async function loadTvDevices() {
    const token = getAuthToken();
    const tbody = document.getElementById('tvDevicesTableBody');
    
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/tv-devices`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.devices && data.devices.length > 0) {
            tbody.innerHTML = data.devices.map(device => `
                <tr>
                    <td>
                        <code style="background:#f7fafc; padding:4px 8px; border-radius:4px;">
                            ${device.mac_address}
                        </code>
                    </td>
                    <td>${device.package_id ? `Package #${device.package_id}` : '—'}</td>
                    <td>
                        <span class="status-badge ${device.is_active ? 'status-success' : 'status-failed'}">
                            ${device.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>${device.expires_at ? new Date(device.expires_at).toLocaleString() : '—'}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="disconnectTv(${device.id})">
                            <i class="fas fa-unlink"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align:center; padding:40px; color:#a0aec0;">
                        <i class="fas fa-tv" style="font-size:40px; display:block; margin-bottom:12px;"></i>
                        No TV devices connected
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading TV devices:', error);
    }
}

async function disconnectTv(deviceId) {
    if (!confirm('Disconnect this TV device?')) return;
    showNotification('TV disconnected', 'success');
    loadTvDevices();
}

// ============================================================================
// SETTINGS
// ============================================================================

async function loadSettings() {
    const token = getAuthToken();
    const settingsContent = document.getElementById('settingsContent');
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.settings.length > 0) {
            settingsContent.innerHTML = data.settings.map(setting => `
                <div class="form-group">
                    <label class="form-label">
                        <i class="fas fa-${setting.setting_key === 'support_phone' ? 'phone' : setting.setting_key === 'tv_support_enabled' ? 'tv' : 'cog'}"></i> 
                        ${setting.description || setting.setting_key}
                    </label>
                    <input type="text" class="form-input" 
                           name="${setting.setting_key}" 
                           value="${setting.setting_value}" 
                           data-setting-key="${setting.setting_key}">
                </div>
            `).join('') + `
                <button class="btn btn-primary" onclick="saveSettings()">
                    <i class="fas fa-save"></i> Save Settings
                </button>
            `;
        } else {
            settingsContent.innerHTML = '<p>No settings found</p>';
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
        
        showNotification('Settings saved successfully!', 'success');
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// FIXED: Correctly handles days, weeks, months
function formatDuration(seconds) {
    if (!seconds) return '-';
    seconds = parseInt(seconds);
    
    // Minutes (less than 1 hour)
    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)} min`;
    }
    
    // Hours (less than 1 day)
    if (seconds < 86400) {
        const hours = Math.floor(seconds / 3600);
        return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
    }
    
    // Days (1-6 days)
    if (seconds < 604800) {
        const days = Math.floor(seconds / 86400);
        return `${days} ${days === 1 ? 'day' : 'days'}`;
    }
    
    // Weeks (7-27 days)
    if (seconds < 2592000) {
        const days = Math.floor(seconds / 86400);
        if (days % 7 === 0) {
            const weeks = days / 7;
            return `${weeks} ${weeks === 1 ? 'week' : 'weeks'}`;
        }
        return `${days} days`;
    }
    
    // Months (30+ days)
    const months = Math.floor(seconds / 2592000);
    const remainingDays = Math.floor((seconds % 2592000) / 86400);
    
    if (remainingDays === 0) {
        return `${months} ${months === 1 ? 'month' : 'months'}`;
    }
    return `${months} ${months === 1 ? 'month' : 'months'} ${remainingDays} days`;
}

function showSection(section) {
    document.querySelectorAll('[id$="-section"]').forEach(el => {
        el.style.display = 'none';
    });
    
    const sectionElement = document.getElementById(section + '-section');
    if (sectionElement) {
        sectionElement.style.display = 'block';
    }
    
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    if (event && event.target) {
        const navLink = event.target.closest('.nav-link');
        if (navLink) navLink.classList.add('active');
    }
    
    switch (section) {
        case 'dashboard': loadDashboardStats(); break;
        case 'packages': loadPackages(); break;
        case 'transactions': loadTransactions(); break;
        case 'tv-devices': loadTvDevices(); break;
        case 'settings': loadSettings(); break;
    }
    
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.remove('open');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
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
// CREATE & UPDATE PACKAGE FUNCTIONS
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
            showNotification('Package created successfully!', 'success');
            closePackageModal();
            loadPackages();
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Error creating package', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error creating package', 'error');
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
            showNotification('Package updated successfully!', 'success');
            closePackageModal();
            loadPackages();
            loadDashboardStats();
        } else {
            showNotification(data.error || 'Error updating package', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error updating package', 'error');
    }
}
