#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DIR="${ROOT_DIR}/build"
mkdir -p "${BUILD_DIR}"

echo "=== Building VideoUpscaler C++ Native Backend ==="
cd "${BUILD_DIR}"
cmake -GNinja -DCMAKE_BUILD_TYPE=Release "${ROOT_DIR}/backend"
ninja -j"$(nproc)"

echo "=== Build Successful: ${BUILD_DIR}/libvideoupscaler.so ==="
ls -lh "${BUILD_DIR}/libvideoupscaler.so"
