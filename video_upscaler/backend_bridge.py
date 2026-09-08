import os
import sys
import ctypes
from enum import IntEnum
from typing import Optional, Tuple, List, Dict, Any
import numpy as np


class DeviceType(IntEnum):
    AUTO = 0
    GPU = 1
    CPU = 2
    HYBRID = 3


def find_library_path() -> str:
    # 1. Environment variable
    env_path = os.environ.get("LIBVIDEOUPSCALER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. Project build directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(base_dir, "build", "libvideoupscaler.so"),
        os.path.join(base_dir, "libvideoupscaler.so"),
        os.path.join(os.path.dirname(__file__), "libvideoupscaler.so"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    raise FileNotFoundError(
        f"libvideoupscaler.so could not be found. Please run scripts/build_backend.sh first. Checked: {candidates}"
    )


class VideoUpscalerBackend:
    def __init__(self, lib_path: Optional[str] = None):
        if lib_path is None:
            lib_path = find_library_path()
        self.lib_path = lib_path
        self._lib = ctypes.CDLL(self.lib_path)
        self._setup_c_signatures()

    def _setup_c_signatures(self):
        # int videoupscaler_get_gpu_count();
        self._lib.videoupscaler_get_gpu_count.argtypes = []
        self._lib.videoupscaler_get_gpu_count.restype = ctypes.c_int

        # const char* videoupscaler_get_gpu_name(int device_index);
        self._lib.videoupscaler_get_gpu_name.argtypes = [ctypes.c_int]
        self._lib.videoupscaler_get_gpu_name.restype = ctypes.c_char_p

        # videoupscaler_t* videoupscaler_create(...)
        self._lib.videoupscaler_create.argtypes = [
            ctypes.c_char_p,  # model_path
            ctypes.c_char_p,  # param_path
            ctypes.c_int,     # scale
            ctypes.c_int,     # device_type
            ctypes.c_int,     # tile_size
            ctypes.c_int,     # tile_pad
            ctypes.c_int      # num_threads
        ]
        self._lib.videoupscaler_create.restype = ctypes.c_void_p

        # int videoupscaler_process_frame(...)
        self._lib.videoupscaler_process_frame.argtypes = [
            ctypes.c_void_p,  # handle
            ctypes.POINTER(ctypes.c_uint8),  # in_rgb
            ctypes.c_int,     # in_w
            ctypes.c_int,     # in_h
            ctypes.POINTER(ctypes.c_uint8)   # out_rgb
        ]
        self._lib.videoupscaler_process_frame.restype = ctypes.c_int

        # int videoupscaler_benchmark(...)
        self._lib.videoupscaler_benchmark.argtypes = [
            ctypes.c_char_p,  # model_path
            ctypes.c_char_p,  # param_path
            ctypes.c_int,     # scale
            ctypes.c_int,     # width
            ctypes.c_int,     # height
            ctypes.c_int,     # num_frames
            ctypes.POINTER(ctypes.c_double),  # out_gpu_fps
            ctypes.POINTER(ctypes.c_double),  # out_cpu_fps
            ctypes.POINTER(ctypes.c_double)   # out_hybrid_fps
        ]
        self._lib.videoupscaler_benchmark.restype = ctypes.c_int

        # void videoupscaler_destroy(videoupscaler_t* handle);
        self._lib.videoupscaler_destroy.argtypes = [ctypes.c_void_p]
        self._lib.videoupscaler_destroy.restype = None

    def get_gpu_devices(self) -> List[Dict[str, Any]]:
        count = self._lib.videoupscaler_get_gpu_count()
        devices = []
        for i in range(count):
            name_bytes = self._lib.videoupscaler_get_gpu_name(i)
            name = name_bytes.decode("utf-8") if name_bytes else f"GPU {i}"
            devices.append({"id": i, "name": name})
        return devices

    def benchmark(
        self,
        model_path: str,
        param_path: str,
        scale: int,
        width: int = 512,
        height: int = 288,
        num_frames: int = 5
    ) -> Dict[str, float]:
        gpu_fps = ctypes.c_double(0.0)
        cpu_fps = ctypes.c_double(0.0)
        hybrid_fps = ctypes.c_double(0.0)

        ret = self._lib.videoupscaler_benchmark(
            model_path.encode("utf-8"),
            param_path.encode("utf-8"),
            scale,
            width,
            height,
            num_frames,
            ctypes.byref(gpu_fps),
            ctypes.byref(cpu_fps),
            ctypes.byref(hybrid_fps)
        )
        if ret != 0:
            raise RuntimeError(f"videoupscaler_benchmark failed with code {ret}")

        return {
            "gpu_fps": float(gpu_fps.value),
            "cpu_fps": float(cpu_fps.value),
            "hybrid_fps": float(hybrid_fps.value),
        }

    def create_instance(
        self,
        model_path: str,
        param_path: str,
        scale: int,
        device_type: DeviceType = DeviceType.GPU,
        tile_size: int = 256,
        tile_pad: int = 10,
        num_threads: int = 0
    ) -> "UpscalerSession":
        return UpscalerSession(
            backend=self,
            model_path=model_path,
            param_path=param_path,
            scale=scale,
            device_type=device_type,
            tile_size=tile_size,
            tile_pad=tile_pad,
            num_threads=num_threads
        )


class UpscalerSession:
    def __init__(
        self,
        backend: VideoUpscalerBackend,
        model_path: str,
        param_path: str,
        scale: int,
        device_type: DeviceType,
        tile_size: int = 256,
        tile_pad: int = 10,
        num_threads: int = 0
    ):
        self.backend = backend
        self.model_path = model_path
        self.param_path = param_path
        self.scale = scale
        self.device_type = device_type
        self.tile_size = tile_size
        self.tile_pad = tile_pad
        self.num_threads = num_threads

        handle = self.backend._lib.videoupscaler_create(
            model_path.encode("utf-8"),
            param_path.encode("utf-8"),
            scale,
            int(device_type),
            tile_size,
            tile_pad,
            num_threads
        )
        if not handle:
            raise RuntimeError(
                f"Failed to create videoupscaler instance for model '{model_path}' on device {device_type.name}"
            )
        self._handle = handle

    def process_frame(self, in_frame: np.ndarray) -> np.ndarray:
        """
        Upscales an RGB24 frame uint8 of shape (H, W, 3).
        Returns an upscaled RGB24 frame uint8 of shape (H*scale, W*scale, 3).
        """
        if not in_frame.flags["C_CONTIGUOUS"]:
            in_frame = np.ascontiguousarray(in_frame)

        h, w, c = in_frame.shape
        if c != 3 or in_frame.dtype != np.uint8:
            raise ValueError(f"Input frame must be RGB24 uint8 (H, W, 3), got shape {in_frame.shape} dtype {in_frame.dtype}")

        out_h = h * self.scale
        out_w = w * self.scale
        out_frame = np.empty((out_h, out_w, 3), dtype=np.uint8)

        in_ptr = in_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        out_ptr = out_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

        ret = self.backend._lib.videoupscaler_process_frame(
            self._handle,
            in_ptr,
            w,
            h,
            out_ptr
        )
        if ret != 0:
            raise RuntimeError(f"videoupscaler_process_frame failed with code {ret}")

        return out_frame

    def process_frame_bytes(self, in_bytes: bytes, width: int, height: int) -> bytes:
        """
        Processes raw bytes directly without numpy intermediate allocation.
        """
        in_arr = np.frombuffer(in_bytes, dtype=np.uint8).reshape((height, width, 3))
        out_arr = self.process_frame(in_arr)
        return out_arr.tobytes()

    def close(self):
        if hasattr(self, "_handle") and self._handle:
            self.backend._lib.videoupscaler_destroy(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
