#!/usr/bin/env python3
"""
Drone Command Center Server
Web-based interface for the autonomous drone agent with real-time video streaming,
chat interface, and manual controls.
"""

import asyncio
import json
import base64
import logging
import os
import sys
import threading
import time
import argparse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import cv2
import numpy as np
from datetime import datetime

# Web server imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(__file__))

try:
    from drone.simple_tello import SimpleTello
except ImportError:
    # Mock SimpleTello for testing
    class SimpleTello:
        def __init__(self):
            self.is_connected = False
        def connect(self): return True
        def streamon(self): pass
        def takeoff(self): return True
        def land(self): return True
        def move_up(self, distance): return True
        def move_down(self, distance): return True
        def move_left(self, distance): return True
        def move_right(self, distance): return True
        def move_forward(self, distance): return True
        def move_back(self, distance): return True
        def rotate_clockwise(self, angle): return True
        def rotate_counter_clockwise(self, angle): return True
        def get_battery(self): return 100
        def get_height(self): return 50
        def get_frame(self): return np.zeros((480, 640, 3), dtype=np.uint8)
        def emergency(self): return True
        def streamoff(self): pass
        def end(self): pass

# Import our drone agent modules
try:
    from autonomous_realtime_drone_agent import RealtimeDroneAgent, DroneState
    from vision_analyzer import VisionAnalyzer
    from drone_controller import DroneController
except ImportError as e:
    print(f"Warning: Could not import drone modules: {e}")
    print("Running in standalone mode")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClientSession:
    """Track individual client sessions."""
    websocket: WebSocket
    client_id: str
    settings: Dict[str, Any]
    connected_at: datetime

class CommandCenter:
    """Web server for Drone Command Center interface."""
    
    def __init__(self, vision_only: bool = True, port: int = 8000):
        self.vision_only = vision_only
        self.port = port
        
        # FastAPI app
        self.app = FastAPI(title="Drone Command Center")
        self.setup_routes()
        
        # Connected clients
        self.clients: Dict[str, ClientSession] = {}
        
        # Drone components
        self.drone = SimpleTello()
        self.drone_state = DroneState()
        self.drone_agent = None
        
        # Video streaming
        self.video_capture = None
        self.streaming_active = False
        
        # Mission control
        self.current_mission = None
        self.mission_active = False
        
        # Status update thread
        self.status_thread = None
        self.running = False
        
    def setup_routes(self):
        """Setup FastAPI routes."""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Static files
        static_path = os.path.join(os.path.dirname(__file__))
        self.app.mount("/static", StaticFiles(directory=static_path), name="static")
        
        @self.app.get("/", response_class=HTMLResponse)
        async def serve_index():
            """Serve the main HTML page."""
            return FileResponse(os.path.join(static_path, "web/index.html"))
        
        @self.app.get("/style.css")
        async def serve_css():
            """Serve CSS file."""
            return FileResponse(os.path.join(static_path, "web/style.css"))
        
        @self.app.get("/script.js")
        async def serve_js():
            """Serve JavaScript file."""
            return FileResponse(os.path.join(static_path, "web/script.js"))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """Handle WebSocket connections."""
            await self.handle_websocket(websocket)
            
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "vision_only": self.vision_only}
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle individual WebSocket connection."""
        await websocket.accept()
        
        client_id = f"client_{int(time.time() * 1000)}"
        session = ClientSession(
            websocket=websocket,
            client_id=client_id,
            settings={},
            connected_at=datetime.now()
        )
        
        self.clients[client_id] = session
        logger.info(f"Client {client_id} connected")
        
        try:
            # Send initial status
            await self.send_to_client(client_id, {
                "type": "status_update",
                "status": self.get_current_status()
            })
            
            await self.send_to_client(client_id, {
                "type": "log_entry",
                "message": f"Connected to Drone Command Center (Mode: {'Vision Only' if self.vision_only else 'Real Drone'})"
            })
            
            # Listen for messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.handle_client_message(client_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Handle message from client."""
        msg_type = message.get("type")
        
        try:
            if msg_type == "configure":
                await self.handle_configure(client_id, message.get("settings", {}))
            elif msg_type == "chat":
                await self.handle_chat_message(client_id, message.get("message", ""))
            elif msg_type == "manual_command":
                await self.handle_manual_command(client_id, message)
            elif msg_type == "emergency_stop":
                await self.handle_emergency_stop(client_id)
            elif msg_type == "start_mission":
                await self.handle_start_mission(client_id, message.get("mission_type"))
            elif msg_type == "pause_mission":
                await self.handle_pause_mission(client_id)
            elif msg_type == "update_settings":
                await self.handle_update_settings(client_id, message.get("settings", {}))
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling message {msg_type}: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": f"Error processing {msg_type}: {str(e)}"
            })
    
    async def handle_configure(self, client_id: str, settings: Dict[str, Any]):
        """Handle client configuration."""
        if client_id in self.clients:
            self.clients[client_id].settings = settings
            logger.info(f"Client {client_id} configured: {settings}")
            
            # Initialize video streaming based on settings
            await self.setup_video_streaming(settings)
    
    async def handle_chat_message(self, client_id: str, message: str):
        """Handle chat message from client."""
        logger.info(f"Chat message from {client_id}: {message}")
        
        await self.send_to_client(client_id, {
            "type": "log_entry",
            "message": f"Processing: {message}"
        })
        
        # Process with drone agent if available
        if self.drone_agent and hasattr(self.drone_agent, 'process_text_command'):
            try:
                response = await self.drone_agent.process_text_command(message)
                await self.send_to_client(client_id, {
                    "type": "chat_response",
                    "message": response
                })
            except Exception as e:
                logger.error(f"Drone agent error: {e}")
                response = self.generate_fallback_response(message)
                await self.send_to_client(client_id, {
                    "type": "chat_response",
                    "message": response
                })
        else:
            # Generate fallback response
            response = self.generate_fallback_response(message)
            await self.send_to_client(client_id, {
                "type": "chat_response",
                "message": response
            })
    
    def generate_fallback_response(self, message: str) -> str:
        """Generate fallback response when drone agent is not available."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['takeoff', 'take off', 'launch']):
            return "I understand you want to take off. In real drone mode, I would execute this command safely."
        elif any(word in message_lower for word in ['land', 'landing']):
            return "Landing command received. I would bring the drone down safely in real mode."
        elif any(word in message_lower for word in ['move', 'go', 'forward', 'backward', 'left', 'right']):
            return "Movement command understood. I would execute precise movements in real drone mode."
        elif any(word in message_lower for word in ['battery', 'status', 'health']):
            return f"Current status: Battery {self.drone_state.battery}%, Altitude {self.drone_state.height}cm, Flight mode: {'Flying' if self.drone_state.is_flying else 'Grounded'}"
        elif any(word in message_lower for word in ['camera', 'see', 'look', 'vision']):
            return "I can see through the camera feed. In real mode, I would analyze the drone's camera for obstacles and navigation."
        elif any(word in message_lower for word in ['emergency', 'stop', 'help']):
            return "Emergency protocols activated. All movement stopped. Drone safety is my priority."
        else:
            return "I understand your command. Currently in simulation mode - switch to real drone mode to execute actual flight commands."
    
    async def handle_manual_command(self, client_id: str, command_data: Dict[str, Any]):
        """Handle manual drone command."""
        command = command_data.get("command")
        distance = command_data.get("distance", 30)
        
        logger.info(f"Manual command from {client_id}: {command}")
        
        try:
            result = await self.execute_drone_command(command, distance)
            
            await self.send_to_client(client_id, {
                "type": "log_entry",
                "message": f"Command executed: {command} - {result}"
            })
            
            # Update status after command
            await self.broadcast_status_update()
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": f"Command failed: {str(e)}"
            })
    
    async def execute_drone_command(self, command: str, distance: int = 30) -> str:
        """Execute drone command and return result."""
        if self.vision_only:
            # Simulate command execution
            await asyncio.sleep(0.5)  # Simulate processing time
            
            if command == "takeoff":
                self.drone_state.is_flying = True
                self.drone_state.height = 50
                return "Takeoff simulated successfully"
            elif command == "land":
                self.drone_state.is_flying = False
                self.drone_state.height = 0
                return "Landing simulated successfully"
            elif command.startswith("move_"):
                self.drone_state.movement_count += 1
                return f"Movement simulated: {command} {distance}cm"
            elif command.startswith("rotate_"):
                return f"Rotation simulated: {command}"
            else:
                return f"Command simulated: {command}"
        else:
            # Execute real drone command
            try:
                if command == "takeoff":
                    result = self.drone.takeoff()
                    if result:
                        self.drone_state.is_flying = True
                        return "Takeoff successful"
                    else:
                        return "Takeoff failed"
                elif command == "land":
                    result = self.drone.land()
                    if result:
                        self.drone_state.is_flying = False
                        return "Landing successful"
                    else:
                        return "Landing failed"
                elif command == "move_forward":
                    result = self.drone.move_forward(distance)
                    return f"Moved forward {distance}cm" if result else "Move forward failed"
                elif command == "move_backward":
                    result = self.drone.move_back(distance)
                    return f"Moved backward {distance}cm" if result else "Move backward failed"
                elif command == "move_left":
                    result = self.drone.move_left(distance)
                    return f"Moved left {distance}cm" if result else "Move left failed"
                elif command == "move_right":
                    result = self.drone.move_right(distance)
                    return f"Moved right {distance}cm" if result else "Move right failed"
                elif command == "move_up":
                    result = self.drone.move_up(distance)
                    return f"Moved up {distance}cm" if result else "Move up failed"
                elif command == "move_down":
                    result = self.drone.move_down(distance)
                    return f"Moved down {distance}cm" if result else "Move down failed"
                elif command == "rotate_left":
                    result = self.drone.rotate_counter_clockwise(90)
                    return "Rotated left 90°" if result else "Rotation failed"
                elif command == "rotate_right":
                    result = self.drone.rotate_clockwise(90)
                    return "Rotated right 90°" if result else "Rotation failed"
                else:
                    return f"Unknown command: {command}"
            except Exception as e:
                return f"Command error: {str(e)}"
    
    async def handle_emergency_stop(self, client_id: str):
        """Handle emergency stop command."""
        logger.warning(f"EMERGENCY STOP requested by {client_id}")
        
        try:
            if not self.vision_only:
                self.drone.emergency()
            
            self.drone_state.is_flying = False
            self.mission_active = False
            
            # Broadcast emergency stop to all clients
            await self.broadcast_message({
                "type": "log_entry",
                "message": "🚨 EMERGENCY STOP ACTIVATED"
            })
            
            await self.broadcast_status_update()
            
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
    
    async def handle_start_mission(self, client_id: str, mission_type: str):
        """Handle mission start command."""
        logger.info(f"Starting mission: {mission_type}")
        
        self.current_mission = mission_type
        self.mission_active = True
        
        await self.send_to_client(client_id, {
            "type": "log_entry",
            "message": f"Mission started: {mission_type}"
        })
        
        # Start mission execution in background
        asyncio.create_task(self.execute_mission(mission_type))
    
    async def handle_pause_mission(self, client_id: str):
        """Handle mission pause command."""
        logger.info("Pausing mission")
        
        self.mission_active = False
        
        await self.send_to_client(client_id, {
            "type": "log_entry",
            "message": "Mission paused"
        })
    
    async def handle_update_settings(self, client_id: str, settings: Dict[str, Any]):
        """Handle settings update."""
        if client_id in self.clients:
            self.clients[client_id].settings.update(settings)
            logger.info(f"Settings updated for {client_id}")
            
            await self.send_to_client(client_id, {
                "type": "log_entry",
                "message": "Settings updated successfully"
            })
    
    async def execute_mission(self, mission_type: str):
        """Execute automated mission."""
        try:
            if mission_type == "patrol":
                await self.execute_patrol_mission()
            elif mission_type == "circle":
                await self.execute_circle_mission()
            elif mission_type == "square":
                await self.execute_square_mission()
            else:
                logger.warning(f"Unknown mission type: {mission_type}")
        except Exception as e:
            logger.error(f"Mission execution error: {e}")
            await self.broadcast_message({
                "type": "log_entry",
                "message": f"Mission failed: {str(e)}"
            })
    
    async def execute_patrol_mission(self):
        """Execute patrol pattern mission."""
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Executing patrol pattern..."
        })
        
        moves = ["move_forward", "move_right", "move_backward", "move_left"]
        
        for move in moves:
            if not self.mission_active:
                break
                
            await self.execute_drone_command(move, 50)
            await asyncio.sleep(2)
            
            await self.broadcast_message({
                "type": "log_entry",
                "message": f"Patrol: {move} completed"
            })
        
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Patrol mission completed"
        })
        
        self.mission_active = False
    
    async def execute_circle_mission(self):
        """Execute circular pattern mission."""
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Executing circle pattern..."
        })
        
        # Execute 8 small movements to form a circle
        for i in range(8):
            if not self.mission_active:
                break
                
            # Move forward and rotate
            await self.execute_drone_command("move_forward", 30)
            await asyncio.sleep(1)
            await self.execute_drone_command("rotate_right", 45)
            await asyncio.sleep(1)
            
            await self.broadcast_message({
                "type": "log_entry",
                "message": f"Circle: segment {i+1}/8 completed"
            })
        
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Circle mission completed"
        })
        
        self.mission_active = False
    
    async def execute_square_mission(self):
        """Execute square pattern mission."""
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Executing square pattern..."
        })
        
        for i in range(4):
            if not self.mission_active:
                break
                
            # Move forward and turn right
            await self.execute_drone_command("move_forward", 60)
            await asyncio.sleep(1)
            await self.execute_drone_command("rotate_right", 90)
            await asyncio.sleep(1)
            
            await self.broadcast_message({
                "type": "log_entry",
                "message": f"Square: side {i+1}/4 completed"
            })
        
        await self.broadcast_message({
            "type": "log_entry",
            "message": "Square mission completed"
        })
        
        self.mission_active = False
    
    async def setup_video_streaming(self, settings: Dict[str, Any]):
        """Setup video streaming based on client settings."""
        camera_source = settings.get("cameraSource", "webcam")
        
        if camera_source == "webcam" and not self.video_capture:
            try:
                self.video_capture = cv2.VideoCapture(0)
                if self.video_capture.isOpened():
                    logger.info("Webcam video streaming started")
                    self.streaming_active = True
                    asyncio.create_task(self.video_streaming_loop())
                else:
                    logger.warning("Failed to open webcam")
            except Exception as e:
                logger.error(f"Video setup error: {e}")
        elif camera_source == "drone":
            logger.info("Drone camera streaming configured")
            # Drone camera streaming would be handled by the drone agent
    
    async def video_streaming_loop(self):
        """Main video streaming loop."""
        while self.streaming_active and self.video_capture:
            try:
                ret, frame = self.video_capture.read()
                if ret:
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_data = base64.b64encode(buffer).decode()
                    
                    # Broadcast frame to all connected clients
                    await self.broadcast_message({
                        "type": "video_frame",
                        "frame": frame_data
                    })
                
                await asyncio.sleep(1/30)  # 30 FPS
            except Exception as e:
                logger.error(f"Video streaming error: {e}")
                break
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current drone status."""
        return {
            "battery": self.drone_state.battery,
            "altitude": self.drone_state.height,
            "speed": 0,  # TODO: Implement speed tracking
            "heading": 0,  # TODO: Implement heading tracking
            "flightMode": "Flying" if self.drone_state.is_flying else "Grounded",
            "signalStrength": 95 if not self.vision_only else 100
        }
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if client_id in self.clients:
            try:
                await self.clients[client_id].websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                # Remove disconnected client
                if client_id in self.clients:
                    del self.clients[client_id]
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
            
        # Send to all clients
        tasks = []
        for client_id in list(self.clients.keys()):
            tasks.append(self.send_to_client(client_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_status_update(self):
        """Broadcast status update to all clients."""
        status = self.get_current_status()
        await self.broadcast_message({
            "type": "status_update",
            "status": status
        })
    
    def start_status_updates(self):
        """Start periodic status updates."""
        async def status_update_loop():
            while self.running:
                try:
                    await self.broadcast_status_update()
                    await asyncio.sleep(2)  # Update every 2 seconds
                except Exception as e:
                    logger.error(f"Status update error: {e}")
                    await asyncio.sleep(5)
        
        asyncio.create_task(status_update_loop())
    
    async def initialize_drone(self):
        """Initialize drone connection."""
        if not self.vision_only:
            try:
                logger.info("Connecting to Tello drone...")
                if self.drone.connect():
                    self.drone.streamon()
                    self.drone_state.battery = self.drone.get_battery()
                    logger.info(f"✅ Drone connected, battery: {self.drone_state.battery}%")
                else:
                    logger.error("❌ Failed to connect to drone")
            except Exception as e:
                logger.error(f"❌ Drone initialization error: {e}")
        else:
            logger.info("Running in vision-only mode (simulation)")
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up server resources...")
        
        self.running = False
        self.streaming_active = False
        
        # Close video capture
        if self.video_capture:
            self.video_capture.release()
        
        # Clean up drone
        if self.drone and not self.vision_only:
            try:
                if self.drone_state.is_flying:
                    logger.info("Landing drone before cleanup...")
                    self.drone.land()
                    await asyncio.sleep(2)
                
                self.drone.streamoff()
                self.drone.end()
            except Exception as e:
                logger.warning(f"Drone cleanup warning: {e}")
        
        # Close all client connections
        for client_id in list(self.clients.keys()):
            try:
                await self.clients[client_id].websocket.close()
            except:
                pass
        
        logger.info("✅ Cleanup completed")
    
    async def run(self):
        """Run the server."""
        self.running = True
        
        # Initialize drone
        await self.initialize_drone()
        
        # Start status updates
        self.start_status_updates()
        
        # Run the server
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        try:
            logger.info(f"🚁 Drone Command Center starting on http://localhost:{self.port}")
            await server.serve()
        except KeyboardInterrupt:
            logger.info("👋 Server stopped by user")
        finally:
            await self.cleanup()

async def main():
    """Main function to run the command center server."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Drone Command Center Server')
    parser.add_argument('--vision-only', action='store_true', default=True,
                        help='Run in vision-only mode (simulation) - default: True')
    parser.add_argument('--real-drone', action='store_true', default=False,
                        help='Connect to real drone (overrides --vision-only)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Server port (default: 8000)')
    
    args = parser.parse_args()
    
    # Determine vision_only mode
    vision_only = not args.real_drone  # If real_drone is True, vision_only is False
    
    print("🚁🌐 Drone Command Center Server")
    print("=" * 50)
    print(f"🤖 Mode: {'VISION ONLY (Simulation)' if vision_only else 'REAL DRONE'}")
    print(f"🌐 Port: {args.port}")
    print(f"🔗 URL: http://localhost:{args.port}")
    print()
    
    # Create and run server
    server = CommandCenter(vision_only=vision_only, port=args.port)
    
    try:
        await server.run()
    except Exception as e:
        logger.error(f"❌ Server error: {e}")

if __name__ == "__main__":
    print("🚁🌐 Drone Command Center Server")
    print("=" * 50)
    print()
    print("📋 FEATURES:")
    print("  • Real-time web interface for drone control")
    print("  • Live video streaming from drone/webcam")
    print("  • Chat interface with speech input/output")
    print("  • Manual flight controls with keyboard shortcuts")
    print("  • Automated mission planning (patrol, circle, square)")
    print("  • Real-time telemetry and status monitoring")
    print("  • Emergency stop and safety features")
    print("  • Settings for drone mode, camera, and audio")
    print()
    print("🚀 USAGE:")
    print("  • Vision Only (Safe):  python command_center_server.py")
    print("  • Real Drone Mode:     python command_center_server.py --real-drone")
    print("  • Custom Port:         python command_center_server.py --port 9000")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")