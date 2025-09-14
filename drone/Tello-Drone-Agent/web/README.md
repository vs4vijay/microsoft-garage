# 🚁🌐 Drone Command Center

A comprehensive web-based interface for controlling and monitoring drones with real-time video streaming, AI-powered chat, and advanced flight controls. Integrates seamlessly with the autonomous drone agent for intelligent flight operations.

## ✨ Features

### 🎮 Core Functionality
- **Real-time Web Interface**: Modern, responsive web UI for drone control
- **Live Video Streaming**: Camera feed from drone or webcam with crosshair overlay
- **AI Chat Assistant**: Natural language control with speech input/output
- **Manual Flight Controls**: Joystick-style controls with keyboard shortcuts
- **Mission Planning**: Automated flight patterns (patrol, circle, square, waypoints)
- **Emergency Safety**: One-click emergency stop with safety protocols
- **Real-time Telemetry**: Battery, altitude, speed, heading, and signal monitoring

### 🤖 AI Integration
- **GPT-4o Realtime API**: Direct integration with Azure OpenAI for intelligent responses
- **Speech-to-Speech**: Natural conversation with the drone
- **Vision Analysis**: Real-time image analysis for obstacle detection
- **Multi-modal Control**: Text, speech, and visual commands

### 🛡️ Safety Features
- **Emergency Stop**: Immediate drone shutdown capability
- **Battery Monitoring**: Low battery warnings and automatic landing
- **Connection Status**: Real-time monitoring of all system connections
- **Flight Boundaries**: Configurable altitude and distance limits
- **Obstacle Detection**: AI-powered vision analysis for safe navigation

### 📱 User Interface
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Theme**: Modern dark UI optimized for drone operations
- **Real-time Updates**: Live status updates via WebSocket
- **Settings Panel**: Configurable drone, camera, and audio settings
- **Flight Log**: Detailed logging of all operations and events

## 🚀 Quick Start

### Basic Mode (Vision Only - Safe for Testing)
```bash
# Windows
launch_command_center.bat

# Linux/Mac
./launch_command_center.sh
```

### Enhanced Mode (With AI Agent)
```bash
# Windows
launch_enhanced_command_center.bat

# Linux/Mac  
./launch_enhanced_command_center.sh
```

### Manual Installation
```bash
# 1. Install dependencies
pip install -r command_center/requirements.txt

# 2. Launch basic command center
cd command_center
python command_center_server.py --vision-only

# 3. Or launch enhanced version with AI
python enhanced_command_center.py --vision-only
```

## 🌐 Access the Interface

Once started, open your browser to:
**http://localhost:8000**

## 🎯 Usage Scenarios

### 1. **Remote Drone Monitoring**
- Monitor multiple drones from a central command center
- Real-time video feeds and telemetry data
- Emergency intervention capabilities

### 2. **Educational Drone Training**
- Safe simulation mode for learning drone operations
- Interactive controls with immediate feedback
- Mission planning and execution practice

### 3. **Autonomous Mission Control**
- AI-powered mission planning and execution
- Natural language mission commands
- Real-time adaptation based on environment

### 4. **Search and Rescue Operations**
- Video streaming for area surveillance
- Coordinated multi-drone operations
- Emergency response protocols

### 5. **Agricultural Monitoring**
- Automated crop inspection patterns
- Real-time field analysis
- Data collection and reporting

### 6. **Security and Surveillance**
- Perimeter patrol missions
- Motion detection and alerts
- Remote area monitoring

## 🎮 Controls

### Manual Controls
| Button | Action | Keyboard |
|--------|--------|----------|
| Takeoff | Launch drone | `T` |
| Land | Safe landing | `L` |
| Forward | Move forward | `W` |
| Backward | Move backward | `S` |
| Left | Move left | `A` |
| Right | Move right | `D` |
| Up | Altitude up | `Q` |
| Down | Altitude down | `E` |
| Emergency | Emergency stop | `ESC` |
| Voice | Speech input | `SPACE` |

### Chat Commands (Examples)
- "Take off and hover at 1 meter"
- "Move forward 50 centimeters"
- "Rotate 90 degrees clockwise"
- "Start a circle pattern"
- "What do you see? Check for obstacles"
- "Land safely"
- "Emergency stop"

## ⚙️ Configuration

### Environment Variables (Required for AI Mode)
```bash
export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'
export AZURE_OPENAI_API_KEY='your-api-key'
export AZURE_OPENAI_REALTIME_DEPLOYMENT='gpt-4o-realtime-preview'
```

### Settings Panel Options
- **Drone Mode**: Vision Only (simulation) / Real Drone
- **Camera Source**: Drone Camera / Webcam
- **Video Quality**: 720p / 480p / 360p
- **Speech Output**: Enable/disable AI voice responses
- **Speech Input**: Enable/disable voice commands
- **Safety Limits**: Max altitude, low battery warning threshold

## 🏗️ Architecture

### Components
1. **Web Frontend** (`index.html`, `style.css`, `script.js`)
   - Modern responsive UI with real-time updates
   - WebSocket communication for live data
   - Speech recognition and synthesis

2. **Command Center Server** (`command_center_server.py`)
   - FastAPI web server with WebSocket support
   - Video streaming and command processing
   - Basic drone simulation

3. **Enhanced Command Center** (`enhanced_command_center.py`)
   - Full integration with autonomous drone agent
   - GPT-4o Realtime API connectivity
   - Advanced AI-powered features

4. **Bridge Communication**
   - Seamless integration between web UI and drone agent
   - Real-time data synchronization
   - Fallback mechanisms for safety

### Data Flow
```
Web UI ←→ WebSocket ←→ Command Center Server ←→ Drone Agent ←→ GPT-4o API
   ↓                           ↓                       ↓
Camera Feed              Mission Control         Physical Drone
```

## 🔧 Development

### Project Structure
```
command_center/
├── index.html              # Main web interface
├── style.css               # UI styling
├── script.js               # Frontend logic
├── command_center_server.py # Basic web server
├── enhanced_command_center.py # AI-integrated server
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding New Features
1. **New UI Components**: Add to `index.html` and style in `style.css`
2. **Client Logic**: Extend `script.js` with new JavaScript functions
3. **Server Endpoints**: Add new handlers in the server files
4. **AI Commands**: Extend the drone agent's function registry

### API Endpoints
- `GET /`: Main web interface
- `WebSocket /ws`: Real-time communication
- `GET /health`: System health check
- `GET /style.css`: CSS styling
- `GET /script.js`: JavaScript client

## 🐛 Troubleshooting

### Common Issues

**Cannot connect to drone:**
- Ensure drone is powered on and in WiFi mode
- Check WiFi connection to drone network
- Verify drone IP address in settings

**AI agent not responding:**
- Check Azure OpenAI environment variables
- Verify internet connection
- Check Azure OpenAI service status

**Video feed not working:**
- Allow camera permissions in browser
- Check camera connection
- Try different video quality settings

**WebSocket connection issues:**
- Check firewall settings
- Ensure port 8000 is available
- Try different browser

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python command_center_server.py --vision-only
```

## 📄 License

This project is part of the Microsoft Garage Drone project. Please refer to the main project license.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues, questions, or feature requests:
1. Check the troubleshooting section
2. Review existing issues in the repository
3. Create a new issue with detailed information

---

**🚁 Happy Flying! 🌐**