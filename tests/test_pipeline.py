import os
import unittest
import tempfile
import subprocess
from video_upscaler.pipeline import VideoUpscalePipeline
from video_upscaler.backend_bridge import DeviceType
from video_upscaler.utils import probe_video


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.input_video = os.path.join(self.temp_dir, "input.mp4")
        self.output_video = os.path.join(self.temp_dir, "output.mp4")

        # Generate 30 frames of 240x136 video with audio tone
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=240x136:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            self.input_video
        ]
        res = subprocess.run(cmd)
        self.assertEqual(res.returncode, 0)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_pipeline_cpu_upscale(self):
        cpu_output = os.path.join(self.temp_dir, "output_cpu.mp4")
        pipeline = VideoUpscalePipeline(
            input_path=self.input_video,
            output_path=cpu_output,
            model_name="realesr-animevideov3-x2",
            scale=2,
            device_type=DeviceType.CPU,
            tile_size=120,
            tile_pad=10
        )
        stats = pipeline.run(max_frames=10)

        self.assertEqual(stats["processed_frames"], 10)
        self.assertTrue(os.path.exists(cpu_output))
        self.assertGreater(os.path.getsize(cpu_output), 0)

        meta = probe_video(cpu_output)
        self.assertEqual(meta["width"], 480)
        self.assertEqual(meta["height"], 272)
        self.assertEqual(meta["audio_stream_count"], 1)

    def test_pipeline_gpu_upscale(self):
        from video_upscaler.backend_bridge import VideoUpscalerBackend
        if len(VideoUpscalerBackend().get_gpu_devices()) == 0:
            self.skipTest("No Vulkan GPU available on this system")

        pipeline = VideoUpscalePipeline(
            input_path=self.input_video,
            output_path=self.output_video,
            model_name="realesr-animevideov3-x2",
            scale=2,
            device_type=DeviceType.GPU,
            tile_size=256,
            tile_pad=10
        )
        stats = pipeline.run()

        self.assertEqual(stats["processed_frames"], 30)
        self.assertTrue(os.path.exists(self.output_video))
        self.assertGreater(os.path.getsize(self.output_video), 0)

        meta = probe_video(self.output_video)
        self.assertEqual(meta["width"], 480)
        self.assertEqual(meta["height"], 272)
        self.assertEqual(meta["audio_stream_count"], 1)

    def test_pipeline_hybrid_upscale(self):
        from video_upscaler.backend_bridge import VideoUpscalerBackend
        if len(VideoUpscalerBackend().get_gpu_devices()) == 0:
            self.skipTest("No Vulkan GPU available on this system")

        hybrid_output = os.path.join(self.temp_dir, "output_hybrid.mp4")
        pipeline = VideoUpscalePipeline(
            input_path=self.input_video,
            output_path=hybrid_output,
            model_name="realesr-animevideov3-x2",
            scale=2,
            device_type=DeviceType.HYBRID,
            tile_size=120,
            tile_pad=10
        )
        stats = pipeline.run()

        self.assertEqual(stats["processed_frames"], 30)
        self.assertTrue(os.path.exists(hybrid_output))
        meta = probe_video(hybrid_output)
        self.assertEqual(meta["width"], 480)
        self.assertEqual(meta["height"], 272)
        self.assertEqual(meta["audio_stream_count"], 1)

    def test_pipeline_realcugan_upscale(self):
        from video_upscaler.backend_bridge import VideoUpscalerBackend
        has_gpu = len(VideoUpscalerBackend().get_gpu_devices()) > 0
        cugan_output = os.path.join(self.temp_dir, "output_cugan.mp4")
        pipeline = VideoUpscalePipeline(
            input_path=self.input_video,
            output_path=cugan_output,
            model_name="cugan",
            device_type=DeviceType.GPU if has_gpu else DeviceType.CPU,
            tile_size=120
        )
        self.assertEqual(pipeline.tile_pad, 18)
        frames_to_run = None if has_gpu else 10
        stats = pipeline.run(max_frames=frames_to_run)

        expected_count = 30 if has_gpu else 10
        self.assertEqual(stats["processed_frames"], expected_count)
        self.assertTrue(os.path.exists(cugan_output))
        meta = probe_video(cugan_output)
        self.assertEqual(meta["width"], 480)
        self.assertEqual(meta["height"], 272)
        self.assertEqual(meta["audio_stream_count"], 1)


if __name__ == "__main__":
    unittest.main()
