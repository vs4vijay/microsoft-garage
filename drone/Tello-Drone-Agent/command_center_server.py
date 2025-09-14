#!/usr/bin/env python3
"""
Enhanced Drone Command Center Bridge
Integrates the web interface directly with the existing autonomous_realtime_drone_agent.py
Run: 
uv run --with-requirements requirements.txt --with-requirements requirements.cc.txt command_center_server.py
"""

import asyncio
import json
import logging
import os
import sys
import threading
import queue
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autonomous_realtime_drone_agent import RealtimeDroneAgent, DroneState
from command_center import CommandCenter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandCenterServer(CommandCenter):
    """Enhanced command center that integrates with the autonomous drone agent."""
    
    def __init__(self, vision_only: bool = True, port: int = 8000):
        super().__init__(vision_only, port)
        
        # Drone agent integration
        self.drone_agent: Optional[RealtimeDroneAgent] = None
        self.agent_connected = False
        
        # Communication queues between web interface and drone agent
        self.web_to_agent_queue = queue.Queue()
        self.agent_to_web_queue = queue.Queue()
        
        # Bridge thread for handling agent communication
        self.bridge_thread = None
        
    async def initialize_drone_agent(self):
        """Initialize the autonomous drone agent."""
        try:
            logger.info("Initializing autonomous drone agent...")
            
            # Create drone agent instance
            self.drone_agent = RealtimeDroneAgent(vision_only=self.vision_only)
            
            # Connect to Azure OpenAI Realtime API
            if await self.drone_agent.connect_realtime():
                self.agent_connected = True
                logger.info("✅ Drone agent connected to Realtime API")
                
                # Start bridge communication thread
                self.bridge_thread = threading.Thread(target=self._bridge_communication_loop, daemon=True)
                self.bridge_thread.start()
                
                # Modify the agent's function execution to route through web interface
                self._patch_agent_functions()
                
            else:
                logger.error("❌ Failed to connect drone agent to Realtime API")
                
        except Exception as e:
            logger.error(f"❌ Drone agent initialization error: {e}")
    
    def _patch_agent_functions(self):
        """Patch drone agent functions to route through web interface."""
        if not self.drone_agent:
            return
            
        # Store original functions
        original_functions = self.drone_agent.functions.copy()
        
        # Create wrapped functions that communicate through the bridge
        for func_name, original_func in original_functions.items():
            self.drone_agent.functions[func_name] = self._create_bridge_function(func_name, original_func)
    
    def _create_bridge_function(self, func_name: str, original_func):
        """Create a bridge function that routes through web interface."""
        async def bridge_function(**kwargs):
            try:
                # Send command to web interface for execution
                command_data = {
                    "type": "agent_command",
                    "function": func_name,
                    "arguments": kwargs,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Broadcast to web clients
                await self.broadcast_message({
                    "type": "log_entry",
                    "message": f"Agent executing: {func_name}"
                })
                
                # Execute the original function
                result = await original_func(**kwargs)
                
                # Broadcast result
                await self.broadcast_message({
                    "type": "log_entry",
                    "message": f"Agent result: {result}"
                })
                
                return result
                
            except Exception as e:
                error_msg = f"Bridge function error for {func_name}: {str(e)}"
                logger.error(error_msg)
                await self.broadcast_message({
                    "type": "log_entry",
                    "message": error_msg
                })
                return error_msg
        
        return bridge_function
    
    def _bridge_communication_loop(self):
        """Bridge communication loop between web interface and drone agent."""
        logger.info("Bridge communication loop started")
        
        while self.running and self.agent_connected:
            try:
                # Process messages from web to agent
                try:
                    message = self.web_to_agent_queue.get(timeout=0.1)
                    self._process_web_to_agent_message(message)
                except queue.Empty:
                    pass
                
                # Process messages from agent to web
                try:
                    message = self.agent_to_web_queue.get(timeout=0.1)
                    asyncio.run_coroutine_threadsafe(
                        self._process_agent_to_web_message(message),
                        asyncio.get_event_loop()
                    )
                except queue.Empty:
                    pass
                    
            except Exception as e:
                logger.error(f"Bridge communication error: {e}")
                
        logger.info("Bridge communication loop ended")
    
    def _process_web_to_agent_message(self, message: Dict[str, Any]):
        """Process message from web interface to drone agent."""
        # This would handle cases where the web interface needs to send
        # specific commands or data to the drone agent
        pass
    
    async def _process_agent_to_web_message(self, message: Dict[str, Any]):
        """Process message from drone agent to web interface."""
        # Broadcast agent messages to web clients
        await self.broadcast_message(message)
    
    async def handle_chat_message(self, client_id: str, message: str):
        """Enhanced chat message handling with drone agent integration."""
        logger.info(f"Chat message from {client_id}: {message}")
        
        await self.send_to_client(client_id, {
            "type": "log_entry",
            "message": f"Processing: {message}"
        })
        
        if self.drone_agent and self.agent_connected:
            try:
                # Send message to drone agent through its audio processing pipeline
                await self._send_text_to_agent(message)
                
                # The response will come through the agent's response handling
                await self.send_to_client(client_id, {
                    "type": "chat_response",
                    "message": "Message sent to drone agent. Listening for response..."
                })
                
            except Exception as e:
                logger.error(f"Error sending to drone agent: {e}")
                # Fallback to original chat handling
                await super().handle_chat_message(client_id, message)
        else:
            # Fallback to original chat handling
            await super().handle_chat_message(client_id, message)
    
    async def _send_text_to_agent(self, text: str):
        """Send text message to drone agent."""
        if self.drone_agent and self.drone_agent.websocket:
            # Create a text input message for the realtime API
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            
            await self.drone_agent.websocket.send(json.dumps(message))
            
            # Trigger response generation
            response_request = {
                "type": "response.create"
            }
            await self.drone_agent.websocket.send(json.dumps(response_request))
    
    async def handle_manual_command(self, client_id: str, command_data: Dict[str, Any]):
        """Enhanced manual command handling with agent integration."""
        command = command_data.get("command")
        distance = command_data.get("distance", 30)
        
        logger.info(f"Manual command from {client_id}: {command}")
        
        if self.drone_agent and self.agent_connected:
            try:
                # Use the drone agent's functions directly
                if command in self.drone_agent.functions:
                    func = self.drone_agent.functions[command]
                    
                    # Prepare arguments based on command type
                    kwargs = {}
                    if command in ['move_forward', 'move_backward', 'move_left', 'move_right', 'move_up', 'move_down']:
                        kwargs['distance'] = distance
                    elif command in ['rotate_clockwise', 'rotate_counter_clockwise']:
                        kwargs['angle'] = 90  # Default rotation angle
                    
                    result = await func(**kwargs)
                    
                    await self.send_to_client(client_id, {
                        "type": "log_entry",
                        "message": f"Command executed via agent: {command} - {result}"
                    })
                    
                else:
                    # Fallback to server execution
                    await super().handle_manual_command(client_id, command_data)
                    
            except Exception as e:
                logger.error(f"Agent command execution error: {e}")
                await self.send_to_client(client_id, {
                    "type": "error",
                    "message": f"Agent command failed: {str(e)}"
                })
        else:
            # Fallback to server execution
            await super().handle_manual_command(client_id, command_data)
        
        # Update status after command
        await self.broadcast_status_update()
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current drone status from agent if available."""
        if self.drone_agent and self.drone_agent.drone_state:
            state = self.drone_agent.drone_state
            return {
                "battery": state.battery,
                "altitude": state.height,
                "speed": 0,  # TODO: Implement speed tracking
                "heading": 0,  # TODO: Implement heading tracking
                "flightMode": "Flying" if state.is_flying else "Grounded",
                "signalStrength": 95 if not self.vision_only else 100,
                "movementCount": state.movement_count,
                "lastAnalysis": state.last_image_analysis[:50] + "..." if len(state.last_image_analysis) > 50 else state.last_image_analysis
            }
        else:
            return super().get_current_status()
    
    async def initialize_drone(self):
        """Initialize drone with agent integration."""
        # Initialize the autonomous drone agent first
        await self.initialize_drone_agent()
        
        # Then initialize the base drone if not using agent
        if not self.agent_connected:
            await super().initialize_drone()
    
    async def cleanup(self):
        """Enhanced cleanup with agent cleanup."""
        logger.info("Cleaning up enhanced command center...")
        
        # Stop bridge communication
        if self.bridge_thread and self.bridge_thread.is_alive():
            # The thread will stop when self.running becomes False
            pass
        
        # Cleanup drone agent
        if self.drone_agent:
            try:
                await self.drone_agent.cleanup()
            except Exception as e:
                logger.warning(f"Agent cleanup warning: {e}")
        
        # Call parent cleanup
        await super().cleanup()

async def main():
    """Main function for enhanced drone command center."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced Drone Command Center with Agent Integration')
    parser.add_argument('--vision-only', action='store_true', default=True,
                        help='Run in vision-only mode (simulation) - default: True')
    parser.add_argument('--real-drone', action='store_true', default=False,
                        help='Connect to real drone (overrides --vision-only)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Server port (default: 8000)')
    
    args = parser.parse_args()
    
    # Determine vision_only mode
    vision_only = not args.real_drone
    
    print("🚁🌐🤖 Enhanced Drone Command Center")
    print("=" * 50)
    print(f"🤖 Mode: {'VISION ONLY (Simulation)' if vision_only else 'REAL DRONE'}")
    print(f"🧠 AI Agent: Integrated with GPT-4o Realtime API")
    print(f"🌐 Port: {args.port}")
    print(f"🔗 URL: http://localhost:{args.port}")
    print()
    
    # Check environment variables
    required_vars = ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.info("💡 Set them with:")
        for var in missing_vars:
            logger.info(f"   export {var}='your-value'")
        return
    
    # Create and run enhanced server
    server = CommandCenterServer(vision_only=vision_only, port=args.port)
    
    try:
        await server.run()
    except Exception as e:
        logger.error(f"❌ Server error: {e}")

if __name__ == "__main__":
    print("🚁🌐🤖 Enhanced Drone Command Center")
    print("=" * 50)
    print()
    print("📋 ENHANCED FEATURES:")
    print("  • Full integration with autonomous drone agent")
    print("  • GPT-4o Realtime API for natural language control")
    print("  • Speech-to-speech communication with AI")
    print("  • Real-time vision analysis and obstacle detection")
    print("  • Web interface for remote control and monitoring")
    print("  • Automatic mission execution with AI guidance")
    print("  • Safety protocols and emergency stop")
    print("  • Multi-modal interaction (text, speech, vision)")
    print()
    print("🚀 USAGE:")
    print("  • Enhanced Mode (AI + Web):  python enhanced_command_center.py")
    print("  • Real Drone Mode:           python enhanced_command_center.py --real-drone")
    print("  • Custom Port:               python enhanced_command_center.py --port 9000")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")