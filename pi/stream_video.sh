# Make POST request to 192.168.0.14:4337
# Get the server_ip out of the json response store it in IP_ADDRESS
LOCAL_IP=$(ifconfig | grep 'inet 192.168.' | awk '{print $2}' | cut -d/ -f1)
echo "LOCAL_IP: $LOCAL_IP"
PUBLIC_IP=$(curl -s https://api.ipify.org)

# if no local ip then make one up
if [ -z "$LOCAL_IP" ]; then
  LOCAL_IP="192.168.0.2"
fi

CONNECTION_SERVICE_URL="http://3.215.138.208:4337/client"

# Example POST request
# curl -X POST http://127.0.0.1:5000/client \
#      -H "Content-Type: application/json" \
#      -d '{
#            "client_local_ip": "192.168.0.20",
#            "client_public_ip": "123.45.67.89"
#          }'


while true
do
  IP_ADDRESS=$(curl -s -X POST $CONNECTION_SERVICE_URL -H "Content-Type: application/json" -d "{\"client_local_ip\": \"$LOCAL_IP\", \"client_public_ip\": \"$PUBLIC_IP\"}" | jq -r '.server_ip')

  echo "IP_ADDRESS: $IP_ADDRESS"
  echo "PORT: $PORT"

  # if no IP_ADDRESS then sleep for 5 seconds and try again
  if [ -z "$IP_ADDRESS" ]; then
    echo "No IP_ADDRESS found. Sleeping for 5 seconds..."
    sleep 5
    continue
  fi

  # Ping the IP_ADDRESS (1 packet, timeout 2 seconds)
  if ! ping -c 1 -W 2 "$IP_ADDRESS" > /dev/null 2>&1; then
    echo "Cannot reach $IP_ADDRESS. Sleeping for 5 seconds..."
    sleep 5
    continue
  fi

  echo "Starting GStreamer..."
  
  # G Streamer (hardware encoded with v4l2h264enc)
  gst-launch-1.0 \
    libcamerasrc ! \
    v4l2convert ! video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 ! \
    queue ! \
    videoscale ! video/x-raw,width=428,height=240 ! \
    queue leaky=2 max-size-buffers=10 ! \
    v4l2h264enc ! 'video/x-h264,level=(string)3' ! h264parse config-interval=1 ! \
    queue leaky=2 max-size-buffers=10 ! \
    mpegtsmux ! \
    queue leaky=2 max-size-buffers=10 ! \
    udpsink host=$IP_ADDRESS port=$PORT sync=false

  echo "GStreamer exited. Restarting in 5 seconds..."
  sleep 5
done
