// ============================================================================
// Lincoln's net - Plans/Packages Module
// ============================================================================

async function loadPlans() {
    await loadPackagesTable();
}

async function loadPackagesTable() {
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
                    <td>${formatCurrency(pkg.price)}</td>
                    <td>${formatDuration(pkg.duration_seconds)}</td>
                    <td>${pkg.download_rate_limit} / ${pkg.upload_rate_limit}</td>
                    <td>${pkg.max_users || 1}</td>
                    <td>${pkg.supports_tv ? 'Yes' : '—'}</td>
                    <td><span class="status-badge ${pkg.is_active ? 'status-success' : 'status-failed'}">${pkg.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editPackage(${pkg.id})"><i class="fas fa-edit"></i></button>
                        <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading packages:', error);
    }
}

// Package modal functions
function openPackageModal(packageData = null) { /* ... */ }
function closePackageModal() { /* ... */ }
async function editPackage(packageId) { /* ... */ }
async function deletePackage(packageId) { /* ... */ }
async function createPackage(formData) { /* ... */ }
async function updatePackage(packageId, formData) { /* ... */ }
