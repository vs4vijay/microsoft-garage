import socket
import time
import threading
from typing import Optional, Tuple, List, Callable
import json
import cv2
import numpy as np
from queue import Queue
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GarageDrone:
    def __init__(self, ip: str = "192.168.10.1", port: int = 8889):
        """
        Initialize Tello SDK with video streaming support
        """
        self.ip = ip
        self.port = port
        self.command_port = 8889
        self.video_port = 11000
        self.socket = None
        self.video_socket = None
        self.is_connected = False
        self.is_video_streaming = False
        
        # Video streaming attributes
        self.video_queue = Queue(maxsize=10)
        self.video_thread = None
        self.video_callback = None
        self.frame_count = 0
        
        # Command response handling
        self.response_timeout = 5.0
        self.last_response_time = 0
        
    def connect(self) -> bool:
        """Establish connection to Tello drone"""
        try:
            # Create command socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.command_port))
            
            # Send initial command to test connection
            self.send_command("command")
            response = self.receive_response()
            
            if response and "ok" in response.lower():
                self.is_connected = True
                logger.info("Successfully connected to Tello drone")
                return True
            else:
                logger.error("Failed to connect to Tello drone")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Tello drone"""
        if self.is_connected:
            try:
                self.send_command("land")
                self.socket.close()
                if self.video_thread and self.video_thread.is_alive():
                    self.stop_video_streaming()
                self.is_connected = False
                logger.info("Disconnected from Tello drone")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def send_command(self, command: str) -> bool:
        """Send command to Tello drone"""
        if command is not "command" and not self.is_connected:
            logger.warning("Not connected to drone")
            return False
            
        try:
            self.socket.sendto(command.encode('utf-8'), (self.ip, self.port))
            self.last_response_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return False
    
    def receive_response(self, timeout: float = None) -> Optional[str]:
        """Receive response from Tello drone"""
        if not self.socket:
            return None
            
        try:
            if timeout is None:
                timeout = self.response_timeout
                
            self.socket.settimeout(timeout)
            data, addr = self.socket.recvfrom(1024)
            response = data.decode('utf-8')
            return response
        except socket.timeout:
            logger.warning("Command response timeout")
            return "timeout"
        except Exception as e:
            logger.error(f"Error receiving response: {e}")
            return None
    
    def start_video_streaming(self, callback: Callable[[np.ndarray], None] = None):
        """Start video streaming from Tello drone"""
        if not self.is_connected:
            logger.error("Cannot start video streaming: Not connected to drone")
            return False
            
        try:
            # Send command to start video streaming
            self.send_command("streamon")
            response = self.receive_response()
            
            if not response or "ok" not in response.lower():
                logger.error("Failed to start video streaming")
                return False
            
            # Create video socket
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_socket.bind(('', self.video_port))
            self.video_socket.settimeout(1.0)
            
            # Set callback function for video frames
            self.video_callback = callback
            self.is_video_streaming = True
            
            # Start video processing thread
            self.video_thread = threading.Thread(target=self._video_processing_loop)
            self.video_thread.daemon = True
            self.video_thread.start()
            
            logger.info("Video streaming started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting video streaming: {e}")
            self.is_video_streaming = False
            return False
    
    def stop_video_streaming(self):
        """Stop video streaming from Tello drone"""
        try:
            if self.is_video_streaming:
                self.send_command("streamoff")
                self.is_video_streaming = False
                
                # Close video socket
                if self.video_socket:
                    self.video_socket.close()
                
                # Wait for thread to finish
                if self.video_thread and self.video_thread.is_alive():
                    self.video_thread.join(timeout=2.0)
                
                logger.info("Video streaming stopped")
        except Exception as e:
            logger.error(f"Error stopping video streaming: {e}")
    
    def _video_processing_loop(self):
        """Internal method to process video frames"""
        try:
            while self.is_video_streaming:
                try:
                    data, addr = self.video_socket.recvfrom(2048)
                    
                    # Convert data to numpy array
                    frame_data = np.frombuffer(data, dtype=np.uint8)
                    
                    # Decode frame using OpenCV
                    frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        self.frame_count += 1
                        
                        # Add frame to queue for processing
                        try:
                            self.video_queue.put_nowait(frame)
                        except:
                            # Queue full, remove oldest frame
                            try:
                                self.video_queue.get_nowait()
                                self.video_queue.put_nowait(frame)
                            except:
                                pass
                        
                        # Call callback if provided
                        if self.video_callback:
                            try:
                                self.video_callback(frame)
                            except Exception as e:
                                logger.error(f"Error in video callback: {e}")
                                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_video_streaming:
                        logger.error(f"Video processing error: {e}")
                        
        except Exception as e:
            logger.error(f"Video thread error: {e}")

    # Movement Commands
    def takeoff(self) -> str:
        """Takeoff drone"""
        self.send_command("takeoff")
        return self.receive_response()
    
    def land(self) -> str:
        """Land drone"""
        self.send_command("land")
        return self.receive_response()
    
    def move_forward(self, distance: int) -> str:
        """Move forward (20-500 cm)"""
        if not 20 <= distance <= 500:
            raise ValueError("Distance must be between 20 and 500 cm")
        self.send_command(f"forward {distance}")
        return self.receive_response()
    
    def move_back(self, distance: int) -> str:
        """Move backward (20-500 cm)"""
        if not 20 <= distance <= 500:
            raise ValueError("Distance must be between 20 and 500 cm")
        self.send_command(f"back {distance}")
        return self.receive_response()
    
    def move_left(self, distance: int) -> str:
        """Move left (20-500 cm)"""
        if not 20 <= distance <= 500:
            raise ValueError("Distance must be between 20 and 500 cm")
        self.send_command(f"left {distance}")
        return self.receive_response()
    
    def move_right(self, distance: int) -> str:
        """Move right (20-500 cm)"""
        if not 20 <= distance <= 500:
            raise ValueError("Distance must be between 20 and 500 cm")
        self.send_command(f"right {distance}")
        return self.receive_response()
    
    def move_up(self, distance: int) -> str:
        """Move up (20-50 cm)"""
        if not 20 <= distance <= 50:
            raise ValueError("Distance must be between 20 and 50 cm")
        self.send_command(f"up {distance}")
        return self.receive_response()
    
    def move_down(self, distance: int) -> str:
        """Move down (20-50 cm)"""
        if not 20 <= distance <= 50:
            raise ValueError("Distance must be between 20 and 50 cm")
        self.send_command(f"down {distance}")
        return self.receive_response()
    
    def rotate_left(self, degrees: int) -> str:
        """Rotate left (1-360 degrees)"""
        if not 1 <= degrees <= 360:
            raise ValueError("Degrees must be between 1 and 360")
        self.send_command(f"ccw {degrees}")
        return self.receive_response()
    
    def rotate_right(self, degrees: int) -> str:
        """Rotate right (1-360 degrees)"""
        if not 1 <= degrees <= 360:
            raise ValueError("Degrees must be between 1 and 360")
        self.send_command(f"cw {degrees}")
        return self.receive_response()
    
    def flip(self, direction: str) -> str:
        """Perform a flip in specified direction"""
        valid_directions = ['f', 'b', 'l', 'r']
        if direction not in valid_directions:
            raise ValueError("Direction must be one of: f, b, l, r")
        self.send_command(f"flip {direction}")
        return self.receive_response()
    
    def set_speed(self, speed: int) -> str:
        """Set flight speed (10-100 cm/s)"""
        if not 10 <= speed <= 100:
            raise ValueError("Speed must be between 10 and 100 cm/s")
        self.send_command(f"speed {speed}")
        return self.receive_response()
    
    # Sensor Data Commands
    def get_battery(self) -> int:
        """Get battery percentage"""
        self.send_command("battery?")
        response = self.receive_response()
        try:
            return int(response)
        except:
            return 0
    
    def get_height(self) -> int:
        """Get current height"""
        self.send_command("height?")
        response = self.receive_response()
        try:
            return int(response)
        except:
            return 0
    
    def get_speed(self) -> int:
        """Get current speed"""
        self.send_command("speed?")
        response = self.receive_response()
        try:
            return int(response)
        except:
            return 0
    
    def get_temperature(self) -> str:
        """Get temperature"""
        self.send_command("temp?")
        return self.receive_response()
    
    def get_time(self) -> str:
        """Get flight time"""
        self.send_command("time?")
        return self.receive_response()
    
    def get_wifi_signal(self) -> str:
        """Get WiFi signal strength"""
        self.send_command("wifi?")
        return self.receive_response()
    
    # Status Commands
    def emergency_stop(self):
        """Emergency stop - immediately land drone"""
        self.send_command("emergency")
        return self.receive_response()

# Restructured version for better integration with existing code
class TelloDrone:
    """Wrapper class for Tello drone operations with video streaming support"""
    
    def __init__(self):
        self.drone = GarageDrone()
        
    def connect(self) -> bool:
        """Connect to drone"""
        return self.drone.connect()
    
    def disconnect(self):
        """Disconnect from drone"""
        self.drone.disconnect()
    
    def start_video_streaming(self, callback: Callable[[np.ndarray], None] = None):
        """Start video streaming"""
        return self.drone.start_video_streaming(callback)
    
    def stop_video_streaming(self):
        """Stop video streaming"""
        self.drone.stop_video_streaming()
    
    def takeoff(self) -> str:
        """Takeoff drone"""
        return self.drone.takeoff()
    
    def land(self) -> str:
        """Land drone"""
        return self.drone.land()
    
    def get_battery(self) -> int:
        """Get battery percentage"""
        return self.drone.get_battery()
    
    def get_height(self) -> int:
        """Get current height"""
        return self.drone.get_height()
    
    def set_speed(self, speed: int) -> str:
        """Set flight speed"""
        return self.drone.set_speed(speed)
    
    # Add more methods as needed...

# Example usage function
def example_usage():
    """Example of how to use the Tello drone with video streaming"""
    
    # Create drone instance
    drone = TelloDrone()
    
    try:
        # Connect to drone
        if not drone.connect():
            print("Failed to connect to drone")
            return
        
        print("Connected to drone!")
        
        # Start video streaming
        def process_frame(frame):
            """Process incoming video frames"""
            # Example: Display frame using OpenCV
            cv2.imshow('Tello Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                drone.stop_video_streaming()
                cv2.destroyAllWindows()
        
        drone.start_video_streaming(process_frame)
        
        # Takeoff and perform some actions
        drone.takeoff()
        print(f"Battery: {drone.get_battery()}%")
        
        # Move around
        drone.set_speed(50)
        drone.move_forward(100)
        drone.rotate_right(90)
        drone.move_up(50)
        
        # Land
        drone.land()
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Cleanup
        drone.stop_video_streaming()
        drone.disconnect()

if __name__ == "__main__":
    # Example usage - uncomment to run
    # example_usage()
    pass

# Additional helper functions for video processing
def save_frame(frame, filename):
    """Save frame to file"""
    try:
        cv2.imwrite(filename, frame)
        print(f"Frame saved as {filename}")
    except Exception as e:
        print(f"Error saving frame: {e}")

def display_frame(frame):
    """Display frame in window"""
    try:
        cv2.imshow('Tello Frame', frame)
        cv2.waitKey(1)
    except Exception as e:
        print(f"Error displaying frame: {e}")

# Simple test function
def test_video_streaming():
    """Simple test for video streaming"""
    drone = TelloDrone()
    
    try:
        if drone.connect():
            print("Starting video streaming...")
            
            def simple_callback(frame):
                # Simple callback that just displays frames
                cv2.imshow('Tello Stream', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    drone.stop_video_streaming()
                    cv2.destroyAllWindows()
            
            drone.start_video_streaming(simple_callback)
            
            # Let it run for a few seconds
            import time
            time.sleep(5)
            
            drone.stop_video_streaming()
            drone.disconnect()
            
    except Exception as e:
        print(f"Test error: {e}")
    
    finally:
        cv2.destroyAllWindows()

# For testing purposes, you can uncomment the following line to run a quick test:
# test_video_streaming()  # Uncomment this to run the test

# Note: Make sure to install required dependencies:
# pip install opencv-python numpy