/**
 * Admin Dashboard JavaScript
 * Handles detectability, user management, and admin-only features
 */

let detectabilityMap = null;
let detectabilityMarkers = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeDetectability();
    initializeUserManagement();
    initializeSystemMonitoring();
    initializeTheme();
});

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Detectability Features
function initializeDetectability() {
    // Initialize map
    detectabilityMap = L.map('detectability-map').setView([28.6139, 77.2090], 10);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(detectabilityMap);
    
    // Load detectability data
    loadDetectabilityData();
    
    // Refresh button
    document.getElementById('refresh-detectability').addEventListener('click', function() {
        loadDetectabilityData();
    });
    
    // Auto-refresh every 10 seconds
    setInterval(loadDetectabilityData, 10000);
}

function loadDetectabilityData() {
    fetch('/api/admin/detectability')
        .then(response => response.json())
        .then(data => {
            updateDetectabilityMap(data.users);
            updateDetectabilityList(data.users);
        })
        .catch(error => {
            console.error('Error loading detectability data:', error);
        });
}

function updateDetectabilityMap(users) {
    // Clear existing markers
    detectabilityMarkers.forEach(marker => detectabilityMap.removeLayer(marker));
    detectabilityMarkers = [];
    
    const bounds = [];
    
    users.forEach(user => {
        if (user.location) {
            const color = getThreatColor(user.threat_level);
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `<div style="background: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
            
            const marker = L.marker([user.location.lat, user.location.lng], { icon: icon })
                .addTo(detectabilityMap)
                .bindPopup(`
                    <strong>${user.username}</strong><br>
                    Status: ${user.status}<br>
                    Threat: ${user.threat_level}<br>
                    Last Seen: ${new Date(user.last_seen).toLocaleTimeString()}
                `);
            
            detectabilityMarkers.push(marker);
            bounds.push([user.location.lat, user.location.lng]);
        }
    });
    
    if (bounds.length > 0) {
        detectabilityMap.fitBounds(bounds, { padding: [50, 50] });
    }
}

function updateDetectabilityList(users) {
    const container = document.getElementById('detectability-users');
    container.innerHTML = '';
    
    if (users.length === 0) {
        container.innerHTML = '<p class="loading-text">No active users detected</p>';
        return;
    }
    
    users.forEach(user => {
        const item = document.createElement('div');
        item.className = `user-detect-item status-${user.threat_level.toLowerCase()}`;
        
        const locationText = user.location 
            ? `Location: ${user.location.lat.toFixed(4)}, ${user.location.lng.toFixed(4)}`
            : 'Location: Not available';
        
        item.innerHTML = `
            <h4>${user.username}</h4>
            <p><i class="fas fa-circle"></i> Status: <strong>${user.status}</strong></p>
            <p><i class="fas fa-exclamation-triangle"></i> Threat: <strong>${user.threat_level}</strong></p>
            <p><i class="fas fa-map-marker-alt"></i> ${locationText}</p>
            <p><i class="fas fa-clock"></i> Last Seen: ${new Date(user.last_seen).toLocaleString()}</p>
        `;
        
        container.appendChild(item);
    });
}

function getThreatColor(level) {
    const colors = {
        'SAFE': '#10b981',
        'LOW': '#f59e0b',
        'MEDIUM': '#f97316',
        'HIGH': '#ef4444',
        'CRITICAL': '#dc2626'
    };
    return colors[level] || '#6c757d';
}

// User Management
function initializeUserManagement() {
    // View contacts buttons
    document.querySelectorAll('.btn-view-contacts').forEach(btn => {
        btn.addEventListener('click', function() {
            const username = this.getAttribute('data-username');
            viewUserContacts(username);
        });
    });
    
    // View details buttons
    document.querySelectorAll('.btn-view').forEach(btn => {
        btn.addEventListener('click', function() {
            const username = this.getAttribute('data-username');
            viewUserDetails(username);
        });
    });
    
    // Delete buttons
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const username = this.getAttribute('data-username');
            deleteUser(username);
        });
    });
}

function viewUserContacts(username) {
    fetch(`/api/admin/user_details/${username}`)
        .then(response => response.json())
        .then(data => {
            showModal('Contacts', `
                <h3>Emergency Contacts for ${username}</h3>
                ${data.contacts.length > 0 
                    ? data.contacts.map(contact => `
                        <div class="contact-item">
                            <h4>${contact.name}</h4>
                            <p><i class="fas fa-phone"></i> ${contact.phone}</p>
                            ${contact.email ? `<p><i class="fas fa-envelope"></i> ${contact.email}</p>` : ''}
                        </div>
                    `).join('')
                    : '<p>No contacts registered</p>'
                }
            `);
        })
        .catch(error => {
            console.error('Error loading user details:', error);
            alert('Error loading user contacts');
        });
}

function viewUserDetails(username) {
    fetch(`/api/admin/user_details/${username}`)
        .then(response => response.json())
        .then(data => {
            showModal('User Details', `
                <div class="user-details">
                    <h3>${username}</h3>
                    <p><strong>Created:</strong> ${data.created_at || 'Unknown'}</p>
                    <p><strong>Emergency Contacts:</strong> ${data.contact_count}</p>
                    <h4 style="margin-top: 1.5rem;">Contact List:</h4>
                    ${data.contacts.length > 0 
                        ? data.contacts.map(contact => `
                            <div class="contact-item">
                                <h4>${contact.name}</h4>
                                <p><i class="fas fa-phone"></i> ${contact.phone}</p>
                                ${contact.email ? `<p><i class="fas fa-envelope"></i> ${contact.email}</p>` : ''}
                            </div>
                        `).join('')
                        : '<p>No contacts registered</p>'
                    }
                </div>
            `);
        })
        .catch(error => {
            console.error('Error loading user details:', error);
            alert('Error loading user details');
        });
}

function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        return;
    }
    
    fetch('/api/admin/delete_user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            // Remove the user row from the table with animation
            const userRow = document.querySelector(`tr[data-username="${username}"]`);
            if (userRow) {
                userRow.style.transition = 'opacity 0.3s';
                userRow.style.opacity = '0';
                setTimeout(() => {
                    userRow.remove();
                    // Refresh stats after deletion
                    setTimeout(() => {
                        location.reload();
                    }, 500);
                }, 300);
            } else {
                location.reload();
            }
        } else {
            alert('Error: ' + (data.error || 'Failed to delete user'));
        }
    })
    .catch(error => {
        console.error('Error deleting user:', error);
        alert('Error deleting user. Please try again.');
    });
}

// System Monitoring
function initializeSystemMonitoring() {
    loadSystemStats();
    setInterval(loadSystemStats, 5000); // Update every 5 seconds
}

function loadSystemStats() {
    // Load user threat statuses for the first card
    loadUserThreatStatuses();
    
    // Load activity logs for recent events
    loadActivityLogs();
}

function loadActivityLogs() {
    fetch('/api/admin/activity_logs')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateActivityLogs(data.logs);
            } else {
                console.error('Failed to load activity logs:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading activity logs:', error);
        });
}

function loadUserThreatStatuses() {
    fetch('/api/admin/user_threat_status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateUserThreatStatuses(data.users);
            } else {
                console.error('Failed to load user threat statuses:', data.error);
                updateUserThreatStatuses([]);
            }
        })
        .catch(error => {
            console.error('Error loading user threat statuses:', error);
            updateUserThreatStatuses([]);
        });
}

function updateUserThreatStatuses(users) {
    const container = document.getElementById('user-threat-list');
    
    if (!users || users.length === 0) {
        container.innerHTML = '<p class="loading-text">No users with active monitoring</p>';
        return;
    }
    
    // Sort users by threat score (highest first)
    const sortedUsers = users.slice().sort((a, b) => b.threat_score - a.threat_score);
    
    container.innerHTML = sortedUsers.map(user => {
        const threatState = user.threat_state || 'SAFE';
        const threatScore = (user.threat_score || 0).toFixed(2);
        const username = user.username;
        const lastUpdated = new Date(user.last_updated).toLocaleString();
        const isMonitoringActive = user.monitoring_active;
        
        // Determine CSS class based on threat level
        let threatClass = 'safe';
        if (threatState === 'MEDIUM') threatClass = 'medium';
        else if (threatState === 'HIGH') threatClass = 'high';
        else if (threatState === 'CRITICAL') threatClass = 'critical';
        
        // Status indicator
        const statusIndicator = isMonitoringActive ? 
            '<i class="fas fa-circle status-active" title="Monitoring Active"></i>' : 
            '<i class="fas fa-circle status-inactive" title="Monitoring Inactive"></i>';
        
        return `
            <div class="user-threat-item ${threatClass}">
                <div class="user-threat-header">
                    <strong>${username}</strong>
                    ${statusIndicator}
                    <span class="threat-state">${threatState}</span>
                </div>
                <div class="user-threat-details">
                    <span class="threat-score">Score: ${threatScore}</span>
                    <small class="last-updated">${lastUpdated}</small>
                </div>
            </div>
        `;
    }).join('');
}

function updateActivityLogs(logs) {
    const eventsContainer = document.getElementById('recent-events');
    
    if (!logs || logs.length === 0) {
        eventsContainer.innerHTML = '<p class="loading-text">No recent activity</p>';
        return;
    }
    
    // Display logs in reverse chronological order (most recent first)
    const sortedLogs = logs.slice().reverse();
    
    eventsContainer.innerHTML = sortedLogs.map(log => {
        const userType = log.user_type === 'admin' ? 'ADMIN' : 'USER';
        const action = log.action;
        const username = log.username;
        const timestamp = new Date(log.timestamp).toLocaleString();
        const details = log.details ? ` - ${log.details}` : '';
        
        // Style based on user type
        const userTypeClass = log.user_type === 'admin' ? 'admin' : 'user';
        
        return `
            <div class="event-item ${userTypeClass}">
                <strong>[${userType}]</strong> ${username}: ${action}${details}<br>
                <small>${timestamp}</small>
            </div>
        `;
    }).join('');
}

// Modal Functions
function showModal(title, content) {
    const modal = document.getElementById('user-modal');
    const modalBody = document.getElementById('user-modal-body');
    
    modalBody.innerHTML = content;
    modal.classList.add('show');
    
    // Close button
    document.querySelector('.modal-close').onclick = function() {
        modal.classList.remove('show');
    };
    
    // Close on outside click
    modal.onclick = function(e) {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    };
    
    // ESC key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            modal.classList.remove('show');
        }
    });
}



