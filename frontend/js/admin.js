// ============================================================================
// Lincoln's net - Admin Panel JavaScript (Complete)
// Single page application with login and dashboard
// ============================================================================

const BACKEND_URL = 'https://lincolns-net-backend.onrender.com';
const CURRENCY = 'KES';

// ============================================================================
// AUTHENTICATION FUNCTIONS
// ============================================================================

/**
 * Get the admin authentication token from localStorage
 * @returns {string|null} The auth token or null if not logged in
 */
function getAuthToken() {
    return localStorage.getItem('adminAuth');
}

/**
 * Check if admin is currently logged in
 * @returns {boolean} True if logged in
 */
function isLoggedIn() {
    return !!getAuthToken();
}

/**
 * Set the authentication token in localStorage
 * @param {string} username - Admin username
 * @param {string} password - Admin password
 */
function setAuthToken(username, password) {
    const token = btoa(username + ':' + password);
    localStorage.setItem('adminAuth', token);
}

/**
 * Logout the admin user
 */
function logout() {
    localStorage.removeItem('adminAuth');
    showLogin();
    
    // Show logout notification
    showNotification('You have been logged out', 'info');
}

/**
 * Show the login view and hide dashboard
 */
function showLogin() {
    document.getElementById('loginView').style.display = 'flex';
    document.getElementById('dashboardView').style.display = 'none';
    
    // Clear password field
    const passwordField = document.getElementById('password');
    if (passwordField) {
        passwordField.value = '';
    }
    
    // Focus on username
    const usernameField = document.getElementById('username');
    if (usernameField) {
        usernameField.focus();
    }
}

/**
 * Show the dashboard view and hide login
 */
function showDashboard() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'flex';
    
    // Load all dashboard data
    loadDashboardStats();
    loadPackages();
    loadTransactions();
}

// ============================================================================
// PASSWORD TOGGLE
// ============================================================================

/**
 * Toggle password visibility for the login form
 */
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

/**
 * Handle login form submission
 * @param {Event} e - Form submit event
 */
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorElement = document.getElementById('loginError');
    const errorText = document.getElementById('loginErrorText');
    const loginButton = document.getElementById('loginButton');
    
    // Reset error
    errorElement.style.display = 'none';
    
    // Validate inputs
    if (!username || !password) {
        errorText.textContent = 'Please enter both username and password';
        errorElement.style.display = 'flex';
        return;
    }
    
    // Disable button and show loading
    loginButton.disabled = true;
    loginButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Store auth token
            setAuthToken(username, password);
            
            // Show success notification
            showNotification('Login successful!', 'success');
            
            // Show dashboard
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
        // Re-enable button
        loginButton.disabled = false;
        loginButton.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
    }
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

/**
 * Show a notification message
 * @param {string} message - Message to display
 * @param {string} type - Notification type (success, error, info, warning)
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

/**
 * Get the appropriate icon for notification type
 */
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

/**
 * Load dashboard statistics from backend
 */
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
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('Error loading dashboard data', 'error');
    }
}

// ============================================================================
// PACKAGE MANAGEMENT
// ============================================================================

/**
 * Load packages from backend
 */
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
                        <span class="status-badge ${pkg.is_active ? 'status-success' : 'status-failed'}">
                            <i class="fas fa-${pkg.is_active ? 'check-circle' : 'times-circle'}"></i>
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
                    <td colspan="6" style="text-align:center; padding:40px; color:#a0aec0;">
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

/**
 * Create a new package
 */
async function createPackage(e) {
    e.preventDefault();
    
    const token = getAuthToken();
    const formData = {
        name: document.getElementById('packageName').value.trim(),
        description: document.getElementById('packageDescription').value.trim(),
        price: parseFloat(document.getElementById('packagePrice').value),
        duration_seconds: parseInt(document.getElementById('packageDuration').value),
        download_rate_limit: document.getElementById('packageDownload').value.trim(),
        upload_rate_limit: document.getElementById('packageUpload').value.trim(),
    };
    
    // Validate
    if (!formData.name || !formData.price || !formData.duration_seconds) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
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

/**
 * Edit a package
 */
async function editPackage(packageId) {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            const pkg = data.package;
            
            // Fill form with package data
            document.getElementById('packageName').value = pkg.name;
            document.getElementById('packageDescription').value = pkg.description || '';
            document.getElementById('packagePrice').value = pkg.price;
            document.getElementById('packageDuration').value = pkg.duration_seconds;
            document.getElementById('packageDownload').value = pkg.download_rate_limit;
            document.getElementById('packageUpload').value = pkg.upload_rate_limit;
            
            // Store package ID for update
            document.getElementById('packageForm').dataset.packageId = packageId;
            
            // Change modal title
            document.querySelector('#packageModal .modal-header h2').innerHTML = 
                '<i class="fas fa-edit"></i> Edit Package';
            
            openPackageModal();
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error loading package details', 'error');
    }
}

/**
 * Update an existing package
 */
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

/**
 * Delete (deactivate) a package
 */
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

/**
 * Load transactions from backend
 */
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
                    <td>
                        <i class="fas fa-phone"></i> ${tx.phone_number}
                    </td>
                    <td>${CURRENCY} ${parseFloat(tx.amount).toLocaleString()}</td>
                    <td>
                        <span class="status-badge status-${tx.status.toLowerCase()}">
                            <i class="fas fa-${getStatusIcon(tx.status)}"></i>
                            ${tx.status}
                        </span>
                    </td>
                    <td>
                        <i class="fas fa-calendar"></i> ${new Date(tx.created_at).toLocaleString()}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align:center; padding:40px; color:#a0aec0;">
                        <i class="fas fa-exchange-alt" style="font-size:40px; display:block; margin-bottom:12px;"></i>
                        No transactions yet
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        showNotification('Error loading transactions', 'error');
    }
}

/**
 * Get status icon
 */
function getStatusIcon(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'check-circle';
        case 'pending': return 'clock';
        case 'failed': return 'times-circle';
        case 'expired': return 'hourglass-end';
        default: return 'info-circle';
    }
}

// ============================================================================
// SETTINGS
// ============================================================================

/**
 * Load system settings
 */
async function loadSettings() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        const settingsContent = document.getElementById('settingsContent');
        
        if (data.success && data.settings.length > 0) {
            settingsContent.innerHTML = data.settings.map(setting => `
                <div class="form-group">
                    <label class="form-label">
                        <i class="fas fa-cog"></i> ${setting.description || setting.setting_key}
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

/**
 * Save system settings
 */
async function saveSettings() {
    const token = getAuthToken();
    const settingsInputs = document.querySelectorAll('[data-setting-key]');
    
    try {
        for (const input of settingsInputs) {
            const response = await fetch(`${BACKEND_URL}/admin/api/settings`, {
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

/**
 * Format duration in seconds to human-readable
 */
function formatDuration(seconds) {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds} seconds`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days`;
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)} weeks`;
    return `${Math.floor(seconds / 2592000)} months`;
}

/**
 * Show a specific section in the dashboard
 */
function showSection(section) {
    // Hide all sections
    document.querySelectorAll('[id$="-section"]').forEach(el => {
        el.style.display = 'none';
    });
    
    // Show selected section
    const sectionElement = document.getElementById(section + '-section');
    if (sectionElement) {
        sectionElement.style.display = 'block';
    }
    
    // Update navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    if (event && event.target) {
        const navLink = event.target.closest('.nav-link');
        if (navLink) {
            navLink.classList.add('active');
        }
    }
    
    // Load data for section
    switch (section) {
        case 'dashboard':
            loadDashboardStats();
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
    
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
    }
}

/**
 * Toggle sidebar on mobile
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

/**
 * Open package modal
 */
function openPackageModal() {
    const modal = document.getElementById('packageModal');
    if (modal) {
        modal.classList.add('open');
    }
}

/**
 * Close package modal
 */
function closePackageModal() {
    const modal = document.getElementById('packageModal');
    if (modal) {
        modal.classList.remove('open');
        
        // Reset form
        const form = document.getElementById('packageForm');
        if (form) {
            form.reset();
            delete form.dataset.packageId;
        }
        
        // Reset modal title
        const title = document.querySelector('#packageModal .modal-header h2');
        if (title) {
            title.innerHTML = '<i class="fas fa-plus-circle"></i> Add Package';
        }
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Handle login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Handle package form
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
            };
            
            if (packageId) {
                updatePackage(packageId, formData);
            } else {
                createPackage(e);
            }
        });
    }
    
    // Close modals when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('open');
        }
    });
    
    // Check authentication on page load
    if (isLoggedIn()) {
        showDashboard();
    } else {
        showLogin();
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById('sidebar');
            const menuBtn = document.getElementById('menuBtn');
            
            if (sidebar && sidebar.classList.contains('open') &&
                !sidebar.contains(event.target) &&
                menuBtn && !menuBtn.contains(event.target)) {
                sidebar.classList.remove('open');
            }
        }
    });
});
