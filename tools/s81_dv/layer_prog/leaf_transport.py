#!/usr/bin/env python3
"""Per-leaf slice<->leaf transport terms, derived from the emitted leaf routes of a bound plan (never hand-written).

Input: the report of emitted_leaf_routes.py for the plan being compiled.  The DL 4 + 4 constants in lower_vpx.py,
lower_vs.py and entry_norm.py are the as-built case of these terms:
  lo send       LO_AFTER_CTL(leaf) = 7 + dn + up          (15 at dn = up = 4; lower_vpx.leg_program(lo_after_ctl=))
  Engram REDUCE issue offset(leaf) = max(dn + up) - (dn + up), leaves with one offset share one CTL (the mask carries them;
                the REDUCE body is the same on every leaf)
  norm NORMR    issue offset(leaf) = max(dn + up + pdsk) - (dn + up + pdsk); every NORMR needs its own CTL because its
                body differs per leaf (a1 = global beat), so two leaves on one offset cannot be issued.
"""
import json

LO_LOCAL = 7          # lower_vpx edge chain with the DL 4 + 4 relays removed


def load(path):
    with open(path) as f:
        report = json.load(f)
    if report.get('schema') != 'opentallas.s81.emitted_leaf_boundary_routes.v1' or report.get('verdict') != 'PASS_SELECTED_BOUNDARY_WIRING':
        raise ValueError('actual emitted leaf boundary routes required')
    return report


def slices(report):
    """{slice: {'sid':, 'dn':[5], 'up':[5], 'pdsk':[5]}} for the complete 16-slice, 80-leaf cohort"""
    out = {}
    for row in report['leaves']:
        s = out.setdefault(row['slice'], dict(sid=row['sid'], dn=[None] * 5, up=[None] * 5, pdsk=[None] * 5))
        k = row['leaf']
        s['dn'][k], s['up'][k], s['pdsk'][k] = (row['xr_command_to_leaf_boundary_edges'],
                                               row['vn_b_partial_to_xr_input_edges'], row['pdsk_edges'])
    if len(out) != 16 or any(None in s[f] for s in out.values() for f in ('dn', 'up', 'pdsk')):
        raise ValueError('complete 16-slice 80-leaf route cohort required')
    return out


def lo_after_ctl(s, leaf):
    return LO_LOCAL + s['dn'][leaf] + s['up'][leaf]


def _offsets(totals):
    high = max(totals)
    return [high - t for t in totals]


def eng_ctls(s):
    """Engram REDUCE CTLs: [(issue offset, leaf mask)], ascending offset; equal round trips share one CTL"""
    groups = {}
    for k, off in enumerate(_offsets([s['dn'][k] + s['up'][k] for k in range(5)])):
        groups[off] = groups.get(off, 0) | 1 << k
    return sorted(groups.items())


def norm_issue(s):
    """(NORMR issue offset per leaf, leaf groups that need one edge).  Groups must be empty for a slice to compile."""
    off = _offsets([s['dn'][k] + s['up'][k] + s['pdsk'][k] for k in range(5)])
    return off, [[k for k in range(5) if off[k] == o] for o in sorted(set(off)) if off.count(o) > 1]


def summary(report):
    """the per-plan table a compile needs, plus the slices whose norm calendar has no legal issue"""
    tab = {}
    for name, s in sorted(slices(report).items()):
        off, clash = norm_issue(s)
        tab[name] = dict(sid=s['sid'], dn=s['dn'], up=s['up'], pdsk=s['pdsk'],
                         lo_after_ctl=[lo_after_ctl(s, k) for k in range(5)], eng_ctls=eng_ctls(s),
                         norm_issue=off, norm_clash=clash)
    return tab


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('routes')
    a = ap.parse_args()
    t = summary(load(a.routes))
    print(json.dumps(dict(slices=t, norm_blocked=[n for n, v in t.items() if v['norm_clash']]), indent=1))
