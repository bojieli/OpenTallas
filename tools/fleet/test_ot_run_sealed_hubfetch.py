"""ot-run-sealed HUB-FETCH (KW-FIX-44 11-10): the hub runs host commands itself (it cannot ssh to its own name) and a fetch host that already holds a copy
of K returns the job into a private stage dir, so that copy is never overwritten or removed by the copy-back."""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_sealed_hf", str(HERE / "ot-run-sealed"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


K = "/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/hbm/kit-wave/hbm/d44v/items/q_x/attempt_1/gen/q_x"


class HubFetch(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_hub_commands_run_locally(self):
        for h in ("intel2", "localhost"):
            self.assertEqual(self.m.on(h, "echo hi"), ["bash", "-c", "echo hi"])

    def test_other_hosts_go_through_ssh(self):
        a = self.m.on("epyc7", "echo hi")
        self.assertEqual(a[0], "ssh")
        self.assertIn("-n", a)
        self.assertEqual(a[-2:], ["epyc7", "echo hi"])
        b = self.m.on("epyc7", "tar -xf -", n=False, timeout_flag=False)
        self.assertNotIn("-n", b)
        self.assertNotIn("ConnectTimeout=20", b)

    def test_otrun_host_names(self):
        self.assertEqual(self.m.otrun_host("intel2"), "localhost")
        self.assertEqual(self.m.otrun_host("epyc8"), "epyc8")

    def test_stage_return_sets_a_private_return_dir(self):
        spec = {"copy_back": {}}
        self.m.STAGE[:] = [None]
        self.m.stage_return(spec, "/srv/opentallas-scratch2/claude/ot-jobs", K)
        st = spec["copy_back"]["stage"]
        self.assertTrue(st.startswith("/srv/opentallas-scratch2/claude/ot-jobs/.return/"))
        self.assertEqual(st.rsplit("/", 1)[1], "q_x")
        self.assertEqual(spec["return"]["to"], st)
        self.assertEqual(self.m.STAGE, [])            # one-shot

    def test_stage_return_without_k_present_changes_nothing(self):
        spec = {"copy_back": {}}
        self.m.STAGE[:] = []
        self.m.stage_return(spec, "/srv/x", K)
        self.assertEqual(spec, {"copy_back": {}})

    def test_copy_back_refuses_a_stage_with_a_foreign_basename(self):
        self.assertEqual(self.m.copy_back("epyc7", "intel2", K, stage="/srv/opentallas-scratch2/claude/ot-jobs/.return/1-2/other"), 99)


if __name__ == "__main__":
    unittest.main()
