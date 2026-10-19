#!/usr/bin/env python3
"""dv_layer_slices.py -- which die slices / units bound each representative layer's cycles on the p4l DV die, and the
minimal set of slice cuts that covers every slice class per layer (LB2-S81/RUN, TOK.DS.BENCH.3, 10-18).

Inputs (all from the die of record and the compiler, nothing measured here):
  * the bind9 die.v + p4l plan + land plan (dv_layer_compile.Die): slice masters, sid straps, CTL path per slice
    (dv_layer_compile.ctl_path: seq_host vo -> tvS/tvN -> column-4 inject -> rstop 2 / stop + line link ages), the
    landed links between slices and the shared units (gunit, svc_rs chain, bk_sel / bk_col, seq_host, lk_* lanes);
  * the priced p4l op schedule per layer (dv_layer_compile.layer_schedule = dv_layer_price facts + dv_price dv_base
    deltas + accepted_cost.solve) and the compiler's op -> unit map (dv_layer_compile.op_unit).

Composition (the rule the layer record uses): the schedule is static, so every slice runs the same compiled calendar
shifted by its CTL arrival a_s; ops on a shared unit start when the latest feeding slice's beat lands there.  The
layer's cycles = max over cuts c of (the last scheduled event the bench measured on c's instances), with every cut's
neighbour traffic replayed at its scheduled cycle.  Under that rule the bounding instance for each op class is:
  slice-local (vp/vn/vq/vs/xr/xfin, frames)   the slice with the latest CTL arrival (all slices run it)
  end-slice lep (TP collectives, stage hop)   the four end slices (they own the lk_* link lanes)
  gunit / svc_rs / bk                          the shared unit, fed through its entry slices (landed links below)
  head / MTP draft                             not on the p4l die (head-die netlist missing: GAP_HEAD)

Output: JSON (--out) with per-slice facts, per-layer bounding instances per op class and the cut set with, per cut,
the instance list file (dv_slice_cut.py --insts syntax) and the layers / classes it covers.
Usage: dv_layer_slices.py --out slices.json [--die-ref origin/main] [--sets-dir DIR]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import dv_layer_compile as C  # noqa: E402

LAYERS = ['L0', 'L2', 'L14', 'L20', 'head']

# op unit (dv_layer_compile.OPMAP unit string prefix) -> op class
def op_class(unit):
    if unit.startswith('head die'):
        return 'head_die'
    if unit.startswith('end-slice lep'):
        return 'end_lep'
    if unit.startswith('gunit'):
        return 'gunit'
    if unit.startswith('svc_rs'):
        return 'svc'
    if unit.startswith('bk units'):
        return 'bk'
    if unit.startswith('frames'):
        return 'frames'
    if unit.startswith('slice'):
        return 'slice'
    return 'unmapped'


# the minimal cut set (instance sets in dv_slice_cut.py --insts syntax; the cutter grows relays / landings / reset
# stations / clock-forward cells to the die roots and the neighbours' landings)
CUTS = {
    'cut_0S': dict(insts=['u_s_0S'],
                   classes=['slice', 'frames', 'end_lep'],
                   why='lepw end slice (S tier W end): the LATEST CTL arrival of all 16 slices (56.5 edges) -> bounds '
                       'every slice-local op; owns lk_WS0/WS1 (TP collectives, stage hop). Same master as u_s_0N '
                       '(arrival 50.5, lk_WN*): 0N = this cut shifted by the static arrival difference.',
                   blocked_by=['G1', 'G3']),
    'cut_7': dict(insts=['u_s_7S', 'u_s_7N'],
                  classes=['slice', 'frames', 'end_lep', 'host_plane'],
                  why='the two E-end masters in one cut: lepe_nh u_s_7S (lk_ES*) and lepe u_s_7N (host plane: lk_EN*, '
                      'ht_7N host lane to seq_host, 59 edges); collectives run on both ends of the TP ring',
                  blocked_by=['G1', 'G3']),
    'cut_3S_ctl': dict(insts=['u_seqhost', 'u_bk_sel', 'u_s_4S', 'u_s_3S'],
                       classes=['slice', 'frames', 'ctl', 'interior'],
                       why='CTL injection path (seq_host calendar -> tvS -> bk_sel -> column-4 re-inject -> 3S) and the '
                           'interior master ot_s81sl_slice; 3S/4S are the entry slices of gunit and the svc chain '
                           '(u_s_3S -> u_gunit / u_rsv_05, u_s_4S -> u_rsv_11)',
                       blocked_by=['G1', 'G2']),
    'cut_svc': dict(insts=['u_gunit', '/u_rsv_\\d\\d/', '/u_ctrl_\\d\\d/', 'u_bk_col', 'u_phy_hbm'],
                    classes=['gunit', 'svc', 'bk'],
                    why='shared units: gunit (HC, router, top-6), the svc_rs chain with its ctrl tiles and the HBM PHY '
                        'model (attention window / scores / P.V, Engram rows), bk_col (index scan / candidate merge); '
                        'fed from the entry slices (3S, 3N, 4S, 1N) and seq_host at their scheduled cycles',
                    blocked_by=['G1']),
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--die-ref', default='origin/main')
    ap.add_argument('--die-src', default=None)
    ap.add_argument('--cache', default=None)
    ap.add_argument('--sets-dir', default=None, help='also write <cut>.txt instance sets here')
    a = ap.parse_args(argv)
    tree = C.die_tree(a.die_ref, a.die_src, a.cache)
    die = C.Die(tree)
    sl = die.slices()
    facts = {}
    for s in sorted(sl):
        p = C.ctl_path(die, s)
        lk = sorted({k for k, L in die.links.items() if any(x[0] == s for x in L['src'] + L['dst'])
                     and any(x[0].startswith('u_lk_') for x in L['src'] + L['dst'])})
        units = sorted({x[0] for k, L in die.links.items() if any(y[0] == s for y in L['src'] + L['dst'])
                        for x in L['src'] + L['dst'] if not x[0].startswith(('u_s_', 'u_f_', 'u_lk_'))})
        facts[s] = dict(master=sl[s]['master'], sid=sl[s]['sid'], ctl_arrival_edges=p['edges'], entry_port=p['entry_port'],
                        frames=len(die.frames_of(s)), edge_links=lk, unit_links=units)
    for k, v in CUTS.items():       # every cut slice carries its own frames (plan group), nothing else
        v['insts_full'] = v['insts'] + [f for i in v['insts'] if i in sl for f in die.frames_of(i)]
    latest = max(facts, key=lambda s: facts[s]['ctl_arrival_edges'])
    ends = [s for s in facts if facts[s]['master'] != 'ot_s81sl_slice']
    unit_feed = {}
    for k, L in die.links.items():
        for x in L['src']:
            for y in L['dst']:
                if x[0].startswith('u_s_') and not y[0].startswith(('u_s_', 'u_f_', 'u_lk_')):
                    unit_feed.setdefault(y[0], set()).add(x[0])
                if y[0].startswith('u_s_') and not x[0].startswith(('u_s_', 'u_f_', 'u_lk_')):
                    unit_feed.setdefault(x[0], set()).add(y[0])
    layers = {}
    for L in LAYERS:
        S = C.layer_schedule(tree, L, 'ar')
        by = {}
        for o in S['ops']:
            unit, st, _ = C.op_unit(o['op'])
            c = op_class(unit)
            b = by.setdefault(c, dict(ops=0, critical_ops=0, critical_cycles=0.0, last_end=0.0, status={}))
            b['ops'] += 1
            b['status'][st] = b['status'].get(st, 0) + 1
            if o['critical']:
                b['critical_ops'] += 1
                b['critical_cycles'] = round(b['critical_cycles'] + o['cycles'], 1)
            b['last_end'] = max(b['last_end'], o['end'])
        bound = {}
        for c in by:
            if c in ('slice', 'frames'):
                bound[c] = dict(instances=[latest], rule=f'latest CTL arrival ({facts[latest]["ctl_arrival_edges"]} edges)')
            elif c == 'end_lep':
                bound[c] = dict(instances=sorted(ends), rule='the end slices own the lk_* lanes (cross-die terms: TOKEN-XDIE-S81)')
            elif c == 'gunit':
                bound[c] = dict(instances=['u_gunit'] + sorted(unit_feed.get('u_gunit', ())), rule='shared unit + entry slices')
            elif c == 'svc':
                ent = sorted(set().union(*[unit_feed.get(u, set()) for u in unit_feed if u.startswith('u_rsv_')]))
                bound[c] = dict(instances=['u_rsv_* (16) + u_ctrl_* (16) + u_phy_hbm'] + ent, rule='svc chain + entry slices')
            elif c == 'bk':
                bound[c] = dict(instances=['u_bk_sel', 'u_bk_col'] + sorted(unit_feed.get('u_bk_col', ())), rule='bk units + entry slice')
            else:
                bound[c] = dict(instances=[], rule='not on the p4l die (head-die netlist not in the die sources): no cut possible')
        cuts = sorted({k for k, v in CUTS.items() for c in by if c in v['classes']}
                      | ({'cut_7', 'cut_3S_ctl'} if any(c in by for c in ('slice', 'end_lep')) else set()))
        layers[L] = dict(price_span=S['span'], price_crit=S['crit'], by_class=by, bounding=bound, cuts=cuts,
                         critical_class=max(by, key=lambda c: by[c]['critical_cycles']),
                         coverable_on_p4l='head_die' not in by)
    out = dict(schema='opentallas.s81_dv.layer_slices.v1', date='2026-10-18', lane='LB2-S81/RUN',
               tool='tools/s81_dv/dv_layer_slices.py', die_ref=a.die_ref,
               die_ref_sha=(tree / '.done').read_text().strip() if (tree / '.done').exists() else None,
               die_v_sha256=die.die_sha,
               composition='layer cycles = max over the cuts of the last scheduled event measured on the cut; every '
                           'slice runs the same calendar shifted by its CTL arrival; neighbour / unit traffic replayed '
                           'at its scheduled cycle (dv_slice_replay.py); TP collectives E from TOKEN-XDIE-S81',
               latest_ctl_slice=latest, end_slices=sorted(ends), slices=facts,
               unit_entry_slices={u: sorted(v) for u, v in sorted(unit_feed.items())},
               cuts=CUTS, layers=layers)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    if a.sets_dir:
        d = Path(a.sets_dir); d.mkdir(parents=True, exist_ok=True)
        for k, v in CUTS.items():
            (d / f'set_{k}.txt').write_text(f'# {k}: {v["why"]}\n' + '\n'.join(v['insts_full']) + '\n')
    for L, r in layers.items():
        print(f'{L}: span {r["price_span"]} crit-class {r["critical_class"]} cuts {",".join(r["cuts"]) or "-"}'
              f'{"" if r["coverable_on_p4l"] else " (NOT on p4l)"}')
    print(f'latest CTL slice {latest} {facts[latest]["ctl_arrival_edges"]} edges; ends {sorted(ends)}')


if __name__ == '__main__':
    main()
