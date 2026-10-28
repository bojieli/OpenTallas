"""DIE-QC-8: --region-dme-early opt-in (12.3 v5.0 macro insertion-delay balancing by construction, no pads)."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


def _arrivals(dn, root, rep):
    """model arrival (ps) of every tap from the DME root: sum of leg_ps on the path + the tap leg (um, as leaf S)"""
    out, st = {}, [(root, 0.0)]
    while st:
        i, a = st.pop()
        d = dn[i]
        for t in d["taps"]:
            out[t[1]] = a + abs(t[2] - d["x"]) + abs(t[3] - d["y"])
        st += [(k, a + D.leg_ps(abs(dn[k]["x"] - d["x"]) + abs(dn[k]["y"] - d["y"]), rep)) for k in d["kids"]]
    return out


def test_early_tap_arrives_early_by_construction():
    site, taps = _c_partition()
    base, broot, _ = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    a0 = _arrivals(base, broot, 250.0)
    t = taps[0]
    e = 60.0
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early={(t[0], t[1]): e})
    a = _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(a0)                                   # every tap delivered once
    rest = [v for k, v in a.items() if k != t[1]]
    assert max(rest) - min(rest) <= 25.0                             # the other taps stay balanced
    got = sum(rest) / len(rest) - a[t[1]]
    row = st["early_taps"][0]
    assert abs(got - e) <= abs(row["miss_ps"]) + 25.0, (got, row)    # early within the reported miss + one balance band
    assert all(site.legal((d["x"], d["y"])) for d in dn if d["kids"] or d["taps"])


def test_default_and_length_mode_unchanged():
    site, taps = _c_partition()
    a, ra, sa = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    b, rb, sb = D.dme_region_tree(site, taps, delay_rep_um=250.0, early={})
    assert a == b and ra == rb and sa == sb
    c, rc, sc = D.dme_region_tree(site, taps)
    d, rd, sd = D.dme_region_tree(site, taps, early={(taps[0][0], taps[0][1]): 60.0})   # length mode ignores early
    assert c == d and rc == rd and sc == sd


def test_flag_is_opt_in():
    assert inspect.signature(D.clock_kit).parameters["region_dme_early"].default is None
    assert inspect.signature(D.write_kit).parameters["region_dme_early"].default is None
    assert "--region-dme-early" in inspect.getsource(D.main)
