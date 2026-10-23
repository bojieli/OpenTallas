#!/usr/bin/env python3
"""FT-KV2-CHAINS 10-23: KV-die census rewrites for the trees left after the PV broadcast chain (ft_kv_pv_chain.py),
measured with the same planner (tools/die_feedthrough/plan.py, identical settings).

    ft_kv_tree_chain.py rewrite --census PVCHAIN.json.gz --dump DUMP --out OUT.json.gz --tree-out TREE.json
                                [--trees resp,cmd] [--head-qslice]
    ft_kv_tree_chain.py report  --dump DUMP --tree TREE.json --before PLAN0.json --after PLAN1.json [--json OUT]

What the RTL is, and what the census made of it
-----------------------------------------------
(c) astk response_data (+ pvw cmd).  qkd_pvw_die_t (tools/qwen_kv_die/pv_trunk_gen.py, KVPLAN 1815) already carries
    in_e (the two astk quadrants' 256-b response words) and the pair control word cmd_w (32 b) + rst_n as ONE
    registered 289-b column trunk a pair column c (c0 / c1 at the pair's centre channel): CL<c>_0..2 at the strip end,
    then per block row r an X<r>c station (734-um pitch, the row's tap point) and two pass-through M<r>_1/_2 stations
    (245-um hops of the 400-um plan), CP taps -> K<r>c<g> (one per column group) -> S / R relays -> the 8 bank slices.
    The census treats relays as transparent, so it FLATTENS this trunk into 1,024 independent 7.4-8.9-mm lanes a
    quadrant pair (src owner_7 -> every slice; 95 b each) and 2,176 pvw ctl cmd lanes (12-13 mm), and the planner routes
    each one on its own straight L: 851k + 296k bit-mm (21% of the die's bit-mm) for what is physically 4 trunks.
    Rewrite: rebuild the real tree from the census relay paths (trie over src -> relays -> sink), take each wire's
    width from the dump bundles (relay -> relay; the sink edge keeps the census bits of the rewritten groups), then
    COLLAPSE pass-through stations (one child): what is left is the registered chain with one station a block row (X),
    the per-group tap K and its local re-drive to the slices, entry owner_7 -> CL as one lane.  plan.py re-stations
    every collapsed lane at the 1.2-mm reach exactly as it does every other lane.  Static: one fixed path a sink, no
    hub, no credits, nothing tied off (the same relays / bits as the RTL; only pass-through stations go).
(a)/(b) head dr_o / f_t* / kp / kp_o and hst t2 ti_b.  NOT long trees: inside each 1,030 x 540-um head footprint the
    data path is T2 (hst_*_t2, qkh_head_gather_stage) -> 4 front quarters (809 b each: row_in[256g+:256] + full q 512 +
    ctl) -> 16 stin (233 b) -> 16 lane8 (233 b), lane8 -> stk -> ktree (32 b); every hop is one registered leaf-to-leaf
    wire of 150-400 um (straight), the sinks of a fan-out sit 135 um apart and take DISJOINT slices except q.  A
    registered chain T2 -> front3 -> ... -> front0 would carry 1559/1303/1047/791 b = 4,700 b-hops against the star's
    4 x 809 = 3,236: chaining adds wire.  No rewrite.  --head-qslice is the one structural lever found (RTL change, see
    below): front g serves the lanes whose Q fragment needs q_data half (g & 1) only, so T2 -> front q_data 512 -> 256 b.

Outputs: the rewritten census (summary.tree_chain = stats) and TREE.json (nodes, edges with their new group keys, sink
paths and the old per-sink stages) that 'report' joins with the two plans: per-tree lanes / overflow lanes / overflow
bits / M8 (H) and M9 (V) track-mm, channel relays, max stages, and every sink's arrival stage before -> after.
"""
import argparse
import collections
import gzip
import json
import math
import re
from pathlib import Path

RELAY_RE = re.compile(r'^(qkd_rlys|qkd_rlysh|qkd_rlyi_|qkd_astk_rly|qkd_landsh)')
PV_SINK_RE = re.compile(r'^pvw_[01]__u_s\d+_(b\d|j)$')
TREES = dict(
    resp=lambda g: g['src_bus'] == 'response_data' and bool(PV_SINK_RE.match(g['dst'])),
    cmd=lambda g: g['src_bus'] == 'cmd' and g['src'].startswith('pvw_') and g['src'].endswith('__u_ctl')
                   and bool(PV_SINK_RE.match(g['dst'])),
)


def _open(p, mode='rt'):
    return gzip.open(p, mode) if str(p).endswith('.gz') else open(p, mode)


def load_blocks(dump):
    out = {}
    for ln in Path(dump, 'blocks.tsv').read_text().splitlines():
        f = ln.split('\t')
        if len(f) < 6:
            continue
        try:
            out[f[0]] = (f[1], float(f[2]), float(f[3]), float(f[4]), float(f[5]))
        except ValueError:
            continue
    return out


def load_bundles(dump):
    """-> {(src inst, dst inst): bits}, {(src inst, dst inst): set of dst buses}"""
    bits = collections.defaultdict(int)
    dbus = collections.defaultdict(set)
    with _open(Path(dump, 'bundles.tsv.gz')) as f:
        for ln in f:
            s = ln.rstrip('\n').split('\t')
            if len(s) >= 5 and s[1] != 'tie_hi':
                bits[(s[0], s[2])] += int(s[4])
                dbus[(s[0], s[2])].add(s[3])
    return bits, dbus


def centre(b):
    _, x, y, w, h = b
    return (round(x + w / 2, 3), round(y + h / 2, 3))


def lane(src, sbus, dst, dbus, bits, spt, dpt, reach, tag, kind='data'):
    L = abs(spt[0] - dpt[0]) + abs(spt[1] - dpt[1])
    return dict(src=src, src_bus=sbus, dst=dst, dst_bus=dbus, kind=kind, bits=int(bits), chains=1, stages=0,
                stages_min=0, lands=0, nbuf_max=0, cur_um=round(L, 1), straight_um=round(L, 1), detour=1.0,
                ideal_stages=max(0, math.ceil(L / reach) - 1), route='HV', src_pt=[round(spt[0], 3), round(spt[1], 3)],
                dst_pt=[round(dpt[0], 3), round(dpt[1], 3)], crosses=[], tree_chain=tag)


def chain_trees(groups, names, blocks, bund_dbus, reach):
    """-> (kept groups, new groups, tree record).  Reset groups (kind 'reset': plan.py does not route them) stay as
    they are, and their 1-b reset relays are not counted in the sink edges."""
    bund, dbus_of = bund_dbus
    hit = lambda g: g['kind'] != 'reset' and any(TREES[n](g) for n in names)
    sel = [g for g in groups if hit(g)]
    keep = [g for g in groups if not hit(g)]
    tag_of = lambda g: next(n for n in names if TREES[n](g))
    # trie: node = instance name; root nodes carry the source pin point, sinks the census dst point
    children = collections.defaultdict(set)
    parents = collections.defaultdict(set)
    pt = {}
    roots = set()
    sink_bits = collections.defaultdict(int)          # (last relay, sink) -> census bits of the rewritten groups
    sink_groups = []
    for g in sel:
        path = [g['src']] + list(g.get('relays') or []) + [g['dst']]
        roots.add(g['src'])
        pt.setdefault(g['src'], tuple(g['src_pt']))
        pt.setdefault(g['dst'], tuple(g['dst_pt']))
        for r in g.get('relays') or []:
            pt.setdefault(r, centre(blocks[r]))
        for a, b in zip(path, path[1:]):
            parents[b].add(a)
            children[a].add(b)
        sink_bits[(path[-2], g['dst'])] += g['bits']
        sink_groups.append(dict(tree=tag_of(g), src=g['src'], dst=g['dst'], dst_bus=g['dst_bus'], bits=g['bits'],
                                stages_rtl=g['stages'], path=path))
    sinks = {g['dst'] for g in sel}
    drives = collections.defaultdict(set)              # sink -> the relays driving it directly (dump bundles)
    for (a, b) in bund:
        if b in sinks and a in blocks and RELAY_RE.match(blocks[a][0]) and dbus_of[(a, b)] != {'rst_n'}:
            drives[b].add(a)
    # retained nodes: roots, sinks, branch points (>= 2 children) and merge points (>= 2 parents: resp + cmd share the
    # CL / X trunk from the CL station on)
    keep_node = set(roots) | sinks | {n for n, c in children.items() if len(c) >= 2} | \
        {n for n, p in parents.items() if len(p) >= 2}
    new, edges = [], {}

    def emit(u):
        chains = collections.defaultdict(list)
        for c in sorted(children.get(u, ())):
            chain = [u, c]
            while chain[-1] not in keep_node:
                (nx,) = children[chain[-1]]
                chain.append(nx)
            chains[chain[-1]].append(chain)
        for v, cs in chains.items():
            if v in sinks and not children.get(v):
                # the sink edge: the real wire widths from u into the sink's own relays (K -> S r0 40 b + S r1 16 b +
                # R 1 b), from the dump bundles; the last relay -> slice bundle also carries the V chunk (PV chain) and
                # the census attributes the same K bits to every upstream source (EN, WN, ctl), so neither is used.
                # A direct edge keeps the census bits.
                own = [r for r in drives.get(v, ()) if (u, r) in bund]
                bits = sum(bund[(u, r)] for r in own) if own else sink_bits[(u, v)]
            else:
                bits = max(min(w for w in [bund.get((a, b), 0) for a, b in zip(ch, ch[1:])] if w > 0) for ch in cs)
            key = (u, v)
            if key not in edges:
                sbus = 'b' if u not in roots else next(g['src_bus'] for g in sel if g['src'] == u)
                dbus = 'pv2' if v in sinks else 'a'
                gnew = lane(u, sbus, v, dbus, bits, pt[u], pt[v], reach, 'tc')
                edges[key] = dict(src=u, dst=v, bits=bits, dropped=sorted({d for ch in cs for d in ch[1:-1]}),
                                  um=gnew['straight_um'])
                new.append(gnew)
            if v not in done:
                done.add(v)
                emit(v)
    done = set()
    for r in sorted(roots):
        emit(r)
    rec = dict(nodes=sorted(keep_node - sinks - roots), roots=sorted(roots), n_sinks=len(sinks),
               edges=list(edges.values()), sink_groups=[dict(s, path=None, kept=[n for n in s['path'] if n in keep_node])
                                                       for s in sink_groups])
    stats = dict(trees=names, old_groups=len(sel), old_bits=sum(g['bits'] for g in sel),
                 old_bitmm=round(sum(g['bits'] * g['straight_um'] for g in sel) / 1000),
                 new_groups=len(new), new_bits=sum(g['bits'] for g in new),
                 new_bitmm=round(sum(g['bits'] * g['straight_um'] for g in new) / 1000),
                 stations_kept=len(rec['nodes']),
                 stations_dropped=len({d for e in edges.values() for d in e['dropped']}))
    return keep, new, rec, stats


def head_qslice(groups):
    """--head-qslice (RTL change, measured as a what-if): T2 -> front q_data_in 512 -> 256 b."""
    n = 0
    out = []
    for g in groups:
        if g['src_bus'] == 'ti_b' and re.match(r'^hst_\w+_t2$', g['src']) and g['dst_bus'] == 'q_data_in' \
                and '__g_front_' in g['dst'] and g['bits'] == 512:
            g = dict(g, bits=256, qslice=True)
            n += 1
        out.append(g)
    return out, n


def cmd_rewrite(a):
    with _open(a.census) as f:
        cen = json.load(f)
    blocks = load_blocks(a.dump)
    bund = load_bundles(a.dump)
    reach = float(cen['summary'].get('reach_um') or 1200.0)
    names = [t for t in a.trees.split(',') if t]
    groups = cen['groups']
    stats = dict()
    rec = dict()
    if names:
        keep, new, rec, stats = chain_trees(groups, names, blocks, bund, reach)
        groups = keep + new
    if a.head_qslice:
        groups, nq = head_qslice(groups)
        stats['head_qslice_groups'] = nq
    cen = dict(cen, groups=groups)
    cen['summary'] = dict(cen['summary'], tree_chain=stats)
    with _open(a.out, 'wt') as f:
        json.dump(cen, f)
    if a.tree_out:
        Path(a.tree_out).write_text(json.dumps(rec))
    print(json.dumps(stats))


# ---------------------------------------------------------------------------------------------------------------- report
FAMILIES = [
    ('head', lambda l, tc: l['src'].startswith('head_') and '__' in l['src'] and l['dst'].startswith('head_')),
    ('hst_t2_ti_b', lambda l, tc: re.match(r'^hst_\w+_t2$', l['src']) is not None and l['dst'].startswith('head_')),
    ('resp_cmd', lambda l, tc: (l['src'], l['dst']) in tc or (bool(PV_SINK_RE.match(l['dst'])) and (
        l['src_bus'] == 'response_data' or (l['src_bus'] == 'cmd' and l['src'].endswith('__u_ctl'))))),
    ('pvw_ts', lambda l, tc: l['src_bus'] == 'ts'),
]


def tracks(bits, occ=0.6):
    return int(math.ceil(bits / occ - 1e-9))


def lane_tmm(l):
    pts = l.get('pts') or []
    n = tracks(l['bits'])
    h = sum(abs(b[0] - a[0]) for a, b in zip(pts, pts[1:])) / 1000
    v = sum(abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])) / 1000
    return n * h, n * v


def plan_metrics(plan, die, tc=frozenset()):
    x0, y0, x1, y1 = die['die']
    pitch = {L['name']: L['pitch'] for L in die['layers']}
    capH = ((y1 - y0) / pitch['M8']) * (x1 - x0) / 1000
    capV = ((x1 - x0) / pitch['M9']) * (y1 - y0) / 1000
    fam = collections.defaultdict(lambda: dict(lanes=0, bits=0, ovf_lanes=0, ovf_bits=0, M8_tmm=0.0, M9_tmm=0.0,
                                               chan_relays=0, max_stages=0))
    tot = dict(lanes=0, ovf_lanes=0, ovf_bits=0, M8_tmm=0.0, M9_tmm=0.0)
    for l in plan['lanes']:
        h, v = lane_tmm(l)
        names = [n for n, f in FAMILIES if f(l, tc)][:1] or ['other']
        for n in names + ['_all']:
            r = fam[n]
            r['lanes'] += 1
            r['bits'] += l['bits']
            r['ovf_lanes'] += int(bool(l.get('track_overflow')))
            r['ovf_bits'] += l['bits'] if l.get('track_overflow') else 0
            r['M8_tmm'] += h
            r['M9_tmm'] += v
            r['chan_relays'] += l.get('channel_stages', 0)
            r['max_stages'] = max(r['max_stages'], l.get('stages_new', 0))
    out = {}
    for n, r in fam.items():
        out[n] = dict(r, M8_tmm=round(r['M8_tmm']), M9_tmm=round(r['M9_tmm']),
                      M8_pct=round(100 * r['M8_tmm'] / capH, 1), M9_pct=round(100 * r['M9_tmm'] / capV, 1))
    s = plan['summary']
    out['_summary'] = dict(lanes=s['lanes'], track_overflow_lanes=s['track_overflow_lanes'],
                           channel_relays_new=s['channel_relays_new'], max_stages_new=s['max_stages_new'],
                           stages_new_bitw=s['stages_new_bitw'], cap_M8_tmm=round(capH), cap_M9_tmm=round(capV))
    return out


def arrivals(tree, before, after, reach=1200.0):
    """per sink group: RTL stages (census), before = plan stages of the flattened lane, after = sum over the kept path
    of (plan stages of each lane) + one register per kept intermediate station."""
    st0 = {(l['src'], l['dst'], l['dst_bus']): l['stages_new'] for l in before['lanes']}
    tc = {(e['src'], e['dst']) for e in tree['edges']}
    st1 = {(l['src'], l['dst']): l['stages_new'] for l in after['lanes'] if (l['src'], l['dst']) in tc}
    um = {(e['src'], e['dst']): e['um'] for e in tree['edges']}
    rows = []
    for s in tree['sink_groups']:
        k = s['kept']
        new = sum(st1[(a, b)] for a, b in zip(k, k[1:])) + (len(k) - 2)
        ideal = sum(max(0, math.ceil(um[(a, b)] / reach) - 1) for a, b in zip(k, k[1:])) + (len(k) - 2)
        rows.append(dict(tree=s['tree'], src=s['src'], dst=s['dst'], dst_bus=s['dst_bus'], rtl=s['stages_rtl'],
                         before=st0.get((s['src'], s['dst'], s['dst_bus'])), after=new, ideal=ideal))
    return rows


def cmd_report(a):
    die = json.load(open(Path(a.dump, 'die.json')))
    res = dict()
    plans = dict(before=a.before, after=a.after)
    if a.qslice:
        plans['after_qslice'] = a.qslice
    tree = json.loads(Path(a.tree).read_text()) if a.tree else dict(edges=[])
    tc = frozenset((e['src'], e['dst']) for e in tree['edges'])
    loaded = {}
    for k, p in plans.items():
        loaded[k] = json.load(_open(p))
        res[k] = plan_metrics(loaded[k], die, tc)
    if a.tree:
        rows = arrivals(tree, loaded['before'], loaded['after'])
        agg = collections.defaultdict(list)
        for r in rows:
            m = re.match(r'^(pvw_[01])__u_s(\d+)_(b\d|j)$', r['dst'])
            agg[(r['tree'], r['src'].split('__')[0], m.group(1))].append(r)
        res['arrivals'] = [dict(tree=t, src=s, pair=p, n=len(v),
                                rtl=[min(x['rtl'] for x in v), max(x['rtl'] for x in v)],
                                before=[min(x['before'] for x in v), max(x['before'] for x in v)],
                                after=[min(x['after'] for x in v), max(x['after'] for x in v)],
                                ideal=[min(x['ideal'] for x in v), max(x['ideal'] for x in v)])
                           for (t, s, p), v in sorted(agg.items())]
        if a.arrivals_tsv:
            with open(a.arrivals_tsv, 'w') as f:
                f.write('tree\tsrc\tdst\tdst_bus\tstages_rtl\tstages_before\tstages_after\tstages_ideal\n')
                for r in rows:
                    f.write(f"{r['tree']}\t{r['src']}\t{r['dst']}\t{r['dst_bus']}\t{r['rtl']}\t{r['before']}\t"
                            f"{r['after']}\t{r['ideal']}\n")
    txt = json.dumps(res, indent=1)
    if a.json:
        Path(a.json).write_text(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('rewrite')
    r.add_argument('--census', required=True)
    r.add_argument('--dump', required=True)
    r.add_argument('--out', required=True)
    r.add_argument('--tree-out')
    r.add_argument('--trees', default='resp,cmd')
    r.add_argument('--head-qslice', action='store_true')
    p = sub.add_parser('report')
    p.add_argument('--dump', required=True)
    p.add_argument('--before', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--qslice')
    p.add_argument('--tree')
    p.add_argument('--json')
    p.add_argument('--arrivals-tsv')
    a = ap.parse_args()
    (cmd_rewrite if a.cmd == 'rewrite' else cmd_report)(a)


if __name__ == '__main__':
    main()
