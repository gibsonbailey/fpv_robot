PORT=/dev/cu.usbmodem101
PORT=$(arduino-cli board list | grep "Nano Every" | awk '{print $1}')

arduino-cli monitor --port $PORT --config baudrate=9600
