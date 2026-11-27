"""DIE-HEAD-13: opt-in band_ring="ff" (ring flops only FIRM, bit-major, ring logic to GPL); defaults unchanged."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_landing_plan as CP  # noqa: E402
import landing_place as LP  # noqa: E402
from schema import SCHEMA, _check  # noqa: E402
from test_landing_place_spread import _P  # noqa: E402

TCL = (HERE / "landing_placement.tcl").read_text()


def test_ff_suffix_only_when_band_has_ring_place():
    r = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i"}
    assert "ring:i}" in LP.tcl(_P({"i": dict(r)}), "t")
    assert "ring:i+ff}" in LP.tcl(_P({"i": dict(r, ring_place="ff")}), "t")
    assert "ring:i@1.8037+ff}" in LP.tcl(_P({"i": dict(r, spread=1.8037, ring_place="ff")}), "t")


def test_compose_band_ring_validation():
    with pytest.raises(ValueError):
        CP.compose(dict(), dict(), band_reserve="padded", band_ring="ff")
    with pytest.raises(ValueError):
        CP.compose(dict(), dict(), band_reserve="ring_ff", band_ring="logic")


def test_storage_band_records_ring_place_only_when_ff():
    from test_clock_landing_band_reserve import _type
    try:
        CP.BAND_RESERVE = "ring_ff"
        b = CP._storage_band(_type(), "wide_i", 63, [])
        assert "ring_place" not in b
        CP.BAND_RING = "ff"
        f = CP._storage_band(_type(), "wide_i", 63, [])
        assert f["ring_place"] == "ff"
        assert f["rect_um"] == b["rect_um"] and f["area_reserve_um2"] == b["area_reserve_um2"]
    finally:
        CP.BAND_RESERVE = "padded"; CP.BAND_RING = "all"


def test_default_tags_take_the_unchanged_path():
    # the ff branch only triggers on the +ff suffix; plain/spread ring tags keep the netlist-order first-fit path
    assert "if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]}" in TCL
    assert "proc cland_put {i rect tag {sp {}} {cur 0}}" in TCL
    assert "if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_ffkey_sorts_bit_major():
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[10\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_", "u/u_ring.s_d[2][9]$_DFFE_PP_"]
    body = proc + "set l {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + "} { lappend l [list [cland_ffkey $n] $n] }\n" \
        "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    slots_bits = [tuple(int(v) for v in re.findall(r"\[(\d+)", o)) for o in out]
    assert slots_bits == [(0, 9), (1, 9), (2, 9), (3, 9), (0, 10)]


class _PT:
    """a type whose bus i runs lsb_high and whose ft slot fx carries in_order lsb_high / out_order lsb_low."""
    def __init__(self, bands, order="lsb_high"):
        self.types = {"t": {"buses": [{"name": "i", "order": order}],
                            "ft_slots": [{"name": "fx", "in_order": "lsb_high", "out_order": "lsb_low"}],
                            "clock": {"landing_contract": {"monitor": "dataflow", "bands": bands, "pins": []}}}}


def test_lsb_high_bus_gets_reversed_ff_tag_only():
    # DIE-HEAD-32: an lsb_high bus fills its ring_place=ff band in descending bit order (+ffr); lsb_low (default) keeps +ff
    r = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i"}
    assert "ring:i@1.8037+ffr}" in LP.tcl(_PT({"i": dict(r, spread=1.8037, ring_place="ff")}), "t")
    assert "ring:i@1.8037+ff}" in LP.tcl(_PT({"i": dict(r, spread=1.8037, ring_place="ff")}, "lsb_low"), "t")
    # order only matters for flop-only placement: an "all" band stays the netlist-order tag
    assert "ring:i@1.8037}" in LP.tcl(_PT({"i": dict(r, spread=1.8037)}), "t")
    # A measured local order can override the inherited FT slot order.
    assert "ring:fx_i+ff}" in LP.tcl(_PT({"fx_i": dict(r, ring_place="ff", pinslot_order="lsb_low")}), "t")
    # ft-slot buses take in_order/out_order; an unknown bus defaults to lsb_low
    assert "ring:fx_i+ffr}" in LP.tcl(_PT({"fx_i": dict(r, ring_place="ff", instance="u_cland_fx_i")}), "t")
    assert "ring:fx_o+ff}" in LP.tcl(_PT({"fx_o": dict(r, ring_place="ff", instance="u_cland_fx_o")}), "t")
    assert "ring:q+ff}" in LP.tcl(_PT({"q": dict(r, ring_place="ff", instance="u_cland_q")}), "t")
    # the placer takes the +ffr tag down the flop-only path
    assert "if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]}" in TCL
    assert "set rev [string match {ring:*+ffr} $tag]" in TCL
    assert "[cland_ffkey [lindex $pr 0] $rev $wch $nbits $wwc $rwc $tail_groups $wcw]" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_ffkey_rev_sorts_bits_descending_slots_ascending():
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[10\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_", "u/u_ring.s_d[2][565]$_DFFE_PP_"]
    def order(rev):
        body = proc + "set l {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + \
            "} { lappend l [list [cland_ffkey $n %d] $n] }\n" % rev + \
            "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
        out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
        return [tuple(int(v) for v in re.findall(r"\[(\d+)", o)) for o in out]
    assert order(0) == [(0, 9), (1, 9), (3, 9), (0, 10), (2, 565)]
    assert order(1) == [(2, 565), (0, 10), (0, 9), (1, 9), (3, 9)]


def _keyed_order(names, rev):
    procs = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0) + \
        re.search(r"proc cland_dsel_wch \{names\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    body = procs + "set ns {" + " ".join("{" + n + "}" for n in names) + "}\nset w [cland_dsel_wch $ns]\nputs W=$w\n" \
        "set l {}\nforeach n $ns { lappend l [list [cland_ffkey $n %d $w] $n] }\n" % rev + \
        "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    return out[0], out[1:]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_chunked_read_registers_follow_their_word_bit():
    # FLOW-10 (HEAD st_str r2r 510): dch[c].u_dsel/y[i] = word bit c*WCH+i sits right after that bit's storage slots;
    # the chunk one-hot selects di[k] at the chunk centre.  Before: raw-name keys packed every y register first.
    names = [r"u/u_ring.dch\[1\].u_dsel/y\[0\]$_DFF_P_", r"u/u_ring.s_d\[1\]\[2\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/y\[1\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[1\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/di\[0\]$_DFFE_PP_", r"u/u_ring.s_d\[1\]\[1\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/y\[0\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[2\]$_DFFE_PP_",
             r"u/u_ring.s_d\[0\]\[0\]$_DFFE_PP_", r"u/u_ring.dch\[1\].u_dsel/y\[1\]$_DFF_P_",
             r"u/u_ring.s_d\[0\]\[3\]$_DFFE_PP_"]
    w, out = _keyed_order(names, 0)
    assert w == "W=2"
    short = [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in out]
    assert short == ["s_d[0][0]", "dch[0].u_dsel/y[0]",
                     "s_d[0][1]", "s_d[1][1]", "dch[0].u_dsel/di[0]", "dch[0].u_dsel/y[1]",
                     "s_d[0][2]", "s_d[1][2]", "dch[1].u_dsel/y[0]",
                     "s_d[0][3]", "dch[1].u_dsel/y[1]"]
    _, rev = _keyed_order(names, 1)
    assert [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in rev][:2] == ["s_d[0][3]", "dch[1].u_dsel/y[1]"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_band_without_chunked_registers_keeps_old_keys():
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.rp\[0\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_"]
    w, out = _keyed_order(names, 0)
    assert w == "W=0"
    old = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    body = old + "foreach n {" + " ".join("{" + n + "}" for n in names) + "} { puts [cland_ffkey $n 0] }\n"
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    assert keys == ["u/u_ring.s_d|000000009|000000003|$_DFFE_PP_", r"u/u_ring.rp\[0\]$_DFF_P_",
                    "u/u_ring.s_d|000000009|000000000|$_DFFE_PP_"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_status_bits_above_bus_width_keep_raw_key():
    # HEAD st_str d ring: word bits 512..514 (above the 512-bit d_i bus) feed the plan-sited status stage at the band's
    # low corner; they keep the raw-name key instead of following bit 514 to the band's far end (r2r 537.8)
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.dch\[8\].u_dsel/y\[2\]$_DFF_P_", r"u/u_ring.dch\[7\].u_dsel/y\[63\]$_DFF_P_"]
    body = proc + "foreach n {" + " ".join("{" + n + "}" for n in names) + "} { puts [cland_ffkey $n 0 64 512] }\n"
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    assert keys == [names[0], "u/u_ring.s_d|000000511|999999998|$_DFF_P_"]
    assert "set nbits [expr {max($nbits,$bi+1)}]" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_tail_group_read_selector_stays_on_last_payload_bit():
    # l48vd READ_CHUNK/WRITE_TAIL (opt-in tail_groups): a short last read chunk keeps its di selector at the last payload
    # bit (slot range 999999970+) instead of falling back to the raw-name key.
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    nm = r"u/u_ring.dch\[8\].u_dsel/di\[0\]$_DFFE_PP_"
    body = proc + "puts [cland_ffkey {%s} 0 64 520 0 64 0]\nputs [cland_ffkey {%s} 0 64 520 0 64 1]\n" % (nm, nm)
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    # CLAND-FFKEY-CLAMP-1123: tail_groups=0 now clamps the same selector to bit 519 in the default di slot range
    assert keys == ["u/u_ring.s_d|000000519|999999990|$_DFFE_PP_", "u/u_ring.s_d|000000519|999999970|$_DFFE_PP_"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_chunk_wire_storage_names_key_as_their_slot_and_bit():
    # KV-PLAN-2 11-09 (kv3_hgi_v3 ft27_i): storage flops named by the chunk wire dch[c].sd_c[slot*WCH+i] take the key of
    # s_d[slot][c*WCH+i] (bit-major, before that bit's read register), not a raw-name key (the START rekey then moved
    # all 4,436 of them to one block).  Mutant control: the same names with wch 0 keep the raw-name key.
    names = [r"u/u_ring.dch\[1\].u_dsel/y\[0\]$_DFF_P_", r"u/u_ring.dch\[1\].sd_c\[2\]$_DFFE_NP_",
             r"u/u_ring.dch\[0\].u_dsel/y\[1\]$_DFF_P_", r"u/u_ring.dch\[0\].sd_c\[1\]$_DFFE_NP_",
             r"u/u_ring.dch\[0\].sd_c\[3\]$_DFFE_NP_", r"u/u_ring.dch\[0\].u_dsel/y\[0\]$_DFF_P_",
             r"u/u_ring.dch\[1\].sd_c\[0\]$_DFFE_NP_", r"u/u_ring.dch\[0\].sd_c\[0\]$_DFFE_NP_",
             r"u/u_ring.dch\[0\].sd_c\[2\]$_DFFE_NP_", r"u/u_ring.dch\[1\].u_dsel/y\[1\]$_DFF_P_",
             r"u/u_ring.dch\[1\].sd_c\[1\]$_DFFE_NP_", r"u/u_ring.dch\[1\].sd_c\[3\]$_DFFE_NP_"]
    w, out = _keyed_order(names, 0)
    assert w == "W=2"
    short = [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in out]
    # bit 0 = dch0 sd_c 0 (slot 0), 2 (slot 1); bit 1 = dch0 sd_c 1, 3; bit 2 = dch1 sd_c 0, 2; bit 3 = dch1 sd_c 1, 3
    assert short == ["dch[0].sd_c[0]", "dch[0].sd_c[2]", "dch[0].u_dsel/y[0]",
                     "dch[0].sd_c[1]", "dch[0].sd_c[3]", "dch[0].u_dsel/y[1]",
                     "dch[1].sd_c[0]", "dch[1].sd_c[2]", "dch[1].u_dsel/y[0]",
                     "dch[1].sd_c[1]", "dch[1].sd_c[3]", "dch[1].u_dsel/y[1]"]
    _, rev = _keyed_order(names, 1)
    assert [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in rev][:3] == \
        ["dch[1].sd_c[1]", "dch[1].sd_c[3]", "dch[1].u_dsel/y[1]"]
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    nm = r"u/u_ring.dch\[1\].sd_c\[3\]$_DFFE_NP_"
    pad = r"u/u_ring.dch\[1\].sd_c\[1\]$_DFFE_NP_"
    body = proc + "puts [cland_ffkey {%s} 0 0]\nputs [cland_ffkey {%s} 0 2 3]\nputs [cland_ffkey {%s} 0 2 3]\n" % (nm, pad, nm)
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    # wch 0: raw key (old path); bit 3 >= nbits 3: a pad/status bit keeps the raw key; bit 2 < 3 keys as storage
    assert keys == [nm, pad, nm]
    nm2 = r"u/u_ring.dch\[1\].sd_c\[2\]$_DFFE_NP_"
    k2 = subprocess.run(["tclsh"], input=proc + "puts [cland_ffkey {%s} 0 2 3]\n" % nm2, capture_output=True, text=True,
                        check=True).stdout.split()
    assert k2 == ["u/u_ring.s_d|000000002|000000001|$_DFFE_NP_"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_wchkc_writer_storage_keyed_like_s_d():
    # CLAND-RING-LOCALITY (GEN-CLASS-1 11-12): LOCAL ring storage g_wcc.wcc[c].u_wcc/m[slot][k] keys as s_d[slot][c*16+k],
    # the chunk slot copy tcc at its chunk centre; the plain s_d form keys exactly as before
    procs = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\} \{wwc 0\} \{rwc 0\} \{tail_groups 0\} \{wcw 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0) + \
        re.search(r"proc cland_wcc_w \{names\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    p = "u_cland_y/u_ring.genblk1.g_wcc.wcc\\[%d\\].u_wcc/%s"
    names = [p % (1, "m\\[0\\]\\[3\\]$_DFFE_NP_"), p % (0, "m\\[2\\]\\[15\\]$_DFFE_NP_"), p % (1, "tcc\\[0\\]$_DFF_P_"),
             p % (0, "m\\[0\\]\\[3\\]$_DFFE_NP_")]
    body = procs + "set ns {" + " ".join("{" + n + "}" for n in names) + "}\nset w [cland_wcc_w $ns]\nputs $w\n" \
        "foreach n $ns { puts [cland_ffkey $n 0 0 64 0 0 0 $w] }\nputs [cland_ffkey {u_cland_y/u_ring.s_d\\[1\\]\\[19\\]$_DFF_N_}]\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")
    assert out[0] == "16"
    assert out[1] == "u_cland_y/u_ring.s_d|000000019|000000000|$_DFFE_NP_"
    assert out[2] == "u_cland_y/u_ring.s_d|000000015|000000002|$_DFFE_NP_"
    assert out[3] == "u_cland_y/u_ring.s_d|000000024|999999960|\\[0\\]$_DFF_P_"
    assert out[4] == "u_cland_y/u_ring.s_d|000000003|000000000|$_DFFE_NP_"
    assert out[5] == "u_cland_y/u_ring.s_d|000000019|000000001|$_DFF_N_"


def test_profile_emits_only_one_scoped_native_directive():
    guard = "u_ring.g_wreg.sl[3].ch[0].u_wen/q$_DFF_P_"
    lepk = {"rect_um": [935.28, 255.6, 1054.08, 511.2], "instance": "u_cland_lepk_i0", "ring_place": "ff"}
    profile = {"inset_um": [320, 440, 1028.16], "guard_east_um": 1062.72,
               "guard_seats_um": {guard: [1054.08, 267.57]}}
    ordinary = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_q", "ring_place": "ff"}
    baseline = _P({"lepk_i0": lepk, "q": ordinary})
    candidate = _P({"lepk_i0": dict(lepk, pinslot_profile=profile), "q": ordinary})
    for p in (baseline, candidate):
        p.types["t"]["outline_um"] = [1071.36, 1408.32]
    before = LP.tcl(baseline, "t")
    after = LP.tcl(candidate, "t")
    rows = [line for line in after.splitlines() if line.startswith("dict set ::cland_pinslot_profiles")]
    assert len(rows) == 1
    assert "{u_cland_lepk_i0}" in rows[0] and "{u_cland_q}" not in rows[0]
    assert "{" + guard + "}" in rows[0]
    assert after.replace(rows[0] + "\n", "") == before
    with pytest.raises(ValueError, match="invalid writer guard"):
        LP._pinslot_profile_tcl("t", {"bands": {"lepk_i0": dict(lepk, pinslot_profile=dict(
            profile, guard_seats_um={guard: [1054.08, 400]}))}}, candidate.types["t"])


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_actual_pin_y_checks_plan_and_native_identity_before_using_physical_rows():
    guard = "u_ring.g_wreg.sl[3].ch[0].u_wen/q$_DFF_P_"
    members = [[f"u_cland_lepk_i0/u_ring.q[{i}]$_DFF_P_", bit] for i, bit in enumerate([0, 1, 1, 2])]
    pins = [["M4", 19.9, 3.1], ["M6", 19.9, 4.1], ["M4", 19.9, 7.1]]
    profile = {"inset_um": [4, 6, 12], "guard_east_um": 18,
               "guard_seats_um": {guard: [16, 2]},
               "actual_pin_y": {"pins": pins, "members": members}}
    band = {"rect_um": [1, 1, 16, 8], "ring_place": "ff", "pinslot_profile": profile}
    c = {"bands": {"lepk_i0": band}}
    t = {"outline_um": [20, 10], "buses": [{"name": "lepk_i0", "dir": "in", "face": "E", "layers": ["M4", "M6"]}],
         "clock": {"landing_contract": c}}
    def profile_schema(schema):
        return schema["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"][
            "landing_contract"]["properties"]["bands"]["additionalProperties"]["properties"]["pinslot_profile"]
    schema = profile_schema(SCHEMA)
    errors = []
    _check(profile, schema, "$", errors)
    assert not errors
    assert schema["properties"]["actual_pin_y"] == profile_schema(
        json.loads((HERE / "die_plan.schema.json").read_text()))["properties"]["actual_pin_y"]
    declared = [{"name": f"lepk_i0[{i}]", "layer": layer, "x": x, "y": y}
                for i, (layer, x, y) in enumerate(pins)]
    LP.validate_pinslot_plan_pins("hd_lep0N", t, declared)
    with pytest.raises(ValueError, match="differs from current plan pin records"):
        LP.validate_pinslot_plan_pins("hd_lep0N", t, [dict(declared[0], y=3.2), *declared[1:]])
    with pytest.raises(ValueError, match="invalid or duplicate native member"):
        LP._actual_pin_y_manifest("hd_lep0N", "lepk_i0",
                                  dict(profile["actual_pin_y"], members=[*members[:-1], members[0]]), t, 16)
    with pytest.raises(ValueError, match="requires one existing soft FF y-slot band"):
        LP._pinslot_profile_tcl("hd_lep0N", {"bands": {"lepk_i0": dict(band, dsel_cone=True)}}, t)

    procs = "".join(re.search(rf"^proc {proc} .*?\n\}}\n", TCL, re.M | re.S).group()
                    for proc in ("cland_kbit", "cland_check_actual_pin_y", "cland_place_pinslot"))
    fixture = r"""
set ff_dbu 1000
set ff_y0 0
set ff_rh 100
set ff_blk block
proc block {method} {return {bt0 bt1 bt2}}
foreach i {0 1 2} {
 proc bt$i {method} [format {
  switch $method {
   getName {return {lepk_i0[%d]}}
   getIoType {return INPUT}
   getBPins {return bp%d}
  }
 } $i $i]
 proc bp$i {method} [format {return box%d} $i]
}
proc box0 {method} {return m4}
proc box1 {method} {return m6}
proc box2 {method} {return m4}
proc m4 {method} {return M4}
proc m6 {method} {return M6}
proc cland_pinslot_guard {args} {return {}}
proc cland_put {inst rect args} {puts [lindex $rect 1]}
set ordered {}
foreach i {0 1 2 3} bit {0 1 1 2} {
 proc ff$i {method} [format {return {u_cland_lepk_i0/u_ring.q\[%d\]$_DFF_P_}} $i]
 lappend ordered [list [format {data|%09d|0|key} $bit] ff$i]
}
set pins {0 {19900 3100} 1 {19900 4100} 2 {19900 7100}}
set profile [dict get $::cland_pinslot_profiles u_cland_lepk_i0]
"""
    generated = LP._pinslot_profile_tcl("hd_lep0N", c, t)
    command = "cland_place_pinslot $ordered {1 1 16 8} ring:lepk_i0+ff 1 $pins 0 1"
    body = procs + generated + fixture
    def run(change="", suffix=" $profile"):
        return subprocess.run(["tclsh", "/dev/stdin"], input=body + change + "\n" + command + suffix + "\n",
                              capture_output=True, text=True)
    assert run().stdout.split() == ["3.1", "4.1", "4.1", "7.1"]
    assert run(suffix=" [lrange $profile 0 3]").stdout.split() == ["3.1", "4.4", "5.7", "7.1"]
    for change, error in [
        ("dict set pins 1 {19900 4101}", "stale native BTerm"),
        ("proc box1 {method} {return m4}", "stale native BTerm"),
        ("set ordered [lreplace $ordered 1 2 [lindex $ordered 2] [lindex $ordered 1]]", "stale ordered native member"),
        ("dict unset pins 1", "incomplete native pin or key set"),
    ]:
        rejected = run(change)
        assert rejected.returncode and error in rejected.stderr
        assert not rejected.stdout
