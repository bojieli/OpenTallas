#!/usr/bin/env python3
"""VM bank <-> LG tap leaf face search (GEO-H, 2026-10-15).

Inputs are actual views only: the CLOSED LG leaf LEF (ot_hbm_vm_lg_static_bank, R0 only:
no SYMMETRY declared) and the actual RG7/WG3 bank BTerm centres read back from ODB.
The bank kit is unclosed (gate WARN), so its pin plan may still be assigned top-down.

Candidates are pure slot permutations of the bank's existing physical pin groups (same
per-face counts, same tracks, zero area): the logical LG link (RG0+WG0, 556 bits) is moved
onto slots now held by another group. For each plan the LG0 leaf origin is searched on a
0.216 um grid outside the bank with >= 5.4 um clearance; LG1/LG2 abut far(W)->near(E)
in R0 and their cost is plan-independent. Metric: sum over bits of pin-centre Manhattan
distance (bit-um) and the maximum bit. No timing/congestion/route claim.
"""
import argparse, csv, hashlib, json, re
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def lef_pins(path):
    t = Path(path).read_text()
    w, h = map(float, re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)', t).groups())
    if re.search(r'\bSYMMETRY\b', t): raise SystemExit('LEF declares SYMMETRY: extend search to flips')
    pins = {}
    for m in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n|$)', t, re.S):
        n, b = m.groups()
        if 'USE POWER' in b or 'USE GROUND' in b: continue
        a, c, d, e = map(float, re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', b).groups())
        pins[n] = ((a + d) / 2, (c + e) / 2)
    return (w, h), pins

def bank_pins(path):
    d = json.loads(Path(path).read_text()); W, H = d['die'][2], d['die'][3]; pins = {}
    for n, _, use, _, shapes in d['bterms']:
        if n in ('VDD', 'VSS'): continue
        _, (a, b, c, e) = shapes[0]; pins[n] = ((a + c) / 2, (b + e) / 2)
    return (W, H), pins

def group(pins, base):
    out = {}
    for n, xy in pins.items():
        m = re.fullmatch(re.escape(base) + r'(?:\[(\d+)\])?', n)
        if m: out[int(m[1] or 0)] = xy
    return [out[k] for k in sorted(out)]

LINK = [('near_rq', 'rq'), ('near_wq', 'wq'), ('near_rr', 'rr'), ('near_w_done', 'wq_done')]

def plan_pairs(bp, lp, rg, wg):
    names = {'rq': f'rq{rg}', 'rr': f'rr{rg}', 'wq': f'wq{wg}', 'wq_done': f'wq_done{wg}'}
    pairs = []
    for lg_port, b in LINK:
        bs, ls = group(bp, names[b]), group(lp, lg_port)
        if len(bs) != len(ls): raise SystemExit(f'width mismatch {names[b]} {len(bs)} vs {lg_port} {len(ls)}')
        pairs += list(zip(bs, ls))
    return pairs

def cost(pairs, ox, oy):
    ds = [abs(bx - lx - ox) + abs(by - ly - oy) for (bx, by), (lx, ly) in pairs]
    return sum(ds), max(ds)

def search(pairs, bank, leaf, clr=5.4, grid=0.216, span=500.0):
    W, H = bank; w, h = leaf; best = None
    # coarse 10.8 um scan, then 0.216 refinement around the best
    def legal(ox, oy):
        return ox + w + clr <= 0 or ox >= W + clr or oy + h + clr <= 0 or oy >= H + clr
    def scan(xs, ys):
        nonlocal best
        for ox in xs:
            for oy in ys:
                if not legal(ox, oy): continue
                s, m = cost(pairs, ox, oy)
                if best is None or s < best[0] - 1e-9: best = (s, m, ox, oy)
    st = 10.8; rng = lambda a, b, s: [round(a + i * s, 3) for i in range(int((b - a) / s) + 1)]
    scan(rng(-w - span, W + span, st), rng(-h - span, H + span, st))
    for _ in range(2):
        _, _, bx, by = best
        scan(rng(bx - st, bx + st, grid * 5), rng(by - st, by + st, grid * 5))
    _, _, bx, by = best
    scan(rng(bx - 1.08, bx + 1.08, grid), rng(by - 1.08, by + 1.08, grid))
    s, m, ox, oy = best
    return dict(sum_bit_um=round(s, 3), max_bit_um=round(m, 3), lg0_origin_um=[ox, oy])

def chain(lp, leaf, clr=5.4):
    far = [group(lp, n) for n in ('far_rq', 'far_wq', 'far_rr', 'far_w_done')]
    near = [group(lp, n) for n in ('near_rq', 'near_wq', 'near_rr', 'near_w_done')]
    ox = -(leaf[0] + clr)  # next leaf directly west, same row
    ds = [abs(fx - (nx + ox)) + abs(fy - ny) for F, N in zip(far, near) for (fx, fy), (nx, ny) in zip(F, N)]
    return dict(per_hop_sum_bit_um=round(sum(ds), 3), per_hop_max_bit_um=round(max(ds), 3), bits=len(ds))

def face(xy, W, H):
    x, y = xy; d = {'W': x, 'E': W - x, 'S': y, 'N': H - y}; return min(d, key=d.get)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lg-lef', required=True); ap.add_argument('--bank-pins', required=True)
    ap.add_argument('--out', required=True); a = ap.parse_args()
    leaf, lp = lef_pins(a.lg_lef); bank, bp = bank_pins(a.bank_pins)
    plans = {'P0_current_RG0_WG0': (0, 0)}
    for rg in range(7):
        for wg in range(3):
            if (rg, wg) != (0, 0): plans[f'P_RG{rg}_WG{wg}_slots'] = (rg, wg)
    res = {}
    for name, (rg, wg) in plans.items():
        pr = plan_pairs(bp, lp, rg, wg)
        faces = sorted({face(b, *bank) for b, _ in pr})
        r = search(pr, bank, leaf); r.update(bank_slot_groups=[f'rq{rg}', f'rr{rg}', f'wq{wg}', f'wq_done{wg}'], bank_faces=faces, bits=len(pr))
        res[name] = r
    base = res['P0_current_RG0_WG0']['sum_bit_um']
    for r in res.values(): r['delta_vs_current_pct'] = round(100 * (r['sum_bit_um'] - base) / base, 2)
    ranked = sorted(res, key=lambda k: res[k]['sum_bit_um'])
    out = dict(schema='opentallas.hbm.geo.vm_lg_face_search.v1',
               inputs=dict(lg_lef=a.lg_lef, lg_lef_sha256=sha(a.lg_lef), bank_pins=a.bank_pins, bank_pins_sha256=sha(a.bank_pins)),
               lg_leaf_um=leaf, bank_um=bank, lg_orientation='R0 only (no SYMMETRY)', clearance_um=5.4,
               lg_chain_hop=chain(lp, leaf), plans=res, ranked=ranked,
               scope='per bank; x8 banks x4 quadrants for die totals; pin-centre Manhattan, no route/timing/PG claim')
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    for k in ranked[:8] + ['P0_current_RG0_WG0']: print(k, res[k])
    print('chain', out['lg_chain_hop'])

if __name__ == '__main__': main()
