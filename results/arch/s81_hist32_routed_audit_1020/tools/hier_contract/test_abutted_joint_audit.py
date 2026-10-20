#!/usr/bin/env python3
"""Unit tests for abutted_joint_audit.py (pure python, synthetic fixtures; no die data, no EDA tools).

    python3 -m pytest -q tools/hier_contract/test_abutted_joint_audit.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abutted_joint_audit as aja  # noqa: E402

N = 64


def lef(name, port, face, w=10.0, h=10.0, order=None, direction="OUTPUT"):
    """one macro, bus `port[0..N-1]` on `face`, bit k at lo + (hi-lo)(k+.5)/N over 1..9 (order permutes slots)"""
    order = order or list(range(N))
    L = [f"MACRO {name}", "  CLASS BLOCK ;", f"  SIZE {w} BY {h} ;"]
    for slot, k in enumerate(order):
        t = 1 + 8 * (slot + 0.5) / N
        x, y = {"E": (w - 0.05, t), "W": (0.05, t), "N": (t, h - 0.05), "S": (t, 0.05)}[face]
        L += [f"  PIN {port}[{k}]", f"    DIRECTION {direction} ;", "    USE SIGNAL ;", "    PORT", "      LAYER M5 ;",
              f"        RECT {x - 0.01:.3f} {y - 0.01:.3f} {x + 0.01:.3f} {y + 0.01:.3f} ;", "    END", f"  END {port}[{k}]"]
    L.append(f"END {name}")
    return "\n".join(L) + "\n"


def spec(top, face, port, balance=True, desc=False):
    s = {"name": top.lower(), "top": top, "kind": "tile", "pins": {face: [port]}, "pin_ranges": {port: [1.0, 9.0]},
         "route": {"pin_balance": {"group_max": 1}} if balance else {}}
    if desc:
        s["pin_order_desc"] = [port]
    return s


class Case:
    def __init__(self, ob="R0", balance_b=True, lef_b_order=None, routed_b=False, place_b=True, bx=10.0,
                 verilog=None, b_face="W"):
        self.d = Path(tempfile.mkdtemp(prefix="aja_"))
        kr = self.d / "kits"
        for k, s in (("ka", spec("TA", "E", "d")), ("kb", spec("TB", b_face, "q", balance=balance_b))):
            (kr / "physical/ref_tile" / k).mkdir(parents=True)
            (kr / "physical/ref_tile" / k / "spec.json").write_text(json.dumps(s))
        (self.d / "v.lef").write_text(lef("TA", "d", "E") + lef("TB", "q", b_face, order=lef_b_order, direction="INPUT"))
        (self.d / "die.v").write_text(verilog or ("module top ();\n  wire [63:0] n;\n  TA a (.d(n));\n"
                                                  "  TB b (.q(n[63:0]));\n  TIEHIx1_ASAP7_75t_R t0 (.H(x));\nendmodule\n"))
        pl = ["place_inst -name a -location {0.000 0.000} -orientation R0 -status FIRM"]
        if place_b:
            pl.append(f"set _blk [ord::get_db_block]\not_mts::place [$_blk findInst b] {bx:.3f} 0.000 {ob}")
        (self.d / "place.tcl").write_text("\n".join(pl) + "\n")
        self.args = ["--die", "t", "--verilog", str(self.d / "die.v"), "--place", str(self.d / "place.tcl"),
                     "--lef", str(self.d / "v.lef"), "--kit-root", str(kr), "--out", str(self.d / "o.json"),
                     "--handoff", str(self.d / "h.md")]
        if routed_b:
            (self.d / "lv.tsv").write_text("TB\tclosure-record-x\n")
            self.args += ["--status", f"lane_views:{self.d / 'lv.tsv'}"]

    def run(self):
        rc = aja.main(self.args)
        return rc, json.loads((self.d / "o.json").read_text())


class TestJoints(unittest.TestCase):
    def test_identity_ok(self):
        rc, r = Case().run()
        self.assertEqual(rc, 0)
        self.assertTrue(r["complete"])
        (j,) = r["joints"]
        self.assertEqual(j["bits"], N)
        self.assertEqual(j["verdict"], "ok")
        self.assertTrue(j["identity"])
        self.assertFalse(j["mirrored"])
        self.assertEqual(j["a"]["source"], ["kit_plan"])
        self.assertEqual(r["summary"]["joints_gt32"], 1)

    def test_mirrored_neighbour_reversed(self):
        rc, r = Case(ob="MX").run()               # B flipped in y: its W face runs top-down along the E/W joint
        (j,) = r["joints"]
        self.assertTrue(j["mirrored"])
        self.assertTrue(j["reversed"])
        self.assertEqual(j["verdict"], "reversed")
        self.assertEqual(j["name_wired_crossings"], N * (N - 1) // 2)
        fx = j["fix"]
        self.assertEqual(fx["side"], "b")          # tie on instance count: b (non-routed, later) re-kits
        p = fx["ports"]["q"]
        self.assertTrue(p["pin_order_desc"])
        self.assertAlmostEqual(p["pin_range"][0], 1.0, places=3)
        self.assertAlmostEqual(p["pin_range"][1], 9.0, places=3)
        md = (Path(r["source"]["verilog"]).parent / "h.md").read_text()
        self.assertIn("pin_order_desc", md)

    def test_desc_kit_fixes_mirror(self):
        c = Case(ob="MX")
        s = spec("TB", "W", "q", desc=True)
        (Path(c.args[c.args.index("--kit-root") + 1]) / "physical/ref_tile/kb/spec.json").write_text(json.dumps(s))
        rc, r = c.run()
        (j,) = r["joints"]
        self.assertTrue(j["mirrored"])
        self.assertEqual(j["verdict"], "ok")

    def test_my_is_not_mirrored_across_ew_face(self):
        # MY flips x: B's master E face becomes its die W face, bits still ascend in y -> no reversal; the B bus is on
        # master W, which MY puts on the far side: pins are off the facing face -> no joint judged
        c = Case(ob="MY")
        rc, r = c.run()
        self.assertEqual(r["joints"], [])

    def test_corner_pins_of_a_side_face_are_not_a_joint(self):
        # B abuts A's E face but its bus sits on its own S face: the first pins lie within the face tolerance of the
        # joint line, yet they face south -> no joint
        rc, r = Case(b_face="S").run()
        self.assertEqual(r["joints"], [])

    def test_undefined_without_pin_balance(self):
        rc, r = Case(balance_b=False).run()
        (j,) = r["joints"]
        self.assertEqual(j["verdict"], "undefined")
        self.assertFalse(j["order_defined"])
        self.assertTrue(any("pin_balance" in x for x in j["fix"]["actions"]))
        self.assertEqual(r["summary"]["order_undefined"], 1)

    def test_routed_view_uses_lef_centres(self):
        order = list(range(32, 64)) + list(range(0, 32))     # two 32-b chunks placed swapped (PPL chunk scatter)
        rc, r = Case(lef_b_order=order, routed_b=True, balance_b=False).run()
        (j,) = r["joints"]
        self.assertEqual(j["b"]["source"], ["routed_lef"])
        self.assertTrue(j["order_defined"])
        self.assertEqual(j["verdict"], "scrambled")
        self.assertEqual(j["name_wired_crossings"], 32 * 32)
        # b's own order is chunk-scrambled: a cannot match it with a range -> b (CLOSED) re-kits with pin_balance
        self.assertEqual(j["fix"]["side"], "b")
        self.assertFalse(j["fix"]["own_order_monotonic"]["b"])
        self.assertTrue(any("re-route" in x and x.startswith("b:") for x in j["fix"]["actions"]))

    def test_gap_and_far(self):
        rc, r = Case(bx=13.0).run()               # 3 um pinless gap: still a joint
        self.assertEqual(len(r["joints"]), 1)
        rc, r = Case(bx=30.0).run()               # 20 um: a channel, not a joint
        self.assertEqual(r["joints"], [])

    def test_fail_closed_missing_place(self):
        rc, r = Case(place_b=False).run()
        self.assertEqual(rc, 3)
        self.assertFalse(r["complete"])
        self.assertIn("b", r["missing"]["no_place"])

    def test_small_bus_not_judged(self):
        v = "module top ();\n  wire [63:0] n;\n  TA a (.d(n));\n  TB b (.q({32'b0, n[31:0]}));\nendmodule\n"
        rc, r = Case(verilog=v).run()
        (j,) = r["joints"]
        self.assertEqual(j["bits"], 32)
        self.assertEqual(j["verdict"], "small")
        self.assertEqual(r["summary"]["joints_gt32"], 0)


class TestParse(unittest.TestCase):
    def test_concat_replication_constants(self):
        n = aja.Netlist("module m (input [3:0] a, output y);\n wire [1:0] w;\n"
                        " X u (.p({2{w[0]}}), .q({a[3:2], 1'b0, w}), .r(), .s(\\esc[1] ));\nendmodule\n",
                        want_masters=None)
        _, ports = n.instances["u"]
        self.assertEqual(ports["p"], [("w", 0), ("w", 0)])
        self.assertEqual(ports["q"], [("a", 3), ("a", 2), None, ("w", 1), ("w", 0)])
        self.assertEqual(ports["r"], [])
        self.assertEqual(ports["s"], [("esc[1]", None)])

    def test_xform_and_dict_order(self):
        self.assertEqual(aja.xform(1, 2, 10, 20, "R180"), (9, 18))
        self.assertEqual(aja.xform(1, 2, 10, 20, "MX"), (1, 18))
        self.assertEqual(aja.xform(1, 2, 10, 20, "R90"), (18, 1))
        names = ["d[10]", "d[2]", "d[1]"]
        self.assertEqual(sorted(names, key=aja._dict_key), ["d[1]", "d[2]", "d[10]"])


if __name__ == "__main__":
    unittest.main()
