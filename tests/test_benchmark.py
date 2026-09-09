import unittest
from video_upscaler.benchmark import run_hardware_benchmark, DeviceType
from video_upscaler.backend_bridge import VideoUpscalerBackend


class TestBenchmark(unittest.TestCase):
    def test_run_benchmark(self):
        result = run_hardware_benchmark(
            model_name="realesr-animevideov3-x2",
            width=256,
            height=256,
            num_frames=2
        )
        self.assertIn("gpu_fps", result)
        self.assertIn("cpu_fps", result)
        self.assertIn("hybrid_fps", result)
        self.assertGreater(result["cpu_fps"], 0.0)
        self.assertGreater(result["best_fps"], 0.0)
        self.assertIn(result["best_device"], [DeviceType.GPU, DeviceType.CPU, DeviceType.HYBRID])

        # If a Vulkan GPU is present, verify GPU and Hybrid throughput
        backend = VideoUpscalerBackend()
        if len(backend.get_gpu_devices()) > 0:
            self.assertGreater(result["gpu_fps"], 0.0)
            self.assertGreater(result["hybrid_fps"], 0.0)


if __name__ == "__main__":
    unittest.main()
