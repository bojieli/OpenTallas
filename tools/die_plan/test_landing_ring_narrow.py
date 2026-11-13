"""R1-NARROW per-type metadata reaches the standard CA generator without changing K."""
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError
from test_clock_landings import A_BODY, B_BODY
from test_count_straps import strap_vehicle
from test_param_wrap_hard_ring import _hard, _params


def narrow_type(plan, value):
    plan["partition_types"]["B"].setdefault("clock", {})["landing_ring_narrow"] = value


def test_narrow_parameter_only_and_same_strap_ties():
    plan, table = strap_vehicle()
    base = Landings(plan, table).type_rtl("B", B_BODY)
    ties = CAB.strap_ties(table["count_aligned"], plan)
    narrow_type(plan, True)
    land = Landings(plan, table)
    actual = land.type_rtl("B", B_BODY)
    assert ", .NARROW(1)) u_cland_y" in actual
    assert actual.replace(", .NARROW(1)", "") == base
    assert CAB.strap_ties(table["count_aligned"], plan) == ties
    assert land.reset_placements["B"]["y"]["ring_narrow_added_cycles"] == 0
    assert "NARROW" not in land.type_rtl("A", A_BODY)


def test_explicit_zero_keeps_legacy_bytes():
    plan, table = strap_vehicle()
    base = Landings(plan, table).type_rtl("B", B_BODY)
    narrow_type(plan, False)
    assert Landings(plan, table).type_rtl("B", B_BODY) == base


@pytest.mark.parametrize("value", [-1, 2, "1"])
def test_invalid_narrow_is_rejected(value):
    plan, table = strap_vehicle()
    narrow_type(plan, value)
    with pytest.raises(LandingError, match="landing_ring_narrow"):
        Landings(plan, table).type_rtl("B", B_BODY)


def test_signed_child_cannot_be_reparameterised():
    plan, table = strap_vehicle()
    base, params = _params(Landings(plan, table).type_rtl("B", B_BODY))
    _hard(plan, base, params)
    narrow_type(plan, True)
    assert _params(Landings(plan, table).type_rtl("B", B_BODY)) == (base, params)


def test_signed_narrow_child_is_retained_without_type_flag():
    plan, table = strap_vehicle()
    base, params = _params(Landings(plan, table).type_rtl("B", B_BODY))
    params["NARROW"] = 1
    _hard(plan, base, params)
    assert _params(Landings(plan, table).type_rtl("B", B_BODY)) == (base, params)
