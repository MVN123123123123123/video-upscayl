#include "engine.h"
#include "ncnn/cpu.h"
#include <iostream>
#include <omp.h>

InferenceWorker::InferenceWorker()
    : use_gpu_(false), gpu_id_(0), num_threads_(1) {
}

InferenceWorker::~InferenceWorker() {
    std::lock_guard<std::mutex> lock(infer_mutex_);
    net_.clear();
}

bool InferenceWorker::init(
    const std::string& model_path,
    const std::string& param_path,
    bool use_gpu,
    int gpu_id,
    int num_threads
) {
    std::lock_guard<std::mutex> lock(infer_mutex_);
    use_gpu_ = use_gpu;
    gpu_id_ = gpu_id;

    if (use_gpu_) {
        net_.opt.use_vulkan_compute = true;
        net_.opt.use_fp16_packed = true;
        net_.opt.use_fp16_storage = true;
        net_.opt.use_fp16_arithmetic = true;
        net_.opt.use_packing_layout = true;
        net_.set_vulkan_device(gpu_id_);
    } else {
        net_.opt.use_vulkan_compute = false;
        int threads = num_threads;
        if (threads <= 0) {
            threads = ncnn::get_cpu_count();
        }
        if (threads <= 0) {
            threads = 4;
        }
        num_threads_ = threads;
        net_.opt.num_threads = num_threads_;
    }

    int ret_param = net_.load_param(param_path.c_str());
    if (ret_param != 0) {
        std::cerr << "[VideoUpscaler] Error loading param file: " << param_path << " (code: " << ret_param << ")" << std::endl;
        return false;
    }

    int ret_model = net_.load_model(model_path.c_str());
    if (ret_model != 0) {
        std::cerr << "[VideoUpscaler] Error loading model weights: " << model_path << " (code: " << ret_model << ")" << std::endl;
        return false;
    }

    const auto& in_names = net_.input_names();
    if (!in_names.empty() && in_names[0]) {
        in_name_ = in_names[0];
    } else {
        in_name_ = "data";
    }

    const auto& out_names = net_.output_names();
    if (!out_names.empty() && out_names[0]) {
        out_name_ = out_names[0];
    } else {
        out_name_ = "output";
    }

    return true;
}

int InferenceWorker::process_tile(
    const uint8_t* in_rgb,
    int w,
    int h,
    uint8_t* out_rgb,
    int scale
) {
    (void)scale;
    ncnn::Mat in = ncnn::Mat::from_pixels(in_rgb, ncnn::Mat::PIXEL_RGB, w, h);
    if (in.empty()) {
        std::cerr << "[VideoUpscaler] Failed to allocate input Mat for tile (" << w << "x" << h << ")" << std::endl;
        return -1;
    }

    const float norm_vals[3] = {1.0f / 255.0f, 1.0f / 255.0f, 1.0f / 255.0f};
    in.substract_mean_normalize(nullptr, norm_vals);

    ncnn::Mat out;
    {
        std::lock_guard<std::mutex> lock(infer_mutex_);
        ncnn::Extractor ex = net_.create_extractor();
        ex.input(in_name_.c_str(), in);
        int ret = ex.extract(out_name_.c_str(), out);
        if (ret != 0) {
            std::cerr << "[VideoUpscaler] Error extracting output layer '" << out_name_ << "': " << ret << std::endl;
            return ret;
        }
    }

    const float denorm_vals[3] = {255.0f, 255.0f, 255.0f};
    const float mean_vals[3] = {0.0f, 0.0f, 0.0f};
    out.substract_mean_normalize(mean_vals, denorm_vals);
    out.to_pixels(out_rgb, ncnn::Mat::PIXEL_RGB);

    return 0;
}
