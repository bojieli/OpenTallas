#!/usr/bin/env python3
"""H-NETLIST 1815: the HBM die REGIONAL SYNCHRONOUS RESET FOREST as a full_die_v16 revision layer (owner standard
10-16: regional sync reset trees with registered stages, no die-wide async fan-out; hops within the measured reach).

Input: a contract GENERATED WITHOUT the forest (its clock_resets name every reset port and its hb_ckgen por source; its
bridge_rst_n edges) and the placement (case manifest; relay stations: the 'home (x, y)' of their note).
Per domain d (stream / serial / hbm / link) and region z (C band x in [CB0, CB1], quadrants SW/SE/NW/NE at die mid):
    hb_ckgen.por_d --(hop tiles every <= R um, L path)--> hbfd_rrl_sync root at the region's sink centroid
        --(hop tiles, L path, shared prefixes)--> leaf hbfd_rrl_hop per (R x R cell, sink class), <= FANOUT sinks
        --> element reset pins.   Relay-station rs pins get their own leaves (class 'relay').
Equal age per domain: release age(sink) = pre-root hops + 3 (root) + root->leaf hops + 1 (leaf); every leaf is padded
with hop tiles to the domain maximum, so every reset pin of a domain releases on the same edge (compiler constant
RESET_AGE[d] in the report).  bridge_rst_n (subr_<q> -> su_<q>k, already synchronous in stream): hop chains, padded
equal age per source, leaf = last hop.  Each tile is clocked by its domain's regional root (clock kind 'clock').
    reset_forest_layer.py --contract C.json[.gz] --manifest M.json --out LAYER.json --report REP.json [--reach 405]
                          [--fanout 2048] [--mut-skew]   (--mut-skew: one leaf one hop deeper; bench mutant only)
"""
import argparse, collections, gzip, json, math, re
from pathlib import Path

CB0, CB1 = 14970.0, 18831.0
SRC = 'rtl/hbm_accel/die_glue/hbfd_rrl.sv'
DEPS = ['rtl/lib/ot_rst_relay.sv']
HOME = re.compile(r'home \(([-\d.]+), ([-\d.]+)\)')


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--reach', type=float, default=405.0); ap.add_argument('--fanout', type=int, default=2048)
    ap.add_argument('--mut-skew', action='store_true')
    a = ap.parse_args()
    R, FO = a.reach, a.fanout
    c = load(a.contract); man = load(a.manifest)
    pl = man['placement']; W, H = man['die_um']
    inst = c['instances']

    def pos(n):
        p = pl.get(n)
        if p is not None:
            return (p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
        m = HOME.search(inst[n].get('note', ''))
        return (float(m.group(1)), float(m.group(2))) if m else None

    def zone(xy):
        x, y = xy
        if CB0 <= x <= CB1:
            return 'C'
        return ('N' if y >= H / 2 else 'S') + ('W' if x < CB0 else 'E')
    md = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    ck = pos('hb_ckgen')
    tiles, edges, clocks, problems = [], [], [], []
    nid = collections.Counter()

    def tile(kind, dom, tag, xy, note):
        nid[tag] += 1
        n = f'rrf_{tag}_{nid[tag]:04d}'
        tiles.append(dict(name=n, master=f'hbfd_rrl_{kind}', source=SRC, rtl_deps=DEPS, params={}, slot=None,
                          owner='H-NETLIST reset forest', note=f'{note}; home ({round(xy[0], 1)}, {round(xy[1], 1)}) um'))
        clocks.append(dict(inst=n, port='clk', domain=dom, kind='clock'))
        return n

    def E(src, dst, dom):
        edges.append(dict(src=src, dst=dst, bits=1, clock=dom, basis='H-NETLIST 1815 regional sync reset forest'))

    def lpath(p, q):
        """points every R um along the L path p -> q (x first), excluding p, excluding q"""
        L = md(p, q); n = max(0, math.ceil(L / R) - 1); out = []
        for k in range(1, n + 1):
            t = k * L / (n + 1); dx = abs(q[0] - p[0])
            if t <= dx:
                out.append((p[0] + math.copysign(t, q[0] - p[0]), p[1]))
            else:
                out.append((q[0], p[1] + math.copysign(t - dx, q[1] - p[1])))
        return out
    # ---- sinks per domain from clock_resets
    sinks = collections.defaultdict(list)
    unplaced = collections.Counter()
    for x in c['clock_resets']:
        if x['kind'] != 'reset' or x['source'][0] != 'hb_ckgen':
            continue
        dom = x['domain']; xy = pos(x['instance'])
        if xy is None:
            unplaced[inst[x['instance']]['master']] += 1
            continue
        cls = 'relay' if inst[x['instance']]['master'].startswith('hbfd_rly_') else 'elem'
        for b in range(x['bits']):     # a multi-bit reset port (per-lane / per-region copies): every bit is a sink pin
            sinks[(dom, x['source'][1])].append((x['instance'], (x['port'], b, x['bits']), xy, cls))
    rep = dict(schema='opentallas.hbm.reset_forest.v1', reach_um=R, fanout_cap=FO, domains={}, unplaced=dict(unplaced))
    ports = []
    for (dom, por), S in sorted(sinks.items()):
        byz = collections.defaultdict(list)
        for s in S:
            byz[zone(s[2])].append(s)
        plan = []   # (zone, root, [(leaf_xy, cls, [sinks])])
        for z, Z in sorted(byz.items()):
            cx = sum(s[2][0] for s in Z) / len(Z); cy = sum(s[2][1] for s in Z) / len(Z)
            cells = collections.defaultdict(list)
            for s in Z:
                cells[(int(s[2][0] // R), int(s[2][1] // R), s[3])].append(s)
            leaves = []
            for (gx, gy, cls), L_ in sorted(cells.items()):
                for k in range(0, len(L_), FO):
                    chunk = L_[k:k + FO]
                    leaves.append(((sum(s[2][0] for s in chunk) / len(chunk), sum(s[2][1] for s in chunk) / len(chunk)), cls, chunk))
            plan.append((z, (cx, cy), leaves))
        # ages before padding
        ages = []
        for z, root, leaves in plan:
            pre = len(lpath(ck, root))
            for lxy, cls, chunk in leaves:
                ages.append(pre + 3 + len(lpath(root, lxy)) + 1)
        AGE = max(ages)
        stats = dict(sinks=len(S), regions={}, age=AGE, tiles=0)
        mut_done = False
        for z, root, leaves in plan:
            tag = f'{dom[:2]}{z}'
            prev = ['hb_ckgen', por]
            for xy in lpath(ck, root):
                n = tile('hop', dom, tag, xy, f'{dom} reset: hb_ckgen.{por} -> {z} root, reach hop')
                E(prev, [n, 'rst_n_in'], dom); prev = [n, 'rst_n']
            rt = tile('sync', dom, tag, root, f'{dom} reset: {z} regional root (async por -> 2-flop sync release)')
            E(prev, [rt, 'rst_n_in'], dom)
            pre = len(lpath(ck, root))
            trie = {}
            nleaf = 0
            for lxy, cls, chunk in leaves:
                prev = [rt, 'rst_n']; key = ()
                for xy in lpath(root, lxy):
                    key = key + ((round(xy[0]), round(xy[1])),)
                    if key not in trie:
                        n = tile('hop', dom, tag, xy, f'{dom} reset: {z} root -> leaf, reach hop')
                        E(prev, [n, 'rst_n_in'], dom); trie[key] = n
                    prev = [trie[key], 'rst_n']
                pads = AGE - (pre + 3 + len(lpath(root, lxy)) + 1)
                if a.mut_skew and not mut_done:
                    pads += 1; mut_done = True
                for k in range(pads):
                    n = tile('hop', dom, tag, lxy, f'{dom} reset: {z} equal-age pad {k + 1}/{pads}')
                    E(prev, [n, 'rst_n_in'], dom); prev = [n, 'rst_n']
                lf = tile('hop', dom, tag, lxy, f'{dom} reset: {z} leaf ({cls}, {len(chunk)} sinks)')
                E(prev, [lf, 'rst_n_in'], dom); nleaf += 1
                for (i, (p, b, nb), _xy, _c) in chunk:
                    E([lf, 'rst_n', 0, 1], [i, p, b, b + 1] if nb > 1 else [i, p], dom)
                    if b == 0:
                        ports.append([i, p])
            stats['regions'][z] = dict(sinks=sum(len(l[2]) for l in leaves), leaves=nleaf, root=[round(root[0]), round(root[1])],
                                       pre_root_hops=pre)
        stats['tiles'] = sum(1 for t in tiles if t['name'].startswith(f'rrf_{dom[:2]}'))
        rep['domains'][f'{dom}:{por}'] = stats
    # ---- bridge_rst_n: synchronous stream source -> hop chains, equal age per source
    drop = []
    br = collections.defaultdict(list)
    for e in c['edges']:
        if e['source'][1] == 'bridge_rst_n':
            br[e['source'][0]].append(e['sink'])
    for s_, dsts in sorted(br.items()):
        drop.extend([s_, 'bridge_rst_n', d[0]] for d in dsts)
        sp = pos(s_); dom = 'stream'
        lens = [len(lpath(sp, pos(d[0]))) for d in dsts]
        AGE = max(lens) + 1
        tag = f'br{s_.split("_")[-1]}'
        for d, L_ in zip(dsts, lens):
            prev = [s_, 'bridge_rst_n']; dxy = pos(d[0])
            for xy in lpath(sp, dxy):
                n = tile('hop', dom, tag, xy, f'bridge reset {s_} -> {d[0]}, reach hop')
                E(prev, [n, 'rst_n_in'], dom); prev = [n, 'rst_n']
            for k in range(AGE - 1 - L_):
                n = tile('hop', dom, tag, dxy, f'bridge reset {s_} -> {d[0]}, equal-age pad')
                E(prev, [n, 'rst_n_in'], dom); prev = [n, 'rst_n']
            lf = tile('hop', dom, tag, dxy, f'bridge reset {s_} -> {d[0]}, leaf')
            E(prev, [lf, 'rst_n_in'], dom); E([lf, 'rst_n'], [d[0], d[1]], dom)
        rep['domains'][f'bridge:{s_}'] = dict(sinks=len(dsts), age=AGE)
    spec = dict(region='reset_forest', author='Claude H-NETLIST 1815', basis_commit='owner standard 10-16 (regional sync reset trees)',
                instances=tiles, edges=edges, clocks=clocks, straps=[], gaps=[], drop_edges=drop,
                reset_forest_ports=ports, notes=__doc__.split('\n\n')[0])
    a.out.write_text(json.dumps(spec) + '\n')
    rep.update(tiles=len(tiles), reset_ports=len(ports), problems=problems,
               tiles_by_master=dict(collections.Counter(t['master'] for t in tiles)))
    a.report.write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('tiles', 'reset_ports', 'tiles_by_master', 'unplaced')}),
          {k: (v.get('sinks'), v.get('age')) for k, v in rep['domains'].items()}, len(problems), 'problems')


if __name__ == '__main__':
    main()
