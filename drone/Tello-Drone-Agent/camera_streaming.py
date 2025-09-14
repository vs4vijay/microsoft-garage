#!/usr/bin/env python3
"""
Camera Streaming Component for Drone Command Center
Handles live video streaming from drone camera or webcam.
"""

import cv2
import numpy as np
import streamlit as st
import threading
import time
import queue
from typing import Optional, Tuple, Any
import logging
from datetime import datetime
import base64

logger = logging.getLogger(__name__)

class CameraStream:
    """Enhanced camera streaming for drone command center."""
    
    def __init__(self):
        self.is_streaming = False
        self.current_frame = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.capture_thread = None
        self.camera_source = None
        self.frame_count = 0
        self.recording = False
        self.video_writer = None
        
        # Camera settings
        self.resolution = (640, 480)
        self.fps = 24
        self.brightness = 0
        self.contrast = 0
        
    def start_camera_stream(self, source: str = "webcam", drone=None) -> bool:
        """
        Start camera streaming.
        
        Args:
            source: "webcam" or "drone"
            drone: Drone object if using drone camera
        """
        try:
            if source == "drone" and drone:
                # Use drone camera
                self.camera_source = self._setup_drone_camera(drone)
            else:
                # Use webcam
                self.camera_source = self._setup_webcam()
            
            if self.camera_source is None:
                return False
            
            self.is_streaming = True
            self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.capture_thread.start()
            
            logger.info(f"Camera stream started: {source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera stream: {e}")
            return False
    
    def stop_camera_stream(self):
        """Stop camera streaming."""
        self.is_streaming = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        
        if self.camera_source:
            if hasattr(self.camera_source, 'release'):
                self.camera_source.release()
            self.camera_source = None
        
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        logger.info("Camera stream stopped")
    
    def _setup_drone_camera(self, drone) -> Any:
        """Setup drone camera stream."""
        try:
            # Enable drone video stream
            if hasattr(drone, 'streamon'):
                drone.streamon()
            
            # Get frame reader
            if hasattr(drone, 'get_frame_read'):
                return drone.get_frame_read()
            elif hasattr(drone, 'get_frame'):
                return drone
            else:
                logger.warning("Drone doesn't support video streaming")
                return None
                
        except Exception as e:
            logger.error(f"Failed to setup drone camera: {e}")
            return None
    
    def _setup_webcam(self, camera_id: int = 0) -> Optional[cv2.VideoCapture]:
        """Setup webcam stream."""
        try:
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                logger.error("Failed to open webcam")
                return None
            
            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            return cap
            
        except Exception as e:
            logger.error(f"Failed to setup webcam: {e}")
            return None
    
    def _capture_frames(self):
        """Capture frames in a separate thread."""
        while self.is_streaming and self.camera_source:
            try:
                frame = self._get_frame()
                
                if frame is not None:
                    # Apply image processing
                    processed_frame = self._process_frame(frame)
                    
                    # Update current frame
                    self.current_frame = processed_frame
                    
                    # Add to queue for streaming
                    if not self.frame_queue.full():
                        self.frame_queue.put(processed_frame)
                    
                    # Record if enabled
                    if self.recording and self.video_writer:
                        self.video_writer.write(processed_frame)
                    
                    self.frame_count += 1
                
                time.sleep(1 / self.fps)
                
            except Exception as e:
                logger.error(f"Frame capture error: {e}")
                time.sleep(0.1)
    
    def _get_frame(self) -> Optional[np.ndarray]:
        """Get a frame from the camera source."""
        try:
            # Handle different camera source types
            if hasattr(self.camera_source, 'frame'):
                # Drone frame reader
                return self.camera_source.frame
            elif hasattr(self.camera_source, 'get_frame'):
                # Drone direct frame access
                return self.camera_source.get_frame()
            elif hasattr(self.camera_source, 'read'):
                # OpenCV VideoCapture
                ret, frame = self.camera_source.read()
                return frame if ret else None
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get frame: {e}")
            return None
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply image processing to frame."""
        try:
            # Apply brightness adjustment
            if self.brightness != 0:
                frame = cv2.convertScaleAbs(frame, alpha=1, beta=self.brightness)
            
            # Apply contrast adjustment
            if self.contrast != 0:
                alpha = (self.contrast + 50) / 50.0
                frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
            
            # Add timestamp overlay
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (255, 255, 255), 2)
            
            # Add frame counter
            cv2.putText(frame, f"Frame: {self.frame_count}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            return frame
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame."""
        if not self.frame_queue.empty():
            try:
                return self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        return self.current_frame
    
    def capture_photo(self, filename: Optional[str] = None) -> str:
        """Capture a photo from current frame."""
        if self.current_frame is None:
            return "No frame available for capture"
        
        try:
            if filename is None:
                filename = f"drone_photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            cv2.imwrite(filename, self.current_frame)
            logger.info(f"Photo captured: {filename}")
            return f"Photo saved as {filename}"
            
        except Exception as e:
            error_msg = f"Failed to capture photo: {e}"
            logger.error(error_msg)
            return error_msg
    
    def start_recording(self, filename: Optional[str] = None) -> str:
        """Start video recording."""
        if self.current_frame is None:
            return "No video stream available for recording"
        
        try:
            if filename is None:
                filename = f"drone_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                filename, fourcc, self.fps, self.resolution
            )
            
            self.recording = True
            logger.info(f"Recording started: {filename}")
            return f"Recording started: {filename}"
            
        except Exception as e:
            error_msg = f"Failed to start recording: {e}"
            logger.error(error_msg)
            return error_msg
    
    def stop_recording(self) -> str:
        """Stop video recording."""
        if not self.recording:
            return "No recording in progress"
        
        try:
            self.recording = False
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            logger.info("Recording stopped")
            return "Recording stopped successfully"
            
        except Exception as e:
            error_msg = f"Failed to stop recording: {e}"
            logger.error(error_msg)
            return error_msg
    
    def set_camera_settings(self, brightness: int = 0, contrast: int = 0, 
                           resolution: Tuple[int, int] = None, fps: int = None):
        """Update camera settings."""
        self.brightness = max(-50, min(50, brightness))
        self.contrast = max(-50, min(50, contrast))
        
        if resolution:
            self.resolution = resolution
        
        if fps:
            self.fps = max(1, min(60, fps))
        
        # Apply settings to webcam if active
        if hasattr(self.camera_source, 'set') and resolution:
            self.camera_source.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera_source.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        
        if hasattr(self.camera_source, 'set') and fps:
            self.camera_source.set(cv2.CAP_PROP_FPS, fps)
    
    def get_camera_info(self) -> dict:
        """Get camera information and status."""
        return {
            'is_streaming': self.is_streaming,
            'recording': self.recording,
            'frame_count': self.frame_count,
            'resolution': self.resolution,
            'fps': self.fps,
            'brightness': self.brightness,
            'contrast': self.contrast,
            'source_type': 'drone' if hasattr(self.camera_source, 'frame') else 'webcam'
        }
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convert frame to base64 for web display."""
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{frame_base64}"
        except Exception as e:
            logger.error(f"Failed to convert frame to base64: {e}")
            return ""

# Streamlit component for camera display
def render_camera_component(camera_stream: CameraStream, 
                          container_key: str = "camera_feed") -> None:
    """Render camera component in Streamlit."""
    
    # Create placeholder for video feed
    video_placeholder = st.empty()
    
    # Get latest frame
    frame = camera_stream.get_latest_frame()
    
    if frame is not None:
        # Convert BGR to RGB for display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Display frame
        video_placeholder.image(
            frame_rgb,
            channels="RGB",
            use_column_width=True,
            caption="Live Camera Feed"
        )
    else:
        video_placeholder.info("📹 Camera feed not available")
    
    # Camera controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📸 Photo", key=f"{container_key}_photo"):
            result = camera_stream.capture_photo()
            st.success(result)
    
    with col2:
        if camera_stream.recording:
            if st.button("⏹️ Stop Rec", key=f"{container_key}_stop_rec"):
                result = camera_stream.stop_recording()
                st.info(result)
        else:
            if st.button("🎥 Record", key=f"{container_key}_start_rec"):
                result = camera_stream.start_recording()
                st.success(result)
    
    with col3:
        if st.button("🔄 Refresh", key=f"{container_key}_refresh"):
            st.rerun()
    
    with col4:
        camera_info = camera_stream.get_camera_info()
        status_icon = "🟢" if camera_info['is_streaming'] else "🔴"
        st.write(f"{status_icon} {camera_info['source_type'].title()}")
    
    # Camera settings in expander
    with st.expander("⚙️ Camera Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            brightness = st.slider(
                "Brightness", -50, 50, camera_stream.brightness,
                key=f"{container_key}_brightness"
            )
            
            resolution_options = {
                "720p": (1280, 720),
                "480p": (640, 480),
                "360p": (480, 360)
            }
            
            current_res = "480p"  # Default
            for name, res in resolution_options.items():
                if res == camera_stream.resolution:
                    current_res = name
                    break
            
            resolution_name = st.selectbox(
                "Resolution", 
                list(resolution_options.keys()),
                index=list(resolution_options.keys()).index(current_res),
                key=f"{container_key}_resolution"
            )
        
        with col2:
            contrast = st.slider(
                "Contrast", -50, 50, camera_stream.contrast,
                key=f"{container_key}_contrast"
            )
            
            fps = st.slider(
                "FPS", 10, 30, camera_stream.fps,
                key=f"{container_key}_fps"
            )
        
        # Apply settings if changed
        new_resolution = resolution_options[resolution_name]
        if (brightness != camera_stream.brightness or 
            contrast != camera_stream.contrast or
            new_resolution != camera_stream.resolution or
            fps != camera_stream.fps):
            
            camera_stream.set_camera_settings(
                brightness=brightness,
                contrast=contrast,
                resolution=new_resolution,
                fps=fps
            )
            st.success("Camera settings updated!")

# Auto-refresh component for real-time streaming
def auto_refresh_camera(camera_stream: CameraStream, refresh_rate: float = 0.1):
    """Auto-refresh camera feed for real-time streaming."""
    if camera_stream.is_streaming:
        time.sleep(refresh_rate)
        st.rerun()