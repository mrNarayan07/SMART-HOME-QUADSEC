// dashboard.js - Face Recognition Security System Dashboard Functionality

class SecurityDashboard {
    constructor() {
        this.isLoading = false;
        this.refreshInterval = null;
        this.lastUpdateTime = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupImageModals();
        this.checkSystemStatus();
        this.setupAutoRefresh();
        
        // Initialize tooltips and popovers
        this.initializeBootstrapComponents();
        
        console.log('Security Dashboard initialized');
    }
    
    setupEventListeners() {
        // Filter form submission
        const filterForm = document.getElementById('filterForm');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => this.handleFilterSubmit(e));
        }
        
        // Clear filters button
        const clearFiltersBtn = document.getElementById('clearFilters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
        
        // Auto-filter on input change
        const statusFilter = document.getElementById('statusFilter');
        const nameFilter = document.getElementById('nameFilter');
        const dateFilter = document.getElementById('dateFilter');
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.debounceFilter());
        }
        
        if (nameFilter) {
            nameFilter.addEventListener('input', () => this.debounceFilter());
        }
        
        if (dateFilter) {
            dateFilter.addEventListener('change', () => this.debounceFilter());
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Handle page visibility change
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        
        // Handle online/offline status
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
    }
    
    setupImageModals() {
        // Set up image modal functionality
        const imageModal = document.getElementById('imageModal');
        if (imageModal) {
            imageModal.addEventListener('show.bs.modal', (event) => {
                const trigger = event.relatedTarget;
                if (trigger) {
                    const imageSrc = trigger.getAttribute('data-image-src');
                    const imageTime = trigger.getAttribute('data-image-time');
                    const imageName = trigger.getAttribute('data-image-name');
                    
                    this.populateImageModal(imageSrc, imageTime, imageName);
                }
            });
        }
        
        // Setup thumbnail click handlers
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('face-thumbnail')) {
                e.preventDefault();
                const modal = new bootstrap.Modal(document.getElementById('imageModal'));
                modal.show();
            }
        });
    }
    
    populateImageModal(imageSrc, imageTime, imageName) {
        const modalImage = document.getElementById('modalImage');
        const modalImageName = document.getElementById('modalImageName');
        const modalImageTime = document.getElementById('modalImageTime');
        
        if (modalImage) modalImage.src = imageSrc;
        if (modalImageName) modalImageName.textContent = imageName || 'Unknown';
        if (modalImageTime) modalImageTime.textContent = imageTime || 'Unknown';
    }
    
    handleFilterSubmit(e) {
        e.preventDefault();
        this.applyFilters();
    }
    
    applyFilters() {
        if (this.isLoading) return;
        
        const formData = new FormData(document.getElementById('filterForm'));
        const params = new URLSearchParams();
        
        // Build query parameters
        for (let [key, value] of formData.entries()) {
            if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        // Redirect to filtered URL
        window.location.href = `/?${params.toString()}`;
    }
    
    clearFilters() {
        const form = document.getElementById('filterForm');
        if (form) {
            form.reset();
            window.location.href = '/';
        }
    }
    
    debounceFilter() {
        clearTimeout(this.filterTimeout);
        this.filterTimeout = setTimeout(() => {
            this.applyFilters();
        }, 500);
    }
    
    async refreshData() {
        if (this.isLoading) return;
        
        try {
            this.setLoading(true);
            
            // Get current filters
            const urlParams = new URLSearchParams(window.location.search);
            const apiUrl = `/api/logs?${urlParams.toString()}`;
            
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            
            // Update the logs table
            this.updateLogsTable(data.logs);
            
            // Update pagination if needed
            this.updatePagination(data.pagination);
            
            // Update statistics
            await this.updateStatistics();
            
            this.showNotification('Data refreshed successfully', 'success');
            this.lastUpdateTime = new Date();
            
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh data', 'error');
        } finally {
            this.setLoading(false);
        }
    }
    
    updateLogsTable(logs) {
        const tbody = document.querySelector('.logs-table tbody');
        if (!tbody) return;
        
        if (logs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center no-data">
                        <div class="no-data-content">
                            <i class="fas fa-inbox"></i>
                            <p>No activity logs found</p>
                            <small>Try adjusting your filters or check if the recognition system is running</small>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = logs.map(log => this.createLogRow(log)).join('');
        
        // Reinitialize event listeners for new elements
        this.setupImageModals();
    }
    
    createLogRow(log) {
        const imageContent = log.image_exists ? `
            <img src="/image/${log.image_path.split('/').pop()}" 
                 class="face-thumbnail" 
                 alt="Face capture"
                 data-bs-toggle="modal" 
                 data-bs-target="#imageModal"
                 data-image-src="/image/${log.image_path.split('/').pop()}"
                 data-image-time="${log.timestamp}"
                 data-image-name="${log.name}">
            <i class="fas fa-expand-alt image-expand-icon"></i>
        ` : log.status === 'known' ? `
            <span class="no-image">
                <i class="fas fa-user-check"></i>
                No image
            </span>
        ` : `
            <span class="no-image text-muted">
                <i class="fas fa-image"></i>
                Not available
            </span>
        `;
        
        const confidenceContent = log.confidence_score ? `
            <div class="confidence-info">
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${log.confidence_score}%"></div>
                </div>
                <span class="confidence-text">${log.confidence_score}%</span>
            </div>
        ` : '<span class="text-muted">N/A</span>';
        
        return `
            <tr class="log-row fade-in" data-status="${log.status}">
                <td>
                    <div class="time-info">
                        <div class="absolute-time">${log.timestamp}</div>
                        <div class="relative-time">${log.relative_time}</div>
                    </div>
                </td>
                <td>
                    <span class="status-badge status-${log.status_class}">
                        ${log.status_icon} ${log.status.charAt(0).toUpperCase() + log.status.slice(1)}
                    </span>
                </td>
                <td>
                    <div class="name-info">
                        ${log.name !== 'Unknown' ? `
                            <i class="fas fa-user text-success"></i>
                            <strong>${log.name}</strong>
                        ` : `
                            <i class="fas fa-user-secret text-danger"></i>
                            <em>Unknown Person</em>
                        `}
                    </div>
                </td>
                <td>
                    <div class="image-info">
                        ${imageContent}
                    </div>
                </td>
                <td>${confidenceContent}</td>
                <td>
                    <span class="camera-info">
                        <i class="fas fa-video"></i>
                        ${log.camera_id}
                    </span>
                </td>
            </tr>
        `;
    }
    
    updatePagination(pagination) {
        // Update pagination info if needed
        const logsCount = document.querySelector('.logs-count');
        if (logsCount && pagination) {
            logsCount.textContent = `Showing ${pagination.logs?.length || 0} of ${pagination.total_count} logs`;
        }
    }
    
    async updateStatistics() {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Failed to fetch statistics');
            
            const stats = await response.json();
            
            // Update statistics cards
            this.updateStatCard('total_logs', stats.total_logs);
            this.updateStatCard('known_count', stats.known_count);
            this.updateStatCard('unknown_count', stats.unknown_count);
            this.updateStatCard('recent_activity', stats.recent_activity);
            this.updateStatCard('family_count', stats.family_count);
            this.updateStatCard('most_active_member', stats.most_active_member);
            
        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }
    
    updateStatCard(key, value) {
        const elements = document.querySelectorAll(`[data-stat="${key}"], .stat-number`);
        elements.forEach(el => {
            if (el.dataset.stat === key || el.closest('.stat-card')?.dataset.stat === key) {
                el.textContent = value;
            }
        });
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const status = await response.json();
            
            this.updateSystemStatus(status);
            
        } catch (error) {
            console.error('Error checking system status:', error);
            this.updateSystemStatus({ error: 'Connection failed' });
        }
    }
    
    updateSystemStatus(status) {
        const systemStatusEl = document.getElementById('systemStatus');
        if (!systemStatusEl) return;
        
        if (status.error) {
            systemStatusEl.innerHTML = `
                <i class="fas fa-circle text-danger"></i>
                System Error
            `;
        } else if (status.recognition_system === 'Running') {
            systemStatusEl.innerHTML = `
                <i class="fas fa-circle text-success"></i>
                System Online
            `;
        } else {
            systemStatusEl.innerHTML = `
                <i class="fas fa-circle text-warning"></i>
                System Offline
            `;
        }
    }
    
    setupAutoRefresh() {
        // Auto refresh every 30 seconds when page is visible
        this.refreshInterval = setInterval(() => {
            if (!document.hidden && !this.isLoading) {
                this.refreshData();
            }
        }, 30000);
    }
    
    handleVisibilityChange() {
        if (!document.hidden) {
            // Page became visible, refresh if data is old
            if (this.lastUpdateTime && Date.now() - this.lastUpdateTime > 60000) {
                this.refreshData();
            }
        }
    }
    
    handleOnlineStatus(isOnline) {
        if (isOnline) {
            this.showNotification('Connection restored', 'success');
            this.checkSystemStatus();
        } else {
            this.showNotification('Connection lost', 'warning');
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + R: Refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            this.refreshData();
        }
        
        // Escape: Clear search/filters
        if (e.key === 'Escape') {
            const nameFilter = document.getElementById('nameFilter');
            if (nameFilter && nameFilter.value) {
                nameFilter.value = '';
                this.debounceFilter();
            }
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        
        const spinner = document.getElementById('loadingSpinner');
        const refreshBtn = document.getElementById('refreshBtn');
        
        if (spinner) {
            spinner.classList.toggle('show', loading);
        }
        
        if (refreshBtn) {
            refreshBtn.disabled = loading;
            const icon = refreshBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-spin', loading);
            }
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show notification`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${this.getNotificationIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    initializeBootstrapComponents() {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    destroy() {
        // Cleanup when component is destroyed
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.filterTimeout) {
            clearTimeout(this.filterTimeout);
        }
        
        // Remove event listeners
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('online', this.handleOnlineStatus);
        window.removeEventListener('offline', this.handleOnlineStatus);
        document.removeEventListener('keydown', this.handleKeyboardShortcuts);
    }
}

// Utility functions
function formatRelativeTime(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diff = now - then;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days} day${days !== 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
        return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else {
        return 'Just now';
    }
}

function formatTimestamp(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (error) {
        return timestamp;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.securityDashboard = new SecurityDashboard();
    
    // Add some helpful console information
    console.log('%c🏠 Face Recognition Security System Dashboard', 'color: #0d6efd; font-weight: bold; font-size: 16px;');
    console.log('%cKeyboard Shortcuts:', 'color: #6c757d; font-weight: bold;');
    console.log('  • Ctrl/Cmd + R: Refresh data');
    console.log('  • Escape: Clear search filters');
    console.log('%cAPI Endpoints:', 'color: #6c757d; font-weight: bold;');
    console.log('  • /api/logs: Get activity logs');
    console.log('  • /api/stats: Get statistics');
    console.log('  • /api/system/status: Get system status');
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.securityDashboard) {
        window.securityDashboard.destroy();
    }
});

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SecurityDashboard, formatRelativeTime, formatTimestamp };
}