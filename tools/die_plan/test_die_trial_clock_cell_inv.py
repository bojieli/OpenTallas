"""DIE-QC-11: --clock-cell inv (opt-in).  Measured on QC trial8 (BUF-only forwarded clock): fall-rise delay grows 3.8 ps
per stage TT (652 ps at 165 stages; the low phase vanishes).  An inverter tree alternates the asymmetry stage by stage;
every tap must still see the true clock polarity (even inverter count), by construction."""
from pathlib import Path
import inspect
import re
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_link_fishbone import _P, REG, FEED
from test_die_trial_link_htree import TAPS


def _tree():
    return D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0)


def _parity_per_tap(v):
    """walk the netlist from 'root': inverter count parity at every tap port"""
    drv = {}
    for m in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", v, re.M):
        drv[m.group(4)] = (m.group(1), m.group(3))
    out = {}
    for m in re.finditer(r"assign (\S+) = (\S+);", v):
        n, k, stages = m.group(2), 0, 0
        while n != "root":
            cell, a = drv[n]
            k += cell == D.CLK_INV
            stages += 1
            n = a
        out[m.group(1)] = (k % 2, stages)
    return out


def test_default_byte_identical():
    a = D.tree_netlist(_tree(), TAPS, rep_um=250.0)
    b = D.tree_netlist(_tree(), TAPS, rep_um=250.0, clock_cell="buf")
    assert a[0] == b[0] and a[1] == b[1]
    assert D.CLK_INV not in a[0]


def test_inv_tree_even_polarity_at_every_tap():
    n = _tree()
    v, place, tap_ports, _, _ = D.tree_netlist(n, TAPS, rep_um=250.0, clock_cell="inv")
    assert D.BUF not in v                                  # every stage is an inverter
    par = _parity_per_tap(v)
    assert len(par) == len(TAPS)
    assert all(p == 0 for p, _ in par.values()), par       # true polarity at every tap
    assert any(s % 2 == 0 for _, s in par.values())        # (parity inverter only where needed)
    insts = {p[0] for p in place}
    assert all(re.search(rf"\b{i}\b", v) for i in insts)   # every cell placed


def test_flag_is_opt_in():
    assert inspect.signature(D.tree_netlist).parameters["clock_cell"].default == "buf"
    assert inspect.signature(D.clock_kit).parameters["clock_cell"].default == "buf"
    assert inspect.signature(D.write_kit).parameters["clock_cell"].default == "buf"
    assert "--clock-cell" in inspect.getsource(D.main)


def test_inv2_even_legs_true_polarity_without_tap_inverters():
    old = D.EVEN_LEGS
    try:
        D.EVEN_LEGS = True
        n = _tree()
        v, place, _, _, _ = D.tree_netlist(n, TAPS, rep_um=250.0, clock_cell="inv2")
    finally:
        D.EVEN_LEGS = old
    assert D.BUF not in v and " q" not in v                  # no tap parity inverters needed
    par = _parity_per_tap(v)
    assert all(p == 0 for p, _ in par.values()), par
    assert all(s % 2 == 0 for _, s in par.values())          # even stage count on every root->tap path
    assert all(d.get("inv_parity") == 0 for d in n.values())  # true polarity at every node


def test_even_legs_priced_in_leg_ps():
    old = D.EVEN_LEGS
    try:
        D.EVEN_LEGS = False
        one = D.leg_ps(100.0, 250.0)
        D.EVEN_LEGS = True
        two = D.leg_ps(100.0, 250.0)
        three_even = D.leg_ps(600.0, 250.0)                  # ceil(600/250) = 3 -> 4 stages
    finally:
        D.EVEN_LEGS = old
    d0 = D.STAGE_1X_TT[0]
    assert abs(two - one - d0) < 1e-6 + D.STAGE_1X_TT[2] * 100.0 * 100.0
    assert three_even > D.leg_ps(600.0, 250.0)
