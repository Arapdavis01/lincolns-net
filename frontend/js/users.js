// ============================================================================
// Lincoln's net - Users Module (Complete)
// Includes: Search, Stats, Detail Modal, Block/Unblock, Pagination, Export
// ============================================================================

let currentPage = 1;
const usersPerPage = 10;
let totalUsersCount = 0;
let currentSearchQuery = '';
let currentStatusFilter = '';

// ============================================================================
// MAIN LOADER
// ============================================================================

async function loadUsers() {
    await Promise.all([
        loadUserStats(),
        loadUsersTable(),
    ]);
}

// ============================================================================
// USER STATS CARDS
// ============================================================================

async function loadUserStats() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/users-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('totalUsersCount').textContent = data.total_users || 0;
            document.getElementById('activeUsersCount').textContent = data.active_users || 0;
            document.getElementById('newUsersToday').textContent = data.new_today || 0;
            document.getElementById('usersRevenue').textContent = formatCurrency(data.total_revenue);
        }
    } catch (error) {
        console.error('Error loading user stats:', error);
    }
}

// ============================================================================
// USERS TABLE
// ============================================================================

async function loadUsersTable() {
    const token = getAuthToken();
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    // Show loading
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;"><div class="spinner"></div></td></tr>';
    
    try {
        // Build query URL
        let url = `${BACKEND_URL}/admin/api/users?limit=${usersPerPage}&offset=${(currentPage - 1) * usersPerPage}`;
        
        if (currentSearchQuery) {
            url += `&search=${encodeURIComponent(currentSearchQuery)}`;
        }
        
        if (currentStatusFilter) {
            url += `&status=${currentStatusFilter}`;
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
            totalUsersCount = data.total || data.users.length;
            
            tbody.innerHTML = data.users.map(user => `
                <tr onclick="viewUserDetails('${user.phone_number}')" style="cursor: pointer;">
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="user-avatar-sm">
                                ${getInitials(user.phone_number)}
                            </div>
                            <span>${user.phone_number}</span>
                        </div>
                    </td>
                    <td>
                        <code style="background:#2d3748;padding:4px 8px;border-radius:4px;color:#e2e8f0;font-size:12px;">
                            ${user.mac_address || '—'}
                        </code>
                    </td>
                    <td>
                        <i class="fas fa-${user.device_type === 'tv' ? 'tv' : user.device_type === 'tablet' ? 'tablet' : 'mobile-alt'}"></i>
                        ${user.device_type || 'phone'}
                    </td>
                    <td>${formatCurrency(user.total_spent)}</td>
                    <td>${user.transaction_count || 0}</td>
                    <td>${user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}</td>
                    <td>
                        <span class="dark-badge ${user.is_active ? 'green' : 'gray'}">
                            <i class="fas fa-circle"></i> ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td onclick="event.stopPropagation()">
                        <div style="display:flex;gap:6px;">
                            <button class="btn btn-sm btn-primary" onclick="viewUserDetails('${user.phone_number}')" title="View">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${user.is_active ? `
                            <button class="btn btn-sm btn-danger" onclick="blockUser('${user.phone_number}')" title="Block">
                                <i class="fas fa-ban"></i>
                            </button>
                            ` : `
                            <button class="btn btn-sm btn-success" onclick="unblockUser('${user.phone_number}')" title="Unblock">
                                <i class="fas fa-check"></i>
                            </button>
                            `}
                        </div>
                    </td>
                </tr>
            `).join('');
            
            // Update pagination
            renderPagination();
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-users" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No users found
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:40px;color:#e53e3e;">Error loading users</td></tr>';
    }
}

// ============================================================================
// SEARCH
// ============================================================================

function searchUsers() {
    const searchInput = document.getElementById('userSearchInput');
    if (!searchInput) return;
    
    currentSearchQuery = searchInput.value.trim();
    currentPage = 1;
    loadUsersTable();
}

// Debounced search on input
let searchTimeout;
function onUserSearchInput() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchUsers();
    }, 500);
}

// ============================================================================
// FILTER BY STATUS
// ============================================================================

function filterUsersByStatus() {
    const filterSelect = document.getElementById('userStatusFilter');
    if (!filterSelect) return;
    
    currentStatusFilter = filterSelect.value;
    currentPage = 1;
    loadUsersTable();
}

// ============================================================================
// PAGINATION
// ============================================================================

function renderPagination() {
    const paginationContainer = document.getElementById('usersPagination');
    if (!paginationContainer) return;
    
    const totalPages = Math.ceil(totalUsersCount / usersPerPage);
    
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }
    
    let paginationHTML = `
        <button class="pagination-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i> Prev
        </button>
    `;
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            paginationHTML += `
                <button class="pagination-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">
                    ${i}
                </button>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            paginationHTML += '<span class="pagination-dots">...</span>';
        }
    }
    
    paginationHTML += `
        <button class="pagination-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
            Next <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    paginationHTML += `<span class="pagination-info">Page ${currentPage} of ${totalPages} (${totalUsersCount} users)</span>`;
    
    paginationContainer.innerHTML = paginationHTML;
}

function goToPage(page) {
    currentPage = page;
    loadUsersTable();
}

// ============================================================================
// USER DETAILS MODAL
// ============================================================================

async function viewUserDetails(phoneNumber) {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/users/${encodeURIComponent(phoneNumber)}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            const user = data.user;
            
            // Fill modal content
            document.getElementById('userDetailContent').innerHTML = `
                <div style="text-align:center;margin-bottom:20px;">
                    <div class="user-detail-avatar">
                        ${getInitials(user.phone_number)}
                    </div>
                    <h3 style="color:#e2e8f0;margin:12px 0 4px;">${user.phone_number}</h3>
                    <span class="dark-badge ${user.is_active ? 'green' : 'gray'}">
                        <i class="fas fa-circle"></i> ${user.is_active ? 'Active' : 'Inactive'}
                    </span>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Total Spent</small>
                        <div style="color:#e2e8f0;font-weight:700;font-size:18px;">${formatCurrency(user.total_spent)}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Transactions</small>
                        <div style="color:#e2e8f0;font-weight:700;font-size:18px;">${user.transaction_count}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">First Seen</small>
                        <div style="color:#e2e8f0;font-size:14px;">${user.first_seen ? new Date(user.first_seen).toLocaleString() : '—'}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;">
                        <small style="color:#a0aec0;">Last Seen</small>
                        <div style="color:#e2e8f0;font-size:14px;">${user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}</div>
                    </div>
                </div>
                
                ${user.active_session ? `
                <div style="background:rgba(72,187,120,0.1);padding:12px;border-radius:8px;margin-bottom:16px;">
                    <small style="color:#48bb78;font-weight:600;">ACTIVE SESSION</small>
                    <div style="color:#e2e8f0;font-size:14px;margin-top:4px;">
                        Package: ${user.active_session.package_name}<br>
                        Expires: ${new Date(user.active_session.expires_at).toLocaleString()}
                    </div>
                </div>
                ` : ''}
                
                <h4 style="color:#a0aec0;margin-bottom:12px;">Recent Transactions</h4>
                <div style="max-height:200px;overflow-y:auto;">
                    ${data.transactions.map(tx => `
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #3a3a4d;">
                            <div>
                                <div style="color:#e2e8f0;font-size:13px;">${tx.package_name}</div>
                                <small style="color:#a0aec0;">${new Date(tx.created_at).toLocaleString()}</small>
                            </div>
                            <div style="text-align:right;">
                                <div style="color:#e2e8f0;font-weight:600;">${formatCurrency(tx.amount)}</div>
                                <span class="dark-badge ${tx.status === 'SUCCESS' ? 'green' : tx.status === 'PENDING' ? 'yellow' : 'red'}">${tx.status}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            
            // Store phone for actions
            document.getElementById('userDetailModal').dataset.phoneNumber = phoneNumber;
            
            // Open modal
            document.getElementById('userDetailModal').classList.add('open');
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        showNotification('Error loading user details', 'error');
    }
}

function closeUserDetailModal() {
    const modal = document.getElementById('userDetailModal');
    if (modal) modal.classList.remove('open');
}

// ============================================================================
// BLOCK / UNBLOCK USER
// ============================================================================

async function blockUser(phoneNumber) {
    if (!confirm(`Block user ${phoneNumber}? This will disconnect them.`)) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/users/${encodeURIComponent(phoneNumber)}/block`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('User blocked successfully!', 'success');
            loadUsersTable();
            loadUserStats();
        } else {
            showNotification(data.error || 'Failed to block user', 'error');
        }
    } catch (error) {
        console.error('Error blocking user:', error);
        showNotification('Error blocking user', 'error');
    }
}

async function unblockUser(phoneNumber) {
    if (!confirm(`Unblock user ${phoneNumber}?`)) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/users/${encodeURIComponent(phoneNumber)}/unblock`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('User unblocked successfully!', 'success');
            loadUsersTable();
        }
    } catch (error) {
        console.error('Error unblocking user:', error);
        showNotification('Error unblocking user', 'error');
    }
}

// ============================================================================
// EXPORT USERS
// ============================================================================

function exportUsers() {
    const token = getAuthToken();
    
    showNotification('Exporting users...', 'info');
    
    fetch(`${BACKEND_URL}/admin/api/users?limit=1000`, {
        headers: { 'Authorization': 'Basic ' + token },
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.users.length > 0) {
            // Create CSV content
            let csv = 'Phone Number,MAC Address,Device Type,Total Spent,Transactions,Last Seen,Status\n';
            
            data.users.forEach(user => {
                csv += `${user.phone_number},${user.mac_address || 'N/A'},${user.device_type},${user.total_spent},${user.transaction_count},${user.last_seen || 'N/A'},${user.is_active ? 'Active' : 'Inactive'}\n`;
            });
            
            // Download CSV
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `users_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
            
            showNotification('Users exported successfully!', 'success');
        }
    })
    .catch(error => {
        console.error('Export error:', error);
        showNotification('Error exporting users', 'error');
    });
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getInitials(phoneNumber) {
    if (!phoneNumber) return '?';
    
    // Remove + and country code for initials
    const clean = phoneNumber.replace(/^\+?254/, '').replace(/^0/, '');
    return clean.substring(0, 2).toUpperCase();
}
