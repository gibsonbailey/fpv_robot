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

            for i in range(2):
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

                t2 = response["t2"]
                t3 = response["t3"]

                print()
                print(f"t1: {t1}")
                print(f"t2: {t2}")
                print(f"t3: {t3}")
                print(f"t4: {t4}")

                offset = ((t2 - t1) - (t4 - t3)) / 2
                print(f"offset: {offset}")
            exit()

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
