"""CLOCK-128-R8: opt-in RCX stage model for hold_demand (default unchanged)"""
import hold_demand as H


def test_default_unchanged():
    H.set_stage_model("r4_native")
    assert H.STAGE == {"TT": (52.713, 0.058822), "FF": (38.561, 0.060298)}


def test_rcx_model_reproduces_r6_legs():
    try:
        H.set_stage_model("r6_rcx_ndr016")
        for c, want in (("TT", 103.16), ("FF", 85.68)):
            d0, k = H.STAGE[c]
            assert abs(d0 + k * 430.2 - want) < 0.01
        assert H.STAGE["TT"][0] == 52.713 and H.STAGE["FF"][0] == 38.561
        assert 0.0 < H.cell_share("TT") < 1.0
    finally:
        H.set_stage_model("r4_native")
