import collections
import socket
import struct
import time

from manager.headset_location import get_headset_location
from manager.exceptions import ControllerServerConnectionRefusedError


def recv_all(sock, length):
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Socket connection closed")
        data += more
    return data


def start_clock_sync_client():
    clock_sync_packet_count = 0

    headset_location = get_headset_location()

    if headset_location is None:
        print("Failed to get headset server info")
        return

    print(
        f"Connecting to headset at {headset_location['server_ip']}:{headset_location['server_port']}"
    )

    HOST = headset_location["server_ip"]
    PORT = int(headset_location["server_port"])

    # HOST = "192.168.0.20"

    # Create a socket connection to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)  # Set a timeout for the connection attempt

    try:
        with sock as s:
            try:
                s.connect((HOST, PORT))
            except socket.timeout:
                print("Socket timed out")
                raise ControllerServerConnectionRefusedError(HOST, PORT)
            except ConnectionRefusedError:
                raise ControllerServerConnectionRefusedError(HOST, PORT)
            print(f"connected to headset at {HOST}:{PORT}")

            while True:
                data = recv_all(s, 24)
                if not data:
                    break

                if all(x == 0 for x in [timestamp_ms, pitch, yaw, throttle, steering]):
                    # this is a time offset measurement
                    s.sendall(struct.pack("<Qff", int(time.time() * 1000), 0, 0))
                    print("sent time offset measurement")
                    clock_sync_packet_count += 1
                    continue
    except ConnectionError:
        print("Connection closed by server")
        return clock_sync_packet_count
    except Exception as e:
        raise e
