import socket
import json
import struct
import time
import collections
import requests


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

    timeout_failure_window = [False] * 1000
    timeout_failure_window_index = 0

    time_lag_ms_window = [0] * 1000
    time_lag_ms_window_index = 0

    # server_connection_data = get_controller_server_info()
    server_connection_data = get_controller_server_info()

    if server_connection_data is None:
        print("Failed to get controller server info")
        return

    print(
        f"Connecting to server at {server_connection_data['server_ip']}:{server_connection_data['server_port']}"
    )

    HOST = server_connection_data["server_ip"]
    PORT = int(server_connection_data["server_port"])
    HOST = 'localhost'

    # Create a socket connection to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)  # Set a timeout for the connection attempt
    with sock as s:
        try:
            s.connect((HOST, PORT))
        except socket.timeout:
            print("Socket timed out")
            raise ControllerServerConnectionRefusedError(HOST, PORT)
        except ConnectionRefusedError:
            raise ControllerServerConnectionRefusedError(HOST, PORT)
        print(f"Server connected to {HOST}:{PORT}")
        while True:
            data = recv_all(s, 24)
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
                timestamp_ms, pitch, yaw, throttle, steering = struct.unpack(
                    "<Qffff",  # < means little-endian. Q means unsigned long long (8 bytes), f means float (4 bytes)
                    data,
                )
            except ValueError:
                print("Invalid data format from control server")
                continue
            except Exception:
                print("other exception")
                continue

            if all(x == 0 for x in [timestamp_ms, pitch, yaw, throttle, steering]):
                # this is a time offset measurement
                t2 = int(time.time() * 1000)
                t3 = int(time.time() * 1000)
                data = json.dumps({"t2": t2, "t3": t3}).encode("utf-8")
                s.sendall(data)
                continue

            # Intermittently show the data for sanity check
            if time_buffer_print_index % time_buffer_print_interval == 0:
                print(
                    f"pitch: {pitch}, yaw: {yaw}, throttle: {throttle}, steering: {steering}, timeout failure percentage: {(sum(timeout_failure_window) / len(timeout_failure_window)) * 100:.1f}%"
                )

            failure_threshold = min(time_lag_ms_window) + 500

            time_lag_ms = (time.time() * 1000) - timestamp_ms

            # Check if timestamp is too old
            timeout_failure = time_lag_ms > failure_threshold

            if time_buffer_print_index % 3 == 0:
                print("time lag", int(time_lag_ms), "ms")

            timeout_failure_window[
                timeout_failure_window_index % len(timeout_failure_window)
            ] = timeout_failure
            timeout_failure_window_index += 1

            time_lag_ms_window[time_lag_ms_window_index % len(time_lag_ms_window)] = (
                time_lag_ms
            )
            time_lag_ms_window_index += 1

            # Throw out stale packets
            if timeout_failure:
                continue


run_headset_orientation_client()
