"""FP-LINT 2026-10-08: floorplan margin lint (tools/fp_margin_lint.py) and its closure-loop wiring."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402
import fp_margin_lint as F  # noqa: E402

LAYERS = [{"name": f"M{i}", "level": i, "dir": "VERTICAL" if i % 2 else "HORIZONTAL",
           "pitch": {1: .036, 2: .036, 3: .036, 4: .048, 5: .048, 6: .064, 7: .064}[i],
           "width": {1: .018, 2: .018, 3: .018, 4: .024, 5: .024, 6: .032, 7: .032}[i]} for i in range(1, 8)]


def dump(**kw):
    d = {"dbu": 1000, "die": [0, 0, 200, 200], "core": [0, 0, 200, 200], "layers": LAYERS,
         "masters": {"DFFHQNx1_ASAP7_75t_R": {"n": 1000, "w": 1.08, "h": 0.27, "type": "CORE", "block": False, "top_layer": 0},
                     "BUFx2_ASAP7_75t_R": {"n": 100, "w": 0.27, "h": 0.27, "type": "CORE", "block": False, "top_layer": 0}},
         "macros": [], "bterms": [], "pdn_edge": [], "blockages": [], "rows": []}
    d.update(kw)
    return d


def m4_pin(name, y, x0=0.0):
    return [name, name, "SIGNAL", "INPUT", [["M4", [x0, y - 0.012, x0 + 0.192, y + 0.012]]]]


class Lint(unittest.TestCase):
    def checks(self, d, **th):
        return {f["check"] for f in F.lint(d, th)["fails"]}

    def test_clean_passes(self):
        self.assertEqual(F.lint(dump())["verdict"], "PASS")

    def test_util(self):
        d = dump()
        d["masters"]["DFFHQNx1_ASAP7_75t_R"]["n"] = 90000      # 26.2k um2 of 40k = 65.6%
        self.assertIn("util", self.checks(d))
        d["masters"]["DFFHQNx1_ASAP7_75t_R"]["n"] = 78000      # 57% + 1 BUFx2/flop -> 70% with the hold allowance
        self.assertIn("util", self.checks(d))
        d["masters"]["DFFHQNx1_ASAP7_75t_R"]["n"] = 60000      # 44% / 52%
        self.assertNotIn("util", self.checks(d))

    def test_pin_density(self):
        dense = [m4_pin(f"a{i}", 10 + i * 0.048) for i in range(3000)]       # 20.8 b/um over 144 um (vm8 seam)
        self.assertIn("pin_density", self.checks(dump(bterms=dense)))
        half = [m4_pin(f"a{i}", 10 + i * 0.096) for i in range(1800)]        # 10.4 b/um (hfd_svc, closed)
        self.assertNotIn("pin_density", self.checks(dump(bterms=half)))
        short = [m4_pin(f"a{i}", 10 + i * 0.048) for i in range(560)]        # full column, 27 um (s81 hend hx)
        self.assertNotIn("pin_density", self.checks(dump(bterms=short)))

    def test_pin_width(self):
        ck = ["ck", "ck", "SIGNAL", "INPUT", [["M7", [99.6, 199.7, 99.664, 200.0]]]]    # 0.064 on M7 (vm8)
        self.assertIn("pin_width", self.checks(dump(bterms=[ck])))
        ok = ["ck", "ck", "SIGNAL", "INPUT", [["M7", [99.6, 199.7, 99.632, 200.0]]]]
        self.assertNotIn("pin_width", self.checks(dump(bterms=[ok])))

    def test_pin_pdn_full_column(self):
        strap = [["wire", "M5", "", [0.24, 0.5, 0.36, 199.5]]]                 # pdn_view M5 offset 0.300 (hx_E)
        full = [m4_pin(f"i{i}", 20 + i * 0.048) for i in range(400)]
        self.assertIn("pin_pdn", self.checks(dump(bterms=full, pdn_edge=strap)))
        half = [m4_pin(f"i{i}", 20 + i * 0.096) for i in range(400)]
        r = F.lint(dump(bterms=half, pdn_edge=strap))
        self.assertNotIn("pin_pdn", {f["check"] for f in r["fails"]})
        self.assertIn("pin_pdn", {w["check"] for w in r["warns"]})
        moved = [["wire", "M5", "", [2.64, 0.5, 2.76, 199.5]]]                  # m5w offset 2.700
        self.assertNotIn("pin_pdn", self.checks(dump(bterms=full, pdn_edge=moved)))

    def test_sliver_and_blockage(self):
        macros = [{"name": "a", "master": "B", "bbox": [20, 20, 120, 60], "status": "FIRM", "halo": None, "pins": []},
                  {"name": "b", "master": "B", "bbox": [20, 63, 120, 100], "status": "FIRM", "halo": None, "pins": []}]
        rows = [[0, 60 + k * 0.27, 200, 60.27 + k * 0.27] for k in range(11)]
        masters = dict(dump()["masters"], B={"n": 2, "w": 100, "h": 40, "type": "BLOCK", "block": True, "top_layer": 4})
        self.assertIn("sliver", self.checks(dump(macros=macros, rows=rows, masters=masters)))
        blk = [{"bbox": [20, 60, 120, 63], "soft": False, "max_density": 0}]
        self.assertNotIn("sliver", self.checks(dump(macros=macros, rows=rows, masters=masters, blockages=blk)))

    def test_bank_distance_and_macro_edge(self):
        masters = dict(dump()["masters"], B={"n": 1, "w": 20, "h": 20, "type": "BLOCK", "block": True, "top_layer": 4})
        pins = [m4_pin(f"k{i}", 10 + i) for i in range(20)]
        bank = {"name": "bank", "master": "B", "bbox": [150, 150, 170, 170], "status": "FIRM", "halo": None,
                "pins": [[f"k{i}", 150, 160, "INPUT", None] for i in range(20)]}
        self.assertIn("bank_distance", self.checks(dump(bterms=pins, macros=[bank], masters=masters)))
        near = dict(bank, bbox=[2, 5, 22, 35], pins=[[f"k{i}", 2, 10 + i, "INPUT", None] for i in range(20)])
        self.assertNotIn("bank_distance", self.checks(dump(bterms=pins, macros=[near], masters=masters)))
        wall = {"name": "sram", "master": "B", "bbox": [3, 0, 23, 60], "status": "FIRM", "halo": None, "pins": []}
        self.assertIn("macro_edge", self.checks(dump(bterms=[m4_pin(f"p{i}", 5 + i) for i in range(40)],
                                                     macros=[wall], masters=masters)))

    def test_channel(self):
        masters = dict(dump()["masters"], B={"n": 2, "w": 90, "h": 200, "type": "BLOCK", "block": True, "top_layer": 7})
        a = {"name": "a", "master": "B", "bbox": [0, 0, 90, 200], "status": "FIRM", "halo": None,
             "pins": [[f"n{i}", 89, 100, "OUTPUT", None] for i in range(5000)]}
        b = dict(a, name="b", bbox=[110, 0, 200, 200], pins=[[f"n{i}", 111, 100, "INPUT", None] for i in range(5000)])
        # a vertical cut through the 20 um channel: 5,000 nets vs 200 um of free M4/M6 length (4.2k + 3.1k) x 0.5 = 3.6k
        # tracks -- no: the cut runs through the channel (x=100), all 200 um free: capacity 3.6k < 5k
        self.assertIn("channel", self.checks(dump(macros=[a, b], masters=masters)))
        b2 = dict(b, pins=[[f"n{i}", 111, 100, "INPUT", None] for i in range(1000)])
        self.assertNotIn("channel", self.checks(dump(macros=[a, b2], masters=masters)))

    def test_relay_lint(self):
        bad = F.relay_lint({"ok": [(0, 0), (400, 0), (800, 0)], "far": [(0, 0), (500, 0), (300, 0), (900, 0)],
                            "back": [(12844, 5385), (12621, 4832), (13300, 5385)]})
        kinds = {(b["chain"], b["kind"]) for b in bad}
        self.assertNotIn("ok", {c for c, _ in kinds})
        self.assertIn(("far", "reach"), kinds)
        self.assertIn(("back", "far_side"), kinds)

    def test_cli_exit_codes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "d.json"
            d = dump()
            d["masters"]["DFFHQNx1_ASAP7_75t_R"]["n"] = 90000
            p.write_text(json.dumps(d))
            self.assertEqual(F.main(["check", str(p), "--out", str(Path(td) / "r.json")]), 3)
            self.assertEqual(F.main(["check", str(p), "--set", "util_max=0.7", "--set", "util_hold_max=0.85"]), 0)
            self.assertEqual(F.main(["check", str(p), "--warn-only"]), 0)


def run_launch(spec_extra, kind="route"):
    spec = {"name": "t", "block": "b", "route_hold_corners": "keep",
            "source": {"branch": "main", "commit": "c" * 40}, "stages": {}, **spec_extra}
    j = {"name": "t", "run": "/r", "host": "ot-epyc3", "spec": spec, "commit_full": "c" * 40, "attempt": 1,
         "created": "2026-10-08T19:00:00-07:00"}
    bodies = []

    def fake_ssh(host, c, input=None, **k):
        if input is not None:
            bodies.append(input)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "ship_helpers"), patch.object(cl, "is_local", lambda h: False):
        cl.launch_stage(j, {"kind": kind, "key": kind, "threads": 4}, "echo x")
    return bodies[0]


class LoopWiring(unittest.TestCase):
    def test_default_on(self):
        b = run_launch({})
        self.assertIn("export OT_FP_LINT=1 OT_FP_LINT_DIR=/r/cl/fplint/route.a1", b)
        self.assertIn("cp -f /r/cl/$f /r/src/tools/$f", b)
        self.assertIn("-v \"$OT_FP_LINT_DIR:/ot_fplint\"", b)          # the docker shim mounts the verdict dir
        self.assertIn("OT_FP_LINT_DIR=/r/cl/fplint/calibrate.a1", run_launch({}, "calibrate"))

    def test_opt_out_and_overrides(self):
        self.assertNotIn("export OT_FP_LINT=1", run_launch({"fp_lint": False}))
        b = run_launch({"fp_lint": {"set": {"util_max": 0.62}, "warn_only": True}})
        self.assertIn("OT_FP_LINT_ARGS='--set util_max=0.62 --warn-only'", b)

    def test_crash_becomes_floorplan_margin(self):
        j = {"name": "t", "run": "/r", "host": "ot-epyc3", "stage_tag": "route.a1", "attempt": 1, "retries_used": 0,
             "spec": {"verdict": {}}, "status": "RUNNING"}
        fail = "fp_margin_lint: FAIL util: utilisation 77.5% > 60%\nFLOORPLAN_MARGIN: util: utilisation 77.5% > 60%"
        done = {}

        def fake_ssh(host, c, **k):
            return SimpleNamespace(returncode=0, stdout=fail if "fplint/route.a1/FAIL" in c else "", stderr="")

        def fake_finish(j, status, reason, text):
            done.update(status=status, reason=reason, text=text)
        with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "finish", fake_finish), \
                patch.object(cl, "kill_own_stage", lambda j: done.setdefault("killed", True)):
            cl.crash(j, {"kind": "route", "key": "route"}, None, "rc=1")
        self.assertEqual(done["status"], "FLOORPLAN_MARGIN")
        self.assertTrue(done["reason"].startswith("util: utilisation 77.5%"))
        self.assertTrue(done.get("killed"))
        self.assertIn("FLOORPLAN_MARGIN", cl.TERMINAL)


if __name__ == "__main__":
    unittest.main()
