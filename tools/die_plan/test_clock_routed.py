#!/usr/bin/env python3
"""CLOCK-128-R5 clock_routed: plan-fixed die clock as FIXED regular dbWire (unit tests, no OpenROAD)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_routed as CR  # noqa: E402

BUF = "BUFx24_ASAP7_75t_R"
CELLS = {"u1": dict(x=10.0, y=20.25), "u2": dict(x=60.0, y=20.25)}


def wire_h():
    # u1/Y -> M8 trunk at y 21.249 -> M9 drop at x 61.674 down to u2 centre y -> u2/A
    return dict(name="n1", drv="u1", loads=["u2"], horiz=True, drv_xy=[10.81, 20.385], trunk_tap=[10.81, 21.249],
                branches=[["u2", 61.674, 20.385]],
                segs=[["M8", 10.81, 21.249, 61.674, 21.249], ["M9", 61.674, 20.385, 61.674, 21.249]])


class StairTest(unittest.TestCase):
    def test_stair_reaches_pin_manhattan_min_steps(self):
        px, py = CR.pin_point(CELLS, "u2", "A", BUF)
        st = CR.stair("M9", 61.674, 20.385, px, py)
        self.assertEqual(st[0], ("M9", 61.674, 20.385))
        self.assertEqual(st[-1], ("M1", px, py))
        for (l0, x0, y0), (l1, x1, y1) in zip(st, st[1:]):
            if l0 != l1:
                self.assertEqual((x0, y0), (x1, y1))            # via: same point
                self.assertEqual(abs(CR.LAYERS.index(l0) - CR.LAYERS.index(l1)), 1)
            else:
                self.assertTrue(x0 == x1 or y0 == y1)
                ln = abs(x1 - x0) + abs(y1 - y0)
                self.assertGreaterEqual(ln + 1e-9, CR.STEP.get(l0, 0.0) if l0 not in ("M3", "M2") else 0.05 - 1e-9)
                # preferred direction only
                self.assertTrue((y0 == y1) if l0 in CR.HORIZ else (x0 == x1))

    def test_pin_access_rows_differ(self):
        a = CR.pin_point(CELLS, "u1", "A", BUF)
        y = CR.pin_point(CELLS, "u1", "Y", BUF)
        self.assertAlmostEqual(y[1] - a[1], 0.09, places=6)
        mx = dict(CELLS, u3=dict(x=0.0, y=0.27, orient="MX"))
        self.assertAlmostEqual(CR.pin_point(mx, "u3", "A", BUF)[1], 0.27 + 0.18, places=6)
        with self.assertRaises(ValueError):
            CR.pin_point(dict(u=dict(x=0, y=0)), "u", "A", "INVx1_ASAP7_75t_R")


class EmitTest(unittest.TestCase):
    def test_routed_tcl_structure(self):
        L, rec = CR.routed_tcl([wire_h()], CELLS, {}, BUF, "ot_mesh_ndr")
        txt = "\n".join(L)
        self.assertEqual(rec["nets"], 1)
        self.assertEqual(rec["pin_stairs"], 2)
        self.assertIn("addITerm [IT u1 Y]", txt)
        self.assertIn("addITerm [IT u2 A]", txt)
        self.assertIn("set jt [$e addTechVia [V VIA78]]", txt)       # junction at the trunk tap
        # driver path (default width), trunk (NDR), drop (NDR), drop split below VIA78 (default width)
        self.assertEqual(txt.count("FIXED"), 4)
        self.assertNotIn("RL M1", txt)
        self.assertIn("set jv [$e addTechVia [V VIA78]]\n$e newPath $jv FIXED\n", txt)
        self.assertNotIn(" ROUTED ", txt)
        # the only extra M8/M9 metal: the 0.2-um M8 step under the M9 drop end
        self.assertEqual(rec["extra_top"], [("n1", "M8", 61.674, 20.385, 61.474, 20.385)])

    def test_port_endpoints(self):
        w = dict(name="t", drv="u1", loads=["port:tp"], horiz=True, drv_xy=[10.81, 20.385], trunk_tap=[10.81, 21.249],
                 branches=[["port:tp", 20.0, 20.28]], segs=[["M8", 10.81, 21.249, 20.0, 21.249], ["M9", 20.0, 20.28, 20.0, 21.249]])
        L, rec = CR.routed_tcl([w], CELLS, {"tp": dict(layer="M8", xy=[19.16, 20.28])}, BUF, "x")
        self.assertIn("addBTerm [BT tp]", "\n".join(L))
        self.assertIn(("t", "M8", 20.0, 20.28, 19.16, 20.28), rec["extra_top"])


class ShieldOnlyTest(unittest.TestCase):
    def test_transform_drops_clock_sbox_keeps_shields(self):
        import die_clock_128 as C128
        nd = dict(width=0.16, space=0.08, rf=0.25, cf=1.3)
        L = C128.combo_tcl([wire_h()], nd, "VSS")
        S = CR.shield_only_tcl(L)
        fw = [s for s in S if s.startswith("proc fw ")][0]
        self.assertNotIn("dbSBox_create $sw", fw)
        self.assertEqual(fw.count("dbSBox_create $fsw"), 2)               # both shield stripes, both directions
        self.assertEqual(fw.count("lappend ::ot_clk_obs"), 2)
        self.assertIn("proc fwnet {nm} { return {} }", S)


class PlanCheckTest(unittest.TestCase):
    def _def(self, w, rec, shift=0.0, moved=False):
        # synthesize the DEF route the encoder would produce (legs + M8 step), dbu 1000
        q = lambda v: int(round(v * 1000))
        x0, y = 10.81, 21.249
        xd = 61.674 + shift
        r = (f"- n1 ( u1 Y ) ( u2 A ) + USE CLOCK + NONDEFAULTRULE ot_mesh_ndr\n"
             f"  + FIXED M8 ( {q(x0)} {q(y)} ) ( {q(xd)} * ) VIA89 ( * * )\n"
             f"  NEW M9 ( {q(xd)} {q(y)} ) ( * {q(20.385)} ) VIA89 ( * * )\n"
             f"  NEW M8 ( {q(xd)} {q(20.385)} ) ( {q(xd - 0.2)} * ) VIA78 ;\n")
        ux = 60.0 + (0.5 if moved else 0.0)
        return (f"COMPONENTS 2 ;\n- u1 BUFx24_ASAP7_75t_R + FIXED ( 10000 20250 ) N ;\n"
                f"- u2 BUFx24_ASAP7_75t_R + FIXED ( {q(ux)} 20250 ) N ;\nEND COMPONENTS\n"
                f"NETS 1 ;\n{r}END NETS\n")

    def test_equal_and_detects_moves(self):
        w = wire_h()
        _, rec = CR.routed_tcl([w], CELLS, {}, BUF, "x")
        ok = CR.plan_check(self._def(w, rec), [w], rec, CELLS)
        self.assertTrue(ok["equal"], ok)
        bad = CR.plan_check(self._def(w, rec, shift=0.08), [w], rec, CELLS)
        self.assertFalse(bad["equal"])
        self.assertEqual(bad["n_mismatch"], 1)
        mv = CR.plan_check(self._def(w, rec, moved=True), [w], rec, CELLS)
        self.assertFalse(mv["equal"])
        self.assertEqual(mv["n_moved"], 1)


class CensusTest(unittest.TestCase):
    def test_cross_net_short_found(self):
        sh = [("a", "M3", 0, 0, 0.018, 0.1), ("b", "M3", 0.01, 0.05, 0.028, 0.2), ("a", "M3", 0.0, 0.0, 0.018, 0.3)]
        c = CR.stair_census(sh)
        self.assertEqual(c["shorts"], 2)
        c2 = CR.stair_census([("a", "M3", 0, 0, 0.018, 0.1), ("b", "M3", 0.03, 0, 0.048, 0.1)])
        self.assertEqual((c2["shorts"], c2["spacing"]), (0, 1))


class SpefTest(unittest.TestCase):
    def test_spef_rc_name_map(self):
        p = Path(__file__).resolve().parent / "_t_cr.spef"
        p.write_text("*NAME_MAP\n*1 n1\n*2 u1\n\n*PORTS\n\n*D_NET *1 4.5\n*CONN\n*I *2:Y O\n*I u2:A I\n*CAP\n1 *1:1 2\n"
                     "*RES\n1 *1:1 *1:2 0.25\n2 *1:2 *1:3 0.5\n*END\n")
        try:
            rc = CR.spef_rc(p, ["n1"])
        finally:
            p.unlink()
        self.assertEqual(rc["n1"], dict(c_ff=4.5, r_kohm=0.75, conn=2))

    def test_spef_rc_units(self):
        p = Path(__file__).resolve().parent / "_t_cr2.spef"
        p.write_text("*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*D_NET n1 0.0045\n*CONN\n*I u1:Y O\n*CAP\n1 n1:1 0.002\n"
                     "*RES\n1 n1:1 n1:2 250\n2 n1:2 n1:3 500\n*END\n")
        try:
            rc = CR.spef_rc(p, ["n1"])
        finally:
            p.unlink()
        self.assertAlmostEqual(rc["n1"]["c_ff"], 4.5)
        self.assertAlmostEqual(rc["n1"]["r_kohm"], 0.75)


if __name__ == "__main__":
    unittest.main()
