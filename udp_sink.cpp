#include <iostream>
#include <opencv2/opencv.hpp>

// These are C libraries, so we need to use extern "C" to prevent name mangling
extern "C" {
    #include <libavformat/avformat.h>
    #include <libavcodec/avcodec.h>
    #include <libswscale/swscale.h>
    #include <libavutil/imgutils.h>
}

// Read callback for the in-memory buffer
static int read_packet(void *opaque, uint8_t *buf, int buf_size) {
    struct BufferData {
        const uint8_t *ptr;
        size_t size;
    };
    BufferData *bd = (BufferData *)opaque;
    int len = FFMIN(buf_size, bd->size);
    if(len == 0)
        return AVERROR_EOF;
    memcpy(buf, bd->ptr, len);
    bd->ptr  += len;
    bd->size -= len;
    return len;
}

int main() {
    std::cout << "Starting UDP video stream receiver..." << std::endl;

    avformat_network_init();

    // SDP description embedded as a string.
    const char *sdp_data =
        "v=0\n"
        // "o=- 0 0 IN IP4 192.168.0.22\n"   // Use the streaming machine's IP.
        "o=- 0 0 IN IP4 0.0.0.0\n"   // Use the streaming machine's IP.
        "s=No Name\n"
        // "c=IN IP4 192.168.1.22\n"
        "c=IN IP4 0.0.0.0\n"
        "t=0 0\n"
        "a=tool:libavformat\n"
        "m=video 5253 RTP/AVP 96\n"
        "a=rtpmap:96 H264/90000\n";

    // Initialize buffer data structure
    struct BufferData {
        const uint8_t *ptr;
        size_t size;
    } bd;
    bd.ptr = (const uint8_t*)sdp_data;
    bd.size = strlen(sdp_data);

    // Allocate buffer for AVIOContext (you can choose an appropriate size)
    const int buffer_size = 4096;
    uint8_t *avio_buffer = (uint8_t*)av_malloc(buffer_size);
    if (!avio_buffer) {
        std::cerr << "Could not allocate avio buffer." << std::endl;
        return -1;
    }

    // Create custom AVIOContext.
    AVIOContext *avio_ctx = avio_alloc_context(
        avio_buffer, buffer_size,
        0, // write_flag = 0 (read-only)
        &bd, // opaque pointer to our BufferData
        read_packet, // our read callback
        nullptr, // no write callback
        nullptr  // no seek callback
    );
    if (!avio_ctx) {
        std::cerr << "Could not allocate AVIOContext." << std::endl;
        av_free(avio_buffer);
        return -1;
    }

    std::cout << "Opening UDP stream: " << "SDP" << std::endl;

    AVFormatContext* formatContext = avformat_alloc_context();
    formatContext->pb = avio_ctx;

    if (avformat_open_input(&formatContext, nullptr, nullptr, nullptr) != 0) {
        std::cerr << "Error: Could not open UDP stream." << std::endl;
        return -1;
    }

    std::cout << "Opened UDP stream successfully." << std::endl;

    av_log_set_level(AV_LOG_DEBUG);

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

    int dst_width = 854;
    int dst_height = 480;
    AVPixelFormat dst_pix_fmt = AV_PIX_FMT_BGRA;

    struct SwsContext* swsCtx = sws_getContext(
        codecContext->width,
        codecContext->height,
        codecContext->pix_fmt,
        dst_width,
        dst_height,
        dst_pix_fmt,
        // codecContext->width,
        // codecContext->height,
        // AV_PIX_FMT_BGR24,
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
            // Convert the frame from its native format to BGRA (used by OpenCV)
            cv::Mat image(dst_height, dst_width, CV_8UC4);
            uint8_t* dest[4] = { image.data, nullptr, nullptr, nullptr };
            int dest_linesize[4] = { static_cast<int>(image.step[0]), 0, 0, 0 };
            sws_scale(
                swsCtx,
                latest_frame->data,
                latest_frame->linesize,
                0,
                codecContext->height,
                dest,
                dest_linesize
            );

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
    if (avio_ctx) {
        av_freep(&avio_ctx->buffer);
        avio_context_free(&avio_ctx);
    }
    avformat_network_deinit();

    return 0;
}
