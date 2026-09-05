// ============================================================================
// Lincoln's net - Users Module
// ============================================================================

async function loadUsers() {
    const token = getAuthToken();
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/users`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.users.length > 0) {
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${user.phone_number}</td>
                    <td>${user.mac_address || '—'}</td>
                    <td>${user.total_spent ? formatCurrency(user.total_spent) : '—'}</td>
                    <td>${user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}</td>
                    <td><span class="dark-badge ${user.is_active ? 'green' : 'red'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:40px;">No users found</td></tr>';
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}
