# 🚁 Drone Command Center - Setup Instructions

## Overview
The Drone Command Center is a comprehensive Streamlit-based web interface for controlling and monitoring DJI Tello drones. It provides an intuitive dashboard with manual controls, intelligent chat interface, live camera streaming, flight telemetry, and mission planning capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows, macOS, or Linux
- Microphone and speakers (for voice features)
- DJI Tello drone (for real drone mode)
- Azure OpenAI API access (for AI features)

### Installation

1. **Clone the repository**
   ```bash
   cd drone/Tello-Drone-Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements_streamlit.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project directory:
   ```bash
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   AZURE_OPENAI_API_KEY=your-api-key-here
   AZURE_OPENAI_REALTIME_DEPLOYMENT=gpt-4o-realtime-preview
   ```

4. **Run the application**
   ```bash
   streamlit run drone_command_center.py
   ```

5. **Access the interface**
   Open your browser to `http://localhost:8501`

## 🎮 Features

### 🔧 Connection Modes
- **Vision Only Mode (Safe)**: Simulates drone without hardware - perfect for testing
- **Real Drone Mode**: Connects to actual DJI Tello drone

### 🎮 Manual Control
- **Primary Controls**: Takeoff, Land, Status Check, Emergency Stop
- **Directional Movement**: 8-directional movement with customizable distance
- **Rotation Controls**: Clockwise and counter-clockwise rotation
- **Advanced Controls**: XYZ positioning and curved flight paths
- **Real-time Status**: Battery, height, flight time, movement count

### 💬 Intelligent Chat Interface
- **Text Input**: Type commands in natural language
- **Voice Recognition**: Speak commands using microphone
- **Voice Synthesis**: Hear responses in customizable voice
- **Command Parsing**: Understands drone commands like:
  - "Take off"
  - "Move forward 50 centimeters"
  - "Turn right 90 degrees"
  - "What's my battery level?"
  - "Take a picture"

### 📹 Live Camera Feed
- **Drone Camera**: Live stream from Tello camera (real mode)
- **Webcam Fallback**: Use computer camera (vision mode)
- **Image Capture**: Take photos with timestamp
- **Video Recording**: Record flight footage
- **AI Analysis**: Analyze images for objects, obstacles, landing spots

### 📊 Flight Telemetry
- **Real-time Metrics**: Battery, height, flight time, movements
- **Live Charts**: Battery and height graphs over time
- **Flight Log**: Detailed log of all commands and actions
- **Data Export**: Download flight data as CSV

### 🗺️ Mission Planning
- **Waypoint Editor**: Add custom waypoints with XYZ coordinates
- **Pre-defined Patterns**: Square, circle, triangle flight patterns
- **3D Visualization**: Interactive 3D mission path preview
- **Mission Execution**: Automated waypoint following
- **Mission Save/Load**: Store and reuse mission plans

### ⚙️ Settings & Configuration
- **Safety Settings**: Max height, distance, battery limits
- **Camera Settings**: Resolution, FPS, brightness, contrast
- **Voice Settings**: Speech rate, volume, voice selection
- **Connection Settings**: Timeouts, retry attempts, heartbeat

## 🛡️ Safety Features

### Emergency Controls
- **Emergency Stop Button**: Immediately lands drone
- **Auto-land**: Automatic landing on low battery
- **Flight Limits**: Configurable height and distance restrictions
- **Connection Monitoring**: Real-time connection status

### Safety Guidelines
1. **Always maintain visual contact** with your drone
2. **Fly in open areas** away from people and obstacles
3. **Check battery levels** before flight
4. **Respect local regulations** and no-fly zones
5. **Use Vision Only mode** for initial testing

## 🎯 Usage Scenarios

### 1. Learning and Training
- **Vision Only Mode**: Practice controls without risk
- **Command Learning**: Learn voice commands safely
- **Mission Planning**: Design flight paths visually

### 2. Recreational Flying
- **Manual Control**: Direct joystick-style control
- **Voice Commands**: Hands-free operation
- **Photo/Video**: Capture aerial footage
- **Automated Patterns**: Execute pre-programmed flights

### 3. Inspection and Monitoring
- **Mission Planning**: Systematic area coverage
- **Image Analysis**: AI-powered object detection
- **Data Logging**: Record flight parameters
- **Repeatable Missions**: Consistent inspection routes

### 4. Education and Research
- **Programming Interface**: Extend with custom commands
- **Data Analysis**: Export flight data for research
- **Computer Vision**: Integrate custom image processing
- **Multi-drone Coordination**: (Future enhancement)

## 🔧 Troubleshooting

### Common Issues

**Connection Problems:**
- Ensure drone is powered on and in WiFi mode
- Check WiFi connection to Tello network
- Verify Azure OpenAI credentials

**Audio Issues:**
- Check microphone permissions
- Install PyAudio dependencies: `pip install pyaudio`
- On macOS: `brew install portaudio`
- On Ubuntu: `sudo apt-get install portaudio19-dev`

**Camera Problems:**
- Verify camera permissions
- Check OpenCV installation: `pip install opencv-python`
- For drone camera: Ensure video stream is enabled

**Voice Recognition:**
- Check internet connection (uses Google Speech API)
- Verify microphone is working
- Reduce background noise

### System Requirements

**Minimum:**
- Python 3.8+
- 4GB RAM
- 1GB storage
- Microphone/speakers for voice features

**Recommended:**
- Python 3.9+
- 8GB RAM
- 2GB storage
- Dedicated graphics card for video processing
- High-quality microphone for voice recognition

## 🚀 Advanced Usage

### Custom Commands
Add new drone commands by extending the `DroneChat` class in `chat_interface.py`:

```python
def custom_command_patterns(self):
    self.command_patterns['hover'] = [
        r'hover', r'stay\s*still', r'hold\s*position'
    ]
```

### Mission Scripting
Create complex missions programmatically:

```python
# Example: Spiral pattern
def create_spiral_mission(self, radius=50, height_increment=10, revolutions=3):
    waypoints = []
    for i in range(revolutions * 8):
        angle = (2 * math.pi * i) / 8
        current_radius = radius * (i / (revolutions * 8))
        x = int(current_radius * math.cos(angle))
        y = int(current_radius * math.sin(angle))
        z = i * height_increment
        waypoints.append({'x': x, 'y': y, 'z': z, 'speed': 30})
    return waypoints
```

### Custom Image Analysis
Extend the vision system with custom analysis:

```python
def analyze_custom_objects(self, frame):
    # Add your custom computer vision code here
    # Return analysis results as string
    pass
```

## 📱 Mobile Usage

While designed for desktop, the interface is responsive and can be used on tablets:

1. **Access via mobile browser**: `http://your-computer-ip:8501`
2. **Limited touch controls**: Some buttons may be small
3. **Voice commands recommended**: Easier than touch controls
4. **Camera viewing**: Good for monitoring flights

## 🔄 Updates and Maintenance

### Regular Updates
```bash
# Update dependencies
pip install -r requirements_streamlit.txt --upgrade

# Update Streamlit
pip install streamlit --upgrade
```

### Backup Flight Data
Flight logs are stored in session state. For persistence:
1. Export flight data regularly
2. Save mission plans
3. Backup environment configuration

## 🆘 Support

### Getting Help
1. **Check logs**: Enable debug logging for detailed error info
2. **Test in Vision Mode**: Isolate hardware vs software issues
3. **Verify dependencies**: Ensure all packages are installed
4. **Check network**: Confirm drone WiFi connection

### Common Solutions
- **Restart application**: Often resolves connection issues
- **Clear browser cache**: For web interface problems  
- **Restart drone**: Power cycle if connection fails
- **Check permissions**: Camera and microphone access

## 🔮 Future Enhancements

Planned features for future releases:
- **Multi-drone support**: Control multiple drones
- **Advanced missions**: Automated survey patterns
- **Machine learning**: Custom object recognition training
- **Mobile app**: Native iOS/Android application
- **Swarm coordination**: Formation flying capabilities
- **Live streaming**: Real-time video sharing
- **Cloud integration**: Remote monitoring and control

---

## 🏷️ Version Information

**Current Version**: 1.0.0
**Compatibility**: DJI Tello, Tello EDU
**Python Requirements**: 3.8+
**Streamlit Version**: 1.28+

**Last Updated**: December 2024
**Tested On**: Windows 10/11, macOS 12+, Ubuntu 20.04+

---

Enjoy flying safely with your Drone Command Center! 🚁✨