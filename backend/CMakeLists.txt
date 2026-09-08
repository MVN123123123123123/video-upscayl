cmake_minimum_required(VERSION 3.20)
project(videoupscaler_backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(OpenMP REQUIRED)

set(NCNN_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/ncnn")

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${NCNN_ROOT}/include
)

link_directories(
    ${NCNN_ROOT}/lib
)

add_library(videoupscaler SHARED
    src/engine.cpp
    src/videoupscaler.cpp
)

target_compile_options(videoupscaler PRIVATE
    -O3
    -march=native
    -Wall
    -Wextra
)

target_link_libraries(videoupscaler PRIVATE
    ncnn
    glslang
    SPIRV
    vulkan
    OpenMP::OpenMP_CXX
    pthread
    dl
)

set_target_properties(videoupscaler PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "videoupscaler"
)
