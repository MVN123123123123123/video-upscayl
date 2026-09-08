"""
Video-Upscayl Windows Standalone Packaging Script (PyInstaller)
Creates a self-contained, windowed executable for Windows users.
"""

import os
import sys
import shutil
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def build_standalone():
    print("=== Packaging Video-Upscayl for Windows ===")

    try:
        import PyInstaller
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    dist_dir = os.path.join(ROOT_DIR, "dist")
    build_dir = os.path.join(ROOT_DIR, "build_pyinstaller")

    # Locate backend DLL
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

    data_args = []
    if dll_path:
        print(f"[INFO] Bundling native backend: {dll_path}")
        data_args.extend(["--add-binary", f"{dll_path};."])
    else:
        print("[WARNING] videoupscaler.dll not found in build directory. Please compile it first.")

    models_dir = os.path.join(ROOT_DIR, "models")
    if os.path.exists(models_dir):
        print(f"[INFO] Bundling models from: {models_dir}")
        data_args.extend(["--add-data", f"{models_dir};models"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "Video-Upscayl",
        "--windowed",                 # No command prompt console window on Windows!
        "--onedir",
        "--clean",
        "--distpath", dist_dir,
        "--workpath", build_dir,
    ] + data_args + [
        os.path.join(ROOT_DIR, "video_upscaler", "__main__.py")
    ]

    print(f"Running command:\n{' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("\n=== Packaging Completed Successfully! ===")
    print(f"Standalone distribution generated at:\n{os.path.join(dist_dir, 'Video-Upscayl')}")

if __name__ == "__main__":
    build_standalone()
