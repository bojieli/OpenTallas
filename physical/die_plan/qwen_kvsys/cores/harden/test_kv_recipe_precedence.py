"""AUTOBUILD-PIPE-4 10-31: gen_core_kit_kv recipe precedence. A matching 'prefix*' entry used to be applied AFTER
the exact core entry and override it, so qkd_hr_cdc_hi (8224-bit flop array) could not get more than the
qkd_hr_cdc_* SYNTH_MEMORY_MAX_BITS 8192 and failed yosys in KIT-WAVE event28w_c. Most specific entry wins."""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('gen_core_kit_kv', HERE / 'gen_core_kit_kv.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def test_exact_beats_wildcard_beats_default():
    recs = {"_default": {"util": 0.6, "sigmax": "M5"}, "a_*": {"util": 0.5, "x": 1}, "a_b*": {"util": 0.4},
            "a_b_c": {"util": 0.3}}
    assert G.resolve_recipe(recs, "a_b_c") == {"util": 0.3, "sigmax": "M5", "x": 1}
    assert G.resolve_recipe(recs, "a_b_d") == {"util": 0.4, "sigmax": "M5", "x": 1}
    assert G.resolve_recipe(recs, "z") == {"util": 0.6, "sigmax": "M5"}


def test_kv_recipes_cdc_hi_memory_bits():
    recs = json.load(open(HERE / "recipes_kv.json"))
    assert G.resolve_recipe(recs, "qkd_hr_cdc_hi")["synth_memory_max_bits"] >= 8224
    assert G.resolve_recipe(recs, "qkd_hr_cdc_ch")["synth_memory_max_bits"] == 8192
    assert G.resolve_recipe(recs, "qkd_hr_core_rx")["synth_memory_max_bits"] == 16384
    assert G.resolve_recipe(recs, "kv3_astk_q0")["synth_memory_max_bits"] == 32768
