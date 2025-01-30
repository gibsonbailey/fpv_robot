


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


