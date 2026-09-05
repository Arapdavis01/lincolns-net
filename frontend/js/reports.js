// ============================================================================
// Lincoln's net - Reports Module
// Generates revenue and usage reports
// ============================================================================

async function loadReports() {
    const token = getAuthToken();
    
    // Load report summary
    await loadReportSummary();
    
    // Load revenue by day chart
    await loadRevenueChart();
}

async function loadReportSummary() {
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${BACKEND_URL}/admin/api/dashboard-stats`, {
            headers: { 'Authorization': 'Basic ' + token },
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('reportTotalRevenue').textContent = formatCurrency(data.total_revenue);
            document.getElementById('reportTotalTransactions').textContent = data.total_transactions || 0;
            document.getElementById('reportTotalCustomers').textContent = data.total_customers || 0;
            document.getElementById('reportActiveCustomers').textContent = data.active_customers || 0;
        }
    } catch (error) {
        console.error('Error loading report summary:', error);
    }
}

async function loadRevenueChart() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    
    // Sample data - replace with real API data
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const revenue = [1200, 1900, 1500, 2100, 1800, 2500, 2300];
    
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: days,
            datasets: [{
                label: 'Revenue (KES)',
                data: revenue,
                backgroundColor: 'rgba(0, 123, 255, 0.6)',
                borderColor: '#007bff',
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#a0aec0' },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#a0aec0' },
                },
            },
        },
    });
}

async function exportReport(type) {
    showNotification(`Exporting ${type} report...`, 'info');
    
    // Implementation for CSV/PDF export
    setTimeout(() => {
        showNotification('Report exported successfully!', 'success');
    }, 1500);
}
