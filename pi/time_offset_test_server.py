import socket
import json
import struct
import time


# Create socket server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind(("0.0.0.0", 12345))
    server_socket.listen()
    print("Server listening on port 12345")

    while True:
        conn, addr = server_socket.accept()
        with conn:
            print("Connected by", addr)

            offsets = []

            print("Calibrating time offset...")

            for i in range(50):
                pitch = 0.0
                yaw = 0.0
                throttle = 0.0
                steering = 0.0

                t1 = int(time.time() * 1000)

                data = struct.pack(
                    "<Qffff",
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                conn.sendall(data)
                data = conn.recv(1024)

                t4 = int(time.time() * 1000)

                t = struct.unpack("<Q", data)[0]

                offset = ((t - t1) - (t - t4)) / 2
                offsets.append(offset)
                # print(f"offset: {offset}")
                time.sleep(0.1)

            avg_offset = sum(offsets) / len(offsets)
            print(f"avg_offset: {avg_offset}")

            for i in range(5):
                pitch = 0.0
                yaw = 0.0
                throttle = 0.0
                steering = 0.0

                t1 = int(time.time() * 1000)

                data = struct.pack(
                    "<Qffff",
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                conn.sendall(data)
                data = conn.recv(1024)

                t4 = int(time.time() * 1000)

                response = json.loads(data.decode("utf-8"))

                t4 = int(time.time() * 1000)

                t = struct.unpack("<Q", data)[0]

                offset = ((t - t1) - (t - t4)) / 2

                print()
                print(f"start: {t1}")
                print(f"other_recv: {t}")
                print(f"other_send: {t}")
                print(f"end: {t4}")

                offset = ((t - t1) - (t - t4)) / 2
                offsets.append(offset)
                print(f"offset: {offset}")
                time.sleep(1)

            while True:
                # Send data which can be unpacked like this:
                # timestamp, pitch, yaw, throttle, steering = struct.unpack(
                #     "<Qffff",  # < means little-endian. Q means unsigned long long (8 bytes), f means float (4 bytes)
                #     data,
                # )

                timestamp = int(time.time() * 1000)
                pitch = 0.0
                yaw = 0.0
                throttle = 0.0
                steering = 0.0
                data = struct.pack("<Qffff", timestamp, pitch, yaw, throttle, steering)

                conn.sendall(data)

                time.sleep(0.001)
