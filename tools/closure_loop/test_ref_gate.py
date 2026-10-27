"""REF-TILE GATE submit hook (ref-flow-1011, 2026-10-11): ref_tile jobs REFUSE on a gate FAIL (default mode refuse),
other jobs only WARN (default other=warn); STATE/ref_gate.json switches modes; spec "ref_gate": false opts out."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl

sys.path.insert(0, str(Path(cl.__file__).resolve().parent.parent / "ref_tile"))
import pre_route_gate  # noqa: E402


def job(ref=True, **kw):
    s = {"name": "p", "block": "b", "source": {"commit": "c"}, **kw}
    if ref:
        s["ref_tile"] = True
    return {"name": "p", "status": "QUEUED", "events": [], "spec": s}


class RefGateHook(unittest.TestCase):
    def run_hook(self, state, res, j):
        with tempfile.TemporaryDirectory() as t:
            for f, v in state.items():
                (Path(t) / f).write_text(json.dumps(v))
            with patch.object(cl, "STATE", Path(t)), patch.object(cl, "ledger"), patch.object(cl, "log"), \
                    patch.object(pre_route_gate, "submit_check", return_value=res) as h:
                cl.ref_gate_at_submit(j)
            return j, h

    def test_ref_tile_refuse_default(self):
        j, _ = self.run_hook({}, {"verdict": "REFUSE", "message": "pins: x"}, job())
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("REF_GATE", j["reason"])

    def test_other_jobs_warn_default(self):
        j, _ = self.run_hook({}, {"verdict": "REFUSE", "message": "sources: y"}, job(ref=False))
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["submit_checks"]["ref_gate"]["verdict"], "WARN")

    def test_modes_and_opt_out(self):
        j, h = self.run_hook({"ref_gate.json": {"mode": "off"}}, {"verdict": "REFUSE", "message": "z"}, job())
        self.assertEqual(j["status"], "QUEUED")
        h.assert_not_called()
        j, h = self.run_hook({}, {"verdict": "REFUSE", "message": "z"}, job(ref_gate=False))
        h.assert_not_called()
        j, _ = self.run_hook({"ref_gate.json": {"other": "refuse"}}, {"verdict": "REFUSE", "message": "z"}, job(ref=False))
        self.assertEqual(j["status"], "REFUSED")

    def test_gate_error_never_blocks(self):
        j, _ = self.run_hook({}, {"verdict": "SKIP", "message": "gate error"}, job())
        self.assertEqual(j["status"], "QUEUED")


class RefGateReal(unittest.TestCase):
    def test_source_sync_detects_unsynced_hook(self):
        spec = {"source": {"commit": "HEAD", "paths": ["tools"]},
                "stages": {"route": {"cmd": "bash tools/ref_tile/ref_route.sh x/kit.env L R"}}}
        g = pre_route_gate.Gate()
        old = pre_route_gate.ROOT
        try:
            pre_route_gate.ROOT = Path(cl.__file__).resolve().parents[2]
            r = pre_route_gate.check_sources(g, spec, ("physical/qwen_die_masters/pre_cts_skew.tcl",), None)
        finally:
            pre_route_gate.ROOT = old
        self.assertIn("physical/qwen_die_masters/pre_cts_skew.tcl", r["outside"])
        self.assertEqual(g.verdict, "FAIL")


if __name__ == "__main__":
    unittest.main()
