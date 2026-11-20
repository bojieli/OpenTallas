"""gen_core_kit_kv.py recipe pg_top M7 (KV-PC-PG-2330 11-19): own M5/M6/M7 PG on the die grid, pins on M7."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_kv as G  # noqa: E402


def test_pdn_pgtop_m7_text():
    t = G.PDN_PGTOP_M7
    assert "-pins {M7}" in t
    assert "-layer {M5} -width {0.12} -spacing {0.072} -pitch {4.32} -offset {2.064}" in t
    assert "-layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {1.968}" in t
    assert "-layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}" in t
    for pair in ("M5 M6", "M6 M7"):
        assert f"add_pdn_connect -grid {{top}} -layers {{{pair}}}" in t
    assert "-pins {M5}" not in G.PDN_PGTOP_M7 and "-pins {M5}" in G.PDN


def test_pc_recipes_carry_pg_top():
    recs = json.load(open(Path(G.__file__).with_name("recipes_kv.json")))
    for mod in ("qkd_kvs_pcc", "qkd_kvs_pcf", "qkd_kvs_pcc_h_head_p", "qkd_kvs_pcf_h_head_p"):
        assert G.resolve_recipe(recs, mod).get("pg_top") == "M7", mod
    assert "pg_top" not in G.resolve_recipe(recs, "kv3_pv_pair")
