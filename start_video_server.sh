gst-launch-1.0 -v \
udpsrc port=5000 ! \
h264parse ! \
avdec_h264 ! \
videoconvert ! \
autovideosink sync=false
