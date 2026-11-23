"""CLAND-FFKEY-CLAMP-1123 (FABLE-OPEN-KV x15): a chunk-centre select key past the bus width is clamped to bit width-1
(landing_placement.tcl cland_ffkey) and the static plan census (cland_ffkey_clamp.py) finds the same groups."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
sys.path.insert(0, str(HERE))
import cland_ffkey_clamp as cfc  # noqa: E402

needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _proc(n):
    return re.search(r"^proc %s \{.*?^\}\n" % n, TCL, re.S | re.M).group(0)


def _keys(names, wch, nbits):
    body = _proc("cland_ffkey") + "set ::cland_ffkey_clamps {}\n" + \
        "foreach n {" + " ".join("{" + n + "}" for n in names) + "} { puts [cland_ffkey $n 0 %d %d] }\n" % (wch, nbits) + \
        "foreach c $::cland_ffkey_clamps { puts CLAMP=[lrange $c 0 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")
    return [o for o in out if o and not o.startswith("CLAMP=")], [o[6:] for o in out if o.startswith("CLAMP=")]


def _di(c, k=0):
    return r"u/u_ring.dch\[%d\].u_dsel/di\[%d\]$_DFF_P_" % (c, k)


@needs_tcl
def test_last_chunk_select_clamped_to_last_bit():
    names = [_di(0), _di(2), _di(2, 1), r"u/u_ring.dch\[2\].u_dsel/y\[17\]$_DFF_P_", _di(3)]
    keys, clamps = _keys(names, 64, 145)
    assert keys[0] == r"u/u_ring.s_d|000000032|999999990|$_DFF_P_"            # in-width centre: unchanged
    assert keys[1] == r"u/u_ring.s_d|000000144|999999990|$_DFF_P_"            # centre 160 >= 145 -> bit 144
    assert keys[2] == r"u/u_ring.s_d|000000144|999999991|$_DFF_P_"
    assert keys[3] == names[3] and keys[4] == names[4]                         # padding bit / all-padding chunk: raw
    assert clamps == ["160 145", "160 145"]


@needs_tcl
def test_unknown_width_and_full_chunks_unchanged():
    keys, clamps = _keys([_di(2)], 64, 0)
    assert keys == [r"u/u_ring.s_d|000000160|999999990|$_DFF_P_"] and not clamps
    keys, clamps = _keys([_di(2)], 64, 192)
    assert keys == [r"u/u_ring.s_d|000000160|999999990|$_DFF_P_"] and not clamps


@needs_tcl
@pytest.mark.parametrize("width", [1, 2, 31, 32, 33, 64, 96, 97, 144, 145, 160, 161, 1104, 1118, 1056])
def test_static_census_matches_tcl(width):
    rw = ((width + 63) // 64) * 64
    keys, clamps = _keys([_di(c) for c in range(rw // 64)], 64, width)
    tcl = sorted({int(c.split()[0]) for c in clamps})
    assert tcl == sorted(k for _, k in cfc.clamped_chunks(width))
    assert all("|%09d|" % (width - 1) in keys[c] for c, _ in cfc.clamped_chunks(width))


def test_place_ff_reports_each_clamped_group():
    i = TCL.index(" set ::cland_ffkey_clamps {}\n set ffs [lmap pr $ffs {list [cland_ffkey [lindex $pr 0]")
    j = TCL.index('puts "OT_CLAND_FFKEY_CLAMP $prefix key $ck >= width $cw -> [expr {$cw-1}]')
    assert i < j < TCL.index("set ordered [lsort -dictionary -index 0 $ffs]")


def test_census_reads_plan_bands(tmp_path):
    plan = {"partition_types": {"kv3_hroot": {
        "buses": [{"name": "i_slg", "width": 145}],
        "clock": {"landing_contract": {"pins": [{"name": "cland_fstart_in_i_kvs"}], "bands": {
            "i_slg": {"ring_place": "ff"},                                    # width from the bus
            "i_kvs": {"width": 1118, "ring_width": 1152, "ring_place": "ff"},
            "ft0_i": {"width": 128, "ring_width": 128},                       # full chunks: none
            "ft1_i": {"width": 13, "ring_width": 64}}}}}}}                    # latent (not +ff)
    rows = cfc.census(plan)
    assert [(r["band"], r["chunk"], r["key"], r["clamp_to"], r["ring_place"], r["start"]) for r in rows] == [
        ("ft1_i", 0, 32, 12, None, False), ("i_kvs", 17, 1120, 1117, "ff", True), ("i_slg", 2, 160, 144, "ff", False)]
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    out = subprocess.run([sys.executable, "-I", str(HERE / "cland_ffkey_clamp.py"), str(p)], capture_output=True,
                         text=True, check=True).stdout
    assert "3 clamped select groups (2 live ring_place=ff, 1 latent), 2 live bands, 1 live without a START pin" in out
    assert "OT_CLAND_FFKEY_CLAMP kv3_hroot.i_slg dch[2] key 160 >= width 145 -> 144" in out
