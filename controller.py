import struct
import collections
import socket
import subprocess
import time
import threading
import serial

from pynput import keyboard


# Run the bash command as a single subprocess
arduino_port = subprocess.run(
    ["bash", "-c", "arduino-cli board list | grep 'Nano Every' | awk '{print $1}'"],
    capture_output=True,
    text=True,
).stdout.strip()

print(f"Arduino Port: {arduino_port}")
baud_rate = 115200


# Open the serial connection to the Arduino
ser = serial.Serial(arduino_port, baud_rate)
time.sleep(1)  # Give some time for the connection to establish


def recv_all(sock, length):
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Socket connection closed")
        data += more
    return data


def run_headset_orientation_server():
    time_buffer_size = 20

    # dequeue for time buffer
    time_buffer = collections.deque(maxlen=time_buffer_size)

    time_buffer_print_interval = 60
    time_buffer_print_index = 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        HOST = "0.0.0.0"  # Listen on all interfaces
        PORT = 12345  # Port to listen on
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                # data = conn.recv(8)
                data = recv_all(conn, 8)
                if not data:
                    break
                # str_data = data.decode()

                time_buffer.append(time.time())
                if len(time_buffer) == time_buffer_size:
                    time_buffer.popleft()
                    time_buffer_print_index += 1
                    if time_buffer_print_index % time_buffer_print_interval == 0:
                        time_diff = time_buffer[-1] - time_buffer[0]
                        print(f"cam data {time_buffer_size / time_diff} Hz")

                # # There must be two commas in the string to be valid
                # if str_data.count(",") != 2:
                #     print(f"Invalid data format: must have 2 commas; {str_data}")
                #     continue
                # pitch, yaw, roll = str_data.split(",")
                # print("pitch", pitch)
                # print("yaw", yaw)
                try:
                    pitch, yaw = struct.unpack("<ff", data)
                    # pitch = float(pitch)
                    # yaw = float(yaw)
                except ValueError:
                    print("Invalid data format: must be float")
                    continue
                send_command_to_arduino(-pitch, -yaw)


def validate_and_send_command_to_arduino(message):
    try:
        pitch, yaw = message.strip().split(" ")
        pitch = int(pitch)
        yaw = int(yaw)
    except:
        print("wrong format")
        return
    send_command_to_arduino(pitch, yaw)


last_sent_pitch = 0
last_sent_yaw = 0


def send_command_to_arduino(pitch, yaw):
    # Only send the command if it's different from the last one
    global last_sent_pitch
    global last_sent_yaw
    if pitch == last_sent_pitch and yaw == last_sent_yaw:
        return
    last_sent_pitch = pitch
    last_sent_yaw = yaw

    # 0xDEADBEEF as a header
    ready_to_send_bytes = struct.pack("<Iff", 0xDEADBEEF, pitch, yaw)

    # Send the packet
    ser.write(ready_to_send_bytes)

    # print(f"Sent pitch: {pitch} yaw {yaw}")
    # print(f"Sent: {pitch_bytes} {yaw_bytes}")


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
frame_rate = 200
frame_time = 1 / frame_rate

g_pitch = 0
g_yaw = 0


# Create a thread that listens for data from the Arduino
def read_from_arduino():
    while True:
        data = ser.readline().decode("utf-8").strip()
        if data:
            print(f"Received: {data}")


# Continuously wait for a key press to send data
try:
    # Start the thread that listens for data from the Arduino
    read_thread = threading.Thread(target=read_from_arduino)
    read_thread.start()

    print('Calibrate the robot by sending pitch and yaw. Then enter "next".')
    while True:
        command = input("Enter two integers for pitch and yaw respectively:\n")

        # headset
        if command == "h":
            while True:
                try:
                    run_headset_orientation_server()
                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(2)

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

            send_command_to_arduino(g_pitch, g_yaw)

        # Wait for the next frame
        time.sleep(frame_time)
except KeyboardInterrupt:
    print("Program stopped.")
    listener.stop()
finally:
    ser.close()  # Close the serial port when done
