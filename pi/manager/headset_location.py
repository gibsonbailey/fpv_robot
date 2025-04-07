import socket

import requests

from .utils import cache_if_not_none

CONNECTION_SERVICE_IP = "3.215.138.208"
CONNECTION_SERVICE_PORT = 4337


@cache_if_not_none
def get_headset_location() -> dict[str, str] | None:
    client_local_ip = socket.gethostbyname(socket.gethostname())
    client_public_ip = requests.get("https://api.ipify.org").text

    print(f"Client Local IP: {client_local_ip}")
    print(f"Client Public IP: {client_public_ip}")

    # Send a request to the connection service
    response = requests.post(
        f"http://{CONNECTION_SERVICE_IP}:{CONNECTION_SERVICE_PORT}/client",
        json={
            "client_local_ip": client_local_ip,
            "client_public_ip": client_public_ip,
        },
    )
    if response.status_code == 200:
        """
        Response looks like this:
        {
          "server_ip": "192.168.0.10",
          "server_port": "8080",
          "stored_at": "2024-12-14T12:34:56.789Z"
        }
        """
        resp_json = response.json()
        print("Received response from connection service")
        print(f"headset ip: {resp_json['server_ip']} port: {resp_json['server_port']}")
        return resp_json
    else:
        print("Failed to get controller server info")
        return None


def set_headset_location() -> bool:
    """Set the headset location in the connection service."""
    public_ip = requests.get("https://api.ipify.org").text

    response = requests.post(
        f"http://{CONNECTION_SERVICE_IP}:{CONNECTION_SERVICE_PORT}/server",
        json={
            "server_public_ip": public_ip,
            "server_local_ip": socket.gethostbyname(socket.gethostname()),
            "server_port": 0,
        },
    )
    if response.status_code == 200:
        print("Successfully set headset location")
        return True
    else:
        print("Failed to set headset location")
        return False
