class ControllerServerConnectionRefusedError(Exception):
    # Store ip and port
    def __init__(self, ip, port):
        super().__init__(f"Connection refused by server at {ip}:{port}")
        self.ip: str = ip
        self.port: int = port

