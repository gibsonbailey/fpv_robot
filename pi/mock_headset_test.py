# From the perspective of the headset:
# First, the headset server starts listening for incoming TCP connections
# The headset server will then accept a TCP connection from the pi
# The headset server will then send a clock sync message to the pi
# The pi will then respond with a clock sync message
# This repeats until the clock sync is complete
# The headset server will then close the TCP connection

# The headset server will then start listening for incoming UDP messages
# The headset server will then receive a keepalive packet from the pi
# The keepalive packet will contain the pi's IP address and port
# The headset can now stream control messages to the pi

# Create a TCP socket for the clock sync
import select
import socket
import struct
import time

from pynput import keyboard

from manager.constants import CLOCK_SYNC_PORT, CONTROL_STREAM_PORT
from manager.headset_location import set_headset_location
from manager.utils import recv_all

TELEMETRY_PACKET_SIZE = 16

print("Setting headset location...")
success = set_headset_location()
if not success:
    exit(1)

print("Starting mock headset server...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("0.0.0.0", CLOCK_SYNC_PORT))
sock.listen(1)

print(f"Listening for incoming TCP connections on port {CLOCK_SYNC_PORT}...")

conn, addr = sock.accept()
print(f"Accepted connection from {addr}")


timestamp_ms_offsets = []

for i in range(10):
    before_timestamp_ms = int(time.time() * 1000)

    # Send 1 byte clock sync message
    conn.sendall(b"\x01")

    # Receive clock sync message
    data = recv_all(conn, 8)
    if not data:
        break

    # Unpack the clock sync message
    remote_timestamp_ms = struct.unpack("<Q", data[:8])[0]

    after_timestamp_ms = int(time.time() * 1000)

    # Example offset calculation from c++
    # int64 diff1 = static_cast<int64>(t_client) - static_cast<int64>(t1);
    # int64 diff2 = static_cast<int64>(t4) - static_cast<int64>(t_client);

    # int64 offset = (diff1 + diff2) / 2;

    print(
        f"diff_1: {remote_timestamp_ms - before_timestamp_ms} = {remote_timestamp_ms} - {before_timestamp_ms}"
    )
    print(
        f"diff_2: {after_timestamp_ms - remote_timestamp_ms} = {after_timestamp_ms} - {remote_timestamp_ms}"
    )

    diff_1 = remote_timestamp_ms - before_timestamp_ms
    diff_2 = after_timestamp_ms - remote_timestamp_ms

    offset = (diff_1 + diff_2) / 2
    timestamp_ms_offsets.append(offset)

sock.close()

avg_offset = int(sum(timestamp_ms_offsets) / len(timestamp_ms_offsets))

print(f"Average offset: {avg_offset} ms")

print("Opening UDP socket for control messages...")
# Create a UDP socket for control messages
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

udp_sock.bind(("0.0.0.0", CONTROL_STREAM_PORT))
udp_sock.setblocking(False)

# Wait for the first packet from the receiver to get its address
data, target_addr = udp_sock.recvfrom(1024)
print(f"Received initial packet from {target_addr}, starting to send data.")


def calculate_checksum(data: bytes) -> int:
    """
    Calculate a simple 16-bit checksum by summing all bytes in the data.
    The result is masked to 16 bits (0xFFFF).
    """
    return sum(data) & 0xFFFF


def send_packet(
    sock: socket.socket,
    target_addr: tuple[str, int],
    seq: int,
    payload: bytes,
    steering_value: float,
    throttle_value: float,
):
    """
    Send a UDP packet with sequence number, checksum, and payload.

    Args:
        sock: UDP socket object
        target_addr: Tuple of (target_ip, target_port)
        seq: Sequence number
        payload: Byte string of the payload data
    """
    checksum = calculate_checksum(payload)
    # Pack header: sequence number (1 byte), checksum (2 bytes), long (8 bytes) (big-endian)
    # Payload: 4-byte float (big-endian)
    header = struct.pack(">IHQ", seq, checksum, avg_offset + int(time.time() * 1000))
    packet = header + payload
    _ = sock.sendto(packet, target_addr)
    print(f"sent - Seq: {int(seq):05d}, Payload: {steering_value}, {throttle_value}")
    # if seq % 1000 == 0:
    #     # Print the packet details every 1k packets
    #     print(f"sent - Seq: {int(seq / 1000):05d}, Payload: {payload.hex()}")


# Function to handle key press events

throttle = 0.0
steering = 0.0


def on_press(key):
    global throttle
    global steering
    try:
        if key == keyboard.Key.up:
            throttle = 0.25
        elif key == keyboard.Key.down:
            throttle = -0.45
        elif key == keyboard.Key.right:
            steering = 0.5
        elif key == keyboard.Key.left:
            steering = -0.5
        else:
            throttle = 0.0
            steering = 0.0
    except AttributeError:
        return


def on_release(key):
    global throttle
    global steering
    if key == keyboard.Key.up or key == keyboard.Key.down:
        throttle = 0.0
    elif key == keyboard.Key.right or key == keyboard.Key.left:
        steering = 0.0
    elif key == keyboard.Key.esc:
        # Stop listener
        return


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()  # Start the listener

seq = 0  # Initialize sequence number
counter = 0  # Initialize payload counter for simulation

# Send data packets continuously
while True:
    # Check if there is data to read from the socket
    readable, _, _ = select.select([sock], [], [], 0.01)  # 10ms timeout
    if readable:
        latest_packet = None

        # Drain the socket buffer to find the latest packet
        while True:
            try:
                data, _ = sock.recvfrom(1024)  # Buffer size of 1024 bytes

                # Check if packet is
                if len(data) != TELEMETRY_PACKET_SIZE:
                    print("Received packet not the right size, skipping")
                    continue

                try:
                     latest_packet = struct.unpack(
                        "<ffii",
                        # speed_mph,
                        # distance_ft,
                        # control_battery_percentage,
                        # drive_battery_percentage,
                        data
                    )
                except struct.error:
                    print("Failed to unpack telemetry data")
                    continue
            except BlockingIOError:
                # No more packets to read, exit the inner loop
                break
        if latest_packet:
            # Process the latest packet if one was found
            print(
                f"received - speed_mph: {latest_packet[0]}, distance_ft: {latest_packet[1]}, control_battery_percentage: {latest_packet[2]}, drive_battery_percentage: {latest_packet[3]}"
            )

    # Simulate a control signal with a payload of 4 floats
    payload = struct.pack(
        ">ffff", float(counter / 10), 0.0, float(throttle), float(steering)
    )
    send_packet(udp_sock, target_addr, seq, payload, steering, throttle)

    # Increment sequence number
    seq = seq + 1
    counter += 1

    # Control packet rate
    time.sleep(0.01)
