# DJI Tello

Resource and Details about DJI Tello Drone

## Table of Contents

- [Programming](#programming)
- [Technical Details](#technical-details)
  - [Communication](#communication)
  - [Video Specifications](#video-specifications)
  - [Distance and Speed Units](#distance-and-speed-units)
- [Capabilities](#capabilities)
  - [Flight Control](#flight-control)
  - [Movement (20-500 cm range)](#movement-20-500-cm-range)
  - [Rotation (1-360 degrees)](#rotation-1-360-degrees)
  - [Flips](#flips)
  - [Speed Control (1-100 cm/s)](#speed-control-1-100-cms)
  - [Status Queries](#status-queries)
  - [Video Streaming](#video-streaming)
- [Troubleshooting](#troubleshooting)

## Programming

Python SDK for Tello - https://github.com/dji-sdk/Tello-Python

- This contains Tello wrapper class for interacting with the DJI Tello drone using Python.

Simulator - https://github.com/Fireline-Science/tello_sim

---

## Technical Details

### Communication

- **Command Port**: 8889 (UDP)
- **Video Port**: 11111 (UDP)
- **Video Format**: H.264
- **Command Timeout**: Configurable (default 0.3s)

### Video Specifications

- **Codec**: H.264
- **Resolution**: 960x720
- **Frame Rate**: 30 FPS
- **Format**: BGR (Blue-Green-Red)

### Distance and Speed Units

- **Metric Mode**: Meters and KPH
- **Imperial Mode**: Feet and MPH
- **Internal API**: Centimeters and cm/s

---

## Capabilities

Currently Supported Commands

### Flight Control

- `takeoff` - Initiates take-off
- `land` - Initiates landing

### Movement (20-500 cm range)

- `forward` - Move forward
- `back` - Move backward
- `left` - Move left
- `right` - Move right
- `up` - Move up
- `down` - Move down

### Rotation (1-360 degrees)

- `cw` - Rotate clockwise
- `ccw` - Rotate counter-clockwise

### Flips

- `flip l` - Flip left
- `flip r` - Flip right
- `flip f` - Flip forward
- `flip b` - Flip backward

### Speed Control (1-100 cm/s)

- `speed` - Set speed

### Status Queries

- `battery?` - Get battery percentage
- `height?` - Get current height
- `time?` - Get flight time
- `speed?` - Get current speed

### Video Streaming

- `streamon` - Enable video streaming
- `streamoff` - Disable video streaming

---

## Troubleshooting

- Always check battery level before flight
- Ensure adequate space for maneuvers
- Monitor flight time to prevent automatic landing
- Use timeouts between commands for stability
- Test in a safe, open environment first

1. **Connection Failed**

   - Ensure Tello is in AP mode
   - Connect to Tello WiFi network
   - Check IP addresses and ports

2. **Video Stream Not Working**

   - Verify `streamon` command was sent
   - Check video port binding
   - Ensure libh264decoder is installed

3. **Commands Not Responding**

   - Increase command timeout
   - Check for interference
   - Ensure drone is in command mode

4. **Poor Video Quality**
   - Move closer to drone
   - Reduce WiFi interference
   - Check for packet loss
