import unittest
from core_pg_stub import port_lines,rectangles,refresh

class CorePGTest(unittest.TestCase):
 def test_native_pair_phase_and_extent(self):
  p=rectangles(172.8,345.6)
  self.assertEqual(p['VSS'][0],[6.324,4.32,6.444,341.28])
  self.assertEqual(p['VDD'][0],[6.516,4.32,6.636,341.28])
  self.assertAlmostEqual(p['VSS'][1][0]-p['VSS'][0][0],4.32)
  self.assertEqual(len(p['VSS'])+len(p['VDD']),76)
 def test_refresh_preserves_all_functional_geometry(self):
  base='MACRO X\n  SIZE 172.8 BY 345.6 ;\n  PIN d[0]\n    PORT\n      LAYER M4 ;\n      RECT 0 1 0.084 1.024 ;\n    END\n  END d[0]\n  OBS\n    LAYER M7 ;\n    RECT 1 1 171 344 ;\n  END\nEND X\n'
  result=refresh(base)
  pg='\n'.join(port_lines(172.8,345.6))+'\n'
  self.assertEqual(result.replace(pg,''),base)
 def test_existing_pg_and_m7_views_are_not_rewritten(self):
  for layer in ['M5','M7']:
   base=f'MACRO X\n  SIZE 100 BY 100 ;\n  PIN VDD\n    PORT\n      LAYER {layer} ;\n      RECT 1 1 2 2 ;\n    END\n  END VDD\n  OBS\nEND X\n'
   with self.assertRaisesRegex(ValueError,'preserve existing'):refresh(base)
 def test_too_small_for_native_recipe_is_rejected(self):
  with self.assertRaises(ValueError):rectangles(8,100)

if __name__=='__main__':unittest.main()


def test_refresh_without_obs_inserts_before_end_macro():
    # PG-CORECONN-3 11-03: S81 H2 coll lane.lef stubs have no OBS (one-space indent); pins go before END <macro>
    base = 'MACRO L\n SIZE 172.8 BY 345.6 ;\n PIN d[0]\n  PORT\n   LAYER M4 ;\n   RECT 0 1 0.084 1.024 ;\n  END\n END d[0]\nEND L\nEND LIBRARY\n'
    out = refresh(base)
    pg = '\n'.join(port_lines(172.8, 345.6)) + '\n'
    assert out.replace(pg, '') == base and out.index(pg) == base.index('END L\n')


def test_class_b_stubs_carry_native_m5_pg():
    # PG-CORECONN-3 11-03 class B: the 5 plan stubs without PIN VDD/VSS now carry the native M5 recipe, OBS <= M5
    from pathlib import Path
    root = Path(__file__).resolve().parent
    for s in CLASS_B:
        text = (root / s).read_text()
        for net in ('VDD', 'VSS'):
            body = text.split(f'PIN {net}\n', 1)[1].split(f'END {net}\n', 1)[0]
            assert 'LAYER M5' in body and 'USE ' in body, (s, net)
        assert not ({'M6', 'M7'} & _obs_layers(text)), s


def test_signed_ln_stubs_carry_signed_view_pg():
    # PG-CORECONN-3 11-03: S81-060/061 are SIGNED (eco_m0 i2/i3, t-s81 7af661c74dd8); their stubs carry the signed
    # abstract's PIN VDD/VSS verbatim (24 M5 straps each, VSS y 4.297-108.023, VDD y 4.311-108.009), not the recipe
    from pathlib import Path
    root = Path(__file__).resolve().parent
    for s in SIGNED_LN:
        text = (root / s).read_text()
        for net, (y0, y1) in (('VSS', ('4.297', '108.023')), ('VDD', ('4.311', '108.009'))):
            body = text.split(f'PIN {net}\n', 1)[1].split(f'END {net}\n', 1)[0]
            rects = [l.split() for l in body.splitlines() if l.strip().startswith('RECT')]
            assert len(rects) == 24 and all(r[2] == y0 and r[4] == y1 for r in rects), (s, net)



CLASS_B = ["cores/eng/lef/dsdv_eng_rr_h0.lef", "cores/eng/lef/dsdv_eng_rr_h1.lef",
           "cores/legacy/lef/dsdv_eng_rr_e_clkm5_1101.lef", "h2_2249/coll_w/lane.lef", "h2_2249/coll_e/lane.lef",
           "cores/h2/ot_s81_mu72_lnland/ot_s81_mu72_lnland.lef", "cores/h2/ot_s81_mu72_lnland_nst/ot_s81_mu72_lnland_nst.lef"]
SIGNED_LN = CLASS_B[5:]
STUBS_M5 = ["cores/leaf/lef/ot_s81sl_ve_m_tpl.lef", "cores/leaf/lef/ot_s81sl_ve_s_tpl.lef",
            "cores/leaf/lef/ot_s81sl_ve_s_tpl_w1728.lef", "cores/leaf/lef/ot_s81sl_vn_a_tpl.lef",
            "cores/leaf/lef/ot_s81sl_vn_b_tpl.lef", "cores/leaf/lef/ot_s81sl_vq_tpl.lef", "cores/leaf/lef/ot_s81sl_vs_tpl.lef",
            "cores/eg/lef/ot_s81sl_eg_c.lef", "cores/svc/lef/dsdv_svc_sx_hrow_c.lef"]


def _obs_layers(text):
    import re
    o = re.search(r"(?ms)^\s*OBS\s*$(.*?)^\s*END\s*$", text)
    return set(re.findall(r"LAYER (M\d+)", o.group(1))) if o else set()


def test_m5_pg_stubs_leave_m6_open_for_core_pg_connect():
    # PDN-0006 class (kv_leaf__t1/t5 11-03): M5 PG pins under an own M6/M7 OBS cannot land on the parent M6 straps.
    from pathlib import Path
    root = Path(__file__).resolve().parent
    for s in STUBS_M5:
        text = (root / s).read_text()
        assert "LAYER M5" in text.split("PIN VSS", 1)[1].split("END VSS", 1)[0], s
        assert not ({"M6", "M7"} & _obs_layers(text)), s


def test_clip_obs_drops_only_layers_above_top():
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parent / "core_pg_stub.py"
    spec = importlib.util.spec_from_file_location("cps", p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    lef = ("MACRO x\n  PIN VSS\n    PORT\n      LAYER M5 ;\n        RECT 1 1 2 2 ;\n    END\n  END VSS\n"
           "  OBS\n    LAYER M4 ;\n      RECT 0 0 9 9 ;\n    LAYER M6 ;\n      RECT 0 0 9 9 ;\n    LAYER M7 ;\n"
           "      RECT 0 0 9 9 ;\n  END\nEND x\n")
    out = m.clip_obs(lef)
    assert _obs_layers(out) == {"M4"}
    assert "LAYER M5" in out and out.count("RECT") == 2
