"""FABLE-FIX-QC-COLL 11-21: the QC (qwen_compute) default relay_mid regex RELAY_MID_RE_QC groups every register rank of a
bound ot_dp_dly / landing pad chain as one station, leaves the other QC flops alone, is makefile-safe, and is selected
below the plan / env keys; the other dies keep RELAY_MID_RE.  Names are real coll_core instances (pkit10_wall geom.tsv).
    python3 -m pytest -q tools/die_plan/test_relay_mid_qc.py"""
import os, re, shutil, subprocess, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_phys

P = "u_bound.u_d5_io_collective_u_io_"
CHAIN = [
    (P + "g_face_0_u_face_rx_data.r[0][17]$_DFF_P_", P + "g_face_0_u_face_rx_data.r[0]"),
    (P + "g_face_0_u_face_rx_data.r[3][545]$_DFF_P_", P + "g_face_0_u_face_rx_data.r[3]"),
    (P + "g_face_0_u_face_rx_data.q[545]$_DFF_P_", P + "g_face_0_u_face_rx_data.q"),
    (P + "u_collective_up_rec.r[2][0]$_DFF_P_", P + "u_collective_up_rec.r[2]"),
    (P + "u_collective_ur_rec.q[513]$_DFF_P_", P + "u_collective_ur_rec.q"),
    ("u_bound.u_lpad_rec_rx_s1_i.r[0][546]$_DFF_P_", "u_bound.u_lpad_rec_rx_s1_i.r[0]"),
    ("u_bound.u_lpad_fltv_s_i.q[24]$_DFF_P_", "u_bound.u_lpad_fltv_s_i.q"),
    ("u_bound.u_lpad_flt_s_i.q$_DFF_P_", "u_bound.u_lpad_flt_s_i.q"),            # 1-bit pad
    ("u_bound.u_r0.u_y_xo0_0.u.o[8]", "u_bound.u_r0.u_y_xo0_0"),                  # the S81 relays keep their group
    ("u_u_r0_u_y_xo0_0.u.o[8]", "u_u_r0_u_y_xo0_0"),
]
OTHER = [
    "u_bound.u_io_collective_u_io_g_face_0_u_face.g_codec.u_codec.u_ctl.q_pin[5]$_DFF_P_",
    "u_bound.u_io_collective_u_io_u_collective.u_coll.g_sxo[2].u_face/qdata[443]$_DFF_P_",
    "u_bound.u_io_collective_u_io_u_collective.u_coll.up_rec[5]$_DFF_P_",
    "u_bound.u_io_collective_u_io_g_face_0_u_face.u_tx.wd[32]$_DFF_P_",
    "u_bound.u_bin_rec_rx_s0_i/q[3]$_DFF_P_", "u_bound.u_bout_rec_tx_s2/q[440]$_DFF_P_",
    "u_bound.u_ist_rec_tx_s0_0/q[1]$_DFF_P_", "u_bound.u_cland_rec_rx_s0_i/u_ring.dch[3].sd_c[1]$_DFF_P_",
    "u_bound.u_rrl_221$_DFF_PN0_", "u_bound.u_d5_x.r_reset_meta[0]$_DFF_P_", "u_bound.u_d5_x.qv$_DFF_P_",
    "u_bound.u_io_collective_u_io_g_face_0_u_face.u_rx.r_reset_q[0]$_DFF_PN0_",
]


def grp(name, rx=None):
    m = re.match(rx or gen_phys.RELAY_MID_RE_QC, name)
    return m.group(1) if m else None


def test_qc_re_groups_each_pad_rank():
    for name, want in CHAIN:
        assert grp(name) == want, name
    # the five ranks of one d5 pad are five different stations
    ranks = {grp(P + "u_collective_up_rec.r[%d][7]$_DFF_P_" % k) for k in range(4)} | {grp(P + "u_collective_up_rec.q[7]$_DFF_P_")}
    assert len(ranks) == 5 and None not in ranks


def test_qc_re_leaves_other_flops():
    for name in OTHER:
        assert grp(name) is None, name


def test_qc_re_is_makefile_safe_and_s81_compatible():
    assert "$" not in gen_phys.RELAY_MID_RE_QC and "#" not in gen_phys.RELAY_MID_RE_QC
    for name in ("u_bound.u_r0.u_y_xo0_0.u.o[8]", "x.u_y_rt_24b_0.sk[3]", "u_u_r0_u_y_xd_1.o[0]"):
        assert grp(name) == grp(name, gen_phys.RELAY_MID_RE), name


def test_die_default_selection(monkeypatch):
    monkeypatch.delenv("OT_RELAY_MID_RE", raising=False)
    assert gen_phys._relay_mid_re({}, "coll_core", "qwen_compute") == gen_phys.RELAY_MID_RE_QC
    for die in (None, "s81", "s81_head", "qwen_kvsys", "head"):
        assert gen_phys._relay_mid_re({}, "col_h10_r0", die) == gen_phys.RELAY_MID_RE      # other dies: unchanged
    assert gen_phys._relay_mid_re({}, "coll_core") == gen_phys.RELAY_MID_RE                # old two-argument call
    b = {"relay_mid_re": "A", "relay_mid_re_types": {"coll_core": "B"}}
    assert gen_phys._relay_mid_re(b, "coll_core", "qwen_compute") == "B"
    assert gen_phys._relay_mid_re(b, "coll_ftc", "qwen_compute") == "A"
    monkeypatch.setenv("OT_RELAY_MID_RE", "E")
    assert gen_phys._relay_mid_re(b, "coll_core", "qwen_compute") == "E"


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_tcl_regexp_first_capture_matches_python():
    """relay_mid.tcl: `regexp $rm_re [string map {\\\\ {}} name] -> pfx` (Tcl ARE lookahead, same first capture)."""
    script = "set re {%s}\n" % gen_phys.RELAY_MID_RE_QC
    for name, _ in CHAIN:
        script += "if {[regexp $re {%s} -> pfx]} {puts $pfx} else {puts NONE}\n" % name
    for name in OTHER:
        script += "if {[regexp $re {%s} -> pfx]} {puts $pfx} else {puts NONE}\n" % name
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True).stdout.split("\n")
    assert out[:len(CHAIN)] == [w for _, w in CHAIN]
    assert out[len(CHAIN):len(CHAIN) + len(OTHER)] == ["NONE"] * len(OTHER)
