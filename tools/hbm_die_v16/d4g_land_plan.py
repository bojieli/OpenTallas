#!/usr/bin/env python3
"""HBM-LANDING 10-18: d4g LANDING E pilot (model, NOT die STA) -> land plan + per-class latency deltas for the pricer.

Every d4g plan link (results/arch/hbm_die_d4g/plan/d4g_phy: compact.graph.json links on compact.P.json outlines) whose
two ends sit in DIFFERENT, NON-NEIGHBOUR clock regions (d4g_region_map.json; the relay_layer_d4f.py 'inter' rule) is a
forwarded-clock lane and ends in a landing (lanes/LANDING-CONTRACT.md).  Intra-region and neighbour-region links keep
plain root-clocked relays (no landing, priced unchanged).

Geometry: link length = closest-point Manhattan gap between the two outlines (the plan model).  Stations N per link =
the class's plan stage count (eval.json per_class stages_bw, bits-weighted) scaled by the link's length over the class
bits-weighted mean length, rounded up (N >= 1 once the gap exceeds the 405 um reach).

Clock model (ASSUMPTIONS, stated; the die STA re-derives E at GEN2 -- K is a strap):
  * forwarded hop k -> k+1 (half-cycle station: ONE kept inverter replaces the BUFx12f forward of hbfd_rly_*_fc):
      h = 115 ps (S81 p4j measured ck -> ck_o arc) + 0.72 ps/um x hop length (S81 p4j clock leg 453.6 ps incl. the
      repeated forwarded-clock wire);  FF = 0.76 x TT (closed hbfd_rly_136_EW_fc insertion 57.7 / 76.2 ps).
      The inverter is assumed equal to the buffer it replaces (+-10 ps: inside the window margins below).
  * die clock tree to each region root: BUFx24 M8 repeater model of tools/hbm_die_v15/die_clock_tree.py (stage_ps,
      ~176 ps / 420 um TT) along the Manhattan path from the hb_ckgen pin (grants_d4g.json slot) to the region site;
      FF = 0.76 x TT.  Region-local trees are equal on both ends and cancel.
  * dL = L_src_root + N h - L_sink_root  (the lane clock at the ring vs the sink root, same logical edge).
  * RTL (2e482a69f, hbm_lane_bench): hop 0 = NON-inverting ICG on the source root (one full cycle), then N - 1 half-cycle
      stations, so the ring write is (N + 2)/2 cycles after the launch edge (+ dL); the landing output register reads at
      launch + ceil(N/2) + 1 + E.  Read-after-write margin m = E + (N odd ? 1/2 : 0) - dL/T, i.e. an ODD N gives the
      handoff T/2 of slack:  dL' = dL - (N odd ? T/2 : 0)  (the old inverting-hop-0 model added T/2 for odd N: wrong
      for this RTL; checked by the relay lockstep at E = 1, K = ceil(N/2) + 1, both parities).
LANDING-CONTRACT L5 with D = 4, ONE E per link (all lanes of the bundle; the same at TT and FF), CHAIN convention
(relay_layer_d4f.py --land, relay_lockstep_bench.py):
      E = max over corners of max(1, ceil((dL' + t_cq + t_su + U_setup) / T))
      window: (E - D) T + t_hold + U_hold < dL'_c < E T - t_cq - t_su - U_setup   at TT AND FF
      t_cq 45, t_su 25, U_setup 60, t_hold 15, U_hold 25 ps (ASAP7 DFF, die uncertainty policy).
      K = (ceil(N/2) + E) mod 2D (sources and sinks released on the same root edge, G = R0; the binder re-derives
      K = (ceil(N/2) + E + G - R0) mod 2D).  K here uses the MODEL N; relay_layer_d4f.py recomputes K from E and the
      layer's real N unless the entry's 'stations' equals it.
Latency charged per traversal (L4): half-cycle  ceil(N/2) + 1 (ring) + E (+1 block flop, already in the base price)
                                    full-cycle  N + 1 + E
  vs today's N  ->  delta_half = 1 + E_h - floor(N/2),  delta_full = 1 + E_f.
Per class the pricer stage count gets the bits-weighted mean delta over the class's links (unlanded links 0).

    d4g_land_plan.py [--out results/arch/hbm_die_d4g/landing]
"""
import argparse, collections, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D4G = ROOT / 'results/arch/hbm_die_d4g'
T_CLS = {'SU_CORE': 1111.1, 'SFU_CORE': 1111.1, 'LG_SU': 1111.1, 'LG_SFU': 1111.1}   # serial-chain domain 0.9 GHz (3:4)
T_STREAM = 833.3
D = 4
TCQ, TSU, US, TH, UH = 45.0, 25.0, 60.0, 15.0, 25.0
FF_RATIO = 0.76
REACH = 405.0


def hop_ps(L):
    return 115.0 + 0.72 * L


def tree_ps(d):
    if d <= 0:
        return 0.0
    n = max(1, math.ceil(d / 420.0))
    return n * (25.0 + 8.6e-4 * (d / n) ** 2)


def gap(a, b):
    return (max(0.0, a['x'] - b['x'] - b['w'], b['x'] - a['x'] - a['w'])
            + max(0.0, a['y'] - b['y'] - b['h'], b['y'] - a['y'] - a['h']))


def e_of(dl, T):
    return max(1, math.ceil((dl + TCQ + TSU + US) / T))


def window_ok(dl, E, T):
    return (E - D) * T + TH + UH < dl < E * T - TCQ - TSU - US


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=D4G / 'landing')
    a = ap.parse_args()
    G = json.loads((D4G / 'plan/d4g_phy/compact.graph.json').read_text())
    P = json.loads((D4G / 'plan/d4g_phy/compact.P.json').read_text())
    ev = json.loads((D4G / 'plan/d4g_phy/eval.json').read_text())
    M = json.loads((D4G / 'd4g_region_map.json').read_text())
    gr = json.loads((D4G / 'grants_d4g.json').read_text())
    ck = next(s for s in gr['slots'] if s['name'] == 'hb_ckgen')
    ckxy = (ck['origin']['x'] + ck['outline']['w'] / 2, ck['origin']['y'] + ck['outline']['h'] / 2)
    reg = {k: v['region'] for k, v in M['instances'].items()}
    site = {k: v['site'] for k, v in M['regions'].items()}
    neigh = {frozenset(x) for x in M['neighbours']}
    Lroot = {r: tree_ps(abs(s[0] - ckxy[0]) + abs(s[1] - ckxy[1])) for r, s in site.items()}
    st_bw = {k: v['stages_bw'] for k, v in ev['per_class'].items()}
    links = [l for l in G['links'] if l['src'] in P and l['dst'] in P]
    for l in links:
        l['len'] = gap(P[l['src']], P[l['dst']])
    mlen = {}
    for c in st_bw:
        L = [l for l in links if l['cls'] == c]
        bw = sum(l['bits'] for l in L)
        mlen[c] = (sum(l['bits'] * l['len'] for l in L) / bw) if bw else 0.0
    rows, cls_acc = [], collections.defaultdict(lambda: dict(bits=0, dh=0.0, df=0.0, landed_bits=0, links=0, landed=0))
    for l in links:
        c = l['cls']; T = T_CLS.get(c, T_STREAM)
        rs, rd = reg.get(l['src']), reg.get(l['dst'])
        inter = rs != rd and frozenset((rs, rd)) not in neigh
        n = 0
        if l['len'] > REACH and mlen.get(c):
            n = max(1, math.ceil(st_bw[c] * l['len'] / mlen[c] - 1e-9))
        acc = cls_acc[c]; acc['bits'] += l['bits']; acc['links'] += 1
        row = dict(link=f"{l['src']}->{l['dst']}", id=l['id'], cls=c, bits=l['bits'], src=l['src'], dst=l['dst'],
                   src_region=rs, dst_region=rd, len_um=round(l['len'], 1), stations=n, period_ps=T,
                   landed=bool(inter and n >= 1))
        if not row['landed']:
            row['why_not'] = ('same region' if rs == rd else 'neighbour regions (plain root->root relays)' if inter is False
                              else 'no relay station (0-stage link: neighbour root->root hop)')
            rows.append(row); continue
        hop = l['len'] / (n + 1)
        res = {}
        for corner, f in (('tt', 1.0), ('ff', FF_RATIO)):
            base = (Lroot[rs] + n * hop_ps(hop) - Lroot[rd]) * f
            res[corner] = dict(full=base, half=base - (T / 2 if n % 2 else 0.0))   # RTL 2e482a69f: odd N = T/2 slack
        out = {}
        for mode in ('half', 'full'):
            E = max(e_of(res['tt'][mode], T), e_of(res['ff'][mode], T))
            ok = window_ok(res['tt'][mode], E, T) and window_ok(res['ff'][mode], E, T)
            Dn = D
            while not ok and Dn < 16:      # hold side failing: raise D, not E (L5)
                Dn *= 2
                ok = ((E - Dn) * T + TH + UH < min(res['tt'][mode], res['ff'][mode]))
            out[mode] = dict(E=E, D=Dn, window_ok=ok)
        Eh, Ef = out['half']['E'], out['full']['E']
        K = (math.ceil(n / 2) + Eh) % (2 * D)
        dh = 1 + Eh - n // 2; df = 1 + Ef
        row.update(E=Eh, K=K, D=out['half']['D'], window_ok=out['half']['window_ok'],
                   dL_tt=round(res['tt']['half'], 1), dL_ff=round(res['ff']['half'], 1),
                   E_full_cycle=Ef, dL_tt_full=round(res['tt']['full'], 1), dL_ff_full=round(res['ff']['full'], 1),
                   latency_half=math.ceil(n / 2) + 1 + Eh, latency_full=n + 1 + Ef, latency_now=n,
                   delta_half=dh, delta_full=df)
        acc['landed'] += 1; acc['landed_bits'] += l['bits']; acc['dh'] += l['bits'] * dh; acc['df'] += l['bits'] * df
        rows.append(row)
    landed = [r for r in rows if r['landed']]
    per_class = {c: dict(links=v['links'], landed_links=v['landed'], bits=v['bits'], landed_bits=v['landed_bits'],
                         plan_stages_bw=st_bw.get(c),
                         delta_half_bw=round(v['dh'] / v['bits'], 3) if v['bits'] else 0.0,
                         delta_full_bw=round(v['df'] / v['bits'], 3) if v['bits'] else 0.0,
                         E_hist=dict(sorted(collections.Counter(r['E'] for r in landed if r['cls'] == c).items())))
                 for c, v in sorted(cls_acc.items())}
    rp = collections.defaultdict(int)
    for r in landed:
        k = f"{r['src_region']}->{r['dst_region']}"
        rp[k] = max(rp[k], r['E'])
    ring = [r for r in landed if r['cls'] == 'COLL_RING']
    summ = dict(links=len(rows), landed_links=len(landed),
                E_hist=dict(sorted(collections.Counter(r['E'] for r in landed).items())),
                E_hist_full_cycle=dict(sorted(collections.Counter(r['E_full_cycle'] for r in landed).items())),
                window_fail=[r['link'] for r in landed if not r['window_ok']],
                D_raised=[r['link'] for r in landed if r['D'] != D],
                ring_ab=[{k: r[k] for k in ('link', 'stations', 'len_um', 'dL_tt', 'dL_ff', 'E', 'K', 'latency_half', 'latency_full')}
                         for r in ring])
    plan = dict(schema='opentallas.hbm_d4g.land_plan.v1', lane='HBM-LANDING/DCC+PRICE 10-18',
                status='MODEL pilot (no die STA yet): E/K re-derived from GEN2 die STA at TT+FF; relay_layer_d4f.py --land-plan '
                       'matches link "<src>-><dst>" (plan block names), else by_region_pair "<src region>-><dst region>" (max E), '
                       'else by_class E (max)',
                rule=__doc__, D=D, ckgen_xy=[round(x, 1) for x in ckxy],
                by_region_pair=dict(sorted(rp.items())),
                by_class={c: max([r['E'] for r in landed if r['cls'] == c], default=None) for c in per_class},
                per_class=per_class, summary=summ, links=rows)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'land_plan_d4g.json').write_text(json.dumps(plan, indent=1) + '\n')
    print(json.dumps(dict(summary={k: v for k, v in summ.items() if k != 'ring_ab'},
                          ring_ab=summ['ring_ab'][:8],
                          per_class={c: {k: v[k] for k in ('landed_links', 'links', 'delta_half_bw', 'delta_full_bw', 'E_hist')}
                                     for c, v in per_class.items() if v['landed_links']}), indent=1))


if __name__ == '__main__':
    main()
