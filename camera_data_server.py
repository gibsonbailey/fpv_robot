# simple_tcp_server.py

import time
import collections
import struct
import socket


def recv_all(sock, length):
    data = b""
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError("Socket connection closed")
        data += more
    return data


def run_headset_orientation_server():
    time_buffer_size = 20

    # dequeue for time buffer
    time_buffer = collections.deque(maxlen=time_buffer_size)

    time_buffer_print_interval = 60
    time_buffer_print_index = 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        HOST = "0.0.0.0"  # Listen on all interfaces
        PORT = 12345  # Port to listen on
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while True:
                # data = conn.recv(8)
                data = recv_all(conn, 8)
                if not data:
                    break
                # str_data = data.decode()

                time_buffer.append(time.time())
                if len(time_buffer) == time_buffer_size:
                    time_buffer.popleft()
                    time_buffer_print_index += 1
                    if time_buffer_print_index % time_buffer_print_interval == 0:
                        time_diff = time_buffer[-1] - time_buffer[0]
                        print(f"cam data {time_buffer_size / time_diff} Hz")

                try:
                    pitch, yaw = struct.unpack("<ff", data)
                except ValueError:
                    print("Invalid data format: must be float")
                    continue

                print(f"pitch: {pitch} yaw: {yaw}")

while True:
    try:
        run_headset_orientation_server()
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
