"""Static provisioning contracts; never read local credentials or run a VM."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
LINUX = ROOT / "Scripts/linux"


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def play(name):
    return read_yaml(LINUX / "ansible" / f"{name}.yml")[0]


def module_args(tasks, module):
    return next(task[module] for task in tasks if module in task)


class ProvisioningContracts(unittest.TestCase):
    def test_account_settings_are_namespaced_and_derived_from_engagement(self):
        defaults = read_yaml(LINUX / "vars.yml")
        self.assertTrue(all(key.startswith("workbox_") for key in defaults))
        self.assertEqual(defaults["workbox_user_name"], "{{ linux.user.name }}")
        self.assertEqual(defaults["workbox_user_password_hash"], "{{ linux.user.password_hash }}")
        self.assertIn("/config/engagement.yml", (ROOT / ".gitignore").read_text())
        account = play("user")
        user = module_args(account["tasks"], "ansible.builtin.user")
        self.assertEqual(user["name"], "{{ workbox_user_name }}")
        self.assertEqual(user["password"], "{{ workbox_user_password_hash }}")
        self.assertEqual(user["update_password"], "on_create")
        self.assertIs(user["append"], True)
        account_task = next(t for t in account["tasks"] if "ansible.builtin.user" in t)
        self.assertIs(account_task["no_log"], True)

    def test_account_consumers_load_the_same_engagement_file(self):
        for name in ("user", "docker", "dotfiles", "wallpaper", "tool-repositories"):
            with self.subTest(playbook=name):
                self.assertEqual(play(name)["vars_files"], [
                    "../vars.yml",
                    "{{ workbox_engagement_vars_file | default('../../../config/engagement.yml') }}",
                ])

    def test_engagement_template_requires_a_local_password_hash(self):
        example = read_yaml(ROOT / "config/engagement.example.yml")
        self.assertEqual(example["linux"]["user"]["name"], "user")
        self.assertEqual(example["linux"]["user"]["password_hash"], "")
        self.assertFalse((LINUX / "vars.local.example.yml").exists())

    def test_docker_and_dotfiles_use_the_configured_user(self):
        docker = module_args(play("docker")["tasks"], "ansible.builtin.user")
        self.assertEqual(docker["name"], "{{ workbox_user_name }}")
        self.assertIs(docker["append"], True)
        dotfiles = play("dotfiles")
        user_block = next(t for t in dotfiles["tasks"] if "block" in t)
        self.assertEqual(user_block["become_user"], "{{ workbox_user_name }}")
        self.assertIn("workbox_user_name", dotfiles["vars"]["dotfiles_home"])

    def test_tool_repositories_use_the_user_home_and_preserve_existing_clones(self):
        self.assertIsInstance(read_yaml(LINUX / "vars.yml")["workbox_tool_repositories"], list)
        repositories = play("tool-repositories")
        self.assertEqual(repositories["vars"]["workbox_tools_home"],
                         "{{ ansible_facts.getent_passwd[workbox_user_name][4] }}")
        self.assertEqual(repositories["vars"]["workbox_tools_directory"], "{{ workbox_tools_home }}/tools")
        packages = module_args(repositories["tasks"], "ansible.builtin.apt")
        self.assertEqual(set(packages["name"]), {"acl", "git"})
        user_block = next(t for t in repositories["tasks"] if "block" in t)
        self.assertIs(user_block["become"], True)
        self.assertEqual(user_block["become_user"], "{{ workbox_user_name }}")
        self.assertEqual(user_block["environment"]["HOME"], "{{ workbox_tools_home }}")
        self.assertEqual(user_block["environment"]["GIT_TERMINAL_PROMPT"], "0")
        folder = module_args(user_block["block"], "ansible.builtin.file")
        self.assertEqual(folder["path"], "{{ workbox_tools_directory }}")
        self.assertEqual(folder["state"], "directory")
        git_task = next(t for t in user_block["block"] if "ansible.builtin.git" in t)
        self.assertEqual(git_task["loop"], "{{ workbox_tool_repositories }}")
        git = git_task["ansible.builtin.git"]
        self.assertEqual(git["dest"], "{{ workbox_tools_directory }}/{{ item.name }}")
        self.assertEqual(git["version"], "{{ item.version | default('HEAD') }}")
        self.assertIs(git["update"], False)
        self.assertIs(git["force"], False)

    def test_packages_have_one_owner_and_are_batched(self):
        tools = play("tools")
        task = tools["tasks"][0]
        self.assertNotIn("loop", task)
        self.assertNotIn("with_items", task)
        apt = task["ansible.builtin.apt"]
        self.assertIn("unique", apt["name"])
        self.assertGreater(apt["cache_valid_time"], 0)
        packages = tools["vars"]["workbox_base_tools"] + read_yaml(LINUX / "vars.yml")["workbox_extra_tools"]
        self.assertEqual(len(packages), len(set(packages)))
        dotfiles_packages = module_args(play("dotfiles")["tasks"], "ansible.builtin.apt")["name"]
        self.assertFalse(set(packages) & set(dotfiles_packages))

    def test_wallpaper_is_installed_for_the_engagement_user(self):
        wallpaper = play("wallpaper")
        packages = module_args(wallpaper["tasks"], "ansible.builtin.apt")["name"]
        self.assertIn("xfconf", packages)
        self.assertIn("x11-xserver-utils", packages)
        copies = [task["ansible.builtin.copy"] for task in wallpaper["tasks"] if "ansible.builtin.copy" in task]
        image = next(task for task in copies if task.get("src", "").endswith("kali-bg.png"))
        self.assertTrue((LINUX / "ansible" / image["src"]).resolve().is_file())
        with (ROOT / "config/files/kali-bg.png").open("rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
        self.assertTrue(image["dest"].startswith("/usr/local/share/backgrounds/"))
        autostart = next(task for task in copies if task["dest"].endswith(".desktop"))
        self.assertEqual(autostart["owner"], "{{ workbox_user_name }}")
        self.assertIn("OnlyShowIn=XFCE;", autostart["content"])
        self.assertIn(image["dest"], autostart["content"])
        self.assertIn("workbox_user_name", wallpaper["vars"]["workbox_wallpaper_home"])

    def test_keyboard_updates_system_defaults_cache_and_xfce(self):
        self.assertEqual(read_yaml(ROOT / "config/defaults.yml")["linux"]["locale"]["keyboard"], "se")
        locale = play("locale")
        system = next(task for task in locale["tasks"] if "ansible.builtin.lineinfile" in task)
        self.assertEqual(system["ansible.builtin.lineinfile"]["path"], "/etc/default/keyboard")
        self.assertEqual(system["loop"], [
            {"key": "XKBLAYOUT", "value": "{{ workbox_keyboard }}"},
            {"key": "XKBVARIANT", "value": ""},
        ])
        handlers = {task["name"]: task["ansible.builtin.command"]["argv"] for task in locale["handlers"]}
        self.assertEqual(set(system["notify"]), set(handlers))
        self.assertIn(["setupcon", "--keyboard-only", "--save-only"], handlers.values())
        self.assertIn(["udevadm", "trigger", "--subsystem-match=input", "--action=change"], handlers.values())
        copies = [task["ansible.builtin.copy"] for task in locale["tasks"] if "ansible.builtin.copy" in task]
        helper = next(task for task in copies if task.get("src", "").endswith("set-keyboard.sh"))
        self.assertTrue((LINUX / "ansible" / helper["src"]).resolve().is_file())
        autostart = next(task for task in copies if task["dest"].endswith(".desktop"))
        self.assertEqual(autostart["dest"], "/etc/xdg/autostart/workbox-keyboard.desktop")
        self.assertIn("OnlyShowIn=XFCE;", autostart["content"])
        self.assertIn("Exec=" + helper["dest"] + " {{ workbox_keyboard }}", autostart["content"])
        autostart_task = next(task for task in locale["tasks"] if task.get("ansible.builtin.copy") == autostart)
        self.assertEqual(set(autostart_task["notify"]), set(handlers))
        vagrant = (ROOT / "Vagrantfile").read_text()
        self.assertIn("linux_keyboard.match?(keyboard_pattern)", vagrant)

    def test_collection_bootstrap_is_declared(self):
        requirements = read_yaml(LINUX / "requirements.yml")
        self.assertIn("community.general", [c["name"] for c in requirements["collections"]])
        vagrant = (ROOT / "Vagrantfile").read_text()
        self.assertIn('ansible.galaxy_role_file = "./Scripts/linux/requirements.yml"', vagrant)
        self.assertIn("ansible-galaxy collection install --requirements-file=%{role_file}", vagrant)

    def test_validation_uses_locked_dummy_credentials(self):
        fixture = read_yaml(ROOT / "tests/fixtures/vars.yml")
        self.assertEqual(fixture["linux"]["user"]["password_hash"], "!")
        self.assertEqual(fixture["linux"]["user"]["name"], "validation-user")
        lint = read_yaml(ROOT / ".ansible-lint")
        self.assertIn("tests/fixtures/vars.yml", lint["extra_vars"]["workbox_engagement_vars_file"])

    def test_provisioning_order_and_scope(self):
        imports = [p["ansible.builtin.import_playbook"] for p in read_yaml(LINUX / "playbook.yml")]
        self.assertLess(imports.index("ansible/user.yml"), imports.index("ansible/docker.yml"))
        self.assertLess(imports.index("ansible/dotfiles.yml"), imports.index("ansible/wallpaper.yml"))
        self.assertLess(imports.index("ansible/user.yml"), imports.index("ansible/tool-repositories.yml"))
        self.assertLess(imports.index("ansible/docker.yml"), imports.index("ansible/bloodhound.yml"))
        self.assertEqual(len(imports), len(set(imports)))
        self.assertFalse(any("adaptix" in name.lower() for name in imports))


if __name__ == "__main__":
    unittest.main()
