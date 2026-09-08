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
        "type": "extreme_detail",
        "description": "State-of-the-art detail & texture upscaler (4x) - Pushes micro-detail & sharpness to the limit",
        "bin_name": "4x-UltraSharp.bin",
        "param_name": "4x-UltraSharp.param",
        "bin_url": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/NCNN/4x-UltraSharp-fp16.bin",
        "param_url": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/NCNN/4x-UltraSharp-fp16.param"
    }
}


def list_available_models() -> List[Dict[str, Any]]:
    return list(MODEL_REGISTRY.values())


def get_model_info(model_identifier: str, scale: Optional[int] = None) -> Dict[str, Any]:
    # Exact match
    if model_identifier in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_identifier]

    # Match by scale
    if scale is not None:
        for m in MODEL_REGISTRY.values():
            if m["scale"] == scale:
                return m

    # Fuzzy match
    for name, info in MODEL_REGISTRY.items():
        if model_identifier.lower() in name.lower():
            return info

    available = ", ".join(MODEL_REGISTRY.keys())
    raise ValueError(f"Unknown model '{model_identifier}'. Available models: {available}")


def ensure_model_files(model_info: Dict[str, Any], models_dir: Optional[str] = None) -> tuple[str, str]:
    """
    Ensures that the model's .bin and .param files exist in models_dir.
    Downloads them if missing.
    Returns (bin_path, param_path).
    """
    if models_dir is None:
        models_dir = BASE_MODELS_DIR

    os.makedirs(models_dir, exist_ok=True)

    bin_path = os.path.join(models_dir, model_info["bin_name"])
    param_path = os.path.join(models_dir, model_info["param_name"])

    if os.path.exists(bin_path) and os.path.exists(param_path):
        return bin_path, param_path

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
    temp_zip = os.path.join(models_dir, "temp_models.zip")

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
            for member in z.infolist():
                filename = os.path.basename(member.filename)
                if filename in (model_info["bin_name"], model_info["param_name"]):
                    target = os.path.join(models_dir, filename)
                    with z.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

    if not os.path.exists(bin_path) or not os.path.exists(param_path):
        raise FileNotFoundError(f"Failed to extract {model_info['bin_name']} and {model_info['param_name']}")

    return bin_path, param_path
