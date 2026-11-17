"""gen_phys RELAY_MID_RE default matches both hierarchical and synthesis-flattened relay names (S81-TYPES-R2 11-16)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_phys


def grp(name):
    m = re.match(gen_phys.RELAY_MID_RE, name)
    return m.group(1) if m else None


def test_hierarchical_relay():
    assert grp("u_bound.u_r0.u_y_xo0_0.u.o[8]") == "u_bound.u_r0.u_y_xo0_0"


def test_flattened_relay():
    assert grp("u_bound.u_u_r0_u_y_xo0_0.u.o[8]$_DFF_PN0_") == "u_bound.u_u_r0_u_y_xo0_0"
    assert grp("u_bound.u_u_y_rt_24a_0.u.q") == "u_bound.u_u_y_rt_24a_0"


def test_non_relay_untouched():
    for n in ("u_bound.u_u_r0_u_bs1.o_x0", "u_bound.u_u_r0_xu_y_a.q", "u_y_top_no_dot"):
        assert grp(n) is None
