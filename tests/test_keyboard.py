"""Exercise keyboard login setup without changing a real desktop or console."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "Scripts/linux/files/set-keyboard.sh"
XFCONF_STUB = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

path = Path(os.environ["KEYBOARD_TEST_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
assert args[:2] == ["--channel", "keyboard-layout"]
assert "--create" in args
prop = args[args.index("--property") + 1]
value = args[args.index("--set") + 1]
kind = args[args.index("--type") + 1]
if prop == state.get("fail_property"):
    sys.exit(1)
state["calls"].append([prop, kind, value])
state["values"][prop] = [kind, value]
path.write_text(json.dumps(state))
'''


class KeyboardHelperTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workbox-keyboard-test-")
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        self.state_path = directory / "state.json"
        command = directory / "xfconf-query"
        command.write_text(XFCONF_STUB)
        command.chmod(0o755)
        self.environment = dict(os.environ,
                                PATH=str(directory) + os.pathsep + os.environ["PATH"],
                                KEYBOARD_TEST_STATE=str(self.state_path))
        self.initial = {"calls": [], "values": {
            "/Default/XkbLayout": ["string", "us"],
            "/Default/XkbVariant": ["string", "dvorak"],
            "/Default/XkbDisable": ["bool", "false"],
            "/Default/XkbModel": ["string", "pc105"],
            "/Default/XkbOptions/Compose": ["string", "compose:rwin"],
        }}
        self.state_path.write_text(json.dumps(self.initial))

    def state(self):
        return json.loads(self.state_path.read_text())

    def run_helper(self, *arguments):
        return subprocess.run(["bash", str(HELPER), *arguments], env=self.environment,
                              capture_output=True, text=True, timeout=10)

    def test_swedish_replaces_stale_layout_and_variant_only(self):
        result = self.run_helper("se")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertEqual(state["calls"], [
            ["/Default/XkbDisable", "bool", "true"],
            ["/Default/XkbLayout", "string", "se"],
            ["/Default/XkbVariant", "string", ""],
            ["/Default/XkbDisable", "bool", "false"],
        ])
        for prop in ("/Default/XkbModel", "/Default/XkbOptions/Compose"):
            self.assertEqual(state["values"][prop], self.initial["values"][prop])

    def test_layout_remains_configurable(self):
        result = self.run_helper("se,us")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state()["values"]["/Default/XkbLayout"], ["string", "se,us"])

    def test_repeated_runs_preserve_the_same_settings(self):
        first = self.run_helper("se")
        self.assertEqual(first.returncode, 0, first.stderr)
        values = self.state()["values"]
        second = self.run_helper("se")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.state()["values"], values)

    def test_missing_or_invalid_layout_is_rejected_before_writes(self):
        cases = [(), ("",), ("se us",), ("se;id",), ("se\n",), ("se'",), ("se,",), ("--help",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = self.run_helper(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.state(), self.initial)

    def test_settings_failure_stops_configuration(self):
        state = self.state()
        state["fail_property"] = "/Default/XkbLayout"
        self.state_path.write_text(json.dumps(state))
        result = self.run_helper("se")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.state()["calls"]), 1)


if __name__ == "__main__":
    unittest.main()
