#!/usr/bin/env python3
"""Hub as hard cores (COORD 10-23 B2 review item 4: the flat 6.26M-cell hub probe peaked at 132 GB; OpenROAD cap 400k
cells / run).  The hub's 121 as-built leaves are grouped into hard CLUSTER cores of <= CAP cells by greedy agglomeration
on the census traffic (merge the pair with the most bits between them while the merged core stays <= CAP), so the
widest internal buses (svg<->vmks, vms<->banks, xload bd<->eg, coll<->rs/gi, dbk<->wbk) stay inside one core.  A leaf
over CAP (ot_hfd_coll_q2_hard_v8g 465k) is split into ceil(cells/CAP) slices first (CORE-HBM over-cap leaf rule).
The hub top is then a channel partition: cluster cores + hub-boundary pin registers + repeaters, no other logic.
Outputs (per variant dir): hub_cores.json = [{core, cells, leaves, ext_bits, int_bits}] + inter-core channel bits."""
import collections, json, math, re, sys

CAP = 400_000
TARGET = 360_000           # 10 % margin under the OpenROAD 400k-cell cap
PINREG = 2.5               # cells per hub-boundary bit (pin flop + buffer) inside the core that owns the bus


def cluster(insts, cells, edges, ext):
    units, ucell, uof = [], {}, {}
    for i in insts:
        k = max(1, math.ceil(cells[i] / TARGET))
        for s in range(k):
            u = i if k == 1 else f'{i}#s{s}'
            units.append(u); ucell[u] = cells[i] / k + PINREG * ext.get(i, 0) / k; uof[u] = i
    E = collections.Counter()
    for (a, b), v in edges.items():
        ua = [u for u in units if uof[u] == a]; ub = [u for u in units if uof[u] == b]
        for x in ua:
            for y in ub:
                E[frozenset((x, y))] += v / (len(ua) * len(ub))
    for i in insts:            # slices of one leaf: their shared state is internal -> heavy pull, but cap decides
        ss = [u for u in units if uof[u] == i]
        for x in range(len(ss) - 1):
            E[frozenset((ss[x], ss[x + 1]))] += 1e6
    cl = {u: {u} for u in units}
    cc = dict(ucell)
    def inter(a, b):
        return sum(E[frozenset((x, y))] for x in cl[a] for y in cl[b])
    while True:
        best = None
        ks = list(cl)
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                a, b = ks[x], ks[y]
                if cc[a] + cc[b] > TARGET:
                    continue
                v = inter(a, b)
                if v > 0 and (best is None or v > best[0]):
                    best = (v, a, b)
        if best is None:
            break
        _, a, b = best
        cl[a] |= cl.pop(b); cc[a] += cc.pop(b)
    # leftover clusters under TARGET / 2 (no traffic partner fits, e.g. the 16 pc controllers): merge the smallest into
    # the partner with the most bits to it (then the smallest) while the result stays <= TARGET
    while True:
        sm_ = sorted((k for k in cl if cc[k] < TARGET / 2), key=lambda k: cc[k])
        done = True
        for k in sm_:
            cand = [j for j in cl if j != k and cc[j] + cc[k] <= TARGET]
            if not cand:
                continue
            tgt = max(cand, key=lambda j: (inter(k, j), -cc[j]))
            cl[tgt] |= cl.pop(k); cc[tgt] += cc.pop(k)
            done = False
            break
        if done:
            break
    return cl, cc, E, uof


def compute(T, census, M, part='NW_hub'):
    import roles
    cen, blocks, role, bw = census
    cev = json.load(open(f'{roles.D4G}/inputs/cells_evidence.json'))['masters']
    hub = sorted(n for n, ps in M.items() if ps == [part])
    cells = {}
    for i in hub:
        m = blocks.get(i, {}).get('master', '')
        cells[i] = int(cev.get(m, {}).get('cells') or cev.get(re.sub(r'__pv\d+$', '', m), {}).get('cells') or 0)
    ext, intr = collections.Counter(), collections.Counter()
    for g in cen['groups']:
        if g['kind'] in ('clock', 'reset') or re.match(r'^(por_|pll_|clk|rst)', g['src_bus']):
            continue
        s, d = g['src'], g['dst']
        if s not in M or d not in M:
            continue
        w = bw.get(f"{s}.{g['src_bus']}"); b = min(g['bits'], w) if w else g['bits']
        if s in hub and d in hub:
            if s != d:
                intr[tuple(sorted((s, d)))] += b
        elif s in hub:
            ext[s] += b
        elif d in hub:
            ext[d] += b
    cl, cc, E, uof = cluster(hub, cells, intr, ext)
    names = {}
    out = []
    for k in sorted(cl, key=lambda k: -cc[k]):
        us = sorted(cl[k])
        lv = sorted({uof[u] for u in us})
        ib = sum(E[frozenset((x, y))] for x in us for y in us if x < y and E[frozenset((x, y))] < 1e6)
        xb = 0.0
        for j in cl:
            if j != k:
                xb += sum(E[frozenset((x, y))] for x in us for y in cl[j] if E[frozenset((x, y))] < 1e6)
        eb = sum(ext.get(uof[u], 0) / sum(1 for v in uof if uof[v] == uof[u]) for u in us)
        nm = f'u_hcl{len(out):02d}'
        nsl = {l: sum(1 for v in uof if uof[v] == l) for l in lv}
        out.append(dict(core=nm, cells=int(cc[k]), leaf_share=[[uof[u_], nsl[uof[u_]]] for u_ in us], leaf_cells=int(sum(cells[uof[u]] / sum(1 for v in uof if uof[v] == uof[u]) for u in us)),
                        leaves=[u.replace('#', '_') for u in us], ext_bits=int(eb), hub_int_bits=int(xb), core_int_bits=int(ib)))
    chan = int(sum(o['hub_int_bits'] for o in out) / 2)
    res = dict(rule=__doc__.split('\n')[0], cap=CAP, target=TARGET, pinreg_cells_per_bit=PINREG,
               hub_leaf_cells=sum(cells.values()), hub_ext_bits=sum(ext.values()), hub_internal_bits=sum(intr.values()),
               cores=out, n_cores=len(out), max_core_cells=max(o['cells'] for o in out),
               channel_bits=chan, bits_kept_inside_cores=int(sum(intr.values()) - chan))
    return res


def render(plan, hc, path, tn='q_hub'):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    t = plan['partition_types'][tn]
    w, h = t['outline_um']
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.add_patch(Rectangle((0, 0), w, h, fc='#eee', ec='k'))
    cm = {c['core']: c for c in hc['cores']}
    for c in t['hard_cores']:
        x, y = c['origin_um']; a, b = c['outline_um']; d = cm[c['inst']]
        ax.add_patch(Rectangle((x, y), a, b, fc='#9ecae1', ec='k'))
        fam = sorted({re.sub(r'_NW.*|NW.*', '', l) for l, _ in d['leaf_share']})
        ax.text(x + a / 2, y + b / 2, f"{c['inst'][2:]} {d['cells'] // 1000}k\n" + '\n'.join(fam[:6]), ha='center', va='center', fontsize=6)
    ax.set_xlim(-50, w + 50); ax.set_ylim(-50, h + 50); ax.set_aspect('equal')
    ax.set_title(f"{tn} {w:.0f} x {h:.0f} um: {len(t['hard_cores'])} hard cluster cores <= {hc['target'] // 1000}k cells "
                 f"(max {hc['max_core_cells'] // 1000}k); channels {hc.get('chan_um')} um\nhub-top channel bits "
                 f"{hc['channel_bits']} (inter-core) + {hc['hub_ext_bits']} (boundary); {hc['bits_kept_inside_cores']} bits kept inside cores", fontsize=9)
    plt.savefig(path, dpi=110, bbox_inches='tight')
    plt.close(fig)


def main(variant_dir='B2'):
    sys.argv = ['x']
    import gen_arch as GA, roles
    T = GA.build('B2'); census = roles.load(); M = GA.mapping(T, census)
    res = compute(T, census, M)
    out, chan = res['cores'], res['channel_bits']
    json.dump(res, open(f'{variant_dir}/hub_cores.json', 'w'), indent=1)
    print(len(out), 'cores; max', res['max_core_cells'], 'channel bits', chan, 'of', res['hub_internal_bits'])
    for o in out:
        print(o['core'], o['cells'], o['ext_bits'], o['hub_int_bits'], ' '.join(o['leaves'])[:150])


if __name__ == '__main__':
    main(*sys.argv[1:])
