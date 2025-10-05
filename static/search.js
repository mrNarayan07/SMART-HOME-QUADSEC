// search.js - Face Recognition Security System Search Functionality

class SecuritySearch {
    constructor() {
        this.searchResults = [];
        this.savedSearches = [];
        this.isSearching = false;
        this.searchTimeout = null;
        
        this.init();
    }
    
    init() {
        this.loadSavedSearches();
        this.setupEventListeners();
        this.setupQuickFilters();
        this.checkSystemStatus();
        this.initializeBootstrapComponents();
        
        console.log('Security Search initialized');
    }
    
    setupEventListeners() {
        // Main search form
        const searchForm = document.getElementById('advancedSearchForm');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => this.handleSearchSubmit(e));
        }
        
        // Search input with debounce
        const searchQuery = document.getElementById('searchQuery');
        if (searchQuery) {
            searchQuery.addEventListener('input', () => this.debounceSearch());
            searchQuery.addEventListener('keydown', (e) => this.handleSearchKeydown(e));
        }
        
        // Clear search button
        const clearSearchBtn = document.getElementById('clearSearch');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => this.clearSearch());
        }
        
        // Reset search button
        const resetSearchBtn = document.getElementById('resetSearch');
        if (resetSearchBtn) {
            resetSearchBtn.addEventListener('click', () => this.resetSearch());
        }
        
        // Save search button
        const saveSearchBtn = document.getElementById('saveSearch');
        if (saveSearchBtn) {
            saveSearchBtn.addEventListener('click', () => this.saveCurrentSearch());
        }
        
        // Clear saved searches
        const clearSavedBtn = document.getElementById('clearSavedSearches');
        if (clearSavedBtn) {
            clearSavedBtn.addEventListener('click', () => this.clearSavedSearches());
        }
        
        // Range slider for confidence
        const confidenceSlider = document.getElementById('confidenceMin');
        if (confidenceSlider) {
            confidenceSlider.addEventListener('input', (e) => this.updateConfidenceDisplay(e.target.value));
        }
        
        // Filter change events
        const filterElements = ['statusSearch', 'cameraSearch', 'dateFrom', 'dateTo', 'sortBy'];
        filterElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.debounceSearch());
            }
        });
        
        // System status check
        this.setupAutoRefresh();
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }
    
    setupQuickFilters() {
        const quickFilterButtons = document.querySelectorAll('[data-filter]');
        quickFilterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.applyQuickFilter(button.dataset.filter);
            });
        });
    }
    
    applyQuickFilter(filterType) {
        // Clear existing filters first
        this.resetSearch();
        
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        const thisWeekStart = new Date(today);
        thisWeekStart.setDate(today.getDate() - today.getDay());
        
        switch (filterType) {
            case 'today':
                document.getElementById('dateFrom').value = this.formatDate(today);
                document.getElementById('dateTo').value = this.formatDate(today);
                break;
                
            case 'yesterday':
                document.getElementById('dateFrom').value = this.formatDate(yesterday);
                document.getElementById('dateTo').value = this.formatDate(yesterday);
                break;
                
            case 'week':
                document.getElementById('dateFrom').value = this.formatDate(thisWeekStart);
                document.getElementById('dateTo').value = this.formatDate(today);
                break;
                
            case 'unknown':
                document.getElementById('statusSearch').value = 'unknown';
                break;
                
            case 'known':
                document.getElementById('statusSearch').value = 'known';
                break;
                
            case 'high-confidence':
                document.getElementById('statusSearch').value = 'known';
                document.getElementById('confidenceMin').value = '80';
                this.updateConfidenceDisplay('80');
                break;
        }
        
        // Trigger search
        this.performSearch();
    }
    
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    handleSearchSubmit(e) {
        e.preventDefault();
        this.performSearch();
    }
    
    handleSearchKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            this.performSearch();
        }
    }
    
    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            const query = document.getElementById('searchQuery').value.trim();
            if (query.length >= 2) {
                this.performSearch();
            } else if (query.length === 0) {
                this.clearResults();
            }
        }, 500);
    }
    
    async performSearch() {
        if (this.isSearching) return;
        
        try {
            this.setSearching(true);
            
            const searchParams = this.collectSearchParams();
            const results = await this.executeSearch(searchParams);
            
            this.displayResults(results);
            this.updateResultsCount(results.length);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showNotification('Search failed. Please try again.', 'error');
            this.displayError(error.message);
        } finally {
            this.setSearching(false);
        }
    }
    
    collectSearchParams() {
        return {
            query: document.getElementById('searchQuery').value.trim(),
            status: document.getElementById('statusSearch').value,
            camera: document.getElementById('cameraSearch').value,
            dateFrom: document.getElementById('dateFrom').value,
            dateTo: document.getElementById('dateTo').value,
            confidenceMin: document.getElementById('confidenceMin').value,
            sortBy: document.getElementById('sortBy').value
        };
    }
    
    async executeSearch(params) {
        const searchUrl = new URL('/api/search', window.location.origin);
        
        // Build query string
        if (params.query) searchUrl.searchParams.set('q', params.query);
        if (params.status) searchUrl.searchParams.set('status', params.status);
        if (params.camera) searchUrl.searchParams.set('camera', params.camera);
        if (params.dateFrom) searchUrl.searchParams.set('date_from', params.dateFrom);
        if (params.dateTo) searchUrl.searchParams.set('date_to', params.dateTo);
        if (params.confidenceMin > 0) searchUrl.searchParams.set('confidence_min', params.confidenceMin);
        if (params.sortBy) searchUrl.searchParams.set('sort', params.sortBy);
        
        const response = await fetch(searchUrl);
        if (!response.ok) {
            throw new Error(`Search request failed: ${response.status}`);
        }
        
        const data = await response.json();
        return data.results || [];
    }
    
    displayResults(results) {
        this.searchResults = results;
        
        const resultsContainer = document.getElementById('searchResults');
        const resultsTable = document.getElementById('resultsTable');
        const resultsTableBody = document.getElementById('resultsTableBody');
        
        if (results.length === 0) {
            this.showNoResults();
            return;
        }
        
        // Hide no-search state and show results table
        const noSearchState = document.querySelector('.no-search-state');
        if (noSearchState) noSearchState.style.display = 'none';
        
        if (resultsTable) resultsTable.classList.remove('d-none');
        
        // Populate results table
        if (resultsTableBody) {
            resultsTableBody.innerHTML = results.map(result => this.createResultRow(result)).join('');
        }
        
        // Setup image modals for new results
        this.setupImageModals();
    }
    
    createResultRow(result) {
        const imageContent = result.image_exists ? `
            <img src="/image/${result.image_path.split('/').pop()}" 
                 class="face-thumbnail" 
                 alt="Face capture"
                 data-bs-toggle="modal" 
                 data-bs-target="#imageModal"
                 data-image-src="/image/${result.image_path.split('/').pop()}"
                 data-image-time="${result.timestamp}"
                 data-image-name="${result.name}"
                 data-image-status="${result.status}"
                 data-image-confidence="${result.confidence_score || 'N/A'}">
            <i class="fas fa-expand-alt image-expand-icon"></i>
        ` : result.status === 'known' ? `
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
        
        const confidenceContent = result.confidence_score ? `
            <div class="confidence-info">
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${result.confidence_score}%"></div>
                </div>
                <span class="confidence-text">${result.confidence_score}%</span>
            </div>
        ` : '<span class="text-muted">N/A</span>';
        
        return `
            <tr class="log-row fade-in" data-status="${result.status}">
                <td>
                    <div class="time-info">
                        <div class="absolute-time">${result.timestamp}</div>
                        <div class="relative-time">${result.relative_time}</div>
                    </div>
                </td>
                <td>
                    <span class="status-badge status-${result.status_class}">
                        ${result.status_icon} ${result.status.charAt(0).toUpperCase() + result.status.slice(1)}
                    </span>
                </td>
                <td>
                    <div class="name-info">
                        ${result.name !== 'Unknown' ? `
                            <i class="fas fa-user text-success"></i>
                            <strong>${result.name}</strong>
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
                        ${result.camera_id}
                    </span>
                </td>
            </tr>
        `;
    }
    
    showNoResults() {
        const resultsTable = document.getElementById('resultsTable');
        const resultsContainer = document.getElementById('searchResults');
        
        if (resultsTable) resultsTable.classList.add('d-none');
        
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="no-results-state text-center">
                    <div class="no-results-icon">
                        <i class="fas fa-search-minus"></i>
                    </div>
                    <h6>No Results Found</h6>
                    <p>No activity logs match your search criteria.</p>
                    <div class="no-results-suggestions">
                        <h6><i class="fas fa-lightbulb"></i> Try:</h6>
                        <ul class="list-unstyled">
                            <li>• Broadening your search terms</li>
                            <li>• Removing some filters</li>
                            <li>• Checking for typos</li>
                            <li>• Using different date ranges</li>
                        </ul>
                    </div>
                </div>
            `;
        }
    }
    
    clearResults() {
        const noSearchState = document.querySelector('.no-search-state');
        const resultsTable = document.getElementById('resultsTable');
        
        if (noSearchState) noSearchState.style.display = 'block';
        if (resultsTable) resultsTable.classList.add('d-none');
        
        this.updateResultsCount(0);
        this.searchResults = [];
    }
    
    displayError(message) {
        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="error-state text-center">
                    <div class="error-icon">
                        <i class="fas fa-exclamation-triangle text-danger"></i>
                    </div>
                    <h6>Search Error</h6>
                    <p>${message}</p>
                    <button class="btn btn-outline-primary" onclick="window.location.reload()">
                        <i class="fas fa-sync-alt"></i> Refresh Page
                    </button>
                </div>
            `;
        }
    }
    
    updateResultsCount(count) {
        const resultsCount = document.getElementById('resultsCount');
        if (resultsCount) {
            if (count === 0) {
                resultsCount.textContent = 'No results found';
            } else {
                resultsCount.textContent = `Found ${count} result${count !== 1 ? 's' : ''}`;
            }
        }
    }
    
    clearSearch() {
        document.getElementById('searchQuery').value = '';
        this.clearResults();
    }
    
    resetSearch() {
        const form = document.getElementById('advancedSearchForm');
        if (form) {
            form.reset();
            this.updateConfidenceDisplay('0');
        }
        this.clearResults();
    }
    
    updateConfidenceDisplay(value) {
        const display = document.getElementById('confidenceMinValue');
        if (display) {
            display.textContent = `${value}%`;
        }
    }
    
    saveCurrentSearch() {
        const params = this.collectSearchParams();
        
        // Check if search has meaningful criteria
        if (!params.query && !params.status && !params.dateFrom && !params.dateTo && params.confidenceMin == 0) {
            this.showNotification('Please enter search criteria before saving', 'warning');
            return;
        }
        
        const searchName = prompt('Enter a name for this search:') || `Search ${Date.now()}`;
        
        const savedSearch = {
            id: Date.now(),
            name: searchName,
            params: params,
            created: new Date().toISOString(),
            resultCount: this.searchResults.length
        };
        
        this.savedSearches.push(savedSearch);
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        this.showNotification('Search saved successfully', 'success');
    }
    
    loadSavedSearches() {
        try {
            const saved = localStorage.getItem('securitySearches');
            this.savedSearches = saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Failed to load saved searches:', error);
            this.savedSearches = [];
        }
        
        this.renderSavedSearches();
    }
    
    saveSavedSearches() {
        try {
            localStorage.setItem('securitySearches', JSON.stringify(this.savedSearches));
        } catch (error) {
            console.error('Failed to save searches:', error);
        }
    }
    
    renderSavedSearches() {
        const container = document.getElementById('savedSearchesList');
        if (!container) return;
        
        if (this.savedSearches.length === 0) {
            container.innerHTML = `
                <div class="no-saved-searches">
                    <i class="fas fa-bookmark"></i>
                    <span>No saved searches yet</span>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.savedSearches.map(search => `
            <div class="saved-search-item" data-search-id="${search.id}">
                <div class="saved-search-info">
                    <div class="saved-search-name">${search.name}</div>
                    <div class="saved-search-meta">
                        ${new Date(search.created).toLocaleDateString()} • 
                        ${search.resultCount} results
                    </div>
                </div>
                <div class="saved-search-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="securitySearch.loadSavedSearch(${search.id})">
                        <i class="fas fa-play"></i> Load
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="securitySearch.deleteSavedSearch(${search.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    loadSavedSearch(searchId) {
        const search = this.savedSearches.find(s => s.id === searchId);
        if (!search) return;
        
        // Load search parameters into form
        const params = search.params;
        if (params.query) document.getElementById('searchQuery').value = params.query;
        if (params.status) document.getElementById('statusSearch').value = params.status;
        if (params.camera) document.getElementById('cameraSearch').value = params.camera;
        if (params.dateFrom) document.getElementById('dateFrom').value = params.dateFrom;
        if (params.dateTo) document.getElementById('dateTo').value = params.dateTo;
        if (params.confidenceMin) {
            document.getElementById('confidenceMin').value = params.confidenceMin;
            this.updateConfidenceDisplay(params.confidenceMin);
        }
        if (params.sortBy) document.getElementById('sortBy').value = params.sortBy;
        
        // Execute the search
        this.performSearch();
        
        this.showNotification(`Loaded search: ${search.name}`, 'success');
    }
    
    deleteSavedSearch(searchId) {
        if (!confirm('Are you sure you want to delete this saved search?')) return;
        
        this.savedSearches = this.savedSearches.filter(s => s.id !== searchId);
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        this.showNotification('Saved search deleted', 'success');
    }
    
    clearSavedSearches() {
        if (!confirm('Are you sure you want to clear all saved searches?')) return;
        
        this.savedSearches = [];
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        this.showNotification('All saved searches cleared', 'success');
    }
    
    setupImageModals() {
        const imageModal = document.getElementById('imageModal');
        if (imageModal) {
            imageModal.addEventListener('show.bs.modal', (event) => {
                const trigger = event.relatedTarget;
                if (trigger) {
                    const imageSrc = trigger.getAttribute('data-image-src');
                    const imageTime = trigger.getAttribute('data-image-time');
                    const imageName = trigger.getAttribute('data-image-name');
                    const imageStatus = trigger.getAttribute('data-image-status');
                    const imageConfidence = trigger.getAttribute('data-image-confidence');
                    
                    this.populateImageModal(imageSrc, imageTime, imageName, imageStatus, imageConfidence);
                }
            });
        }
    }
    
    populateImageModal(imageSrc, imageTime, imageName, imageStatus, imageConfidence) {
        const elements = {
            modalImage: document.getElementById('modalImage'),
            modalImageName: document.getElementById('modalImageName'),
            modalImageTime: document.getElementById('modalImageTime'),
            modalImageStatus: document.getElementById('modalImageStatus'),
            modalImageConfidence: document.getElementById('modalImageConfidence')
        };
        
        if (elements.modalImage) elements.modalImage.src = imageSrc;
        if (elements.modalImageName) elements.modalImageName.textContent = imageName || 'Unknown';
        if (elements.modalImageTime) elements.modalImageTime.textContent = imageTime || 'Unknown';
        if (elements.modalImageStatus) {
            elements.modalImageStatus.innerHTML = imageStatus === 'known' 
                ? '<span class="badge bg-success">Known</span>'
                : '<span class="badge bg-danger">Unknown</span>';
        }
        if (elements.modalImageConfidence) {
            elements.modalImageConfidence.textContent = imageConfidence !== 'N/A' 
                ? `${imageConfidence}%` 
                : 'N/A';
        }
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
            systemStatusEl.innerHTML = `<i class="fas fa-circle text-danger"></i> System Error`;
        } else if (status.recognition_system === 'Running') {
            systemStatusEl.innerHTML = `<i class="fas fa-circle text-success"></i> System Online`;
        } else {
            systemStatusEl.innerHTML = `<i class="fas fa-circle text-warning"></i> System Offline`;
        }
    }
    
    setupAutoRefresh() {
        setInterval(() => {
            if (!document.hidden) {
                this.checkSystemStatus();
            }
        }, 30000);
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + F: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('searchQuery');
            if (searchInput) searchInput.focus();
        }
        
        // Escape: Clear search
        if (e.key === 'Escape') {
            this.clearSearch();
        }
        
        // Ctrl/Cmd + Enter: Search
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            this.performSearch();
        }
    }
    
    setSearching(searching) {
        this.isSearching = searching;
        
        const spinner = document.getElementById('loadingSpinner');
        const searchBtn = document.querySelector('#advancedSearchForm button[type="submit"]');
        
        if (spinner) {
            spinner.classList.toggle('show', searching);
        }
        
        if (searchBtn) {
            searchBtn.disabled = searching;
            const icon = searchBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-spin', searching);
            }
        }
    }
    
    showNotification(message, type = 'info') {
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
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    destroy() {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        document.removeEventListener('keydown', this.handleKeyboardShortcuts);
    }
}

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.securitySearch = new SecuritySearch();
    
    console.log('%c🔍 Face Recognition Security Search', 'color: #0d6efd; font-weight: bold; font-size: 16px;');
    console.log('%cKeyboard Shortcuts:', 'color: #6c757d; font-weight: bold;');
    console.log('  • Ctrl/Cmd + F: Focus search input');
    console.log('  • Ctrl/Cmd + Enter: Execute search');
    console.log('  • Escape: Clear search');
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.securitySearch) {
        window.securitySearch.destroy();
    }
});

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecuritySearch;
}