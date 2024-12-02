# simple_tcp_server.py

import socket


def run_headset_orientation_server():
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
                data = conn.recv(1024)
                if not data:
                    break
                str_data = data.decode()

                # There must be two commas in the string to be valid
                if str_data.count(",") != 2:
                    print("Invalid data format: comma count mismatch")
                    continue
                pitch, yaw, roll = str_data.split(",")
                try:
                    pitch = int(float(pitch))
                    yaw = int(float(yaw))
                except ValueError:
                    print("Invalid data format: float conversion failed")
                    continue

                print(f"pitch: {pitch} yaw: {yaw}")

run_headset_orientation_server()
