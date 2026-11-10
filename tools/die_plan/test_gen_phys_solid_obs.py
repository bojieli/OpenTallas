#!/usr/bin/env python3
"""KV-PLAN-2 11-09 (COORD / ROOT-MERGE-57 scope ruling): solid staging of routed upper-layer core OBS is opt-in per die.
qwen_kvsys is on by default; S81, S81 HEAD, QC and HBM kits stage their macro LEFs byte-identical to main unless their
plan sets die.kit_solid_routed_obs."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G
import view_lef as V
from test_view_lef import lib, routed_lef


def plan(name, **kw):
    return SimpleNamespace(die=dict(name=name, period_ps=833, **kw))


class Scope(unittest.TestCase):
    def test_default_on_only_for_kv(self):
        self.assertTrue(G.solid_obs_on(plan("qwen_kvsys")))
        for d in ("s81", "s81_head", "hbm", "hbm_arch", "qwen_compute"):
            self.assertFalse(G.solid_obs_on(plan(d)), d)

    def test_plan_key_overrides_both_ways(self):
        self.assertTrue(G.solid_obs_on(plan("hbm", kit_solid_routed_obs=True)))
        self.assertFalse(G.solid_obs_on(plan("qwen_kvsys", kit_solid_routed_obs=False)))

    def test_s81_and_hbm_staged_lef_byte_identical_to_main(self):
        # the gen_phys call site: stage_kit_macros(..., solid=solid_obs_on(P) and not bump_ports)
        text = routed_lef(frag_layers=("M6", "M7"), step=1.0)
        for die, want_same in (("s81", True), ("hbm", True), ("qwen_kvsys", False)):
            with tempfile.TemporaryDirectory() as td:
                d = Path(td)
                (d / "v").mkdir()
                (d / "v" / "m.lef").write_text(text)
                (d / "v" / "m_tt.lib").write_text(lib("m"))
                kd = d / "kit"
                (kd / "macros").mkdir(parents=True)
                (kd / "macros" / "m.lef").write_text(text)
                V.stage_kit_macros(kd, [("u", "m", "v/m.lef", "v/m_tt.lib", 0, 0, "R0")], lambda p: d / p,
                                   log=lambda *_: None, solid=G.solid_obs_on(plan(die)) and True)
                self.assertEqual((kd / "macros" / "m.lef").read_text() == text, want_same, die)

    def test_call_site_uses_the_die_switch(self):
        src = Path(G.__file__).read_text()
        self.assertIn("solid=solid_obs_on(P) and not bump_ports)", src)


if __name__ == "__main__":
    unittest.main()
