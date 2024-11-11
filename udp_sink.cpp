#include <iostream>
#include <opencv2/opencv.hpp>

// These are C libraries, so we need to use extern "C" to prevent name mangling
extern "C" {
    #include <libavformat/avformat.h>
    #include <libavcodec/avcodec.h>
    #include <libswscale/swscale.h>
    #include <libavutil/imgutils.h>
}


int main() {
    std::cout << "Starting UDP video stream receiver..." << std::endl;

    avformat_network_init();

    const char* url = "udp://@:5000";  // Listen on all network interfaces, port 5000

    std::cout << "Opening UDP stream: " << url << std::endl;

    AVFormatContext* formatContext = nullptr;
    if (avformat_open_input(&formatContext, url, nullptr, nullptr) != 0) {
        std::cerr << "Error: Could not open UDP stream." << std::endl;
        return -1;
    }

    std::cout << "Opened UDP stream successfully." << std::endl;

    if (avformat_find_stream_info(formatContext, nullptr) < 0) {
        std::cerr << "Error: Could not find stream information." << std::endl;
        return -1;
    }

    std::cout << "Found stream information." << std::endl;
    std::cout << "Number of streams: " << formatContext->nb_streams << std::endl;

    const AVCodec* codec = nullptr;
    int videoStreamIndex = -1;
    for (unsigned int i = 0; i < formatContext->nb_streams; i++) {
        if (formatContext->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            videoStreamIndex = i;
            codec = avcodec_find_decoder(formatContext->streams[i]->codecpar->codec_id);
            break;
        }
    }


    std::cout << "Codec found." << std::endl;

    if (videoStreamIndex == -1) {
        std::cerr << "Error: Could not find a video stream." << std::endl;
        return -1;
    }

    AVCodecContext* codecContext = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codecContext, formatContext->streams[videoStreamIndex]->codecpar);
    if (avcodec_open2(codecContext, codec, nullptr) < 0) {
        std::cerr << "Error: Could not open codec." << std::endl;
        return -1;
    }

    struct SwsContext* swsCtx = sws_getContext(
        codecContext->width,
        codecContext->height,
        codecContext->pix_fmt,
        codecContext->width,
        codecContext->height,
        AV_PIX_FMT_BGR24,
        SWS_BILINEAR,
        nullptr,
        nullptr,
        nullptr
    );

    AVFrame* frame = av_frame_alloc();
    AVFrame* latest_frame = av_frame_alloc();
    AVPacket* packet = av_packet_alloc();

    // Create an OpenCV window
    cv::namedWindow("UDP Video Stream", cv::WINDOW_AUTOSIZE);

    while (true) {
        std::cout << "Waiting for frame..." << std::endl;
        if (av_read_frame(formatContext, packet) >= 0) {
            if (packet->stream_index == videoStreamIndex) {
                avcodec_send_packet(codecContext, packet);
            }
            av_packet_unref(packet);
        }
        std::cout << "Decoding frame..." << std::endl;

        bool have_new_frame = false;

        while (avcodec_receive_frame(codecContext, frame) == 0) {
            av_frame_unref(latest_frame);
            av_frame_move_ref(latest_frame, frame);
            have_new_frame = true;
        }

        std::cout << "Frame decoded." << std::endl;

        if (have_new_frame) {
            // Convert the frame from its native format to BGR (used by OpenCV)
            cv::Mat image(codecContext->height, codecContext->width, CV_8UC3);
            uint8_t* dest[4] = { image.data, nullptr, nullptr, nullptr };
            int dest_linesize[4] = { static_cast<int>(image.step[0]), 0, 0, 0 };
            sws_scale(swsCtx, latest_frame->data, latest_frame->linesize, 0, codecContext->height, dest, dest_linesize);

            // Display the image
            cv::imshow("UDP Video Stream", image);

            // Exit if 'q' is pressed
            if (cv::waitKey(1) == 'q') {
                goto end;  // Break out of nested loops
            }
        }

    }

end:
    // Cleanup
    cv::destroyWindow("UDP Video Stream");
    sws_freeContext(swsCtx);
    av_frame_free(&frame);
    av_frame_free(&latest_frame);
    av_packet_free(&packet);
    avcodec_free_context(&codecContext);
    avformat_close_input(&formatContext);
    avformat_network_deinit();

    return 0;
}
