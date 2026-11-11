"""ot-udevd-guard (KW-FIX-44, COORD 11-10): restart systemd-udevd above OT_UDEVD_MAX_GB RSS, log it, else do nothing."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Guard(unittest.TestCase):
    def run_(self, rss_kb, **env):
        d = Path(tempfile.mkdtemp())
        (d / "bin").mkdir()
        proc = d / "proc" / "4242"
        proc.mkdir(parents=True)
        (proc / "status").write_text(f"Name:\tsystemd-udevd\nVmRSS:\t{rss_kb} kB\n")
        w = lambda n, b: ((d / "bin" / n).write_text("#!/bin/bash\n" + b + "\n"), (d / "bin" / n).chmod(0o755))
        w("systemctl", 'echo "$*" >> "$CALLS"; case "$*" in *MainPID*) cat "$PIDF";; esac')
        w("sudo", '[ "$1" = -n ] && shift; echo 4343 > "$PIDF"; "$@"')
        (d / "pid").write_text("4242\n")
        s = (HERE / "ot-udevd-guard").read_text().replace('"/proc/$pid/status"', f'"{d}/proc/$pid/status"')
        g = d / "guard"
        g.write_text(s)
        g.chmod(0o755)
        e = dict(os.environ, PATH=f"{d}/bin:" + os.environ["PATH"], CALLS=str(d / "calls"), PIDF=str(d / "pid"),
                 OT_UDEVD_LOG=str(d / "log"), **env)
        r = subprocess.run([str(g)], capture_output=True, text=True, env=e, timeout=30)
        calls = (d / "calls").read_text() if (d / "calls").exists() else ""
        log = (d / "log").read_text() if (d / "log").exists() else ""
        return r, calls, log

    def test_below_limit_no_restart(self):
        r, calls, log = self.run_(3 * 1024 * 1024)
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("restart", calls)
        self.assertEqual(log, "")

    def test_above_limit_restarts_and_logs(self):
        r, calls, log = self.run_(int(4.5 * 1024 * 1024))
        self.assertIn("restart systemd-udevd.service", calls)
        self.assertIn("RESTART systemd-udevd pid 4242 RSS 4.5 GB > 4 GB: ok (new pid 4343)", log)

    def test_limit_from_env(self):
        r, calls, log = self.run_(3 * 1024 * 1024, OT_UDEVD_MAX_GB="2")
        self.assertIn("restart", calls)


if __name__ == "__main__":
    unittest.main()
