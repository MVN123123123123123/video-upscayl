import os
import sys
import unittest
from unittest.mock import patch

from video_upscaler.utils import get_hardware_info, get_ffmpeg_path, get_ffprobe_path, get_subprocess_kwargs
from video_upscaler.backend_bridge import find_library_path, VideoUpscalerBackend
from video_upscaler.cli import entry_point


class TestCrossPlatform(unittest.TestCase):
    def test_hardware_info(self):
        hw = get_hardware_info()
        self.assertIn("os_name", hw)
        self.assertIn("cpu_name", hw)
        self.assertIn("cpu_threads", hw)
        self.assertIn("cpu_simd", hw)
        self.assertIn("ram_gb", hw)
        self.assertIn("gpus", hw)
        self.assertGreater(hw["cpu_threads"], 0)
        self.assertGreater(hw["ram_gb"], 0.0)

    def test_ffmpeg_probe_discovery(self):
        ffmpeg = get_ffmpeg_path()
        ffprobe = get_ffprobe_path()
        self.assertTrue(os.path.exists(ffmpeg), f"FFmpeg binary not found: {ffmpeg}")
        self.assertTrue(os.path.exists(ffprobe), f"FFprobe binary not found: {ffprobe}")

    def test_subprocess_kwargs(self):
        kwargs = get_subprocess_kwargs()
        if sys.platform == "win32":
            self.assertIn("creationflags", kwargs)
            self.assertEqual(kwargs["creationflags"], 0x08000000)
        else:
            self.assertEqual(kwargs, {})

    def test_library_resolution(self):
        lib_path = find_library_path()
        self.assertTrue(os.path.exists(lib_path), f"Library not found: {lib_path}")

    def test_windows_gui_default_launch(self):
        """Verify that on Windows without --cli, entry_point invokes launch_gui directly."""
        mock_gui_module = unittest.mock.MagicMock()
        with patch.dict(sys.modules, {"video_upscaler.gui": mock_gui_module}), \
             patch("sys.platform", "win32"), \
             patch("sys.argv", ["video-upscaler"]):
            entry_point()
            mock_gui_module.launch_gui.assert_called_once()

    def test_appimage_gui_default_launch(self):
        """Verify that inside AppImage without CLI subcommands, entry_point invokes launch_gui."""
        mock_gui_module = unittest.mock.MagicMock()
        with patch.dict(sys.modules, {"video_upscaler.gui": mock_gui_module}), \
             patch.dict(os.environ, {"APPIMAGE": "/path/to/Video-Upscayl.AppImage"}), \
             patch("sys.argv", ["Video-Upscayl.AppImage"]):
            entry_point()
            mock_gui_module.launch_gui.assert_called_once()

    def test_entry_point_demo_invokes_cli(self):
        """Verify that 'demo' subcommand dispatches directly to CLI main."""
        with patch("video_upscaler.cli.main") as mock_main:
            with patch("sys.argv", ["video-upscaler", "demo", "--no-browser"]):
                entry_point()
                mock_main.assert_called_once()

    def test_candidate_model_dirs_and_writable_cache(self):
        from video_upscaler.models import get_candidate_model_dirs, get_writable_model_dir
        dirs = get_candidate_model_dirs()
        self.assertTrue(len(dirs) > 0)
        writable_dir = get_writable_model_dir()
        self.assertTrue(os.path.isdir(writable_dir))

    def test_model_alias_resolution(self):
        from video_upscaler.models import get_model_info
        # Test exact
        self.assertEqual(get_model_info("4x-UltraSharp")["name"], "4x-UltraSharp")
        self.assertEqual(get_model_info("realesr-animevideov3-x2")["name"], "realesr-animevideov3-x2")
        # Test friendly alias
        self.assertEqual(get_model_info("animevidv3-2x")["name"], "realesr-animevideov3-x2")
        self.assertEqual(get_model_info("animevideov3-2x")["name"], "realesr-animevideov3-x2")
        self.assertEqual(get_model_info("animevid-2x")["name"], "realesr-animevideov3-x2")
        self.assertEqual(get_model_info("ultrasharp")["name"], "4x-UltraSharp")
        # Test Real-CUGAN aliases
        self.assertEqual(get_model_info("realcugan")["name"], "realcugan-se-x2")
        self.assertEqual(get_model_info("cugan")["name"], "realcugan-se-x2")
        self.assertEqual(get_model_info("real-cugan")["name"], "realcugan-se-x2")
        self.assertEqual(get_model_info("cugan-2x")["name"], "realcugan-se-x2")
        self.assertEqual(get_model_info("cugan-3x")["name"], "realcugan-se-x3")
        self.assertEqual(get_model_info("realcugan-pro-x2")["name"], "realcugan-pro-x2")
        self.assertEqual(get_model_info("cugan-pro-2x")["name"], "realcugan-pro-x2")
        self.assertEqual(get_model_info("realcugan-se-x2")["tile_pad"], 18)
        self.assertEqual(get_model_info("realcugan-se-x3")["tile_pad"], 14)
        # Test scale matching without override
        self.assertEqual(get_model_info(None, scale=2)["scale"], 2)


if __name__ == "__main__":
    unittest.main()

