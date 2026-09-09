"""
Video-Upscayl Windows Standalone Packaging Script (PyInstaller)
Creates a completely self-contained, zero-dependency .exe file for Windows users.
Bundles Python runtime, Tkinter GUI, OpenCV, NumPy, FFmpeg/FFprobe,
pre-trained models, and the native C++ Vulkan/SIMD backend.
"""

import os
import sys
import shutil
import argparse
import subprocess
import urllib.request
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")


def ensure_windows_ffmpeg() -> tuple[str, str]:
    """Locates or downloads standalone static FFmpeg/FFprobe binaries for Windows."""
    ffmpeg_name = "ffmpeg.exe"
    ffprobe_name = "ffprobe.exe"

    search_dirs = [
        os.path.join(ROOT_DIR, "bin"),
        os.path.join(ROOT_DIR, "tools"),
        os.path.join(ROOT_DIR, "tools", "ffmpeg", "bin"),
        ROOT_DIR,
    ]
    # Check PATH
    p_ffmpeg = shutil.which("ffmpeg")
    p_ffprobe = shutil.which("ffprobe")
    if p_ffmpeg and p_ffprobe:
        return p_ffmpeg, p_ffprobe

    for s_dir in search_dirs:
        ff_cand = os.path.join(s_dir, ffmpeg_name)
        fp_cand = os.path.join(s_dir, ffprobe_name)
        if os.path.isfile(ff_cand) and os.path.isfile(fp_cand):
            return ff_cand, fp_cand

    # Download portable static release if not found
    print("[INFO] FFmpeg not found locally. Downloading portable static Windows build...")
    os.makedirs(TOOLS_DIR, exist_ok=True)
    zip_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_target = os.path.join(TOOLS_DIR, "ffmpeg.zip")

    try:
        print(f"Downloading from: {zip_url}")
        req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, open(zip_target, "wb") as out:
            shutil.copyfileobj(resp, out)

        print("Extracting ffmpeg.exe and ffprobe.exe...")
        with zipfile.ZipFile(zip_target, "r") as z:
            for member in z.namelist():
                if member.endswith("ffmpeg.exe"):
                    with z.open(member) as src, open(os.path.join(TOOLS_DIR, ffmpeg_name), "wb") as dst:
                        shutil.copyfileobj(src, dst)
                elif member.endswith("ffprobe.exe"):
                    with z.open(member) as src, open(os.path.join(TOOLS_DIR, ffprobe_name), "wb") as dst:
                        shutil.copyfileobj(src, dst)
    finally:
        if os.path.exists(zip_target):
            os.remove(zip_target)

    ffmpeg_bin = os.path.join(TOOLS_DIR, ffmpeg_name)
    ffprobe_bin = os.path.join(TOOLS_DIR, ffprobe_name)
    return ffmpeg_bin, ffprobe_bin


def build_standalone(mode="onefile"):
    print(f"=== Packaging Video-Upscayl for Windows (Mode: {mode}) ===")

    try:
        import PyInstaller
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])

    dist_dir = os.path.join(ROOT_DIR, "dist")
    build_dir = os.path.join(ROOT_DIR, "build_pyinstaller")
    os.makedirs(dist_dir, exist_ok=True)

    # 1. Locate backend DLL
    dll_candidates = [
        os.path.join(ROOT_DIR, "build", "videoupscaler.dll"),
        os.path.join(ROOT_DIR, "build", "libvideoupscaler.dll"),
        os.path.join(ROOT_DIR, "build", "Release", "videoupscaler.dll"),
        os.path.join(ROOT_DIR, "videoupscaler.dll"),
    ]
    dll_path = None
    for c in dll_candidates:
        if os.path.exists(c):
            dll_path = c
            break

    bin_args = []
    if dll_path:
        print(f"[INFO] Bundling native backend: {dll_path}")
        bin_args.extend(["--add-binary", f"{dll_path};."])
    else:
        print("[WARNING] videoupscaler.dll not found. Compiling native backend is recommended.")

    # Locate OpenMP runtime (vcomp140.dll) if present
    for vcomp_candidate in [
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "vcomp140.dll"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "vcomp140.dll"),
    ]:
        if os.path.exists(vcomp_candidate):
            print(f"[INFO] Bundling MSVC OpenMP runtime: {vcomp_candidate}")
            bin_args.extend(["--add-binary", f"{vcomp_candidate};."])
            break

    # 2. Locate / bundle FFmpeg and FFprobe
    try:
        ffmpeg_bin, ffprobe_bin = ensure_windows_ffmpeg()
        if os.path.exists(ffmpeg_bin) and os.path.exists(ffprobe_bin):
            print(f"[INFO] Bundling FFmpeg: {ffmpeg_bin}")
            print(f"[INFO] Bundling FFprobe: {ffprobe_bin}")
            bin_args.extend([
                "--add-binary", f"{ffmpeg_bin};.",
                "--add-binary", f"{ffprobe_bin};.",
            ])
    except Exception as e:
        print(f"[WARNING] Could not bundle FFmpeg automatically: {e}")

    # 3. Locate / bundle models
    data_args = []
    models_dir = os.path.join(ROOT_DIR, "models")
    if os.path.exists(models_dir):
        print(f"[INFO] Bundling pretrained models from: {models_dir}")
        data_args.extend(["--add-data", f"{models_dir};models"])

    # 4. Icon
    icon_args = []
    icon_path = os.path.join(ROOT_DIR, "scripts", "resources", "video-upscayl.ico")
    png_icon = os.path.join(ROOT_DIR, "scripts", "resources", "video-upscayl.png")
    if os.path.exists(icon_path):
        icon_args.extend(["--icon", icon_path])
    elif os.path.exists(png_icon):
        icon_args.extend(["--icon", png_icon])

    mode_flag = "--onefile" if mode == "onefile" else "--onedir"
    exe_name = "Video-Upscayl-Windows-x64" if mode == "onefile" else "Video-Upscayl"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", exe_name,
        "--windowed",                 # No console popup on double click!
        mode_flag,
        "--clean",
        "--noconfirm",
        "--distpath", dist_dir,
        "--workpath", build_dir,
    ] + icon_args + bin_args + data_args + [
        os.path.join(ROOT_DIR, "video_upscaler", "__main__.py")
    ]

    print(f"\nRunning command:\n{' '.join(cmd)}\n")
    subprocess.check_call(cmd)

    if mode == "onefile":
        out_file = os.path.join(dist_dir, f"{exe_name}.exe")
        print("\n=== Single-File Executable Packaging Completed Successfully! ===")
        print(f"Deliverable: {out_file}")
    else:
        out_folder = os.path.join(dist_dir, exe_name)
        print("\n=== Directory Packaging Completed Successfully! ===")
        print(f"Deliverable: {out_folder}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Video-Upscayl for Windows")
    parser.add_argument("--mode", choices=["onefile", "onedir", "both"], default="onefile",
                        help="Packaging mode: onefile (single .exe) or onedir (directory)")
    args = parser.parse_args()

    if args.mode == "both":
        build_standalone(mode="onefile")
        build_standalone(mode="onedir")
    else:
        build_standalone(mode=args.mode)
