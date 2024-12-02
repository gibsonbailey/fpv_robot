libdir=/opt/homebrew/Cellar/ffmpeg/7.1_3/lib
includedir=/opt/homebrew/Cellar/ffmpeg/7.1_3/include

binary_name=udp_sink

# g++ -std=c++17 -o udp_sink udp_sink.cpp $(pkg-config --cflags --libs opencv4 libavformat libavcodec libavutil libswscale libavdevice libavfilter) -lpthread

UNREAL_PROJECT_DIR=/Users/bailey/src/MyBlankVRProject

lib_dir="$UNREAL_PROJECT_DIR/ThirdParty/mac/lib"
include_dir="$UNREAL_PROJECT_DIR/ThirdParty/mac/include"

x264_lib_dir=/Users/bailey/src/unreal_fpvcam/ThirdParty/mac/lib
x264_include_dir=/Users/bailey/src/unreal_fpvcam/ThirdParty/mac/include

g++ -v -std=c++17 -o udp_sink udp_sink.cpp $(pkg-config --cflags --libs opencv4 ) \
  -I$include_dir -L$lib_dir -lavformat -lavcodec -lavutil -lswscale -lx264 \
  -lpthread -liconv -lz


  # -framework CoreFoundation -framework VideoToolbox -framework CoreVideo \
