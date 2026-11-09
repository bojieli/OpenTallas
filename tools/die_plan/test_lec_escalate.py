"""LEC-ESCALATE (DIE-QC-97 11-09): a final compare-point cone every normal stage left undecided is rerun once, alone,
with &cec -m -C OT_LEC_ESCALATE_C (5000000) and wall OT_LEC_ESCALATE_S (1800 s) before it is reported UNPROVEN
(QC coll_core v3: 6 undecided cones each proved EQUIVALENT that way in 240-602 s).  An escalated cone that still
hangs stays undecided (never proved); a NOT EQUIVALENT answer is a difference.  Only the final miter escalates.
    python3 -m unittest tools/die_plan/test_lec_escalate.py"""
import argparse
import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("lec", Path(__file__).with_name("lec.py"))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)


class EscalateTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)
        self.calls = []

    def _prove(self, names, hard, esc_answer="Networks are equivalent", env=None, escalate=True):
        """names: miter outputs; hard: ids that hang in every normal stage.  esc_answer: what the escalated run
        prints for a hard cone (None: it hangs too)."""
        m = lec.Aig()
        x = m.add_input("x")
        m.outs, m.onames = [x] * len(names), list(names)
        calls, tmp = self.calls, self.tmp

        def run(args, **kw):
            script = Path(args[-1]).read_text() if args[1] == "-f" else args[-1]
            if "&fraig" in script:
                (tmp / "h_swept.aig").touch()
                return SimpleNamespace(stdout=f"Undef calls {len(names)}", stderr="")
            ids = [int(i) for i in re.findall(r"&cone -O (\d+)", script)]
            big = "-C 5000000" in script or "-C 77" in script
            calls.append((ids, big, kw.get("timeout")))
            out = []
            for i in ids:
                if i in hard and (not big or esc_answer is None):
                    raise subprocess.TimeoutExpired(args, kw.get("timeout") or 0, output=None)
                out.append(esc_answer if i in hard else "Networks are equivalent")
            return SimpleNamespace(stdout="\n".join(out), stderr="")

        rec = {} if escalate else None
        e = {"OT_LEC_CONE_S": "1", **(env or {})}
        with patch.dict(os.environ, e, clear=True), patch.object(lec, "xor_sat", lambda *a: {}), \
                patch.object(lec, "abc_bin", lambda: "fake-abc"), \
                patch.object(lec, "aig_outputs", lambda p: [2] * len(names)), \
                patch.object(lec, "lit_val", lambda *a: 0), patch.object(lec.subprocess, "run", run):
            st = lec.prove(m, tmp, 100, [], tag="h", escalate=rec)
        return st, rec

    def test_undecided_cone_escalated_and_proved(self):
        st, rec = self._prove(["a", "crc", "c"], {1})
        self.assertEqual(st, {"a": "proved", "crc": "proved", "c": "proved"})
        self.assertEqual(rec["proved"], ["crc"])
        self.assertEqual(rec["conflicts"], 5000000)
        esc = [c for c in self.calls if c[1]]
        self.assertEqual(esc, [([1], True, 1800.0)])          # once, alone, with the escalation wall

    def test_escalated_cone_that_still_hangs_stays_undecided(self):
        st, rec = self._prove(["a", "crc"], {1}, esc_answer=None)
        self.assertEqual(st["crc"], "undecided")
        self.assertEqual(rec["undecided"], ["crc"])

    def test_escalation_difference_is_reported(self):
        st, rec = self._prove(["a", "crc"], {1}, esc_answer="Networks are NOT EQUIVALENT")
        self.assertEqual(st["crc"], "differs")
        self.assertEqual(rec["differs"], ["crc"])

    def test_only_the_final_miter_escalates(self):
        st, rec = self._prove(["a", "crc"], {1}, escalate=False)
        self.assertEqual(st["crc"], "undecided")
        self.assertFalse(any(c[1] for c in self.calls))

    def test_disabled_and_tunable(self):
        st, rec = self._prove(["a", "crc"], {1}, env={"OT_LEC_ESCALATE_C": "0"})
        self.assertEqual(st["crc"], "undecided")
        self.assertEqual(rec["skipped"], ["crc"])
        self.assertFalse(any(c[1] for c in self.calls))
        self.calls.clear()
        st, rec = self._prove(["a", "crc"], {1}, env={"OT_LEC_ESCALATE_C": "77", "OT_LEC_ESCALATE_S": "30"})
        self.assertEqual(st["crc"], "proved")
        self.assertEqual([c for c in self.calls if c[1]], [([1], True, 30.0)])

    def test_cap_leaves_the_rest_undecided(self):
        st, rec = self._prove(["a", "p", "q"], {1, 2}, env={"OT_LEC_ESCALATE_MAX": "1"})
        self.assertEqual((st["p"], st["q"]), ("proved", "undecided"))
        self.assertEqual((rec["tried"], rec["skipped"]), (["p"], ["q"]))

    def test_via_docker_forwards_budget(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"OT_LEC_ESCALATE_C": "9000000",
                                                                         "OT_LEC_ESCALATE_S": "3600"}, clear=True):
            args = argparse.Namespace(kit=d, out=str(Path(d) / "out"), conflicts=100, jobs=1, netlist=None,
                                      reuse=False, gold_frontend=None, hints=None, port_map=None)
            with patch.object(lec.subprocess, "run") as run:
                run.return_value.returncode = 0
                self.assertEqual(lec.via_docker(args, "pinned-image", 16), 0)
            cmd = run.call_args.args[0]
            self.assertIn("OT_LEC_ESCALATE_C=9000000", cmd)
            self.assertIn("OT_LEC_ESCALATE_S=3600", cmd)


if __name__ == "__main__":
    unittest.main()
