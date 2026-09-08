# 🚀 Video-Upscayl

A universal, high-performance, hardware-accelerated video super-resolution upscaler written in **Python** with a high-speed native **C++ backend** leveraging **Vulkan Compute** and **Multi-Core SIMD / OpenMP**.

Engineered to maximize throughput directly on your computer's hardware without architectural lock-in, Video-Upscayl runs seamlessly on **NVIDIA**, **AMD**, and **Intel GPUs**, as well as any modern CPU (**AVX-512**, **AVX2 + FMA**, **AVX**, **SSE4.2**, or **ARM NEON**), or concurrently in **Concurrent Hybrid mode (GPU + CPU)**.

---

## 🌟 Key Features

- **Universal Hardware Acceleration (GPU & CPU)**:
  - **Vulkan Compute**: Dynamically probes GPU hardware capabilities (FP16 packed math, FP16 storage, and 16x16 cooperative matrix operations) on **NVIDIA GeForce / RTX**, **AMD Radeon**, and **Intel Arc / Iris Xe** GPUs.
  - **Multi-Architecture CPU SIMD**: Dynamic runtime vector dispatch that automatically executes **AVX-512**, **AVX2 + FMA**, **AVX**, or **ARM NEON** instruction kernels with zero Python GIL contention. Never crashes with `SIGILL (Illegal instruction)` on non-AVX512 machines.
  - **Multi-Threaded Tile Tiler**: OpenMP parallelized tile slicing and border stitching across all available CPU cores.
  - **Concurrent Hybrid Mode**: Distributes inference workload across both GPU and CPU simultaneously.
  - **Multi-GPU Selection**: Seamlessly switches between or auto-picks high-performance discrete GPUs on dual-GPU laptops and workstations.

- **🪟 Full Windows OS Support with GUI-First Mode**:
  - **Zero-CLI Requirement on Windows**: Designed specifically so Windows users never need to use a command prompt. Running the application or clicking the launcher opens directly into the Graphical User Interface.
  - **Windowed No-Console Execution**: Uses `pythonw.exe` and `CREATE_NO_WINDOW` flags so no black command prompt windows flash or interrupt the user.
  - **One-Click Launchers**: Includes double-clickable `launch_gui.bat` and `run.bat`.
  - **Native C++ Windows DLL**: Full Windows DLL symbol exports (`__declspec(dllexport)`) with build scripts for Visual Studio / MSVC and PowerShell.
  - **Standalone Packaging**: Includes PyInstaller packaging script (`scripts/package_windows.py`) to build a self-contained zero-install `.exe`.

- **⚡ Zero-Disk-I/O In-Memory Streaming**:
  - Decodes and encodes video frames in-memory via direct FFmpeg pipes (`rgb24`).
  - Preserves SSD health and prevents disk bottlenecks.

- **💎 Seamless Overlapping Tiling**:
  - Scales 720p, 1080p, 1440p, and 4K footage without running out of VRAM.
  - Reflective border padding eliminates seam lines and border artifacts.

- **🎵 Bit-Perfect Audio & Subtitle Preservation**:
  - Copies multi-track audio, subtitles, and container metadata without lossy re-encoding.

---

## 🪟 Windows OS Quick Start (GUI Mode)

### Running on Windows:
Simply double-click:
```bat
launch_gui.bat
```
*(Or double-click `run.bat`)*

On Windows, the application **automatically launches the Graphical User Interface (GUI)** by default.

### Building Native DLL on Windows:
If you are compiling from source on Windows:
```bat
scripts\build_windows.bat
```
*(Or using PowerShell: `powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1`)*

Requirements:
- Visual Studio (C++ Desktop Development) or Ninja with CMake
- [Vulkan SDK](https://vulkan.lunarg.com/sdk/home)
- Python 3.10+ and FFmpeg (place `ffmpeg.exe` in the folder or in system PATH)

### Packaging Standalone `.exe` for Windows:
```bash
python scripts/package_windows.py
```
Produces a self-contained, windowed `Video-Upscayl.exe` in `dist/Video-Upscayl/`.

---

## 🐧 Linux / macOS Quick Start

### 1. Build Native Backend
```bash
./scripts/build_backend.sh
```
This builds `build/libvideoupscaler.so` with portable multi-architecture CPU optimization (`-O3 -mtune=generic -fopenmp`) and Vulkan acceleration.

### 2. Install Python Dependencies
```bash
pip install -e .
```

### 3. Launch the GUI
```bash
video-upscaler gui
# or:
video-upscaler-gui
```

### 4. Or Use the CLI
```bash
# Auto-detect fastest hardware mode (GPU vs CPU vs Hybrid)
video-upscaler upscale -i input.mp4 -o output.mp4 --device auto

# Inspect detected CPU SIMD and GPU telemetry
video-upscaler info

# Run hardware inference benchmark
video-upscaler benchmark -w 512 -h 288 -n 5

# Generate side-by-side comparison video
video-upscaler upscale -i input.mp4 --compare
```

---

## 📊 Supported Pretrained Models

| Model Name | Scale | Target Content |
| :--- | :---: | :--- |
| **`4x-UltraSharp`** | 4x | **Maximum detail & texture upscaler** (reconstructs micro-details, hair, fabric, crisp lines) |
| `realesr-animevideov3-x2` *(default)* | 2x | High-speed anime, cartoon, animation video |
| `realesr-animevideov3-x3` | 3x | High-speed anime, cartoon, animation video |
| `realesr-animevideov3-x4` | 4x | High-speed anime, cartoon, animation video |
| `realesrgan-x4plus` | 4x | Real-world footage, live action video, photos |
| `realesrgan-x4plus-anime` | 4x | 2D illustrations, digital artwork, anime |

---

## 🧪 Running Automated Tests

Run the complete cross-platform test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```
All 14 tests validate:
- Dynamic CPU SIMD detection
- Vendor-neutral GPU discovery & enumeration
- GPU, CPU, and Hybrid inference
- Boundary seam continuity
- Hardware benchmarking
- Cross-platform FFmpeg/FFprobe resolution
- Windows GUI auto-launch behavior
