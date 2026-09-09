import os
import sys
import urllib.request
from typing import Dict, Any, Optional, List
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

BASE_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "realesr-animevideov3-x2": {
        "name": "realesr-animevideov3-x2",
        "scale": 2,
        "type": "anime_video",
        "description": "Ultra-fast anime & cartoon video upscaler (2x)",
        "bin_name": "realesr-animevideov3-x2.bin",
        "param_name": "realesr-animevideov3-x2.param",
        "bin_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth",
        "ncnn_zip_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    },
    "realesr-animevideov3-x3": {
        "name": "realesr-animevideov3-x3",
        "scale": 3,
        "type": "anime_video",
        "description": "Ultra-fast anime & cartoon video upscaler (3x)",
        "bin_name": "realesr-animevideov3-x3.bin",
        "param_name": "realesr-animevideov3-x3.param",
        "ncnn_zip_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    },
    "realesr-animevideov3-x4": {
        "name": "realesr-animevideov3-x4",
        "scale": 4,
        "type": "anime_video",
        "description": "Ultra-fast anime & cartoon video upscaler (4x)",
        "bin_name": "realesr-animevideov3-x4.bin",
        "param_name": "realesr-animevideov3-x4.param",
        "ncnn_zip_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    },
    "realesrgan-x4plus": {
        "name": "realesrgan-x4plus",
        "scale": 4,
        "type": "general",
        "description": "High-fidelity realistic photo & live action video upscaler (4x)",
        "bin_name": "realesrgan-x4plus.bin",
        "param_name": "realesrgan-x4plus.param",
        "ncnn_zip_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    },
    "realesrgan-x4plus-anime": {
        "name": "realesrgan-x4plus-anime",
        "scale": 4,
        "type": "anime_art",
        "description": "High-fidelity anime illustration upscaler (4x)",
        "bin_name": "realesrgan-x4plus-anime.bin",
        "param_name": "realesrgan-x4plus-anime.param",
        "ncnn_zip_url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    },
    "4x-UltraSharp": {
        "name": "4x-UltraSharp",
        "scale": 4,
        "tile_pad": 10,
        "type": "extreme_detail",
        "description": "State-of-the-art detail & texture upscaler (4x) - Pushes micro-detail & sharpness to the limit",
        "bin_name": "4x-UltraSharp.bin",
        "param_name": "4x-UltraSharp.param",
        "bin_url": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/NCNN/4x-UltraSharp-fp16.bin",
        "param_url": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/NCNN/4x-UltraSharp-fp16.param"
    },

    # --- Real-CUGAN Models (Bilibili AI Lab) ---
    "realcugan-se-x2": {
        "name": "realcugan-se-x2",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video",
        "description": "State-of-the-art anime & cartoon video upscaler (Real-CUGAN 2x Standard, Bilibili AI Lab)",
        "bin_name": "realcugan-se-x2.bin",
        "param_name": "realcugan-se-x2.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up2x-no-denoise.bin",
        "zip_param_path": "models-se/up2x-no-denoise.param"
    },
    "realcugan-se-x2-denoise3x": {
        "name": "realcugan-se-x2-denoise3x",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video",
        "description": "Real-CUGAN 2x with heavy noise & compression artifact reduction (Bilibili AI Lab)",
        "bin_name": "realcugan-se-x2-denoise3x.bin",
        "param_name": "realcugan-se-x2-denoise3x.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up2x-denoise3x.bin",
        "zip_param_path": "models-se/up2x-denoise3x.param"
    },
    "realcugan-se-x2-conservative": {
        "name": "realcugan-se-x2-conservative",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video",
        "description": "Real-CUGAN 2x conservative model preserving subtle textures & line weight (Bilibili AI Lab)",
        "bin_name": "realcugan-se-x2-conservative.bin",
        "param_name": "realcugan-se-x2-conservative.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up2x-conservative.bin",
        "zip_param_path": "models-se/up2x-conservative.param"
    },
    "realcugan-se-x3": {
        "name": "realcugan-se-x3",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video",
        "description": "State-of-the-art anime & cartoon video upscaler (Real-CUGAN 3x Standard, Bilibili AI Lab)",
        "bin_name": "realcugan-se-x3.bin",
        "param_name": "realcugan-se-x3.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up3x-no-denoise.bin",
        "zip_param_path": "models-se/up3x-no-denoise.param"
    },
    "realcugan-se-x3-denoise3x": {
        "name": "realcugan-se-x3-denoise3x",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video",
        "description": "Real-CUGAN 3x with heavy noise & compression artifact reduction (Bilibili AI Lab)",
        "bin_name": "realcugan-se-x3-denoise3x.bin",
        "param_name": "realcugan-se-x3-denoise3x.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up3x-denoise3x.bin",
        "zip_param_path": "models-se/up3x-denoise3x.param"
    },
    "realcugan-se-x3-conservative": {
        "name": "realcugan-se-x3-conservative",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video",
        "description": "Real-CUGAN 3x conservative model preserving subtle textures & line weight (Bilibili AI Lab)",
        "bin_name": "realcugan-se-x3-conservative.bin",
        "param_name": "realcugan-se-x3-conservative.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-se/up3x-conservative.bin",
        "zip_param_path": "models-se/up3x-conservative.param"
    },
    "realcugan-pro-x2": {
        "name": "realcugan-pro-x2",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video_pro",
        "description": "Professional high-detail anime video upscaler (Real-CUGAN 2x Pro, Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x2.bin",
        "param_name": "realcugan-pro-x2.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up2x-no-denoise.bin",
        "zip_param_path": "models-pro/up2x-no-denoise.param"
    },
    "realcugan-pro-x2-denoise3x": {
        "name": "realcugan-pro-x2-denoise3x",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video_pro",
        "description": "Professional Real-CUGAN 2x Pro with heavy noise reduction (Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x2-denoise3x.bin",
        "param_name": "realcugan-pro-x2-denoise3x.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up2x-denoise3x.bin",
        "zip_param_path": "models-pro/up2x-denoise3x.param"
    },
    "realcugan-pro-x2-conservative": {
        "name": "realcugan-pro-x2-conservative",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video_pro",
        "description": "Professional Real-CUGAN 2x Pro conservative texture preserver (Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x2-conservative.bin",
        "param_name": "realcugan-pro-x2-conservative.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up2x-conservative.bin",
        "zip_param_path": "models-pro/up2x-conservative.param"
    },
    "realcugan-pro-x3": {
        "name": "realcugan-pro-x3",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video_pro",
        "description": "Professional high-detail anime video upscaler (Real-CUGAN 3x Pro, Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x3.bin",
        "param_name": "realcugan-pro-x3.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up3x-no-denoise.bin",
        "zip_param_path": "models-pro/up3x-no-denoise.param"
    },
    "realcugan-pro-x3-denoise3x": {
        "name": "realcugan-pro-x3-denoise3x",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video_pro",
        "description": "Professional Real-CUGAN 3x Pro with heavy noise reduction (Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x3-denoise3x.bin",
        "param_name": "realcugan-pro-x3-denoise3x.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up3x-denoise3x.bin",
        "zip_param_path": "models-pro/up3x-denoise3x.param"
    },
    "realcugan-pro-x3-conservative": {
        "name": "realcugan-pro-x3-conservative",
        "scale": 3,
        "tile_pad": 14,
        "type": "anime_video_pro",
        "description": "Professional Real-CUGAN 3x Pro conservative texture preserver (Bilibili AI Lab)",
        "bin_name": "realcugan-pro-x3-conservative.bin",
        "param_name": "realcugan-pro-x3-conservative.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-pro/up3x-conservative.bin",
        "zip_param_path": "models-pro/up3x-conservative.param"
    },
    "realcugan-nose-x2": {
        "name": "realcugan-nose-x2",
        "scale": 2,
        "tile_pad": 18,
        "type": "anime_video_fast",
        "description": "High-speed anime video upscaler without Squeeze-and-Excitation (Real-CUGAN No-SE 2x, Bilibili AI Lab)",
        "bin_name": "realcugan-nose-x2.bin",
        "param_name": "realcugan-nose-x2.param",
        "ncnn_zip_url": "https://github.com/nihui/realcugan-ncnn-vulkan/releases/download/20220728/realcugan-ncnn-vulkan-20220728-ubuntu.zip",
        "zip_bin_path": "models-nose/up2x-no-denoise.bin",
        "zip_param_path": "models-nose/up2x-no-denoise.param"
    }
}


MODEL_ALIASES: Dict[str, str] = {
    # Real-CUGAN aliases
    "realcugan": "realcugan-se-x2",
    "cugan": "realcugan-se-x2",
    "real-cugan": "realcugan-se-x2",
    "realcugan-2x": "realcugan-se-x2",
    "realcugan-x2": "realcugan-se-x2",
    "realcugan2x": "realcugan-se-x2",
    "cugan-2x": "realcugan-se-x2",
    "cugan2x": "realcugan-se-x2",
    "cugan-x2": "realcugan-se-x2",
    "real-cugan-2x": "realcugan-se-x2",
    "real-cugan-x2": "realcugan-se-x2",
    "realcugan-se": "realcugan-se-x2",
    "real-cugan-se": "realcugan-se-x2",
    "real-cugan-se-2x": "realcugan-se-x2",
    "real-cugan-se-x2": "realcugan-se-x2",

    "realcugan-3x": "realcugan-se-x3",
    "realcugan-x3": "realcugan-se-x3",
    "realcugan3x": "realcugan-se-x3",
    "cugan-3x": "realcugan-se-x3",
    "cugan3x": "realcugan-se-x3",
    "cugan-x3": "realcugan-se-x3",
    "real-cugan-3x": "realcugan-se-x3",
    "real-cugan-x3": "realcugan-se-x3",
    "real-cugan-se-3x": "realcugan-se-x3",
    "real-cugan-se-x3": "realcugan-se-x3",

    "realcugan-pro": "realcugan-pro-x2",
    "cugan-pro": "realcugan-pro-x2",
    "cugan-pro-2x": "realcugan-pro-x2",
    "realcugan-pro-2x": "realcugan-pro-x2",
    "real-cugan-pro-2x": "realcugan-pro-x2",
    "real-cugan-pro-x2": "realcugan-pro-x2",

    "cugan-pro-3x": "realcugan-pro-x3",
    "realcugan-pro-3x": "realcugan-pro-x3",
    "real-cugan-pro-3x": "realcugan-pro-x3",
    "real-cugan-pro-x3": "realcugan-pro-x3",

    "realcugan-nose": "realcugan-nose-x2",
    "cugan-nose": "realcugan-nose-x2",
    "real-cugan-nose": "realcugan-nose-x2",

    # animevideov3 aliases
    "animevidv3-2x": "realesr-animevideov3-x2",
    "animevidv3-x2": "realesr-animevideov3-x2",
    "animevideov3-2x": "realesr-animevideov3-x2",
    "animevideov3-x2": "realesr-animevideov3-x2",
    "animevid-2x": "realesr-animevideov3-x2",
    "anime-2x": "realesr-animevideov3-x2",
    "anime2x": "realesr-animevideov3-x2",
    "realesr-anime-2x": "realesr-animevideov3-x2",

    "animevidv3-3x": "realesr-animevideov3-x3",
    "animevidv3-x3": "realesr-animevideov3-x3",
    "animevideov3-3x": "realesr-animevideov3-x3",
    "animevideov3-x3": "realesr-animevideov3-x3",
    "animevid-3x": "realesr-animevideov3-x3",
    "anime-3x": "realesr-animevideov3-x3",
    "anime3x": "realesr-animevideov3-x3",
    "realesr-anime-3x": "realesr-animevideov3-x3",

    "animevidv3-4x": "realesr-animevideov3-x4",
    "animevidv3-x4": "realesr-animevideov3-x4",
    "animevideov3-4x": "realesr-animevideov3-x4",
    "animevideov3-x4": "realesr-animevideov3-x4",
    "animevid-4x": "realesr-animevideov3-x4",
    "anime-4x": "realesr-animevideov3-x4",
    "anime4x": "realesr-animevideov3-x4",
    "realesr-anime-4x": "realesr-animevideov3-x4",

    # ultrasharp aliases
    "ultrasharp": "4x-UltraSharp",
    "ultra-sharp": "4x-UltraSharp",
    "4x-ultrasharp": "4x-UltraSharp",
    "4xultrasharp": "4x-UltraSharp",

    # x4plus aliases
    "x4plus": "realesrgan-x4plus",
    "realesr-x4plus": "realesrgan-x4plus",
    "x4plus-anime": "realesrgan-x4plus-anime",
    "realesr-x4plus-anime": "realesrgan-x4plus-anime",
}


def list_available_models() -> List[Dict[str, Any]]:
    return list(MODEL_REGISTRY.values())


def get_model_info(model_identifier: Optional[str] = None, scale: Optional[int] = None) -> Dict[str, Any]:
    if model_identifier:
        # 1. Exact match
        if model_identifier in MODEL_REGISTRY:
            return MODEL_REGISTRY[model_identifier]

        # 2. Case-insensitive exact match
        for name, info in MODEL_REGISTRY.items():
            if name.lower() == model_identifier.lower():
                return info

        # 3. Known alias match
        norm = model_identifier.lower().replace("_", "-").strip()
        if norm in MODEL_ALIASES:
            return MODEL_REGISTRY[MODEL_ALIASES[norm]]

        # 4. Fuzzy substring match (with or without hyphens)
        clean_id = norm.replace("-", "")
        for name, info in MODEL_REGISTRY.items():
            clean_name = name.lower().replace("-", "")
            if clean_id in clean_name or clean_name in clean_id:
                return info

    # 5. Match by scale if model_identifier is not given or not matched
    if scale is not None:
        for m in MODEL_REGISTRY.values():
            if m["scale"] == scale:
                return m

    available = ", ".join(MODEL_REGISTRY.keys())
    raise ValueError(f"Unknown model '{model_identifier}'. Available models: {available}")


def get_user_cache_model_dir() -> str:
    """Returns a persistent, user-writable directory for downloading models."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Video-Upscayl", "models")
    return os.path.expanduser("~/.cache/video-upscayl/models")


def get_candidate_model_dirs(explicit_dir: Optional[str] = None) -> List[str]:
    """Returns all directories where model weights might be located, in priority order."""
    dirs: List[str] = []
    if explicit_dir:
        dirs.append(os.path.abspath(explicit_dir))

    # Base development / source dir
    dirs.append(BASE_MODELS_DIR)

    # PyInstaller bundled location
    if hasattr(sys, "_MEIPASS"):
        dirs.append(os.path.join(getattr(sys, "_MEIPASS"), "models"))

    # AppImage bundled location
    appdir = os.environ.get("APPDIR")
    if appdir:
        dirs.append(os.path.join(appdir, "models"))
        dirs.append(os.path.join(appdir, "usr", "share", "video-upscayl", "models"))

    # Next to frozen executable
    if getattr(sys, "frozen", False) and sys.executable:
        dirs.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "models"))

    # Persistent user cache
    dirs.append(get_user_cache_model_dir())

    # Return deduplicated list
    seen = set()
    result = []
    for d in dirs:
        norm = os.path.normpath(d)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def get_writable_model_dir(preferred_dir: Optional[str] = None) -> str:
    """Finds or creates a writable directory to save downloaded models."""
    candidates = []
    if preferred_dir:
        candidates.append(preferred_dir)
    else:
        # If not running in a frozen/appimage bundle, preferred is BASE_MODELS_DIR
        is_bundle = hasattr(sys, "_MEIPASS") or bool(os.environ.get("APPDIR")) or getattr(sys, "frozen", False)
        if not is_bundle:
            candidates.append(BASE_MODELS_DIR)

    candidates.append(get_user_cache_model_dir())

    for c in candidates:
        try:
            os.makedirs(c, exist_ok=True)
            test_file = os.path.join(c, ".write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return c
        except (OSError, PermissionError):
            continue

    import tempfile
    fallback = os.path.join(tempfile.gettempdir(), "video_upscayl_models")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def ensure_model_files(model_info: Dict[str, Any], models_dir: Optional[str] = None) -> tuple[str, str]:
    """
    Ensures that the model's .bin and .param files exist in models_dir or candidate dirs.
    Downloads them if missing.
    Returns (bin_path, param_path).
    """
    bin_name = model_info["bin_name"]
    param_name = model_info["param_name"]

    # 1. Search candidate directories for existing files
    for candidate_dir in get_candidate_model_dirs(models_dir):
        bin_candidate = os.path.join(candidate_dir, bin_name)
        param_candidate = os.path.join(candidate_dir, param_name)
        if os.path.isfile(bin_candidate) and os.path.isfile(param_candidate):
            return bin_candidate, param_candidate

    # 2. Not found, determine writable directory to download into
    target_dir = get_writable_model_dir(models_dir)
    bin_path = os.path.join(target_dir, bin_name)
    param_path = os.path.join(target_dir, param_name)

    # Direct URL download support
    if "bin_url" in model_info and "param_url" in model_info:
        print(f"Downloading model '{model_info['name']}' from Hugging Face...")
        import urllib.request
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn()
        ) as progress:
            task_param = progress.add_task("Downloading architecture", total=None)
            urllib.request.urlretrieve(model_info["param_url"], param_path)
            progress.update(task_param, completed=100, total=100)

            task_bin = progress.add_task("Downloading weights", total=None)
            def reporthook(count, block_size, total_size):
                if total_size > 0:
                    progress.update(task_bin, total=total_size, completed=count * block_size)
            urllib.request.urlretrieve(model_info["bin_url"], bin_path, reporthook=reporthook)

        if os.path.exists(bin_path) and os.path.exists(param_path):
            return bin_path, param_path

    # If missing, download release zip and extract
    zip_url = model_info.get("ncnn_zip_url")
    if not zip_url:
        raise FileNotFoundError(f"Model files for {model_info['name']} not found and no download URL available.")

    print(f"Downloading model '{model_info['name']}' from {zip_url}...")
    temp_zip = os.path.join(target_dir, "temp_models.zip")

    try:
        import urllib.request
        import zipfile

        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn()
        ) as progress:
            task = progress.add_task("Downloading", total=None)

            def reporthook(count, block_size, total_size):
                if total_size > 0:
                    progress.update(task, total=total_size, completed=count * block_size)

            urllib.request.urlretrieve(zip_url, temp_zip, reporthook=reporthook)

        with zipfile.ZipFile(temp_zip, "r") as z:
            zip_bin_path = model_info.get("zip_bin_path")
            zip_param_path = model_info.get("zip_param_path")

            for member in z.infolist():
                if zip_bin_path and member.filename.endswith(zip_bin_path):
                    target = os.path.join(target_dir, model_info["bin_name"])
                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                elif zip_param_path and member.filename.endswith(zip_param_path):
                    target = os.path.join(target_dir, model_info["param_name"])
                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                else:
                    filename = os.path.basename(member.filename)
                    if filename in (model_info["bin_name"], model_info["param_name"]):
                        target = os.path.join(target_dir, filename)
                        with z.open(member) as src, open(target, "wb") as dst:
                            dst.write(src.read())

    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

    if not os.path.exists(bin_path) or not os.path.exists(param_path):
        raise FileNotFoundError(f"Failed to extract {model_info['bin_name']} and {model_info['param_name']}")

    return bin_path, param_path
