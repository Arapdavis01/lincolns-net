// ============================================================================
// Lincoln's net - Settings Module (Complete)
// Includes: Tabs, Save All, Reset, Change Password, Test Payment
// ============================================================================

let settingsCurrentTab = 'general';
let allSettingsData = {};

// ============================================================================
// MAIN LOADER
// ============================================================================

async function loadSettings() {
    await loadAllSettings();
    initializeSettingsTabs();
}

// ============================================================================
// LOAD ALL SETTINGS
// ============================================================================

async function loadAllSettings() {
    const token = getAuthToken();
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    // Show loading
    settingsContent.innerHTML = '<div style="text-align:center;padding:40px;"><div class="spinner"></div></div>';
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings/all`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            allSettingsData = data.categories || {};
            renderSettingsTabs();
            renderCurrentTab();
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        settingsContent.innerHTML = '<p style="color:#e53e3e;text-align:center;padding:40px;">Error loading settings</p>';
    }
}

// ============================================================================
// SETTINGS TABS
// ============================================================================

function initializeSettingsTabs() {
    const tabContainer = document.getElementById('settingsTabs');
    if (!tabContainer) return;
    
    const tabs = [
        { id: 'general', label: 'General', icon: 'fa-cog' },
        { id: 'payment', label: 'Payment', icon: 'fa-money-bill-wave' },
        { id: 'network', label: 'Network', icon: 'fa-wifi' },
        { id: 'features', label: 'Features', icon: 'fa-toggle-on' },
        { id: 'security', label: 'Security', icon: 'fa-shield-alt' },
    ];
    
    tabContainer.innerHTML = tabs.map(tab => `
        <button class="settings-tab ${tab.id === settingsCurrentTab ? 'active' : ''}" 
                onclick="switchSettingsTab('${tab.id}')" id="settings-tab-${tab.id}">
            <i class="fas ${tab.icon}"></i> ${tab.label}
        </button>
    `).join('');
}

function switchSettingsTab(tabId) {
    settingsCurrentTab = tabId;
    
    // Update tab buttons
    document.querySelectorAll('.settings-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeTab = document.getElementById(`settings-tab-${tabId}`);
    if (activeTab) activeTab.classList.add('active');
    
    renderCurrentTab();
}

function renderCurrentTab() {
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    const categorySettings = allSettingsData[settingsCurrentTab] || [];
    
    if (categorySettings.length === 0) {
        settingsContent.innerHTML = `
            <div style="text-align:center;padding:40px;color:#a0aec0;">
                <i class="fas fa-cog" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                No settings in this category
            </div>
        `;
        return;
    }
    
    let formHTML = '<form id="settingsForm">';
    
    categorySettings.forEach(setting => {
        formHTML += renderSettingField(setting);
    });
    
    formHTML += `
        <div style="display:flex;gap:12px;margin-top:24px;">
            <button type="button" class="btn btn-primary" onclick="saveCurrentTabSettings()">
                <i class="fas fa-save"></i> Save ${settingsCurrentTab.charAt(0).toUpperCase() + settingsCurrentTab.slice(1)} Settings
            </button>
        </div>
    </form>`;
    
    settingsContent.innerHTML = formHTML;
}

function renderSettingField(setting) {
    const key = setting.setting_key;
    const value = setting.setting_value || '';
    const description = setting.description || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const isSecret = setting.is_secret || false;
    
    // Feature toggles
    if (key.startsWith('enable_') || key.startsWith('tv_') || key === 'debug_mode' || key === 'maintenance_mode') {
        const isChecked = value === 'true' || value === '1';
        return `
            <div class="form-group">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <label class="form-label" style="color:var(--dark-gray);margin-bottom:0;">
                        <i class="fas fa-toggle-on" style="color:#007bff;"></i> ${description}
                    </label>
                    <label class="toggle-switch">
                        <input type="checkbox" data-setting-key="${key}" ${isChecked ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
        `;
    }
    
    // Secret fields (masked)
    if (isSecret || key.includes('secret') || key.includes('password') || key.includes('passkey')) {
        return `
            <div class="form-group">
                <label class="form-label" style="color:var(--dark-gray);">
                    <i class="fas fa-lock" style="color:#e53e3e;"></i> ${description}
                </label>
                <div class="input-group">
                    <span class="input-icon"><i class="fas fa-lock"></i></span>
                    <input type="password" class="form-input" value="${value}" 
                           data-setting-key="${key}" placeholder="••••••••"
                           style="background:var(--dark-sidebar);border:1px solid var(--dark-border);color:var(--dark-text);">
                    <button type="button" class="password-toggle" onclick="toggleSettingVisibility(this)">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    // Regular text field
    return `
        <div class="form-group">
            <label class="form-label" style="color:var(--dark-gray);">
                <i class="fas fa-cog" style="color:#007bff;"></i> ${description}
            </label>
            <input type="text" class="form-input" value="${value}" 
                   data-setting-key="${key}" placeholder="Enter ${description.toLowerCase()}"
                   style="background:var(--dark-sidebar);border:1px solid var(--dark-border);color:var(--dark-text);">
        </div>
    `;
}

// ============================================================================
// TOGGLE SECRET VISIBILITY
// ============================================================================

function toggleSettingVisibility(button) {
    const input = button.previousElementSibling;
    const icon = button.querySelector('i');
    
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// ============================================================================
// SAVE SETTINGS
// ============================================================================

async function saveCurrentTabSettings() {
    const token = getAuthToken();
    const formInputs = document.querySelectorAll('#settingsForm [data-setting-key]');
    
    const settingsToSave = {};
    
    formInputs.forEach(input => {
        if (input.type === 'checkbox') {
            settingsToSave[input.dataset.settingKey] = input.checked ? 'true' : 'false';
        } else {
            settingsToSave[input.dataset.settingKey] = input.value;
        }
    });
    
    if (Object.keys(settingsToSave).length === 0) {
        showNotification('No settings to save', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings/save-all`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify({ settings: settingsToSave }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Settings saved successfully!', 'success');
            loadAllSettings();
        } else {
            showNotification(data.error || 'Error saving settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

// Legacy function for backward compatibility
async function saveSettings() {
    await saveCurrentTabSettings();
}

// ============================================================================
// RESET SETTINGS
// ============================================================================

async function resetSettings() {
    if (!confirm('Reset all settings to defaults?')) return;
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings/reset`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Settings reset to defaults!', 'success');
            loadAllSettings();
        } else {
            showNotification(data.error || 'Error resetting', 'error');
        }
    } catch (error) {
        console.error('Error resetting:', error);
        showNotification('Error resetting settings', 'error');
    }
}

// ============================================================================
// CHANGE PASSWORD
// ============================================================================

async function changePassword() {
    const currentPassword = document.getElementById('currentPassword')?.value || '';
    const newPassword = document.getElementById('newPassword')?.value || '';
    const confirmPassword = document.getElementById('confirmPassword')?.value || '';
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        showNotification('Please fill all password fields', 'warning');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showNotification('New passwords do not match', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        showNotification('Password must be at least 6 characters', 'warning');
        return;
    }
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings/change-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + token,
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Password changed successfully!', 'success');
            // Clear password fields
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } else {
            showNotification(data.error || 'Error changing password', 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showNotification('Error changing password', 'error');
    }
}

// ============================================================================
// TEST PAYMENT CONNECTION
// ============================================================================

async function testPaymentConnection() {
    const token = getAuthToken();
    const testButton = document.getElementById('testPaymentBtn');
    
    if (testButton) {
        testButton.disabled = true;
        testButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
    }
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings/test-payment`, {
            method: 'POST',
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message || 'Payment gateway is reachable!', 'success');
        } else {
            showNotification(data.message || data.error || 'Connection failed', 'error');
        }
    } catch (error) {
        console.error('Test payment error:', error);
        showNotification('Error testing payment connection', 'error');
    } finally {
        if (testButton) {
            testButton.disabled = false;
            testButton.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
        }
    }
}

// ============================================================================
// RENDER SECURITY TAB (Password Change)
// ============================================================================

function renderSecurityTab() {
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    settingsContent.innerHTML = `
        <div class="form-section">
            <h3 class="form-section-title" style="color:var(--dark-text);">
                <i class="fas fa-key" style="color:#e53e3e;"></i> Change Admin Password
            </h3>
            
            <div class="form-group">
                <label class="form-label" style="color:var(--dark-gray);">
                    <i class="fas fa-lock" style="color:#e53e3e;"></i> Current Password
                </label>
                <input type="password" class="form-input" id="currentPassword" 
                       placeholder="Enter current password"
                       style="background:var(--dark-sidebar);border:1px solid var(--dark-border);color:var(--dark-text);">
            </div>
            
            <div class="form-group">
                <label class="form-label" style="color:var(--dark-gray);">
                    <i class="fas fa-key" style="color:#e53e3e;"></i> New Password
                </label>
                <input type="password" class="form-input" id="newPassword" 
                       placeholder="Enter new password (min 6 characters)"
                       style="background:var(--dark-sidebar);border:1px solid var(--dark-border);color:var(--dark-text);">
            </div>
            
            <div class="form-group">
                <label class="form-label" style="color:var(--dark-gray);">
                    <i class="fas fa-check" style="color:#48bb78;"></i> Confirm New Password
                </label>
                <input type="password" class="form-input" id="confirmPassword" 
                       placeholder="Confirm new password"
                       style="background:var(--dark-sidebar);border:1px solid var(--dark-border);color:var(--dark-text);">
            </div>
            
            <button class="btn btn-primary" onclick="changePassword()">
                <i class="fas fa-key"></i> Change Password
            </button>
        </div>
    `;
}

// ============================================================================
// RENDER PAYMENT TAB (with Test Connection)
// ============================================================================

function renderPaymentTab() {
    const categorySettings = allSettingsData['payment'] || [];
    
    if (categorySettings.length === 0) {
        return;
    }
    
    let formHTML = '<form id="settingsForm">';
    
    categorySettings.forEach(setting => {
        formHTML += renderSettingField(setting);
    });
    
    formHTML += `
        <div style="display:flex;gap:12px;margin-top:24px;flex-wrap:wrap;">
            <button type="button" class="btn btn-primary" onclick="saveCurrentTabSettings()">
                <i class="fas fa-save"></i> Save Payment Settings
            </button>
            <button type="button" class="btn btn-success" id="testPaymentBtn" onclick="testPaymentConnection()">
                <i class="fas fa-plug"></i> Test Connection
            </button>
        </div>
    </form>`;
    
    const settingsContent = document.getElementById('settingsContent');
    if (settingsContent) settingsContent.innerHTML = formHTML;
}

// ============================================================================
// OVERRIDE renderCurrentTab FOR SPECIAL TABS
// ============================================================================

function renderCurrentTab() {
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    // Special handling for security tab
    if (settingsCurrentTab === 'security') {
        renderSecurityTab();
        return;
    }
    
    // Special handling for payment tab (with test button)
    if (settingsCurrentTab === 'payment') {
        renderPaymentTab();
        return;
    }
    
    // Regular tabs
    const categorySettings = allSettingsData[settingsCurrentTab] || [];
    
    if (categorySettings.length === 0) {
        settingsContent.innerHTML = `
            <div style="text-align:center;padding:40px;color:#a0aec0;">
                <i class="fas fa-cog" style="font-size:40px;display:block;margin-bottom:12px;"></i>
                No settings in this category
            </div>
        `;
        return;
    }
    
    let formHTML = '<form id="settingsForm">';
    
    categorySettings.forEach(setting => {
        formHTML += renderSettingField(setting);
    });
    
    formHTML += `
        <div style="display:flex;gap:12px;margin-top:24px;">
            <button type="button" class="btn btn-primary" onclick="saveCurrentTabSettings()">
                <i class="fas fa-save"></i> Save Settings
            </button>
        </div>
    </form>`;
    
    settingsContent.innerHTML = formHTML;
}
