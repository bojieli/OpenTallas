"""DIE-HEAD-84 (CTL_n vC/vD): clock.landing_ring_wreg read_chunk / write_tail -> the cas READ_CHUNK / WRITE_TAIL
parameters and the kit's local chunk placement; same cycles, so strap K and the word stream are unchanged."""
import pytest
import count_align_bind as CAB
from clock_landings import Landings, ring_write_reg
from landing_place import _local_chunk_config
from test_clock_landings import B_BODY
from test_count_straps import strap_vehicle
from test_ring_wreg import _declare_freg


def _wreg(p, **kw):
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = dict(buses=["y"], dsrep=1, freg=True,
                                                                                  write_chunk=8, **kw)


def test_rtl_parameters_and_same_k():
    p, t = strap_vehicle()
    _wreg(p)
    _declare_freg(p, t)
    base_rtl, base_k = Landings(p, t).type_rtl("B", B_BODY), CAB.strap_ties(t["count_aligned"], p)
    p2, t2 = strap_vehicle()
    _wreg(p2, read_chunk=32, write_tail=True)
    _declare_freg(p2, t2)
    rtl = Landings(p2, t2).type_rtl("B", B_BODY)
    assert ".WRITE_CHUNK(8), .WRITE_TAIL(1), .READ_CHUNK(32), .FREG(1)) u_cland_y" in rtl
    assert rtl.replace(", .WRITE_TAIL(1), .READ_CHUNK(32)", "") == base_rtl
    assert CAB.strap_ties(t2["count_aligned"], p2) == base_k


def test_placement_chunks():
    p, _ = strap_vehicle()
    _wreg(p, read_chunk=32, write_tail=True)
    assert "{write 8 read 32 tail 1}" in _local_chunk_config(p["partition_types"]["B"])
    p2, _ = strap_vehicle()
    _wreg(p2)
    assert "{write 8 read 64}" in _local_chunk_config(p2["partition_types"]["B"])


@pytest.mark.parametrize("kw", [dict(read_chunk=65), dict(read_chunk=True), dict(write_tail=1)])
def test_bad_values(kw):
    p, _ = strap_vehicle()
    _wreg(p, **kw)
    with pytest.raises(ValueError):
        ring_write_reg(p, "B", "y")
