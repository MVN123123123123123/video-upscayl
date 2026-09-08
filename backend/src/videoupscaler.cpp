#include "videoupscaler.h"
#include "engine.h"
#include "tiler.h"
#include <chrono>
#include <iostream>
#include <cstring>
#include <thread>
#include <vector>
#include <atomic>

static std::atomic<int> g_instance_count{0};
static std::mutex g_gpu_init_mutex;

static void ensure_gpu_instance() {
    std::lock_guard<std::mutex> lock(g_gpu_init_mutex);
    if (g_instance_count.fetch_add(1) == 0) {
        ncnn::create_gpu_instance();
    }
}

static void release_gpu_instance() {
    std::lock_guard<std::mutex> lock(g_gpu_init_mutex);
    if (g_instance_count.fetch_sub(1) == 1) {
        ncnn::destroy_gpu_instance();
    }
}

extern "C" {

int videoupscaler_get_gpu_count() {
    ensure_gpu_instance();
    int count = ncnn::get_gpu_count();
    release_gpu_instance();
    return count;
}

const char* videoupscaler_get_gpu_name(int device_index) {
    ensure_gpu_instance();
    int count = ncnn::get_gpu_count();
    const char* name = "Unknown GPU";
    if (device_index >= 0 && device_index < count) {
        const ncnn::VulkanDevice* dev = ncnn::get_gpu_device(device_index);
        if (dev) {
            name = dev->info.device_name();
        }
    }
    release_gpu_instance();
    return name;
}

videoupscaler_t* videoupscaler_create(
    const char* model_path,
    const char* param_path,
    int scale,
    int device_type,
    int tile_size,
    int tile_pad,
    int num_threads
) {
    if (!model_path || !param_path) {
        return nullptr;
    }

    ensure_gpu_instance();

    auto* ctx = new videoupscaler_ctx();
    ctx->scale = scale;
    ctx->device_type = device_type;
    ctx->tile_size = (tile_size > 0) ? tile_size : 0;
    ctx->tile_pad = (tile_pad >= 0) ? tile_pad : 10;
    ctx->num_threads = num_threads;
    ctx->model_path = model_path;
    ctx->param_path = param_path;

    if (device_type == DEVICE_GPU || device_type == DEVICE_HYBRID) {
        ctx->gpu_worker = std::make_unique<InferenceWorker>();
        if (!ctx->gpu_worker->init(model_path, param_path, true, 0, 0)) {
            std::cerr << "[VideoUpscaler] Failed to initialize GPU worker" << std::endl;
            delete ctx;
            release_gpu_instance();
            return nullptr;
        }
    }

    if (device_type == DEVICE_CPU || device_type == DEVICE_HYBRID) {
        ctx->cpu_worker = std::make_unique<InferenceWorker>();
        if (!ctx->cpu_worker->init(model_path, param_path, false, 0, num_threads)) {
            std::cerr << "[VideoUpscaler] Failed to initialize CPU worker" << std::endl;
            delete ctx;
            release_gpu_instance();
            return nullptr;
        }
    }

    return ctx;
}

static int process_tiles_single_worker(
    InferenceWorker* worker,
    const std::vector<TileInfo>& tiles,
    const unsigned char* in_rgb,
    int in_w,
    int in_h,
    unsigned char* out_rgb,
    int scale
) {
    int out_w = in_w * scale;
    int out_h = in_h * scale;

    for (const auto& t : tiles) {
        std::vector<uint8_t> tile_in(t.padded_w * t.padded_h * 3);
        Tiler::extract_tile(in_rgb, in_w, in_h, t, tile_in.data());

        int out_tile_w = t.padded_w * scale;
        int out_tile_h = t.padded_h * scale;
        std::vector<uint8_t> tile_out(out_tile_w * out_tile_h * 3);

        int ret = worker->process_tile(tile_in.data(), t.padded_w, t.padded_h, tile_out.data(), scale);
        if (ret != 0) {
            return ret;
        }

        Tiler::stitch_tile(tile_out.data(), t, scale, out_rgb, out_w, out_h);
    }
    return 0;
}

static int process_tiles_hybrid(
    InferenceWorker* gpu_worker,
    InferenceWorker* cpu_worker,
    const std::vector<TileInfo>& tiles,
    const unsigned char* in_rgb,
    int in_w,
    int in_h,
    unsigned char* out_rgb,
    int scale
) {
    int out_w = in_w * scale;
    int out_h = in_h * scale;

    if (tiles.size() <= 1 || !cpu_worker) {
        return process_tiles_single_worker(gpu_worker, tiles, in_rgb, in_w, in_h, out_rgb, scale);
    }

    std::atomic<size_t> tile_cursor{0};
    std::atomic<int> error_flag{0};

    auto worker_task = [&](InferenceWorker* worker) {
        while (error_flag.load(std::memory_order_relaxed) == 0) {
            size_t idx = tile_cursor.fetch_add(1);
            if (idx >= tiles.size()) {
                break;
            }
            const auto& t = tiles[idx];
            std::vector<uint8_t> tile_in(t.padded_w * t.padded_h * 3);
            Tiler::extract_tile(in_rgb, in_w, in_h, t, tile_in.data());

            int out_tile_w = t.padded_w * scale;
            int out_tile_h = t.padded_h * scale;
            std::vector<uint8_t> tile_out(out_tile_w * out_tile_h * 3);

            int ret = worker->process_tile(tile_in.data(), t.padded_w, t.padded_h, tile_out.data(), scale);
            if (ret != 0) {
                error_flag.store(ret);
                break;
            }

            Tiler::stitch_tile(tile_out.data(), t, scale, out_rgb, out_w, out_h);
        }
    };

    std::thread gpu_thread(worker_task, gpu_worker);
    std::thread cpu_thread(worker_task, cpu_worker);

    gpu_thread.join();
    cpu_thread.join();

    return error_flag.load();
}

int videoupscaler_process_frame(
    videoupscaler_t* handle,
    const unsigned char* in_rgb,
    int in_w,
    int in_h,
    unsigned char* out_rgb
) {
    if (!handle || !in_rgb || !out_rgb || in_w <= 0 || in_h <= 0) {
        return -1;
    }

    std::vector<TileInfo> tiles = Tiler::compute_tiles(in_w, in_h, handle->tile_size, handle->tile_pad);

    if (handle->device_type == DEVICE_HYBRID && handle->gpu_worker && handle->cpu_worker) {
        return process_tiles_hybrid(
            handle->gpu_worker.get(),
            handle->cpu_worker.get(),
            tiles,
            in_rgb,
            in_w,
            in_h,
            out_rgb,
            handle->scale
        );
    } else if (handle->device_type == DEVICE_CPU && handle->cpu_worker) {
        return process_tiles_single_worker(
            handle->cpu_worker.get(),
            tiles,
            in_rgb,
            in_w,
            in_h,
            out_rgb,
            handle->scale
        );
    } else if (handle->gpu_worker) {
        return process_tiles_single_worker(
            handle->gpu_worker.get(),
            tiles,
            in_rgb,
            in_w,
            in_h,
            out_rgb,
            handle->scale
        );
    }

    return -2;
}

int videoupscaler_benchmark(
    const char* model_path,
    const char* param_path,
    int scale,
    int width,
    int height,
    int num_frames,
    double* out_gpu_fps,
    double* out_cpu_fps,
    double* out_hybrid_fps
) {
    if (!model_path || !param_path || width <= 0 || height <= 0 || num_frames <= 0) {
        return -1;
    }

    std::vector<uint8_t> dummy_in(width * height * 3, 128);
    int out_w = width * scale;
    int out_h = height * scale;
    std::vector<uint8_t> dummy_out(out_w * out_h * 3, 0);

    // 1. Benchmark GPU
    if (out_gpu_fps) {
        videoupscaler_t* ctx_gpu = videoupscaler_create(
            model_path, param_path, scale, DEVICE_GPU, 256, 10, 0
        );
        if (ctx_gpu) {
            // Warmup
            videoupscaler_process_frame(ctx_gpu, dummy_in.data(), width, height, dummy_out.data());

            auto t0 = std::chrono::high_resolution_clock::now();
            for (int i = 0; i < num_frames; i++) {
                videoupscaler_process_frame(ctx_gpu, dummy_in.data(), width, height, dummy_out.data());
            }
            auto t1 = std::chrono::high_resolution_clock::now();
            double secs = std::chrono::duration<double>(t1 - t0).count();
            *out_gpu_fps = (secs > 0) ? (num_frames / secs) : 0.0;
            videoupscaler_destroy(ctx_gpu);
        } else {
            *out_gpu_fps = 0.0;
        }
    }

    // 2. Benchmark CPU (fewer frames if large, e.g. std::min(num_frames, 3))
    if (out_cpu_fps) {
        int cpu_frames = std::min(num_frames, 3);
        videoupscaler_t* ctx_cpu = videoupscaler_create(
            model_path, param_path, scale, DEVICE_CPU, 256, 10, 0
        );
        if (ctx_cpu) {
            // Warmup
            videoupscaler_process_frame(ctx_cpu, dummy_in.data(), width, height, dummy_out.data());

            auto t0 = std::chrono::high_resolution_clock::now();
            for (int i = 0; i < cpu_frames; i++) {
                videoupscaler_process_frame(ctx_cpu, dummy_in.data(), width, height, dummy_out.data());
            }
            auto t1 = std::chrono::high_resolution_clock::now();
            double secs = std::chrono::duration<double>(t1 - t0).count();
            *out_cpu_fps = (secs > 0) ? (cpu_frames / secs) : 0.0;
            videoupscaler_destroy(ctx_cpu);
        } else {
            *out_cpu_fps = 0.0;
        }
    }

    // 3. Benchmark Hybrid
    if (out_hybrid_fps) {
        videoupscaler_t* ctx_hybrid = videoupscaler_create(
            model_path, param_path, scale, DEVICE_HYBRID, 256, 10, 0
        );
        if (ctx_hybrid) {
            // Warmup
            videoupscaler_process_frame(ctx_hybrid, dummy_in.data(), width, height, dummy_out.data());

            auto t0 = std::chrono::high_resolution_clock::now();
            for (int i = 0; i < num_frames; i++) {
                videoupscaler_process_frame(ctx_hybrid, dummy_in.data(), width, height, dummy_out.data());
            }
            auto t1 = std::chrono::high_resolution_clock::now();
            double secs = std::chrono::duration<double>(t1 - t0).count();
            *out_hybrid_fps = (secs > 0) ? (num_frames / secs) : 0.0;
            videoupscaler_destroy(ctx_hybrid);
        } else {
            *out_hybrid_fps = 0.0;
        }
    }

    return 0;
}

void videoupscaler_destroy(videoupscaler_t* handle) {
    if (handle) {
        delete handle;
        release_gpu_instance();
    }
}

} // extern "C"
