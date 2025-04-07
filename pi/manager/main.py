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

from manager.clock_sync import start_clock_sync_client
from manager.udp_control_receiver import start_udp_control_receiver


clock_sync_cycles = start_clock_sync_client()
print(f"Clock sync cycles: {clock_sync_cycles}")

if clock_sync_cycles == 0:
    print("Clock sync failed")
    exit(1)

print("Clock sync finished")

# Now we can start the UDP socket to send and receive real-time data
start_udp_control_receiver()
