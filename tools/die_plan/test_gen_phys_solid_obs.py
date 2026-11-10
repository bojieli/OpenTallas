#!/usr/bin/env python3
"""KV-PLAN-2 11-09 GRT-CORE-SHADOW (kv3_hgi_v3 GRT-0116; COORD / ROOT-MERGE-57 scope ruling).

A hard core whose upper-layer OBS is its own routing fragments gets zero GRT capacity on those layers over its outline
(grt_core_shadow.tcl, sourced from the kit's grt_pre.tcl).  The LEF is never changed (the die PDN reaches the core's M5
PG stripes through the M6/M7 gaps).  Opt-in per die: qwen_kvsys by default, plan key die.kit_solid_routed_obs; S81,
S81 HEAD, QC and HBM kits stay byte-identical to main."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G
import view_lef as V

GRT_PRE = "set gp_dir [file dirname [file normalize [info script]]]\nsource [file join $gp_dir vclk_corner.tcl]\n"


def pin(n, layer="M3", use="SIGNAL", rect="0 0 0.1 0.1"):
    return (f"  PIN {n}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n      LAYER {layer} ;\n        RECT {rect} ;\n"
            f"    END\n  END {n}\n")


def routed_lef(m="m", frag_layers=("M6",), step=1.0, pg_layer="M5"):
    """10x10 macro: M1-M5 solid, signal pins on M3, PG stripe on pg_layer, one short wire per step cell on frag_layers"""
    obs = "".join(f"    LAYER M{i} ;\n     RECT  0 0 10 10 ;\n" for i in range(1, 6))
    for L in ("M6", "M7"):
        if L in frag_layers:
            obs += f"    LAYER {L} ;\n" + "".join(
                f"     RECT  {x + 0.1:.3f} {y + 0.1:.3f} {x + 0.4:.3f} {y + 0.132:.3f} ;\n"
                for x in [i * step for i in range(int(10 / step))] for y in [j * step for j in range(int(10 / step))])
        else:
            obs += f"    LAYER {L} ;\n     RECT  1 1 1.2 1.032 ;\n"
    pins = pin("a") + pin("VSS", layer=pg_layer, use="GROUND", rect="4 0.5 4.12 9.5")
    return f"VERSION 5.8 ;\nMACRO {m}\n  CLASS BLOCK ;\n  SIZE 10 BY 10 ;\n{pins}  OBS\n{obs}  END\nEND {m}\nEND LIBRARY\n"


def plan(name, **kw):
    return SimpleNamespace(die=dict(name=name, period_ps=833, **kw))


class RoutedLayers(unittest.TestCase):
    def test_fragment_layers_above_pins_listed(self):
        cov, size = V.routed_obs_layers(routed_lef(frag_layers=("M6", "M7")), "m", grid=1.0)
        self.assertEqual(set(cov), {"M6", "M7"})
        self.assertEqual(size, (10.0, 10.0))

    def test_sparse_solid_and_pin_layers_not_listed(self):
        self.assertEqual(V.routed_obs_layers(routed_lef(frag_layers=("M6",), step=2.0), "m", grid=1.0)[0], {})
        # PG pins count as pin layers: a PG stripe on M6 keeps M6 (and below) out
        self.assertEqual(set(V.routed_obs_layers(routed_lef(frag_layers=("M6", "M7"), pg_layer="M6"), "m",
                                                 grid=1.0)[0]), {"M7"})
        self.assertEqual(V.routed_obs_layers(routed_lef(frag_layers=()), "m")[0], {})   # M1-M5 solid, M6/M7 sparse


class Shadow(unittest.TestCase):
    def kit(self, td, text):
        kd = Path(td) / "kit"
        (kd / "macros").mkdir(parents=True)
        (kd / "macros" / "m.lef").write_text(text)
        (kd / "grt_pre.tcl").write_text(GRT_PRE)
        return kd

    def macros(self, o="R0"):
        return [("u_bound.u_c0", "m", "views/m.lef", "views/m_tt.lib", 100.0, 200.0, o)]

    def test_kv_kit_gets_shadow_and_lef_unchanged(self):
        text = routed_lef(frag_layers=("M6", "M7"))
        with tempfile.TemporaryDirectory() as td:
            kd = self.kit(td, text)
            self.assertTrue(G.stage_core_shadow(plan("qwen_kvsys"), kd, self.macros(), {}, []))
            sh = (kd / "grt_core_shadow.tcl").read_text()
            self.assertIn("set_global_routing_region_adjustment {100.0000 200.0000 110.0000 210.0000} -layer M6 "
                          "-adjustment 1.0", sh)
            self.assertIn("-layer M7 -adjustment 1.0", sh)
            self.assertIn("source [file join $gp_dir grt_core_shadow.tcl]", (kd / "grt_pre.tcl").read_text())
            self.assertEqual((kd / "macros" / "m.lef").read_text(), text)     # the LEF (PDN, DRT view) is untouched

    def test_s81_head_qc_hbm_kits_byte_identical_to_main(self):
        text = routed_lef(frag_layers=("M6", "M7"))
        for die in ("s81", "s81_head", "qwen_compute", "hbm", "hbm_arch"):
            with tempfile.TemporaryDirectory() as td:
                kd = self.kit(td, text)
                self.assertFalse(G.stage_core_shadow(plan(die), kd, self.macros(), {}, []), die)
                self.assertEqual(sorted(p.name for p in kd.iterdir()), ["grt_pre.tcl", "macros"], die)
                self.assertEqual((kd / "grt_pre.tcl").read_text(), GRT_PRE, die)
                self.assertEqual((kd / "macros" / "m.lef").read_text(), text, die)

    def test_plan_key_overrides_and_bump_kits_excluded(self):
        text = routed_lef(frag_layers=("M6",))
        with tempfile.TemporaryDirectory() as td:
            self.assertTrue(G.stage_core_shadow(plan("hbm", kit_solid_routed_obs=True), self.kit(td, text),
                                                self.macros(), {}, []))
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(G.stage_core_shadow(plan("qwen_kvsys", kit_solid_routed_obs=False), self.kit(td, text),
                                                 self.macros(), {}, []))
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(G.stage_core_shadow(plan("qwen_kvsys"), self.kit(td, text), self.macros(), {}, ["b"]))

    def test_clean_core_and_rotation(self):
        with tempfile.TemporaryDirectory() as td:
            kd = self.kit(td, routed_lef(frag_layers=()))
            self.assertFalse(G.stage_core_shadow(plan("qwen_kvsys"), kd, self.macros(), {}, []))
            self.assertEqual((kd / "grt_pre.tcl").read_text(), GRT_PRE)
        t = G.core_shadow_tcl([("u", "m.lef", 0.0, 0.0, "R90")],
                              lambda n: (routed_lef(frag_layers=("M6",)).replace("SIZE 10 BY 10", "SIZE 10 BY 4"), "m"))
        self.assertIn("{0.0000 0.0000 4.0000 10.0000} -layer M6", t)

    def test_macro_moves_win(self):
        with tempfile.TemporaryDirectory() as td:
            kd = self.kit(td, routed_lef(frag_layers=("M6",)))
            G.stage_core_shadow(plan("qwen_kvsys"), kd, self.macros(),
                                {"u_bound.u_c0": dict(x=5.0, y=6.0, orient="R0")}, [])
            self.assertIn("{5.0000 6.0000 15.0000 16.0000}", (kd / "grt_core_shadow.tcl").read_text())


class Scope(unittest.TestCase):
    def test_default_on_only_for_kv(self):
        self.assertTrue(G.solid_obs_on(plan("qwen_kvsys")))
        for d in ("s81", "s81_head", "hbm", "hbm_arch", "qwen_compute"):
            self.assertFalse(G.solid_obs_on(plan(d)), d)

    def test_gen_calls_the_stage(self):
        self.assertIn("stage_core_shadow(P, kd, macros, macro_moves, bump_ports)", Path(G.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
