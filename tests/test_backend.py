import os
import unittest
import numpy as np
from video_upscaler.backend_bridge import VideoUpscalerBackend, DeviceType


class TestBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = VideoUpscalerBackend()
        cls.model_bin = "models/realesr-animevideov3-x2.bin"
        cls.model_param = "models/realesr-animevideov3-x2.param"
        assert os.path.exists(cls.model_bin), f"Model bin not found: {cls.model_bin}"
        assert os.path.exists(cls.model_param), f"Model param not found: {cls.model_param}"

    def test_cpu_simd_detection(self):
        simd = self.backend.get_cpu_simd_info()
        self.assertIsInstance(simd, str)
        self.assertGreater(len(simd), 0)
        # Should detect one of the valid SIMD families
        valid_families = ["AVX", "SSE", "NEON", "ARM", "RISC-V", "Standard"]
        self.assertTrue(any(v in simd for v in valid_families), f"Unexpected SIMD string: {simd}")

    def test_gpu_discovery(self):
        gpus = self.backend.get_gpu_devices()
        self.assertIsInstance(gpus, list)
        if len(gpus) == 0:
            self.skipTest("No Vulkan GPU devices found on this system (headless CI runner)")
        self.assertGreaterEqual(len(gpus), 1)
        # Vendor-neutral validation: check that name and vendor are reported cleanly
        first_gpu = gpus[0]
        self.assertIn("name", first_gpu)
        self.assertIn("vendor", first_gpu)
        self.assertIn("type", first_gpu)
        self.assertGreater(len(first_gpu["name"]), 0)
        self.assertGreater(len(first_gpu["vendor"]), 0)

    def test_gpu_diagnostic_telemetry(self):
        diag = self.backend.get_gpu_diagnostic_info()
        self.assertIsInstance(diag, str)
        self.assertGreater(len(diag), 0)

    def test_auto_upscale(self):
        session = self.backend.create_instance(
            model_path=self.model_bin,
            param_path=self.model_param,
            scale=2,
            device_type=DeviceType.AUTO,
            tile_size=128,
            tile_pad=10
        )
        in_frame = np.full((64, 64, 3), 110, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (128, 128, 3))
        self.assertEqual(out_frame.dtype, np.uint8)
        session.close()

    def test_gpu_upscale(self):
        if len(self.backend.get_gpu_devices()) == 0:
            self.skipTest("No Vulkan GPU available on this system")
        session = self.backend.create_instance(
            model_path=self.model_bin,
            param_path=self.model_param,
            scale=2,
            device_type=DeviceType.GPU,
            tile_size=256,
            tile_pad=10
        )
        in_frame = np.full((128, 128, 3), 120, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (256, 256, 3))
        self.assertEqual(out_frame.dtype, np.uint8)
        session.close()

    def test_cpu_upscale(self):
        session = self.backend.create_instance(
            model_path=self.model_bin,
            param_path=self.model_param,
            scale=2,
            device_type=DeviceType.CPU,
            tile_size=256,
            tile_pad=10
        )
        in_frame = np.full((64, 64, 3), 100, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (128, 128, 3))
        session.close()

    def test_hybrid_upscale(self):
        if len(self.backend.get_gpu_devices()) == 0:
            self.skipTest("No Vulkan GPU available on this system")
        session = self.backend.create_instance(
            model_path=self.model_bin,
            param_path=self.model_param,
            scale=2,
            device_type=DeviceType.HYBRID,
            tile_size=100,
            tile_pad=10
        )
        # 200x200 with tile_size 100 produces 4 tiles distributed across GPU and CPU
        in_frame = np.full((200, 200, 3), 150, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (400, 400, 3))
        session.close()

    def test_tile_seam_continuity(self):
        dev = DeviceType.GPU if len(self.backend.get_gpu_devices()) > 0 else DeviceType.CPU
        session = self.backend.create_instance(
            model_path=self.model_bin,
            param_path=self.model_param,
            scale=2,
            device_type=dev,
            tile_size=100,
            tile_pad=10
        )
        # Linear gradient image
        x = np.linspace(50, 200, 200, dtype=np.uint8)
        y = np.linspace(50, 200, 200, dtype=np.uint8)
        xx, yy = np.meshgrid(x, y)
        img = np.stack([xx, yy, xx], axis=-1).astype(np.uint8)

        out = session.process_frame(img)
        # Check boundary seam at x=200
        seam_diff = np.abs(out[:, 199, :].astype(int) - out[:, 200, :].astype(int))
        mean_diff = np.mean(seam_diff)
        self.assertLess(mean_diff, 5.0, f"Seam difference too high: {mean_diff}")
        session.close()

    def test_realcugan_gpu_upscale(self):
        cugan_bin = "models/realcugan-se-x2.bin"
        cugan_param = "models/realcugan-se-x2.param"
        if not os.path.exists(cugan_bin) or not os.path.exists(cugan_param):
            self.skipTest("Real-CUGAN model files not found locally")
        if len(self.backend.get_gpu_devices()) == 0:
            self.skipTest("No Vulkan GPU available on this system")

        session = self.backend.create_instance(
            model_path=cugan_bin,
            param_path=cugan_param,
            scale=2,
            device_type=DeviceType.GPU,
            tile_size=100,
            tile_pad=18
        )
        in_frame = np.full((128, 128, 3), 120, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (256, 256, 3))
        self.assertEqual(out_frame.dtype, np.uint8)
        session.close()

    def test_realcugan_cpu_upscale(self):
        cugan_bin = "models/realcugan-se-x2.bin"
        cugan_param = "models/realcugan-se-x2.param"
        if not os.path.exists(cugan_bin) or not os.path.exists(cugan_param):
            self.skipTest("Real-CUGAN model files not found locally")

        session = self.backend.create_instance(
            model_path=cugan_bin,
            param_path=cugan_param,
            scale=2,
            device_type=DeviceType.CPU,
            tile_size=64,
            tile_pad=18
        )
        in_frame = np.full((64, 64, 3), 100, dtype=np.uint8)
        out_frame = session.process_frame(in_frame)
        self.assertEqual(out_frame.shape, (128, 128, 3))
        session.close()

    def test_realcugan_tile_seam_continuity(self):
        cugan_bin = "models/realcugan-se-x2.bin"
        cugan_param = "models/realcugan-se-x2.param"
        if not os.path.exists(cugan_bin) or not os.path.exists(cugan_param):
            self.skipTest("Real-CUGAN model files not found locally")
        dev = DeviceType.GPU if len(self.backend.get_gpu_devices()) > 0 else DeviceType.CPU

        session = self.backend.create_instance(
            model_path=cugan_bin,
            param_path=cugan_param,
            scale=2,
            device_type=dev,
            tile_size=100,
            tile_pad=18
        )
        # Linear gradient image
        x = np.linspace(50, 200, 200, dtype=np.uint8)
        y = np.linspace(50, 200, 200, dtype=np.uint8)
        xx, yy = np.meshgrid(x, y)
        img = np.stack([xx, yy, xx], axis=-1).astype(np.uint8)

        out = session.process_frame(img)
        # Check boundary seam at x=200
        seam_diff = np.abs(out[:, 199, :].astype(int) - out[:, 200, :].astype(int))
        mean_diff = np.mean(seam_diff)
        self.assertLess(mean_diff, 5.0, f"Real-CUGAN seam difference too high: {mean_diff}")
        session.close()

    def test_realcugan_x3_tile_seam_and_zero_black_bars(self):
        cugan_bin = "models/realcugan-pro-x3-denoise3x.bin"
        cugan_param = "models/realcugan-pro-x3-denoise3x.param"
        if not os.path.exists(cugan_bin) or not os.path.exists(cugan_param):
            cugan_bin = "models/realcugan-se-x3.bin"
            cugan_param = "models/realcugan-se-x3.param"
        if not os.path.exists(cugan_bin) or not os.path.exists(cugan_param):
            self.skipTest("Real-CUGAN 3x model files not found locally")

        dev = DeviceType.GPU if len(self.backend.get_gpu_devices()) > 0 else DeviceType.CPU

        session = self.backend.create_instance(
            model_path=cugan_bin,
            param_path=cugan_param,
            scale=3,
            device_type=dev,
            tile_size=100,
            tile_pad=14
        )
        # 200x200 image across 4 tiles
        x = np.linspace(60, 210, 200, dtype=np.uint8)
        y = np.linspace(60, 210, 200, dtype=np.uint8)
        xx, yy = np.meshgrid(x, y)
        img = np.stack([xx, yy, xx], axis=-1).astype(np.uint8)

        out = session.process_frame(img)
        self.assertEqual(out.shape, (600, 600, 3))

        # Check there are 0 black pixels anywhere in the upscaled output
        black_pixels = np.all(out == 0, axis=-1)
        self.assertEqual(int(np.sum(black_pixels)), 0, "Real-CUGAN 3x produced black bar/edge pixels!")

        # Check seam continuity at tile boundary x=300 (which corresponds to x=100 * scale 3)
        seam_diff = np.abs(out[:, 299, :].astype(int) - out[:, 300, :].astype(int))
        mean_diff = np.mean(seam_diff)
        self.assertLess(mean_diff, 5.0, f"Real-CUGAN 3x seam difference too high: {mean_diff}")
        session.close()


if __name__ == "__main__":
    unittest.main()
