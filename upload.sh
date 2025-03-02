PORT=/dev/cu.usbserial-02BA53BD
PORT=/dev/cu.SLAB_USBtoUART
PORT=/dev/cu.usbmodem101
PORT=$(arduino-cli board list | grep "Nano Every" | awk '{print $1}')

# arduino-cli upload --log --fqbn esp32:esp32:featheresp32 --port $PORT combined

if [ -z "$PORT" ]; then
  echo "No port found"
  exit 1
fi

echo "Uploading to $PORT"

arduino-cli upload --log -p $PORT --fqbn arduino:megaavr:nona4809 stepper
