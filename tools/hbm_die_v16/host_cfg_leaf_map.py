#!/usr/bin/env python3
"""HBM-B-RTL1 (10-17, plan (b) d4g): map every host configuration target of the d4f die to one of the 4 PHY-side
host leaves (ot_hbm_host_cfg_leaf) and re-index host_status (ot_hbm_status_join_fa) for the leaf composition.

Input: host_fan.json = per-bit trace of the d4f run8b contract (host_cp_ingress cfg fan-out; host_status t_ready /
t_active / t_fault drivers through the relay chains).  Output: the mapping JSON for the H-D4G lane.

Leaf rule (quadrant of a target):
  R1 instance suffix _SW/_SE/_NW/_NE (or _<q>_ctl) -> that quadrant;
  R2 SM-indexed services <name>_<SW|NW><k> (cp_svg, xc, sm, svg, vmks): plan (b) quad_of_sm, k < 4 -> W quadrant
     of that stack (SW / NW), k >= 4 -> E quadrant (SE / NE);
  R3 die-wide targets (col_su, col_idx, hc_eng): the quadrant that contains their plan (b) home block centre
     (plan_b_inner compact.P.json: col_su / col_idx home idx_op at (11808, 15299) -> SE); hc_eng is replaced in d4g by
     hce_<q> (HBM-B-RTL2), each on its own quadrant's leaf -- until then it is on SE with col_*;
  R4 status-only sources (fault bits of instances that take no configuration: ep_*, wbk_*, sucx_*, sfus_*, sfup_*)
     fan in through their quadrant's leaf too (suffix rule; COLL endpoints by plan (b) epq: S0 SW, S3 SE, N0 NW,
     N2 NE, S1 = host link SW), so host_status takes ONLY leaf outputs (+ h_fault / a_fault as today).
Every leaf output copy is equal-age (CFG_LAT 2), so every target sees the bundle 2 edges (plus its lane) later than
the ingress; all 4 ingress->leaf lanes must have the SAME relay depth (equal-age broadcast).
Status: each target keeps its own bits; leaf q carries its targets' bits in host_status order; the d4g join input
order is leaf SW, SE, NW, NE (each leaf's bits in d4f index order) -> new TGTS / bit permutation below.
"""
import argparse, json, re
QS = ('SW', 'SE', 'NW', 'NE')
# HBM-B-RTL1b 10-17 (coordinator 0ds): one hardened variant per quadrant at its EXACT widths (no tied status input, no
# spare id); the variant name / kit and the widths it was hardened at (checked against the derived NT / NF below).
VARIANT = {'SW': ('ot_hbm_host_cfg_leaf_sw', 'hdie_host_cfg_leaf_sw_r1', 18, 29),
           'SE': ('ot_hbm_host_cfg_leaf_se', 'hdie_host_cfg_leaf_se_r1', 18, 26),
           'NW': ('ot_hbm_host_cfg_leaf_nw', 'hdie_host_cfg_leaf_nw_r1', 19, 29),
           'NE': ('ot_hbm_host_cfg_leaf_ne', 'hdie_host_cfg_leaf_ne_r1', 14, 23)}


def split_ab(tq, pins_of):
    """copy A (W face) / copy B (E face): balanced sink pins, deterministic (largest first, ties by name).  Both copies
    are equal-age (CFG_LAT 2), so the die generator may move a target to the face nearer it without any cycle change."""
    a, b, na, nb = [], [], 0, 0
    for n in sorted(tq, key=lambda n: (-pins_of[n], n)):
        if na <= nb:
            a.append(n); na += pins_of[n]
        else:
            b.append(n); nb += pins_of[n]
    return sorted(a), sorted(b), na, nb
HOME_DIE_WIDE = {'col_su': 'SE', 'col_idx': 'SE', 'hc_eng': 'SE'}
EP = {'ep_S0': 'SW', 'ep_S1': 'SW', 'ep_S3': 'SE', 'ep_N0': 'NW', 'ep_N2': 'NE'}   # plan (b) epq (+ S1 = host link, W)


def quad(n):
    if n in HOME_DIE_WIDE:
        return HOME_DIE_WIDE[n], 'R3'
    if n in EP:
        return EP[n], 'R4'
    m = re.match(r'^(?:cp_svg|xc|sm|svg|vmks)_(SW|NW)(\d+)$', n)
    if m:
        k = int(m.group(2))
        return {'SW': ('SW', 'SE'), 'NW': ('NW', 'NE')}[m.group(1)][k >= 4], 'R2'
    m = re.search(r'_(SW|SE|NW|NE)(?:_ctl)?$', n)
    if m:
        return m.group(1), 'R1'
    raise SystemExit(f'no leaf rule for {n}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('fan'); ap.add_argument('--tgts', required=True, help='host_status TGTS hex (d4f instance param)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    f = json.load(open(a.fan))
    st = f['status']
    nt = len(st['t_ready']); nf = len(st['t_fault'])
    h = a.tgts.split("'h")[1]
    tg = [int(h[len(h) - 2 * (i + 1):len(h) - 2 * i], 16) for i in range(nt)]
    targets = sorted(n for n in f['cfg'] if n != 'host_status')
    stat_only = sorted({x[0] for x in st['t_fault'] + st['t_ready']} - set(targets))
    leaf = {n: quad(n) for n in targets + stat_only}
    # status bits per target
    rdy = {}; flt = {}
    for i, x in enumerate(st['t_ready']):
        rdy.setdefault(x[0], []).append(i)
    for i, x in enumerate(st['t_fault']):
        flt.setdefault(x[0], []).append(i)
    for i, x in enumerate(st['t_active']):
        assert st['t_ready'][i][0] == x[0], (i, x)
    miss = sorted(set(rdy) | set(flt) - set(targets))
    order_r = []; order_f = []; leaves = {}
    for q in QS:
        tq = [n for n in targets if leaf[n][0] == q]
        sq = [n for n in stat_only if leaf[n][0] == q]
        rq = sorted(i for n in tq + sq for i in rdy.get(n, []))
        fq = sorted(i for n in tq + sq for i in flt.get(n, []))
        order_r += rq; order_f += fq
        pins = sorted({f'{n}.{p.split("->")[1]}' for n in tq for p in f['cfg'][n]})
        pins_of = {n: len({p.split('->')[1] for p in f['cfg'][n]}) for n in tq}
        ca, cb, na, nb = split_ab(tq, pins_of)
        mod, kit, vnt, vnf = VARIANT[q]
        assert (vnt, vnf) == (len(rq), len(fq)), (q, vnt, vnf, len(rq), len(fq))
        src = lambda x: f'{x[0]}.{x[1]}[{x[2]}]'
        leaves[q] = dict(instance=f'hleaf_{q}', master=mod, kit=kit, NT=len(rq), NF=len(fq),
                         targets=tq, copy_a_W_face=ca, copy_b_E_face=cb, copy_sink_pins=[na, nb],
                         status_only_sources=sq, sink_pins=len(pins),
                         t_ready_d4f_index=rq, t_fault_d4f_index=fq,
                         t_ready_order=[[k, i, src(st['t_ready'][i])] for k, i in enumerate(rq)],
                         t_active_order=[[k, i, src(st['t_active'][i])] for k, i in enumerate(rq)],
                         t_fault_order=[[k, i, src(st['t_fault'][i])] for k, i in enumerate(fq)])
    nostat = [n for n in targets if n not in rdy and n not in flt]
    unmapped_r = sorted(set(range(nt)) - set(order_r)); unmapped_f = sorted(set(range(nf)) - set(order_f))
    new_tgts = ''.join(f'{tg[i]:02x}' for i in reversed(order_r))
    out = dict(schema='opentallas.hbm_d4g.host_cfg_leaf_map.v1', basis='d4f run8b regen contract (claude/hdie-d4f-r8b-1017)',
               rule=__doc__.split('Leaf rule')[1].split('Status:')[0].strip(), cfg_lat_edges=2, st_lat_edges=2,
               leaf_bind_note='leaf input t_ready[k] / t_active[k] / t_fault[k] = the source in *_order[k] = [k, d4f index, '
                              'instance.pin[bit]]; s_* output k = the same bit (order preserved) -> host_status input '
                              'by join_d4g perm. Every leaf input and output has a real driver / sink (no ties).',
               leaves=leaves, rules_used={n: leaf[n][1] for n in targets + stat_only},
               targets_without_status=nostat,
               status_sources_not_cfg_targets=dict(t_ready=[(i, st['t_ready'][i][0]) for i in unmapped_r],
                                                   t_fault=[(i, st['t_fault'][i][0]) for i in unmapped_f]),
               join_d4g=dict(note='host_status t_ready/t_active input k = d4f index t_ready_perm[k]; t_fault input k = d4f '
                                  'index t_fault_perm[k]; leaf-sourced bits first (SW,SE,NW,NE), then the direct sources '
                                  'listed in status_sources_not_cfg_targets in d4f order. GUARD(d4g) = 8 + 4 + lane edges.',
                             t_ready_perm=order_r + unmapped_r, t_fault_perm=order_f + unmapped_f,
                             TGTS=f"{nt*8}'h" + ''.join(f'{tg[i]:02x}' for i in reversed(order_r + unmapped_r))))
    json.dump(out, open(a.out, 'w'), indent=1)
    for q in QS:
        L = leaves[q]; print(q, 'targets', len(L['targets']), 'sink pins', L['sink_pins'], 'NT', L['NT'], 'NF', L['NF'])
    print('no status:', nostat, 'direct status:', out['status_sources_not_cfg_targets'])


if __name__ == '__main__':
    main()
