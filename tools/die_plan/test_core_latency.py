"""CORE-LAT-1: declared hard-core cycles are counted in the kit-source depth used by LATCHECK and the bind pricing."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_latency as CL  # noqa: E402
import lane_asbuilt_latency as LAL  # noqa: E402
import native_istations as NI  # noqa: E402


def typ(declare, regs=2):
    t = {"internal_stations": [{"conn": "bus:b_hw_hc0_o", "regs_um": [[0, 0]] * regs}],
         "hard_cores": [{"inst": "u_tap", "module": "m"}]}
    if declare:
        t["hard_cores"][0]["core_latency"] = {"out": {"b_hw_hc0_o": declare}}
    return t


def test_no_declaration_is_unchanged():
    assert CL.out_cycles(typ(0), "b_hw_hc0_o") == 0
    assert LAL.kit_depth(typ(0), "b_hw_hc0_o")[0] == 2
    assert NI.kit_source_depth(typ(0), "b_hw_hc0_o") == 2


def test_declared_cycles_add_to_kit_source_depth():
    t = typ(1, regs=1)                       # one station dropped, one core register declared: same depth as before
    assert LAL.kit_depth(t, "b_hw_hc0_o")[0] == 2
    assert NI.kit_source_depth(t, "b_hw_hc0_o") == 2
    assert LAL.kit_depth(typ(1, regs=2), "b_hw_hc0_o")[0] == 3   # declared but station kept: one cycle longer, LATCHECK fails
    assert CL.out_cycles(t, "other_bus") == 0


def soft(declare, regs=2):
    t = typ(0, regs)
    if declare:
        t["soft_latency"] = {"out": {"b_hw_hc0_o": declare}, "inst": "u_soft", "note": "relay inside soft logic"}
    return t


def test_soft_declaration_counts_like_core_declaration():
    assert CL.soft_out_cycles(soft(0), "b_hw_hc0_o") == 0
    assert CL.out_cycles(soft(1), "b_hw_hc0_o") == 1 and CL.out_cycles(soft(1), "other_bus") == 0
    assert LAL.kit_depth(soft(1, regs=1), "b_hw_hc0_o")[0] == LAL.kit_depth(typ(1, regs=1), "b_hw_hc0_o")[0] == 2
    assert NI.kit_source_depth(soft(1, regs=2), "b_hw_hc0_o") == 3


def test_soft_and_core_declarations_add():
    t = typ(1, regs=0); t["soft_latency"] = {"out": {"b_hw_hc0_o": 2}, "inst": "u_soft"}
    assert CL.out_cycles(t, "b_hw_hc0_o") == 3


def test_soft_latency_schema():
    import schema as S
    sch = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["soft_latency"]
    try:
        import jsonschema
    except ImportError:
        assert sch["required"] == ["out", "inst"]
        return
    jsonschema.validate({"out": {"lepk_o0": 1}, "inst": "u_bound.u_u_lep"}, sch)
    for bad in ({"out": {"lepk_o0": 0}, "inst": "u"}, {"out": {}, "inst": "u"}, {"out": {"lepk_o0": 1}}, {"out": {"x": 1}, "inst": "u", "zz": 1}):
        try:
            jsonschema.validate(bad, sch)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(bad)
