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
    # 1. Explicit environment variable
    env_path = os.environ.get("LIBVIDEOUPSCALER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. Determine platform library extensions
    if sys.platform == "win32":
        lib_names = ["videoupscaler.dll", "libvideoupscaler.dll"]
    elif sys.platform == "darwin":
        lib_names = ["libvideoupscaler.dylib", "videoupscaler.dylib"]
    else:
        lib_names = ["libvideoupscaler.so", "videoupscaler.so"]

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    search_dirs = [
        os.path.join(base_dir, "build"),
        os.path.join(base_dir, "build", "Release"),
        os.path.join(base_dir, "build", "Debug"),
        os.path.join(base_dir, "bin"),
        base_dir,
        os.path.dirname(__file__),
    ]

    # PyInstaller bundled location
    if hasattr(sys, "_MEIPASS"):
        meipass = getattr(sys, "_MEIPASS")
        search_dirs.insert(0, meipass)
        search_dirs.insert(1, os.path.join(meipass, "lib"))
        search_dirs.insert(2, os.path.join(meipass, "bin"))

    # Frozen executable location
    if getattr(sys, "frozen", False) and sys.executable:
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        search_dirs.insert(0, exe_dir)
        search_dirs.insert(1, os.path.join(exe_dir, "lib"))
        search_dirs.insert(2, os.path.join(exe_dir, "bin"))

    # Linux AppImage root environment
    appdir = os.environ.get("APPDIR")
    if appdir:
        search_dirs.insert(0, os.path.join(appdir, "usr", "lib"))
        search_dirs.insert(1, os.path.join(appdir, "lib"))
        search_dirs.insert(2, os.path.join(appdir, "usr", "bin"))
        search_dirs.insert(3, appdir)

    candidates = []
    for s_dir in search_dirs:
        for name in lib_names:
            candidate = os.path.join(s_dir, name)
            candidates.append(candidate)
            if os.path.exists(candidate):
                return candidate

    raise FileNotFoundError(
        f"Native backend library ({', '.join(lib_names)}) could not be found.\n"
        f"Please run scripts/build_backend.sh (on Linux/macOS) or scripts/build_windows.bat (on Windows).\n"
        f"Checked locations:\n" + "\n".join(f" - {c}" for c in candidates)
    )


class VideoUpscalerBackend:
    def __init__(self, lib_path: Optional[str] = None):
        if lib_path is None:
            lib_path = find_library_path()
        self.lib_path = os.path.abspath(lib_path)

        # On Windows, register directory to DLL search path for dependencies (Vulkan, OpenMP, etc.)
        if sys.platform == "win32":
            dll_dir = os.path.dirname(self.lib_path)
            if hasattr(os, "add_dll_directory") and os.path.exists(dll_dir):
                try:
                    os.add_dll_directory(dll_dir)
                except Exception:
                    pass
            vulkan_sdk = os.environ.get("VULKAN_SDK")
            if vulkan_sdk and hasattr(os, "add_dll_directory"):
                vk_bin = os.path.join(vulkan_sdk, "bin")
                if os.path.exists(vk_bin):
                    try:
                        os.add_dll_directory(vk_bin)
                    except Exception:
                        pass

        self._lib = ctypes.CDLL(self.lib_path)
        self._setup_c_signatures()

    def _setup_c_signatures(self):
        # int videoupscaler_get_gpu_count();
        self._lib.videoupscaler_get_gpu_count.argtypes = []
        self._lib.videoupscaler_get_gpu_count.restype = ctypes.c_int

        # const char* videoupscaler_get_gpu_name(int device_index);
        self._lib.videoupscaler_get_gpu_name.argtypes = [ctypes.c_int]
        self._lib.videoupscaler_get_gpu_name.restype = ctypes.c_char_p

        # const char* videoupscaler_get_gpu_vendor(int device_index);
        if hasattr(self._lib, "videoupscaler_get_gpu_vendor"):
            self._lib.videoupscaler_get_gpu_vendor.argtypes = [ctypes.c_int]
            self._lib.videoupscaler_get_gpu_vendor.restype = ctypes.c_char_p

        # int videoupscaler_get_gpu_type(int device_index);
        if hasattr(self._lib, "videoupscaler_get_gpu_type"):
            self._lib.videoupscaler_get_gpu_type.argtypes = [ctypes.c_int]
            self._lib.videoupscaler_get_gpu_type.restype = ctypes.c_int

        # const char* videoupscaler_get_cpu_simd_info();
        if hasattr(self._lib, "videoupscaler_get_cpu_simd_info"):
            self._lib.videoupscaler_get_cpu_simd_info.argtypes = []
            self._lib.videoupscaler_get_cpu_simd_info.restype = ctypes.c_char_p

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

        # videoupscaler_t* videoupscaler_create_with_gpu(...)
        if hasattr(self._lib, "videoupscaler_create_with_gpu"):
            self._lib.videoupscaler_create_with_gpu.argtypes = [
                ctypes.c_char_p,  # model_path
                ctypes.c_char_p,  # param_path
                ctypes.c_int,     # scale
                ctypes.c_int,     # device_type
                ctypes.c_int,     # tile_size
                ctypes.c_int,     # tile_pad
                ctypes.c_int,     # num_threads
                ctypes.c_int      # gpu_device_id
            ]
            self._lib.videoupscaler_create_with_gpu.restype = ctypes.c_void_p

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

        # int videoupscaler_benchmark_with_gpu(...)
        if hasattr(self._lib, "videoupscaler_benchmark_with_gpu"):
            self._lib.videoupscaler_benchmark_with_gpu.argtypes = [
                ctypes.c_char_p,  # model_path
                ctypes.c_char_p,  # param_path
                ctypes.c_int,     # scale
                ctypes.c_int,     # width
                ctypes.c_int,     # height
                ctypes.c_int,     # num_frames
                ctypes.c_int,     # gpu_device_id
                ctypes.POINTER(ctypes.c_double),  # out_gpu_fps
                ctypes.POINTER(ctypes.c_double),  # out_cpu_fps
                ctypes.POINTER(ctypes.c_double)   # out_hybrid_fps
            ]
            self._lib.videoupscaler_benchmark_with_gpu.restype = ctypes.c_int

        # void videoupscaler_destroy(videoupscaler_t* handle);
        self._lib.videoupscaler_destroy.argtypes = [ctypes.c_void_p]
        self._lib.videoupscaler_destroy.restype = None

    def get_cpu_simd_info(self) -> str:
        """Returns detected runtime vector extensions (e.g. AVX-512, AVX2 + FMA, AVX, SSE4.2, ARM NEON)."""
        if hasattr(self._lib, "videoupscaler_get_cpu_simd_info"):
            res = self._lib.videoupscaler_get_cpu_simd_info()
            if res:
                return res.decode("utf-8")
        return "Standard SIMD"

    def get_gpu_devices(self) -> List[Dict[str, Any]]:
        """Returns list of all available GPU devices with vendor and type details."""
        count = self._lib.videoupscaler_get_gpu_count()
        devices = []
        for i in range(count):
            name_bytes = self._lib.videoupscaler_get_gpu_name(i)
            name = name_bytes.decode("utf-8") if name_bytes else f"GPU {i}"

            vendor = "Unknown"
            if hasattr(self._lib, "videoupscaler_get_gpu_vendor"):
                v_bytes = self._lib.videoupscaler_get_gpu_vendor(i)
                if v_bytes:
                    vendor = v_bytes.decode("utf-8")

            gtype = -1
            if hasattr(self._lib, "videoupscaler_get_gpu_type"):
                gtype = self._lib.videoupscaler_get_gpu_type(i)

            type_names = {0: "Discrete", 1: "Integrated", 2: "Virtual", 3: "CPU"}
            type_str = type_names.get(gtype, "Unknown")

            devices.append({
                "id": i,
                "name": name,
                "vendor": vendor,
                "type": type_str,
                "is_discrete": (gtype == 0),
            })
        return devices

    def benchmark(
        self,
        model_path: str,
        param_path: str,
        scale: int,
        width: int = 512,
        height: int = 288,
        num_frames: int = 5,
        gpu_id: int = -1
    ) -> Dict[str, float]:
        gpu_fps = ctypes.c_double(0.0)
        cpu_fps = ctypes.c_double(0.0)
        hybrid_fps = ctypes.c_double(0.0)

        if hasattr(self._lib, "videoupscaler_benchmark_with_gpu"):
            ret = self._lib.videoupscaler_benchmark_with_gpu(
                model_path.encode("utf-8"),
                param_path.encode("utf-8"),
                scale,
                width,
                height,
                num_frames,
                gpu_id,
                ctypes.byref(gpu_fps),
                ctypes.byref(cpu_fps),
                ctypes.byref(hybrid_fps)
            )
        else:
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
        num_threads: int = 0,
        gpu_id: int = -1
    ) -> "UpscalerSession":
        return UpscalerSession(
            backend=self,
            model_path=model_path,
            param_path=param_path,
            scale=scale,
            device_type=device_type,
            tile_size=tile_size,
            tile_pad=tile_pad,
            num_threads=num_threads,
            gpu_id=gpu_id
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
        num_threads: int = 0,
        gpu_id: int = -1
    ):
        self.backend = backend
        self.model_path = model_path
        self.param_path = param_path
        self.scale = scale
        self.device_type = device_type
        self.tile_size = tile_size
        self.tile_pad = tile_pad
        self.num_threads = num_threads
        self.gpu_id = gpu_id

        if hasattr(self.backend._lib, "videoupscaler_create_with_gpu"):
            handle = self.backend._lib.videoupscaler_create_with_gpu(
                model_path.encode("utf-8"),
                param_path.encode("utf-8"),
                scale,
                int(device_type),
                tile_size,
                tile_pad,
                num_threads,
                gpu_id
            )
        else:
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
