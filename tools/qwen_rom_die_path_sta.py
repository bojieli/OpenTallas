#!/usr/bin/env python3
"""Qwen3-8B ROM die: routed-path stage audit of every die-level net (the die-level path STA).

The die is a symmetric array of closed elements whose boundaries are registered (closure kit: register at every macro
boundary), so every die-level net is a register-to-register hop whose only timing content is its wire.  The wire
stage is a measured component: tools/qwen_corridor_gate.py routed a 430.56 um registered span with the r2 repeater
density and closed it at SS 60 ps setup (+11.9 ps) and FF 25 ps hold (results/rtl/qwen_corridor_gate_20261003,
D_tile_r2), while 504 um spans miss SS by 29-79 ps.  This tool takes the die's global-route wire length of every
bundled net (OpenROAD `report_wire_length -global_route`, k-bundled GRT case) and states, per hop and per pipelined
path, the registered stages that length needs at the measured closing pitch, against the stage counts the
floorplan bound (wire_bound_8k: rectilinear centre distance) already prices.  A hop that has no pipeline stage in
the RTL (element port to element port) passes only if its routed length is within one measured stage.

This is a composition of measured components (element closures + the measured stage), not a flat die OpenSTA run;
the flat die netlist with every element's cells is not built.

    python3 tools/qwen_rom_die_path_sta.py --wirelength W/wirelength.csv --out rec.json <qwen_rom_fulldie_b3r2 plan args>
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie_b3r2 as B   # noqa: E402

PITCH_UM = 430.56          # corridor gate D_tile_r2: SS60 +11.9 ps, FF25 met
MISS_UM = 504.0            # corridor gate A spans: SS -29..-79 ps
# classes whose hops carry pipeline stations in the floorplan/RTL (stage count follows length); every other class is
# an element-port-to-element-port hop that must fit one stage
PIPELINED = {'corridor', 'head_chain', 'tree_block', 'tree_spine', 'link_spine', 'link_channel', 'clock_trunk', 'io'}


def wirelength(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if len(f) >= 3 and f[0] == 'grt:':
            out[f[1]] = float(f[2])
    return out


def audit(v, m, wl):
    by = {i.name: i for i in m['insts']}
    per_bus = {}
    for bid, cl, bits, eps in m['buses']:
        ls = [um for n, um in wl.items() if n.split('[')[0] == f'n_{bid}']
        if not ls:
            continue
        (a, _), (b, _) = eps[0], eps[1]
        man = abs(by[a].cx - by[b].cx) + abs(by[a].cy - by[b].cy) if a in by and b in by else None
        per_bus[bid] = dict(cls=cl, bits=bits, routed_max_um=max(ls), routed_mean_um=sum(ls) / len(ls), nets=len(ls),
                            centre_manhattan_um=man)
    return per_bus


def _index(wl):
    idx = {}
    for n, um in wl.items():
        base = n.split('[')[0]
        e = idx.get(base)
        idx[base] = um if e is None else max(e, um)
    return idx


SS_PS_PER_UM = 1.135      # W15 SS routed repeated span slope (tools/uarch_model.py SS_REACH_UM basis)
STAGE_SLACK_PS = 11.9      # corridor gate D_tile_r2 at 430.56 um


def skew_pitch(skew_ps):
    """the longest registered span that still closes SS setup when the two stage flops see `skew_ps` of adverse
    clock skew beyond the measured vehicle's own tree: the measured 430.56 um span's +11.9 ps, less the skew, at the
    measured SS slope of a repeated span"""
    return PITCH_UM + min(0.0, STAGE_SLACK_PS - skew_ps) / SS_PS_PER_UM


def record(v, m, wl_path, pitch=None):
    global PITCH_UM
    if pitch:
        PITCH_UM = pitch
    wl = wirelength(wl_path)
    mx = _index(wl)
    by = {i.name: i for i in m['insts']}
    L = lambda bid: mx.get(f'n_{bid}')          # noqa: E731
    cen = lambda a, b: abs(by[a].cx - by[b].cx) + abs(by[a].cy - by[b].cy)   # noqa: E731
    st = lambda um: math.ceil(um / PITCH_UM)     # noqa: E731
    bus = {bid: (cl, bits, eps) for bid, cl, bits, eps in m['buses']}
    # ---- block words: root -> slab (-> band primary via pfrag) -> tree top (pword)
    prim, frag = {}, {}
    for bid, (cl, bits, eps) in bus.items():
        if bid.startswith('pword_'):
            prim[eps[0][0]] = bid
        if bid.startswith('pfrag_'):
            frag[eps[0][0]] = bid
    words = []
    for bid, (cl, bits, eps) in bus.items():
        if not bid.startswith('bword_'):
            continue
        root, slab = eps[0][0], eps[1][0]
        legs = [bid]
        geo = [cen(root, slab)]
        if slab in frag:
            legs.append(frag[slab])
            nxt = bus[frag[slab]][2][1][0]
            geo.append(cen(slab, nxt))
            slab = nxt
        legs.append(prim[slab])
        geo.append(cen(slab, bus[prim[slab]][2][1][0]))
        routed = [L(x) for x in legs]
        if any(r is None for r in routed):
            continue
        words.append(dict(word=bid, legs=legs, routed_um=[round(r, 1) for r in routed], centre_um=[round(g, 1) for g in geo],
                          stages_routed=sum(st(r) for r in routed), stages_floorplan=sum(st(g) for g in geo)))
    ws = max(words, key=lambda w: w['stages_routed'])
    wf = max(w['stages_floorplan'] for w in words)
    # ---- hub <-> stack links: vertical leg + corner + horizontal waypoints + strip FIFO, then the in-strip fan
    links = []
    for s_ in m['lfifos']:
        si = 0 if s_[1] == 'S' else 1
        vleg = [b for b in bus if b.startswith(f'lnkv_{si}_{s_[0]}_')] or \
            [b for b in bus if re.match(rf'lnkv_{si}_(\d+|c)$', b)]       # split leg (per side) or shared leg
        chain = vleg + [b for b in bus if b.startswith(f'lnkh_{si}{s_[0]}_')]
        fs = [f'fan_{s_}_s', f'fan_{s_}_21', f'fan_{s_}_10']     # strip FIFO -> farthest row engine, each hop registered
        fn = [f'fan_{s_}_n', f'fan_{s_}_34', f'fan_{s_}_45']
        r_chain = sum(L(b) or 0 for b in chain)
        hop_st = sum(st(L(b)) for b in chain if L(b))      # every waypoint hop is registered (stations)
        fan_st = max(sum(st(L(b)) for b in c if L(b)) for c in (fs, fn))
        fan_far = max(sum(L(b) or 0 for b in c) for c in (fs, fn))
        links.append(dict(stack=s_, hops=len(chain), routed_um=round(r_chain, 1), stages_routed_hops=hop_st,
                          stages_routed_min=st(r_chain), fan_routed_far_um=round(fan_far, 1), fan_stages=fan_st))
    lw = max(links, key=lambda x: x['stages_routed_hops'] + x['fan_stages'])
    # ---- single-hop classes: element port -> element port must fit one measured stage
    single = {}
    for bid, (cl, bits, eps) in bus.items():
        if cl in PIPELINED or bid.startswith(('bword_', 'pword_', 'pfrag_', 'lnk', 'fan_')):
            continue
        r = L(bid)
        if r is None:
            continue
        e = single.setdefault(cl, dict(hops=0, worst_um=0.0, worst=None, over_pitch=[], over_504=0))
        e['hops'] += 1
        if r > e['worst_um']:
            e['worst_um'], e['worst'] = round(r, 1), bid
        if r > PITCH_UM:
            e['over_pitch'].append(dict(bus=bid, routed_um=round(r, 1), stages_needed=st(r)))
        e['over_504'] += r > MISS_UM
    for e in single.values():
        e['n_over_pitch'] = len(e['over_pitch'])
        e['over_pitch'] = sorted(e['over_pitch'], key=lambda z: -z['routed_um'])[:12]
    # ---- pipelined per-hop classes: worst hop between two stations
    hop = {}
    for bid, (cl, bits, eps) in bus.items():
        if cl not in PIPELINED or bid.startswith(('bword_', 'pword_', 'pfrag_')):
            continue
        r = L(bid)
        if r is None:
            continue
        e = hop.setdefault(cl, dict(hops=0, worst_um=0.0, worst=None, stages_worst_hop=0))
        e['hops'] += 1
        if r > e['worst_um']:
            e['worst_um'], e['worst'], e['stages_worst_hop'] = round(r, 1), bid, st(r)
    return dict(
        schema='opentallas.qwen-rom-die.path-sta.v1', wirelength=str(wl_path), pitch_um=PITCH_UM,
        measured_stage=dict(record='results/rtl/qwen_corridor_gate_20261003 (D_tile_r2 430.56 um: SS60 +11.9 ps, '
                                   'FF25 met; A spans 504 um: SS -29..-79 ps)'),
        block_words=dict(count=len(words), worst=ws, stages_routed_max=ws['stages_routed'], stages_floorplan_max=wf,
                         mean_routed=round(sum(w['stages_routed'] for w in words) / len(words), 2),
                         delta_vs_floorplan=ws['stages_routed'] - wf),
        links=dict(per_stack=links, worst=lw['stack'], stages_routed=lw['stages_routed_hops'] + lw['fan_stages'],
                   floorplan_priced=53),
        single_hop=single, pipelined_hops=hop,
        method='GRT wire length per k-bundled net (worst bundle of each bus); stages = ceil(routed / 430.56 um); '
               'block-word and link paths sum their registered hops; single-hop classes must fit one stage')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--wirelength', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--skew-ps', type=float, default=0.0,
                    help='adverse clock skew between die stage flops beyond the measured stage vehicle (region CTS)')
    ap.add_argument('--slab-group-h', type=float, default=0.0)
    ap.add_argument('--cdc', default='')
    ap.add_argument('--r18', action='store_true')
    ap.add_argument('--r19', action='store_true')
    ap.add_argument('--tree-interleave', action='store_true')
    a = ap.parse_args(argv)
    v, m = B.selected(True, b3r3=True, b3r6=True, tree_cols=6, bw_align=True, bw_edge=True, io_faces=True,
                      bw_edge_inner=True, bw_sp=200, m6_strip=40, slab_group_h=a.slab_group_h, cdc=B._cdc_arg(a.cdc),
                      r18=a.r18, r19=a.r19, tree_interleave=a.tree_interleave)
    rec = record(v, m, a.wirelength, pitch=skew_pitch(a.skew_ps) if a.skew_ps else None)
    rec['skew_ps'] = a.skew_ps
    rec['floorplan'] = dict(slab_group_h=a.slab_group_h, cdc=a.cdc, die=m['die'])
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(block_words={k: rec['block_words'][k] for k in ('stages_routed_max', 'stages_floorplan_max',
                                                                          'mean_routed', 'delta_vs_floorplan')},
                          links={k: rec['links'][k] for k in ('worst', 'stages_routed')},
                          single_hop={c: (e['hops'], e['worst_um'], e['n_over_pitch'], e['over_504'])
                                      for c, e in rec['single_hop'].items()},
                          pipelined_hops={c: (e['hops'], e['worst_um'], e['stages_worst_hop'])
                                          for c, e in rec['pipelined_hops'].items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
