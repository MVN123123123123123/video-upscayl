import os
import sys
import re
import json
import shutil
import platform
import subprocess
import ctypes
from typing import Dict, Any, Optional


def find_executable(name: str) -> Optional[str]:
    """Finds an executable in PATH or standard system/bundle directories."""
    # 1. Custom environment variable override
    env_var = f"{name.upper()}_PATH"
    if env_var in os.environ and os.path.exists(os.environ[env_var]):
        return os.environ[env_var]

    # 2. Check standard PATH lookup (including .exe on Windows)
    path_hit = shutil.which(name)
    if path_hit:
        return path_hit

    # 3. Check local directory / bundled locations
    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    search_dirs = [
        os.getcwd(),
        base_dir,
        os.path.join(base_dir, "tools"),
        os.path.join(base_dir, "bin"),
        os.path.join(base_dir, "tools", "ffmpeg", "bin"),
    ]

    if sys.platform == "win32":
        # Standard Windows installation paths
        search_dirs.extend([
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
            os.path.expandvars(r"%USERPROFILE%\scoop\shims"),
        ])

    for s_dir in search_dirs:
        candidate = os.path.join(s_dir, exe_name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK if sys.platform != "win32" else os.R_OK):
            return candidate

    return None


def get_ffmpeg_path() -> str:
    path = find_executable("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "FFmpeg executable ('ffmpeg' or 'ffmpeg.exe') was not found in PATH or standard directories.\n"
            "Please install FFmpeg or place ffmpeg.exe inside the project directory.\n"
            "Download: https://ffmpeg.org/download.html"
        )
    return path


def get_ffprobe_path() -> str:
    path = find_executable("ffprobe")
    if not path:
        raise FileNotFoundError(
            "FFprobe executable ('ffprobe' or 'ffprobe.exe') was not found in PATH or standard directories.\n"
            "Please install FFmpeg tools or place ffprobe.exe inside the project directory.\n"
            "Download: https://ffmpeg.org/download.html"
        )
    return path


def get_subprocess_kwargs() -> Dict[str, Any]:
    """Returns platform-specific subprocess kwargs, e.g. hiding console window on Windows."""
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        # 0x08000000 = CREATE_NO_WINDOW
        kwargs["creationflags"] = 0x08000000
    return kwargs


def probe_video(video_path: str) -> Dict[str, Any]:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    ffprobe_cmd = get_ffprobe_path()
    cmd = [
        ffprobe_cmd,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **get_subprocess_kwargs()
    )
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {video_path}: {res.stderr}")

    data = json.loads(res.stdout)

    video_stream = None
    audio_streams = []
    subtitle_streams = []

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and video_stream is None:
            video_stream = stream
        elif codec_type == "audio":
            audio_streams.append(stream)
        elif codec_type == "subtitle":
            subtitle_streams.append(stream)

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    # Calculate FPS
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) > 0 else 30.0
    else:
        fps = float(fps_str)

    # Duration
    duration_str = video_stream.get("duration") or data.get("format", {}).get("duration", "0")
    duration = float(duration_str)

    # Total frames
    nb_frames_str = video_stream.get("nb_frames")
    if nb_frames_str and nb_frames_str.isdigit() and int(nb_frames_str) > 0:
        total_frames = int(nb_frames_str)
    else:
        total_frames = int(round(duration * fps)) if duration > 0 and fps > 0 else 0

    pix_fmt = video_stream.get("pix_fmt", "yuv420p")
    video_codec = video_stream.get("codec_name", "unknown")

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "fps_rational": fps_str,
        "duration": duration,
        "total_frames": total_frames,
        "video_codec": video_codec,
        "pix_fmt": pix_fmt,
        "audio_stream_count": len(audio_streams),
        "subtitle_stream_count": len(subtitle_streams),
        "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
        "size_bytes": os.path.getsize(video_path)
    }


def get_hardware_info() -> Dict[str, Any]:
    info = {
        "os_name": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu_name": "Unknown CPU",
        "cpu_threads": os.cpu_count() or 1,
        "cpu_simd": "Detecting...",
        "gpus": [],
        "ram_gb": 0.0
    }

    # Cross-platform CPU Model Name
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            info["cpu_name"] = str(cpu_name).strip()
            winreg.CloseKey(key)
        except Exception:
            info["cpu_name"] = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "x86_64 Processor")
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
            info["cpu_name"] = out.strip()
        except Exception:
            info["cpu_name"] = platform.processor() or "Apple Silicon / Intel Mac"
    else:
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu_name"] = line.split(":", 1)[1].strip()
                        break
        except Exception:
            info["cpu_name"] = platform.processor() or "x86_64 Linux Processor"

    # Cross-platform RAM
    if sys.platform == "win32":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            info["ram_gb"] = round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
            info["ram_gb"] = round(int(out.strip()) / (1024 ** 3), 1)
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = float(line.split()[1])
                        info["ram_gb"] = round(kb / (1024 * 1024), 1)
                        break
        except Exception:
            pass

    # Native Backend GPU & CPU SIMD Telemetry
    try:
        from .backend_bridge import VideoUpscalerBackend
        backend = VideoUpscalerBackend()
        info["gpus"] = backend.get_gpu_devices()
        info["cpu_simd"] = backend.get_cpu_simd_info()
    except Exception as e:
        info["gpu_error"] = str(e)
        info["cpu_simd"] = "Standard SIMD"

    return info
