"""
Video-Upscayl: High-Performance Hardware-Accelerated Video Upscaler
Python frontend with native C++ Vulkan/AVX-512 backend and Hybrid GPU+CPU execution.
"""

from .backend_bridge import VideoUpscalerBackend, UpscalerSession, DeviceType
from .models import list_available_models, get_model_info, ensure_model_files
from .benchmark import run_hardware_benchmark, auto_select_device
from .pipeline import VideoUpscalePipeline
from .utils import probe_video, get_hardware_info

__version__ = "1.0.0"
__all__ = [
    "VideoUpscalerBackend",
    "UpscalerSession",
    "DeviceType",
    "list_available_models",
    "get_model_info",
    "ensure_model_files",
    "run_hardware_benchmark",
    "auto_select_device",
    "VideoUpscalePipeline",
    "probe_video",
    "get_hardware_info",
]
