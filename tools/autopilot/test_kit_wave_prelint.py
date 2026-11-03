#!/usr/bin/env python3
"""KW-FIX-4 11-03 (OWNER gen-time lint, ADVISORY per OWNER 07:0x): plan-static + same-block verdict checks report a
type as a LINT-ADVISORY row (stage prelint); they never block a launch except a missing planned core view: cells > 150k, memory over SYNTH_MEMORY_MAX_BITS not a macro,
planned core without a signed view, leaked strap ports."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def probe(plan, **kw):
    with tempfile.TemporaryDirectory() as d:
        pp = Path(d) / "plan.json"
        pp.write_text(json.dumps(plan))
        out = subprocess.run([sys.executable, "-c", KW.PROBE_PLAN, json.dumps(dict(plan=str(pp), **kw))],
                             capture_output=True, text=True, cwd=d)
        return json.loads(out.stdout.split("AP_JSON ", 1)[1])


PLAN = {"partition_types": {
    "big": {"cells": 160000, "contents": [{"inst": "u", "module": "m"}]},
    "sum": {"contents": [{"inst": "a", "module": "a", "cells": 100000}, {"inst": "b", "module": "b", "cells": 60000}]},
    "cored": {"cells": 900000, "hard_cores": [{"inst": "c", "module": "c", "lef": "c.lef", "lib": "c.lib"}]},
    "small": {"cells": 149000},
    "leak": {"buses": [{"name": "strap_id", "dir": "in", "width": 4}, {"name": "d_i", "dir": "in", "width": 8}]},
    "ok_strap": {"buses": [{"name": "strap_id", "dir": "in", "width": 4}], "id_straps": [{"name": "strap_id", "width": 4}]},
    "dup": {"id_straps": [{"name": "strap_a", "width": 1}, {"name": "strap_a", "width": 1}]},
    "pv": {"hard_cores": [{"inst": "p0", "module": "kv3_pv_pair"}]}}}


class Probe(unittest.TestCase):
    def test_plan_static_lint(self):
        res = probe(PLAN)
        lint = res["lint"]
        self.assertEqual(sorted(lint), ["big", "dup", "leak", "sum"])
        self.assertTrue(lint["big"][0].startswith("cells: est 160000"))
        self.assertTrue(lint["sum"][0].startswith("cells: est 160000"))     # sum of contents[].cells
        self.assertIn("strap_id", lint["leak"][0])
        self.assertIn("duplicate", lint["dup"][0])
        self.assertEqual(res["probe_v"], KW.PROBE_V)
        self.assertNotIn("big", probe(PLAN, cells_max=200000)["lint"])     # die override of the cell limit

    def test_entry_block_and_opt_out(self):
        res = probe(PLAN)
        d = {"event": "e", "_plan_flags": res["flags"], "_plan_deps": res["deps"], "_plan_lint": res["lint"]}
        names = {t: f"b_{t}" for t in PLAN["partition_types"]}
        d["_lint"] = KW.prelint(d, "die", names, {"items": {}})
        # OWNER 07:0x advisory: lint hits never block; only a missing planned core view does (WAIT-DEP)
        self.assertIsNone(KW.plan_entry_block(d, "big"))
        self.assertIsNone(KW.plan_entry_block(d, "leak"))
        self.assertIn("big", d["_lint"])
        self.assertTrue(KW.plan_entry_block(dict(d, prelint_block=True), "big").startswith("LINT cells"))
        self.assertTrue(KW.plan_entry_block(dict(d, prelint_block=True), "leak").startswith("LINT strap"))
        self.assertIsNone(KW.plan_entry_block(d, "small"))
        self.assertIsNone(KW.plan_entry_block(d, "cored"))
        self.assertIsNone(KW.plan_entry_block(d, "ok_strap"))
        # planned core: keeps its WAIT-DEP launch hold, and also shows as a LINT 'view' row
        self.assertTrue(KW.plan_entry_block(d, "pv").startswith("WAIT-DEP"))
        self.assertTrue(d["_lint"]["pv"][0].startswith("view: planned hard core"))
        self.assertIsNone(KW.plan_entry_block(dict(d, prelint=False, prelint_block=True), "big"))


class History(unittest.TestCase):
    def setUp(self):
        self.d = {"event": "e", "retry": ["svc@2"]}
        self.names = {"svc": "blk1", "other": "blk9"}
        key = KW.item_key("s81", "e", "svc", "blk1")
        self.st = {"items": {key: {"die": "s81", "item": "svc", "attempt": 2, "status": "FAIL", "class": "FLOW",
                                   "reason": "kit recipe at gen: memory bits over SYNTH_MEMORY_MAX_BITS (GEN_LINT)"}}}

    def test_memory_verdict_same_block_is_lint(self):
        lint = KW.prelint(self.d, "s81", self.names, self.st)
        self.assertEqual(list(lint), ["svc"])
        self.assertTrue(lint["svc"][0].startswith("memory:"))
        self.d["_lint"] = lint
        self.assertIsNone(KW.plan_entry_block(self.d, "svc"))                      # advisory
        self.assertTrue(KW.plan_entry_block(dict(self.d, prelint_block=True), "svc").startswith("LINT memory"))

    def test_named_fix_or_new_block_clears(self):
        self.assertEqual(KW.prelint(dict(self.d, retry_fix={"svc@2": "abc123 memory macros"}), "s81", self.names,
                                    self.st), {})
        self.assertEqual(KW.prelint(self.d, "s81", {"svc": "blk2"}, self.st), {})

    def test_stages_rows(self):
        cfg = {"dies": {"s81": dict(self.d, plan="/p/plan.json", _plan_sha="f" * 64, _lint_blocks=self.names)}}
        KW.record_lint(self.st, cfg, "s81", KW.prelint(self.d, "s81", self.names, self.st))
        with tempfile.TemporaryDirectory() as ap:
            KW.write_stages(self.st, ap, cfg)
            rows = [r.split("\t") for r in (Path(ap) / KW.STAGES_FILE).read_text().splitlines()]
        col = {c: i for i, c in enumerate(rows[0])}
        lint = [r for r in rows[1:] if r[col["status"]] == "LINT-ADVISORY"]
        self.assertEqual(len(lint), 1)
        r = lint[0]
        self.assertEqual((r[col["item"]], r[col["stage"]], r[col["class"]], r[col["block_sha"]]),
                         ("svc", "prelint", "LINT", "blk1"))
        KW.record_lint(self.st, cfg, "s81", {})          # a clean verdict next tick drops the die's LINT rows
        self.assertEqual(self.st["lint"], {})


if __name__ == "__main__":
    unittest.main()
