import socket
import time
import threading
from typing import Optional, Tuple, List
import json

class TelloSDK:
    def __init__(self, ip: str = "192.168.10.1", port: int = 8889):
        """
        Initialize Tello SDK connection
        """
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", 8889))
        self.is_connected = False
        self.response_timeout = 10  # seconds
        
    def connect(self) -> bool:
        """
        Establish connection to Tello drone
        """
        try:
            print('---')
            # Send a test command to verify connection
            response = self.send_command("command")
            print('---response', response)
            if "ok" in response.lower() or "OK" in response:
                self.is_connected = True
                return True
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_command(self, command: str) -> str:
        """
        Send command to Tello and receive response
        """
        # if command != "command" and not self.is_connected:
        #     raise Exception("Not connected to Tello")
            
        try:
            self.socket.sendto(command.encode(), (self.ip, self.port))
            response, _ = self.socket.recvfrom(1024)
            return response.decode()
        except socket.timeout:
            return "timeout"
        except Exception as e:
            return f"error: {str(e)}"
    
    def takeoff(self) -> str:
        """Initiate takeoff"""
        return self.send_command("takeoff")
    
    def land(self) -> str:
        """Initiate landing"""
        return self.send_command("land")
    
    def emergency_stop(self) -> str:
        """Emergency stop - immediately stops all motors"""
        return self.send_command("emergency")
    
    def forward(self, distance: int) -> str:
        """Move forward (10-100 cm)"""
        if not 10 <= distance <= 100:
            raise ValueError("Distance must be between 10 and 100 cm")
        return self.send_command(f"forward {distance}")
    
    def back(self, distance: int) -> str:
        """Move backward (10-100 cm)"""
        if not 10 <= distance <= 100:
            raise ValueError("Distance must be between 10 and 100 cm")
        return self.send_command(f"back {distance}")
    
    def left(self, distance: int) -> str:
        """Move left (10-100 cm)"""
        if not 10 <= distance <= 100:
            raise ValueError("Distance must be between 10 and 100 cm")
        return self.send_command(f"left {distance}")
    
    def right(self, distance: int) -> str:
        """Move right (10-100 cm)"""
        if not 10 <= distance <= 100:
            raise ValueError("Distance must be between 10 and 100 cm")
        return self.send_command(f"right {distance}")
    
    def up(self, distance: int) -> str:
        """Move up (20-50 cm)"""
        if not 20 <= distance <= 50:
            raise ValueError("Distance must be between 20 and 50 cm")
        return self.send_command(f"up {distance}")
    
    def down(self, distance: int) -> str:
        """Move down (20-50 cm)"""
        if not 20 <= distance <= 50:
            raise ValueError("Distance must be between 20 and 50 cm")
        return self.send_command(f"down {distance}")
    
    def rotate_left(self, degrees: int) -> str:
        """Rotate left (1-360 degrees)"""
        if not 1 <= degrees <= 360:
            raise ValueError("Degrees must be between 1 and 360")
        return self.send_command(f"ccw {degrees}")
    
    def rotate_right(self, degrees: int) -> str:
        """Rotate right (1-360 degrees)"""
        if not 1 <= degrees <= 360:
            raise ValueError("Degrees must be between 1 and 360")
        return self.send_command(f"cw {degrees}")
    
    def flip(self, direction: str) -> str:
        """Perform a flip in specified direction"""
        valid_directions = ['f', 'b', 'l', 'r']
        if direction not in valid_directions:
            raise ValueError("Direction must be one of: f, b, l, r")
        return self.send_command(f"flip {direction}")
    
    def set_speed(self, speed: int) -> str:
        """Set flight speed (10-100 cm/s)"""
        if not 10 <= speed <= 100:
            raise ValueError("Speed must be between 10 and 100 cm/s")
        return self.send_command(f"speed {speed}")
    
    def get_battery(self) -> int:
        """Get battery percentage"""
        response = self.send_command("battery?")
        try:
            return int(response)
        except:
            return -1
    
    def get_height(self) -> int:
        """Get current height in cm"""
        response = self.send_command("height?")
        try:
            return int(response)
        except:
            return -1
    
    def get_speed(self) -> int:
        """Get current speed in cm/s"""
        response = self.send_command("speed?")
        try:
            return int(response)
        except:
            return -1
    
    def get_temperature(self) -> Tuple[int, int]:
        """Get temperature (min, max)"""
        response = self.send_command("temp?")
        try:
            # Response format: "min max"
            temp_values = response.split()
            return (int(temp_values[0]), int(temp_values[1]))
        except:
            return (-1, -1)
    
    def get_wifi_signal(self) -> str:
        """Get WiFi signal strength"""
        response = self.send_command("wifi?")
        return response
    
    def get_time(self) -> str:
        """Get current flight time"""
        response = self.send_command("time?")
        return response

# Restriction Manager for Hackathon Organizers
class RestrictionManager:
    def __init__(self):
        self.restrictions = {
            "max_speed": 100,
            "max_distance": 500,
            "command_limit_per_second": 10,
            "allowed_commands": [
                "takeoff", "land", "forward", "back", "left", "right",
                "up", "down", "ccw", "cw", "flip", "speed", "battery?",
                "height?", "speed?", "temp?", "wifi?", "time?"
            ],
            "emergency_stop_allowed": False,
            "max_flight_time": 30,  # seconds
            "allowed_flight_area": {
                "x_min": -100,
                "x_max": 100,
                "y_min": -100,
                "y_max": 100,
                "z_min": 0,
                "z_max": 50
            }
        }
        self.command_count = 0
        self.last_reset_time = time.time()
    
    def is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed based on restrictions"""
        return command in self.restrictions["allowed_commands"]
    
    def check_speed_limit(self, speed: int) -> bool:
        """Check if speed exceeds maximum limit"""
        return speed <= self.restrictions["max_speed"]
    
    def check_distance_limit(self, distance: int) -> bool:
        """Check if distance exceeds maximum limit"""
        return distance <= self.restrictions["max_distance"]
    
    def check_command_rate(self) -> bool:
        """Check if command rate is within limits"""
        current_time = time.time()
        if current_time - self.last_reset_time > 1:
            self.command_count = 0
            self.last_reset_time = current_time
        
        if self.command_count >= self.restrictions["command_limit_per_second"]:
            return False
        
        self.command_count += 1
        return True
    
    def update_restrictions(self, new_restrictions: dict):
        """Update restriction settings"""
        self.restrictions.update(new_restrictions)
    
    def get_current_restrictions(self) -> dict:
        """Get current restrictions"""
        return self.restrictions.copy()

# Enhanced Tello SDK with Restrictions
class RestrictedTelloSDK(TelloSDK):
    def __init__(self, ip: str = "192.168.10.1", port: int = 8889):
        super().__init__(ip, port)
        self.restrictions = RestrictionManager()
    
    def send_command(self, command: str) -> str:
        """Send command with restriction checking"""
        # Check if command is allowed
        if not self.restrictions.is_command_allowed(command):
            return "error: command not allowed"
        
        # Check rate limiting
        if not self.restrictions.check_command_rate():
            return "error: command rate limit exceeded"
        
        # For specific commands, check parameters
        if command.startswith("speed"):
            try:
                speed = int(command.split()[1])
                if not self.restrictions.check_speed_limit(speed):
                    return "error: speed exceeds maximum limit"
            except:
                pass
        elif command.startswith("forward") or command.startswith("back") or \
             command.startswith("left") or command.startswith("right") or \
             command.startswith("up") or command.startswith("down"):
            try:
                distance = int(command.split()[1])
                if not self.restrictions.check_distance_limit(distance):
                    return "error: distance exceeds maximum limit"
            except:
                pass
        
        # Execute the command
        return super().send_command(command)
    
    def emergency_stop(self) -> str:
        """Emergency stop with restriction check"""
        if not self.restrictions.restrictions["emergency_stop_allowed"]:
            return "error: emergency stop not allowed"
        return super().emergency_stop()
    
    def update_restrictions(self, new_restrictions: dict):
        """Update restrictions"""
        self.restrictions.update_restrictions(new_restrictions)