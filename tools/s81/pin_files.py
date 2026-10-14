#!/usr/bin/env python3
"""S81 die: ASSIGNED pin files, one per generated (unclosed) master (owner 2026-10-13 18:22: top-down pin assignment).

The die generator places every pin of a master that has no closed view (tools/dsrom_s81_fulldie.py _faces_r8: each face
from the neighbour or relay it meets; `--pin-align` puts facing pins straight across).  This tool turns the generator's
LEF of a die case into the form the tile kits consume:

  pin_files.py write ELEMENTS.lef PLAN.json.gz OUT_DIR [--case NAME]
      OUT_DIR/<master>.json   ports: {port: {face, layer, bits, at: [first centre um, pitch um] | [centres...], depth}}
                              (offset along the face from its left / bottom end, master frame), outline, instances, and
                              per port the peer master.port(s) it meets and the pin-to-pin length range in the die plan
      OUT_DIR/INDEX.json      master -> file, pins, instances
  pin_files.py tcl OUT_DIR/<master>.json [--scalar p1,p2]   place_pin lines (ref_tile spec "io_tcl"); --scalar names the
                              1-bit ports the tile RTL declares as scalars (the die LEF names them p[0])

Source of the positions: the generator's neighbour rule, NOT global-route guides (the c6p routed database was deleted
after collection; the next routed die case can refine an assignment, which then changes with a contract revision).
"""
from __future__ import annotations
import gzip, json, re, sys
from collections import defaultdict
from pathlib import Path


def parse_lef(text):
    out = {}
    for mm in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1', text, re.S | re.M):
        name, body = mm.group(1), mm.group(2)
        sm = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
        w, h = float(sm.group(1)), float(sm.group(2))
        pins = []
        for pm in re.finditer(r'PIN (\S+)\n.*?LAYER (\S+) ;\s*\n\s*RECT ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ;', body, re.S):
            pins.append((pm.group(1), pm.group(2), tuple(float(pm.group(i)) for i in range(3, 7))))
        out[name] = (w, h, pins)
    return out


def face_of(w, h, r):
    d = {'W': r[0], 'S': r[1], 'E': w - r[2], 'N': h - r[3]}
    return min(d, key=d.get)


def write(lef, plan, outdir, case):
    L = parse_lef(Path(lef).read_text())
    p = json.load(gzip.open(plan))
    cnt = defaultdict(int)
    mst = {}
    for i in p['insts']:
        cnt[i[1]] += 1; mst[i[0]] = i[1]
    peers = defaultdict(lambda: defaultdict(lambda: [1e9, 0.0, 0]))
    for h in p['hops']:
        a, b = mst.get(h[3]), mst.get(h[5])
        if a is None or b is None:
            continue
        pa, pb = h[4].split('[')[0], h[6].split('[')[0]
        lo, hi = h[-2], h[-1]
        if lo is None or hi is None:
            continue
        for me, port, other in ((a, pa, f'{b}.{pb}'), (b, pb, f'{a}.{pa}')):
            r = peers[(me, port)][other]
            r[0], r[1], r[2] = min(r[0], lo), max(r[1], hi), r[2] + 1
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, (w, h, pins) in sorted(L.items()):
        if name not in cnt:
            continue
        groups = defaultdict(list)
        for pn, ly, r in pins:
            m_ = re.match(r'^(.*)\[(\d+)\]$', pn)
            base, bit = (m_.group(1), int(m_.group(2))) if m_ else (pn, 0)
            f = face_of(w, h, r)
            c = (r[1] + r[3]) / 2 if f in 'EW' else (r[0] + r[2]) / 2
            depth = (r[2] - r[0]) if f in 'EW' else (r[3] - r[1])
            groups[base].append((bit, f, ly, round(c, 3), round(depth, 3)))
        ports = {}
        for base, g in sorted(groups.items()):
            g.sort()
            assert [b for b, *_ in g] == list(range(len(g))), (name, base)
            faces, lys = {x[1] for x in g}, {x[2] for x in g}
            if len(faces) != 1 or len(lys) != 1:      # a port on several faces / layers: explicit per-bit records
                ports[base] = dict(bits=len(g), per_bit=[[x[1], x[2], x[3], x[4]] for x in g], uniform=False)
                continue
            cs = [x[3] for x in g]
            st = round(cs[1] - cs[0], 3) if len(cs) > 1 else 0.0
            uni = all(abs(cs[i + 1] - cs[i] - st) < 2e-3 for i in range(len(cs) - 1))
            ports[base] = dict(face=g[0][1], layer=g[0][2], bits=len(g), at=[cs[0], st] if uni else cs, uniform=uni, depth=g[0][4],
                               meets={k: dict(um=[round(v[0], 1), round(v[1], 1)], hops=v[2]) for k, v in sorted(peers[(name, base)].items())})
        rec = dict(schema='opentallas.s81.assigned_pins.v1', master=name, case=case, outline_um=[w, h], instances=cnt[name],
                   rule='die-assigned pins (owner 2026-10-13): the tile kit consumes this file (pin_files.py tcl -> spec io_tcl); '
                        'a pin that cannot be built is ONE request in el1011-s81die.log for the next daily contract revision',
                   source='generator neighbour rule (tools/dsrom_s81_fulldie.py --pin-align); not from global-route guides', ports=ports)
        (out / f'{name}.json').write_text(json.dumps(rec, separators=(',', ':')) + '\n')
        index[name] = dict(file=f'{name}.json', pins=len(pins), ports=len(ports), instances=cnt[name])
    (out / 'INDEX.json').write_text(json.dumps(dict(case=case, masters=index), indent=1) + '\n')
    print(len(index), 'masters', sum(v['pins'] for v in index.values()), 'pins ->', out)


def tcl(path, scalar=()):
    r = json.loads(Path(path).read_text())
    w, h = r['outline_um']
    print(f"# assigned pins of {r['master']} ({r['case']}): generated by tools/s81/pin_files.py tcl; do not edit")
    for port, s in r['ports'].items():
        if 'per_bit' in s:
            rows = [(f_, ly_, c_, d_) for f_, ly_, c_, d_ in s['per_bit']]
        else:
            cs_ = s['at'] if not s['uniform'] else [s['at'][0] + i * s['at'][1] for i in range(s['bits'])]
            rows = [(s['face'], s['layer'], c_, s['depth']) for c_ in cs_]
        for i, (face, layer, c, d) in enumerate(rows):
            x, y = {'W': (d / 2, c), 'E': (w - d / 2, c), 'S': (c, d / 2), 'N': (c, h - d / 2)}[face]
            sz = (d, 0.024) if face in 'EW' else (0.024, d)
            nm = port if port in scalar else f'{port}[{i}]'
            print(f"place_pin -pin_name {{{nm}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz[0]:.3f} {sz[1]:.3f}}} -force_to_die_boundary")


if __name__ == '__main__':
    if len(sys.argv) >= 5 and sys.argv[1] == 'write':
        write(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[sys.argv.index('--case') + 1] if '--case' in sys.argv else 'v17')
    elif len(sys.argv) >= 3 and sys.argv[1] == 'tcl':
        tcl(sys.argv[2], tuple(sys.argv[sys.argv.index('--scalar') + 1].split(',')) if '--scalar' in sys.argv else ())
    else:
        sys.exit(__doc__)
