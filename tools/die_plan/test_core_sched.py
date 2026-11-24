"""CORE-SCHED (HEAD-WEST 11-24): plan clock.taps[kind core].schedule_ps -> core_sched.txt + OT_CORE_SCHED."""
import copy
import pytest
import gen_phys
import schema as S


class _P:
    def __init__(self, t):
        self.types = {"T": t}
        self.clock = {"insertion_ps": 450.0, "insertion_ff_ps": 380.0}


def _t(**tap):
    taps = [dict(name="u_a", xy=[1, 1], kind="core", insertion_ps=558.17), dict(name="u_b.clk", xy=[2, 2], kind="core", insertion_ps=558.17)]
    for k, v in tap.items():
        taps[0][k] = v
    return dict(hard_cores=[dict(inst="u_a"), dict(inst="u_b")], clock=dict(core_taps="early", taps=taps))


def test_absent_schedule_writes_nothing(monkeypatch):
    monkeypatch.setattr(S, "core_taps", lambda P, tn: [(f"clk_c{i}", 0.0, 0.0, tp) for i, tp in enumerate(P.types[tn]["clock"]["taps"])])
    assert gen_phys.core_tap_schedule(_P(_t()), "T") == []


def test_schedule_rows_whole_core_and_one_pin(monkeypatch):
    monkeypatch.setattr(S, "core_taps", lambda P, tn: [(f"clk_c{i}", 0.0, 0.0, tp) for i, tp in enumerate(P.types[tn]["clock"]["taps"])])
    t = _t(schedule_ps=26)
    t["clock"]["taps"][1]["schedule_ps"] = 7.5
    assert gen_phys.core_tap_schedule(_P(t), "T") == [("u_a", "*", 26.0), ("u_b", "clk", 7.5)]


def test_schedule_refuses_merged_or_unknown(monkeypatch):
    monkeypatch.setattr(S, "core_taps", lambda P, tn: [(f"clk_c{i}", 0.0, 0.0, tp) for i, tp in enumerate(P.types[tn]["clock"]["taps"])])
    t = _t(schedule_ps=5, merged_clock_ports=["a", "b"])
    with pytest.raises(ValueError, match="whole-core or one-pin"):
        gen_phys.core_tap_schedule(_P(t), "T")
    t = _t(schedule_ps=5, name="u_zz")
    with pytest.raises(ValueError, match="names no hard_cores"):
        gen_phys.core_tap_schedule(_P(t), "T")


def test_schema_accepts_and_bounds_schedule():
    item = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]["taps"]["items"]
    assert item["properties"]["schedule_ps"]["maximum"] == 150
