"""relay_mid.tcl OT_RELAY_MID_TAIL + gen_phys relay_mid_re / relay_mid_tail selection (FABLE-FIX-KV-HG 11-18)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_phys

HERE = os.path.dirname(os.path.abspath(__file__))


def grp(name):
    m = re.match(gen_phys.RELAY_MID_RE_KV, name)
    return m.group(1) if m else None


def test_kv_re_groups_the_gather_chain():
    assert grp("u_bound.u_hst2_t2.u_reg.ti_b[1408]$_DFF_P_") == "u_bound.u_hst2_t2"
    assert grp("u_bound.u_hst3_g.u_reg.ti_b[119]$_DFF_P_") == "u_bound.u_hst3_g"
    assert grp("u_bound.u_hst12_t1.u_reg.e_b[3]$_DFF_P_") == "u_bound.u_hst12_t1"
    assert grp("u_bound.u_head2_u_ftg.u_reg.ti_b[1469]$_DFF_P_") == "u_bound.u_head2_u_ftg"
    # the S81 relays keep their group
    assert grp("u_bound.u_r0.u_y_xo0_0.u.o[8]") == "u_bound.u_r0.u_y_xo0_0"


def test_kv_re_leaves_side_chain_and_pads_soft():
    for n in ("u_bound.u_hst2_s1.u_reg.s_b[3]$_DFF_P_", "u_bound.u_lpad_i_ectl_Q_N_tN.q[190]$_DFF_P_",
              "u_bound.u_head2_u_score.u_rof.q[0]$_DFF_PN0_", "u_bound.u_hst2_g_no_dot"):
        assert grp(n) is None


def test_re_selection_order(monkeypatch):
    monkeypatch.delenv("OT_RELAY_MID_RE", raising=False)
    assert gen_phys._relay_mid_re({}, "kv3_hgi_v4") == gen_phys.RELAY_MID_RE
    assert gen_phys._relay_mid_re({"relay_mid_re": "A"}, "kv3_hgi_v4") == "A"
    b = {"relay_mid_re": "A", "relay_mid_re_types": {"kv3_hgi_v1": "B", "kv3_hg": "C"}}
    assert gen_phys._relay_mid_re(b, "kv3_hgi_v1__cl141fc26e") == "B"
    assert gen_phys._relay_mid_re(b, "kv3_hg") == "C"
    assert gen_phys._relay_mid_re(b, "kv3_hg_v1") == "A"
    assert gen_phys._relay_mid_re(b, None) == "A"
    monkeypatch.setenv("OT_RELAY_MID_RE", "E")
    assert gen_phys._relay_mid_re(b, "kv3_hgi_v1__cl141fc26e") == "E"


def test_tail_selection(monkeypatch):
    monkeypatch.delenv("OT_RELAY_MID_TAIL", raising=False)
    assert not gen_phys._relay_mid_tail({}, "kv3_hgi_v4")
    assert gen_phys._relay_mid_tail({"relay_mid_tail": True}, None)
    b = {"relay_mid_tail_types": ["kv3_hgi_v1", "kv3_hg_v1p2"]}
    assert gen_phys._relay_mid_tail(b, "kv3_hgi_v1__cl42bc8b12")
    assert gen_phys._relay_mid_tail(b, "kv3_hg_v1p2")
    assert not gen_phys._relay_mid_tail(b, "kv3_hg_v1")
    monkeypatch.setenv("OT_RELAY_MID_TAIL", "1")
    assert gen_phys._relay_mid_tail({}, "kv3_hg_v1")


def test_tcl_tail_law_is_opt_in():
    s = open(os.path.join(HERE, "relay_mid.tcl")).read()
    # the default denominator is the even split; the centroid law exists only inside the env guard
    assert "set rm_den [expr {$n + 1.0}]" in s
    i = s.index('::env(OT_RELAY_MID_TAIL) eq "1"')
    j = s.index("set rm_den [expr {double($n)}]")
    k = s.index("dict set rm_station $c [list [expr {int($ax + ($bx - $ax) * $j / $rm_den)}]")
    assert i < j < k
    assert "* $j / ($n + 1.0))}] [expr {int($ay" not in s      # no second, unguarded copy of the old law
