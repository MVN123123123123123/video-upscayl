import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .backend_bridge import VideoUpscalerBackend, DeviceType
from .models import MODEL_REGISTRY, list_available_models
from .utils import probe_video, get_hardware_info
from .benchmark import run_hardware_benchmark
from .pipeline import VideoUpscalePipeline


class VideoUpscalerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Video-Upscayl - Hardware Video Upscaler")
        self.root.geometry("720x680")
        self.root.minsize(640, 580)

        # Apply clean classic/clam theme
        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")
        elif "classic" in available_themes:
            self.style.theme_use("classic")

        # Variables
        self.input_file_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.model_var = tk.StringVar(value="4x-UltraSharp")
        self.device_var = tk.StringVar(value="auto")
        self.tile_size_var = tk.StringVar(value="256")
        self.tile_pad_var = tk.StringVar(value="10")
        self.compare_var = tk.BooleanVar(value=False)
        self.preview_var = tk.BooleanVar(value=False)
        self.codec_var = tk.StringVar(value="libx264")
        self.crf_var = tk.StringVar(value="18")

        self.info_text_var = tk.StringVar(value="Select an input video file to begin.")
        self.status_text_var = tk.StringVar(value="Status: Ready")

        self.is_processing = False
        self.cancel_requested = False
        self.worker_thread: Optional[threading.Thread] = None
        self.msg_queue = queue.Queue()

        self._create_widgets()
        self._check_queue()
        self._load_system_info()

    def _create_widgets(self):
        # Top banner frame
        header_frame = ttk.Frame(self.root, padding=(10, 8))
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text="Video-Upscayl",
            font=("Helvetica", 14, "bold")
        )
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(
            header_frame,
            text=" - Hardware-Accelerated Video Super-Resolution (Vulkan / AVX-512)",
            font=("Helvetica", 10)
        )
        subtitle_label.pack(side=tk.LEFT, padx=5, pady=3)

        # Main Container
        main_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Video Files Section
        files_group = ttk.LabelFrame(main_frame, text="Video Files", padding=10)
        files_group.pack(fill=tk.X, pady=5)

        # Input Row
        ttk.Label(files_group, text="Input Video:").grid(row=0, column=0, sticky=tk.W, pady=2)
        input_entry = ttk.Entry(files_group, textvariable=self.input_file_var, width=50)
        input_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(files_group, text="Browse...", command=self._browse_input).grid(row=0, column=2, padx=2, pady=2)

        # Probe Info
        info_label = ttk.Label(files_group, textvariable=self.info_text_var, foreground="#333333", font=("Helvetica", 9))
        info_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=2)

        # Output Row
        ttk.Label(files_group, text="Output Video:").grid(row=2, column=0, sticky=tk.W, pady=2)
        output_entry = ttk.Entry(files_group, textvariable=self.output_file_var, width=50)
        output_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(files_group, text="Save As...", command=self._browse_output).grid(row=2, column=2, padx=2, pady=2)

        files_group.columnconfigure(1, weight=1)

        # 2. Settings Section
        settings_group = ttk.LabelFrame(main_frame, text="Upscaling & Hardware Settings", padding=10)
        settings_group.pack(fill=tk.X, pady=5)

        # Model row
        ttk.Label(settings_group, text="Model:").grid(row=0, column=0, sticky=tk.W, pady=4)
        model_combo = ttk.Combobox(
            settings_group,
            textvariable=self.model_var,
            state="readonly",
            values=[
                "4x-UltraSharp",
                "realesr-animevideov3-x2",
                "realesr-animevideov3-x3",
                "realesr-animevideov3-x4",
                "realesrgan-x4plus",
                "realesrgan-x4plus-anime"
            ],
            width=28
        )
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)

        model_desc_btn = ttk.Button(settings_group, text="Model Info", command=self._show_model_info)
        model_desc_btn.grid(row=0, column=2, sticky=tk.W, padx=2, pady=4)

        # Device selection radio row
        ttk.Label(settings_group, text="Device:").grid(row=1, column=0, sticky=tk.W, pady=4)
        device_frame = ttk.Frame(settings_group)
        device_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=4)

        ttk.Radiobutton(device_frame, text="Auto (Fastest)", variable=self.device_var, value="auto").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(device_frame, text="GPU (Vulkan)", variable=self.device_var, value="gpu").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(device_frame, text="Hybrid (GPU+CPU)", variable=self.device_var, value="hybrid").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(device_frame, text="CPU (AVX-512)", variable=self.device_var, value="cpu").pack(side=tk.LEFT, padx=3)

        # Tile size and Padding
        tile_frame = ttk.Frame(settings_group)
        tile_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=4)

        ttk.Label(tile_frame, text="Tile Size:").pack(side=tk.LEFT)
        tile_entry = ttk.Entry(tile_frame, textvariable=self.tile_size_var, width=6)
        tile_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(tile_frame, text="Padding:").pack(side=tk.LEFT, padx=(10, 0))
        pad_entry = ttk.Entry(tile_frame, textvariable=self.tile_pad_var, width=4)
        pad_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(tile_frame, text="CRF Quality:").pack(side=tk.LEFT, padx=(10, 0))
        crf_entry = ttk.Entry(tile_frame, textvariable=self.crf_var, width=4)
        crf_entry.pack(side=tk.LEFT, padx=4)

        # Checkboxes
        check_frame = ttk.Frame(settings_group)
        check_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=5, pady=4)

        ttk.Checkbutton(
            check_frame,
            text="Generate side-by-side comparison video (--compare)",
            variable=self.compare_var
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            check_frame,
            text="5-second preview only",
            variable=self.preview_var
        ).pack(side=tk.LEFT, padx=12)

        # 3. Action Section
        action_frame = ttk.Frame(main_frame, padding=5)
        action_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(
            action_frame,
            text="▶ Start Upscaling",
            command=self._start_upscaling,
            width=18
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(
            action_frame,
            text="⏹ Cancel",
            command=self._cancel_upscaling,
            state=tk.DISABLED,
            width=12
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        self.bench_btn = ttk.Button(
            action_frame,
            text="⚙ Benchmark Hardware",
            command=self._run_benchmark,
            width=20
        )
        self.bench_btn.pack(side=tk.RIGHT, padx=5)

        # Progress bar & Status
        progress_frame = ttk.Frame(main_frame, padding=5)
        progress_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=2)

        self.status_label = ttk.Label(
            progress_frame,
            textvariable=self.status_text_var,
            font=("Helvetica", 9, "bold")
        )
        self.status_label.pack(anchor=tk.W, pady=2)

        # 4. Log Area (Old-school terminal style)
        log_group = ttk.LabelFrame(main_frame, text="Log Console", padding=5)
        log_group.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = tk.Text(
            log_group,
            wrap=tk.WORD,
            height=10,
            bg="#f4f4f4",
            fg="#222222",
            font=("Monospace", 9),
            relief=tk.SUNKEN,
            bd=1
        )
        log_scroll = ttk.Scrollbar(log_group, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _log(self, text: str):
        self.msg_queue.put(("log", text))

    def _check_queue(self):
        while not self.msg_queue.empty():
            msg_type, data = self.msg_queue.get_nowait()
            if msg_type == "log":
                self.log_text.insert(tk.END, data + "\n")
                self.log_text.see(tk.END)
            elif msg_type == "progress":
                completed, total, fps, speed = data
                if total and total > 0:
                    pct = (completed / total) * 100.0
                    self.progress_bar["value"] = pct
                    self.status_text_var.set(
                        f"Status: Processing {completed}/{total} frames ({pct:.1f}%) • {fps:.2f} FPS • {speed:.2f}x"
                    )
                else:
                    self.status_text_var.set(
                        f"Status: Processing frame {completed} • {fps:.2f} FPS • {speed:.2f}x"
                    )
            elif msg_type == "finished":
                success, msg = data
                self.is_processing = False
                self.start_btn.configure(state=tk.NORMAL)
                self.cancel_btn.configure(state=tk.DISABLED)
                self.bench_btn.configure(state=tk.NORMAL)
                if success:
                    self.progress_bar["value"] = 100
                    self.status_text_var.set("Status: Upscaling Completed Successfully!")
                    messagebox.showinfo("Finished", msg)
                else:
                    self.status_text_var.set("Status: Processing Stopped.")
                    messagebox.showerror("Error / Stopped", msg)

        self.root.after(100, self._check_queue)

    def _load_system_info(self):
        hw = get_hardware_info()
        self._log("=== Video-Upscayl Initialized ===")
        self._log(f"CPU: {hw['cpu_name']} ({hw['cpu_threads']} threads)")
        self._log(f"RAM: {hw['ram_gb']} GB")
        if hw["gpus"]:
            for g in hw["gpus"]:
                self._log(f"GPU [{g['id']}]: {g['name']}")
        else:
            self._log("GPU: None detected (running CPU AVX-512)")
        self._log("Ready.\n")

    def _browse_input(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.input_file_var.set(file_path)
            try:
                meta = probe_video(file_path)
                desc = (
                    f"Resolution: {meta['width']}x{meta['height']} | "
                    f"Framerate: {meta['fps']:.2f} FPS | "
                    f"Duration: {meta['duration']:.2f}s ({meta['total_frames']} frames) | "
                    f"Codec: {meta['video_codec']}"
                )
                self.info_text_var.set(desc)

                # Pre-fill output
                stem, ext = os.path.splitext(file_path)
                model_name = self.model_var.get()
                scale = MODEL_REGISTRY.get(model_name, {}).get("scale", 2)
                default_out = f"{stem}_upscaled_{scale}x_{model_name}{ext}"
                self.output_file_var.set(default_out)
                self._log(f"Selected: {os.path.basename(file_path)} ({meta['width']}x{meta['height']})")

            except Exception as e:
                self.info_text_var.set(f"Could not probe video: {e}")

    def _browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Upscaled Video As",
            defaultextension=".mp4",
            filetypes=[
                ("MP4 Video", "*.mp4"),
                ("MKV Video", "*.mkv"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.output_file_var.set(file_path)

    def _show_model_info(self):
        m = self.model_var.get()
        info = MODEL_REGISTRY.get(m, {})
        msg = (
            f"Model: {info.get('name', m)}\n"
            f"Scale: {info.get('scale', '?')}x\n"
            f"Category: {info.get('type', '?')}\n\n"
            f"Description:\n{info.get('description', '')}"
        )
        messagebox.showinfo("Model Details", msg)

    def _run_benchmark(self):
        def worker():
            self._log("\n--- Starting Hardware Inference Benchmark ---")
            self.status_text_var.set("Status: Running hardware benchmark...")
            self.bench_btn.configure(state=tk.DISABLED)
            try:
                res = run_hardware_benchmark(
                    model_name="realesr-animevideov3-x2",
                    width=256,
                    height=256,
                    num_frames=3
                )
                self._log(f"Results on 256x256:")
                self._log(f"  • GPU (Vulkan): {res['gpu_fps']:.2f} FPS ({res['gpu_ms']:.1f} ms)")
                self._log(f"  • CPU (AVX-512): {res['cpu_fps']:.2f} FPS ({res['cpu_ms']:.1f} ms)")
                self._log(f"  • Hybrid (GPU+CPU): {res['hybrid_fps']:.2f} FPS ({res['hybrid_ms']:.1f} ms)")
                self._log(f"Fastest Device: {res['best_device_name']} ({res['best_fps']:.2f} FPS)\n")
                self.status_text_var.set(f"Benchmark finished: {res['best_device_name']} is fastest.")
            except Exception as e:
                self._log(f"Benchmark error: {e}")
                self.status_text_var.set("Benchmark failed.")
            finally:
                self.bench_btn.configure(state=tk.NORMAL)

        threading.Thread(target=worker, daemon=True).start()

    def _start_upscaling(self):
        input_path = self.input_file_var.get().strip()
        output_path = self.output_file_var.get().strip()

        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Error", "Please select a valid input video file.")
            return

        if not output_path:
            messagebox.showerror("Error", "Please specify an output video file path.")
            return

        try:
            tile_size = int(self.tile_size_var.get())
            tile_pad = int(self.tile_pad_var.get())
            crf = int(self.crf_var.get())
        except ValueError:
            messagebox.showerror("Error", "Tile size, padding, and CRF must be valid integers.")
            return

        model_name = self.model_var.get()
        dev_str = self.device_var.get()

        if dev_str == "auto":
            device_type = DeviceType.AUTO
        elif dev_str == "gpu":
            device_type = DeviceType.GPU
        elif dev_str == "cpu":
            device_type = DeviceType.CPU
        elif dev_str == "hybrid":
            device_type = DeviceType.HYBRID
        else:
            device_type = DeviceType.GPU

        self.is_processing = True
        self.cancel_requested = False
        self.start_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)
        self.bench_btn.configure(state=tk.DISABLED)
        self.progress_bar["value"] = 0

        self._log(f"\n--- Starting Upscaling Job ---")
        self._log(f"Input: {input_path}")
        self._log(f"Output: {output_path}")
        self._log(f"Model: {model_name}")
        self._log(f"Device: {device_type.name}")

        def run_thread():
            try:
                # If auto, benchmark
                actual_device = device_type
                if actual_device == DeviceType.AUTO:
                    self._log("Auto-detecting fastest device...")
                    from .benchmark import auto_select_device
                    meta = probe_video(input_path)
                    model_info = MODEL_REGISTRY.get(model_name, {})
                    actual_device = auto_select_device(model_info, meta["width"], meta["height"])
                    self._log(f"Auto-selected device: {actual_device.name}")

                max_frames = None
                if self.preview_var.get():
                    meta = probe_video(input_path)
                    max_frames = int(meta["fps"] * 5)
                    self._log(f"Preview mode enabled: limit to {max_frames} frames (5s)")

                pipeline = VideoUpscalePipeline(
                    input_path=input_path,
                    output_path=output_path,
                    model_name=model_name,
                    device_type=actual_device,
                    tile_size=tile_size,
                    tile_pad=tile_pad,
                    codec=self.codec_var.get(),
                    crf=crf
                )

                def prog_cb(completed, total, fps, speed):
                    self.msg_queue.put(("progress", (completed, total, fps, speed)))

                def cancel_check():
                    return self.cancel_requested

                stats = pipeline.run(
                    max_frames=max_frames,
                    progress_callback=prog_cb,
                    cancel_check=cancel_check
                )

                if self.cancel_requested:
                    self._log("Upscaling was cancelled.")
                    self.msg_queue.put(("finished", (False, "Upscaling cancelled by user.")))
                    return

                self._log(f"Upscaling finished: {stats['processed_frames']} frames in {stats['elapsed_seconds']:.2f}s ({stats['average_fps']:.2f} FPS)")
                self._log(f"Saved: {output_path} ({stats['output_size_mb']} MB)")

                # Handle comparison video
                if self.compare_var.get():
                    self._log("Generating side-by-side comparison video...")
                    stem, ext = os.path.splitext(output_path)
                    cmp_path = f"{stem}_compare.mp4"
                    meta = probe_video(input_path)
                    scale = pipeline.scale
                    out_w = meta["width"] * scale
                    out_h = meta["height"] * scale
                    import subprocess
                    cmp_cmd = [
                        "ffmpeg", "-y", "-v", "error",
                        "-i", input_path,
                        "-i", output_path,
                        "-filter_complex",
                        f"[0:v]scale={out_w}:{out_h}:flags=neighbor,drawtext=text='ORIGINAL (Nearest)':x=20:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[left]; "
                        f"[1:v]drawtext=text='UPSCALED ({scale}x {model_name})':x=20:y=20:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.6[right]; "
                        f"[left][right]hstack[v]",
                        "-map", "[v]",
                        "-map", "1:a?",
                        "-c:v", self.codec_var.get(),
                        "-c:a", "copy",
                        "-crf", str(crf),
                        "-pix_fmt", "yuv420p",
                        cmp_path
                    ]
                    subprocess.run(cmp_cmd)
                    self._log(f"Comparison video saved: {cmp_path}")

                self.msg_queue.put((
                    "finished",
                    (True, f"Upscaling Completed!\nProcessed {stats['processed_frames']} frames at {stats['average_fps']:.2f} FPS.\nSaved to: {output_path}")
                ))

            except Exception as e:
                self._log(f"Upscaling Error: {e}")
                self.msg_queue.put(("finished", (False, str(e))))

        self.worker_thread = threading.Thread(target=run_thread, daemon=True)
        self.worker_thread.start()

    def _cancel_upscaling(self):
        if self.is_processing:
            self.cancel_requested = True
            self.cancel_btn.configure(state=tk.DISABLED)
            self._log("Stopping pipeline... please wait a moment.")


def launch_gui():
    root = tk.Tk()
    app = VideoUpscalerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
