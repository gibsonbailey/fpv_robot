


# Macbook in Dalton Gardens
IP_ADDRESS=10.0.0.165
PORT=5253


# VR Headset at home
IP_ADDRESS=192.168.0.11
PORT=5253

# Mac at home
IP_ADDRESS=192.168.0.3
PORT=5253

# VR Headset in Dalton Gardens
IP_ADDRESS=10.0.0.187
PORT=5253


# Make POST request to 192.168.0.14:4337
# Get the server_ip out of the json response store it in IP_ADDRESS
LOCAL_IP=$(ifconfig | grep 'inet 192.168.0' | awk '{print $2}' | cut -d/ -f1)
echo "LOCAL_IP: $LOCAL_IP"
PUBLIC_IP=$(curl -s https://api.ipify.org)

# Example POST request
# curl -X POST http://127.0.0.1:5000/client \
#      -H "Content-Type: application/json" \
#      -d '{
#            "client_local_ip": "192.168.0.20",
#            "client_public_ip": "123.45.67.89"
#          }'
while
do
  IP_ADDRESS=$(curl -s -X POST http://192.168.0.14:4337/client -H "Content-Type: application/json" -d "{\"client_local_ip\": \"$LOCAL_IP\", \"client_public_ip\": \"$PUBLIC_IP\"}" | jq -r '.server_ip')
  
  echo "IP_ADDRESS: $IP_ADDRESS"
  echo "PORT: $PORT"

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

# G Streamer (software encoded with x264)
# gst-launch-1.0 -vvv \
# libcamerasrc ! \
# video/x-raw,width=1920,height=1080,framerate=15/1 ! \
# videoscale ! \
# video/x-raw,width=428,height=240 ! \
# videoconvert ! \
# queue max-size-buffers=1 leaky=downstream ! \
# x264enc bitrate=4000 speed-preset=superfast tune=zerolatency key-int-max=30 ! \
# h264parse ! \
# mpegtsmux ! \
# udpsink host=$IP_ADDRESS port=$PORT


