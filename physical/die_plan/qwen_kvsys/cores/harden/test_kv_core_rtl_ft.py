"""DIE-KV-51 10-31: kv_core_rtl.load_pins drops the plan pins file island_ft ports (gen_core_kit_kv builds them)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_core_rtl as K  # noqa: E402


def test_load_pins_skips_island_ft(tmp_path):
    doc = {"pins": [{"name": "a[0]"}, {"name": "a[1]"}, {"name": "ft_ck_i_0"}, {"name": "ft_ck_o_0"}, {"name": "clk"}],
           "island_ft": {"arcs": [{"source": "ft_ck_i_0", "sink": "ft_ck_o_0", "kind": "clock"}]}}
    p = tmp_path / "pins.json"
    p.write_text(json.dumps(doc))
    assert list(K.load_pins(p)) == [("a", 0), ("a", 1), ("clk", None)]


def test_load_pins_without_island_ft_unchanged(tmp_path):
    doc = {"pins": [{"name": "ft_ck_i_0"}, {"name": "b[3]"}]}
    p = tmp_path / "pins.json"
    p.write_text(json.dumps(doc))
    assert list(K.load_pins(p)) == [("ft_ck_i_0", None), ("b", 3)]
