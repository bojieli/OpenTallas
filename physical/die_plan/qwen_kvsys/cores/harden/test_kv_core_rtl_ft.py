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


def _bound(insts):
    from types import SimpleNamespace as NS
    net = NS(insts=insts, bits=lambda e: [e], find=lambda n: n)
    return NS(net=net, g={"n": [("u_other", "x")]}, pdir=lambda m, p: "input", path=Path("part.sv"))


def _astk():
    note = "astk_core: astk_EN__a + astk_EN__b"
    return ({"contents": [{"inst": "astk_EN__a"}, {"inst": "astk_EN__b"}]},
            {"inst": "astk_EN", "module": "kv3_astk", "note": note})


def test_analyse_composed_core_is_single_leaf():
    t, hc = _astk()
    ms, pre, mine, bits = K.analyse(_bound({"u_astk_EN": ("kv3_astk", {"a__d": "n"})}), t, hc)
    assert (ms, pre, list(mine)) == (["astk_EN"], None, ["u_astk_EN"])
    assert [b["base"] for b in bits.values()] == ["a__d"]


def test_analyse_still_refuses_missing_members():
    t, hc = _astk()
    try:
        K.analyse(_bound({"u_other": ("m", {})}), t, hc)
    except SystemExit as ex:
        assert "member leaves missing" in str(ex)
    else:
        raise AssertionError("missing members must fail")
