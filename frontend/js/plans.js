// ============================================================================
// Lincoln's net - Plans/Packages Module (Complete)
// Includes: Stats, Search, Filter, Sort, View Toggle, Duplicate, Toggle Status
// ============================================================================

let plansCurrentView = 'table'; // 'table' or 'card'
let plansCurrentSearch = '';
let plansCurrentStatusFilter = '';
let plansCurrentTvFilter = '';
let plansCurrentSort = 'price_asc';
let plansList = [];

// ============================================================================
// MAIN LOADER
// ============================================================================

async function loadPlans() {
    await Promise.all([
        loadPlansStats(),
        loadPlansTable(),
    ]);
}

// ============================================================================
// PLANS STATS CARDS
// ============================================================================

async function loadPlansStats() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/plans-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('plansTotalCount').textContent = data.total_plans || 0;
            document.getElementById('plansActiveCount').textContent = data.active_plans || 0;
            document.getElementById('plansTvCount').textContent = data.tv_plans || 0;
            document.getElementById('plansAvgPrice').textContent = formatCurrency(data.avg_price);
            
            // Most popular plan
            const popularElement = document.getElementById('plansMostPopular');
            if (popularElement && data.most_popular) {
                popularElement.textContent = data.most_popular;
            }
        }
    } catch (error) {
        console.error('Error loading plans stats:', error);
    }
}

// ============================================================================
// PLANS TABLE/CARD VIEW
// ============================================================================

async function loadPlansTable() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.packages.length > 0) {
            plansList = data.packages;
            
            // Apply filters
            let filteredPlans = [...plansList];
            
            // Search filter
            if (plansCurrentSearch) {
                filteredPlans = filteredPlans.filter(pkg => 
                    pkg.name.toLowerCase().includes(plansCurrentSearch.toLowerCase())
                );
            }
            
            // Status filter
            if (plansCurrentStatusFilter === 'active') {
                filteredPlans = filteredPlans.filter(pkg => pkg.is_active);
            } else if (plansCurrentStatusFilter === 'inactive') {
                filteredPlans = filteredPlans.filter(pkg => !pkg.is_active);
            }
            
            // TV filter
            if (plansCurrentTvFilter === 'tv') {
                filteredPlans = filteredPlans.filter(pkg => pkg.supports_tv);
            } else if (plansCurrentTvFilter === 'no_tv') {
                filteredPlans = filteredPlans.filter(pkg => !pkg.supports_tv);
            }
            
            // Sort
            filteredPlans = sortPlansList(filteredPlans);
            
            // Render based on view
            if (plansCurrentView === 'table') {
                renderPlansTable(filteredPlans);
            } else {
                renderPlansCards(filteredPlans);
            }
        }
    } catch (error) {
        console.error('Error loading plans:', error);
    }
}

function sortPlansList(plans) {
    const sorted = [...plans];
    
    switch (plansCurrentSort) {
        case 'price_asc':
            sorted.sort((a, b) => parseFloat(a.price) - parseFloat(b.price));
            break;
        case 'price_desc':
            sorted.sort((a, b) => parseFloat(b.price) - parseFloat(a.price));
            break;
        case 'name_asc':
            sorted.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'name_desc':
            sorted.sort((a, b) => b.name.localeCompare(a.name));
            break;
        case 'duration_asc':
            sorted.sort((a, b) => a.duration_seconds - b.duration_seconds);
            break;
        case 'duration_desc':
            sorted.sort((a, b) => b.duration_seconds - a.duration_seconds);
            break;
    }
    
    return sorted;
}

// ============================================================================
// RENDER TABLE VIEW
// ============================================================================

function renderPlansTable(plans) {
    const tbody = document.getElementById('packagesTableBody');
    const cardContainer = document.getElementById('plansCardView');
    
    if (cardContainer) cardContainer.style.display = 'none';
    if (tbody) tbody.parentElement.parentElement.style.display = 'block';
    
    if (!tbody) return;
    
    if (plans.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center;padding:40px;color:#a0aec0;">
                    <i class="fas fa-box-open" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                    No plans found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = plans.map(pkg => `
        <tr onclick="viewPlanDetails(${pkg.id})" style="cursor: pointer;">
            <td>
                <strong>${pkg.name}</strong>
                ${pkg.description ? `<br><small style="color:#a0aec0;">${pkg.description}</small>` : ''}
            </td>
            <td><strong style="color:#48bb78;">${formatCurrency(pkg.price)}</strong></td>
            <td><i class="fas fa-clock"></i> ${formatDuration(pkg.duration_seconds)}</td>
            <td>
                <i class="fas fa-download"></i> ${pkg.download_rate_limit} 
                <i class="fas fa-upload"></i> ${pkg.upload_rate_limit}
            </td>
            <td>
                <span class="dark-badge ${pkg.max_users > 1 ? 'yellow' : 'gray'}">
                    <i class="fas fa-${pkg.max_users > 1 ? 'users' : 'user'}"></i> ${pkg.max_users}
                </span>
            </td>
            <td>
                ${pkg.supports_tv ? 
                    '<span class="dark-badge purple"><i class="fas fa-tv"></i> TV</span>' : 
                    '<span style="color:#4a5568;">—</span>'
                }
            </td>
            <td onclick="event.stopPropagation()">
                <label class="toggle-switch">
                    <input type="checkbox" ${pkg.is_active ? 'checked' : ''} 
                           onchange="togglePlanStatus(${pkg.id}, this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </td>
            <td onclick="event.stopPropagation()">
                <div style="display:flex;gap:6px;">
                    <button class="btn btn-sm btn-primary" onclick="viewPlanDetails(${pkg.id})" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="editPackage(${pkg.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-success" onclick="duplicatePlan(${pkg.id})" title="Duplicate">
                        <i class="fas fa-copy"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// ============================================================================
// RENDER CARD VIEW
// ============================================================================

function renderPlansCards(plans) {
    const cardContainer = document.getElementById('plansCardView');
    const tbody = document.getElementById('packagesTableBody');
    
    if (tbody) tbody.parentElement.parentElement.style.display = 'none';
    if (cardContainer) cardContainer.style.display = 'grid';
    
    if (!cardContainer) return;
    
    if (plans.length === 0) {
        cardContainer.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:40px;color:#a0aec0;">
                <i class="fas fa-box-open" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                No plans found
            </div>
        `;
        return;
    }
    
    cardContainer.innerHTML = plans.map(pkg => `
        <div class="plan-card" onclick="viewPlanDetails(${pkg.id})">
            <div class="plan-card-header">
                <h4>${pkg.name}</h4>
                <span class="dark-badge ${pkg.is_active ? 'green' : 'red'}">
                    ${pkg.is_active ? 'Active' : 'Inactive'}
                </span>
            </div>
            <div class="plan-card-price">${formatCurrency(pkg.price)}</div>
            <div class="plan-card-details">
                <span><i class="fas fa-clock"></i> ${formatDuration(pkg.duration_seconds)}</span>
                <span><i class="fas fa-download"></i> ${pkg.download_rate_limit}</span>
                <span><i class="fas fa-upload"></i> ${pkg.upload_rate_limit}</span>
            </div>
            <div class="plan-card-meta">
                <span class="dark-badge ${pkg.max_users > 1 ? 'yellow' : 'gray'}">
                    <i class="fas fa-users"></i> ${pkg.max_users} users
                </span>
                ${pkg.supports_tv ? '<span class="dark-badge purple"><i class="fas fa-tv"></i> TV</span>' : ''}
            </div>
            <div class="plan-card-actions" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-primary" onclick="editPackage(${pkg.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-sm btn-success" onclick="duplicatePlan(${pkg.id})">
                    <i class="fas fa-copy"></i> Duplicate
                </button>
                <button class="btn btn-sm btn-danger" onclick="deletePackage(${pkg.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// ============================================================================
// SEARCH & FILTERS
// ============================================================================

function searchPlans() {
    const searchInput = document.getElementById('plansSearchInput');
    if (!searchInput) return;
    plansCurrentSearch = searchInput.value.trim();
    loadPlansTable();
}

let plansSearchTimeout;
function onPlansSearchInput() {
    clearTimeout(plansSearchTimeout);
    plansSearchTimeout = setTimeout(() => searchPlans(), 500);
}

function filterPlansByStatus() {
    const filterSelect = document.getElementById('plansStatusFilter');
    if (!filterSelect) return;
    plansCurrentStatusFilter = filterSelect.value;
    loadPlansTable();
}

function filterPlansByTv() {
    const filterSelect = document.getElementById('plansTvFilter');
    if (!filterSelect) return;
    plansCurrentTvFilter = filterSelect.value;
    loadPlansTable();
}

function sortPlans() {
    const sortSelect = document.getElementById('plansSort');
    if (!sortSelect) return;
    plansCurrentSort = sortSelect.value;
    loadPlansTable();
}

// ============================================================================
// VIEW TOGGLE
// ============================================================================

function togglePlansView(view) {
    plansCurrentView = view;
    
    // Update toggle buttons
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.getElementById(`view-${view}`);
    if (activeBtn) activeBtn.classList.add('active');
    
    loadPlansTable();
}

// ============================================================================
// DUPLICATE PLAN
// ============================================================================

async function duplicatePlan(packageId) {
    if (!confirm('Duplicate this plan?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}/duplicate`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Plan duplicated successfully!', 'success');
            loadPlansTable();
            loadPlansStats();
        } else {
            showNotification(data.error || 'Failed to duplicate', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error duplicating plan', 'error');
    }
}

// ============================================================================
// TOGGLE PLAN STATUS
// ============================================================================

async function togglePlanStatus(packageId, isActive) {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}/toggle`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`Plan ${data.package.is_active ? 'activated' : 'deactivated'}!`, 'success');
            loadPlansStats();
        } else {
            showNotification(data.error || 'Failed to toggle', 'error');
            loadPlansTable(); // Revert
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error toggling plan', 'error');
    }
}

// ============================================================================
// VIEW PLAN DETAILS
// ============================================================================

async function viewPlanDetails(packageId) {
    const token = getAuthToken();
    
    try {
        // Get package details
        const pkgResponse = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const pkgData = await pkgResponse.json();
        
        // Get subscribers
        const subResponse = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}/subscribers`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const subData = await subResponse.json();
        
        if (pkgData.success) {
            const pkg = pkgData.package;
            
            document.getElementById('planDetailContent').innerHTML = `
                <div style="text-align:center;margin-bottom:20px;">
                    <div style="width:50px;height:50px;border-radius:12px;background:var(--gradient);display:flex;align-items:center;justify-content:center;margin:0 auto;font-size:24px;color:white;">
                        <i class="fas fa-box"></i>
                    </div>
                    <h3 style="color:#e2e8f0;margin:12px 0 4px;">${pkg.name}</h3>
                    <p style="color:#a0aec0;font-size:14px;">${pkg.description || 'No description'}</p>
                </div>
                
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;text-align:center;">
                        <small style="color:#a0aec0;">Price</small>
                        <div style="color:#48bb78;font-weight:700;font-size:20px;margin-top:4px;">${formatCurrency(pkg.price)}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;text-align:center;">
                        <small style="color:#a0aec0;">Duration</small>
                        <div style="color:#e2e8f0;font-weight:700;font-size:16px;margin-top:4px;">${formatDuration(pkg.duration_seconds)}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;text-align:center;">
                        <small style="color:#a0aec0;">Active Subscribers</small>
                        <div style="color:#007bff;font-weight:700;font-size:20px;margin-top:4px;">${subData.active_subscribers || 0}</div>
                    </div>
                    <div style="background:#1a1a27;padding:12px;border-radius:8px;text-align:center;">
                        <small style="color:#a0aec0;">Total Revenue</small>
                        <div style="color:#9f7aea;font-weight:700;font-size:16px;margin-top:4px;">${formatCurrency(subData.total_revenue)}</div>
                    </div>
                </div>
                
                <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-bottom:16px;">
                    <span class="dark-badge yellow"><i class="fas fa-download"></i> ${pkg.download_rate_limit}</span>
                    <span class="dark-badge yellow"><i class="fas fa-upload"></i> ${pkg.upload_rate_limit}</span>
                    <span class="dark-badge green"><i class="fas fa-users"></i> ${pkg.max_users} users</span>
                    ${pkg.supports_tv ? '<span class="dark-badge purple"><i class="fas fa-tv"></i> TV</span>' : ''}
                </div>
                
                <div style="display:flex;gap:12px;">
                    <button class="btn btn-primary btn-block" onclick="editPackage(${pkg.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-success btn-block" onclick="duplicatePlan(${pkg.id})">
                        <i class="fas fa-copy"></i> Duplicate
                    </button>
                </div>
            `;
            
            document.getElementById('planDetailModal').classList.add('open');
        }
    } catch (error) {
        console.error('Error loading plan details:', error);
        showNotification('Error loading details', 'error');
    }
}

function closePlanDetailModal() {
    const modal = document.getElementById('planDetailModal');
    if (modal) modal.classList.remove('open');
}

// ============================================================================
// PACKAGE MODAL FUNCTIONS (Shared - from admin.js)
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

async function editPackage(packageId) {
    const token = getAuthToken();
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        const data = await response.json();
        if (data.success) {
            closePlanDetailModal();
            openPackageModal(data.package);
            document.getElementById('packageForm').dataset.packageId = packageId;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function deletePackage(packageId) {
    if (!confirm('Deactivate this plan?')) return;
    const token = getAuthToken();
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/packages/${packageId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Basic ' + token },
        });
        const data = await response.json();
        if (data.success) {
            showNotification('Plan deactivated!', 'success');
            closePlanDetailModal();
            loadPlansTable();
            loadPlansStats();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

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
            showNotification('Plan created!', 'success');
            closePackageModal();
            loadPlansTable();
            loadPlansStats();
        }
    } catch (error) {
        console.error('Error:', error);
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
            showNotification('Plan updated!', 'success');
            closePackageModal();
            loadPlansTable();
            loadPlansStats();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}
