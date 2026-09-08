

## Installation & Setup

### 1. Prerequisites
- Linux / CachyOS / Arch / Ubuntu / Other
- `g++` (C++17 support) & `cmake`
- `ffmpeg` with `libx264`
- `vulkan-icd-loader` & Vulkan drivers (`vulkan-radeon`, `mesa`, etc.)
- Python 3.10+ and `uv` or `pip`

### 2. Build the C++ Native Backend
```bash
./scripts/build_backend.sh
```
This compiles `build/libvideoupscaler.so` optimized with `-O3 -march=native -fopenmp`.

### 3. Install Python Dependencies
Using `uv`:
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```
Or using standard `pip`:
```bash
pip install -e .
```

---

## Usage Guide

### 1. Graphical User Interface (Old-School Desktop GUI)
For a straightforward, clean, classic utility interface:
```bash
video-upscaler gui
# or directly:
video-upscaler-gui
```
- Select any input video file with a native file dialog.
- Shows video metadata (resolution, fps, duration, frames).
- One-click model selection (e.g. `4x-UltraSharp` for maximum detail or `realesr-animevideov3` for high speed).
- Live progress bar, frame counter, real-time FPS, and cancel button.
- Built-in hardware benchmarking button.

---

### 2. Command-Line Interface (CLI)

#### Upscale a Video (Auto-Select Fastest Hardware)
```bash
video-upscaler upscale -i input.mp4 -o output.mp4 --device auto
```

### 2. Force Specific Device Mode
```bash
# Force GPU (Vulkan)
video-upscaler upscale -i input.mp4 --device gpu

# Force Concurrent Hybrid (GPU + CPU)
video-upscaler upscale -i input.mp4 --device hybrid

# Force Multi-threaded CPU (AVX-512)
video-upscaler upscale -i input.mp4 --device cpu
```

### 3. Generate a Side-by-Side Comparison Video
```bash
video-upscaler upscale -i input.mp4 --compare
```
Generates both `output.mp4` and `output_compare.mp4` with a side-by-side split screen showing original footage versus super-resolution upscaled footage.

### 4. Run Hardware Benchmark
```bash
video-upscaler benchmark -w 512 -h 288 -n 5
```

### 5. Inspect Available Hardware & Models
```bash
video-upscaler info
video-upscaler models
```

---

## Supported Pretrained Models

| Model Name | Scale | Target Content |
| :--- | :---: | :--- |
| **`4x-UltraSharp`** *(new)* | 4x | **Maximum detail & texture upscaler** (reconstructs micro-details, hair, fabric, crisp lines) |
| `realesr-animevideov3-x2` *(default)* | 2x | High-speed anime, cartoon, animation video |
| `realesr-animevideov3-x3` | 3x | High-speed anime, cartoon, animation video |
| `realesr-animevideov3-x4` | 4x | High-speed anime, cartoon, animation video |
| `realesrgan-x4plus` | 4x | Real-world footage, live action video, photos |
| `realesrgan-x4plus-anime` | 4x | 2D illustrations, digital artwork, anime |

---

## Python API Example

```python
from video_upscaler import VideoUpscalePipeline, DeviceType

pipeline = VideoUpscalePipeline(
    input_path="input.mp4",
    output_path="output.mp4",
    model_name="realesr-animevideov3-x2",
    scale=2,
    device_type=DeviceType.GPU,  # Or DeviceType.HYBRID / DeviceType.CPU
    tile_size=256,
    tile_pad=10
)

stats = pipeline.run()
print(f"Processed {stats['processed_frames']} frames at {stats['average_fps']:.2f} FPS")
```

---

## Running Automated Tests

Run the complete test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
All tests validate C++ C-ABI bindings, GPU enumeration, tile seam continuity, hardware benchmarks, and end-to-end video processing.
