/**
 * app.js
 * ------
 * Custom JavaScript for the AI Resume Screening System.
 * Handles: Chart.js initialization, sidebar interactions, form enhancements,
 * dashboard auto-refresh polling, and real-time activity updates.
 */

'use strict';

// ============================================================
// DOM Ready
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initDashboardAutoRefresh();
});

// ============================================================
// Dashboard Auto-Refresh System
// ============================================================

let dashboardRefreshInterval = null;
let lastActivityCount = 0;

/**
 * Initialize dashboard auto-refresh polling.
 * Polls /api/kpis every 5 seconds to update KPIs, charts, and activity.
 */
function initDashboardAutoRefresh() {
    // Only run on dashboard page
    const pipelineChart = document.getElementById('pipelineChart');
    if (!pipelineChart) return;

    // Initial data fetch
    refreshDashboardData();

    // Set up polling interval (every 5 seconds)
    dashboardRefreshInterval = setInterval(refreshDashboardData, 5000);
}

/**
 * Fetch latest dashboard data from the API and update the UI.
 */
function refreshDashboardData() {
    fetch('/api/kpis')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.error) {
                console.warn('Dashboard refresh error:', data.error);
                return;
            }
            updateKPIs(data);
            updateCharts(data);
            updateRecentAnalyzed(data);
            updateActivityFeed(data);
            updateLastRefreshTime();
        })
        .catch(error => {
            console.debug('Dashboard auto-refresh unavailable (user may be on another page):', error);
        });
}

/**
 * Update KPI values on the dashboard.
 */
function updateKPIs(data) {
    const kpis = data.kpis;
    if (!kpis) return;

    const totalEl = document.querySelector('.kpi-total .kpi-value');
    const shortlistedEl = document.querySelector('.kpi-shortlisted .kpi-value');
    const rejectedEl = document.querySelector('.kpi-rejected .kpi-value');
    const pendingEl = document.querySelector('.kpi-pending .kpi-value');

    if (totalEl && kpis.total !== undefined) totalEl.textContent = kpis.total;
    if (shortlistedEl && kpis.shortlisted !== undefined) shortlistedEl.textContent = kpis.shortlisted;
    if (rejectedEl && kpis.rejected !== undefined) rejectedEl.textContent = kpis.rejected;
    if (pendingEl && data.pending_count !== undefined) pendingEl.textContent = data.pending_count;

    // Update average score if element exists
    const avgScoreEl = document.querySelector('.kpi-avg-score .kpi-value');
    if (avgScoreEl && kpis.avg_score !== undefined) {
        avgScoreEl.textContent = kpis.avg_score + '%';
    }
}

/**
 * Update Chart.js charts with new data.
 */
function updateCharts(data) {
    const kpis = data.kpis;
    if (!kpis) return;

    // Update pipeline doughnut chart
    if (window.pipelineChartInstance) {
        window.pipelineChartInstance.data.datasets[0].data = [
            kpis.shortlisted || 0,
            kpis.rejected || 0,
            data.pending_count || 0
        ];
        window.pipelineChartInstance.update('none');
    }

    // Update rejection reasons bar chart
    if (window.rejectionChartInstance) {
        const reasons = data.rejection_reasons || {};
        const labels = Object.keys(reasons);
        const values = Object.values(reasons);

        if (labels.length > 0) {
            window.rejectionChartInstance.data.labels = labels;
            window.rejectionChartInstance.data.datasets[0].data = values;
            window.rejectionChartInstance.update('none');
        }
    }
}

/**
 * Update the "Recent Candidates" section with latest data.
 * Renders as vertical feed cards.
 */
function updateRecentAnalyzed(data) {
    const container = document.getElementById('activityFeedContainer');
    if (!container || !data.recent_analyzed) return;

    // Build HTML for recent candidates as feed cards
    let html = '';
    if (data.recent_analyzed.length > 0) {
        data.recent_analyzed.forEach((c) => {
            const isShortlisted = c.status === 'Shortlisted';
            const icon = isShortlisted ? 'bi-check-circle-fill' : 'bi-x-circle-fill';
            const iconClass = isShortlisted ? 'icon-shortlist' : 'icon-reject';
            const badgeClass = isShortlisted ? 'badge-shortlisted' : 'badge-rejected';
            html += `
                <div class="activity-feed-card">
                    <div class="activity-feed-icon ${iconClass}">
                        <i class="bi ${icon}"></i>
                    </div>
                    <div class="activity-feed-content">
                        <div class="activity-feed-title">Candidate Analyzed</div>
                        <div class="activity-feed-desc">${escapeHtml(c.name || 'Unknown')} — ${escapeHtml(c.role || 'N/A')}</div>
                        <div class="activity-feed-meta">
                            <span class="activity-feed-badge ${badgeClass}">${c.score || 0}% — ${escapeHtml(c.status || '-')}</span>
                        </div>
                    </div>
                    <div class="activity-feed-time">just now</div>
                </div>
            `;
        });
    }
    // Append to dynamic area
    const dynamicArea = document.getElementById('activityFeedDynamic');
    if (dynamicArea) {
        dynamicArea.innerHTML = html;
    }
}

/**
 * Update the activity feed with latest entries.
 */
function updateActivityFeed(data) {
    const container = document.getElementById('activityFeedContainer');
    if (!container || !data.recent_activities) return;

    // Check if activity count has changed
    const currentCount = data.recent_activities.length;
    if (currentCount === lastActivityCount) return;
    lastActivityCount = currentCount;

    let html = '';
    if (data.recent_activities.length > 0) {
        data.recent_activities.forEach((activity) => {
            const iconClass = getActivityIcon(activity.action);
            const colorClass = getActivityColor(activity.status);
            html += `
                <div class="activity-item">
                    <div class="activity-item-main">
                        <i class="bi ${iconClass} ${colorClass}" style="margin-right: 8px;"></i>
                        <strong>${escapeHtml(activity.details || '')}</strong>
                        <span class="activity-meta">${activity.display_time || ''}</span>
                    </div>
                <hr class="activity-divider">
            `;
        });
    } else {
        html = `<div class="empty-state">
            <i class="bi bi-inbox"></i>
            <p>No recent activity yet.</p>
        </div>`;
    }
    container.innerHTML = html;
}

/**
 * Simple HTML escaping to prevent XSS in activity details.
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get Bootstrap icon class for activity type.
 */
function getActivityIcon(action) {
    const icons = {
        'upload': 'bi-cloud-arrow-up-fill',
        'analyze': 'bi-robot',
        'shortlist': 'bi-check-circle-fill',
        'reject': 'bi-x-circle-fill',
        'report': 'bi-file-earmark-bar-graph',
        'delete': 'bi-trash3-fill',
        'save_job': 'bi-save-fill',
        'login': 'bi-box-arrow-in-right',
    };
    return icons[action] || 'bi-info-circle-fill';
}

/**
 * Get CSS color class for activity status.
 */
function getActivityColor(status) {
    const colors = {
        'success': 'text-success',
        'warning': 'text-warning',
        'error': 'text-danger',
    };
    return colors[status] || 'text-secondary';
}

/**
 * Update the "last refreshed" timestamp display.
 */
function updateLastRefreshTime() {
    const el = document.getElementById('lastRefreshTime');
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleTimeString();
    }
}

// ============================================================
// Theme Manager
// ============================================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const html = document.documentElement;

    if (savedTheme === 'dark') {
        html.setAttribute('data-theme', 'dark');
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');

    if (isDark) {
        html.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        if (icon) icon.className = 'bi bi-moon-fill';
        if (label) label.textContent = 'Dark Mode';
    } else {
        html.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        if (icon) icon.className = 'bi bi-sun-fill';
        if (label) label.textContent = 'Light Mode';
    }
}

// ============================================================
// Sidebar Toggle (Mobile)
// ============================================================
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('show');
    document.getElementById('sidebarOverlay').classList.toggle('show');
}

// ============================================================
// Utility Functions
// ============================================================

/**
 * Show a flash message temporarily.
 * @param {string} message - The message text
 * @param {string} type - 'success', 'error', 'warning', 'info'
 */
function showFlash(message, type) {
    const container = document.querySelector('.flash-messages') || createFlashContainer();
    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    const main = document.querySelector('.page-container') || document.querySelector('.main-content');
    if (main) {
        main.prepend(container);
    }
    return container;
}

/**
 * Format a number as percentage.
 */
function formatPercent(value) {
    return Math.round(value) + '%';
}

/**
 * Debounce function for search inputs.
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
