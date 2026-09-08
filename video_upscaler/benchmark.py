from typing import Dict, Any, Optional
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Console

from .backend_bridge import VideoUpscalerBackend, DeviceType
from .models import get_model_info, ensure_model_files, MODEL_REGISTRY


def run_hardware_benchmark(
    model_name: str = "realesr-animevideov3-x2",
    width: int = 512,
    height: int = 288,
    num_frames: int = 5
) -> Dict[str, Any]:
    backend = VideoUpscalerBackend()
    model_info = get_model_info(model_name)
    bin_path, param_path = ensure_model_files(model_info)

    results = backend.benchmark(
        model_path=bin_path,
        param_path=param_path,
        scale=model_info["scale"],
        width=width,
        height=height,
        num_frames=num_frames
    )

    gpu_fps = results["gpu_fps"]
    cpu_fps = results["cpu_fps"]
    hybrid_fps = results["hybrid_fps"]

    # Determine fastest
    scores = [
        (gpu_fps, DeviceType.GPU, "GPU (Vulkan)"),
        (cpu_fps, DeviceType.CPU, "CPU (AVX-512 / OpenMP)"),
        (hybrid_fps, DeviceType.HYBRID, "Hybrid (GPU + CPU)")
    ]
    scores.sort(key=lambda x: x[0], reverse=True)
    best_fps, best_device, best_name = scores[0]

    return {
        "model": model_info["name"],
        "scale": model_info["scale"],
        "resolution": f"{width}x{height}",
        "gpu_fps": gpu_fps,
        "cpu_fps": cpu_fps,
        "hybrid_fps": hybrid_fps,
        "gpu_ms": (1000.0 / gpu_fps) if gpu_fps > 0 else 0.0,
        "cpu_ms": (1000.0 / cpu_fps) if cpu_fps > 0 else 0.0,
        "hybrid_ms": (1000.0 / hybrid_fps) if hybrid_fps > 0 else 0.0,
        "best_device": best_device,
        "best_device_name": best_name,
        "best_fps": best_fps
    }


def format_benchmark_table(bench_data: Dict[str, Any]) -> Table:
    table = Table(title=f"Hardware Inference Benchmark ({bench_data['resolution']} - Model: {bench_data['model']})", style="cyan")
    table.add_column("Device Mode", style="bold white", justify="left")
    table.add_column("Throughput (FPS)", justify="right")
    table.add_column("Latency (ms/frame)", justify="right")
    table.add_column("Relative Speed", justify="right")
    table.add_column("Status", justify="center")

    cpu_fps = max(bench_data["cpu_fps"], 0.001)

    devices = [
        ("GPU (Vulkan)", bench_data["gpu_fps"], bench_data["gpu_ms"], DeviceType.GPU),
        ("CPU (Multi-thread)", bench_data["cpu_fps"], bench_data["cpu_ms"], DeviceType.CPU),
        ("Hybrid (GPU+CPU)", bench_data["hybrid_fps"], bench_data["hybrid_ms"], DeviceType.HYBRID),
    ]

    for name, fps, ms, dtype in devices:
        speedup = f"{fps / cpu_fps:.2f}x"
        is_best = (dtype == bench_data["best_device"])
        status = "[bold green]FASTEST[/bold green]" if is_best else "[dim]Alternative[/dim]"
        style = "green" if is_best else "white"

        table.add_row(
            f"[{style}]{name}[/{style}]",
            f"[{style}]{fps:.2f} FPS[/{style}]",
            f"[{style}]{ms:.1f} ms[/{style}]",
            f"[{style}]{speedup}[/{style}]",
            status
        )

    return table


def auto_select_device(
    model_info: Dict[str, Any],
    width: int,
    height: int,
    console: Optional[Console] = None
) -> DeviceType:
    if console:
        console.print("[dim cyan]Auto-detecting fastest hardware configuration...[/dim cyan]")

    bench = run_hardware_benchmark(
        model_name=model_info["name"],
        width=min(width, 384),
        height=min(height, 216),
        num_frames=3
    )

    if console:
        console.print(format_benchmark_table(bench))
        console.print(f"[bold green]Selected optimal device:[/bold green] [bold yellow]{bench['best_device_name']}[/bold yellow] ({bench['best_fps']:.2f} FPS)\n")

    return bench["best_device"]
