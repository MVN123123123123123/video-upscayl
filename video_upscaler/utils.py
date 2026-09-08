import os
import re
import json
import subprocess
from typing import Dict, Any, Optional


def probe_video(video_path: str) -> Dict[str, Any]:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        "cpu_name": "Unknown CPU",
        "cpu_threads": os.cpu_count() or 1,
        "gpus": [],
        "ram_gb": 0.0
    }

    # CPU Name
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    info["cpu_name"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    # RAM
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemTotal" in line:
                    kb = float(line.split()[1])
                    info["ram_gb"] = round(kb / (1024 * 1024), 1)
                    break
    except Exception:
        pass

    # GPUs
    try:
        from .backend_bridge import VideoUpscalerBackend
        backend = VideoUpscalerBackend()
        info["gpus"] = backend.get_gpu_devices()
    except Exception as e:
        info["gpu_error"] = str(e)

    return info
