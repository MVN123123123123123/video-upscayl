#ifndef VIDEO_UPSCALER_H
#define VIDEO_UPSCALER_H

#ifdef __cplusplus
extern "C" {
#endif

#define DEVICE_AUTO   0
#define DEVICE_GPU    1
#define DEVICE_CPU    2
#define DEVICE_HYBRID 3

typedef struct videoupscaler_ctx videoupscaler_t;

/**
 * Creates and initializes an upscaler instance.
 * @param model_path Path to the .bin weights file.
 * @param param_path Path to the .param architecture file.
 * @param scale Upscaling factor (e.g. 2, 3, 4).
 * @param device_type DEVICE_GPU (1), DEVICE_CPU (2), or DEVICE_HYBRID (3).
 * @param tile_size Tile dimension (e.g. 256, 400). 0 for no tiling.
 * @param tile_pad Margin padding in pixels (e.g. 10).
 * @param num_threads Number of CPU threads (0 for auto-detect).
 * @return Context pointer, or NULL on failure.
 */
videoupscaler_t* videoupscaler_create(
    const char* model_path,
    const char* param_path,
    int scale,
    int device_type,
    int tile_size,
    int tile_pad,
    int num_threads
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
int videoupscaler_process_frame(
    videoupscaler_t* handle,
    const unsigned char* in_rgb,
    int in_w,
    int in_h,
    unsigned char* out_rgb
);

/**
 * Benchmarks GPU, CPU, and Hybrid configurations on synthetic input.
 * @param model_path Path to the .bin weights file.
 * @param param_path Path to the .param architecture file.
 * @param scale Upscaling factor.
 * @param width Test frame width.
 * @param height Test frame height.
 * @param num_frames Number of test frames per device.
 * @param out_gpu_fps Pointer to receive GPU frames per second.
 * @param out_cpu_fps Pointer to receive CPU frames per second.
 * @param out_hybrid_fps Pointer to receive Hybrid frames per second.
 * @return 0 on success, non-zero on error.
 */
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
);

/**
 * Returns the number of available Vulkan GPU devices.
 */
int videoupscaler_get_gpu_count();

/**
 * Returns the name of the specified GPU device.
 */
const char* videoupscaler_get_gpu_name(int device_index);

/**
 * Destroys and cleans up the upscaler instance.
 */
void videoupscaler_destroy(videoupscaler_t* handle);

#ifdef __cplusplus
}
#endif

#endif // VIDEO_UPSCALER_H
