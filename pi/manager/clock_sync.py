import socket
import struct
import time

from manager.constants import CLOCK_SYNC_PORT

from .utils import recv_all
from .exceptions import ControllerServerConnectionRefusedError
from .headset_location import get_headset_location


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
    PORT = CLOCK_SYNC_PORT

    # Create a socket connection to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)  # Set a timeout for the connection attempt

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
                data = recv_all(s, 1)
                if not data:
                    break

                # this is a time offset measurement
                s.sendall(struct.pack("<Q", int(time.time() * 1000)))
                print("sent time offset measurement")
                clock_sync_packet_count += 1
                continue
    except (TimeoutError, ConnectionError):
        print("Socket timed out")
        return clock_sync_packet_count
    except Exception as e:
        raise e
