#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DIR="${ROOT_DIR}/build"
mkdir -p "${BUILD_DIR}"

# Remove stale CMakeCache if it was generated in a different directory or machine
if [[ -f "${BUILD_DIR}/CMakeCache.txt" ]]; then
    if ! grep -q "${BUILD_DIR}" "${BUILD_DIR}/CMakeCache.txt" 2>/dev/null; then
        echo "[INFO] Cleaning stale CMakeCache from another machine or directory..."
        rm -rf "${BUILD_DIR}/CMakeCache.txt" "${BUILD_DIR}/CMakeFiles" "${BUILD_DIR}/build.ninja"
    fi
fi

echo "=== Building VideoUpscaler C++ Native Backend ==="
cd "${BUILD_DIR}"
cmake -GNinja -DCMAKE_BUILD_TYPE=Release "${ROOT_DIR}/backend"
ninja -j"$(nproc)"

echo "=== Build Successful: ${BUILD_DIR}/libvideoupscaler.so ==="
ls -lh "${BUILD_DIR}/libvideoupscaler.so"
