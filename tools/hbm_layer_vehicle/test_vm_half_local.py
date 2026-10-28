#!/usr/bin/env python3
"""DIE-HBM-10 (COORD 10:42 default (a)): opt-in half-local VM in the HBM compiler.  Ports 0-3 / 4-7 are the two VM
halves; the k%8 port rule is kept; a far half's group is an owner-issued crossing read that arrives LX edges later; a
far read the lowering did not price (= the client using its tied request pins) refuses the record.  Default unchanged.
  PYTHONPATH=tools python3 -m pytest tools/hbm_layer_vehicle/test_vm_half_local.py"""
import subprocess
import sys
from pathlib import Path

import pytest

from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.native_profile import NativeTiming

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "results/rtl/hbm_ds_layer_tput_1018/fixtures/L00"
LX = 15


def test_native_timing_lx_contract():
    assert "xread_lx" not in NativeTiming(18, 15).as_dict()            # default views unchanged
    assert NativeTiming(18, 15, None, LX).as_dict()["xread_lx"] == LX
    for bad in (0, 65, 1.5, True):
        with pytest.raises(ValueError):
            NativeTiming(18, 15, None, bad)


def test_placement_half_rule_keeps_k_mod_8():
    base, half = LI.Placement(0), LI.Placement(0, 0, LX)
    for k in range(16):
        assert base.get(k, k % 8, "t") == half.get(k, k % 8, "t", priced=half.far(k % 8))
    assert [half.far(p) for p in range(8)] == [False] * 4 + [True] * 4
    assert len(half.xreads) == 8 and not half.unpriced and not half.conflicts
    h1 = LI.Placement(0, 1, LX)
    assert [h1.far(p) for p in range(8)] == [True] * 4 + [False] * 4
    h1.get(99, 0, "tied")                                              # far read not priced = tied pins used
    h1.get(98, 0, "w", read=False)                                     # writes are not crossing reads
    assert len(h1.unpriced) == 1 and not h1.xreads
    with pytest.raises(ValueError):
        LI.Placement(0, 2, LX)
    with pytest.raises(ValueError):
        LI.Placement(0, 0, None)


def _record23():
    records = LI.ds_dispatches_image(FIX / "images/ds_v41_1M_L00_per_die.json")
    original = LI.load_fixture(FIX)[23]
    import su_bench as SB
    return SB.pack_rec(records[23][1]), original


def _place(half=None):
    p = LI.Placement(0, half, None if half is None else LX)
    p.nxt = [33] * 8                    # record23 image rows (test_native_profile)
    return p


def _run(half, timing):
    raw, original = _record23()
    r = LI.su_record(raw, data=dict(original["vm_in"]), place=_place(half), pad_zero=True, timing=timing)
    LI.fixture_check(r, original)
    return r


@pytest.mark.skipif(not FIX.exists(), reason="DS L00 fixture not present")
def test_su_record_half_local_calendar():
    t0, t = NativeTiming(18, 15), NativeTiming(18, 15, None, LX)
    base = _run(None, t0)
    assert base["status"] == "emitted" and "half_local" not in base
    for half in (0, 1):
        r = _run(half, t)
        assert r["status"] == "emitted", r["reasons"]
        assert r["fixture"]["mismatched_words"] == 0 and r["fixture"]["checked_words"] > 0
        hl = r["half_local"]
        assert hl["crossing_reads"] > 0 and hl["late_groups"] == 0 and hl["unpriced_far_reads"] == 0
        # the same bank reads on the same ports and edges (owner-issued: no request is rerouted or remapped)
        assert r["ql"].f["vmr"] == base["ql"].f["vmr"]
        # far data lands LX later, so the record finishes no earlier and at most LX later than the default
        assert base["last_commit"] <= r["last_commit"] <= base["last_commit"] + LX
        assert r["write_port_guard"]["last_fill_write"] >= base["write_port_guard"]["last_fill_write"]


@pytest.mark.skipif(not FIX.exists(), reason="DS L00 fixture not present")
def test_half_local_fail_closed():
    raw, original = _record23()
    with pytest.raises(ValueError):                                      # Placement LX != contract LX
        LI.su_record(raw, data=dict(original["vm_in"]), place=_place(0), pad_zero=True, timing=NativeTiming(18, 15, None, 4))
    p = _place(0)
    p.get(12345, 5, "tied")                                              # an unpriced far read already happened
    r = LI.su_record(raw, data=dict(original["vm_in"]), place=p, pad_zero=True, timing=NativeTiming(18, 15, None, LX))
    assert r["status"] != "emitted" and any("unpriced far reads" in x for x in r["reasons"])


def test_cli_needs_contract_lx():
    r = subprocess.run([sys.executable, "-m", "hbm_layer_vehicle.layer_images", "--design", "ds", "--layer", "2",
                        "--native-read-return", "18", "--native-write-return", "15", "--half-local", "0",
                        "--boundary", "/nonexistent", "--out", "/tmp/_never"], capture_output=True, text=True,
                       env={"PYTHONPATH": str(ROOT / "tools"), "PATH": "/usr/bin:/bin"})
    assert r.returncode != 0 and "--native-xread-lx" in r.stderr
