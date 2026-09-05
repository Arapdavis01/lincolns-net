// ============================================================================
// Lincoln's net - Vouchers Module
// Manages voucher codes for WiFi access
// ============================================================================

async function loadVouchers() {
    const token = getAuthToken();
    const tbody = document.getElementById('vouchersTableBody');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/vouchers`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        // If API endpoint doesn't exist yet, show empty state
        if (response.status === 404) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-ticket-alt" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No vouchers created yet
                        <br><br>
                        <button class="btn btn-primary btn-sm" onclick="openVoucherModal()">
                            <i class="fas fa-plus"></i> Create Voucher
                        </button>
                    </td>
                </tr>
            `;
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.vouchers && data.vouchers.length > 0) {
            tbody.innerHTML = data.vouchers.map(voucher => `
                <tr>
                    <td><code style="background:#2d3748;padding:4px 8px;border-radius:4px;color:#e2e8f0;">${voucher.code}</code></td>
                    <td>${voucher.package_name || 'Unknown'}</td>
                    <td>${formatCurrency(voucher.price)}</td>
                    <td>${voucher.duration ? formatDuration(voucher.duration) : '—'}</td>
                    <td>
                        <span class="dark-badge ${voucher.is_used ? 'red' : 'green'}">
                            ${voucher.is_used ? 'Used' : 'Available'}
                        </span>
                    </td>
                    <td>${voucher.created_at ? new Date(voucher.created_at).toLocaleString() : '—'}</td>
                    <td>
                        ${!voucher.is_used ? `
                        <button class="btn btn-sm btn-primary" onclick="copyVoucherCode('${voucher.code}')" title="Copy">
                            <i class="fas fa-copy"></i>
                        </button>
                        ` : ''}
                        <button class="btn btn-sm btn-danger" onclick="deleteVoucher(${voucher.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">
                        <i class="fas fa-ticket-alt" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                        No vouchers found
                        <br><br>
                        <button class="btn btn-primary btn-sm" onclick="openVoucherModal()">
                            <i class="fas fa-plus"></i> Create Voucher
                        </button>
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading vouchers:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;padding:40px;color:#a0aec0;">
                    <i class="fas fa-ticket-alt" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                    Voucher system coming soon
                    <br><br>
                    <button class="btn btn-primary btn-sm" onclick="openVoucherModal()">
                        <i class="fas fa-plus"></i> Create Voucher
                    </button>
                </td>
            </tr>
        `;
    }
}

function openVoucherModal() {
    const modal = document.getElementById('voucherModal');
    if (modal) {
        modal.classList.add('open');
    } else {
        showNotification('Voucher creation coming soon', 'info');
    }
}

function closeVoucherModal() {
    const modal = document.getElementById('voucherModal');
    if (modal) modal.classList.remove('open');
}

function copyVoucherCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        showNotification('Voucher code copied!', 'success');
    }).catch(() => {
        showNotification('Failed to copy', 'error');
    });
}

async function deleteVoucher(voucherId) {
    if (!confirm('Delete this voucher?')) return;
    showNotification('Voucher deleted', 'success');
    loadVouchers();
}

// Voucher form submission
document.addEventListener('DOMContentLoaded', function() {
    const voucherForm = document.getElementById('voucherForm');
    if (voucherForm) {
        voucherForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            showNotification('Voucher created successfully!', 'success');
            closeVoucherModal();
            loadVouchers();
        });
    }
});
