#!/usr/bin/env python3
"""S-ELEM-C 2026-10-15: top-down physical plan of one Engram MIX copy cluster (ot_s81_engram_mixq) and of
dsfd_engram_mix4_c (2 x 2 clusters + top strip), from the v21 leaf outlines.  Rows run S -> N with the data flow
(inputs on S faces, outputs on N faces): add8 | shell | mul4 | mul4 | chunk8 | chunk8+sum | norm/gate/control.
Reports the footprint and the pin-face-centroid Manhattan reach of every seam (limit 500 um a registered stage)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[2]
P = json.loads((R / 'physical/s81_die_pins/v21_engram_arithmetic/receipt.json').read_text())
O = {m['master'].replace('ot_s81_engram_', ''): m['outline_um'] for m in P['masters']}
# parent-root leaves without a contract yet: sized from mapped area (summary.json) and pin count (0.096 um a bit, 1 face per bus)
O['shell'] = [453.6, 43.2]      # 2,364 um2 cells; S face VM 20R/4W side ~3.3k bits, N face h/kv/w 3,072 + result 1,024 + eps/scale 64
O['control'] = [90.72, 43.2]    # 1,960 um2 cells -> util 0.50
CH = 10.8                       # channel between leaves (>= 10 um, pin escape + hold buffers)
# columns c = 0..3: mul4 groups 2c (row mul4a) and 2c+1 (row mul4b) feed chunk8 (r, c) r = 0,1 (row chunkA, two per
# column) and r = 2 (row chunkB); the three sums (r = h, k, d) sit at the centre of chunkB; add8 c (h lanes of groups
# 2c, 2c+1) below the shell in its column.
# (a variant with the scalar row between the mul4 rows was measured: sum->control 754 / a_gate 640 / status 541 um,
# no better; the scalar row stays on top, next to the sums, and the two long control edges get relay stages)
ROWS = [('add8', ['add8'] * 4), ('shell', ['shell']), ('mul4a', ['mul4'] * 4), ('mul4b', ['mul4'] * 4),
        ('chunkA', ['chunk8'] * 8), ('chunkB', ['chunk8', 'chunk8', 'sum', 'sum', 'sum', 'chunk8', 'chunk8']),
        ('top', ['norm', 'signed_sqrt', 'control', 'sigmoid', 'norm'])]


def place():
    boxes = []; y = 0.0; W = 0.0
    widths = [sum(O[m][0] for m in r) + CH * (len(r) - 1) for _, r in ROWS]
    W = max(widths)
    for (tag, r), w in zip(ROWS, widths):
        x = (W - w) / 2; h = max(O[m][1] for m in r)
        for i, m in enumerate(r):
            boxes.append(dict(row=tag, master=m, i=i, x=round(x, 3), y=round(y, 3), w=O[m][0], h=O[m][1])); x += O[m][0] + CH
        y += h + CH
    return boxes, round(W, 3), round(y - CH, 3)


def c(b, f, toward=None):
    x = b['x'] + b['w'] / 2
    if toward is not None and b['master'] == 'shell':      # the shell's pins for a leaf sit under / over that leaf
        x = min(max(toward['x'] + toward['w'] / 2, b['x'] + 1), b['x'] + b['w'] - 1)
    return (x, b['y'] + (b['h'] if f == 'N' else 0))


def main():
    boxes, W, H = place()
    by = lambda tag: [b for b in boxes if b['row'] == tag]
    sh = by('shell')[0]; ma, mb = by('mul4a'), by('mul4b'); mul = [ma[g // 2] if g % 2 == 0 else mb[g // 2] for g in range(8)]
    cA = by('chunkA'); cB = [b for b in by('chunkB') if b['master'] == 'chunk8']
    chk = {(r, cc): (cA[2 * cc + r] if r < 2 else cB[cc]) for r in range(3) for cc in range(4)}; ch = list(chk.values())
    sm = [b for b in by('chunkB') if b['master'] == 'sum']; top = by('top'); ad = by('add8')
    ctl = [b for b in top if b['master'] == 'control'][0]; sig = [b for b in top if b['master'] == 'sigmoid'][0]
    nrm = [b for b in top if b['master'] == 'norm']; ssq = [b for b in top if b['master'] == 'signed_sqrt'][0]
    d = lambda a, b: round(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
    seams = {}
    seams['shell.h/kv/w -> mul4 (S)'] = max(d(c(sh, 'N', m), c(m, 'S')) for m in mul)
    seams['shell.h/kv -> add8 (S, h + value)'] = max(d(c(sh, 'S', a), c(a, 'N')) for a in ad)
    seams['add8.y -> shell.result'] = max(d(c(a, 'N'), c(sh, 'S', a)) for a in ad)
    seams['mul4.hh/kk/dot -> chunk8'] = max(d(c(mul[2 * cc + j], 'N'), c(chk[(r, cc)], 'S')) for r in range(3) for cc in range(4) for j in range(2))
    seams['chunk8.sum -> sum'] = max(d(c(chk[(r, cc)], 'N'), c(sm[r], 'S')) for r in range(3) for cc in range(4))
    seams['add8 c <- h of mul4 cols (shell N->S fold) / add8 -> shell'] = max(d(c(a, 'N'), c(sh, 'S', a)) for a in ad)
    seams['sum.y -> norm / control'] = max(d(c(s, 'N'), c(t, 'S')) for s in sm for t in nrm + [ctl])
    seams['control.g_x -> signed_sqrt -> sigmoid -> control'] = max(d(c(ctl, 'N'), c(ssq, 'S')), d(c(ssq, 'N'), c(sig, 'S')), d(c(sig, 'N'), c(ctl, 'S')))
    seams['control.a_gate -> add8 (gate, 32 b)'] = max(d(c(ctl, 'N'), c(a, 'S')) for a in ad)
    seams['shell.iv/phase -> mul4 + add8 (1-bit broadcast)'] = max(max(d(c(sh, 'N', m), c(m, 'S')) for m in mul), max(d(c(sh, 'S', a), c(a, 'N')) for a in ad))
    seams['mvalid[0] -> 12 chunk8 + 3 sum (as written)'] = max(d(c(mul[0], 'N'), c(x, 'S')) for x in ch + sm)
    seams['mvalid[2c] (local) -> chunk8 (r, c)'] = max(d(c(mul[2 * cc], 'N'), c(chk[(r, cc)], 'S')) for r in range(3) for cc in range(4))
    seams['leaf valids/faults -> control (1-bit)'] = max(d(c(b, 'N'), c(ctl, 'S')) for b in mul + ad + nrm + sm)
    seams['control -> sums/norms (go via shell? no: rv/rhh in)'] = max(d(c(s, 'N'), c(ctl, 'S')) for s in sm)
    over = {k: v for k, v in seams.items() if v > 500}
    TOP = 21.6
    mix4 = dict(w=round(2 * W + CH, 3), h=round(2 * H + CH + TOP + CH, 3))
    mix4['area_mm2'] = round(mix4['w'] * mix4['h'] / 1e6, 3)
    leaf_area = sum(b['w'] * b['h'] for b in boxes)
    out = dict(schema='opentallas.s81.mix4.phys_plan.v1', status='PLAN (leaf outlines exact v21; shell/control outlines estimated; no parent route)',
               cluster=dict(w=W, h=H, area_mm2=round(W * H / 1e6, 4), leaf_area_mm2=round(leaf_area / 1e6, 4), leaves=len(boxes), roots=len(boxes) + 1),
               mix4=mix4, mix4_layout='2 x 2 clusters (cluster q at (q%2, q//2)), top strip ck[0] (descriptor/VM pin stage/V broadcast BC=2) between the cluster rows; VM 20R/4W face = the W edge of the strip',
               seams_um=seams, seams_over_500=over, boxes=boxes)
    p = R / 'results/arch/s81_mix4_phys_plan_1015'; p.mkdir(exist_ok=True); (p / 'plan.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'boxes'}, indent=1))


if __name__ == '__main__':
    main()
