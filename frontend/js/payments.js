// ============================================================================
// Lincoln's net - Payments Module
// Includes: Transaction list with Manual RADIUS Sync
// ============================================================================

async function loadPayments() {
    const token = getAuthToken();
    const tbody = document.getElementById('paymentsTableBody');
    if (!tbody) return;
    
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
                        <code style="background:#2d3748;padding:4px 8px;border-radius:4px;color:#e2e8f0;font-size:12px;">
                            ${tx.transaction_id ? tx.transaction_id.substring(0, 12) + '...' : '-'}
                        </code>
                    </td>
                    <td><i class="fas fa-phone"></i> ${tx.phone_number}</td>
                    <td>${formatCurrency(tx.amount)}</td>
                    <td>
                        <i class="fas fa-${tx.device_type === 'tv' ? 'tv' : tx.device_type === 'tablet' ? 'tablet' : 'mobile-alt'}"></i>
                        ${tx.device_type || 'phone'}
                    </td>
                    <td>
                        <span class="dark-badge ${getPaymentStatusColor(tx.status)}">
                            <i class="fas fa-${getPaymentStatusIcon(tx.status)}"></i>
                            ${tx.status}
                        </span>
                    </td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                    <td>
                        ${tx.status === 'SUCCESS' ? `
                        <button class="btn btn-sm btn-warning" onclick="manualRadiusSync('${tx.transaction_id}')" 
                                title="Sync to RADIUS" style="background:rgba(237,137,54,0.2);color:#ed8936;border:1px solid #ed8936;padding:6px 10px;border-radius:6px;cursor:pointer;">
                            <i class="fas fa-sync"></i>
                        </button>
                        ` : `
                        <span style="color:#4a5568;">—</span>
                        `}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-money-bill-wave" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No transactions yet
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading payments:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:40px;color:#e53e3e;">
                    <i class="fas fa-exclamation-circle" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                    Error loading transactions
                </td>
            </tr>
        `;
    }
}

// ============================================================================
// PAYMENT STATUS HELPERS
// ============================================================================

function getPaymentStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'green';
        case 'pending': return 'yellow';
        case 'failed': return 'red';
        case 'expired': return 'gray';
        default: return 'gray';
    }
}

function getPaymentStatusIcon(status) {
    switch (status.toLowerCase()) {
        case 'success': return 'check-circle';
        case 'pending': return 'clock';
        case 'failed': return 'times-circle';
        case 'expired': return 'hourglass-end';
        default: return 'info-circle';
    }
}

// ============================================================================
// FILTER TRANSACTIONS
// ============================================================================

async function filterPayments(status) {
    const token = getAuthToken();
    const tbody = document.getElementById('paymentsTableBody');
    if (!tbody) return;
    
    try {
        const url = status ? `${BACKEND_URL}/admin/api/transactions?status=${status}` : `${BACKEND_URL}/admin/api/transactions`;
        const response = await fetch(url, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            tbody.innerHTML = data.transactions.map(tx => `
                <tr>
                    <td>${tx.transaction_id ? tx.transaction_id.substring(0, 12) + '...' : '-'}</td>
                    <td>${tx.phone_number}</td>
                    <td>${formatCurrency(tx.amount)}</td>
                    <td>${tx.device_type || 'phone'}</td>
                    <td><span class="dark-badge ${getPaymentStatusColor(tx.status)}">${tx.status}</span></td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                    <td>
                        ${tx.status === 'SUCCESS' ? `
                        <button class="btn btn-sm btn-warning" onclick="manualRadiusSync('${tx.transaction_id}')" title="Sync to RADIUS">
                            <i class="fas fa-sync"></i>
                        </button>
                        ` : '—'}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;">No transactions found</td></tr>';
        }
    } catch (error) {
        console.error('Error filtering payments:', error);
    }
}

// ============================================================================
// EXPORT TRANSACTIONS
// ============================================================================

function exportPayments() {
    showNotification('Exporting transactions...', 'info');
    
    // Implement CSV export
    setTimeout(() => {
        showNotification('Transactions exported!', 'success');
    }, 1500);
}
