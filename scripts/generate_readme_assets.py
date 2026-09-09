#!/usr/bin/env python3
"""
Generate README visual assets:
1. docs/images/comparison_crops.png - High-res zoomed before/after comparison grid
2. docs/images/comparison_demo.webp & .gif - Animated split-screen sweeping slider
"""

import os
import cv2
import numpy as np

OUTPUT_DIR = "/home/linux/video-upscayl/docs/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ORIG_PATH = "/home/linux/video-upscayl/docs/videos/demo_original.mp4"
UP3X_PATH = "/home/linux/video-upscayl/docs/videos/demo_upscaled_3x.mp4"

def create_zoomed_crops():
    print("Generating zoomed crops comparison...")
    cap_orig = cv2.VideoCapture(ORIG_PATH)
    cap_up = cv2.VideoCapture(UP3X_PATH)

    # Frame 60 (2.0s into the 6s demo clip)
    cap_orig.set(cv2.CAP_PROP_POS_FRAMES, 60)
    cap_up.set(cv2.CAP_PROP_POS_FRAMES, 60)

    ret1, f_orig = cap_orig.read()
    ret2, f_up = cap_up.read()
    cap_orig.release()
    cap_up.release()

    if not ret1 or not ret2:
        raise RuntimeError("Failed to read frames for crops.")

    # f_orig is 576 x 1024
    # f_up is 1728 x 3072
    # Let's crop two distinct high-detail regions:
    # Crop 1: Character's face & eye region (center-left)
    # Crop 2: Sleeping character's hair & expression (center-right)
    
    crops = [
        ("Character Eyes & Linework", (200, 340, 200, 200)),  # (y, x, h, w) in 576x1024 coords
        ("Sleeping Character & Bokeh", (260, 520, 200, 200)),
    ]

    target_crop_w = 400
    target_crop_h = 400

    panel_list = []
    
    for title, (cy, cx, ch, cw) in crops:
        c1 = f_orig[cy:cy+ch, cx:cx+cw]
        c2 = f_up[cy*3:(cy+ch)*3, cx*3:(cx+cw)*3]

        # Resize original with bicubic to 400x400 to show standard video player scaling
        c1_scaled = cv2.resize(c1, (target_crop_w, target_crop_h), interpolation=cv2.INTER_CUBIC)
        c2_scaled = cv2.resize(c2, (target_crop_w, target_crop_h), interpolation=cv2.INTER_AREA)

        # Annotate c1 (Original)
        cv2.rectangle(c1_scaled, (0, 0), (target_crop_w, 36), (15, 23, 42), -1)
        cv2.putText(c1_scaled, "ORIGINAL (Bicubic Upscale)", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2, cv2.LINE_AA)

        # Annotate c2 (Real-CUGAN)
        cv2.rectangle(c2_scaled, (0, 0), (target_crop_w, 36), (10, 30, 50), -1)
        cv2.putText(c2_scaled, "VIDEO-UPSCAYL (Real-CUGAN 3x)", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (254, 242, 0), 2, cv2.LINE_AA)

        # Add thin border
        c1_bordered = cv2.copyMakeBorder(c1_scaled, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(40, 50, 70))
        c2_bordered = cv2.copyMakeBorder(c2_scaled, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 242, 254))

        panel = np.hstack([c1_bordered, c2_bordered])
        panel_list.append(panel)

    final_crop_image = np.vstack(panel_list)
    out_crop_path = os.path.join(OUTPUT_DIR, "comparison_crops.png")
    cv2.imwrite(out_crop_path, final_crop_image)
    print(f"Saved crops to {out_crop_path}")


def create_animated_slider():
    print("Generating animated slider comparison...")
    cap_orig = cv2.VideoCapture(ORIG_PATH)
    cap_up = cv2.VideoCapture(UP3X_PATH)

    fps = cap_orig.get(cv2.CAP_PROP_FPS)
    target_w = 960
    target_h = 540
    
    # We will generate a 3.6 second loop at 20 fps = 72 frames
    total_frames = 72
    step = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT) / total_frames)
    if step < 1:
        step = 1

    frames = []
    
    for i in range(total_frames):
        f_idx = (i * step) % 180
        cap_orig.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        cap_up.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret1, f1 = cap_orig.read()
        ret2, f2 = cap_up.read()
        if not ret1 or not ret2:
            break

        f1_res = cv2.resize(f1, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        f2_res = cv2.resize(f2, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # Slider position oscillating smoothly between 20% and 80%
        # cos goes from 1 to -1 to 1
        t_norm = i / float(total_frames)
        # Smooth oscillation
        ratio = 0.5 - 0.32 * np.cos(2 * np.pi * t_norm)
        split_x = int(target_w * ratio)

        # Composite frame: Left = f1_res, Right = f2_res
        composite = f2_res.copy()
        composite[:, :split_x] = f1_res[:, :split_x]

        # Draw vertical separator line
        cv2.line(composite, (split_x, 0), (split_x, target_h), (254, 242, 0), 2)

        # Draw slider handle pill in center
        center_y = target_h // 2
        pill_radius = 18
        cv2.circle(composite, (split_x, center_y), pill_radius, (15, 20, 30), -1)
        cv2.circle(composite, (split_x, center_y), pill_radius, (254, 242, 0), 2)
        # Double arrows text
        cv2.putText(composite, "<>", (split_x - 11, center_y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (254, 242, 0), 1, cv2.LINE_AA)

        # Badges
        # Left badge
        cv2.rectangle(composite, (20, 20), (220, 52), (15, 23, 42), -1)
        cv2.rectangle(composite, (20, 20), (220, 52), (100, 116, 139), 1)
        cv2.putText(composite, "ORIGINAL 1024x576", (32, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (241, 245, 249), 1, cv2.LINE_AA)

        # Right badge
        cv2.rectangle(composite, (target_w - 290, 20), (target_w - 20, 52), (10, 30, 50), -1)
        cv2.rectangle(composite, (target_w - 290, 20), (target_w - 20, 52), (254, 242, 0), 1)
        cv2.putText(composite, "REAL-CUGAN 3X (3072x1728)", (target_w - 278, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (254, 242, 0), 1, cv2.LINE_AA)

        # Convert to RGB
        composite_rgb = cv2.cvtColor(composite, cv2.COLOR_BGR2RGB)
        frames.append(composite_rgb)

    cap_orig.release()
    cap_up.release()

    # Save as animated WebP and GIF using PIL/imageio
    from PIL import Image
    pil_frames = [Image.fromarray(f) for f in frames]

    webp_path = os.path.join(OUTPUT_DIR, "comparison_demo.webp")
    pil_frames[0].save(
        webp_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=50,  # 20 fps = 50ms per frame
        loop=0,
        quality=85,
        method=6
    )
    print(f"Saved animated WebP to {webp_path} (Size: {os.path.getsize(webp_path) / 1024:.1f} KB)")

    gif_path = os.path.join(OUTPUT_DIR, "comparison_demo.gif")
    # For GIF, quantize slightly to keep size under 4MB
    pil_frames_quant = [f.quantize(colors=128, method=Image.MEDIANCUT) for f in pil_frames]
    pil_frames_quant[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames_quant[1:],
        duration=50,
        loop=0,
        optimize=True
    )
    print(f"Saved animated GIF to {gif_path} (Size: {os.path.getsize(gif_path) / 1024:.1f} KB)")

if __name__ == "__main__":
    create_zoomed_crops()
    create_animated_slider()
    print("All README comparison assets generated successfully!")
