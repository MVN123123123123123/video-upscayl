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

    def test_pipeline_gpu_upscale(self):
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


if __name__ == "__main__":
    unittest.main()
