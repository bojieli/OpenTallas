"""ot-run-sealed HUB-FETCH (KW-FIX-44 11-10): the hub runs host commands itself (it cannot ssh to its own name) and a fetch host that already holds a copy
of K returns the job into a private stage dir, so that copy is never overwritten or removed by the copy-back."""
import importlib.machinery
import importlib.util
import unittest
from unittest.mock import patch
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


    def test_roamed_place_returns_actual_checkpoint_not_staged_copy(self):
        cb = {"from": "epyc8", "to": "epyc9", "path": K, "stage": "/srv/return/q_x"}
        out = ["ot-run-sealed: SEALED on epyc8: " + K + "\n",
               "ot-run: RAN on intel1 (unit oth-ubuntu-3799539-1794865488): exit 0\n"]
        with patch.object(self.m, "copy_back", return_value=0) as cp:
            self.assertEqual(self.m.return_copy(cb, out), (0, "intel1"))
        cp.assert_called_once_with("intel1", "epyc9", K, "/srv/return/q_x")

    def test_no_terminal_receipt_never_copies_stale_staged_checkpoint(self):
        cb = {"from": "epyc8", "to": "epyc9", "path": K}
        for out in ([], ["ot-run: NOT RUN: no host qualifies\n"],
                    ["ot-run: -> intel1\n"], ["ot-run: RAN on intel1 invalid\n"]):
            with self.subTest(out=out), patch.object(self.m, "copy_back") as cp:
                self.assertEqual(self.m.return_copy(cb, out), (97, None))
                cp.assert_not_called()

    def test_final_receipt_preserves_partial_failure_return_and_hub_alias(self):
        cb = {"from": "epyc8", "to": "epyc9", "path": K}
        out = ["ot-run: RAN on epyc7 (unit earlier): exit 75\n",
               "ot-run: RAN on localhost (unit final): exit 1\n"]
        with patch.object(self.m, "copy_back", return_value=23) as cp:
            self.assertEqual(self.m.return_copy(cb, out), (23, "localhost"))
        cp.assert_called_once_with("localhost", "epyc9", K, None)


if __name__ == "__main__":
    unittest.main()


def test_job_root_sh_prefers_the_root_with_more_usable_space_and_counts_the_root_fs_floor():
    import importlib.machinery, importlib.util, os
    ld = importlib.machinery.SourceFileLoader("sl_jr", os.path.join(os.path.dirname(__file__), "ot-run-sealed"))
    sp = importlib.util.spec_from_loader("sl_jr", ld); m = importlib.util.module_from_spec(sp); ld.exec_module(m)
    assert "ROOT_FLOOR_GB" in dir(m) and m.ROOT_FLOOR_GB == 150
    assert "-gt $((bf+20))" in m.JOB_ROOT_SH and "f-150" in m.JOB_ROOT_SH      # scratch3 only when 20 GB larger, root fs minus its floor
    assert "&& continue; " not in m.JOB_ROOT_SH.replace("|| continue", "")      # the old 'skip a root-fs scratch3' rule is gone
