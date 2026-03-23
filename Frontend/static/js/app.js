/**
 * Frontend Application Logic
 * Handles camera, threat monitoring, map, chatbot, and UI updates
 * ENHANCED GPS DIAGNOSTICS
 */

// Global state
let threatChart = null;
let map = null;
let userLocation = null;
let monitoringInterval = null;
let isMonitoring = false;
let frontStream = null;
let backStream = null;

// Session-based API fetch (no CSRF)
function apiFetch(url, options = {}) {
    return fetch(url, {
        ...options,
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Show loading screen only on first visit
    const loadingScreen = document.getElementById('loading-screen');
    if (loadingScreen) {
        const hasVisited = sessionStorage.getItem('hasVisited');
        if (!hasVisited) {
            setTimeout(function() {
                loadingScreen.classList.add('hidden');
                sessionStorage.setItem('hasVisited', 'true');
            }, 500);
        } else {
            loadingScreen.classList.add('hidden');
        }
    }
    
    initializeCamera();
    initializeMap(); 
    initializeChart();
    initializeEventListeners();
    initializeChatbot();
    initializeTheme();
    detectDeviceType();
});

function sendUserLocation() {
    if (!navigator.geolocation) return;

navigator.geolocation.getCurrentPosition(
        (pos) => {
            apiFetch("/api/update_location", {
                method: "POST",
                body: JSON.stringify({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude
                })
            }).catch(e => console.log('Location update failed:', e));
        },
        (err) => {
            console.warn("Location access denied for background update", err);
        }
    );
}

// Send immediately and every 20 seconds
sendUserLocation();
setInterval(sendUserLocation, 20000);

// Theme initialization
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Device detection
function detectDeviceType() {
    initializeDualCameras();
}

// Camera initialization
async function initializeCamera() {
    await initializeDualCameras();
}

async function initializeDualCameras() {
    const frontVideo = document.getElementById('front-video');
    const backVideo = document.getElementById('back-video');
    const serverFrontVideo = document.getElementById('server-front-video');
    const serverBackVideo = document.getElementById('server-back-video');
    const frontFallback = document.getElementById('front-fallback');
    const backFallback = document.getElementById('back-fallback');
    
    // Front Camera
    try {
        frontStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        frontVideo.srcObject = frontStream;
        frontVideo.style.display = 'block';
        serverFrontVideo.style.display = 'none';
        frontFallback.style.display = 'none';
    } catch (e) {
        frontVideo.style.display = 'none';
        serverFrontVideo.src = '/video_feed';
        serverFrontVideo.style.display = 'block';
        frontFallback.style.display = 'none';
    }
    
    // Back Camera
    try {
        backStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        backVideo.srcObject = backStream;
        backVideo.style.display = 'block';
        serverBackVideo.style.display = 'none';
        backFallback.style.display = 'none';
    } catch (e) {
        backVideo.style.display = 'none';
        serverBackVideo.src = '/video_feed';
        serverBackVideo.style.display = 'block';
        backFallback.style.display = 'none';
    }
}

// Map initialization
function initializeMap() {
    // Check if map container exists
    if (!document.getElementById('map')) return;

    const statusEl = document.getElementById('map-status');

    // Get user location first
    if (navigator.geolocation) {
        if (statusEl) statusEl.textContent = 'Acquiring real-time location (this may take a moment)...';

        // Options for better accuracy and timeout handling
        const geoOptions = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };

        navigator.geolocation.getCurrentPosition(
            function(position) {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                // Initialize Google Map with user location
                initializeGoogleMap(userLocation.lat, userLocation.lng);
                
                if (statusEl) statusEl.textContent = 'Location locked. Fetching safe places...';
                
                // Load safe places ONLY after getting real location
                loadSafePlaces();
            },
            function(error) {
                console.error('Geolocation error:', error);
                
                let errorMsg = "";
                let errorDetails = "";
                
                // DETAILED ERROR MESSAGES
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = "📍 Location Access Required";
                        errorDetails = "To show nearby safe places, this app needs your location. Click 'Allow' when prompted by your browser.";
                        showLocationPermissionGuide();
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = "📍 Location Unavailable";
                        errorDetails = "Your device cannot determine location. Try moving to an open area or check your GPS settings.";
                        break;
                    case error.TIMEOUT:
                        errorMsg = "📍 Location Timeout";
                        errorDetails = "Location request timed out. This may take longer in areas with poor signal.";
                        break;
                }

                if (statusEl) {
                    statusEl.innerHTML = `
                        <div style="text-align: center;">
                            <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">${errorMsg}</div>
                            <div style="font-size: 14px; margin-bottom: 12px;">${errorDetails}</div>
                            <button onclick="requestLocationAccess()" style="padding: 8px 16px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                🔄 Try Again
                            </button>
                        </div>
                    `;
                    statusEl.style.color = '#333';
                }
            },
            geoOptions // Pass the options here
        );
    } else {
        if (statusEl) {
            statusEl.textContent = 'GPS ERROR: Not supported by browser.';
            statusEl.style.color = 'red';
        }
        // Alert removed - using status display instead
    }
}

function initializeGoogleMap(lat, lng) {
    // MapLibre GL JS Map initialization
    map = new maplibregl.Map({
        container: 'map',
        style: 'https://demotiles.maplibre.org/style.json',
        center: [lng, lat],
        zoom: 15
    });

    // Add navigation controls
    map.addControl(new maplibregl.NavigationControl());

    // Add user marker using a custom div element
    const userMarkerEl = document.createElement('div');
    userMarkerEl.className = 'custom-marker user-marker';
    userMarkerEl.innerHTML = '<div class="marker-dot" style="background-color: #4285f4; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>';
    
    const userMarker = new maplibregl.Marker(userMarkerEl)
        .setLngLat([lng, lat])
        .addTo(map);

    // Create popup for user location
    const userPopup = new maplibregl.Popup({ offset: 25 }).setHTML(
        '<div style="font-family: Arial, sans-serif;"><strong>Your Current Location</strong></div>'
    );

    userMarker.setPopup(userPopup);
}

function loadSafePlaces() {
    if (!userLocation) return;
    
    console.log('Safe places fetch:', `/api/safe_places?lat=${userLocation.lat}&lng=${userLocation.lng}`);
    apiFetch(`/api/safe_places?lat=${userLocation.lat}&lng=${userLocation.lng}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const places = data.places || [];
            
            // Filter places within 5 km
            const nearbyPlaces = places.filter(p => p.distance <= 5.0);
            
            if (nearbyPlaces.length === 0) {
                 const statusEl = document.getElementById('map-status');
                 if (statusEl) statusEl.textContent = 'No safe places found nearby in real-time database.';
                 return;
            }

            // Clear existing markers (if any)
            clearSafePlaceMarkers();
            
            // Add markers with popups - initialize bounds
            const bounds = [[userLocation.lng, userLocation.lat]];
            
            nearbyPlaces.forEach(place => {
                // Create marker element using the custom icon
                const markerEl = getPlaceIcon(place.type);
                
                // Create MapLibre marker
                const marker = new maplibregl.Marker(markerEl)
                    .setLngLat([place.lng, place.lat])
                    .addTo(map);

                // Create popup with place information
                const popup = new maplibregl.Popup({ offset: 25 })
                    .setHTML(createPlacePopup(place));

                // Add click event to show popup
                marker.getElement().addEventListener('click', function() {
                    // Close any other open popups
                    closeAllInfoWindows();
                    popup.addTo(map);
                });

                // Store reference for cleanup
                safePlaceMarkers.push({ marker: marker, popup: popup });
                bounds.push([place.lng, place.lat]);
            });
            
            // Fit map to show all markers
            if (nearbyPlaces.length > 0 && bounds.length > 1) {
                const mapBounds = bounds;
                map.fitBounds(mapBounds, { padding: 50 });
            }
            
            const statusEl = document.getElementById('map-status');
            if (statusEl) {
                statusEl.textContent = `Found ${nearbyPlaces.length} verified safe places nearby`;
            }
            
            addLog('info', `Loaded ${nearbyPlaces.length} verified safe places`);
        })
        .catch(error => {
            if (error.message !== "Unauthorized") {
                console.error('Error loading safe places:', error);
                addLog('error', 'Failed to fetch safe places');
            }
        });
}

// Global array to store markers and info windows
let safePlaceMarkers = [];

function clearSafePlaceMarkers() {
    safePlaceMarkers.forEach(item => {
        item.marker.setMap(null);
    });
    safePlaceMarkers = [];
}

function closeAllInfoWindows() {
    safePlaceMarkers.forEach(item => {
        if (item.popup) {
            item.popup.remove();
        }
    });
}

function createPlacePopup(place) {
    const phone = place.phone && place.phone !== "N/A" ? `<p><i class="fas fa-phone"></i> ${place.phone}</p>` : '';
    const rating = place.rating ? `<p><i class="fas fa-star"></i> ${place.rating}/5.0</p>` : '';
    const distance = place.distance ? `<p><i class="fas fa-route"></i> ${place.distance.toFixed(2)} km away</p>` : '';
    const address = place.address ? `<p><i class="fas fa-map-marker-alt"></i> ${place.address}</p>` : '';
    
    // Directions link using OpenStreetMap
    const directionsUrl = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${userLocation.lat}%2C${userLocation.lng}%3B${place.lat}%2C${place.lng}`;
    
    return `
        <div class="place-popup" style="max-width: 250px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 8px 0; color: #333; font-size: 16px;">${escapeHtml(place.name)}</h3>
            <p style="margin: 4px 0; font-weight: bold; color: #666; text-transform: uppercase;">${escapeHtml(place.type)}</p>
            ${distance}
            ${address}
            ${phone}
            ${rating}
            <div style="margin-top: 10px;">
                <a href="${directionsUrl}" target="_blank" 
                   style="display: inline-block; padding: 8px 12px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; font-size: 14px;">
                    <i class="fas fa-directions"></i> Get Directions
                </a>
            </div>
        </div>
    `;
}

function getPlaceIcon(type) {
    // Create custom marker elements based on place type
    const markerEl = document.createElement('div');
    markerEl.className = 'custom-marker';
    
    let color = '#4285f4'; // default blue for other places
    if (type.includes('police')) {
        color = '#ea4335'; // red for police
    } else if (type.includes('hospital')) {
        color = '#34a853'; // green for hospitals
    }
    
    markerEl.innerHTML = `<div class="marker-dot" style="background-color: ${color}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`;
    
    return markerEl;
}

// Chart initialization
function initializeChart() {
    const ctx = document.getElementById('threat-chart').getContext('2d');
    threatChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Threat Score',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 1.0 }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// Enhanced event listeners with better error handling
function initializeEventListeners() {
    const startBtn = document.getElementById('start-monitoring');
    if (startBtn) {
        startBtn.addEventListener('click', startMonitoring);
        // Add visual feedback on hover
        startBtn.addEventListener('mouseenter', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(-2px)';
            }
        });
        startBtn.addEventListener('mouseleave', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(0)';
            }
        });
    }
    
    const stopBtn = document.getElementById('stop-monitoring');
    if (stopBtn) {
        stopBtn.addEventListener('click', stopMonitoring);
        // Add visual feedback on hover
        stopBtn.addEventListener('mouseenter', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(-2px)';
            }
        });
        stopBtn.addEventListener('mouseleave', function() {
            if (!this.disabled) {
                this.style.transform = 'translateY(0)';
            }
        });
    }
    
    const sosBtn = document.getElementById('sos-btn');
    if (sosBtn) {
        sosBtn.addEventListener('click', triggerSOS);
    }
    
    // Enhanced chatbot functionality
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSendBtn = document.getElementById('chatbot-send');
    
    if (chatbotInput && chatbotSendBtn) {
        chatbotSendBtn.addEventListener('click', sendChatbotMessage);
        chatbotInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatbotMessage();
            }
        });
    }
    
    // Auto-alert toggle functionality
    const autoAlertToggle = document.getElementById('auto-alert-toggle');
    if (autoAlertToggle) {
        autoAlertToggle.addEventListener('change', function() {
            const isEnabled = this.checked;
            addLog('info', `Auto-Alert Mode ${isEnabled ? 'enabled' : 'disabled'}`);
            showNotification(`Auto-Alert Mode ${isEnabled ? 'enabled' : 'disabled'}`, 'info');
        });
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + M to start/stop monitoring
        if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
            e.preventDefault();
            if (isMonitoring) {
                stopMonitoring();
            } else {
                startMonitoring();
            }
        }
        
        // Ctrl/Cmd + S for SOS
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            triggerSOS();
        }
    });
    
    // Add connection status monitoring
    window.addEventListener('online', function() {
        showNotification('Connection restored', 'success');
        addLog('info', 'Internet connection restored');
    });
    
    window.addEventListener('offline', function() {
        showNotification('Connection lost - some features may not work', 'warning');
        addLog('warning', 'Internet connection lost');
    });
    
    // Add user feedback for admin mode
    if (document.querySelector('.admin-notice')) {
        console.log('Admin mode detected - all features available');
    }
}

function startMonitoring() {
    apiFetch('/api/start_monitoring', {
        method: 'POST'
    })
    .then(response => {
        if (response.status === 401) {
            window.location.href = '/user-login';
            return;
        }
        if (!response.ok) {
            throw new Error('Server error: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        isMonitoring = true;
        document.getElementById('start-monitoring').style.display = 'none';
        document.getElementById('stop-monitoring').style.display = 'inline-block';
        
        monitoringInterval = setInterval(updateThreatStatus, 1000);
        updateThreatStatus();
        updateRecommendations();
        addLog('success', 'Threat monitoring started');
    })
    .catch(error => {
        console.error('Start monitoring error:', error);
        addLog('error', 'Login required or server error');
        if (error.message.includes('401') || error.message.includes('login')) {
            window.location.href = '/user-login';
        }
    });
}


function stopMonitoring() {
    apiFetch('/api/stop_monitoring', { method: 'POST' })
    .then(async response => {
        if (response.status === 401) {
            window.location.href = '/user-login';
            return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        isMonitoring = false;
        document.getElementById('start-monitoring').style.display = 'inline-block';
        document.getElementById('stop-monitoring').style.display = 'none';
        if (monitoringInterval) clearInterval(monitoringInterval);
        addLog('info', 'Threat monitoring stopped');
    })
    .catch(error => {
        console.error('Stop monitoring error:', error);
        if (error.message.includes('401')) {
            window.location.href = '/user-login';
        }
    });
}


function updateThreatStatus() {
    fetch('/api/threat_status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('status-value').textContent = data.state;
            document.getElementById('status-score').textContent = data.score.toFixed(2);
            document.getElementById('status-chip').className = 'status-chip status-' + data.state.toLowerCase();
            
            // Update bars
            const speechPercent = (data.speech_contribution * 100).toFixed(0);
            const motionPercent = (data.motion_contribution * 100).toFixed(0);
            document.getElementById('speech-progress').style.width = speechPercent + '%';
            document.getElementById('speech-value').textContent = speechPercent + '%';
            document.getElementById('motion-progress').style.width = motionPercent + '%';
            document.getElementById('motion-value').textContent = motionPercent + '%';
            
            // Update chart
            if (data.score !== undefined && threatChart) {
                const now = new Date().toLocaleTimeString();
                threatChart.data.labels.push(now);
                threatChart.data.datasets[0].data.push(data.score);
                if (threatChart.data.labels.length > 30) {
                    threatChart.data.labels.shift();
                    threatChart.data.datasets[0].data.shift();
                }
                threatChart.update();
            }
            
            if (data.state === 'HIGH' || data.state === 'CRITICAL') {
                checkAutoAlert(data.state);
            }
        });
}

function updateRecommendations() {
    fetch('/api/recommendations')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const list = document.getElementById('recommendations-list');
            if (list && data.recommendations) {
                list.innerHTML = '';
                data.recommendations.forEach((rec, index) => {
                    const li = document.createElement('li');
                    li.textContent = rec;
                    li.style.animationDelay = `${index * 0.1}s`;
                    list.appendChild(li);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching recommendations:', error);
            
            // Show fallback recommendations
            const list = document.getElementById('recommendations-list');
            if (list) {
                list.innerHTML = '';
                const fallbackRecommendations = [
                    'Stay aware of your surroundings',
                    'Keep your phone charged and accessible',
                    'Trust your instincts if something feels off'
                ];
                
                fallbackRecommendations.forEach((rec, index) => {
                    const li = document.createElement('li');
                    li.textContent = rec;
                    li.style.animationDelay = `${index * 0.1}s`;
                    list.appendChild(li);
                });
            }
        });
    setTimeout(updateRecommendations, 5000);
}

function triggerSOS() {
    if (!confirm('Are you sure you want to trigger SOS? This will alert your emergency contacts.')) return;
    
    apiFetch('/api/trigger_sos', { method: 'POST' })
    .then(async response => {
        if (response.status === 401) {
            window.location.href = '/user-login';
            return;
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        addLog('critical', `SOS TRIGGERED: ${data.message}`);
        alert('SOS Activated! Your emergency contacts have been notified.');
        updateThreatStatus();
    })
    .catch(error => {
        console.error('SOS error:', error);
        if (error.message.includes('401')) {
            window.location.href = '/user-login';
        }
    });
}


function addLog(severity, message) {
    const container = document.getElementById('logs-container');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${severity}`;
    logEntry.innerHTML = `<span class="log-time">${new Date().toLocaleTimeString()}</span><span class="log-message">${message}</span>`;
    container.insertBefore(logEntry, container.firstChild);
    while (container.children.length > 50) container.removeChild(container.lastChild);
}

// Chatbot functionality
let autoAlertEnabled = false;

function initializeChatbot() {
    const sendBtn = document.getElementById('chatbot-send');
    const input = document.getElementById('chatbot-input');
    const autoAlertToggle = document.getElementById('auto-alert-toggle');
    
    if (autoAlertToggle) {
        autoAlertToggle.addEventListener('change', function() {
            autoAlertEnabled = this.checked;
        });
    }
    
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            sendChatMessage();
        });
    }
    
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
}

function checkAutoAlert(threatLevel) {
    if (autoAlertEnabled) triggerAutoAlert(threatLevel);
}

function triggerAutoAlert(threatLevel) {
    secureFetch('/api/chatbot/auto_alert', {
        method: 'POST',
        body: JSON.stringify({
            threat_level: threatLevel,
            auto_alert: true,
            lat: userLocation ? userLocation.lat : null,
            lng: userLocation ? userLocation.lng : null
        })
    }).then(r => r.json()).then(data => {
        if (data.status === 'alert_sent') {
            const messagesContainer = document.getElementById('chatbot-messages');
            const alertMsg = document.createElement('div');
            alertMsg.className = 'chat-message bot';
            alertMsg.style.background = '#dc3545';
            alertMsg.style.color = 'white';
            alertMsg.innerHTML = `<p><i class="fas fa-exclamation-triangle"></i> ${data.message}</p>`;
            messagesContainer.appendChild(alertMsg);
        }
    });
}

function sendChatMessage() {
    const input = document.getElementById('chatbot-input');
    const messagesContainer = document.getElementById('chatbot-messages');
    const message = input.value.trim();
    if (!message) return;
    
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-message user';
    userMsg.innerHTML = `<p>${escapeHtml(message)}</p>`;
    messagesContainer.appendChild(userMsg);
    input.value = '';
    
    secureFetch('/api/chatbot', {
        method: 'POST',
        body: JSON.stringify({
            message: message,
            lat: userLocation ? userLocation.lat : null,
            lng: userLocation ? userLocation.lng : null
        })
    })
    .then(r => r.json())
    .then(data => {
        const botMsg = document.createElement('div');
        botMsg.className = 'chat-message bot';
        botMsg.innerHTML = `<p>${escapeHtml(data.response)}</p>`;
        messagesContainer.appendChild(botMsg);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Enhanced chatbot functionality
function sendChatbotMessage() {
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSendBtn = document.getElementById('chatbot-send');
    const chatbotMessages = document.getElementById('chatbot-messages');
    
    if (!chatbotInput || !chatbotSendBtn || !chatbotMessages) {
        console.error('Chatbot elements not found');
        return;
    }
    
    const message = chatbotInput.value.trim();
    if (!message) return;
    
    // Add user message
    addChatMessage(message, 'user');
    chatbotInput.value = '';
    
    // Disable send button and show loading
    chatbotSendBtn.disabled = true;
    chatbotSendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    // Send to server
    secureFetch('/api/chatbot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            lat: userLocation ? userLocation.lat : null,
            lng: userLocation ? userLocation.lng : null
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data && data.response) {
            addChatMessage(data.response, 'bot', data);
        } else {
            addChatMessage("I couldn't process that request. Please try again.", 'bot');
        }
    })
    .catch(error => {
        console.error('Chatbot error:', error);
        addChatMessage("Sorry, I'm having trouble connecting right now. Please try again later.", 'bot');
    })
    .finally(() => {
        // Re-enable send button
        chatbotSendBtn.disabled = false;
        chatbotSendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    });
}

function addChatMessage(message, sender, data = null) {
    const chatbotMessages = document.getElementById('chatbot-messages');
    if (!chatbotMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    
    let content = '';
    if (sender === 'bot') {
        // Handle bot responses with rich content
        if (data && data.places) {
            content = `<p>${escapeHtml(message)}</p>`;
            data.places.forEach(place => {
                content += `
                    <div class="place-popup">
                        <h3>${escapeHtml(place.name)}</h3>
                        <p><i class="fas fa-map-marker-alt"></i> ${escapeHtml(place.address || 'Address not available')}</p>
                        <p><i class="fas fa-phone"></i> ${escapeHtml(place.phone || 'Phone not available')}</p>
                        <a href="https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}" 
                           target="_blank" class="btn-directions">
                            <i class="fas fa-directions"></i> Get Directions
                        </a>
                    </div>
                `;
            });
        } else if (data && data.tips) {
            content = `<p>${escapeHtml(message)}</p><ul>`;
            data.tips.forEach(tip => {
                content += `<li>${escapeHtml(tip)}</li>`;
            });
            content += '</ul>';
        } else {
            content = `<p>${escapeHtml(message)}</p>`;
        }
    } else {
        content = `<p>${escapeHtml(message)}</p>`;
    }
    
    messageDiv.innerHTML = content;
    chatbotMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}

// Enhanced notification system
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Set icon based on type
    const icons = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="${icons[type] || icons.info}"></i>
            <span>${escapeHtml(message)}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add to DOM
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, duration);
    
    // Add to logs
    if (type === 'error') {
        addLog('error', message);
    } else if (type === 'success') {
        addLog('success', message);
    }
}

// Helper functions for location permission handling
function showLocationPermissionGuide() {
    const guide = document.createElement('div');
    guide.id = 'location-guide';
    guide.innerHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); z-index: 10000; max-width: 400px; text-align: center;">
            <h3 style="margin-top: 0; color: #4285f4;">📍 Enable Location Access</h3>
            <p><strong>To use this app effectively:</strong></p>
            <ol style="text-align: left; margin: 10px 0;">
                <li>Click the location icon in your browser's address bar</li>
                <li>Select "Allow" for location access</li>
                <li>Refresh the page if needed</li>
            </ol>
            <div style="margin-top: 15px;">
                <button onclick="closeLocationGuide()" style="padding: 8px 16px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px;">
                    Got it!
                </button>
                <button onclick="requestLocationAccess()" style="padding: 8px 16px; background: #34a853; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Try Again
                </button>
            </div>
        </div>
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999;" onclick="closeLocationGuide()"></div>
    `;
    document.body.appendChild(guide);
}

function closeLocationGuide() {
    const guide = document.getElementById('location-guide');
    if (guide) {
        guide.remove();
    }
}

function requestLocationAccess() {
    closeLocationGuide();
    
    const statusEl = document.getElementById('map-status');
    if (statusEl) {
        statusEl.innerHTML = '<div style="text-align: center;">🔄 Requesting location access...</div>';
    }
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            
            // Initialize map with user location
            initializeGoogleMap(userLocation.lat, userLocation.lng);
            
            if (statusEl) {
                statusEl.textContent = 'Location locked. Fetching safe places...';
            }
            
            // Load safe places
            loadSafePlaces();
        },
        function(error) {
            console.error('Geolocation retry error:', error);
            
            let errorMsg = "";
            let errorDetails = "";
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMsg = "📍 Location Access Still Required";
                    errorDetails = "Please allow location access in your browser settings to continue.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMsg = "📍 Location Unavailable";
                    errorDetails = "Your device cannot determine location. Try moving to an open area.";
                    break;
                case error.TIMEOUT:
                    errorMsg = "📍 Location Timeout";
                    errorDetails = "Location request timed out. Please try again.";
                    break;
            }
            
            if (statusEl) {
                statusEl.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 18px; font-weight: bold; margin-bottom: 8px;">${errorMsg}</div>
                        <div style="font-size: 14px; margin-bottom: 12px;">${errorDetails}</div>
                        <button onclick="requestLocationAccess()" style="padding: 8px 16px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            🔄 Try Again
                        </button>
                    </div>
                `;
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}
