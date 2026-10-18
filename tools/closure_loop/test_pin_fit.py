"""flowfix 2026-10-13: the gate judges a pin plan with the ROUTE's pin-placement settings (tools/pin_fit.py), and kit
recipe 2 spreads the pin flops behind the pin hold stages on a dense face.

Reproduces qkd_seq_fan: kc2 (1,623 pins on the 162 um W face, M4 at two tracks) passed the gate, which ran with one pin
group per region, and died in the route, which chunks groups of 32, at 3_2_place_iop with [PPL-0093] "Pin group of size
23 does not fit"; kc3 placed its pins and failed global route behind the 10.4 b/um face (GRT-0116); kc4 closed its
pin placement with pin_ranges + pin_balance and OT_OFLOP_GAP 4.5 / 6 columns."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "ref_tile"))
import pin_fit as PF  # noqa: E402
import pre_route_gate as G  # noqa: E402
import ref_tile as RT  # noqa: E402
import submit_lint as SL  # noqa: E402

LC = {"layer_cap": "M5", "rlayers": ("M2", "M5"), "cap_basis": "new tile"}
W_PORTS = {"aq": 540, "kvn": 1047, "kc": 33, "kvn_cr": 1, "af": 1, "mf": 1}
E_PORTS = {"aqm": 2, "q": 538, "kwm": 24, "kw": 1023, "kc_i": 33, "cr_o": 1, "af_o": 1, "mf_o": 1}
PORTS = {**{k: (v, v > 1) for k, v in {**W_PORTS, **E_PORTS}.items()}, "ck": (1, False), "rst_n": (1, False)}
DIRS = {**{k: "input" for k in E_PORTS}, **{k: "output" for k in W_PORTS}, "ck": "input", "rst_n": "input"}
OUTLINE = [51.84, 162.0]
KC4_RANGES = {"aq": [1.0, 53.0], "kvn": [54.0, 155.0], "kvn_cr": [155.3, 155.5], "kc": [156.0, 159.4],
              "af": [159.8, 160.0], "mf": [160.4, 160.6], "q": [1.0, 50.3], "aqm": [50.3, 53.0], "kw": [54.0, 152.7],
              "kwm": [152.7, 155.0], "cr_o": [155.3, 155.5], "kc_i": [156.0, 159.4], "af_o": [159.8, 160.0],
              "mf_o": [160.4, 160.6], "ck": [25.8, 26.0], "rst_n": [25.8, 26.0]}
TCL = ROOT / "physical/qwen_die_masters/io_flop_at_pins.tcl"


def seq_fan(**kw):
    s = {"name": "qkd_seq_fan", "top": "qkd_seq_fan", "kind": "tile", "clock_port": "ck",
         "pins": {"W": list(W_PORTS), "E": list(E_PORTS), "N": ["ck"], "S": ["rst_n"]},
         "route": {"pin_h": "M4", "pin_v": "M5"}, "recipe": 2, "inhold": True, "outhold": True,
         "io_flop_at_pins": {"cols": 4, "allow_none": True}}
    s.update(kw)
    return s


def fails(g, check):
    return [i for i in g.items if i["check"] == check and i["severity"] == "FAIL"]


def warns(g, check):
    return [i for i in g.items if i["check"] == check and i["severity"] == "WARN"]


class RouteSettingsAreTheGateSettings(unittest.TestCase):
    def test_one_group_bound_everywhere(self):
        job = RT.gen_job({**seq_fan(), "sources": [], "route": {}, "job": {}}, "physical/ref_tile/k", "c" * 40, [])
        self.assertIn(f" OT_PIN_GROUP_MAX={PF.ROUTE_PIN_GROUP_MAX} bash tools/ref_tile/ref_route.sh ",
                      job["stages"]["route"]["cmd"])
        sh = (ROOT / "tools/ref_tile/ref_route.sh").read_text()
        m = re.search(r"^export OT_PIN_GROUP_MAX=\$\{OT_PIN_GROUP_MAX:-(\d+)\}$", sh, re.M)
        self.assertTrue(m, "ref_route.sh applies the route's group bound to every caller (route, gate, --cts)")
        self.assertEqual(int(m.group(1)), PF.ROUTE_PIN_GROUP_MAX)
        self.assertLess(sh.index('source "$KITENV"'), m.start())         # the kit's own export wins (quoted since 7c1815717)
        self.assertIn("OT_PIN_GROUP_MAX={PGM} bash tools/ref_tile/ref_route.sh", G.REMOTE_SH)
        self.assertEqual(SL.FIXES[0]["env"]["OT_PIN_GROUP_MAX"], str(PF.ROUTE_PIN_GROUP_MAX))

    def test_settings_follow_the_kit(self):
        st = RT.route_pin_settings(seq_fan(), LC)
        self.assertEqual((st["group_max"], st["balance"], st["tracks"], st["h"], st["v"]), (32, False, 2.0, ["M4"], ["M5"]))
        s = seq_fan(route={"pin_h": "M4", "pin_v": "M5", "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}})
        st = RT.route_pin_settings(s, LC)
        env = "\n".join(RT.pin_balance_env(s["route"], LC))
        self.assertIn(f"export OT_PIN_GROUP_MAX={st['group_max']}\n", env)
        self.assertEqual((st["group_max"], st["balance"], st["h"]), (1, True, ["M4"]))
        # the kit.env regions and the judged regions are the same list
        self.assertEqual([(r["names"], r["face"], r["range"]) for r in RT.pin_regions(seq_fan(pin_ranges={"aq": [1, 53]}))][:2],
                         [(["kvn", "kc", "kvn_cr", "af", "mf"], "W", None), (["aq"], "W", (1.0, 53.0))])


class SeqFanPinFit(unittest.TestCase):
    def test_kc2_full_face_is_refused_with_the_fix_named(self):
        g = G.Gate()
        G.check_pin_fit(g, seq_fan(), PORTS, OUTLINE, LC)
        f = fails(g, "pin_fit")
        self.assertEqual(len(f), 2, g.items)                     # W (where the route died) and the mirrored E face
        self.assertIn("PPL-0093", f[0]["message"])
        self.assertIn("W face 162 um", f[0]["message"])
        self.assertIn("1623 pins = 51 ordered groups of <= 32", f[0]["message"])
        self.assertIn("1 group(s) of 23 pins find no section", f[0]["message"])     # the route's own error: size 23
        self.assertIn("OT_PIN_GROUP_MAX=32", f[0]["message"])
        for word in ("pin_ranges", "pin_balance", "longer edge"):
            self.assertIn(word, f[0]["fix"])
        self.assertEqual(g.verdict, "FAIL")                                         # REFUSED at submit

    def test_the_old_gate_setting_passed_it(self):
        # one group per region (no OT_PIN_GROUP_MAX): the placer's fallback finds 1,623 contiguous slots of 1,672
        self.assertTrue(PF.region_fit(1623, 0, 162, 162, ["M4"], 2, 0)["fits"])
        self.assertFalse(PF.region_fit(1623, 0, 162, 162, ["M4"], 2, PF.ROUTE_PIN_GROUP_MAX)["fits"])
        self.assertEqual(PF.slot_count(0, 162, 162, 0.096), 1672)
        self.assertEqual(PF.section_bins(1672), [200] * 8 + [72])

    def test_kc4_ranges_and_balance_pass(self):
        g = G.Gate()
        s = seq_fan(pin_ranges=KC4_RANGES, route={"pin_h": "M4", "pin_v": "M5",
                                                  "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}})
        G.check_pin_fit(g, s, PORTS, OUTLINE, LC)
        self.assertEqual(fails(g, "pin_fit"), [], g.items)

    def test_a_longer_edge_passes(self):
        g = G.Gate()
        G.check_pin_fit(g, seq_fan(), PORTS, [51.84, 172.8], LC)
        self.assertEqual(fails(g, "pin_fit"), [], g.items)

    def test_balance_too_tight_is_refused(self):
        g = G.Gate()
        s = seq_fan(pin_ranges={**KC4_RANGES, "kvn": [54.0, 100.0]},
                    route={"pin_h": "M4", "pin_v": "M5", "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}})
        G.check_pin_fit(g, s, PORTS, OUTLINE, LC)
        self.assertEqual(len(fails(g, "pin_fit")), 1)
        self.assertIn("balanced pins", fails(g, "pin_fit")[0]["message"])

    def test_measured_routes(self):
        # smh_pt_w_ref_p45h: 3,705 pins on 371.52 um -> group of 25 left (the log: max contiguous 22 < 25)
        self.assertEqual(PF.region_fit(3705, 0, 371.52, 371.52, ["M4"], 2, 32)["left"], [25])
        # a section of 200 slots takes six groups of 32 and strands 8 ("Not enough available positions (8)")
        self.assertEqual(PF.pack([32] * 7, [200]), [32])
        # exact io_tcl kits and unknown widths are not judged
        g = G.Gate()
        G.check_pin_fit(g, seq_fan(io_tcl="x.tcl"), PORTS, OUTLINE, LC)
        G.check_pin_fit(g, seq_fan(), {**PORTS, "kvn": (None, True), "kw": (None, True)}, OUTLINE, LC)
        self.assertEqual(fails(g, "pin_fit"), [])
        self.assertTrue(any(i["severity"] == "INFO" and "not estimated for 2 region(s)" in i["message"] for i in g.items))

    def test_widths_take_the_spec_parameters(self):
        # the estimate refuses a kit, so widths come only from the fully resolved header (spec params applied):
        # hgi_dma_back_b2 / qfd_tt_up4_leaf were 3-6x too wide at the module defaults, and both are CLOSED
        sv = ("module t #(parameter int NL = 16, parameter int W = NL * 8) (input logic ck,\n"
              "  input logic [NL-1:0][W-1:0] d, output logic [W-1:0] q, output logic v);\nendmodule\n")
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "t.sv").write_text(sv)
            self.assertEqual(G.strict_widths(["t.sv"], "t", {"NL": 4}, Path(td)),
                             {"ck": (1, False), "d": (4 * 32, True), "q": (32, True), "v": (1, False)})
            self.assertEqual(G.strict_widths(["t.sv"], "t", {}, Path(td))["d"], (16 * 128, True))
            (Path(td) / "u.sv").write_text("module u (input my_pkg::bus_t d);\nendmodule\n")
            self.assertIsNone(G.strict_widths(["u.sv"], "u", {}, Path(td)))          # not modelled: no estimate
            self.assertIsNone(G.strict_widths(["t.sv"], "missing", {}, Path(td)))
        g = G.Gate()
        G.check_pin_fit(g, seq_fan(), None, OUTLINE, LC)
        self.assertEqual(fails(g, "pin_fit"), [])
        self.assertTrue(any("not estimated" in i["message"] for i in g.items))

    def test_die_master_lint_uses_the_same_model(self):
        plan = {"die": (51.84, 162.0), "regions": [{"regex": "^w", "edge": "left", "n": 1623}], "free": 0}
        d = SL.density(plan, {"PIN_H": "M4", "PIN_V": "M5"}, 2, group_max=32)
        self.assertEqual(len(d["left"]["ppl"]), 1)
        self.assertIn("23 pins find no section", d["left"]["ppl"][0])
        self.assertEqual(SL.density(plan, {"PIN_H": "M4", "PIN_V": "M5"}, 2, group_max=0)["left"]["ppl"], [])


class RecipeTwoPinFlopSpread(unittest.TestCase):
    def test_model_reproduces_the_working_setting(self):
        d = PF.face_density(1623, 162.0, ["M4"], 2, False)
        self.assertEqual(d, 10.5)                                # 105 pins in a 10 um window at 0.096 um a pin
        p = PF.oflop_plan(d, PF.STAGE_OUT_UM, True, 4)
        self.assertEqual((p["dense"], p["gap"], p["cols"]), (True, 4.5, 6))          # kc4: OT_OFLOP_GAP 4.5, 6 columns
        sparse = PF.oflop_plan(2.0, PF.STAGE_OUT_UM, True, 4)
        self.assertEqual((sparse["dense"], sparse["gap"], sparse["cols"]), (False, 1.0, 4))   # unchanged below ~6 b/um

    def test_tcl_constants_equal_the_model(self):
        t = TCL.read_text()
        for name, val in (("win", PF.OFLOP_WIN_UM), ("row", PF.OFLOP_ROW_UM), ("dense", PF.OFLOP_DENSE_UM),
                          ("slack", PF.OFLOP_SLACK), ("cols_v", PF.OFLOP_COLS_V), ("cols_h", PF.OFLOP_COLS_H),
                          ("depth_max", PF.OFLOP_DEPTH_MAX)):
            m = re.search(rf"^set ot_au_{name} ([\d.]+)$", t, re.M)
            self.assertTrue(m, name)
            self.assertEqual(float(m.group(1)), float(val), name)
        self.assertIn("OT_OFLOP_AUTO", t)
        self.assertIn("$::env(OT_OFLOP_GAP) : 1.0}]", t)                              # explicit gap still read
        self.assertIn("$::env(OT_OFLOP_COLS) : 4}]", t)

    def _tcl(self, env, n=1623, hw=PF.STAGE_OUT_UM, side="L", core=(2.16, 2.16, 49.68, 159.84)):
        body = TCL.read_text()
        head = body[body.index("set ot_au_on"):body.index("set ot_hops")]
        blk = body[body.index("# >>> auto spread"):body.index("# <<< auto spread")]
        cand = " ".join(f"{{{side} {0.78 + k * 0.096:.3f} ffm 0 0 OUTPUT {hw}}}" for k in range(n))
        script = ("proc ffm {a} { return mm }\nproc mm {a} { return [expr {$a eq \"getWidth\" ? 1080 : 270}] }\n"
                  + "".join(f"set ::env({k}) {v}\n" for k, v in env.items())
                  + "set ot_dbu 1000\nlassign {%s} cx0 cy0 cx1 cy1\n" % " ".join(map(str, core))
                  + "set ot_gap [expr {[info exists ::env(OT_OFLOP_GAP)] ? $::env(OT_OFLOP_GAP) : 1.0}]\n"
                  + "set ot_cols [expr {[info exists ::env(OT_OFLOP_COLS)] ? $::env(OT_OFLOP_COLS) : 4}]\n"
                  + head + f"set cand [list {cand}]\n" + blk
                  + f"\nputs \"RESULT $ot_sgap({side}) $ot_scols({side})\"\n")
        with tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False) as f:
            f.write(script)
        try:
            r = subprocess.run(["tclsh", f.name], capture_output=True, text=True, timeout=60)
        finally:
            Path(f.name).unlink()
        self.assertEqual(r.returncode, 0, r.stderr)
        gap, cols = r.stdout.strip().splitlines()[-1].split()[1:]
        return float(gap), int(cols), r.stdout

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh not installed")
    def test_hook_derives_gap_and_columns(self):
        p = PF.oflop_plan(PF.face_density(1623, 162.0, ["M4"], 2, False), PF.STAGE_OUT_UM, True, 4)
        gap, cols, out = self._tcl({"OT_OFLOP_COLS": 4})
        self.assertEqual((gap, cols), (p["gap"], p["cols"]), out)                    # 4.5 um, 6 columns
        self.assertIn("OT_IOFLOP auto side L", out)
        self.assertEqual(self._tcl({"OT_OFLOP_COLS": 4}, hw=0.0)[:2], (1.0, 4))      # no FIRM hold stages: unchanged
        self.assertEqual(self._tcl({}, n=40)[:2], (1.0, 4))                          # sparse face: unchanged
        self.assertEqual(self._tcl({"OT_OFLOP_GAP": 2.5, "OT_OFLOP_COLS": 8})[:2], (2.5, 8))   # explicit overrides kept
        self.assertEqual(self._tcl({"OT_OFLOP_AUTO": 0})[:2], (1.0, 4))              # derivation off
        # N / S face: rows instead of columns, same depth rule
        ph = PF.oflop_plan(PF.face_density(1623, 162.0, ["M5"], 2, False), PF.STAGE_OUT_UM, False, 4)
        gap, cols, out = self._tcl({}, side="B", core=(2.16, 2.16, 159.84, 49.68))
        self.assertEqual((gap, cols), (ph["gap"], ph["cols"]), out)
        # a tile too shallow for the band keeps the flops inside the core
        gap, cols, out = self._tcl({}, core=(2.16, 2.16, 14.0, 159.84))
        self.assertIn("WARNING", out)
        self.assertEqual((gap, cols), (4.5, 1))                  # never fewer than one column; the submit lint refuses

    def _oflop(self, spec, tcl, outline=OUTLINE):
        g = G.Gate()
        plan = G.check_pin_fit(G.Gate(), spec, PORTS, outline, LC)
        G.check_oflop(g, spec, plan, DIRS, outline, tcl)
        return g

    def test_submit_lint_estimates_the_face(self):
        bal = {"pin_h": "M4", "pin_v": "M5", "pin_balance": {"group_max": 1, "h": "M4", "v": "M5"}}
        kc3 = seq_fan(pin_ranges=KC4_RANGES, route=bal)
        new = TCL.read_text()
        old = "set ot_gap 1.0 ;# a source before the automatic spread\n"
        # kc3: dense output face, hook without the derivation, no explicit gap -> WARN with the settings named (never refused)
        g = self._oflop(kc3, old)
        f = [i for i in warns(g, "oflop") if i["message"].startswith("W face")]
        self.assertEqual(len(f), 1, g.items)
        self.assertEqual(len(warns(g, "oflop")), 2)              # the E (input) face is dense too: gap 3.x um
        self.assertIn("W face 10.4 pins/um", f[0]["message"])
        self.assertIn("gap 4.5 um and 6 columns", f[0]["message"])
        self.assertIn('"OT_OFLOP_GAP": "4.5"', f[0]["fix"])
        self.assertIn('"cols": 6', f[0]["fix"])
        # the same kit on a source with the automatic spread passes (INFO with the numbers)
        g = self._oflop(kc3, new)
        self.assertEqual(warns(g, "oflop") + fails(g, "oflop"), [], g.items)
        self.assertTrue(any(i["check"] == "oflop" and "derived in the flow" in i["message"] for i in g.items))
        # kc4's explicit setting passes on either source; an explicit gap that stacks them is flagged
        kc4 = seq_fan(pin_ranges=KC4_RANGES, route=bal, orfs_vars={"OT_OFLOP_GAP": "4.5"},
                      io_flop_at_pins={"cols": 6, "allow_none": True})
        self.assertEqual(warns(self._oflop(kc4, old), "oflop"), [])
        self.assertEqual(len(warns(self._oflop({**kc4, "orfs_vars": {"OT_OFLOP_GAP": "1.0"}}, new), "oflop")), 2)
        self.assertEqual(len(warns(self._oflop({**kc3, "orfs_vars": {"OT_OFLOP_AUTO": "0"}}, new), "oflop")), 2)
        # a tile too shallow behind its dense face is flagged whatever the hook does
        f = warns(self._oflop(kc3, new, outline=[21.6, 162.0]), "oflop")
        self.assertEqual(len(f), 2)
        self.assertIn("longer edge", f[0]["fix"])
        # recipe 1 / no hold stages / a sparse face: not judged
        self.assertEqual(self._oflop(seq_fan(recipe=1, pin_ranges=KC4_RANGES, route=bal), old).items, [])
        sparse = seq_fan(pin_ranges={**KC4_RANGES, "kvn": [54.0, 155.0]}, route=bal)
        ports = {**PORTS, "aq": (100, True), "kvn": (200, True), "q": (100, True), "kw": (200, True)}
        g = G.Gate()
        G.check_oflop(g, sparse, G.check_pin_fit(G.Gate(), sparse, ports, OUTLINE, LC), DIRS, OUTLINE, old)
        self.assertEqual(g.items, [])


def _has(commit):
    return subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}:physical/ref_tile/qkd_seq_fan/kit.env"],
                          capture_output=True).returncode == 0


class SubmitHookOnTheRealKits(unittest.TestCase):
    """the closure loop's submit hook on the three committed qkd_seq_fan kits, each at its job's source commit"""

    def _submit(self, commit, **kw):
        spec = {"ref_tile": True, "name": "qkd_seq_fan-x", "source": {"commit": commit}, **kw,
                "stages": {"route": {"cmd": "bash tools/ref_tile/ref_route.sh physical/ref_tile/qkd_seq_fan/kit.env L R"}}}
        return G.submit_check(spec, str(ROOT), clock_mode="off")

    @unittest.skipUnless(_has("dbf8a21da"), "commit dbf8a21da not in this clone")
    def test_kc2_refused_at_submit(self):
        r = self._submit("dbf8a21da")
        self.assertEqual(r["verdict"], "REFUSE", r)
        self.assertIn("pin_fit: the route's pin placement cannot place this plan (PPL-0093", r["message"])
        self.assertIn("1 group(s) of 23 pins find no section", r["message"])
        self.assertIn("pin_ranges and set route.pin_balance", r["message"])
        # a loop successor of a routed parent is never stopped by the estimate
        r = self._submit("dbf8a21da", auto_react_parent="qkd_seq_fan-kc2-dbf8a21da")
        self.assertEqual(r["verdict"], "WARN", r)

    @unittest.skipUnless(_has("c95524d49"), "commit c95524d49 not in this clone")
    def test_kc3_warned_for_the_stacked_pin_flops(self):
        r = self._submit("c95524d49")
        self.assertEqual(r["verdict"], "WARN", r)                  # an estimate over every port: named, not refused
        self.assertNotIn("pin_fit", r["message"])                 # its pin_ranges + pin_balance plan places
        self.assertIn("oflop: ", r["message"])
        self.assertIn("W face 10.4 pins/um", r["message"])
        self.assertIn('"OT_OFLOP_GAP": "4.5"', r["message"])       # the setting that closed kc4
        self.assertIn('"cols": 6', r["message"])

    @unittest.skipUnless(_has("0f9a940a0"), "commit 0f9a940a0 not in this clone")
    def test_kc4_passes(self):
        # pin_fit passes; the owner pin-register rule (10-15 19:50, refuse from 10-16 19:50) independently names this
        # pre-rule kit, so judge the pin_fit check only
        r = self._submit("0f9a940a0")
        self.assertNotIn("pin_fit", r["message"], r)
        self.assertTrue(r["verdict"] == "PASS" or r["message"].startswith("pin_regs:"), r)


if __name__ == "__main__":
    unittest.main()
