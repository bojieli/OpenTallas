#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (attn): reduce a write_abstract_lef export of hfd_attn_tile (86 MB: every placed shape as
OBS) to the die-facing abstract the HBM die placement needs.

  signal pins   kept verbatim (positions as exported).
  PG pins       M7 stripes (the die PDN contract) plus every M8 strap of the tile (flow/pdn_p3.tcl M8 lattice and the
                flow/bridge_quad_m8.tcl stub bridges, dumped from the odb: --pg-m8 lines "NET x0 y0 x1 y1", merged per
                track), so the die drops M9 onto the tile's M8; M1/M2 rails and M4/M6 shapes stay internal.
  OBS           M1..M8: the outline minus every pin rect on that layer (bloated SPACE um inside the outline), as
                rectangles (x-slab sweep, equal slabs merged); M9: the quad footprints only (the quads' own M9 PG,
                internal to the tile in P3); RVTN/RVTP dropped.

    python3 reduce_lef.py IN.lef OUT.lef --quads 'x0,y0,x1,y1;...' --pg-m8 PG_M8.txt --size W H
"""
import argparse
import re
from collections import defaultdict

SPACE = 0.1


def rects_of(body):
    out, layer = [], None
    for ln in body.splitlines():
        m = re.match(r'\s*LAYER (\S+)', ln)
        if m:
            layer = m.group(1)
            continue
        m = re.match(r'\s*RECT\s+(?:MASK \d+ )?([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)', ln)
        if m:
            out.append((layer, tuple(float(v) for v in m.groups())))
    return out


def complement(w, h, holes):
    """rectangles covering [0,w]x[0,h] minus the union of holes (x0,y0,x1,y1)."""
    xs = sorted({0.0, w} | {min(max(v, 0.0), w) for hb in holes for v in (hb[0], hb[2])})
    slabs = []
    for a, b in zip(xs, xs[1:]):
        if b - a < 1e-6:
            continue
        cov = sorted((hb[1], hb[3]) for hb in holes if hb[0] < b - 1e-9 and hb[2] > a + 1e-9)
        free, y = [], 0.0
        for y0, y1 in cov:
            if y0 > y + 1e-9:
                free.append((y, min(y0, h)))
            y = max(y, y1)
        if y < h - 1e-9:
            free.append((y, h))
        slabs.append([a, b, tuple(free)])
    merged = []
    for s in slabs:
        if merged and merged[-1][2] == s[2] and abs(merged[-1][1] - s[0]) < 1e-9:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [(a, y0, b, y1) for a, b, fr in merged for y0, y1 in fr if y1 - y0 > 1e-6]


def fmt(v):
    return f'{v:.3f}'.rstrip('0').rstrip('.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--quads', required=True, help='x0,y0,x1,y1;... quad footprints (um, tile coordinates)')
    ap.add_argument('--pg-m8', required=True)
    ap.add_argument('--size', nargs=2, type=float, required=True, help='exact outline (the generator master size)')
    a = ap.parse_args()
    m8 = defaultdict(list)
    for ln in open(a.pg_m8):
        n, *v = ln.split()
        x0, y0, x1, y1 = (float(u) for u in v)
        m8[(n, y0, y1)].append([x0, x1])
    m8r = defaultdict(list)
    for (n, y0, y1), segs in m8.items():
        segs.sort()
        cur = segs[0]
        for s0, s1 in segs[1:]:
            if s0 <= cur[1] + 1e-6:
                cur[1] = max(cur[1], s1)
            else:
                m8r[n].append((cur[0], y0, cur[1], y1))
                cur = [s0, s1]
        m8r[n].append((cur[0], y0, cur[1], y1))
    t = open(a.inp).read()
    name = re.search(r'^MACRO (\S+)', t, re.M).group(1)
    w0, h0 = (float(v) for v in re.search(r'^\s*SIZE ([\d.]+) BY ([\d.]+) ;', t, re.M).groups())
    w, h = a.size
    assert abs(w - w0) < 0.006 and abs(h - h0) < 0.006, (w0, h0, w, h)
    t = re.sub(r'^(\s*)SIZE [\d.]+ BY [\d.]+ ;', lambda m: f'{m.group(1)}SIZE {fmt(w)} BY {fmt(h)} ;', t, count=1, flags=re.M)
    head = t[:t.index(f'MACRO {name}')]
    mac = t[t.index(f'MACRO {name}'):t.index(f'END {name}')]
    hdr = mac[:mac.index('  PIN ') if '  PIN ' in mac else mac.index('PIN ')]
    pins = re.findall(r'(\s*PIN (\S+)\n.*?\n\s*END \2\n)', mac, re.S)
    holes = defaultdict(list)
    out_pins, npg = [], defaultdict(int)
    for blk, pn in pins:
        if re.search(r'USE (POWER|GROUND)', blk):
            keep = [(ly, r) for ly, r in rects_of(blk) if ly == 'M7'] + [('M8', r) for r in m8r[pn]]
            for ly, r in keep:
                holes[ly].append(r)
                npg[ly] += 1
            use = re.search(r'USE (POWER|GROUND)', blk).group(1)
            body = '\n'.join(f'      LAYER {ly} ;\n        RECT {" ".join(fmt(v) for v in r)} ;' for ly, r in keep)
            out_pins.append(f'  PIN {pn}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n{body}\n    END\n  END {pn}\n')
        else:
            for ly, r in rects_of(blk):
                holes[ly].append(r)
            out_pins.append(blk.lstrip('\n') if blk.startswith('\n') else blk)
    obs = []
    for ly in ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'):
        hb = [(max(r[0] - SPACE, 0), max(r[1] - SPACE, 0), min(r[2] + SPACE, w), min(r[3] + SPACE, h))
              for r in holes.get(ly, [])]
        rs = complement(w, h, hb)
        obs.append(f'      LAYER {ly} ;\n' + ''.join(f'        RECT {" ".join(fmt(v) for v in r)} ;\n' for r in rs))
    quads = [tuple(float(v) for v in q.split(',')) for q in a.quads.split(';')]
    obs.append('      LAYER M9 ;\n' + ''.join(f'        RECT {" ".join(fmt(v) for v in q)} ;\n' for q in quads))
    text = (head + hdr + ''.join(out_pins) + '  OBS\n' + ''.join(obs) + '  END\n' + f'END {name}\n\nEND LIBRARY\n')
    open(a.out, 'w').write(text)
    print(f'{name}: {len(pins)} pins ({sum(1 for b, _ in pins if "USE POWER" in b or "USE GROUND" in b)} PG, '
          f'PG rects {dict(npg)}), OBS rects {sum(o.count("RECT") for o in obs)}, {len(text)} bytes')


if __name__ == '__main__':
    main()
