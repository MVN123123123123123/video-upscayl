import os
import sys
import time
import subprocess
import signal
from typing import Optional, Dict, Any, Callable
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.console import Console

from .backend_bridge import VideoUpscalerBackend, UpscalerSession, DeviceType
from .models import get_model_info, ensure_model_files
from .utils import probe_video, get_ffmpeg_path, get_subprocess_kwargs


class VideoUpscalePipeline:
    def __init__(
        self,
        input_path: str,
        output_path: str,
        model_name: str = "realesr-animevideov3-x2",
        scale: Optional[int] = None,
        device_type: DeviceType = DeviceType.GPU,
        tile_size: int = 256,
        tile_pad: Optional[int] = None,
        num_threads: int = 0,
        gpu_id: int = -1,
        codec: str = "libx264",
        crf: int = 18,
        preset: str = "fast",
        console: Optional[Console] = None
    ):
        self.input_path = os.path.abspath(input_path)
        self.output_path = os.path.abspath(output_path)
        self.model_info = get_model_info(model_name, scale=scale)
        self.scale = self.model_info["scale"]
        self.device_type = device_type
        self.tile_size = tile_size
        self.num_threads = num_threads
        self.gpu_id = gpu_id
        self.codec = codec
        self.crf = crf
        self.preset = preset
        self.console = console or Console()

        min_pad = self.model_info.get("tile_pad", 10)
        if tile_pad is None:
            self.tile_pad = min_pad
        elif tile_pad < min_pad:
            self.console.print(
                f"[yellow]Notice: Specified tile_pad ({tile_pad}) is less than model minimum ({min_pad}) "
                f"for '{self.model_info['name']}'. Adjusting tile_pad to {min_pad} to prevent tile seam/black bar artifacts.[/yellow]"
            )
            self.tile_pad = min_pad
        else:
            self.tile_pad = tile_pad

        # Probe input
        self.video_meta = probe_video(self.input_path)
        self.in_w = self.video_meta["width"]
        self.in_h = self.video_meta["height"]
        self.out_w = self.in_w * self.scale
        self.out_h = self.in_h * self.scale
        self.fps = self.video_meta["fps"]
        self.fps_rational = self.video_meta["fps_rational"]
        self.total_frames = self.video_meta["total_frames"]

        # Ensure model weights
        self.bin_path, self.param_path = ensure_model_files(self.model_info)

    def run(
        self,
        max_frames: Optional[int] = None,
        progress_callback: Optional[Callable[[int, Optional[int], float, float], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the streaming video upscale pipeline.
        Returns execution statistics dictionary.
        """
        backend = VideoUpscalerBackend()
        session = backend.create_instance(
            model_path=self.bin_path,
            param_path=self.param_path,
            scale=self.scale,
            device_type=self.device_type,
            tile_size=self.tile_size,
            tile_pad=self.tile_pad,
            num_threads=self.num_threads,
            gpu_id=self.gpu_id
        )

        in_frame_bytes = self.in_w * self.in_h * 3
        out_frame_bytes = self.out_w * self.out_h * 3

        ffmpeg_bin = get_ffmpeg_path()
        sub_kwargs = get_subprocess_kwargs()

        # FFmpeg Decoder process (decodes input directly to rawvideo rgb24 on stdout)
        decoder_cmd = [
            ffmpeg_bin,
            "-v", "error",
            "-i", self.input_path,
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
        ]
        if max_frames:
            decoder_cmd.extend(["-vframes", str(max_frames)])
        decoder_cmd.append("-")

        # FFmpeg Encoder process (reads rawvideo rgb24 from stdin, muxes audio/subs from input file)
        encoder_cmd = [
            ffmpeg_bin,
            "-y",
            "-v", "error",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self.out_w}x{self.out_h}",
            "-r", self.fps_rational,
            "-i", "-",
            "-i", self.input_path,
            "-map", "0:v:0",
            "-map", "1:a?",
            "-map", "1:s?",
            "-c:a", "copy",
            "-c:s", "copy",
            "-c:v", self.codec,
            "-crf", str(self.crf),
            "-preset", self.preset,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            self.output_path
        ]

        decoder_proc = None
        encoder_proc = None
        processed_frames = 0
        t_start = time.perf_counter()

        frames_to_process = min(self.total_frames, max_frames) if max_frames else self.total_frames
        if frames_to_process <= 0:
            frames_to_process = None

        try:
            decoder_proc = subprocess.Popen(
                decoder_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=in_frame_bytes * 4,
                **sub_kwargs
            )
            encoder_proc = subprocess.Popen(
                encoder_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=out_frame_bytes * 4,
                **sub_kwargs
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]Upscaling[/bold cyan]"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TextColumn("• [bold green]{task.completed}/{task.total}[/bold green] frames"),
                TextColumn("• [bold yellow]{task.fields[fps]:.2f} FPS[/bold yellow]"),
                TextColumn("• [magenta]{task.fields[speed]:.2f}x[/magenta]"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
                transient=False
            ) as progress:
                task_id = progress.add_task(
                    "Processing",
                    total=frames_to_process,
                    fps=0.0,
                    speed=0.0
                )

                while True:
                    if cancel_check and cancel_check():
                        self.console.print("\n[yellow]Pipeline cancellation requested.[/yellow]")
                        break

                    raw_in = decoder_proc.stdout.read(in_frame_bytes)
                    if not raw_in or len(raw_in) < in_frame_bytes:
                        break

                    out_bytes = session.process_frame_bytes(raw_in, self.in_w, self.in_h)
                    encoder_proc.stdin.write(out_bytes)

                    processed_frames += 1
                    t_elapsed = time.perf_counter() - t_start
                    curr_fps = processed_frames / t_elapsed if t_elapsed > 0 else 0.0
                    speed_x = curr_fps / self.fps if self.fps > 0 else 0.0

                    progress.update(
                        task_id,
                        advance=1,
                        fps=curr_fps,
                        speed=speed_x
                    )

                    if progress_callback:
                        progress_callback(processed_frames, frames_to_process, curr_fps, speed_x)

                    if max_frames and processed_frames >= max_frames:
                        break

        except KeyboardInterrupt:
            self.console.print("\n[bold red]Interrupted by user. Finalizing encoder stream...[/bold red]")
        finally:
            session.close()

            if decoder_proc:
                if decoder_proc.stdout:
                    decoder_proc.stdout.close()
                if decoder_proc.stderr:
                    decoder_proc.stderr.close()
                decoder_proc.terminate()
                decoder_proc.wait()

            if encoder_proc:
                if encoder_proc.stdin:
                    encoder_proc.stdin.close()
                if encoder_proc.stderr:
                    encoder_proc.stderr.close()
                encoder_proc.wait()

        t_total = time.perf_counter() - t_start
        avg_fps = processed_frames / t_total if t_total > 0 else 0.0

        if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
            raise RuntimeError(f"Output video was not successfully generated at {self.output_path}")

        out_size_mb = os.path.getsize(self.output_path) / (1024 * 1024)

        return {
            "processed_frames": processed_frames,
            "elapsed_seconds": t_total,
            "average_fps": avg_fps,
            "speed_multiplier": avg_fps / self.fps if self.fps > 0 else 0.0,
            "output_size_mb": round(out_size_mb, 2),
            "output_path": self.output_path,
            "output_resolution": f"{self.out_w}x{self.out_h}"
        }
