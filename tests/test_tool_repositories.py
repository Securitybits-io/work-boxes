"""Run repository tasks against temporary local Git repos, without sudo or APT."""

import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ToolRepositoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workbox-repositories-test-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.home = self.directory / "home"
        self.home.mkdir()
        self.environment = dict(os.environ, ANSIBLE_NOCOLOR="1",
                                ANSIBLE_LOCAL_TEMP=str(self.directory / "ansible-local"),
                                ANSIBLE_REMOTE_TEMP=str(self.directory / "ansible-remote"),
                                GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                                GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                                GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
        source = ROOT / "Scripts/linux/ansible/tool-repositories.yml"
        plays = yaml.safe_load(source.read_text())
        # Exercise the production tasks, replacing only host-level prerequisites.
        plays[0]["vars_files"] = [str(ROOT / "Scripts/linux/vars.yml")]
        plays[0]["tasks"] = [t for t in plays[0]["tasks"] if "ansible.builtin.apt" not in t]
        self.playbook = self.directory / "playbook.yml"
        self.playbook.write_text(yaml.safe_dump(plays))
        self.extra_vars = self.directory / "vars.json"

    def run_play(self, repositories, success=True):
        self.extra_vars.write_text(json.dumps({
            "linux": {"user": {"name": pwd.getpwuid(os.getuid()).pw_name}},
            "ansible_become": False,
            "ansible_python_interpreter": "/usr/bin/python3",
            "workbox_tools_home": str(self.home),
            "workbox_tool_repositories": repositories,
        }))
        result = subprocess.run([
            "ansible-playbook", "-i", "localhost,", "-c", "local", str(self.playbook),
            "--extra-vars", "@" + str(self.extra_vars),
        ], cwd=self.directory, env=self.environment, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        if success:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("assertion", output)
        return output

    def git(self, directory, *args):
        result = subprocess.run(["git", "-C", str(directory), *args], env=self.environment,
                                capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip()

    def test_empty_list_creates_user_owned_folder_and_is_idempotent(self):
        self.run_play([])
        folder = self.home / "tools"
        self.assertTrue(folder.is_dir())
        self.assertEqual(folder.stat().st_uid, os.getuid())
        self.assertEqual(list(folder.iterdir()), [])
        self.assertRegex(self.run_play([]), r"changed=0\s")

    def test_clones_versions_without_updating_or_removing_existing_work(self):
        source = self.directory / "source"
        source.mkdir()
        self.git(source, "init", "-b", "main")
        content = source / "tool.txt"
        content.write_text("initial\n")
        self.git(source, "add", ".")
        self.git(source, "commit", "-m", "Initial")
        self.git(source, "tag", "v1")
        content.write_text("latest\n")
        self.git(source, "commit", "-am", "Update")
        entries = [
            {"name": "default-tool", "repo": str(source)},
            {"name": "pinned-tool", "repo": str(source), "version": "v1"},
        ]
        self.run_play(entries)
        default = self.home / "tools/default-tool"
        pinned = self.home / "tools/pinned-tool"
        self.assertEqual((default / "tool.txt").read_text(), "latest\n")
        self.assertEqual((pinned / "tool.txt").read_text(), "initial\n")
        self.assertEqual((default / ".git").stat().st_uid, os.getuid())
        self.assertRegex(self.run_play(entries), r"changed=0\s")

        content.write_text("remote update\n")
        self.git(source, "commit", "-am", "Remote update")
        (default / "tool.txt").write_text("local commit\n")
        self.git(default, "commit", "-am", "Local work")
        local_head = self.git(default, "rev-parse", "HEAD")
        (default / "tool.txt").write_text("uncommitted work\n")
        (default / "notes.txt").write_text("untracked work\n")
        entries[1]["version"] = "main"
        self.assertRegex(self.run_play(entries), r"changed=0\s")
        self.assertEqual(self.git(default, "rev-parse", "HEAD"), local_head)
        self.assertEqual((default / "tool.txt").read_text(), "uncommitted work\n")
        self.assertEqual((default / "notes.txt").read_text(), "untracked work\n")
        self.assertEqual((pinned / "tool.txt").read_text(), "initial\n")
        self.run_play([])
        self.assertTrue(default.is_dir())
        self.assertTrue(pinned.is_dir())

    def test_invalid_configuration_is_rejected_before_directory_creation(self):
        valid = {"name": "tool", "repo": "https://example.invalid/tool.git"}
        invalid = [
            "not-a-list", {}, ["not-a-mapping"],
            [dict(valid, name="../outside")], [dict(valid, name="/absolute")],
            [dict(valid, name="trailing\n")], [dict(valid, repo="")],
            [dict(valid, version=123)], [valid, valid],
        ]
        for entries in invalid:
            with self.subTest(repositories=entries):
                self.run_play(entries, success=False)
                self.assertFalse((self.home / "tools").exists())


if __name__ == "__main__":
    unittest.main()
