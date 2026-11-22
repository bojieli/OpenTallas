"""FREG-BUSES-1 (QC-SLE-R5 11-22): clock.landing_ring_wreg.freg_buses puts the FREG face register on the listed buses only."""
import pytest
from clock_landings import ring_write_reg


def _plan(**wreg):
    return {"partition_types": {"B": {"clock": {"landing_ring_wreg": dict(buses=["a", "b", "c"], dsrep=1, **wreg)}}}}


def test_freg_only_on_listed_buses():
    p = _plan(freg_buses=["b"])
    assert ring_write_reg(p, "B", "b")["freg"] is True and ring_write_reg(p, "B", "b")["depth"] == 2
    for bus in ("a", "c"):
        r = ring_write_reg(p, "B", bus)
        assert r["freg"] is False and r["depth"] == 1


def test_same_as_type_wide_freg_on_a_one_bus_type():
    one = {"partition_types": {"B": {"clock": {"landing_ring_wreg": dict(buses=["b"], dsrep=1, freg_buses=["b"])}}}}
    ref = {"partition_types": {"B": {"clock": {"landing_ring_wreg": dict(buses=["b"], dsrep=1, freg=True)}}}}
    assert ring_write_reg(one, "B", "b") == ring_write_reg(ref, "B", "b")


def test_absent_is_unchanged():
    assert ring_write_reg(_plan(), "B", "a")["freg"] is False
    assert ring_write_reg(_plan(freg=True), "B", "c")["freg"] is True


@pytest.mark.parametrize("bad", [[], ["a", "a"], ["bad name"], "a", [1]])
def test_bad_list_refused(bad):
    with pytest.raises(ValueError, match="freg_buses"):
        ring_write_reg(_plan(freg_buses=bad), "B", "a")


def test_exclusive_with_freg():
    with pytest.raises(ValueError, match="excludes freg"):
        ring_write_reg(_plan(freg_buses=["a"], freg=True), "B", "a")
