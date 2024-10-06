import time
import json
import serial

from pynput import keyboard


arduino_port = "/dev/cu.usbmodem2101"
baud_rate = 9600


# Open the serial connection to the Arduino
ser = serial.Serial(arduino_port, baud_rate)
time.sleep(2)  # Give some time for the connection to establish


def validate_and_send_command_to_arduino(message):
    try:
        pitch, yaw = message.strip().split(" ")
        pitch = int(pitch)
        yaw = int(yaw)
    except:
        print("wrong format")
        return
    send_command_to_arduino(pitch, yaw)


def send_command_to_arduino(pitch, yaw):
    # Encode these as two bytes each
    pitch_bytes = pitch.to_bytes(4, byteorder="big", signed=True)
    yaw_bytes = yaw.to_bytes(4, byteorder="big", signed=True)
    ser.write(pitch_bytes)
    ser.write(yaw_bytes)
    print(f"Sent: {pitch_bytes} {yaw_bytes}")


# A set to store currently pressed keys
pressed_keys = set()


# Callback function for key press
def on_press(key):
    try:
        pressed_keys.add(key.char)  # Add the key to the set if it's a character
    except AttributeError:
        pressed_keys.add(key)  # Add special keys (like space, ctrl, etc.)


# Callback function for key release
def on_release(key):
    try:
        pressed_keys.discard(key.char)  # Remove the key from the set
    except AttributeError:
        pressed_keys.discard(key)  # Handle special keys (like space, ctrl, etc.)


# Start listening for key press and release events
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# Desired loop rate
frame_rate = 60
frame_time = 1 / frame_rate

g_pitch = 0
g_yaw = 0

# Continuously wait for a key press to send data
try:
    print('Calibrate the robot by sending pitch and yaw. Then enter "next".')
    while True:
        command = input("Enter two integers for pitch and yaw respectively:\n")
        if command == "next":
            print("entered live mode")
            break
        validate_and_send_command_to_arduino(command)
    while True:
        pitch_delta = 5
        yaw_delta = 5

        # Print the keys that are currently being held down
        if pressed_keys:
            adjusted_pitch_delta = pitch_delta
            adjusted_yaw_delta = yaw_delta

            if keyboard.Key.shift in pressed_keys:
                shift_adjustment = 0.2
                adjusted_pitch_delta *= shift_adjustment
                adjusted_yaw_delta *= shift_adjustment

            if keyboard.Key.down in pressed_keys:
                g_pitch += adjusted_pitch_delta
            if keyboard.Key.up in pressed_keys:
                g_pitch -= adjusted_pitch_delta
            if keyboard.Key.right in pressed_keys:
                g_yaw -= adjusted_yaw_delta
            if keyboard.Key.left in pressed_keys:
                g_yaw += adjusted_yaw_delta

            g_pitch = int(g_pitch)
            g_yaw = int(g_yaw)

            print(f"pitch {g_pitch} yaw {g_yaw}")
            send_command_to_arduino(g_pitch, g_yaw)

        # Wait for the next frame
        time.sleep(frame_time)
except KeyboardInterrupt:
    print("Program stopped.")
    listener.stop()
finally:
    ser.close()  # Close the serial port when done
