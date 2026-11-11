#!/usr/bin/env python3
"""Per-leaf slice<->leaf transport terms, derived from the emitted leaf routes of a bound plan (never hand-written).

Input: the report of emitted_leaf_routes.py for the plan being compiled.  The DL 4 + 4 constants in lower_vpx.py,
lower_vs.py and entry_norm.py are the as-built case of these terms:
  lo send       LO_AFTER_CTL(leaf) = LO_LOCAL + dn + up   (lower_vpx.LO_AFTER_CTL at dn = up = DL; leg_program(lo_after_ctl=))
  Engram REDUCE issue offset(leaf) = max(dn + up) - (dn + up), leaves with one offset share one CTL (the mask carries them;
                the REDUCE body is the same on every leaf)
  norm NORMR    issue offset(leaf) = max(dn + up + pdsk) - (dn + up + pdsk); every NORMR needs its own CTL because its
                body differs per leaf (a1 = global beat), so two leaves on one offset cannot be issued.
"""
import json

try:
    from . import lower_vpx as _LV
    from . import xtier_land as _XT
except ImportError:
    import lower_vpx as _LV
    import xtier_land as _XT

# lower_vpx edge chain with the slice's DL + DL leaf relays removed (S81-XTIER-FIX 11-11: was a hand 7 = 15 - 4 - 4, the
# unlanded ot_s81sl_xr value; the bound xrt lands lo one more edge -> 8; DL = ot_s81sl_slice default, from the RTL)
LO_LOCAL = _LV.LO_AFTER_CTL - 2 * _XT.form()['slice_dl']


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


def report_from_offsets(offsets, top_sha256, view_sha256=None):
    """emitted_leaf_routes report from a per-plan offsets table (the dn/up/pdsk that a plan event moved, e.g.
    lanes/TYPE-SAFE-4-S81-LEAF-OFFSETS.json), bound to the emitted top it will compile against.  The derived columns of
    the table must equal what this module computes from its dn/up/pdsk, so a table from another formula is refused."""
    rows = []
    for name, s in sorted(offsets['slices'].items()):
        for leaf in range(5):
            rows.append(dict(slice=name, sid=s['sid'], leaf=leaf, xr_command_to_leaf_boundary_edges=s['dn'][leaf],
                             vn_b_partial_to_xr_input_edges=s['up'][leaf], pdsk_edges=s['pdsk'][leaf],
                             crossing_plus_pdsk_edges=s['dn'][leaf] + s['up'][leaf] + s['pdsk'][leaf]))
    report = dict(schema='opentallas.s81.emitted_leaf_boundary_routes.v1', verdict='PASS_SELECTED_BOUNDARY_WIRING',
                  source_top_sha256=top_sha256, source_view_sha256=view_sha256, leaves=rows,
                  derived_from_plan_offsets=dict(plan=offsets.get('plan'), tool=offsets.get('tool')),
                  scope='plan offsets table, not a trace of the emitted top', norm_producer_qualified=False,
                  go_readiness_qualified=False, full_token=False, added_rtl_cycles=0)
    for name, row in summary(report).items():
        for key in ('lo_after_ctl', 'eng_ctls', 'norm_issue', 'norm_clash'):
            if key in offsets['slices'][name] and json.loads(json.dumps(row[key])) != offsets['slices'][name][key]:
                raise ValueError(f'offsets table disagrees with leaf_transport on {name} {key}')
    return report


if __name__ == '__main__':
    import argparse
    import hashlib
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('routes')
    ap.add_argument('--from-offsets', action='store_true', help='routes is a per-plan offsets table; write a report to --out')
    ap.add_argument('--top', help='with --from-offsets: the emitted die top the compile will use (BoundDie die_sha is its sha256)')
    ap.add_argument('--view-sha', default=None)
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.from_offsets:
        if not (a.top and a.out):
            ap.error('--from-offsets needs --top and --out')
        with open(a.top, 'rb') as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        with open(a.routes) as f:
            rep = report_from_offsets(json.load(f), sha, a.view_sha)
        with open(a.out, 'w') as f:
            json.dump(rep, f, indent=1)
            f.write('\n')
        print(json.dumps(dict(out=a.out, source_top_sha256=sha, plan=rep['derived_from_plan_offsets']['plan'],
                              norm_blocked=[n for n, v in summary(rep).items() if v['norm_clash']])))
        raise SystemExit(0)
    t = summary(load(a.routes))
    print(json.dumps(dict(slices=t, norm_blocked=[n for n, v in t.items() if v['norm_clash']]), indent=1))
