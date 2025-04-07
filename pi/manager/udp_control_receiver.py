import select
import socket
import struct
import time

from manager.constants import CONTROL_STREAM_PORT

from .arduino_communication import (get_arduino_serial_interface,
                                    send_command_to_arduino)
from .headset_location import get_headset_location

# UDP settings
LOCAL_IP = "0.0.0.0"  # Bind to all interfaces
LOCAL_PORT = 12345  # Local port for receiving


# Keepalive settings
KEEPALIVE_INTERVAL = 15  # Seconds between keepalive packets
KEEPALIVE_MESSAGE = b"PING"  # Simple keepalive message

# Packet structure settings
SEQ_SIZE = 4  # 4 bytes for sequence number (big-endian unsigned int)
CHECKSUM_SIZE = 2  # 2 bytes for checksum (16-bit)
TIMESTAMP_SIZE = 8  # 8 bytes for timestamp (big-endian unsigned long long)
HEADER_SIZE = sum(
    [
        SEQ_SIZE,
        CHECKSUM_SIZE,
        TIMESTAMP_SIZE,
    ]
)


def calculate_checksum(data: bytes) -> int:
    """Calculate a 16-bit checksum by summing the bytes of the payload."""
    return sum(data) & 0xFFFF  # Mask to 16 bits


def send_keepalive(sock: socket.socket, addr: tuple[str, int]):
    """Send a keepalive packet to maintain the NAT mapping."""
    _ = sock.sendto(KEEPALIVE_MESSAGE, addr)
    print(f"Sent keepalive to {addr[0]}:{addr[1]}")


def start_udp_control_receiver(mac_test_environment: bool = False):
    headset_location = get_headset_location()
    if headset_location is None:
        print("Failed to get headset server info in udp_control_receiver.py")
        return

    REMOTE_IP = headset_location["server_ip"]
    REMOTE_PORT = CONTROL_STREAM_PORT

    if not mac_test_environment:
        arduino_serial_interface = get_arduino_serial_interface()
    else:
        pass
        # REMOTE_IP = "127.0.0.1"
    arduino_sequence_number = 0

    # Create and configure the UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOCAL_IP, LOCAL_PORT))
    sock.setblocking(False)  # Set to non-blocking mode

    # Send an initial keepalive to establish the NAT mapping
    send_keepalive(sock, (REMOTE_IP, REMOTE_PORT))
    last_keepalive_time = time.time()

    # Variables to track the latest packet
    latest_seq = -1  # Latest sequence number received
    latest_packet = None  # Latest valid payload

    print(f"Listening for UDP packets on {LOCAL_IP}:{LOCAL_PORT}...")
    while True:
        current_time = time.time()

        # Send keepalive if the interval has elapsed
        if current_time - last_keepalive_time >= KEEPALIVE_INTERVAL:
            send_keepalive(sock, (REMOTE_IP, REMOTE_PORT))
            last_keepalive_time = current_time

        # Check for incoming packets with a short timeout
        readable, _, _ = select.select([sock], [], [], 0.01)  # 10ms timeout
        if readable:
            # Drain the socket buffer to find the latest packet
            while True:
                try:
                    data, _ = sock.recvfrom(1024)  # Buffer size of 1024 bytes
                    # Check if packet has enough data for header
                    if len(data) < HEADER_SIZE:
                        print("Received packet too short, skipping")
                        continue

                    # Extract sequence number and checksum from header
                    # I - unsigned int (4 bytes)
                    # H - unsigned short (2 bytes)
                    # Q - unsigned long long (8 bytes)
                    try:
                        seq, received_checksum, timestamp_ms = struct.unpack(
                            ">IHQ", data[:HEADER_SIZE]
                        )
                    except struct.error:
                        print("Failed to unpack header data")
                        continue
                    payload = data[HEADER_SIZE:]

                    # Verify checksum
                    calc_checksum = calculate_checksum(payload)
                    if calc_checksum != received_checksum:
                        print(
                            f"Checksum mismatch for seq {seq}: {received_checksum} != {calc_checksum}"
                        )
                        continue

                    failure_threshold = 500
                    time_lag_ms = (time.time() * 1000) - timestamp_ms

                    # Check if timestamp is too old
                    timeout_failure = time_lag_ms > failure_threshold
                    if timeout_failure:
                        print(f"Packet too old, seq {seq} - Time lag: {time_lag_ms}ms")
                        continue

                    # Update if this packet is newer
                    if seq > latest_seq:
                        latest_seq = seq
                        latest_packet = payload

                except BlockingIOError:
                    # No more packets to read, exit the inner loop
                    break

            # Process the latest packet if one was found
            if latest_packet:
                print(
                    f"processing - Seq: {int(latest_seq):05d}, Data: {latest_packet.hex()}"
                )
                # if latest_seq % 1000 == 0:
                #     print(
                #         f"processing - Seq: {int(latest_seq / 1000):05d}, Data: {latest_packet.hex()}"
                #     )

                pitch, yaw, throttle, steering = struct.unpack("<ffff", latest_packet)

                if not mac_test_environment:
                    # Send the command to the Arduino
                    send_command_to_arduino(
                        arduino_serial_interface,
                        arduino_sequence_number,
                        pitch,
                        yaw,
                        throttle,
                        steering,
                    )
                arduino_sequence_number = (arduino_sequence_number + 1) % 256

                latest_packet = None  # Reset for the next cycle


if __name__ == "__main__":
    start_udp_control_receiver()
