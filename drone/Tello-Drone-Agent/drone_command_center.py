#!/usr/bin/env python3
"""
Drone Command Center - Streamlit Interface
A comprehensive web-based interface for controlling and monitoring the Tello drone.
"""

import streamlit as st
import asyncio
import threading
import time
import queue
import json
import base64
import cv2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
from streamlit_webrtc import webrtc_streamer, RTCConfiguration
import speech_recognition as sr
import pyttsx3
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import our drone components
from autonomous_realtime_drone_agent import RealtimeDroneAgent, DroneState
from drone_controller import DroneController
from vision_analyzer import VisionAnalyzer
from camera_streaming import CameraStream, render_camera_component
from chat_interface import DroneChat, render_chat_interface, render_voice_shortcuts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="🚁 Drone Command Center",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .status-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #2a5298;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .emergency-btn {
        background-color: #ff4444 !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        border-radius: 5px !important;
        font-weight: bold !important;
    }
    
    .success-btn {
        background-color: #44ff44 !important;
        color: white !important;
    }
    
    .warning-btn {
        background-color: #ffaa44 !important;
        color: white !important;
    }
    
    .info-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2a5298;
    }
    
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

class DroneCommandCenter:
    """Main class for the Streamlit Drone Command Center."""
    
    def __init__(self):
        self.drone_agent = None
        self.vision_only = True
        self.is_connected = False
        self.is_running = False
        
        # Initialize session state variables
        self._init_session_state()
        
        # Initialize components
        self.camera_stream = CameraStream()
        self.drone_chat = DroneChat()
        
        # Mission planning
        self.waypoints = []
        self.mission_status = "idle"
        
    def _init_session_state(self):
        """Initialize Streamlit session state variables."""
        if 'drone_state' not in st.session_state:
            st.session_state.drone_state = DroneState()
        
        if 'flight_log' not in st.session_state:
            st.session_state.flight_log = []
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'telemetry_data' not in st.session_state:
            st.session_state.telemetry_data = {
                'timestamps': [],
                'battery': [],
                'height': [],
                'movement_count': []
            }
        
        if 'emergency_stop' not in st.session_state:
            st.session_state.emergency_stop = False
        
        if 'mission_waypoints' not in st.session_state:
            st.session_state.mission_waypoints = []
        
        if 'connection_status' not in st.session_state:
            st.session_state.connection_status = "Disconnected"
    
    def render_header(self):
        """Render the main header."""
        st.markdown("""
        <div class="main-header">
            <h1>🚁 Drone Command Center</h1>
            <p>Advanced Autonomous Drone Control Interface</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with connection settings and mode selection."""
        st.sidebar.title("🔧 Control Panel")
        
        # Connection Settings
        st.sidebar.subheader("📡 Connection Settings")
        
        # Mode selection
        mode_options = ["Vision Only (Safe)", "Real Drone (Hardware)"]
        selected_mode = st.sidebar.selectbox(
            "Operation Mode",
            mode_options,
            index=0 if self.vision_only else 1,
            help="Vision Only mode simulates drone without hardware"
        )
        self.vision_only = selected_mode == mode_options[0]
        
        # Environment variables check
        st.sidebar.subheader("🔑 API Configuration")
        azure_endpoint = st.sidebar.text_input(
            "Azure OpenAI Endpoint",
            value=os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            type="password"
        )
        azure_key = st.sidebar.text_input(
            "Azure OpenAI API Key",
            value=os.getenv('AZURE_OPENAI_API_KEY', ''),
            type="password"
        )
        
        # Connection controls
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🔌 Connect", use_container_width=True):
                self.connect_drone()
        
        with col2:
            if st.button("🔌 Disconnect", use_container_width=True):
                self.disconnect_drone()
        
        # Status display
        status_color = "🟢" if self.is_connected else "🔴"
        st.sidebar.markdown(f"**Status:** {status_color} {st.session_state.connection_status}")
        
        # Emergency stop
        st.sidebar.subheader("🚨 Emergency Controls")
        if st.sidebar.button("🛑 EMERGENCY STOP", type="primary", use_container_width=True):
            self.emergency_stop()
        
        # Quick actions
        st.sidebar.subheader("⚡ Quick Actions")
        if st.sidebar.button("🚁 Takeoff", disabled=not self.is_connected):
            asyncio.run(self.quick_takeoff())
        
        if st.sidebar.button("🛬 Land", disabled=not self.is_connected):
            asyncio.run(self.quick_land())
        
        if st.sidebar.button("📸 Capture Image", disabled=not self.is_connected):
            asyncio.run(self.capture_image())
    
    def render_main_dashboard(self):
        """Render the main dashboard with tabs."""
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🎮 Manual Control", 
            "💬 Chat Interface", 
            "📊 Telemetry", 
            "🗺️ Mission Planning", 
            "📹 Camera Feed", 
            "⚙️ Settings"
        ])
        
        with tab1:
            self.render_manual_control()
        
        with tab2:
            self.render_chat_interface()
        
        with tab3:
            self.render_telemetry()
        
        with tab4:
            self.render_mission_planning()
        
        with tab5:
            self.render_camera_feed()
        
        with tab6:
            self.render_settings()
    
    def render_manual_control(self):
        """Render manual drone control interface."""
        st.subheader("🎮 Manual Drone Control")
        
        # Flight status overview
        status_container = st.container()
        with status_container:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                flight_status = "✈️ Flying" if st.session_state.drone_state.is_flying else "🛬 Grounded"
                st.metric("Flight Status", flight_status)
            
            with col2:
                battery_level = st.session_state.drone_state.battery
                battery_color = "🟢" if battery_level > 50 else "🟡" if battery_level > 20 else "🔴"
                st.metric("Battery", f"{battery_color} {battery_level}%")
            
            with col3:
                height = st.session_state.drone_state.height
                st.metric("Height", f"📏 {height} cm")
            
            with col4:
                movements = st.session_state.drone_state.movement_count
                st.metric("Movements", f"🎯 {movements}")
            
            with col5:
                mode = "🔒 Vision" if self.vision_only else "🚁 Real"
                st.metric("Mode", mode)
        
        st.divider()
        
        # Emergency controls (prominent)
        emergency_col1, emergency_col2, emergency_col3 = st.columns([1, 2, 1])
        with emergency_col2:
            if st.button("🚨 EMERGENCY STOP 🚨", key="emergency_main", 
                        help="Immediately land the drone", 
                        use_container_width=True):
                self.emergency_stop()
                st.error("🚨 Emergency stop activated!")
        
        st.divider()
        
        # Primary flight controls
        st.subheader("✈️ Primary Flight Controls")
        
        primary_col1, primary_col2, primary_col3 = st.columns(3)
        
        with primary_col1:
            takeoff_disabled = not self.is_connected or st.session_state.drone_state.is_flying
            if st.button("🚁 TAKEOFF", 
                        disabled=takeoff_disabled,
                        use_container_width=True,
                        type="primary",
                        help="Take off and hover"):
                asyncio.run(self.execute_command("takeoff"))
        
        with primary_col2:
            status_disabled = not self.is_connected
            if st.button("� STATUS CHECK", 
                        disabled=status_disabled,
                        use_container_width=True,
                        help="Get current drone status"):
                asyncio.run(self.execute_command("get_drone_status"))
        
        with primary_col3:
            land_disabled = not self.is_connected or not st.session_state.drone_state.is_flying
            if st.button("� LAND", 
                        disabled=land_disabled,
                        use_container_width=True,
                        type="secondary",
                        help="Land at current position"):
                asyncio.run(self.execute_command("land"))
        
        st.divider()
        
        # Movement controls
        st.subheader("🎮 Movement Controls")
        
        # Distance and speed settings
        control_col1, control_col2 = st.columns(2)
        
        with control_col1:
            distance = st.slider("Movement Distance (cm)", 20, 200, 50, 
                               help="Distance for each movement command")
        
        with control_col2:
            angle = st.slider("Rotation Angle (degrees)", 30, 180, 90,
                             help="Angle for rotation commands")
        
        # Movement grid with directional controls
        st.markdown("**Directional Movement:**")
        
        # Top row
        top_col1, top_col2, top_col3 = st.columns(3)
        
        with top_col1:
            if st.button("↖️ Up-Left", use_container_width=True, 
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_up", distance//2))
                asyncio.run(self.execute_movement("move_left", distance//2))
        
        with top_col2:
            if st.button("⬆️ Forward", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_forward", distance))
        
        with top_col3:
            if st.button("↗️ Up-Right", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_up", distance//2))
                asyncio.run(self.execute_movement("move_right", distance//2))
        
        # Middle row
        mid_col1, mid_col2, mid_col3 = st.columns(3)
        
        with mid_col1:
            if st.button("⬅️ Left", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_left", distance))
        
        with mid_col2:
            # Vertical controls
            vert_col1, vert_col2 = st.columns(2)
            with vert_col1:
                if st.button("⬆️ Up", use_container_width=True,
                            disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                    asyncio.run(self.execute_movement("move_up", distance))
            with vert_col2:
                if st.button("⬇️ Down", use_container_width=True,
                            disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                    asyncio.run(self.execute_movement("move_down", distance))
        
        with mid_col3:
            if st.button("➡️ Right", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_right", distance))
        
        # Bottom row
        bottom_col1, bottom_col2, bottom_col3 = st.columns(3)
        
        with bottom_col1:
            if st.button("↙️ Down-Left", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_down", distance//2))
                asyncio.run(self.execute_movement("move_left", distance//2))
        
        with bottom_col2:
            if st.button("⬇️ Backward", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_backward", distance))
        
        with bottom_col3:
            if st.button("↘️ Down-Right", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_movement("move_down", distance//2))
                asyncio.run(self.execute_movement("move_right", distance//2))
        
        st.divider()
        
        # Rotation controls
        st.markdown("**Rotation Controls:**")
        
        rot_col1, rot_col2 = st.columns(2)
        
        with rot_col1:
            if st.button("↪️ Rotate Right", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_rotation("rotate_clockwise", angle))
        
        with rot_col2:
            if st.button("↩️ Rotate Left", use_container_width=True,
                        disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                asyncio.run(self.execute_rotation("rotate_counter_clockwise", angle))
        
        st.divider()
        
        # Advanced controls
        with st.expander("🎯 Advanced Controls"):
            st.markdown("**Precision Movement:**")
            
            adv_col1, adv_col2 = st.columns(2)
            
            with adv_col1:
                st.markdown("**Go to XYZ Position:**")
                x_pos = st.number_input("X (cm)", value=0, min_value=-100, max_value=100, key="manual_x")
                y_pos = st.number_input("Y (cm)", value=0, min_value=-100, max_value=100, key="manual_y")
                z_pos = st.number_input("Z (cm)", value=0, min_value=-50, max_value=100, key="manual_z")
                speed = st.number_input("Speed (cm/s)", value=30, min_value=10, max_value=100, key="manual_speed")
                
                if st.button("🎯 Go to Position", use_container_width=True,
                            disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                    asyncio.run(self.execute_xyz_movement(x_pos, y_pos, z_pos, speed))
            
            with adv_col2:
                st.markdown("**Curved Movement:**")
                x1 = st.number_input("X1 (cm)", value=20, min_value=-30, max_value=30, key="curve_x1")
                y1 = st.number_input("Y1 (cm)", value=0, min_value=-30, max_value=30, key="curve_y1")
                z1 = st.number_input("Z1 (cm)", value=0, min_value=-30, max_value=30, key="curve_z1")
                x2 = st.number_input("X2 (cm)", value=20, min_value=-30, max_value=30, key="curve_x2")
                y2 = st.number_input("Y2 (cm)", value=30, min_value=-30, max_value=30, key="curve_y2")
                z2 = st.number_input("Z2 (cm)", value=0, min_value=-30, max_value=30, key="curve_z2")
                curve_speed = st.number_input("Curve Speed (cm/s)", value=30, min_value=10, max_value=60, key="curve_speed")
                
                if st.button("🌀 Curved Flight", use_container_width=True,
                            disabled=not self.is_connected or not st.session_state.drone_state.is_flying):
                    asyncio.run(self.execute_curve_movement(x1, y1, z1, x2, y2, z2, curve_speed))
        
        # Safety reminder
        st.info("💡 **Safety Tip:** Always ensure clear flight space and maintain visual contact with your drone.")
    
    def render_chat_interface(self):
        """Render chat interface with text and speech input."""
        # Use the integrated chat interface component
        render_chat_interface(self.drone_chat, "main_chat")
        
        st.divider()
        
        # Voice shortcuts for quick commands
        render_voice_shortcuts(self.drone_chat)
    
    def render_telemetry(self):
        """Render real-time telemetry dashboard."""
        st.subheader("📊 Flight Telemetry")
        
        # Real-time metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🔋 Battery Level",
                f"{st.session_state.drone_state.battery}%",
                delta=self.get_battery_delta()
            )
        
        with col2:
            st.metric(
                "📏 Current Height",
                f"{st.session_state.drone_state.height} cm",
                delta=self.get_height_delta()
            )
        
        with col3:
            st.metric(
                "🎯 Total Movements",
                st.session_state.drone_state.movement_count,
                delta=1 if st.session_state.drone_state.movement_count > 0 else 0
            )
        
        with col4:
            flight_time = self.calculate_flight_time()
            st.metric(
                "⏱️ Flight Time",
                flight_time,
                delta=None
            )
        
        # Charts
        if st.session_state.telemetry_data['timestamps']:
            col1, col2 = st.columns(2)
            
            with col1:
                # Battery chart
                battery_fig = px.line(
                    x=st.session_state.telemetry_data['timestamps'],
                    y=st.session_state.telemetry_data['battery'],
                    title="Battery Level Over Time",
                    labels={'x': 'Time', 'y': 'Battery (%)'}
                )
                st.plotly_chart(battery_fig, use_container_width=True)
            
            with col2:
                # Height chart
                height_fig = px.line(
                    x=st.session_state.telemetry_data['timestamps'],
                    y=st.session_state.telemetry_data['height'],
                    title="Height Over Time",
                    labels={'x': 'Time', 'y': 'Height (cm)'}
                )
                st.plotly_chart(height_fig, use_container_width=True)
        
        # Flight log
        st.subheader("📝 Flight Log")
        if st.session_state.flight_log:
            df = pd.DataFrame(st.session_state.flight_log)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No flight data recorded yet. Start flying to see logs here!")
        
        # Export data
        if st.button("📥 Export Flight Data"):
            self.export_flight_data()
    
    def render_mission_planning(self):
        """Render mission planning interface."""
        st.subheader("🗺️ Mission Planning")
        
        # Mission status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Mission Status", self.mission_status.title())
        
        with col2:
            st.metric("Waypoints", len(st.session_state.mission_waypoints))
        
        with col3:
            if st.button("🎯 Execute Mission", disabled=not st.session_state.mission_waypoints):
                self.execute_mission()
        
        st.divider()
        
        # Waypoint input
        st.subheader("📍 Add Waypoints")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            x_coord = st.number_input("X (cm)", value=0, min_value=-100, max_value=100)
        
        with col2:
            y_coord = st.number_input("Y (cm)", value=0, min_value=-100, max_value=100)
        
        with col3:
            z_coord = st.number_input("Z (cm)", value=0, min_value=-50, max_value=100)
        
        with col4:
            speed = st.number_input("Speed (cm/s)", value=30, min_value=10, max_value=100)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ Add Waypoint", use_container_width=True):
                self.add_waypoint(x_coord, y_coord, z_coord, speed)
        
        with col2:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.mission_waypoints = []
                st.rerun()
        
        with col3:
            if st.button("💾 Save Mission", use_container_width=True):
                self.save_mission()
        
        # Waypoint list
        if st.session_state.mission_waypoints:
            st.subheader("📋 Mission Waypoints")
            waypoint_df = pd.DataFrame(st.session_state.mission_waypoints)
            st.dataframe(waypoint_df, use_container_width=True)
            
            # 3D visualization
            if len(st.session_state.mission_waypoints) > 1:
                self.render_3d_mission_plot()
        
        # Pre-defined missions
        st.subheader("🎯 Pre-defined Missions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Square Pattern", use_container_width=True):
                self.load_square_mission()
        
        with col2:
            if st.button("⭕ Circle Pattern", use_container_width=True):
                self.load_circle_mission()
        
        with col3:
            if st.button("📐 Triangle Pattern", use_container_width=True):
                self.load_triangle_mission()
    
    def render_camera_feed(self):
        """Render live camera feed."""
        st.subheader("📹 Live Camera Feed")
        
        # Camera source selection
        col1, col2, col3 = st.columns(3)
        
        with col1:
            camera_source = "Drone Camera" if not self.vision_only else "Webcam"
            st.info(f"📹 **Active Source:** {camera_source}")
        
        with col2:
            if st.button("🔄 Restart Stream", use_container_width=True):
                if self.is_connected:
                    self.camera_stream.stop_camera_stream()
                    time.sleep(1)
                    source = "webcam" if self.vision_only else "drone"
                    drone_obj = None if self.vision_only else self.drone_agent.drone
                    success = self.camera_stream.start_camera_stream(source, drone_obj)
                    if success:
                        st.success("Camera stream restarted!")
                    else:
                        st.error("Failed to restart camera stream")
        
        with col3:
            stream_status = "🟢 Active" if self.camera_stream.is_streaming else "🔴 Inactive"
            st.write(f"**Status:** {stream_status}")
        
        st.divider()
        
        # Render camera component
        if self.is_connected:
            render_camera_component(self.camera_stream, "main_camera")
        else:
            st.warning("Connect to drone first to enable camera feed")
        
        # Image analysis display
        if st.session_state.drone_state.last_image_analysis:
            with st.expander("🔍 Latest Image Analysis", expanded=True):
                st.write(st.session_state.drone_state.last_image_analysis)
                
                # Quick analysis actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔍 Analyze Objects", disabled=not self.is_connected):
                        asyncio.run(self.capture_and_analyze("objects"))
                
                with col2:
                    if st.button("🚧 Check Obstacles", disabled=not self.is_connected):
                        asyncio.run(self.capture_and_analyze("obstacles"))
                
                with col3:
                    if st.button("🎯 Find Landing Spot", disabled=not self.is_connected):
                        asyncio.run(self.capture_and_analyze("landing_spot"))
    
    def render_settings(self):
        """Render settings and configuration panel."""
        st.subheader("⚙️ Settings & Configuration")
        
        # Safety settings
        st.subheader("🛡️ Safety Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_height = st.number_input("Max Height (cm)", value=200, min_value=50, max_value=500)
            max_distance = st.number_input("Max Distance (cm)", value=100, min_value=20, max_value=300)
        
        with col2:
            min_battery = st.number_input("Min Battery (%)", value=20, min_value=10, max_value=50)
            auto_land = st.checkbox("Auto-land on low battery", value=True)
        
        # Communication settings
        st.subheader("📡 Communication Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            connection_timeout = st.number_input("Connection Timeout (s)", value=30, min_value=10, max_value=120)
            retry_attempts = st.number_input("Retry Attempts", value=3, min_value=1, max_value=10)
        
        with col2:
            heartbeat_interval = st.number_input("Heartbeat Interval (s)", value=5, min_value=1, max_value=30)
            command_delay = st.number_input("Command Delay (ms)", value=100, min_value=50, max_value=1000)
        
        # Audio settings
        st.subheader("🔊 Audio Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_voice_feedback = st.checkbox("Enable Voice Feedback", value=True)
            voice_rate = st.slider("Voice Rate", 100, 300, 150)
        
        with col2:
            enable_sound_effects = st.checkbox("Enable Sound Effects", value=True)
            master_volume = st.slider("Master Volume", 0.0, 1.0, 0.8)
        
        # Save settings
        if st.button("💾 Save Settings", use_container_width=True):
            self.save_settings({
                'max_height': max_height,
                'max_distance': max_distance,
                'min_battery': min_battery,
                'auto_land': auto_land,
                'connection_timeout': connection_timeout,
                'retry_attempts': retry_attempts,
                'heartbeat_interval': heartbeat_interval,
                'command_delay': command_delay,
                'enable_voice_feedback': enable_voice_feedback,
                'voice_rate': voice_rate,
                'enable_sound_effects': enable_sound_effects,
                'master_volume': master_volume
            })
            st.success("Settings saved successfully!")
    
    # Core functionality methods
    async def execute_command(self, command: str, **kwargs):
        """Execute a drone command."""
        if not self.drone_agent:
            st.error("Drone not connected!")
            return
        
        try:
            if hasattr(self.drone_agent.drone_controller, command):
                result = await getattr(self.drone_agent.drone_controller, command)(**kwargs)
                self.log_action(command, result, kwargs)
                self.update_telemetry()
                st.success(f"Command executed: {result}")
            else:
                st.error(f"Unknown command: {command}")
        except Exception as e:
            st.error(f"Command failed: {str(e)}")
            logger.error(f"Command {command} failed: {e}")
    
    async def execute_movement(self, command: str, distance: int):
        """Execute a movement command."""
        await self.execute_command(command, distance=distance)
    
    async def execute_rotation(self, command: str, angle: int):
        """Execute a rotation command."""
        await self.execute_command(command, angle=angle)
    
    def connect_drone(self):
        """Connect to the drone."""
        try:
            # Initialize drone agent
            self.drone_agent = RealtimeDroneAgent(vision_only=self.vision_only)
            
            # Connect chat interface to drone agent
            self.drone_chat.drone_agent = self.drone_agent
            
            # Start camera stream
            camera_source = "webcam" if self.vision_only else "drone"
            drone_obj = None if self.vision_only else self.drone_agent.drone
            self.camera_stream.start_camera_stream(camera_source, drone_obj)
            
            # Set connection status
            self.is_connected = True
            st.session_state.connection_status = "Connected (Vision Only)" if self.vision_only else "Connected (Real Drone)"
            
            st.success(f"Connected in {'Vision Only' if self.vision_only else 'Real Drone'} mode!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Connection failed: {str(e)}")
            logger.error(f"Connection failed: {e}")
    
    def disconnect_drone(self):
        """Disconnect from the drone."""
        try:
            # Stop camera stream
            self.camera_stream.stop_camera_stream()
            
            # Disconnect chat interface
            self.drone_chat.drone_agent = None
            
            if self.drone_agent:
                # Clean up drone agent
                self.drone_agent = None
            
            self.is_connected = False
            st.session_state.connection_status = "Disconnected"
            
            st.success("Disconnected successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Disconnection failed: {str(e)}")
            logger.error(f"Disconnection failed: {e}")
    
    def emergency_stop(self):
        """Emergency stop all operations."""
        st.session_state.emergency_stop = True
        
        if self.drone_agent and st.session_state.drone_state.is_flying:
            try:
                asyncio.run(self.execute_command("land"))
                st.error("🚨 EMERGENCY STOP ACTIVATED - LANDING DRONE")
            except Exception as e:
                st.error(f"Emergency landing failed: {str(e)}")
        
        st.session_state.emergency_stop = False
    
    def log_action(self, action: str, result: str, params: dict = None):
        """Log an action to the flight log."""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'action': action,
            'result': result,
            'parameters': params or {}
        }
        st.session_state.flight_log.append(log_entry)
    
    def update_telemetry(self):
        """Update telemetry data."""
        current_time = datetime.now()
        st.session_state.telemetry_data['timestamps'].append(current_time)
        st.session_state.telemetry_data['battery'].append(st.session_state.drone_state.battery)
        st.session_state.telemetry_data['height'].append(st.session_state.drone_state.height)
        st.session_state.telemetry_data['movement_count'].append(st.session_state.drone_state.movement_count)
    
    # Additional helper methods and missing implementations
    
    async def execute_xyz_movement(self, x: int, y: int, z: int, speed: int):
        """Execute XYZ coordinate movement."""
        await self.execute_command("go_xyz_speed", x=x, y=y, z=z, speed=speed)
    
    async def execute_curve_movement(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """Execute curved movement."""
        await self.execute_command("curve_xyz_speed", x1=x1, y1=y1, z1=z1, x2=x2, y2=y2, z2=z2, speed=speed)
    
    async def capture_and_analyze(self, focus: str):
        """Capture and analyze image with specific focus."""
        await self.execute_command("capture_and_analyze_image", focus=focus)
    
    def get_battery_delta(self):
        """Get battery level change."""
        if len(st.session_state.telemetry_data['battery']) >= 2:
            current = st.session_state.telemetry_data['battery'][-1]
            previous = st.session_state.telemetry_data['battery'][-2]
            return current - previous
        return None
    
    def get_height_delta(self):
        """Get height change."""
        if len(st.session_state.telemetry_data['height']) >= 2:
            current = st.session_state.telemetry_data['height'][-1]
            previous = st.session_state.telemetry_data['height'][-2]
            return current - previous
        return None
    
    def calculate_flight_time(self):
        """Calculate total flight time."""
        if st.session_state.drone_state.is_flying and st.session_state.telemetry_data['timestamps']:
            start_time = st.session_state.telemetry_data['timestamps'][0]
            current_time = datetime.now()
            flight_duration = current_time - start_time
            
            hours, remainder = divmod(int(flight_duration.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"
    
    def save_settings(self, settings: dict):
        """Save application settings."""
        try:
            # Store in session state for now (could be expanded to file persistence)
            if 'app_settings' not in st.session_state:
                st.session_state.app_settings = {}
            
            st.session_state.app_settings.update(settings)
            logger.info("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def export_flight_data(self):
        """Export flight data to CSV."""
        if st.session_state.flight_log:
            try:
                df = pd.DataFrame(st.session_state.flight_log)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Flight Log CSV",
                    data=csv,
                    file_name=f"flight_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.success(f"Flight log with {len(st.session_state.flight_log)} entries ready for download!")
                
            except Exception as e:
                st.error(f"Failed to export flight data: {e}")
        else:
            st.warning("No flight data to export")
    
    def save_mission(self):
        """Save current mission plan."""
        if st.session_state.mission_waypoints:
            try:
                mission_data = {
                    'name': f"Mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'waypoints': st.session_state.mission_waypoints,
                    'created': datetime.now().isoformat(),
                    'total_waypoints': len(st.session_state.mission_waypoints)
                }
                
                # Store in session state (could be expanded to file persistence)
                if 'saved_missions' not in st.session_state:
                    st.session_state.saved_missions = []
                
                st.session_state.saved_missions.append(mission_data)
                
                st.success(f"Mission saved with {len(st.session_state.mission_waypoints)} waypoints!")
                
            except Exception as e:
                st.error(f"Failed to save mission: {e}")
        else:
            st.warning("No waypoints to save")
    
    def execute_mission(self):
        """Execute the planned mission."""
        if not st.session_state.mission_waypoints:
            st.warning("No mission waypoints defined")
            return
        
        if not self.is_connected:
            st.error("Drone not connected")
            return
        
        try:
            self.mission_status = "executing"
            
            # Create a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_waypoints = len(st.session_state.mission_waypoints)
            
            for i, waypoint in enumerate(st.session_state.mission_waypoints):
                status_text.text(f"Executing waypoint {i+1}/{total_waypoints}: {waypoint}")
                
                # Execute waypoint movement
                asyncio.run(self.execute_xyz_movement(
                    waypoint['x'], waypoint['y'], waypoint['z'], waypoint['speed']
                ))
                
                # Update progress
                progress = (i + 1) / total_waypoints
                progress_bar.progress(progress)
                
                # Small delay between waypoints
                time.sleep(1)
            
            self.mission_status = "completed"
            status_text.text("Mission completed successfully!")
            st.success("🎯 Mission executed successfully!")
            
        except Exception as e:
            self.mission_status = "failed"
            st.error(f"Mission execution failed: {e}")
            logger.error(f"Mission execution error: {e}")
    
    def render_3d_mission_plot(self):
        """Render 3D mission visualization."""
        if len(st.session_state.mission_waypoints) > 1:
            try:
                waypoints = st.session_state.mission_waypoints
                
                # Extract coordinates
                x_coords = [w['x'] for w in waypoints]
                y_coords = [w['y'] for w in waypoints]
                z_coords = [w['z'] for w in waypoints]
                
                # Create 3D plot
                fig = go.Figure()
                
                # Add waypoint path
                fig.add_trace(go.Scatter3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    mode='lines+markers',
                    marker=dict(
                        size=8,
                        color=list(range(len(waypoints))),
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Waypoint Order")
                    ),
                    line=dict(width=4, color='blue'),
                    name='Mission Path',
                    text=[f"Waypoint {i+1}<br>Speed: {w['speed']} cm/s" for i, w in enumerate(waypoints)],
                    hovertemplate="<b>%{text}</b><br>X: %{x} cm<br>Y: %{y} cm<br>Z: %{z} cm<extra></extra>"
                ))
                
                # Add start and end markers
                fig.add_trace(go.Scatter3d(
                    x=[x_coords[0]],
                    y=[y_coords[0]],
                    z=[z_coords[0]],
                    mode='markers',
                    marker=dict(size=12, color='green', symbol='circle'),
                    name='Start',
                    hovertemplate="<b>Start Point</b><br>X: %{x} cm<br>Y: %{y} cm<br>Z: %{z} cm<extra></extra>"
                ))
                
                fig.add_trace(go.Scatter3d(
                    x=[x_coords[-1]],
                    y=[y_coords[-1]],
                    z=[z_coords[-1]],
                    mode='markers',
                    marker=dict(size=12, color='red', symbol='diamond'),
                    name='End',
                    hovertemplate="<b>End Point</b><br>X: %{x} cm<br>Y: %{y} cm<br>Z: %{z} cm<extra></extra>"
                ))
                
                # Update layout
                fig.update_layout(
                    title="🗺️ 3D Mission Flight Path",
                    scene=dict(
                        xaxis_title="X Position (cm)",
                        yaxis_title="Y Position (cm)",
                        zaxis_title="Z Position (cm)",
                        camera=dict(
                            eye=dict(x=1.5, y=1.5, z=1.5)
                        )
                    ),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Failed to render 3D plot: {e}")
    # Mission pattern loading methods
    def add_waypoint(self, x, y, z, speed):
        """Add a waypoint to the mission."""
        waypoint = {
            'x': x, 'y': y, 'z': z, 'speed': speed,
            'order': len(st.session_state.mission_waypoints) + 1
        }
        st.session_state.mission_waypoints.append(waypoint)
        st.rerun()
    
    def load_square_mission(self):
        """Load a square flight pattern."""
        st.session_state.mission_waypoints = [
            {'x': 50, 'y': 0, 'z': 0, 'speed': 30, 'order': 1},
            {'x': 50, 'y': 50, 'z': 0, 'speed': 30, 'order': 2},
            {'x': 0, 'y': 50, 'z': 0, 'speed': 30, 'order': 3},
            {'x': 0, 'y': 0, 'z': 0, 'speed': 30, 'order': 4}
        ]
        st.success("Square mission pattern loaded!")
        st.rerun()
    
    def load_circle_mission(self):
        """Load a circular flight pattern."""
        import math
        waypoints = []
        radius = 50
        for i in range(8):
            angle = (2 * math.pi * i) / 8
            x = int(radius * math.cos(angle))
            y = int(radius * math.sin(angle))
            waypoints.append({'x': x, 'y': y, 'z': 0, 'speed': 30, 'order': i+1})
        st.session_state.mission_waypoints = waypoints
        st.success("Circle mission pattern loaded!")
        st.rerun()
    
    def load_triangle_mission(self):
        """Load a triangular flight pattern."""
        st.session_state.mission_waypoints = [
            {'x': 50, 'y': 0, 'z': 0, 'speed': 30, 'order': 1},
            {'x': 25, 'y': 43, 'z': 0, 'speed': 30, 'order': 2},
            {'x': -25, 'y': 43, 'z': 0, 'speed': 30, 'order': 3},
            {'x': 0, 'y': 0, 'z': 0, 'speed': 30, 'order': 4}
        ]
        st.success("Triangle mission pattern loaded!")
        st.rerun()
    
    # Quick action methods
    async def quick_takeoff(self):
        """Quick takeoff action."""
        await self.execute_command("takeoff")
    
    async def quick_land(self):
        """Quick land action."""
        await self.execute_command("land")
    
    async def capture_image(self):
        """Capture and analyze image."""
        await self.execute_command("capture_and_analyze_image", focus="objects")

def main():
    """Main application entry point."""
    # Initialize command center
    command_center = DroneCommandCenter()
    
    # Render the application
    command_center.render_header()
    command_center.render_sidebar()
    command_center.render_main_dashboard()
    
    # Auto-refresh for real-time updates
    time.sleep(0.1)

if __name__ == "__main__":
    main()