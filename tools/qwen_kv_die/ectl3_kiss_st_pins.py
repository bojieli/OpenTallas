#!/usr/bin/env python3
"""S-KVASTK 2026-10-18: exact pin plan (io_tcl) of the wires-only ECTL frame cluster qkd_ectl3_kiss_st (die master qkd_ectlk).

Children (hard views, on the 43.2-um lattice, bottoms aligned at y 43.2 so A.rs_o / B.rs_i and B.x_i / C.x_b keep their
grant y):  A qkd_static_ectla_kiss (k3, 172.8 x 194.4) at x 43.2 | B qkd_ectl_b_tp8_direct (pg16, 254.88 x 129.6) at
x 259.2 | C qkd_ectl_c_st (138.24 x 129.6) at x 561.6.  Every frame pin is the straight projection of the child pin it
feeds (same layer, same track: the 43.2 lattice is a multiple of every track pitch), so the frame wires are straight
stubs.  Where a child face is denser than the 6-pins/um face rule (C's t0_q / t1_q 8.7/um, C's si / so 9/um) the run is
spread in bit order to <= 5.2/um with the least squared displacement (isotonic regression).  Faces (die contract
kv_static_die._ECTL_FACE): S t0 e0 e1 s0 s1, N t1 e2 e3 s2 s3, E si so, W the rest except rst_n / cfg (S, under B: they reach A, B and C); the three clock ENTRIES ck[0..2] sit on
the N face straight above each child's ck pin (entry wire ~44 / 108 / 108 um).
Usage: ectl3_kiss_st_pins.py OUT.tcl [OUT_ranges.json]"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'physical/ref_tile'
VIEWS = dict(A=RT / 'qkd_static_ectla_k3/views/qkd_static_ectla_kiss/qkd_static_ectla_kiss.lef',
             B=RT / 'qkd_ectl_b_tp8_direct_pg16/views/qkd_ectl_b_tp8_direct/qkd_ectl_b_tp8_direct.lef',
             C=RT / 'qkd_ectl_c_st/views/qkd_ectl_c_st/qkd_ectl_c_st.lef')
ORG = dict(A=(43.2, 43.2), B=(259.2, 43.2), C=(561.6, 43.2))
W, H = 725.76, 261.36
PITCH = {'M4': 0.048, 'M5': 0.048, 'M6': 0.064}
OFF = {'M4': 0.012, 'M5': 0.012, 'M6': 0.016}
MINP = 0.192                 # 4 M4 / M5 tracks: 5.2 pins/um


def lef_pins(path):
    t = path.read_text()
    out = {}
    for pm in re.finditer(r'^  PIN (\S+)\s*$(.*?)^  END \1\s*$', t, re.M | re.S):
        n = pm.group(1)
        if n in ('VDD', 'VSS'):
            continue
        r = [float(v) for v in re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', pm.group(2)).groups()]
        out[n] = (re.search(r'LAYER\s+(\S+)', pm.group(2)).group(1), (r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    return out


P = {k: lef_pins(v) for k, v in VIEWS.items()}


def child(c, pin):
    lay, x, y = P[c][pin]
    return lay, x + ORG[c][0], y + ORG[c][1]


def bits(name, n):
    return [f'{name}[{i}]' for i in range(n)]


def spread(d, p=MINP, hi=None):
    """ordered positions >= p apart, least squares to d (pool-adjacent-violators on d_i - i p)"""
    z = [v - i * p for i, v in enumerate(d)]
    blocks = []                                  # [sum, count]
    for v in z:
        blocks.append([v, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, c = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += c
    out = []
    for s, c in blocks:
        out += [s / c] * c
    x = [v + i * p for i, v in enumerate(out)]
    if hi is not None and x[-1] > hi:
        x = [v - (x[-1] - hi) for v in x]
    return x


def snap(v, lay):
    return round(OFF[lay] + round((v - OFF[lay]) / PITCH[lay]) * PITCH[lay], 4)


pins = {}                                        # frame pin -> (layer, face, coordinate along the face)


def put(fp, lay, face, a):
    pins[fp] = (lay, face, a)


# ---- S / N: t0 = {q0, c0[15:4], b0, a0, c0[3:0]}; t1 likewise -------------------------------------------------------
for t, side, q, cl, row in (('t0', 'S', 't0_q', 't0_cl', 't0_row'), ('t1', 'N', 't1_q', 't1_cl', 't1_row')):
    src = ([('B', f'{cl}[{i}]') for i in range(4)] + [('A', f'{row}[{i}]') for i in range(512)]
           + [('B', f'{row}[{i}]') for i in range(512)] + [('B', f'{cl}[{i}]') for i in range(4, 16)]
           + [('C', f'{q}[{i}]') for i in range(519)])
    ab = [(f'{t}[{i}]',) + child(c, p) for i, (c, p) in enumerate(src) if c != 'C']
    for fp, lay, x, _ in ab:
        put(fp, lay, side, x)
    ex = ('e0', 'e1', 's0', 's1') if side == 'S' else ('e2', 'e3', 's2', 's3')
    cs = [(f'{t}[{1040 + i}]',) + child('C', f'{q}[{i}]') for i in range(519)]
    for e in ex:
        n = 16 if e[0] == 'e' else 34
        cs += [(f'{e}[{i}]',) + child('C', f'{e}[{i}]') for i in range(n)]
    cs.sort(key=lambda r: r[2])
    hi = None
    if side == 'N':
        hi = child('C', 'ck')[1] - 1.0          # keep C's run left of the C clock entry
    xs = spread([r[2] for r in cs], hi=hi)
    for r, x in zip(cs, xs):
        put(r[0], r[1], side, x)
for i, c in enumerate('ABC'):
    lay, x, _ = child(c, 'ck')
    put(f'ck[{i}]', lay, 'N', x)

# ---- W: A's landing words straight across; A's S-face control words below A ---------------------------------------
for n, (lay, x, y) in P['A'].items():
    base = re.sub(r'\[\d+\]$', '', n)
    if base.startswith(('req_', 'rsp_')):
        put(n, lay, 'W', y + ORG['A'][1])
# rst_n / cfg feed A, B AND C: on the S face straight under B's own rst_n / cfg pins (frame x ~380), so every leg is
# <= ~380 um (gate 1 f1, W-face pins: cfg -> C 688 um > 500 um reach)
for n in ['rst_n'] + bits('cfg', 5):
    lay, x, _ = child('B', n)
    put(n, lay, 'S', x)
ctl = ['kgo'] + bits('epoch', 16) + bits('layer', 6) + ['fault']
for i, n in enumerate(ctl):
    put(n, 'M4', 'W', 8.0 + 0.96 * i)          # y 8 .. 36 (1 pin / 0.96 um), under A's landing face

# ---- E: C's si / so spread in bit order -------------------------------------------------------------------------------
es = [(f'si[{i}]',) + child('C', f'si[{i}]') for i in range(633)] + [(f'so[{i}]',) + child('C', f'so[{i}]') for i in range(413)]
es.sort(key=lambda r: r[3])
for r, y in zip(es, spread([r[3] for r in es])):
    put(r[0], r[1], 'E', y)

# ---- emit -------------------------------------------------------------------------------------------------------------
lines = ['# qkd_ectl3_kiss_st: exact pin plan, S-KVASTK 2026-10-18 (tools/qwen_kv_die/ectl3_kiss_st_pins.py). Do not edit; regenerate.']
used = {}
ranges = {}
for fp in sorted(pins):
    lay, face, a = pins[fp]
    a = snap(a, lay)
    key = (face, lay, a)
    assert key not in used, f'{fp} collides with {used[key]} at {key}'
    used[key] = fp
    if face in 'NS':
        assert 0.5 < a < W - 0.5, (fp, a)
        loc, sz = f'{a:.4f} {0.042 if face == "S" else H - 0.042:.4f}', '0.024 0.084' if lay != 'M6' else '0.032 0.084'
    else:
        assert 0.5 < a < H - 0.5, (fp, a)
        loc, sz = f'{0.042 if face == "W" else W - 0.042:.4f} {a:.4f}', '0.084 0.024' if lay != 'M6' else '0.084 0.032'
    lines.append(f'place_pin -pin_name {{{fp}}} -layer {lay} -location {{{loc}}} -pin_size {{{sz}}} -force_to_die_boundary')
    b = re.sub(r'\[\d+\]$', '', fp)
    r = ranges.setdefault(b, [face, a, a])
    r[1], r[2] = min(r[1], a), max(r[2], a)
Path(sys.argv[1]).write_text('\n'.join(lines) + '\n')
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps({k: v for k, v in sorted(ranges.items())}, indent=1) + '\n')
dens = {}
for (face, lay, a), fp in used.items():
    dens.setdefault(face, []).append(a)
for f, v in sorted(dens.items()):
    v.sort()
    worst = max(sum(1 for u in v if lo <= u < lo + 10) for lo in [x for x in v]) / 10
    print(f'{f}: {len(v)} pins {v[0]:.1f}..{v[-1]:.1f} um, densest 10-um window {worst:.1f}/um')
print(f'{len(pins)} pins')
