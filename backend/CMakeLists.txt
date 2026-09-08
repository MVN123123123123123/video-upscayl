cmake_minimum_required(VERSION 3.20)
project(videoupscaler_backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Option to build portable binaries (safe for any x86_64 machine, non-AVX512, etc.)
option(ENABLE_PORTABLE_BUILD "Build portable binary without CPU architecture lock-in" ON)

find_package(OpenMP REQUIRED)
find_package(Vulkan REQUIRED)

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

target_compile_definitions(videoupscaler PRIVATE
    VIDEOUPSCALER_EXPORTS
)

if(MSVC)
    target_compile_options(videoupscaler PRIVATE
        /O2
        /W3
        /MP
    )
else()
    if(ENABLE_PORTABLE_BUILD)
        # Portable optimization: do NOT force -march=native so binaries run on any CPU
        # NCNN's internal dispatch will dynamically execute AVX-512, AVX2, or AVX at runtime!
        target_compile_options(videoupscaler PRIVATE
            -O3
            -mtune=generic
            -Wall
            -Wextra
        )
    else()
        target_compile_options(videoupscaler PRIVATE
            -O3
            -march=native
            -Wall
            -Wextra
        )
    endif()
endif()

target_link_libraries(videoupscaler PRIVATE
    ncnn
    glslang
    SPIRV
    Vulkan::Vulkan
    OpenMP::OpenMP_CXX
)

if(UNIX AND NOT APPLE)
    target_link_libraries(videoupscaler PRIVATE
        pthread
        dl
    )
endif()

set_target_properties(videoupscaler PROPERTIES
    PREFIX "lib"
    OUTPUT_NAME "videoupscaler"
)
