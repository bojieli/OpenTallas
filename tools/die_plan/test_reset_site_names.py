#!/usr/bin/env python3
"""RELAY-SITES: reset relay names from site + depth, opt-in; absent = the old visit-order names."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import reset_tree as RT


def topo(extra=()):
    taps = [("t0", 100.0, 100.0), ("t1", 900.0, 100.0)] + list(extra)
    return RT.topology(taps, (0.0, 0.0), reach=380.0, box_out=(0, 0, 2000, 2000))


def test_default_keeps_visit_numbers():
    relays = RT.assign(topo(), 6)["relays"]
    nums = [int(m.group(1)) for r in relays for m in [re.fullmatch(r"u_rrl_(\d+)", r["name"])] if m]
    assert nums == list(range(len(relays)))


def test_site_names_are_decimal_and_unique():
    relays = RT.assign(topo(), 6, site_names=True)["relays"]
    names = [r["name"] for r in relays]
    assert len(set(names)) == len(names) and all(re.fullmatch(r"u_rrl_\d+", n) for n in names)
    for r in relays:
        assert r["q"].startswith(("rst_rl_", "rst_n_t"))


def test_added_tap_does_not_rename_relays_at_unmoved_sites():
    a = {(tuple(r["xy"]), r["depth"]): r["name"] for r in RT.assign(topo(), 8, site_names=True)["relays"]}
    b = {(tuple(r["xy"]), r["depth"]): r["name"] for r in
         RT.assign(topo([("t2", 100.0, 1500.0)]), 8, site_names=True)["relays"]}
    shared = set(a) & set(b)
    assert shared
    # visit-order names of the same two trees differ on shared sites; site names cannot, except for a same-site dup
    assert sum(a[k] == b[k] for k in shared) >= len(shared) - 1
