#ifndef TILER_H
#define TILER_H

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <vector>
#include <algorithm>
#include <cstdint>
#include <cstring>
#if defined(_OPENMP)
#include <omp.h>
#endif

struct TileInfo {
    int x0;          // Tile start X in original image
    int y0;          // Tile start Y in original image
    int w;           // Tile valid width
    int h;           // Tile valid height
    int pad;         // Padding on each side
    int padded_w;    // w + 2 * pad
    int padded_h;    // h + 2 * pad
};

class Tiler {
public:
    static std::vector<TileInfo> compute_tiles(int in_w, int in_h, int tile_size, int tile_pad) {
        std::vector<TileInfo> tiles;
        if (tile_size <= 0 || (in_w <= tile_size && in_h <= tile_size)) {
            TileInfo t;
            t.x0 = 0;
            t.y0 = 0;
            t.w = in_w;
            t.h = in_h;
            t.pad = tile_pad;
            t.padded_w = in_w + 2 * tile_pad;
            t.padded_h = in_h + 2 * tile_pad;
            tiles.push_back(t);
            return tiles;
        }

        int num_x = (in_w + tile_size - 1) / tile_size;
        int num_y = (in_h + tile_size - 1) / tile_size;

        for (int ty = 0; ty < num_y; ty++) {
            for (int tx = 0; tx < num_x; tx++) {
                TileInfo t;
                t.x0 = tx * tile_size;
                t.y0 = ty * tile_size;
                t.w = (std::min)(tile_size, in_w - t.x0);
                t.h = (std::min)(tile_size, in_h - t.y0);
                t.pad = tile_pad;
                t.padded_w = t.w + 2 * tile_pad;
                t.padded_h = t.h + 2 * tile_pad;
                tiles.push_back(t);
            }
        }
        return tiles;
    }

    static inline int reflect_coord(int coord, int max_val) {
        if (max_val <= 1) return 0;
        while (coord < 0 || coord >= max_val) {
            if (coord < 0) {
                coord = -coord;
            } else {
                coord = 2 * (max_val - 1) - coord;
            }
        }
        return coord;
    }

    static void extract_tile(
        const uint8_t* in_rgb,
        int in_w,
        int in_h,
        const TileInfo& t,
        uint8_t* tile_rgb
    ) {
        if (t.pad == 0) {
            // Full image or unpadded
            #if defined(_OPENMP)
            #pragma omp parallel for schedule(static) if(t.h > 16)
            #endif
            for (int y = 0; y < t.h; y++) {
                const uint8_t* src_row = in_rgb + ((t.y0 + y) * in_w + t.x0) * 3;
                uint8_t* dst_row = tile_rgb + (y * t.w) * 3;
                std::memcpy(dst_row, src_row, t.w * 3);
            }
            return;
        }

        #if defined(_OPENMP)
        #pragma omp parallel for schedule(static) if(t.padded_h > 16)
        #endif
        for (int py = 0; py < t.padded_h; py++) {
            int src_y = reflect_coord(t.y0 - t.pad + py, in_h);
            const uint8_t* src_row = in_rgb + (src_y * in_w) * 3;
            uint8_t* dst_row = tile_rgb + (py * t.padded_w) * 3;

            for (int px = 0; px < t.padded_w; px++) {
                int src_x = reflect_coord(t.x0 - t.pad + px, in_w);
                dst_row[px * 3 + 0] = src_row[src_x * 3 + 0];
                dst_row[px * 3 + 1] = src_row[src_x * 3 + 1];
                dst_row[px * 3 + 2] = src_row[src_x * 3 + 2];
            }
        }
    }

    static void stitch_tile(
        const uint8_t* tile_rgb,
        const TileInfo& t,
        int scale,
        uint8_t* out_rgb,
        int out_w,
        int out_h,
        int actual_tile_w = 0,
        int actual_tile_h = 0
    ) {
        int valid_w = t.w * scale;
        int valid_h = t.h * scale;
        if (actual_tile_w <= 0) actual_tile_w = t.padded_w * scale;
        if (actual_tile_h <= 0) actual_tile_h = t.padded_h * scale;

        int crop_x = (std::max)(0, (actual_tile_w - valid_w) / 2);
        int crop_y = (std::max)(0, (actual_tile_h - valid_h) / 2);
        int dst_x0 = t.x0 * scale;
        int dst_y0 = t.y0 * scale;
        int tile_stride = actual_tile_w * 3;
        int out_stride = out_w * 3;

        int copy_bytes = (std::min)(valid_w, out_w - dst_x0) * 3;
        if (copy_bytes <= 0) return;

        #if defined(_OPENMP)
        #pragma omp parallel for schedule(static) if(valid_h > 16)
        #endif
        for (int y = 0; y < valid_h; y++) {
            int dst_y = dst_y0 + y;
            if (dst_y < out_h) {
                const uint8_t* src_ptr = tile_rgb + (crop_y + y) * tile_stride + crop_x * 3;
                uint8_t* dst_ptr = out_rgb + dst_y * out_stride + dst_x0 * 3;
                std::memcpy(dst_ptr, src_ptr, copy_bytes);
            }
        }
    }
};

#endif // TILER_H
