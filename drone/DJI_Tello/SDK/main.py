from time import sleep
from RestrictedTelloSDK import RestrictedTelloSDK, TelloSDK

# Basic usage
tello = TelloSDK()

print("Connecting to Drone...")

# Connect to drone
if tello.connect():
    print("Connected successfully!")

    sleep(5)  # Wait for connection to stabilize
    
    # Takeoff
    result = tello.takeoff()
    print(f"Takeoff result: {result}")
    
    # # Move forward
    # result = tello.forward(50)
    # print(f"Forward result: {result}")
    
    # Get battery level
    battery = tello.get_battery()
    print(f"Battery level: {battery}%")
    
    sleep(10)  # Wait for connection to stabilize

    # Land
    result = tello.land()
    print(f"Land result: {result}")

# Update restrictions for hackathon
# new_restrictions = {
#     "max_speed": 50,
#     "command_limit_per_second": 5,
#     "allowed_commands": ["takeoff", "land", "forward", "back", "left", "right"],
#     "emergency_stop_allowed": False
# }

# tello.update_restrictions(new_restrictions)