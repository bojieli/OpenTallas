"""Native ABC tests of enabled unreset load/hold fill; every compare stays present."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("lec_enabled_fill", Path(__file__).parents[1] / "tools/die_plan/lec.py")
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


def capsule(gate_value=0, async_mask=False):
    # Exact HHP shape: enabled word -> beat -> record -> enabled retained.
    # Three real resettable control FFs provide issue / capture-slot / capture-v.
    inputs = {i: [(n, 0)] for i, n in enumerate(["rst_n", "issue_in", "cs_in", "cv_in"])}
    controls = ["issue", "cs", "cv"] + (["rs"] if async_mask else [])

    def side(gold):
        names = controls + (["word", "beat", "record", "retained"] if gold else []) + ["lec_po_y"]
        q = {n: 2 * (4 + i + 1) for i, n in enumerate(names)}
        aa = []

        def AND(a, b):
            aa.extend((a, b))
            return 2 * (4 + len(names) + len(aa) // 2)

        def mux(s, a, b):
            return AND(AND(s, a) ^ 1, AND(s ^ 1, b) ^ 1) ^ 1

        dd = [AND(q["rs"] if async_mask else 2, 4), AND(2, 6), AND(2, 8)]
        if async_mask:
            dd += [2]
        if gold:
            issue = AND(q["issue"], q["rs"]) if async_mask else q["issue"]
            capture = AND(q["cs"], q["cv"])
            if async_mask:
                capture = AND(capture, 2)
            dd += [AND(issue ^ 1, q["word"]), q["word"], q["beat"],
                   mux(capture, q["record"], q["retained"]), q["retained"]]
        else:
            dd += [gate_value]
        aig = dict(I=4, L=len(names), O=1, A=len(aa) // 2, latches=dd,
                   outputs=[q["lec_po_y"]], ands=aa)
        amap = {"input": inputs, "output": {}, "latch": {i: [(n + ".lecq", 0)] for i, n in enumerate(names)}}
        return aig, amap

    g, gm = side(True)
    t, tm = side(False)
    L = E.Lec(g, gm, t, tm)
    L.kit_reset_ports = ["rst_n"]
    return L


def proposals(wrong_data=False, wrong_enable=False, masks=False, wrong_mask=False):
    c = int(wrong_data)
    issue = [["ff:issue", 1]] + ([["ff:rs", 1]] if masks else [])
    capture = [["ff:cs", 1], ["ff:cv", int(not wrong_enable)]] + ([["pi:rst_n[0]", int(not wrong_mask)]] if masks else [])
    return [["gold", "ff:word", ["fill", c, None, [issue]]],
            ["gold", "ff:beat", ["fill", c, "ff:word"]],
            ["gold", "ff:record", ["fill", c, "ff:beat"]],
            ["gold", "ff:retained", ["fill", c, "ff:record", [capture]]]]


class EnabledFill(unittest.TestCase):
    def test_capability_advertises_explicit_opt_in(self):
        self.assertEqual(E.main(["--require-options", "OT_LEC_ENABLE_FILL_GUARD"]), 0)

    def run_native(self, *, enabled=True, wrong_data=False, wrong_enable=False, gate_value=0,
                   async_mask=False, guard_masks=False, wrong_mask=False):
        with patch.dict(os.environ, {"OT_LEC_ENABLE_FILL_GUARD": "1" if enabled else "0"}):
            L = capsule(gate_value, async_mask)
            compares = set(L.gc) & set(L.tc)
            self.assertEqual(compares, {"ff:issue", "ff:cs", "ff:cv", "po:y"} | ({"ff:rs"} if async_mask else set()))
            with tempfile.TemporaryDirectory() as d:
                log = []
                receipt = E.apply_hints(L, proposals(wrong_data, wrong_enable, guard_masks, wrong_mask), Path(d), 1000, log)
                m, _ = L.build(with_compare=True, with_hyp=True)
                status = E.prove(m, Path(d), 1000, log, tag="all_compares")
                self.assertTrue(compares <= set(status), "an original compare disappeared")
                return status, receipt, L

    def test_exact_enabled_load_hold_and_two_pipeline_stages(self):
        status, receipt, _ = self.run_native()
        self.assertTrue(all(s == "proved" for s in status.values()), status)
        self.assertEqual(len(receipt["fill"]), 4)
        enabled = [f for f in receipt["fill"] if "enable_guard" in f]
        self.assertEqual({f["register"] for f in enabled}, {"ff:word", "ff:retained"})

    def test_feature_is_default_off(self):
        status, receipt, _ = self.run_native(enabled=False)
        self.assertEqual(status["po:y"], "differs")
        self.assertEqual(len(receipt["skipped"]), 2)

    def test_wrong_data_relation_is_rejected(self):
        status, receipt, _ = self.run_native(wrong_data=True)
        self.assertEqual(status["po:y"], "differs")
        self.assertEqual(receipt["fill"], [])

    def test_wrong_capture_enable_is_rejected(self):
        status, receipt, _ = self.run_native(wrong_enable=True)
        self.assertEqual(status["po:y"], "differs")
        self.assertNotIn("ff:retained", {f["register"] for f in receipt["fill"]})

    def test_known_data_observation_is_never_masked(self):
        status, receipt, _ = self.run_native(gate_value=1)
        self.assertEqual(len(receipt["fill"]), 4)
        self.assertEqual(status["po:y"], "differs")
        self.assertTrue(all(s == "proved" for n, s in status.items() if n.startswith("hyp:")))

    def test_async_masked_source_requires_its_actual_public_enable(self):
        status, _, _ = self.run_native(async_mask=True)
        self.assertEqual(status["po:y"], "differs")

    def test_exact_async_masked_source_with_reset_port_atom(self):
        status, receipt, _ = self.run_native(async_mask=True, guard_masks=True)
        self.assertTrue(all(s == "proved" for s in status.values()), status)
        self.assertEqual(len(receipt["fill"]), 4)

    def test_wrong_reset_port_guard_is_rejected(self):
        status, receipt, _ = self.run_native(async_mask=True, guard_masks=True, wrong_mask=True)
        self.assertEqual(status["po:y"], "differs")
        self.assertNotIn("ff:retained", {f["register"] for f in receipt["fill"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
