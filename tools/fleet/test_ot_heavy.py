"""ot-heavy (fleet rule 2026-10-10): a capped command is killed at its MemoryMax; big slots are exclusive."""
import os
import pathlib
import subprocess
import tempfile
import sys
import time
import unittest

T = str(pathlib.Path(__file__).with_name("ot-heavy"))
# LOADCAP_1101: these tests are about memory; the host load cap is tested in test_ot_heavy_crit.py
# LOADGATE_1110: the gate reads the REAL host load1 (1.25 x nproc), so on a busy host these timing tests would be held; off here, tested in test_ot_heavy_crit.py
ENV = dict(os.environ, LOAD_CAP_FACTOR="0", LOAD_GATE_FACTOR="0")


class OtHeavy(unittest.TestCase):
    def test_cap_kills_the_command_not_the_host(self):
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "x=bytearray(2*1024**3); print('leak')"],
                           capture_output=True, text=True, env=ENV)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("leak", r.stdout)
        r = subprocess.run([T, "--mem", "1", "--", "python3", "-c", "print('ok')"], capture_output=True, text=True, env=ENV)
        self.assertEqual(r.stdout.strip(), "ok")

    def test_usage(self):
        self.assertEqual(subprocess.run([T, "--", "true"], capture_output=True, env=ENV).returncode, 2)

    def test_no_fixed_slots(self):
        # Exercise the shipped Bash admission/lock/launch path, replacing only
        # external host interfaces in a temporary copy. Real fleet contention
        # and a nine-second wall clock are not a concurrency specification.
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            tools, state = root / "bin", root / "state"
            tools.mkdir(); state.mkdir()
            conf = root / "ot-heavy.conf"
            conf.write_text("LOAD_CAP_FACTOR=0\nLOAD_GATE_FACTOR=0\nLOAD_FRESH_S=0\nOT_HEAVY_SHORT_POOL=0\nTHREAD_CAP_FACTOR=0\n")

            def executable(name, body):
                target = tools / name
                target.write_text(body); target.chmod(0o755)
                return str(target)

            reconcile = executable("reconcile", "#!/bin/sh\ncase \"$1\" in --is-plan|--is-die) exit 1;; --gate) echo 'OK 1 fixture | measured memory available';; esac\n")
            protect = executable("protect", "#!/bin/sh\nexit 1\n")
            exit_wrapper = executable("exit-wrapper", "#!/bin/sh\nshift\nexec \"$@\"\n")
            executable("sudo", "#!/bin/sh\nexit 0\n")
            executable("nproc", "#!/bin/sh\necho 1\n")
            executable("systemd-run", "#!" + sys.executable + "\nimport os,sys\na=sys.argv[sys.argv.index('--')+1:]\nos.execvp(a[0],a)\n")
            script = pathlib.Path(T).read_text()
            for old, replacement in [
                    ("D=/var/tmp/ot-heavy", "D=" + str(state)),
                    ("/etc/ot-heavy.conf", str(conf)),
                    ("/usr/local/bin/ot-heavy-reconcile", reconcile),
                    ("/usr/local/bin/ot-protect-die", protect),
                    ("/usr/local/lib/ot-heavy/ot-heavy-exit", exit_wrapper)]:
                script = script.replace(old, replacement)
            wrapper = root / "ot-heavy"
            wrapper.write_text(script); wrapper.chmod(0o755)
            env = dict(ENV, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                       OT_HEAVY_CONF=str(conf), OT_HEAVY_THREADS="1")
            env.pop("OT_HEAVY_PRIO", None); env.pop("OT_HEAVY_DIRECT", None)
            release = root / "release"
            payload = ("from pathlib import Path;import sys,time;"
                       "Path(sys.argv[1]).write_text('started');"
                       "p=Path(sys.argv[2]);\nwhile not p.exists():time.sleep(.01)\n")
            markers = [root / ("started-" + str(i)) for i in range(3)]
            ps = [subprocess.Popen([str(wrapper), "--mem", "1", "--", sys.executable,
                                    "-c", payload, str(marker), str(release)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env) for marker in markers]
            all_started = False
            try:
                deadline = time.monotonic() + 10  # bounded tiny fixture, never a fleet-job deadline
                while time.monotonic() < deadline:
                    if all(marker.exists() for marker in markers):
                        all_started = True; break
                    if any(p.poll() is not None for p in ps):
                        break
                    time.sleep(.01)
                # No payload is released until all three are simultaneously in
                # the running section. A fixed one/two-slot policy fails here.
                release.write_text("release all")
                outputs = [p.communicate(timeout=5) for p in ps]
                self.assertTrue(all_started, outputs)
                self.assertEqual([p.returncode for p in ps], [0, 0, 0], outputs)
                self.assertFalse(any("slots busy" in err or "thread cap:" in err for _, err in outputs))
            finally:
                release.touch()
                for process in ps:
                    if process.poll() is None:
                        process.terminate(); process.wait(timeout=5)

if __name__ == "__main__":
    unittest.main()
