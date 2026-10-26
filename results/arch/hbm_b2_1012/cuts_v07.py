"""SPEC v0.7 cut check: the B2 die (r25gqn_b2) with the v9 ring / COLL star, HC x lanes v0.6 (2 x 278 a quarter) vs
v0.7 (8 x 150 a quarter). Same counting and capacity model as results/arch/hbm_die_phy_study_1012/cuts.py, plus cuts
across every slice -> HC quarter segment (perpendicular, at the segment midpoint, window = the bounding box +-1 mm)."""
import sys, json, re, collections, copy, pathlib
R = pathlib.Path(__file__).resolve().parents[3]; sys.path.insert(0, str(R / 'tools'))
import hbm_accel_die_fp as F
DW, DH = 32984.288, 25980.528
TPU = {'M4': 1/0.048, 'M5': 1/0.048, 'M6': 1/0.064, 'M7': 1/0.064, 'M8': 1/0.080, 'M9': 1/0.080}
def model(vmap_bits, vmap_r_bits):
    v = copy.deepcopy(F.r25gq_b2()); b = v['vm_b2']
    b.update(ring_bits=2224, coll_tree=tuple(('coll', q) for q in ('SW', 'SE', 'NW', 'NE')), coll_bits=2130,
             vmap_bits=vmap_bits, vmap_r_bits=vmap_r_bits)
    return F.build(v)
def run(m, extra):
    I = {it.name: it for it in m['insts']}; blocks = [it for it in m['insts'] if it.w * it.h > 4e4]
    c = lambda n: (I[n].x + I[n].w / 2, I[n].y + I[n].h / 2)
    def covered(ax, cp, lo, hi):
        iv = sorted((max(lo, it.y), min(hi, it.y + it.h)) if ax == 'x' else (max(lo, it.x), min(hi, it.x + it.w))
                    for it in blocks if ((it.x < cp < it.x + it.w) if ax == 'x' else (it.y < cp < it.y + it.h)))
        t = 0; cur = None
        for a, b_ in (v for v in iv if v[1] > v[0]):
            if cur is None or a > cur[1]:
                if cur: t += cur[1] - cur[0]
                cur = [a, b_]
            else: cur[1] = max(cur[1], b_)
        return t + (cur[1] - cur[0] if cur else 0)
    def cap(ax, L, Lch):
        lo, hi = ('M6', 'M8') if ax == 'x' else ('M7', 'M9')
        return 0.75 * L * TPU[hi] + 0.75 * Lch * TPU[lo] + 0.5 * Lch * TPU['M4' if ax == 'x' else 'M5']
    cuts = {'X_centre_full': ('x', DW / 2, 0, DH), 'Y_centre_full': ('y', DH / 2, 0, DW)}
    for xc in (12000, 13000, 14000, 14400, 15000, 15500, 16000, 16500, 17000, 18000): cuts[f'x{xc/1000:g}_hub'] = ('x', xc, 10000, 16000)
    for yc in (10000, 11000, 12000, 12500, 13000, 14000, 14600, 15000, 16000): cuts[f'y{yc/1000:g}_hub'] = ('y', yc, 12000, 18000)
    cuts.update(extra(c))
    res = {}
    for cn, (ax, cp, lo, hi) in cuts.items():
        tot = 0; byf = collections.Counter()
        for bid, cls, bits, ends in m['buses']:
            pts = [c(e[0]) for e in ends if e[0] in I]
            if len(pts) < 2: continue
            segs = list(zip(pts, pts[1:])) if len(pts) <= 2 else [(pts[0], p) for p in pts[1:]]
            for (x1, y1), (x2, y2) in segs:
                a1, a2, o1, o2 = (x1, x2, y1, y2) if ax == 'x' else (y1, y2, x1, x2)
                if min(a1, a2) < cp < max(a1, a2) and max(min(o1, o2), lo) <= min(max(o1, o2), hi) + 1e-9:
                    tot += bits; byf[re.sub(r'_\d+(_\d+)?$', '', bid)[:22]] += bits
        L = hi - lo; u = cap(ax, L, L - covered(ax, cp, lo, hi))
        res[cn] = dict(axis=ax, pos_um=round(cp), span_um=[round(lo), round(hi)], bits=tot, usable=round(u), util=round(tot / u, 3),
                       vmap_bits=sum(b for f, b in byf.items() if f.startswith('vmap')), top=byf.most_common(5))
    return res
def hc_cuts(c):
    out = {}
    for q in ('SW', 'SE', 'NW', 'NE'):
        (x1, y1), (x2, y2) = c(f'hb_vms_{q}'), c(f'hb_hc_{q}')
        ax = 'x' if abs(x2 - x1) >= abs(y2 - y1) else 'y'
        if ax == 'x': out[f'vmap_{q}_x'] = ('x', (x1 + x2) / 2, min(y1, y2) - 1000, max(y1, y2) + 1000)
        else: out[f'vmap_{q}_y'] = ('y', (y1 + y2) / 2, min(x1, x2) - 1000, max(x1, x2) + 1000)
    return out
if __name__ == '__main__':
    out = {}
    for tag, vb, vr in (('v06', 556, 4), ('v07', 1200, 16)):
        m = model(vb, vr); I = {it.name: it for it in m['insts']}
        out[tag] = run(m, hc_cuts)
        out[tag + '_ends'] = {q: [[round(I[n].x), round(I[n].y), round(I[n].w), round(I[n].h)] for n in (f'hb_vms_{q}', f'hb_hc_{q}')]
                              for q in ('SW', 'SE', 'NW', 'NE')}
    for k in out['v07']:
        a, b = out['v06'][k], out['v07'][k]
        print(f"{k:16s} {a['bits']:7d} {a['util']:6.3f} -> {b['bits']:7d} {b['util']:6.3f}  vmap {b['vmap_bits']:5d}")
    print(json.dumps(out['v07_ends']))
    json.dump(out, open(pathlib.Path(__file__).with_name('cuts_v07.json'), 'w'), indent=1)
