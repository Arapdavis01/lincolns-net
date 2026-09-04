// ============================================================================
// Lincoln's net - Admin Panel (Single Page)
// ============================================================================

const BACKEND_URL = 'https://lincolns-net-backend.onrender.com';
const CURRENCY = 'KES';

// ============================================================================
// AUTH FUNCTIONS
// ============================================================================

function getAuthToken() {
    return localStorage.getItem('adminAuth');
}

function isLoggedIn() {
    return !!getAuthToken();
}

function logout() {
    localStorage.removeItem('adminAuth');
    showLogin();
}

function showLogin() {
    document.getElementById('loginView').style.display = 'flex';
    document.getElementById('dashboardView').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'flex';
    loadDashboardStats();
    loadPackages();
    loadTransactions();
}

// ============================================================================
// LOGIN
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const errorElement = document.getElementById('loginError');
            
            errorElement.style.display = 'none';
            
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
                    localStorage.setItem('adminAuth', btoa(username + ':' + password));
                    showDashboard();
                } else {
                    errorElement.textContent = data.message || 'Invalid credentials';
                    errorElement.style.display = 'block';
                }
            } catch (error) {
                console.error('Login error:', error);
                errorElement.textContent = 'Error connecting to server';
                errorElement.style.display = 'block';
            }
        });
    }
    
    // Check auth on page load
    if (isLoggedIn()) {
        showDashboard();
    } else {
        showLogin();
    }
});

// ============================================================================
// DASHBOARD
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
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// ============================================================================
// PACKAGES
// ============================================================================

async function loadPackages() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        const tbody = document.getElementById('packagesTableBody');
        
        if (data.success && data.packages.length > 0) {
            tbody.innerHTML = data.packages.map(pkg => `
                <tr>
                    <td><strong>${pkg.name}</strong></td>
                    <td>${CURRENCY} ${parseFloat(pkg.price).toLocaleString()}</td>
                    <td>${formatDuration(pkg.duration_seconds)}</td>
                    <td>${pkg.download_rate_limit} / ${pkg.upload_rate_limit}</td>
                    <td>
                        <span class="status-badge ${pkg.is_active ? 'status-success' : 'status-failed'}">
                            ${pkg.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})">🗑️</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px;">No packages found. Add your first package!</td></tr>';
        }
    } catch (error) {
        console.error('Error loading packages:', error);
    }
}

document.getElementById('packageForm')?.addEventListener('submit', async function(e) {
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
            alert('Package created successfully!');
            closePackageModal();
            loadPackages();
            loadDashboardStats();
        } else {
            alert(data.error || 'Error creating package');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error creating package');
    }
});

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
            alert('Package deactivated!');
            loadPackages();
            loadDashboardStats();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// ============================================================================
// TRANSACTIONS
// ============================================================================

async function loadTransactions() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/transactions`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        const tbody = document.getElementById('transactionsTableBody');
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>${tx.transaction_id ? tx.transaction_id.substring(0, 12) + '...' : '-'}</td>
                    <td>${tx.phone_number}</td>
                    <td>${CURRENCY} ${parseFloat(tx.amount).toLocaleString()}</td>
                    <td>
                        <span class="status-badge status-${tx.status.toLowerCase()}">${tx.status}</span>
                    </td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px;">No transactions yet</td></tr>';
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// ============================================================================
// UTILITY
// ============================================================================

function formatDuration(seconds) {
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} days`;
    return `${Math.floor(seconds / 2592000)} months`;
}

function showSection(section) {
    document.querySelectorAll('[id$="-section"]').forEach(el => {
        el.style.display = 'none';
    });
    document.getElementById(section + '-section').style.display = 'block';
    
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    event.target.closest('.nav-link').classList.add('active');
    
    if (section === 'dashboard') loadDashboardStats();
    if (section === 'packages') loadPackages();
    if (section === 'transactions') loadTransactions();
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function openPackageModal() {
    document.getElementById('packageModal').classList.add('open');
}

function closePackageModal() {
    document.getElementById('packageModal').classList.remove('open');
}
