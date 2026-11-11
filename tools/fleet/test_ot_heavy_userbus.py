"""USERBUS_1111 (KW-FIX-44, COORD 11-11): ot-heavy sets XDG_RUNTIME_DIR / DBUS_SESSION_BUS_ADDRESS from the lingering
user manager when the ssh session did not (pam_systemd CreateSession failed), so systemd-run --user can reach the bus."""
import os
import subprocess
import unittest
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "ot-heavy").read_text()
HEAD = SRC[SRC.index("# USERBUS_1111"):SRC.index('MEM=""; TAG=""')]
BUS = Path(f"/run/user/{os.getuid()}/bus")


class UserBus(unittest.TestCase):
    def run_head(self, env):
        out = subprocess.run(["bash", "-c", "set -u\n" + HEAD + 'echo "${XDG_RUNTIME_DIR:-}|${DBUS_SESSION_BUS_ADDRESS:-}"'],
                             env=env, capture_output=True, text=True, check=True)
        return out.stdout.strip()

    @unittest.skipUnless(BUS.is_socket(), "no lingering user bus here")
    def test_missing_session_env_uses_user_manager_bus(self):
        self.assertEqual(self.run_head({"PATH": os.environ["PATH"]}),
                         f"/run/user/{os.getuid()}|unix:path=/run/user/{os.getuid()}/bus")

    def test_existing_env_is_kept(self):
        env = {"PATH": os.environ["PATH"], "XDG_RUNTIME_DIR": "/x", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/y"}
        self.assertEqual(self.run_head(env), "/x|unix:path=/y")

    def test_block_runs_before_any_systemd_run(self):
        self.assertLess(SRC.index("# USERBUS_1111"), SRC.index("systemd-run"))


if __name__ == "__main__":
    unittest.main()
