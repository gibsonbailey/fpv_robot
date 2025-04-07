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
import socket
import struct
import time

from manager.headset_location import set_headset_location
from manager.utils import recv_all


print("Setting headset location...")
success = set_headset_location()
if not success:
    exit(1)

print("Starting mock headset server...")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("0.0.0.0", 6778))
sock.listen(1)

print("Listening for incoming TCP connections on port 6778...")

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

udp_sock.bind(("0.0.0.0", 6779))

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
    sock: socket.socket, target_addr: tuple[str, int], seq: int, payload: bytes
):
    """
    Send a UDP packet with sequence number, checksum, and payload.

    Args:
        sock: UDP socket object
        target_addr: Tuple of (target_ip, target_port)
        seq: Sequence number (0-255)
        payload: Byte string of the payload data
    """
    checksum = calculate_checksum(payload)
    # Pack header: sequence number (1 byte), checksum (2 bytes), long (8 bytes) (big-endian)
    # Payload: 4-byte float (big-endian)
    header = struct.pack(">IHQ", seq, checksum, avg_offset + int(time.time() * 1000))
    packet = header + payload
    _ = sock.sendto(packet, target_addr)
    print(f"sent - Seq: {int(seq):05d}, Payload: {payload.hex()}")
    # if seq % 1000 == 0:
    #     # Print the packet details every 1k packets
    #     print(f"sent - Seq: {int(seq / 1000):05d}, Payload: {payload.hex()}")


seq = 0  # Initialize sequence number
counter = 0  # Initialize payload counter for simulation

# Send data packets continuously
while True:
    # Simulate a control signal with a payload of 4 floats
    payload = struct.pack(">ffff", counter / 10, 2, 3, 4)
    send_packet(udp_sock, target_addr, seq, payload)

    # Increment sequence number
    seq = seq + 1
    counter += 1

    # Control packet rate
    time.sleep(0.01)
