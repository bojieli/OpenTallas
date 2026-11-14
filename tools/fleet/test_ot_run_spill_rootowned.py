"""ROOTOWNED_1114: the spill extraction replaces files a docker job left root-owned (VARIANTS-1 'Cannot open: File exists / Permission denied')."""
import importlib.machinery, importlib.util, os, pathlib, shutil, subprocess, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_rootowned", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_rootowned", loader))
loader.exec_module(M)
SUDO = subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0 and shutil.which("zstd")


@unittest.skipUnless(SUDO, "needs passwordless sudo and zstd")
class RootOwned(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(dir="/tmp", prefix="otspill-")
        self.addCleanup(lambda: subprocess.run(["sudo", "-n", "rm", "-rf", self.base]))
        self.lane = os.path.join(self.base, "lane")
        os.makedirs(self.lane + "/run/logs")
        subprocess.run(["sudo", "-n", "bash", "-c", f"echo OLD > {self.lane}/run/logs/5_1_grt.log; chown -R root:root {self.lane}/run; touch -d '2020-01-01' {self.lane}/run/logs/5_1_grt.log"], check=True)
        self.src = os.path.join(self.base, "src")                       # the sender's tree: same relative path, newer content
        os.makedirs(self.src + "/run/logs")
        open(self.src + "/run/logs/5_1_grt.log", "w").write("NEW\n")

    def extract(self, env=None):
        rel = os.path.relpath(self.src, "/")
        mk = f"cd / && tar -C / --transform='s|{rel}|{os.path.relpath(self.lane, '/')}|' -cf - {rel}/run | zstd -q -1"
        cmd = f"{mk} | " + M.tar_x([self.lane])
        e = {k: v for k, v in os.environ.items() if k != "OT_SPILL_NO_SUDO"}      # conftest sets it for the fake-tar spill tests
        e.update(env or {})
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, env=e)

    def test_root_owned_file_is_replaced(self):
        r = self.extract()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(open(self.lane + "/run/logs/5_1_grt.log").read(), "NEW\n")

    def test_without_sudo_the_old_failure_reproduces(self):
        r = self.extract({"OT_SPILL_NO_SUDO": "1"})
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stderr, "Cannot open|Permission denied|File exists")


if __name__ == "__main__":
    unittest.main()
