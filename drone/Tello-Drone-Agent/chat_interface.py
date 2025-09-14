#!/usr/bin/env python3
"""
Advanced Chat Interface for Drone Command Center
Supports text input, speech recognition, and speech synthesis.
"""

import streamlit as st
import speech_recognition as sr
import pyttsx3
import asyncio
import threading
import queue
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import json
import re
import pyaudio
import wave
import tempfile
import os

logger = logging.getLogger(__name__)

class DroneChat:
    """Advanced chat interface for drone command center."""
    
    def __init__(self, drone_agent=None):
        self.drone_agent = drone_agent
        
        # Speech components
        self.speech_recognizer = sr.Recognizer()
        self.microphone = None
        self.speech_engine = None
        
        # Initialize speech engine
        self._init_speech_engine()
        
        # Audio settings
        self.speech_rate = 150
        self.speech_volume = 0.9
        self.voice_index = 0
        
        # Chat state
        self.is_listening = False
        self.is_speaking = False
        self.conversation_history = []
        
        # Command patterns for drone control
        self.command_patterns = {
            'takeoff': [
                r'take\s*off', r'lift\s*off', r'start\s*flying', r'go\s*up'
            ],
            'land': [
                r'land', r'come\s*down', r'stop\s*flying', r'touch\s*down'
            ],
            'move_forward': [
                r'move\s*forward', r'go\s*forward', r'fly\s*forward',
                r'advance', r'move\s*ahead'
            ],
            'move_backward': [
                r'move\s*back', r'go\s*back', r'fly\s*back',
                r'retreat', r'reverse'
            ],
            'move_left': [
                r'move\s*left', r'go\s*left', r'fly\s*left', r'slide\s*left'
            ],
            'move_right': [
                r'move\s*right', r'go\s*right', r'fly\s*right', r'slide\s*right'
            ],
            'move_up': [
                r'move\s*up', r'go\s*up', r'fly\s*up', r'ascend', r'rise'
            ],
            'move_down': [
                r'move\s*down', r'go\s*down', r'fly\s*down', r'descend'
            ],
            'rotate_clockwise': [
                r'turn\s*right', r'rotate\s*right', r'spin\s*right',
                r'rotate\s*clockwise', r'turn\s*clockwise'
            ],
            'rotate_counter_clockwise': [
                r'turn\s*left', r'rotate\s*left', r'spin\s*left',
                r'rotate\s*counter', r'turn\s*counter'
            ],
            'status': [
                r'status', r'battery', r'height', r'how\s*(are\s*you|high)',
                r'what.*battery', r'check\s*status'
            ],
            'capture': [
                r'take\s*(a\s*)?photo', r'capture', r'picture', r'image',
                r'take\s*(a\s*)?picture', r'snap'
            ]
        }
    
    def _init_speech_engine(self):
        """Initialize text-to-speech engine."""
        try:
            self.speech_engine = pyttsx3.init()
            
            # Set default properties
            self.speech_engine.setProperty('rate', self.speech_rate)
            self.speech_engine.setProperty('volume', self.speech_volume)
            
            # Get available voices
            voices = self.speech_engine.getProperty('voices')
            if voices and len(voices) > 0:
                self.speech_engine.setProperty('voice', voices[0].id)
            
            logger.info("Speech engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize speech engine: {e}")
            self.speech_engine = None
    
    def _init_microphone(self):
        """Initialize microphone for speech recognition."""
        try:
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.speech_recognizer.adjust_for_ambient_noise(source, duration=1)
            
            logger.info("Microphone initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize microphone: {e}")
            return False
    
    def speak_text(self, text: str, interrupt_current: bool = True) -> bool:
        """Convert text to speech."""
        if not self.speech_engine:
            logger.warning("Speech engine not available")
            return False
        
        try:
            if interrupt_current and self.is_speaking:
                self.speech_engine.stop()
            
            self.is_speaking = True
            
            # Run speech in a separate thread to avoid blocking
            def speak_thread():
                try:
                    self.speech_engine.say(text)
                    self.speech_engine.runAndWait()
                finally:
                    self.is_speaking = False
            
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            self.is_speaking = False
            return False
    
    def listen_for_speech(self, timeout: int = 5, phrase_timeout: int = 1) -> Optional[str]:
        """Listen for speech input and convert to text."""
        if not self.microphone:
            if not self._init_microphone():
                return None
        
        try:
            self.is_listening = True
            
            with self.microphone as source:
                logger.info("Listening for speech...")
                
                # Listen for audio with timeout
                audio = self.speech_recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_timeout
                )
            
            self.is_listening = False
            
            # Recognize speech using Google's service
            text = self.speech_recognizer.recognize_google(audio)
            logger.info(f"Speech recognized: {text}")
            
            return text
            
        except sr.WaitTimeoutError:
            self.is_listening = False
            logger.warning("Speech recognition timeout")
            return None
        except sr.UnknownValueError:
            self.is_listening = False
            logger.warning("Could not understand speech")
            return None
        except sr.RequestError as e:
            self.is_listening = False
            logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            self.is_listening = False
            logger.error(f"Speech recognition failed: {e}")
            return None
    
    def parse_drone_command(self, text: str) -> Dict[str, Any]:
        """Parse text input for drone commands."""
        text_lower = text.lower()
        
        # Extract distance/angle values
        distance_match = re.search(r'(\d+)\s*(cm|centimeter|meter|m)', text_lower)
        angle_match = re.search(r'(\d+)\s*(degree|deg|°)', text_lower)
        
        distance = int(distance_match.group(1)) if distance_match else 50
        angle = int(angle_match.group(1)) if angle_match else 90
        
        # Match command patterns
        for command, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    result = {
                        'command': command,
                        'original_text': text,
                        'confidence': 'high'
                    }
                    
                    # Add parameters based on command type
                    if 'move' in command:
                        result['distance'] = min(max(distance, 20), 500)
                    elif 'rotate' in command:
                        result['angle'] = min(max(angle, 30), 360)
                    
                    return result
        
        # No specific command found, treat as general query
        return {
            'command': 'general',
            'original_text': text,
            'confidence': 'low'
        }
    
    async def execute_drone_command(self, command_data: Dict[str, Any]) -> str:
        """Execute a parsed drone command."""
        if not self.drone_agent:
            return "❌ Drone not connected"
        
        command = command_data['command']
        
        try:
            if command == 'takeoff':
                result = await self.drone_agent.drone_controller.takeoff()
            elif command == 'land':
                result = await self.drone_agent.drone_controller.land()
            elif command == 'move_forward':
                result = await self.drone_agent.drone_controller.move_forward(
                    command_data.get('distance', 50)
                )
            elif command == 'move_backward':
                result = await self.drone_agent.drone_controller.move_backward(
                    command_data.get('distance', 50)
                )
            elif command == 'move_left':
                result = await self.drone_agent.drone_controller.move_left(
                    command_data.get('distance', 50)
                )
            elif command == 'move_right':
                result = await self.drone_agent.drone_controller.move_right(
                    command_data.get('distance', 50)
                )
            elif command == 'move_up':
                result = await self.drone_agent.drone_controller.move_up(
                    command_data.get('distance', 50)
                )
            elif command == 'move_down':
                result = await self.drone_agent.drone_controller.move_down(
                    command_data.get('distance', 50)
                )
            elif command == 'rotate_clockwise':
                result = await self.drone_agent.drone_controller.rotate_clockwise(
                    command_data.get('angle', 90)
                )
            elif command == 'rotate_counter_clockwise':
                result = await self.drone_agent.drone_controller.rotate_counter_clockwise(
                    command_data.get('angle', 90)
                )
            elif command == 'status':
                result = await self.drone_agent.drone_controller.get_drone_status()
            elif command == 'capture':
                result = await self.drone_agent._capture_and_analyze_image('objects')
            else:
                result = f"I understand you said: '{command_data['original_text']}', but I'm not sure how to help with that. Try commands like 'take off', 'move forward 50cm', or 'what's my battery level?'"
            
            return result
            
        except Exception as e:
            error_msg = f"❌ Command failed: {str(e)}"
            logger.error(f"Command execution error: {e}")
            return error_msg
    
    def add_to_conversation(self, user_input: str, response: str, command_data: Dict = None):
        """Add exchange to conversation history."""
        entry = {
            'timestamp': datetime.now(),
            'user_input': user_input,
            'response': response,
            'command_data': command_data,
            'type': 'command' if command_data and command_data['command'] != 'general' else 'conversation'
        }
        
        self.conversation_history.append(entry)
        
        # Keep last 50 entries
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def get_conversation_summary(self) -> Dict[str, int]:
        """Get conversation statistics."""
        total_messages = len(self.conversation_history)
        command_messages = sum(1 for entry in self.conversation_history 
                             if entry['type'] == 'command')
        
        return {
            'total_messages': total_messages,
            'command_messages': command_messages,
            'conversation_messages': total_messages - command_messages,
            'success_rate': command_messages / max(total_messages, 1) * 100
        }
    
    def set_voice_settings(self, rate: int = 150, volume: float = 0.9, voice_index: int = 0):
        """Update voice settings."""
        if not self.speech_engine:
            return False
        
        try:
            self.speech_rate = max(50, min(300, rate))
            self.speech_volume = max(0.0, min(1.0, volume))
            self.voice_index = voice_index
            
            self.speech_engine.setProperty('rate', self.speech_rate)
            self.speech_engine.setProperty('volume', self.speech_volume)
            
            # Set voice if available
            voices = self.speech_engine.getProperty('voices')
            if voices and 0 <= voice_index < len(voices):
                self.speech_engine.setProperty('voice', voices[voice_index].id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update voice settings: {e}")
            return False
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices."""
        if not self.speech_engine:
            return []
        
        try:
            voices = self.speech_engine.getProperty('voices')
            return [
                {
                    'id': i,
                    'name': voice.name,
                    'language': getattr(voice, 'languages', ['Unknown'])[0] if hasattr(voice, 'languages') else 'Unknown'
                }
                for i, voice in enumerate(voices)
            ] if voices else []
            
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []

# Streamlit Chat Interface Component
def render_chat_interface(drone_chat: DroneChat, container_key: str = "chat") -> None:
    """Render the chat interface in Streamlit."""
    
    st.subheader("💬 Intelligent Chat Interface")
    
    # Chat history display
    chat_container = st.container()
    
    with chat_container:
        if drone_chat.conversation_history:
            for i, entry in enumerate(drone_chat.conversation_history[-10:]):  # Show last 10
                timestamp = entry['timestamp'].strftime('%H:%M:%S')
                
                # User message
                with st.chat_message("user"):
                    st.write(f"**[{timestamp}]** {entry['user_input']}")
                
                # Assistant response
                with st.chat_message("assistant"):
                    response_text = entry['response']
                    if entry['type'] == 'command' and entry['command_data']:
                        cmd = entry['command_data']['command']
                        st.write(f"🤖 **Executed:** {cmd}")
                    st.write(response_text)
        else:
            st.info("💡 **Start a conversation with your drone!**\n\n"
                   "Try saying:\n"
                   "- 'Take off'\n"
                   "- 'Move forward 50 centimeters'\n"
                   "- 'What's my battery level?'\n"
                   "- 'Turn right 90 degrees'\n"
                   "- 'Take a picture'")
    
    st.divider()
    
    # Input section
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_input(
            "💬 Type your message:",
            placeholder="e.g., 'Take off and move forward 100cm'",
            key=f"{container_key}_input"
        )
    
    with col2:
        input_method = st.selectbox(
            "Input Method",
            ["Text", "Voice"],
            key=f"{container_key}_method"
        )
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📤 Send", key=f"{container_key}_send", type="primary"):
            if user_input.strip():
                process_chat_message(drone_chat, user_input, speak_response=True)
    
    with col2:
        if st.button("🎙️ Voice Input", key=f"{container_key}_voice"):
            with st.spinner("🎤 Listening..."):
                voice_input = drone_chat.listen_for_speech(timeout=5)
                if voice_input:
                    process_chat_message(drone_chat, voice_input, speak_response=True)
                else:
                    st.warning("No speech detected. Please try again.")
    
    with col3:
        if st.button("🔊 Test Voice", key=f"{container_key}_test_voice"):
            drone_chat.speak_text("Hello! This is your drone assistant. I'm ready to help you control your drone.")
            st.success("Voice test completed!")
    
    with col4:
        if st.button("🗑️ Clear Chat", key=f"{container_key}_clear"):
            drone_chat.conversation_history = []
            st.rerun()
    
    # Voice settings in expander
    with st.expander("🔊 Voice Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            speech_rate = st.slider(
                "Speech Rate", 50, 300, drone_chat.speech_rate,
                key=f"{container_key}_rate"
            )
            
            enable_voice_response = st.checkbox(
                "Enable Voice Response", value=True,
                key=f"{container_key}_voice_response"
            )
        
        with col2:
            speech_volume = st.slider(
                "Speech Volume", 0.0, 1.0, drone_chat.speech_volume,
                key=f"{container_key}_volume"
            )
            
            # Voice selection
            available_voices = drone_chat.get_available_voices()
            if available_voices:
                voice_names = [f"{v['name']} ({v['language']})" for v in available_voices]
                voice_selection = st.selectbox(
                    "Voice", voice_names,
                    index=min(drone_chat.voice_index, len(voice_names) - 1),
                    key=f"{container_key}_voice_select"
                )
                new_voice_index = voice_names.index(voice_selection)
            else:
                new_voice_index = 0
        
        # Apply voice settings if changed
        if (speech_rate != drone_chat.speech_rate or 
            speech_volume != drone_chat.speech_volume or
            new_voice_index != drone_chat.voice_index):
            
            success = drone_chat.set_voice_settings(
                rate=speech_rate,
                volume=speech_volume,
                voice_index=new_voice_index
            )
            
            if success:
                st.success("Voice settings updated!")
            else:
                st.error("Failed to update voice settings")
    
    # Conversation statistics
    with st.expander("📊 Conversation Stats"):
        stats = drone_chat.get_conversation_summary()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Messages", stats['total_messages'])
        
        with col2:
            st.metric("Commands Executed", stats['command_messages'])
        
        with col3:
            st.metric("Success Rate", f"{stats['success_rate']:.1f}%")
    
    # Real-time status indicators
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        if drone_chat.is_listening:
            st.info("🎤 Listening for voice input...")
    
    with status_col2:
        if drone_chat.is_speaking:
            st.info("🔊 Speaking response...")

def process_chat_message(drone_chat: DroneChat, user_input: str, speak_response: bool = True):
    """Process a chat message and execute commands."""
    try:
        # Parse the input for drone commands
        command_data = drone_chat.parse_drone_command(user_input)
        
        # Execute the command
        if command_data['command'] != 'general':
            response = asyncio.run(drone_chat.execute_drone_command(command_data))
        else:
            response = "I understand you're trying to communicate, but I'm specifically designed for drone control. Try commands like 'take off', 'move forward', or 'check status'."
        
        # Add to conversation history
        drone_chat.add_to_conversation(user_input, response, command_data)
        
        # Speak response if enabled
        if speak_response and drone_chat.speech_engine:
            # Clean response for speech (remove emojis and formatting)
            clean_response = re.sub(r'[^\w\s.,!?-]', '', response)
            drone_chat.speak_text(clean_response)
        
        # Show success message
        st.success("✅ Message processed!")
        st.rerun()
        
    except Exception as e:
        error_msg = f"❌ Failed to process message: {str(e)}"
        st.error(error_msg)
        logger.error(f"Chat processing error: {e}")

# Voice command shortcuts
def render_voice_shortcuts(drone_chat: DroneChat):
    """Render quick voice command buttons."""
    st.subheader("🎙️ Quick Voice Commands")
    
    commands = [
        ("Take Off", "take off"),
        ("Land", "land"),
        ("Forward 50cm", "move forward 50 centimeters"),
        ("Backward 50cm", "move backward 50 centimeters"),
        ("Turn Right", "turn right 90 degrees"),
        ("Turn Left", "turn left 90 degrees"),
        ("Status Check", "what's my battery and height"),
        ("Take Photo", "take a picture")
    ]
    
    cols = st.columns(4)
    for i, (label, command) in enumerate(commands):
        with cols[i % 4]:
            if st.button(f"🗣️ {label}", key=f"voice_cmd_{i}"):
                process_chat_message(drone_chat, command, speak_response=True)