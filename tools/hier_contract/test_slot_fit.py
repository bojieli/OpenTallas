#!/usr/bin/env python3
"""slot fit at submit + die real-view census (owner 2026-10-13)"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ref_tile"))
import slot_fit as SF  # noqa: E402
import die_real_census as DC  # noqa: E402
import pre_route_gate as G  # noqa: E402

SLOT = {"name": "u_a", "cell": "t_a", "kind": "tile", "parent": "u_cl", "outline": {"w": 43.2, "h": 21.6},
        "pins": [{"name": "din[7:0]", "face": "W", "layer": "M4"}, {"name": "dout[7:0]", "face": "E", "layer": "M4"}],
        "clock_entry": {"pin": "clk", "face": "N", "layer": "M5"}, "target_insertion_ps": 150.0,
        "pg_layer": "M5", "strap_layer": "M6", "signal_max_layer": "M5", "layer_cap": "M5", "version": 3}


def repo(td, slots=(SLOT,), die="s81", extra=None):
    d = Path(td) / "results/arch/hier_contract_1011"
    d.mkdir(parents=True, exist_ok=True)
    c = {"schema": SF.SCHEMA, "die": die, "version": 3, "slots": list(slots)}
    c.update(extra or {})
    (d / f"{die}.json").write_text(json.dumps(c))
    return Path(td)


def kit(td, w=43.2, h=21.6, pins=None, cap="M5", pin_h="M4", pin_v="M5", top="t_a", **spec):
    kd = Path(td) / "kit"
    kd.mkdir(exist_ok=True)
    pins = pins or {"W": ["din"], "E": ["dout"], "N": ["clk"]}
    (kd / "spec.json").write_text(json.dumps(dict({"name": "k_a", "top": top, "kind": "tile", "clock_port": "clk",
                                                   "pins": pins}, **spec)))
    (kd / "floorplan.json").write_text(json.dumps({"die": [0, 0, w, h], "pins": pins,
                                                   "layer_contract": {"rlayers": ["M2", cap]}}))
    (kd / "kit.env").write_text(f"TOP={top}\nPIN_H='{pin_h}'\nPIN_V='{pin_v}'\nRLAYERS='M2 {cap}'\n")
    return kd


class Fit(unittest.TestCase):
    def run_(self, slots=(SLOT,), job=None, extra=None, **kw):
        with tempfile.TemporaryDirectory() as td:
            return SF.check(kit(td, **kw), repo(td, slots, extra=extra), job)

    def test_fit(self):
        r = self.run_(est_insertion_ps=180)
        self.assertEqual((r["status"], r["slot"], r["die"], r["version"]), ("fit", "u_a", "s81", 3))

    def test_no_slot(self):
        self.assertEqual(self.run_(top="other")["status"], "no_slot")

    def test_outline(self):
        r = self.run_(w=45.36)
        self.assertEqual(r["status"], "mismatch")
        self.assertIn("outline 45.36 x 21.6 != slot 43.2 x 21.6", r["mismatches"][0])

    def test_pin_face_missing_extra_any(self):
        r = self.run_(pins={"N": ["din", "clk"], "E": ["dout", "dbg"]})
        m = " | ".join(r["mismatches"])
        self.assertIn("din N (slot W)", m)
        self.assertIn("1 planned ports the slot does not have (e.g. dbg)", m)
        r = self.run_(pins={"W": ["din"], "N": ["clk"]})
        self.assertIn("1 slot pins not in the pin plan (e.g. dout)", r["mismatches"][0])
        r = self.run_(pins={"ANY": ["din"], "E": ["dout"], "N": ["clk"]})
        self.assertIn("din ANY (slot W)", r["mismatches"][0])

    def test_clock_face_and_contract_default(self):
        r = self.run_(pins={"W": ["din", "clk"], "E": ["dout"]})
        self.assertIn("clock clk on W (slot clock_entry N)", r["mismatches"])
        s = dict(SLOT, clock_entry={"pin": "ck", "face": "N", "layer": "M4"})     # M4 cannot be an N-face pin
        r = self.run_((s,), pins={"W": ["din", "clk"], "E": ["dout"]})
        self.assertEqual(r["status"], "fit")
        self.assertTrue(any("contract default" in n for n in r["notes"]))

    def test_pin_layer(self):
        r = self.run_(pin_h="M4 M6")
        self.assertTrue(any("pins may land on M6 (slot M4)" in m for m in r["mismatches"]), r)
        r = self.run_(pin_h="M2")
        self.assertTrue(any("slot pin layer M4 is not a kit pin layer" in m for m in r["mismatches"]), r)
        self.assertEqual(self.run_((dict(SLOT, m6_pin_grant={"x": 1}),), pin_h="M4 M6")["status"], "fit")
        s = dict(SLOT, pin_layers={"N": "M3 M5", "S": "M3 M5", "W": "M4 M6", "E": "M4 M6"})
        self.assertEqual(self.run_((s,), pin_h="M4 M6")["status"], "fit")

    def test_layer_cap(self):
        r = self.run_(cap="M6")
        self.assertIn("routing cap M6 above the slot layer cap M5", r["mismatches"])
        self.assertEqual(self.run_((dict(SLOT, layer_cap="M6"),), cap="M5")["status"], "fit")

    def test_insertion(self):
        r = self.run_(est_insertion_ps=320)
        self.assertTrue(any("estimated clock insertion 320 ps" in m and "150 ps" in m for m in r["mismatches"]))
        r = self.run_()                                   # no estimate: a note, not a mismatch
        self.assertEqual(r["status"], "fit")
        self.assertTrue(any("no clock insertion estimate" in n for n in r["notes"]))
        r = self.run_(job={"est_insertion_ps": 400})      # the job spec's estimate wins
        self.assertEqual(r["status"], "mismatch")

    def test_insertion_from_previous_view(self):
        with tempfile.TemporaryDirectory() as td:
            kd = kit(td)
            (kd / "views/t_a").mkdir(parents=True)
            (kd / "views/t_a/t_a_tt.lib").write_text(
                'library (x) { time_unit : "1ps";\n cell (t_a) {\n pin (clk) { clock : true;\n timing () { '
                'timing_type : max_clock_tree_path; cell_rise (s) { values ("410.0"); } } } } }\n')
            r = SF.check(kd, repo(td))
            self.assertTrue(any("410 ps (previous view t_a_tt.lib" in m for m in r["mismatches"]), r)

    def test_variants_and_cluster_plan(self):
        r = self.run_((dict(SLOT, outline={"w": 10, "h": 10}), dict(SLOT, name="u_b")), est_insertion_ps=150)
        self.assertEqual((r["status"], r["slot"], r["variants"]), ("fit", "u_b", 2))
        sub = {"sub_layouts": {"cl_cell": {"rows": [{"tile": "row0", "cell": "t_c", "w": 86.4, "h": 12.96}]}}}
        r = self.run_(extra=sub, top="t_c", w=86.4, h=12.96)
        self.assertEqual((r["status"], r["slot"]), ("fit", "cl_cell:row0"))
        r = self.run_(extra=sub, top="t_c", w=86.4, h=21.6)
        self.assertIn("outline 86.4 x 21.6 != slot 86.4 x 12.96", r["mismatches"][0])

    def test_explicit_contract_and_superseded(self):
        with tempfile.TemporaryDirectory() as td:
            rp = repo(td, (dict(SLOT, outline={"w": 1, "h": 1}), dict(SLOT, name="u_x")))
            kd = kit(td, contract={"file": "results/arch/hier_contract_1011/s81.json", "slot": "u_a"})
            self.assertEqual(SF.check(kd, rp)["status"], "mismatch")      # the named slot, not the best variant
            d = rp / "results/arch/hier_contract_1012"
            d.mkdir()
            (d / "s81_v2.json").write_text(json.dumps({"schema": SF.SCHEMA, "die": "s81b", "version": 1, "slots": [
                dict(SLOT, name="u_new")], "derived_from": {"contract": "results/arch/hier_contract_1011/s81.json"}}))
            self.assertEqual([c["file"] for c in SF.load_contracts(rp)], ["results/arch/hier_contract_1012/s81_v2.json"])
            r = SF.check(kd, rp)                                          # the named contract is superseded
            self.assertEqual((r["status"], r["slot"], r["die"]), ("fit", "u_new", "s81b"))


class Gate(unittest.TestCase):
    def gate(self, td, job, **kw):
        g = G.Gate()
        with patch.object(SF, "LOG_DIR", Path(td)):
            res = G.check_slot_fit(g, kit(td, **kw), job, str(repo(td)), "abcdef0123456789")
        return g, res

    def test_refused(self):
        with tempfile.TemporaryDirectory() as td:
            g, _ = self.gate(td, {"name": "j1"}, w=45.36)
            self.assertEqual(g.verdict, "FAIL")
            self.assertIn("does not fit slot u_a", g.items[-1]["message"])
            self.assertIn("slot_change_request", g.items[-1]["fix"])
            self.assertFalse((Path(td) / "el1011-s81die.log").exists())

    def test_change_request_warns_and_logs_once(self):
        with tempfile.TemporaryDirectory() as td:
            job = {"name": "j1", "slot_change_request": "el1011-s81die.log 10-13 04:10 slot u_a 45.36 wide, contract v4"}
            for _ in range(2):
                g, _ = self.gate(td, job, w=45.36)
                self.assertEqual(g.verdict, "WARN")
            log = (Path(td) / "el1011-s81die.log").read_text()
            self.assertEqual(log.count("SLOT_CHANGE_REQUEST job=j1 commit=abcdef012345 slot=u_a"), 1)
            self.assertIn("contract v4", log)
            self.assertIn("outline 45.36 x 21.6 != slot 43.2 x 21.6", log)
            g, _ = self.gate(td, {"name": "j2"}, w=45.36, slot_change_request="contract v4")   # tile spec carries it
            self.assertEqual(g.verdict, "WARN")

    def test_fit_and_no_slot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            g, _ = self.gate(td, {"name": "j1"})
            self.assertEqual(g.verdict, "PASS")
            g, res = self.gate(td, {"name": "j1"}, top="unplanned")
            self.assertEqual((g.verdict, res["status"], g.items), ("PASS", "no_slot", []))

    def test_contract_from_git_ref(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            rp = repo(td)
            run = lambda *a: subprocess.run(["git", "-C", td, "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                            check=True, capture_output=True)
            run("init", "-q", "-b", "main")
            run("add", "results")
            run("commit", "-q", "-m", "c")
            (rp / "results/arch/hier_contract_1011/s81.json").unlink()        # stale checkout: the ref still has it
            self.assertEqual(SF.load_contracts(rp), [])
            cs, ref = SF.live_contracts(rp)
            self.assertEqual((ref, [c["file"] for c in cs]), ("main", ["results/arch/hier_contract_1011/s81.json"]))
            g = G.Gate()
            G.check_slot_fit(g, kit(td, w=45.36), {"name": "j"}, td, "")
            self.assertEqual(g.verdict, "FAIL")
            self.assertIn("v3 (main)", g.items[-1]["message"])

    def test_lead_logs(self):
        self.assertEqual(SF.lead_log("qwen_rom_tp8").name, "el1011-qwen-tp8.log")
        self.assertEqual(SF.lead_log("ds_rom_s81_layer1").name, "el1011-s81die.log")
        self.assertEqual(SF.lead_log("hbm_r25gq").name, "el1011-hbmdie.log")
        self.assertEqual(SF.lead_log("x", "results/arch/hier_contract_1011/r25gq.json").name, "el1011-hbmdie.log")
        self.assertIsNone(SF.lead_log("unknown"))


LEF = "MACRO {m}\n  CLASS BLOCK ;\n  SIZE {w} BY {h} ;\n  PIN a\n    PORT\n      LAYER M4 ;\n        RECT 0 1 {x} 1.024 ;\n    END\n  END a\nEND {m}\n"
LIB = 'library (l_{m}) {{\n  cell ({m}) {{\n    area : {a};\n    pin (a) {{ direction : input; }}\n  }}\n}}\n'


class Census(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name) / "src"
        self.case = Path(self.td.name) / "case"
        self.case.mkdir()
        for sub, m, w, a in (("physical/ref_tile/k/views/t_real", "t_real", 43.2, 1), ("physical/v/t_lef", "t_lef", 21.6, 2),
                             ("physical/v/t_etm", "t_etm", 21.6, 3), ("physical/asap7_memory_macros_v2/rom", "rom", 10.8, 4),
                             ("physical/v/t_cand", "t_cand", 21.6, 5)):
            d = self.root / sub
            d.mkdir(parents=True)
            (d / f"{m}.lef").write_text(LEF.format(m=m, w=w, h=10.8, x=0.2))
            (d / f"{m}_tt.lib").write_text(LIB.format(m=m, a=a))
        gen = lambda m, w, x=0.2: LEF.format(m=m, w=w, h=10.8, x=x)  # noqa: E731
        # real + lef_only exact; t_etm / t_cand generated (other pin rect); t_gen has no view at all
        (self.case / "elements.lef").write_text(
            "VERSION 5.8 ;\n" + gen("t_real", 43.2).replace("\n", "\n ") + gen("t_lef", 21.6) + gen("t_etm", 21.6, 0.3)
            + gen("t_cand", 99.0) + gen("t_gen", 5.4) + "END LIBRARY\n")
        (self.case / "macros.lef").write_text("PROPERTYDEFINITIONS\n  MACRO width INTEGER ;\nEND PROPERTYDEFINITIONS\n"
                                              + gen("rom", 10.8))
        (self.case / "merged_tt.lib").write_text(     # merged ETM lib: t_real / t_etm / rom copied, t_lef a budget view
            "library (merged) {\n" + "".join(LIB.format(m=m, a=a).split("\n", 1)[1].rsplit("}", 1)[0]
                                              for m, a in (("t_real", 1), ("t_lef", 77), ("t_etm", 3), ("rom", 4), ("t_gen", 9)))
            + "}\n")
        (self.case / "die.v").write_text(
            "module die (input ck);\n  wire n1;\n" + "".join(f"  {m} u{i}_{k} (.a(n1));\n" for i, (m, n) in enumerate(
                (("t_real", 3), ("t_lef", 2), ("t_etm", 4), ("rom", 5), ("t_cand", 6), ("t_gen", 7), ("BUFx2_ASAP7_75t_R", 9)))
                for k in range(n)) + "  t_real \\esc[0] (.a(n1));\nendmodule\n")
        (self.case / "placed.def").write_text(
            "DESIGN die ;\nCOMPONENTS 3 ;\n - u0 t_real + PLACED ( 0 0 ) N ;\n - u1 t_gen + FIXED ( 0 0 ) N ;\n"
            " - u2 t_gen ;\nEND COMPONENTS\nNETS 1 ;\n - n1 t_real ;\nEND NETS\n")

    def tearDown(self):
        self.td.cleanup()

    def test_case(self):
        out = Path(self.td.name) / "out"
        argv = ["--die", "d", "--case", "it1", "--netlist", str(self.case / "die.v"), "--lef", str(self.case / "elements.lef"),
                "--lef", str(self.case / "macros.lef"), "--lib", str(self.case / "merged_tt.lib"), "--repo", str(self.root),
                "--out", str(out), "--source", "abc123"]
        self.assertEqual(DC.main(argv), 0)
        r = json.loads((out / "d_it1.json").read_text())
        self.assertEqual({m: v["class"] for m, v in r["masters"].items()},
                         {"t_real": "real", "t_lef": "lef_only", "t_etm": "etm_only", "rom": "hard_macro",
                          "t_cand": "placeholder", "t_gen": "placeholder"})
        s = r["summary"]
        self.assertEqual((s["instances"], s["real"], s["lef_only"], s["etm_only"], s["hard_macro"], s["placeholder"]),
                         (28, 4, 2, 4, 5, 13))
        self.assertEqual((r["other_instances"], s["placeholder_with_view"]), (9, 6))
        self.assertEqual(r["masters"]["t_real"]["view"], "physical/ref_tile/k/views/t_real")
        self.assertTrue(r["masters"]["t_etm"]["lef_near"])
        self.assertEqual(s["top_placeholders"][0], ["t_gen", 7])
        self.assertEqual(DC.main(argv + ["--min-real-frac", "0.5"]), 1)
        rows = [ln for ln in (out / "README.md").read_text().splitlines() if ln.startswith("| d | it1 |")]
        self.assertEqual(len(rows), 1)                    # re-run replaces the row
        self.assertIn("| 28 | 4 | 2 | 4 | 5 | 13 | 14.29 | 1 / 6 |", rows[0])

    def test_view_lib_read_by_path_and_def(self):
        out = Path(self.td.name) / "out"
        ll = self.case / "libs_tt.txt"
        ll.write_text(f"/SRC/physical/ref_tile/k/views/t_real/t_real_tt.lib\n/SRC/missing_tt.lib\n")
        self.assertEqual(DC.main(["--die", "d", "--case", "c2", "--def", str(self.case / "placed.def"), "--lef",
                                  str(self.case / "elements.lef"), "--lib-list", str(ll), "--lib-map", f"/SRC={self.root}",
                                  "--repo", str(self.root), "--out", str(out)]), 0)
        s = json.loads((out / "d_c2.json").read_text())["summary"]
        self.assertEqual((s["instances"], s["real"], s["placeholder"]), (3, 1, 2))

    def test_contract(self):
        out = Path(self.td.name) / "out"
        c = Path(self.td.name) / "c.json"
        mk = lambda n, cell, w: {"name": n, "cell": cell, "kind": "tile", "outline": {"w": w, "h": 10.8}}  # noqa: E731
        c.write_text(json.dumps({"schema": SF.SCHEMA, "die": "d", "version": 7, "slots": [
            {"name": "d", "cell": "die", "kind": "die", "outline": {"w": 1, "h": 1}}, mk("a", "t_real", 43.2),
            mk("b", "t_real", 43.2), mk("c", "t_lef", 30.0), mk("e", "t_none", 5.0), mk("f", "rom", 10.8)]}))
        self.assertEqual(DC.main(["--die", "d", "--contract", str(c), "--repo", str(self.root), "--out", str(out)]), 0)
        r = json.loads((out / "d_v7.json").read_text())
        s = r["summary"]
        self.assertEqual((r["mode"], s["instances"], s["real"], s["hard_macro"], s["placeholder"]), ("contract", 5, 2, 1, 2))
        self.assertIn("| d | v7 | contract |", (out / "README.md").read_text())
        # a bindable view is held against the slot's pins: no contract pins = nothing to differ from
        self.assertEqual((r["masters"]["t_real"]["slot_pins"], s["real_slot_exact"]), ("exact", 2))
        d = json.loads(c.read_text())
        for sl in d["slots"]:
            if sl["cell"] == "t_real":
                sl["pins"] = [{"name": "no_such_pin[3:0]", "face": "N", "layer": "M5"}]
                sl["layer_cap"] = {"cap": "M5", "view_max_layer": "M8", "conforms": False}
        c.write_text(json.dumps(d))
        self.assertEqual(DC.main(["--die", "d", "--contract", str(c), "--repo", str(self.root), "--out", str(out)]), 0)
        r = json.loads((out / "d_v7.json").read_text())
        self.assertEqual((r["summary"]["real"], r["summary"]["real_slot_exact"]), (2, 0))
        self.assertEqual(r["masters"]["t_real"]["slot_pins"], "differ")
        self.assertIn("contract pins missing", " ".join(r["masters"]["t_real"]["slot_check"]))

    def test_child_lint_dict_layer_cap(self):
        import child_lint as CL
        s = {"layer_cap": {"cap": "M5", "view_max_layer": "M8", "conforms": False}, "view_cap": "M8"}
        self.assertEqual((CL.pick_cap(s, "M5"), CL.pick_cap(s, "M8"), CL.pick_cap(s, None)), (5, 8, 5))


if __name__ == "__main__":
    unittest.main()
