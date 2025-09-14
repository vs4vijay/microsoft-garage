class DroneCommandCenter {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.videoStream = null;
        this.speechRecognition = null;
        this.speechSynthesis = window.speechSynthesis;
        this.settings = this.loadSettings();
        
        this.initializeElements();
        this.setupEventListeners();
        this.initializeControlsState();
        this.initializeSpeechRecognition();
        this.startVideoStream();
        this.connectToServer();
        
        // Hide loading overlay after initialization
        setTimeout(() => {
            document.getElementById('loadingOverlay').classList.add('hidden');
        }, 2000);
    }

    initializeElements() {
        // Connection status
        this.connectionStatus = document.getElementById('connectionStatus');
        
        // Video elements
        this.videoFeed = document.getElementById('videoFeed');
        this.videoResolution = document.getElementById('videoResolution');
        this.videoFps = document.getElementById('videoFps');
        
        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.voiceIndicator = document.getElementById('voiceIndicator');
        
        // Status elements
        this.batteryLevel = document.getElementById('batteryLevel');
        this.altitude = document.getElementById('altitude');
        this.speed = document.getElementById('speed');
        this.heading = document.getElementById('heading');
        this.flightMode = document.getElementById('flightMode');
        this.signalStrength = document.getElementById('signalStrength');
        
        // Log elements
        this.logMessages = document.getElementById('logMessages');
        
        // Control elements
        this.distanceSlider = document.getElementById('distanceSlider');
        this.distanceValue = document.getElementById('distanceValue');
        
        // Modal elements
        this.settingsModal = document.getElementById('settingsModal');
    }

    initializeControlsState() {
        // Restore collapsed state from localStorage
        const isCollapsed = localStorage.getItem('controlsCollapsed') === 'true';
        if (isCollapsed) {
            const controlsContent = document.getElementById('controlsContent');
            const toggleBtn = document.getElementById('controlsToggle');
            controlsContent.classList.add('collapsed');
            toggleBtn.classList.add('collapsed');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            this.adjustChatLayout();
        }
    }

    setupEventListeners() {
        // Header buttons
        document.getElementById('emergencyStop').addEventListener('click', () => this.emergencyStop());
        document.getElementById('settingsBtn').addEventListener('click', () => this.openSettings());

        // Video controls
        document.getElementById('toggleCamera').addEventListener('click', () => this.toggleCamera());
        document.getElementById('takeSnapshot').addEventListener('click', () => this.takeSnapshot());
        document.getElementById('recordToggle').addEventListener('click', () => this.toggleRecording());

        // Manual controls
        document.querySelectorAll('.control-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.currentTarget.dataset.command;
                this.executeManualCommand(command);
            });
        });

        // Distance slider
        this.distanceSlider.addEventListener('input', (e) => {
            this.distanceValue.textContent = e.target.value;
        });

        // Controls collapse toggle
        document.getElementById('controlsToggle').addEventListener('click', () => this.toggleControls());

        // Mission controls
        document.getElementById('startMission').addEventListener('click', () => this.startMission());
        document.getElementById('pauseMission').addEventListener('click', () => this.pauseMission());

        // Chat controls
        document.getElementById('sendMessage').addEventListener('click', () => this.sendMessage());
        document.getElementById('voiceInput').addEventListener('click', () => this.toggleVoiceInput());
        document.getElementById('voiceToggle').addEventListener('click', () => this.toggleSpeechOutput());
        document.getElementById('clearChat').addEventListener('click', () => this.clearChat());

        // Message input
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });

        // Settings modal
        document.getElementById('closeSettings').addEventListener('click', () => this.closeSettings());
        document.getElementById('cancelSettings').addEventListener('click', () => this.closeSettings());
        document.getElementById('saveSettings').addEventListener('click', () => this.saveSettings());

        // Close modal when clicking outside
        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) {
                this.closeSettings();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    initializeSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRecognition();
            this.speechRecognition.continuous = false;
            this.speechRecognition.interimResults = false;
            this.speechRecognition.lang = 'en-US';

            this.speechRecognition.onstart = () => {
                this.isRecording = true;
                document.getElementById('voiceInput').classList.add('recording');
                this.voiceIndicator.classList.add('active');
                this.addLogEntry('Speech recognition started');
            };

            this.speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.messageInput.value = transcript;
                this.addChatMessage(transcript, 'user');
                this.sendToAgent(transcript);
            };

            this.speechRecognition.onend = () => {
                this.isRecording = false;
                document.getElementById('voiceInput').classList.remove('recording');
                this.voiceIndicator.classList.remove('active');
                this.addLogEntry('Speech recognition ended');
            };

            this.speechRecognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.addLogEntry(`Speech recognition error: ${event.error}`);
                this.isRecording = false;
                document.getElementById('voiceInput').classList.remove('recording');
                this.voiceIndicator.classList.remove('active');
            };
        } else {
            console.warn('Speech recognition not supported');
            this.addLogEntry('Speech recognition not supported in this browser');
        }
    }

    async startVideoStream() {
        try {
            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 }
                },
                audio: false
            };

            this.videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoFeed.srcObject = this.videoStream;
            
            const track = this.videoStream.getVideoTracks()[0];
            const settings = track.getSettings();
            this.videoResolution.textContent = `${settings.width}x${settings.height}`;
            this.videoFps.textContent = `${settings.frameRate} FPS`;
            
            this.addLogEntry('Video stream started');
        } catch (error) {
            console.error('Error starting video stream:', error);
            this.addLogEntry(`Video stream error: ${error.message}`);
            
            // Show placeholder image or message
            this.videoFeed.style.background = 'linear-gradient(45deg, #1a1a2e, #16213e)';
            this.videoResolution.textContent = 'No Camera';
            this.videoFps.textContent = '0 FPS';
        }
    }

    connectToServer() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.isConnected = true;
                this.updateConnectionStatus('connected');
                this.addLogEntry('Connected to Drone Command Center server');
                
                // Send initial configuration
                this.sendToServer({
                    type: 'configure',
                    settings: this.settings
                });
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleServerMessage(data);
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.addLogEntry('Disconnected from server');
                
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.connectToServer(), 5000);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.addLogEntry('Connection error');
            };
        } catch (error) {
            console.error('Failed to connect to server:', error);
            this.addLogEntry('Failed to connect to server');
            
            // Simulate offline mode for demo
            this.simulateOfflineMode();
        }
    }

    simulateOfflineMode() {
        this.addLogEntry('Running in offline simulation mode');
        this.updateConnectionStatus('simulation');
        
        // Simulate status updates
        setInterval(() => {
            this.updateDroneStatus({
                battery: Math.max(20, Math.floor(Math.random() * 100)),
                altitude: Math.floor(Math.random() * 200),
                speed: Math.floor(Math.random() * 10),
                heading: Math.floor(Math.random() * 360),
                flightMode: 'Simulation',
                signalStrength: Math.floor(Math.random() * 100)
            });
        }, 2000);
    }

    handleServerMessage(data) {
        switch (data.type) {
            case 'status_update':
                this.updateDroneStatus(data.status);
                break;
            case 'chat_response':
                this.addChatMessage(data.message, 'assistant');
                if (this.settings.speechOutput && data.audio) {
                    this.playAudioResponse(data.audio);
                } else if (this.settings.speechOutput) {
                    this.speakText(data.message);
                }
                break;
            case 'log_entry':
                this.addLogEntry(data.message);
                break;
            case 'video_frame':
                this.updateVideoFrame(data.frame);
                break;
            case 'error':
                this.addLogEntry(`Error: ${data.message}`);
                break;
        }
    }

    sendToServer(data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected');
            // Handle offline mode
            this.handleOfflineCommand(data);
        }
    }

    handleOfflineCommand(data) {
        // Simulate responses for demo purposes
        if (data.type === 'chat') {
            setTimeout(() => {
                const responses = [
                    "I understand your command. In real mode, I would execute this action.",
                    "Command received. Currently in simulation mode.",
                    "I'm ready to help! Switch to real drone mode to execute commands.",
                    "Simulation mode active. I can see and respond but cannot control a real drone."
                ];
                const response = responses[Math.floor(Math.random() * responses.length)];
                this.addChatMessage(response, 'assistant');
                if (this.settings.speechOutput) {
                    this.speakText(response);
                }
            }, 1000);
        }
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        this.addChatMessage(message, 'user');
        this.sendToAgent(message);
        this.messageInput.value = '';
    }

    sendToAgent(message) {
        this.sendToServer({
            type: 'chat',
            message: message,
            timestamp: new Date().toISOString()
        });
    }

    addChatMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (sender === 'assistant') {
            contentDiv.innerHTML = `<i class="fas fa-robot"></i> ${content}`;
        } else if (sender === 'system') {
            contentDiv.innerHTML = `<i class="fas fa-info-circle"></i> ${content}`;
        } else {
            contentDiv.textContent = content;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        this.chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    toggleVoiceInput() {
        if (!this.speechRecognition) {
            this.addLogEntry('Speech recognition not available');
            return;
        }

        if (this.isRecording) {
            this.speechRecognition.stop();
        } else {
            this.speechRecognition.start();
        }
    }

    toggleSpeechOutput() {
        this.settings.speechOutput = !this.settings.speechOutput;
        this.saveSettings();
        
        const btn = document.getElementById('voiceToggle');
        btn.style.background = this.settings.speechOutput ? 
            'linear-gradient(135deg, #00d4aa 0%, #01a085 100%)' : 
            'rgba(255, 255, 255, 0.1)';
            
        this.addLogEntry(`Speech output ${this.settings.speechOutput ? 'enabled' : 'disabled'}`);
    }

    speakText(text) {
        if (this.speechSynthesis && this.settings.speechOutput) {
            this.speechSynthesis.cancel(); // Cancel any ongoing speech
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 0.8;
            
            this.speechSynthesis.speak(utterance);
        }
    }

    playAudioResponse(audioData) {
        // Convert base64 to blob and play
        const audioBlob = this.base64ToBlob(audioData, 'audio/pcm');
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play().catch(console.error);
    }

    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }

    executeManualCommand(command) {
        const distance = parseInt(this.distanceSlider.value);
        let commandData = { type: 'manual_command', command: command };
        
        if (['move_forward', 'move_backward', 'move_left', 'move_right', 'move_up', 'move_down'].includes(command)) {
            commandData.distance = distance;
        }
        
        this.sendToServer(commandData);
        this.addLogEntry(`Manual command: ${command}${distance ? ` (${distance}cm)` : ''}`);
    }

    toggleControls() {
        const controlsContent = document.getElementById('controlsContent');
        const toggleBtn = document.getElementById('controlsToggle');
        const isCollapsed = controlsContent.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Expand controls
            controlsContent.classList.remove('collapsed');
            toggleBtn.classList.remove('collapsed');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
            localStorage.setItem('controlsCollapsed', 'false');
        } else {
            // Collapse controls
            controlsContent.classList.add('collapsed');
            toggleBtn.classList.add('collapsed');
            toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            localStorage.setItem('controlsCollapsed', 'true');
        }
        
        // Trigger layout adjustment for better chat experience
        this.adjustChatLayout();
    }

    adjustChatLayout() {
        const controlsContent = document.getElementById('controlsContent');
        const chatSection = document.querySelector('.chat-section');
        const isCollapsed = controlsContent.classList.contains('collapsed');
        
        if (isCollapsed) {
            // Give more space to chat when controls are collapsed
            chatSection.style.flex = '1';
        } else {
            // Reset chat layout when controls are expanded
            chatSection.style.flex = '';
        }
    }

    emergencyStop() {
        this.sendToServer({ type: 'emergency_stop' });
        this.addLogEntry('EMERGENCY STOP ACTIVATED');
        this.addChatMessage('Emergency stop activated!', 'system');
    }

    toggleCamera() {
        if (this.videoStream) {
            const videoTrack = this.videoStream.getVideoTracks()[0];
            videoTrack.enabled = !videoTrack.enabled;
            this.addLogEntry(`Camera ${videoTrack.enabled ? 'enabled' : 'disabled'}`);
        }
    }

    takeSnapshot() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = this.videoFeed.videoWidth;
        canvas.height = this.videoFeed.videoHeight;
        
        ctx.drawImage(this.videoFeed, 0, 0);
        
        // Download the image
        const link = document.createElement('a');
        link.download = `drone_snapshot_${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
        
        this.addLogEntry('Snapshot captured');
    }

    toggleRecording() {
        if (!this.mediaRecorder) {
            this.startRecording();
        } else {
            this.stopRecording();
        }
    }

    startRecording() {
        if (!this.videoStream) return;
        
        this.mediaRecorder = new MediaRecorder(this.videoStream);
        this.recordedChunks = [];
        
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.recordedChunks.push(event.data);
            }
        };
        
        this.mediaRecorder.onstop = () => {
            const blob = new Blob(this.recordedChunks, { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.download = `drone_recording_${Date.now()}.webm`;
            link.href = url;
            link.click();
            
            this.addLogEntry('Recording saved');
        };
        
        this.mediaRecorder.start();
        document.getElementById('recordToggle').style.background = 'linear-gradient(135deg, #ff4757 0%, #c44569 100%)';
        this.addLogEntry('Recording started');
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder = null;
            document.getElementById('recordToggle').style.background = 'rgba(255, 255, 255, 0.1)';
            this.addLogEntry('Recording stopped');
        }
    }

    startMission() {
        const missionType = document.getElementById('missionType').value;
        this.sendToServer({
            type: 'start_mission',
            mission_type: missionType
        });
        this.addLogEntry(`Mission started: ${missionType}`);
    }

    pauseMission() {
        this.sendToServer({ type: 'pause_mission' });
        this.addLogEntry('Mission paused');
    }

    updateDroneStatus(status) {
        this.batteryLevel.textContent = `${status.battery}%`;
        this.altitude.textContent = `${status.altitude}cm`;
        this.speed.textContent = `${status.speed}cm/s`;
        this.heading.textContent = `${status.heading}°`;
        this.flightMode.textContent = status.flightMode;
        this.signalStrength.textContent = `${status.signalStrength}%`;
        
        // Update battery color based on level
        const batteryIcon = this.batteryLevel.parentElement.querySelector('.status-icon');
        if (status.battery < 20) {
            batteryIcon.style.color = '#ff4757';
        } else if (status.battery < 50) {
            batteryIcon.style.color = '#ffa502';
        } else {
            batteryIcon.style.color = '#00d4aa';
        }
    }

    updateConnectionStatus(status) {
        const statusElement = this.connectionStatus;
        const statusText = statusElement.querySelector('span');
        
        statusElement.className = `connection-status ${status}`;
        
        switch (status) {
            case 'connected':
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusText.textContent = 'Disconnected';
                break;
            case 'simulation':
                statusText.textContent = 'Simulation Mode';
                break;
        }
    }

    addLogEntry(message) {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'log-time';
        timeSpan.textContent = new Date().toLocaleTimeString();
        
        const messageSpan = document.createElement('span');
        messageSpan.className = 'log-message';
        messageSpan.textContent = message;
        
        logEntry.appendChild(timeSpan);
        logEntry.appendChild(messageSpan);
        this.logMessages.appendChild(logEntry);
        
        // Keep only last 50 log entries
        while (this.logMessages.children.length > 50) {
            this.logMessages.removeChild(this.logMessages.firstChild);
        }
        
        // Scroll to bottom
        this.logMessages.scrollTop = this.logMessages.scrollHeight;
    }

    clearChat() {
        this.chatMessages.innerHTML = '';
        this.addChatMessage('Chat cleared. How can I help you?', 'system');
    }

    openSettings() {
        this.loadSettingsToModal();
        this.settingsModal.classList.add('active');
    }

    closeSettings() {
        this.settingsModal.classList.remove('active');
    }

    loadSettingsToModal() {
        document.getElementById('realDroneMode').checked = this.settings.realDroneMode;
        document.getElementById('droneIP').value = this.settings.droneIP;
        document.getElementById('cameraSource').value = this.settings.cameraSource;
        document.getElementById('videoQuality').value = this.settings.videoQuality;
        document.getElementById('speechOutput').checked = this.settings.speechOutput;
        document.getElementById('speechInput').checked = this.settings.speechInput;
        document.getElementById('maxAltitude').value = this.settings.maxAltitude;
        document.getElementById('lowBatteryWarning').value = this.settings.lowBatteryWarning;
    }

    saveSettings() {
        this.settings = {
            realDroneMode: document.getElementById('realDroneMode').checked,
            droneIP: document.getElementById('droneIP').value,
            cameraSource: document.getElementById('cameraSource').value,
            videoQuality: document.getElementById('videoQuality').value,
            speechOutput: document.getElementById('speechOutput').checked,
            speechInput: document.getElementById('speechInput').checked,
            maxAltitude: parseInt(document.getElementById('maxAltitude').value),
            lowBatteryWarning: parseInt(document.getElementById('lowBatteryWarning').value)
        };
        
        localStorage.setItem('droneCommandCenterSettings', JSON.stringify(this.settings));
        this.addLogEntry('Settings saved');
        this.closeSettings();
        
        // Send updated settings to server
        this.sendToServer({
            type: 'update_settings',
            settings: this.settings
        });
    }

    loadSettings() {
        const defaultSettings = {
            realDroneMode: false,
            droneIP: '192.168.10.1',
            cameraSource: 'webcam',
            videoQuality: '720p',
            speechOutput: true,
            speechInput: true,
            maxAltitude: 300,
            lowBatteryWarning: 20
        };
        
        const savedSettings = localStorage.getItem('droneCommandCenterSettings');
        return savedSettings ? { ...defaultSettings, ...JSON.parse(savedSettings) } : defaultSettings;
    }

    handleKeyboardShortcuts(e) {
        // Emergency stop with Escape key
        if (e.key === 'Escape') {
            this.emergencyStop();
            return;
        }
        
        // Only handle shortcuts if not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key.toLowerCase()) {
            case ' ': // Spacebar for voice input
                e.preventDefault();
                this.toggleVoiceInput();
                break;
            case 't':
                this.executeManualCommand('takeoff');
                break;
            case 'l':
                this.executeManualCommand('land');
                break;
            case 'w':
                this.executeManualCommand('move_forward');
                break;
            case 's':
                this.executeManualCommand('move_backward');
                break;
            case 'a':
                this.executeManualCommand('move_left');
                break;
            case 'd':
                this.executeManualCommand('move_right');
                break;
            case 'q':
                this.executeManualCommand('move_up');
                break;
            case 'e':
                this.executeManualCommand('move_down');
                break;
        }
    }

    updateVideoFrame(frameData) {
        // Update video feed with frame from drone (for real drone mode)
        if (this.settings.cameraSource === 'drone') {
            // Convert base64 frame to blob URL and update video source
            const blob = this.base64ToBlob(frameData, 'image/jpeg');
            const url = URL.createObjectURL(blob);
            this.videoFeed.src = url;
        }
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.droneCommandCenter = new DroneCommandCenter();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, pause video if necessary
        if (window.droneCommandCenter && window.droneCommandCenter.videoFeed) {
            window.droneCommandCenter.videoFeed.pause();
        }
    } else {
        // Page is visible, resume video
        if (window.droneCommandCenter && window.droneCommandCenter.videoFeed) {
            window.droneCommandCenter.videoFeed.play();
        }
    }
});

// Handle beforeunload to clean up resources
window.addEventListener('beforeunload', () => {
    if (window.droneCommandCenter) {
        if (window.droneCommandCenter.websocket) {
            window.droneCommandCenter.websocket.close();
        }
        if (window.droneCommandCenter.videoStream) {
            window.droneCommandCenter.videoStream.getTracks().forEach(track => track.stop());
        }
    }
});