import struct
import subprocess
import time

import serial

from .utils import cache_if_not_none

ARDUINO_BAUD_RATE = 115200


@cache_if_not_none
def get_arduino_port():
    # Run the bash command as a single subprocess
    retries = 3
    for _ in range(retries):
        arduino_port = subprocess.run(
            [
                "bash",
                "-c",
                "arduino-cli board list | grep 'Nano Every' | awk '{print $1}'",
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if arduino_port:
            return arduino_port
    raise RuntimeError(f"Failed to get Arduino port after {retries} retries.")


def get_arduino_serial_interface():
    arduino_port = get_arduino_port()
    print(
        f"Connecting to Arduino on port {arduino_port} at baud rate {ARDUINO_BAUD_RATE}..."
    )
    ser = serial.Serial(arduino_port, ARDUINO_BAUD_RATE)
    time.sleep(1)  # Give some time for the connection to establish
    print("Connected to Arduino")
    return ser


def send_command_to_arduino(
    serial_interface, sequence_number, pitch, yaw, throttle, steering
):
    # Packet is structured as follows:
    # 0xDEADBEEF as a header
    # 1 byte sequence number
    # 4 bytes for pitch
    # 4 bytes for yaw
    # 4 bytes for throttle
    # 4 bytes for steering
    # 1 byte checksum
    ready_to_send_bytes = struct.pack(
        "<IBffff",
        0xDEADBEEF,
        sequence_number,
        pitch,
        yaw,
        throttle,
        steering,
    )

    print(
        f"processing - Seq: {int(sequence_number):03d}, Data: {throttle}, {steering}"
    )

    checksum = 0
    for byte in ready_to_send_bytes:
        checksum ^= byte

    ready_to_send_bytes += struct.pack("<B", checksum)

    # Send the packet
    _ = serial_interface.write(ready_to_send_bytes)


# Create a thread that listens for data from the Arduino
def read_from_arduino(active_socket, serial_port):
    while READ_FROM_ARDUINO_THREAD_ENABLED:
        data = serial_port.readline().decode("utf-8").strip()
        if data:
            print(f"Received from Arduino: {data}")
            if data.startswith("tel:"):
                (
                    _,
                    speed_mph,
                    distance_ft,
                    control_battery_percentage,
                    drive_battery_percentage,
                ) = data.split(" ")
                speed_mph = float(speed_mph)
                distance_ft = float(distance_ft)
                active_socket.sendall(
                    struct.pack(
                        # "<Qffii" means little-endian unsigned long long (8 bytes), float (4 bytes), float (4 bytes), int (4 bytes), int (4 bytes)
                        "<Qffii",
                        0,
                        speed_mph,
                        distance_ft,
                        control_battery_percentage,
                        drive_battery_percentage,
                    )
                )
