# From the perspective of the pi:
# First, get the headset location from the aws server and cache it (happens in clock sync)
# Then, create a TCP socket connection to the headset server to sync clocks
# After clock sync finishes, the clock sync server will be closed, causing the TCP socket to close
# The clock offset is stored on the headset

# Then, we can create a UDP socket to send and receive real-time data
# The UDP socket starts listening
# The UDP socket punches a keepalive packet through the firewall and NAT every 10 seconds
# Then, the headset will know the client's IP address and port (NAT mapped)
# The UDP socket will then receive a stream of control messages from the headset
# These headset messages are validated and then sent to the arduino
# The UDP socket is also used to stream telemetry data to the headset


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

from manager.utils import recv_all


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

    print(f'diff_1: {remote_timestamp_ms - before_timestamp_ms} = {remote_timestamp_ms} - {before_timestamp_ms}')
    print(f'diff_2: {after_timestamp_ms - remote_timestamp_ms} = {after_timestamp_ms} - {remote_timestamp_ms}')

    diff_1 = remote_timestamp_ms - before_timestamp_ms
    diff_2 = after_timestamp_ms - remote_timestamp_ms

    offset = (diff_1 + diff_2) / 2
    timestamp_ms_offsets.append(offset)

avg_offset = int(sum(timestamp_ms_offsets) / len(timestamp_ms_offsets))

print(f"Average offset: {avg_offset} ms")
