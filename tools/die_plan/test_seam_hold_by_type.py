import types
import gen_phys


def _P(**sh):
    return types.SimpleNamespace(clock=dict(insertion_ps=250.0, insertion_tol_ps=40.0, seam_hold=dict(sender_ps=25, seam_ps=110, **sh)))


def test_by_type_overrides_receiver_seam_and_falls_back():
    P = _P(by_type={"hc1*": 160})
    assert gen_phys.seam_hold(P, "hc1_x")["seam_ps"] == 160.0
    assert gen_phys.hold_in_min_ps(P, "hc1_x") == 25 - 160
    assert gen_phys.hold_in_min_ps(P, "other") == 25 - 110
    assert gen_phys.hold_in_min_ps(P) == 25 - 110            # no type: die seam
    assert gen_phys.seam_hold(_P(), "hc1_x")["seam_ps"] == 110.0


def test_by_type_below_floor_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        gen_phys.seam_hold(_P(by_type={"hc1*": 5}), "hc1_x")
