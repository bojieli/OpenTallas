#!/usr/bin/env python3
"""HBM-CORES-REBAL-9 x DIE-HBM-10: the lane build opt-in (NativeTiming mlat / wcopy) composes with the half-local VM
opt-in (xread_lx).  WCOPY moves every bank commit +1 (near fills and far-half crossing arrivals) but not the
write-port pins, so the write-port guard edge is unchanged; defaults stay byte-identical.
  PYTHONPATH=tools python3 -m pytest tools/hbm_layer_vehicle/test_lane_build_compose.py"""
import pytest

from hbm_layer_vehicle.native_profile import NativeTiming
from hbm_layer_vehicle import test_vm_half_local as H


def test_as_dict_defaults_and_fields():
    d0 = NativeTiming(18, 15).as_dict()
    assert not {"mlat", "wcopy", "xread_lx"} & set(d0)
    d = NativeTiming(18, 15, None, H.LX, 5, 1).as_dict()
    assert (d["xread_lx"], d["mlat"], d["wcopy"]) == (H.LX, 5, 1)
    assert d["fill_commit"] == d0["fill_commit"] + 1
    for bad in ((6, 0), (4, 2)):
        with pytest.raises(ValueError):
            NativeTiming(18, 15, None, None, *bad)


@pytest.mark.skipif(not H.FIX.exists(), reason="DS L00 fixture not present")
def test_half_local_with_lane_build():
    for half in (None, 0, 1):
        lx = None if half is None else H.LX
        a = H._run(half, NativeTiming(18, 15, None, lx))
        b = H._run(half, NativeTiming(18, 15, None, lx, 5, 1))
        assert b["status"] == "emitted", b["reasons"]
        assert b["fixture"]["mismatched_words"] == 0 and b["fixture"]["checked_words"] > 0
        # write-port pins unchanged by WCOPY (near and far fills alike)
        assert b["write_port_guard"]["last_fill_write"] == a["write_port_guard"]["last_fill_write"]
        assert b["last_commit"] > a["last_commit"]                       # MLAT 5 / WCOPY 1 cost latency
        if half is not None:
            assert b["half_local"]["late_groups"] == 0 and b["half_local"]["unpriced_far_reads"] == 0
