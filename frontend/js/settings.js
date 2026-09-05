// ============================================================================
// Lincoln's net - Settings Module
// ============================================================================

async function loadSettings() {
    const token = getAuthToken();
    const settingsContent = document.getElementById('settingsContent');
    if (!settingsContent) return;
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/settings`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success && data.settings.length > 0) {
            settingsContent.innerHTML = data.settings.map(setting => `
                <div class="form-group">
                    <label class="form-label">
                        <i class="fas fa-cog"></i> ${setting.description || setting.setting_key}
                    </label>
                    <input type="text" class="form-input" name="${setting.setting_key}" 
                           value="${setting.setting_value}" data-setting-key="${setting.setting_key}">
                </div>
            `).join('') + `
                <button class="btn btn-primary" onclick="saveSettings()">
                    <i class="fas fa-save"></i> Save Settings
                </button>
            `;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() { /* ... */ }
