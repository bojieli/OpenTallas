"""MACRO-SITES-GEN-1122 (COORD, FABLE-KV-DIE): gen_core_kit_kv.py applies the static memory-macro site file at generation, before the
kit receipt; a later manual macro_sites.py run of the same file is a no-op."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path[:0] = [str(HERE), str(REPO / "tools/die_plan")]
import gen_core_kit_kv as G  # noqa: E402

SITES_DIR = REPO / "physical/die_plan/qwen_kvsys/cores/macro_sites"
CFG = "export DIE_AREA = 0 0 380.16 190.08\nexport CORE_AREA = 4.32 4.32 375.84 185.76\nexport MACRO_PLACE_HALO = 4.32 4.32\n"
RECTS = [[268.11, 43.2, 269.73, 43.47], [107.46, 138.24, 110.7, 138.51]]


def test_site_file_follows_module_and_outline(tmp_path):
    assert G.static_sites_file({}, "kv3_pv_pair", "kv3_pv_pair__380.16x190.08") == SITES_DIR / "kv3_pv_pair.json"
    assert G.static_sites_file({}, "qkd_ectlk_q0", "qkd_ectlk_q0__216x172.8") == SITES_DIR / "qkd_ectlk_q0.json"
    assert G.static_sites_file({}, "qkd_ectlk_q0", "qkd_ectlk_q0__216x180") is None          # another outline: never applied
    assert G.static_sites_file({}, "qkd_nosuch", "qkd_nosuch__10x10") is None
    assert G.static_sites_file({"macro_sites": False}, "kv3_pv_pair", "kv3_pv_pair__380.16x190.08") is None
    own = tmp_path / "x.json"
    own.write_text(json.dumps({"core": "m__1x1", "sites": {}}))
    assert G.static_sites_file({"macro_sites": str(own)}, "m", "m__9x9") == own
    with pytest.raises(SystemExit):
        G.static_sites_file({"macro_sites": str(tmp_path / "missing.json")}, "m", "m__1x1")


def test_apply_at_gen_then_manual_rerun_is_a_noop(tmp_path):
    kd = tmp_path / "kv3_pv_pair__380.16x190.08"
    (kd / "macros").mkdir(parents=True)
    (kd / "macros" / "ot_sram_1r1w_32x128_m1.lef").write_text("MACRO ot_sram_1r1w_32x128_m1\n  SIZE 51.408 BY 20.79 ;\nEND\n")
    (kd / "config.mk").write_text(CFG)
    (kd / "island_ft.json").write_text(json.dumps(dict(arcs=[dict(source=f"ft_{k}", rect_um=r) for k, r in enumerate(RECTS)])))
    MS = G.kv_macro_sites()
    assert MS.apply(SITES_DIR / "kv3_pv_pair.json", kd)
    cfg, tcl = (kd / "config.mk").read_text(), (kd / "macro_place.tcl").read_text()
    h = G.kit_hash(kd)
    assert MS.apply(SITES_DIR / "kv3_pv_pair.json", kd) == []                                 # the old post-gen step: no change
    assert (kd / "config.mk").read_text() == cfg and (kd / "macro_place.tcl").read_text() == tcl and G.kit_hash(kd) == h
    (kd / "macro_place.tcl").write_text("# hand placement\n")                                    # a different placement still refuses
    with pytest.raises(SystemExit):
        MS.apply(SITES_DIR / "kv3_pv_pair.json", kd)


def test_gen_applies_sites_before_the_receipt():
    src = (HERE / "gen_core_kit_kv.py").read_text()
    i_cfg = src.index('(kd / "config.mk").write_text("\\n".join(cfg) + "\\n")')
    i_sites = src.index("kv_macro_sites().apply(sites, kd)")
    i_freeze = src.index("kit_hash=kit_hash(kd))")
    i_prov = src.index("LEC.write_kit_provenance(kd, REPO")
    assert i_cfg < i_sites < i_freeze < i_prov
