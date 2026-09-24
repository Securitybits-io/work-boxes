"""Exercise wallpaper setup on fresh profiles using fake X11/Xfconf commands."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "Scripts/linux/files/set-wallpaper.sh"
COMMAND_STUB = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

path = Path(os.environ["WALLPAPER_TEST_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
if Path(sys.argv[0]).name == "xrandr":
    assert args == ["--query"]
    if state.get("fail_query"):
        sys.exit(1)
    print(state["outputs"])
    sys.exit(0)
assert args[:2] == ["--channel", "xfce4-desktop"]
assert "--list" not in args
if state.get("fail_set"):
    sys.exit(1)
prop = args[args.index("--property") + 1]
value = args[args.index("--set") + 1]
kind = args[args.index("--type") + 1]
assert "--create" in args
state["values"][prop] = [kind, value]
path.write_text(json.dumps(state))
'''

OUTPUTS = """Screen 0: minimum 16 x 16, current 3840 x 1080, maximum 32767 x 32767
Virtual-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 508mm x 286mm
   1920x1080     60.00*+
HDMI-2 connected 1920x1080-1920+0 (normal left inverted right x axis y axis) 508mm x 286mm
DP-1 connected (normal left inverted right x axis y axis)
HDMI-3 disconnected (normal left inverted right x axis y axis)
"""


class WallpaperHelperTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workbox-wallpaper-test-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.state_path = self.directory / "state.json"
        self.image = self.directory / "wallpaper with spaces.png"
        self.image.touch()
        for name in ("xfconf-query", "xrandr"):
            command = self.directory / name
            command.write_text(COMMAND_STUB)
            command.chmod(0o755)
        self.environment = dict(os.environ,
                                PATH=str(self.directory) + os.pathsep + os.environ["PATH"],
                                WALLPAPER_TEST_STATE=str(self.state_path), XDG_SESSION_TYPE="x11")

    def configure(self, outputs=OUTPUTS, **options):
        state = {"outputs": outputs, "values": {}}
        state.update(options)
        self.state_path.write_text(json.dumps(state))

    def run_helper(self, image=None):
        return subprocess.run(["bash", str(HELPER), str(image or self.image)],
                              env=self.environment, capture_output=True, text=True, timeout=15)

    def state(self):
        return json.loads(self.state_path.read_text())

    def test_active_displays_and_all_workspaces_are_configured_repeatably(self):
        images = [
            "/backdrop/screen0/monitorVirtual-1/workspace0/last-image",
            "/backdrop/screen0/monitorHDMI-2/workspace0/last-image",
        ]
        self.configure(values={"/desktop-icons/style": ["int", "2"]})
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        values = self.state()["values"]
        for prop in images:
            prefix = prop.rsplit("/", 1)[0]
            self.assertEqual(values[prop], ["string", str(self.image)])
            self.assertEqual(values[prefix + "/image-style"], ["int", "5"])
            self.assertEqual(values[prefix + "/backdrop-cycle-enable"], ["bool", "false"])
        self.assertEqual(values["/desktop-icons/style"], ["int", "2"])
        self.assertEqual(values["/backdrop/single-workspace-mode"], ["bool", "true"])
        self.assertEqual(values["/backdrop/single-workspace-number"], ["int", "0"])
        self.assertFalse(any("monitorDP-1/" in key or "monitorHDMI-3/" in key for key in values))
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state()["values"], values)

    def test_fresh_profile_and_nonzero_screen_need_no_existing_properties(self):
        self.configure(OUTPUTS.replace("Screen 0:", "Screen 1:"))
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state()["values"]["/backdrop/screen1/monitorVirtual-1/workspace0/last-image"],
                         ["string", str(self.image)])

    def test_missing_image_is_rejected_before_querying_settings(self):
        self.configure()
        result = self.run_helper(self.directory / "missing.png")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not readable", result.stderr)
        self.assertEqual(self.state()["values"], {})

    def test_no_active_display_is_reported_without_changing_settings(self):
        self.configure("Screen 0: minimum 16 x 16, current 0 x 0, maximum 32767 x 32767\nDP-1 disconnected")
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No active X11 displays", result.stderr)
        self.assertEqual(self.state()["values"], {})

    def test_settings_write_failure_is_not_hidden(self):
        self.configure(fail_set=True)
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state()["values"], {})

    def test_display_query_failure_is_not_hidden(self):
        self.configure(fail_query=True)
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state()["values"], {})

    def test_invalid_display_response_is_rejected(self):
        self.configure("unexpected output")
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot determine the X11 screen", result.stderr)
        self.assertEqual(self.state()["values"], {})

    def test_wayland_is_rejected_instead_of_configuring_xwayland(self):
        self.configure()
        self.environment["XDG_SESSION_TYPE"] = "wayland"
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an Xfce X11 session", result.stderr)
        self.assertEqual(self.state()["values"], {})


if __name__ == "__main__":
    unittest.main()
