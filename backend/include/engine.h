#ifndef ENGINE_H
#define ENGINE_H

#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <atomic>
#include <thread>
#include <condition_variable>
#include "ncnn/net.h"
#include "ncnn/gpu.h"
#include "tiler.h"
#include "videoupscaler.h"

class InferenceWorker {
public:
    InferenceWorker();
    ~InferenceWorker();

    bool init(
        const std::string& model_path,
        const std::string& param_path,
        bool use_gpu,
        int gpu_id = 0,
        int num_threads = 0
    );

    int process_tile(
        const uint8_t* in_rgb,
        int w,
        int h,
        uint8_t* out_rgb,
        int scale
    );

    bool is_gpu() const { return use_gpu_; }
    int device_id() const { return gpu_id_; }

private:
    ncnn::Net net_;
    bool use_gpu_;
    int gpu_id_;
    int num_threads_;
    std::string in_name_;
    std::string out_name_;
    std::mutex infer_mutex_;
};

struct videoupscaler_ctx {
    int scale;
    int device_type;
    int tile_size;
    int tile_pad;
    int num_threads;
    int gpu_device_id;
    std::string model_path;
    std::string param_path;

    std::unique_ptr<InferenceWorker> gpu_worker;
    std::unique_ptr<InferenceWorker> cpu_worker;

    std::mutex ctx_mutex;
};

#endif // ENGINE_H
