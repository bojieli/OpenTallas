"""SOFTPIN_1114 (ADMIT-TUNE-1): a single-host --job pin is soft only when every spec input names a fetch host."""
import importlib.machinery
import importlib.util
import json
import pathlib
import tempfile
import unittest

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_softpin", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_softpin", loader))
loader.exec_module(M)
JOBS = "/srv/opentallas-scratch2/claude/ot-jobs"


def spec(inputs):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"inputs": inputs}, f)
    f.close()
    return f.name


class SoftPin(unittest.TestCase):
    def test_all_inputs_with_a_fetch_host_may_move(self):
        self.assertTrue(M.soft_pin_ok(spec([{"path": "/a/run_kit.sh", "host": "epyc9"}]), JOBS))

    def test_a_path_only_input_is_soft_pinned_and_input_hold_keeps_it_on_holders(self):
        # SOFTPIN-PATHONLY-1119: the INPUT HOLD step narrows the alternatives to hosts that hold every path-only input
        self.assertTrue(M.soft_pin_ok(spec([{"path": "/a/run_kit.sh"}]), JOBS))
        self.assertTrue(M.soft_pin_ok(spec([{"path": "/a", "host": "hub"}, {"path": "/b"}]), JOBS))
        self.assertFalse(M.soft_pin_ok(spec([{"at": "/x"}]), JOBS))

    def test_kit_local_dir_or_unreadable_spec_stays_hard_pinned(self):
        self.assertFalse(M.soft_pin_ok(spec([{"path": "/a", "host": "hub"}]), "/srv/opentallas-scratch2/claude/lane/kit"))
        self.assertFalse(M.soft_pin_ok("/nonexistent.json", JOBS))
        self.assertFalse(M.soft_pin_ok(spec([]), JOBS))


class InputHold(unittest.TestCase):
    def test_spec_local_inputs_are_the_path_only_ones(self):
        self.assertEqual(M.spec_local_inputs(spec([{"path": "/a"}, {"path": "/b", "host": "hub"}])), ["/a"])
        self.assertEqual(M.spec_local_inputs("/nonexistent.json"), [])

    def test_holders_keep_only_hosts_with_every_path(self):
        have = {"epyc9": True, "epyc2": False, "intel1": True}
        self.assertEqual(M.holders_of(["epyc2", "epyc9", "intel1"], ["/a"], probe_fn=lambda h, p: have[h]), ["epyc9", "intel1"])
        self.assertEqual(M.holders_of(["epyc2"], ["/a"], probe_fn=lambda h, p: have[h]), [])


if __name__ == "__main__":
    unittest.main()
