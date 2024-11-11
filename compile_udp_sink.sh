libdir=/opt/homebrew/Cellar/ffmpeg/7.1_3/lib
includedir=/opt/homebrew/Cellar/ffmpeg/7.1_3/include

binary_name=udp_sink

g++ -std=c++17 -o udp_sink udp_sink.cpp $(pkg-config --cflags --libs opencv4 libavformat libavcodec libavutil libswscale libavdevice libavfilter) -lpthread
# g++ -o udp_sink udp_sink.cpp $(pkg-config --cflags --libs opencv4 libavformat libavcodec libavutil libswscale libavdevice libavfilter) -lpthreadain_file_name=udp_sink.cpp
# g++ -o udp_sink udp_sink.cpp -I$includedir -L$libdir -lavformat -lavcodec -lavutil -lswscale -lavdevice -lavfilter -lopencv_core -lopencv_highgui -lopencv_imgproc -lopencv_videoio -lpthread
# g++ -I$includedir -L$libdir -o $binary_name $main_file_name -lavformat -lavcodec -lavutil -lswscale -lavdevice -lavfilter -lpthread
