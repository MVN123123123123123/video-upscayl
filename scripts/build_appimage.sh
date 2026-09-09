#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

APP_NAME="Video-Upscayl"
APP_BIN="video-upscaler"
BUILD_DIR="${ROOT_DIR}/build"
DIST_DIR="${ROOT_DIR}/dist"
APPDIR="${ROOT_DIR}/build/AppDir"
OUTPUT_APPIMAGE="${DIST_DIR}/${APP_NAME}-x86_64.AppImage"

echo "===================================================================="
echo " Building ${APP_NAME} Standalone AppImage for Linux (x86_64)"
echo "===================================================================="

mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

# 1. Compile C++ backend if not built
SO_PATH="${BUILD_DIR}/libvideoupscaler.so"
if [[ ! -f "${SO_PATH}" ]]; then
    echo "[INFO] Compiling native C++ backend..."
    bash "${SCRIPT_DIR}/build_backend.sh"
fi

if [[ ! -f "${SO_PATH}" ]]; then
    echo "[ERROR] Native backend ${SO_PATH} was not found."
    exit 1
fi

# 2. Verify / install Python dependencies and PyInstaller
PYTHON_BIN="${PYTHON:-python3}"
if command -v uv &>/dev/null && [[ -f "${ROOT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi

echo "[INFO] Using Python: ${PYTHON_BIN}"
if ! "${PYTHON_BIN}" -c "import PyInstaller" &>/dev/null; then
    echo "[INFO] Installing PyInstaller..."
    "${PYTHON_BIN}" -m pip install --upgrade pyinstaller || true
fi

# 3. Clean and prepare AppDir directory structure
echo "[INFO] Preparing AppDir layout at: ${APPDIR}"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APPDIR}/models"

# Copy Desktop entry and Icon
cp "${SCRIPT_DIR}/resources/video-upscayl.desktop" "${APPDIR}/video-upscayl.desktop"
cp "${SCRIPT_DIR}/resources/video-upscayl.desktop" "${APPDIR}/usr/share/applications/video-upscayl.desktop"
cp "${SCRIPT_DIR}/resources/video-upscayl.png" "${APPDIR}/video-upscayl.png"
cp "${SCRIPT_DIR}/resources/video-upscayl.png" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/video-upscayl.png"
cp "${SCRIPT_DIR}/resources/video-upscayl.png" "${APPDIR}/.DirIcon"

# 4. Copy models into AppDir
if [[ -d "${ROOT_DIR}/models" ]]; then
    echo "[INFO] Bundling pretrained neural network models into AppDir..."
    cp -r "${ROOT_DIR}/models/"* "${APPDIR}/models/" 2>/dev/null || true
fi

# 5. Copy native backend library and runtime dependencies
echo "[INFO] Bundling native C++ backend into AppDir/usr/lib..."
cp "${SO_PATH}" "${APPDIR}/usr/lib/"

# Copy shared libraries needed by libvideoupscaler (glslang, SPIRV, OpenMP)
SEARCH_LIB_DIRS=()
for d in /usr/lib /usr/lib64 /usr/lib/x86_64-linux-gnu /lib/x86_64-linux-gnu; do
    if [[ -d "$d" ]]; then
        SEARCH_LIB_DIRS+=("$d")
    fi
done

if [[ ${#SEARCH_LIB_DIRS[@]} -gt 0 ]]; then
    for lib in libglslang.so* libSPIRV.so* libSPIRV-Tools*.so* libgomp.so*; do
        find "${SEARCH_LIB_DIRS[@]}" -name "${lib}" 2>/dev/null | while read -r f; do
            if [[ -f "$f" && ! -L "$f" ]]; then
                cp -n "$f" "${APPDIR}/usr/lib/" 2>/dev/null || true
            elif [[ -L "$f" ]]; then
                cp -P "$f" "${APPDIR}/usr/lib/" 2>/dev/null || true
            fi
        done || true
    done
fi

# 6. Locate or bundle static FFmpeg & FFprobe
FFMPEG_BIN="$(which ffmpeg || true)"
FFPROBE_BIN="$(which ffprobe || true)"

if [[ -n "${FFMPEG_BIN}" && -x "${FFMPEG_BIN}" ]]; then
    echo "[INFO] Bundling ffmpeg: ${FFMPEG_BIN}"
    cp "${FFMPEG_BIN}" "${APPDIR}/usr/bin/ffmpeg"
fi
if [[ -n "${FFPROBE_BIN}" && -x "${FFPROBE_BIN}" ]]; then
    echo "[INFO] Bundling ffprobe: ${FFPROBE_BIN}"
    cp "${FFPROBE_BIN}" "${APPDIR}/usr/bin/ffprobe"
fi

# 7. Package Python application using PyInstaller into AppDir
echo "[INFO] Compiling Python application with PyInstaller..."
PYI_BUILD="${BUILD_DIR}/pyi_build"
PYI_DIST="${BUILD_DIR}/pyi_dist"
rm -rf "${PYI_BUILD}" "${PYI_DIST}"

"${PYTHON_BIN}" -m PyInstaller \
    --name "${APP_BIN}" \
    --onedir \
    --clean \
    --noconfirm \
    --distpath "${PYI_DIST}" \
    --workpath "${PYI_BUILD}" \
    --add-binary "${SO_PATH}:." \
    --add-data "${ROOT_DIR}/models:models" \
    "${ROOT_DIR}/video_upscaler/__main__.py"

# Copy PyInstaller bundle into AppDir
echo "[INFO] Installing PyInstaller payload into AppDir..."
cp -r "${PYI_DIST}/${APP_BIN}/"* "${APPDIR}/usr/bin/"

# 8. Create standard AppRun entrypoint
cat << 'EOF' > "${APPDIR}/AppRun"
#!/bin/sh
set -e

# Resolve directory of AppImage mount point
HERE="$(dirname "$(readlink -f "${0}")")"
export APPDIR="${HERE}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${HERE}/usr/bin:${LD_LIBRARY_PATH:-}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

# Run main application with arguments
exec "${HERE}/usr/bin/video-upscaler" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

# 9. Download appimagetool if not available and package
echo "[INFO] Packaging AppImage using appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool-x86_64.AppImage"
if [[ ! -f "${APPIMAGETOOL}" ]]; then
    echo "[INFO] Downloading appimagetool..."
    curl -sL "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" -o "${APPIMAGETOOL}"
    chmod +x "${APPIMAGETOOL}"
fi

# Extract and run appimagetool without requiring FUSE
cd "${BUILD_DIR}"
ARCH=x86_64 "${APPIMAGETOOL}" --appimage-extract-and-run "${APPDIR}" "${OUTPUT_APPIMAGE}"

echo "===================================================================="
echo " Standalone AppImage Build Completed!"
echo " Artifact: ${OUTPUT_APPIMAGE}"
ls -lh "${OUTPUT_APPIMAGE}"
echo "===================================================================="
