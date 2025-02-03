import struct
import requests
import collections
import socket
import subprocess
import time
import threading
import serial


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


def get_controller_server_info():
    CONNECTION_SERVICE_IP = "3.215.138.208"
    CONNECTION_SERVICE_PORT = 4337

    client_local_ip = socket.gethostbyname(socket.gethostname())
    client_public_ip = requests.get("https://api.ipify.org").text

    print(f"Client Local IP: {client_local_ip}")
    print(f"Client Public IP: {client_public_ip}")

    # Send a request to the connection service
    response = requests.post(
        f"http://{CONNECTION_SERVICE_IP}:{CONNECTION_SERVICE_PORT}/client",
        json={
            "client_local_ip": client_local_ip,
            "client_public_ip": client_public_ip,
        },
    )
    if response.status_code == 200:
        """
        Response looks like this:
        {
          "server_ip": "192.168.0.10",
          "server_port": "8080",
          "stored_at": "2024-12-14T12:34:56.789Z"
        }
        """
        return response.json()
    else:
        print("Failed to get controller server info")
        return None


class ControllerServerConnectionRefusedError(Exception):
    # Store ip and port
    def __init__(self, ip, port):
        super().__init__(f"Connection refused by server at {ip}:{port}")
        self.ip = ip
        self.port = port


def run_headset_orientation_client():
    time_buffer_size = 20

    # dequeue for time buffer
    time_buffer = collections.deque(maxlen=time_buffer_size)

    time_buffer_print_interval = 60
    time_buffer_print_index = 0

    server_connection_data = get_controller_server_info()

    if server_connection_data is None:
        print("Failed to get controller server info")
        return

    HOST = server_connection_data["server_ip"]
    PORT = int(server_connection_data["server_port"])

    # Create a socket connection to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # HOST = "0.0.0.0"  # Listen on all interfaces
        # PORT = 12345  # Port to listen on
        try:
            s.connect((HOST, PORT))
        except ConnectionRefusedError:
            raise ControllerServerConnectionRefusedError(HOST, PORT)
        print(f"Server connected to {HOST}:{PORT}")
        while True:
            data = recv_all(s, 16)
            if not data:
                break

            time_buffer.append(time.time())
            if len(time_buffer) == time_buffer_size:
                time_buffer.popleft()
                time_buffer_print_index += 1
                if time_buffer_print_index % time_buffer_print_interval == 0:
                    time_diff = time_buffer[-1] - time_buffer[0]
                    print(f"cam data {time_buffer_size / time_diff} Hz")

            try:
                pitch, yaw, throttle, steering = struct.unpack("<ffff", data)
            except ValueError:
                print("Invalid data format: must be float")
                continue
            send_command_to_arduino(-pitch, -yaw, throttle, steering)
            if time_buffer_print_index % time_buffer_print_interval == 0:
                print(
                    f"pitch: {pitch}, yaw: {yaw}, throttle: {throttle}, steering: {steering}"
                )


def validate_and_send_command_to_arduino(message):
    try:
        pitch, yaw = message.strip().split(" ")
        pitch = int(pitch)
        yaw = int(yaw)
    except:
        print("wrong format")
        return
    send_command_to_arduino(pitch, yaw, 0, 0)


def send_command_to_arduino(pitch, yaw, throttle, steering):
    # 0xDEADBEEF as a header
    ready_to_send_bytes = struct.pack(
        "<Iffff", 0xDEADBEEF, pitch, yaw, throttle, steering
    )

    # Send the packet
    ser.write(ready_to_send_bytes)

    # print(f"Sent pitch: {pitch} yaw {yaw}")
    # print(f"Sent: {pitch_bytes} {yaw_bytes}")


# Create a thread that listens for data from the Arduino
def read_from_arduino():
    while True:
        data = ser.readline().decode("utf-8").strip()
        if data:
            pass
            # print(f"Received: {data}")


try:
    # Start the thread that listens for data from the Arduino
    read_thread = threading.Thread(target=read_from_arduino)
    read_thread.start()

    while True:
        failure_delay = 4
        try:
            run_headset_orientation_client()
        # In the case of failed connection
        except ControllerServerConnectionRefusedError as e:
            print(f"Connection refused by server at {e.ip}:{e.port}")
            time.sleep(failure_delay)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(failure_delay)

except KeyboardInterrupt:
    print("Program stopped.")
finally:
    ser.close()  # Close the serial port when done
