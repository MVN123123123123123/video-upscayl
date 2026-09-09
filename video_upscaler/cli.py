import os
import sys
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .backend_bridge import VideoUpscalerBackend, DeviceType
from .models import list_available_models, get_model_info, MODEL_REGISTRY
from .benchmark import run_hardware_benchmark, format_benchmark_table, auto_select_device
from .utils import probe_video, get_hardware_info, get_ffmpeg_path, get_subprocess_kwargs
from .pipeline import VideoUpscalePipeline

console = Console()


def print_banner():
    hw = get_hardware_info()
    simd = hw.get("cpu_simd", "SIMD")
    gpus = hw.get("gpus", [])
    if gpus:
        gpu_names = ", ".join(g["name"] for g in gpus[:2])
        gpu_str = f"Vulkan Compute ({gpu_names})"
    else:
        gpu_str = "Vulkan Compute"

    title = Text()
    title.append("🚀 Video-Upscayl ", style="bold bright_cyan")
    title.append("• Universal Hardware-Accelerated Video Super-Resolution\n", style="bold white")
    title.append(f"{gpu_str} / {simd} OpenMP / Concurrent Hybrid Pipeline", style="dim cyan")
    console.print(Panel(title, border_style="bright_blue", expand=False))


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Universal High-Performance Hardware-Accelerated Video Upscaler."""
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("[yellow]Use [bold]video-upscaler --help[/bold] to view all options or run a subcommand.[/yellow]")


@main.command(name="info")
def info_cmd():
    """Display system hardware, CPU SIMD vector extensions, and Vulkan GPU telemetry."""
    print_banner()
    hw = get_hardware_info()

    table = Table(title="Hardware & System Telemetry", style="cyan")
    table.add_column("Component", style="bold white", width=22)
    table.add_column("Details", style="green")

    table.add_row("Operating System", hw["os_name"])
    table.add_row("CPU Model", hw["cpu_name"])
    table.add_row("CPU Threads", f"{hw['cpu_threads']} threads")
    table.add_row("CPU Vector Acceleration", hw["cpu_simd"])
    table.add_row("System Memory", f"{hw['ram_gb']} GB")

    if hw["gpus"]:
        for gpu in hw["gpus"]:
            table.add_row(f"GPU [{gpu['id']}]", f"{gpu['name']} (Vendor: {gpu['vendor']}, {gpu['type']})")
    else:
        table.add_row("GPU", "[yellow]No Vulkan GPU detected (CPU multi-thread mode available)[/yellow]")

    console.print(table)


@main.command(name="models")
def models_cmd():
    """List all supported super-resolution neural network models."""
    print_banner()
    models = list_available_models()

    table = Table(title="Available Pretrained Models", style="cyan")
    table.add_column("Model Name", style="bold yellow")
    table.add_column("Scale", justify="center", style="bold cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="white")

    for m in models:
        table.add_row(m["name"], f"{m['scale']}x", m["type"], m["description"])

    console.print(table)


@main.command(name="gui")
def gui_cmd():
    """Launch the classic desktop Graphical User Interface (GUI)."""
    from .gui import launch_gui
    launch_gui()


@main.command(name="benchmark")
@click.option("-m", "--model", default="realesr-animevideov3-x2", help="Model name for benchmark.")
@click.option("-w", "--width", default=512, help="Test frame width.")
@click.option("-h", "--height", default=288, help="Test frame height.")
@click.option("-n", "--num-frames", default=5, help="Number of benchmark iterations.")
@click.option("--gpu-id", default=-1, type=int, help="Target GPU device index (-1 for auto/best).")
def benchmark_cmd(model, width, height, num_frames, gpu_id):
    """Benchmark GPU vs CPU vs Hybrid inference speed on this machine."""
    print_banner()
    with console.status("[bold green]Executing hardware benchmark (testing GPU, CPU, and Hybrid)...[/bold green]"):
        bench = run_hardware_benchmark(
            model_name=model,
            width=width,
            height=height,
            num_frames=num_frames,
            gpu_id=gpu_id
        )

    console.print(format_benchmark_table(bench))
    console.print(
        f"\n[bold green]Fastest Configuration:[/bold green] [bold yellow]{bench['best_device_name']}[/bold yellow] "
        f"at [bold cyan]{bench['best_fps']:.2f} FPS[/bold cyan] ({bench['resolution']} frame)"
    )


@main.command(name="upscale")
@click.option("-i", "--input", "input_file", required=True, type=click.Path(exists=True), help="Input video file path.")
@click.option("-o", "--output", "output_file", type=click.Path(), help="Output video file path.")
@click.option("-m", "--model", default=None, help="Model name (e.g. realcugan-se-x2, 4x-UltraSharp, realesr-animevideov3-x2, realesrgan-x4plus).")
@click.option("-s", "--scale", type=int, default=None, help="Upscale factor (2, 3, or 4).")
@click.option("-d", "--device", default="auto", type=click.Choice(["auto", "gpu", "cpu", "hybrid"], case_sensitive=False), help="Hardware acceleration device.")
@click.option("--gpu-id", default=-1, type=int, help="Target GPU device index (-1 for auto/best).")
@click.option("-t", "--tile-size", default=256, type=int, help="Tile size (0 to disable tiling).")
@click.option("--tile-pad", default=None, type=int, help="Tile overlap padding in pixels (auto-detected per model if omitted).")
@click.option("--threads", default=0, type=int, help="Number of CPU worker threads (0 for auto).")
@click.option("-c", "--codec", default="libx264", help="Output video codec (e.g. libx264, libx265).")
@click.option("--crf", default=18, type=int, help="Constant Rate Factor (0-51, lower is higher quality).")
@click.option("--preset", default="fast", help="Encoder speed preset.")
@click.option("--max-frames", default=None, type=int, help="Maximum number of frames to process.")
@click.option("--preview", is_flag=True, help="Process only the first 5 seconds as a preview.")
@click.option("--compare", is_flag=True, help="Generate a side-by-side before/after comparison video.")
def upscale_cmd(
    input_file,
    output_file,
    model,
    scale,
    device,
    gpu_id,
    tile_size,
    tile_pad,
    threads,
    codec,
    crf,
    preset,
    max_frames,
    preview,
    compare
):
    """Upscale video using hardware-accelerated deep learning models."""
    print_banner()

    # Probe input
    meta = probe_video(input_file)

    # Determine model and scale
    if model is None:
        if scale == 4:
            model = "realesr-animevideov3-x4"
        elif scale == 3:
            model = "realesr-animevideov3-x3"
        else:
            model = "realesr-animevideov3-x2"

    model_info = get_model_info(model, scale=scale)
    chosen_scale = model_info["scale"]

    # Generate default output name if not provided
    if output_file is None:
        p = Path(input_file)
        output_file = str(p.parent / f"{p.stem}_upscaled_{chosen_scale}x_{model_info['name']}{p.suffix}")

    # Handle preview mode
    if preview and not max_frames:
        max_frames = int(meta["fps"] * 5)

    # Auto-detect device if requested
    if device.lower() == "auto":
        device_type = auto_select_device(
            model_info=model_info,
            width=meta["width"],
            height=meta["height"],
            gpu_id=gpu_id,
            console=console
        )
    elif device.lower() == "gpu":
        device_type = DeviceType.GPU
    elif device.lower() == "cpu":
        device_type = DeviceType.CPU
    elif device.lower() == "hybrid":
        device_type = DeviceType.HYBRID
    else:
        device_type = DeviceType.GPU

    # Display job summary
    table = Table(title="Upscaling Job Specifications", style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    table.add_row("Input File", str(input_file))
    table.add_row("Input Resolution", f"{meta['width']}x{meta['height']} ({meta['video_codec']})")
    table.add_row("Framerate", f"{meta['fps']:.2f} FPS")
    table.add_row("Duration", f"{meta['duration']:.2f}s ({meta['total_frames']} frames)")
    table.add_row("Model", f"{model_info['name']} ({chosen_scale}x)")
    table.add_row("Output Resolution", f"{meta['width'] * chosen_scale}x{meta['height'] * chosen_scale}")
    resolved_pad = tile_pad if tile_pad is not None else model_info.get("tile_pad", 10)
    pad_str = f"{resolved_pad}" if tile_pad is not None else f"{resolved_pad} (auto)"
    table.add_row("Device Mode", device_type.name)
    table.add_row("Tiling Settings", f"tile_size={tile_size}, pad={pad_str}")
    table.add_row("Output Codec", f"{codec} (CRF {crf}, preset {preset})")
    table.add_row("Output File", str(output_file))

    console.print(table)
    console.print()

    # Run Pipeline
    pipeline = VideoUpscalePipeline(
        input_path=input_file,
        output_path=output_file,
        model_name=model_info["name"],
        scale=chosen_scale,
        device_type=device_type,
        tile_size=tile_size,
        tile_pad=tile_pad,
        num_threads=threads,
        gpu_id=gpu_id,
        codec=codec,
        crf=crf,
        preset=preset,
        console=console
    )

    stats = pipeline.run(max_frames=max_frames)

    console.print("\n[bold green]✔ Upscaling Completed Successfully![/bold green]")
    res_table = Table(style="green")
    res_table.add_column("Metric", style="bold white")
    res_table.add_column("Result", style="bold cyan")

    res_table.add_row("Frames Processed", str(stats["processed_frames"]))
    res_table.add_row("Elapsed Time", f"{stats['elapsed_seconds']:.2f} seconds")
    res_table.add_row("Processing Throughput", f"{stats['average_fps']:.2f} FPS ({stats['speed_multiplier']:.2f}x realtime)")
    res_table.add_row("Output File Size", f"{stats['output_size_mb']} MB")
    res_table.add_row("Saved Destination", stats["output_path"])

    console.print(res_table)

    # Optional side-by-side comparison video
    if compare:
        p_out = Path(output_file)
        compare_path = str(p_out.parent / f"{p_out.stem}_compare.mp4")
        console.print(f"\n[bold yellow]Generating side-by-side comparison video...[/bold yellow]")
        out_w = meta["width"] * chosen_scale
        out_h = meta["height"] * chosen_scale
        ffmpeg_bin = get_ffmpeg_path()
        cmp_cmd = [
            ffmpeg_bin, "-y", "-v", "error",
            "-i", input_file,
            "-i", output_file,
            "-filter_complex",
            f"[0:v]scale={out_w}:{out_h}:flags=neighbor,drawtext=text='ORIGINAL (Upscaled Nearest)':x=20:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.6[left]; "
            f"[1:v]drawtext=text='SUPER-RESOLUTION ({chosen_scale}x {model_info['name']})':x=20:y=20:fontsize=24:fontcolor=yellow:box=1:boxcolor=black@0.6[right]; "
            f"[left][right]hstack[v]",
            "-map", "[v]",
            "-map", "1:a?",
            "-c:v", codec,
            "-c:a", "copy",
            "-crf", str(crf),
            "-preset", preset,
            "-pix_fmt", "yuv420p",
            compare_path
        ]
        import subprocess
        res = subprocess.run(cmp_cmd, **get_subprocess_kwargs())
        if res.returncode == 0:
            console.print(f"[bold green]✔ Comparison video saved:[/bold green] [bold cyan]{compare_path}[/bold cyan]")
        else:
            console.print(f"[bold red]Failed to generate comparison video.[/bold red]")


@main.command(name="demo")
@click.option("--port", default=8000, type=int, help="Port to host interactive comparison demo on.")
@click.option("--no-browser", is_flag=True, help="Do not automatically open default web browser.")
def demo_cmd(port: int, no_browser: bool):
    """Launch the interactive before/after video comparison web player."""
    import http.server
    import socketserver
    import webbrowser
    import threading

    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    if not (docs_dir / "index.html").exists():
        console.print("[bold red]Error:[/bold red] Interactive demo files not found in docs/ directory.")
        sys.exit(1)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs_dir), **kwargs)

        def log_message(self, format, *args):
            pass

    console.print(f"[bold cyan]⚡ Video-Upscayl Interactive Comparison Player[/bold cyan]")
    console.print(f"Serving demo at: [bold green]http://localhost:{port}[/bold green]")
    console.print("[dim]Press Ctrl+C to stop the demo server.[/dim]\n")

    url = f"http://localhost:{port}/index.html"
    if not no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        with socketserver.TCPServer(("", port), QuietHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo server stopped.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Failed to start server on port {port}: {e}[/bold red]")


def entry_point():
    """
    Main application entry point.
    - On Windows, or when run as a standalone AppImage, or when run without arguments,
      the Graphical User Interface (GUI) is launched automatically so everyday users
      never have to deal with command line interfaces.
    - If CLI subcommands or '--cli' is passed, the CLI runs directly.
    """
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        main()
        return

    is_appimage = bool(os.environ.get("APPIMAGE") or os.environ.get("APPDIR"))
    is_windows = sys.platform == "win32"

    cli_subcommands = {"upscale", "info", "models", "benchmark", "gui", "demo", "--help", "-h", "--version"}
    args = sys.argv[1:]

    # If any CLI subcommand or help flag is passed, invoke CLI
    if args and any(arg in cli_subcommands for arg in args):
        main()
        return

    # Default to GUI for Windows, AppImage, or zero-argument invocation
    if is_windows or is_appimage or not args:
        from .gui import launch_gui
        launch_gui()
    else:
        main()


if __name__ == "__main__":
    entry_point()
