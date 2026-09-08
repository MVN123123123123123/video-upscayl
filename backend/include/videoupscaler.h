#ifndef VIDEO_UPSCALER_H
#define VIDEO_UPSCALER_H

#if defined(_WIN32) || defined(__CYGWIN__)
  #ifdef VIDEOUPSCALER_EXPORTS
    #define VIDEOUPSCALER_API __declspec(dllexport)
  #else
    #define VIDEOUPSCALER_API __declspec(dllimport)
  #endif
#else
  #if defined(__GNUC__) && __GNUC__ >= 4
    #define VIDEOUPSCALER_API __attribute__((visibility("default")))
  #else
    #define VIDEOUPSCALER_API
  #endif
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define DEVICE_AUTO   0
#define DEVICE_GPU    1
#define DEVICE_CPU    2
#define DEVICE_HYBRID 3

typedef struct videoupscaler_ctx videoupscaler_t;

/**
 * Creates and initializes an upscaler instance using the default or best GPU.
 * @param model_path Path to the .bin weights file.
 * @param param_path Path to the .param architecture file.
 * @param scale Upscaling factor (e.g. 2, 3, 4).
 * @param device_type DEVICE_GPU (1), DEVICE_CPU (2), or DEVICE_HYBRID (3).
 * @param tile_size Tile dimension (e.g. 256, 400). 0 for no tiling.
 * @param tile_pad Margin padding in pixels (e.g. 10).
 * @param num_threads Number of CPU threads (0 for auto-detect).
 * @return Context pointer, or NULL on failure.
 */
VIDEOUPSCALER_API videoupscaler_t* videoupscaler_create(
    const char* model_path,
    const char* param_path,
    int scale,
    int device_type,
    int tile_size,
    int tile_pad,
    int num_threads
);

/**
 * Creates and initializes an upscaler instance specifying the GPU device index.
 * @param gpu_device_id GPU index (-1 for auto/best discrete GPU).
 */
VIDEOUPSCALER_API videoupscaler_t* videoupscaler_create_with_gpu(
    const char* model_path,
    const char* param_path,
    int scale,
    int device_type,
    int tile_size,
    int tile_pad,
    int num_threads,
    int gpu_device_id
);

/**
 * Upscales a single RGB24 frame.
 * @param handle Context pointer.
 * @param in_rgb Pointer to input packed RGB24 buffer (size: in_w * in_h * 3).
 * @param in_w Input frame width.
 * @param in_h Input frame height.
 * @param out_rgb Pointer to output packed RGB24 buffer (size: in_w*scale * in_h*scale * 3).
 * @return 0 on success, non-zero on error.
 */
VIDEOUPSCALER_API int videoupscaler_process_frame(
    videoupscaler_t* handle,
    const unsigned char* in_rgb,
    int in_w,
    int in_h,
    unsigned char* out_rgb
);

/**
 * Benchmarks GPU, CPU, and Hybrid configurations on synthetic input.
 */
VIDEOUPSCALER_API int videoupscaler_benchmark(
    const char* model_path,
    const char* param_path,
    int scale,
    int width,
    int height,
    int num_frames,
    double* out_gpu_fps,
    double* out_cpu_fps,
    double* out_hybrid_fps
);

/**
 * Benchmarks GPU, CPU, and Hybrid configurations specifying the GPU device index.
 */
VIDEOUPSCALER_API int videoupscaler_benchmark_with_gpu(
    const char* model_path,
    const char* param_path,
    int scale,
    int width,
    int height,
    int num_frames,
    int gpu_device_id,
    double* out_gpu_fps,
    double* out_cpu_fps,
    double* out_hybrid_fps
);

/**
 * Returns the number of available Vulkan GPU devices.
 */
VIDEOUPSCALER_API int videoupscaler_get_gpu_count();

/**
 * Returns the name of the specified GPU device.
 */
VIDEOUPSCALER_API const char* videoupscaler_get_gpu_name(int device_index);

/**
 * Returns the vendor name of the specified GPU (e.g. "NVIDIA", "AMD", "Intel", "Apple", "Unknown").
 */
VIDEOUPSCALER_API const char* videoupscaler_get_gpu_vendor(int device_index);

/**
 * Returns the device type (0 = discrete GPU, 1 = integrated GPU, 2 = virtual GPU, 3 = CPU, -1 = unknown).
 */
VIDEOUPSCALER_API int videoupscaler_get_gpu_type(int device_index);

/**
 * Returns the active CPU vector SIMD extension supported on this host (e.g. "AVX-512", "AVX2 + FMA", "AVX", "SSE4.2", "ARM NEON", "Generic").
 */
VIDEOUPSCALER_API const char* videoupscaler_get_cpu_simd_info();

/**
 * Destroys and cleans up the upscaler instance.
 */
VIDEOUPSCALER_API void videoupscaler_destroy(videoupscaler_t* handle);

#ifdef __cplusplus
}
#endif

#endif // VIDEO_UPSCALER_H
