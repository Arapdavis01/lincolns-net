// ============================================================================
// Lincoln's net - Payments Module
// ============================================================================

async function loadPayments() {
    const token = getAuthToken();
    const tbody = document.getElementById('paymentsTableBody');
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
                    <td>${formatCurrency(tx.amount)}</td>
                    <td>${tx.device_type || 'phone'}</td>
                    <td><span class="status-badge status-${tx.status.toLowerCase()}">${tx.status}</span></td>
                    <td>${new Date(tx.created_at).toLocaleString()}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading payments:', error);
    }
}
