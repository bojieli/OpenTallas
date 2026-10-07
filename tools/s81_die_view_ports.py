#!/usr/bin/env python3
"""S81 die-glue views: port records of generator masters (CLAUDE S81-RERUN, 2026-10-06).

A die view of a generated master (forwarded-link stations dsfd_stnh_* / dsfd_stnv_*, the column FIFO dsfd_cfifo, the
ck relays dsfd_lkck_*) is a routed block whose LEF has the SAME macro name, size, pin names, layers and positions as
the generator's master.  Same record format as tools/s81_ph/s81_ph_views.py (CLAUDE S81-PH), but the die variant is
given as tools/dsrom_s81_fulldie.py die options, so the record matches a recorded die case exactly.

  ports --s81-opts "<die options>" --die layer --out DIR --master M ...   ports.json, io_place.tcl, ports.svh
  check --ports DIR --die layer --master M --lef F                       a view LEF against the record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402

V5 = '--rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --pairs 2050 --link-fix'


def build(opts, die):
    S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(
        shlex.split(opts) + ['--gen', 'r8', '--die', die]))
    m = S.build()
    S.finalize_r8(m)
    return m


def records(m, die, opts, names):
    M = S.masters(m, 1)
    pw = S.port_widths(m, 1)
    pdir = m['pdir']
    gen = ROOT / 'tools/dsrom_s81_fulldie.py'
    out = {}
    for n in names:
        if n not in M:
            print(f'{n}: not a generated master of this die', file=sys.stderr)
            continue
        mst = M[n]
        wmap = {p: pw.get((n, p), 0) for p in mst.order}
        ports = {}
        for nm, layer, r in S.pin_rects(mst, 1, wmap):
            base, idx = re.match(r'^(.*)\[(\d+)\]$', nm).groups()
            p = ports.setdefault(base, dict(bits=0, layer=layer, pins=[]))
            p['bits'] = max(p['bits'], int(idx) + 1)
            p['pins'].append([nm, layer] + [round(v, 4) for v in r])
        for base, p in ports.items():
            d, b = pdir[n][base]
            assert b == p['bits'], (n, base, b, p['bits'])
            p['direction'] = d
            x0 = min(q[2] for q in p['pins']); y0 = min(q[3] for q in p['pins'])
            x1 = max(q[4] for q in p['pins']); y1 = max(q[5] for q in p['pins'])
            p['face'] = ('S' if y1 <= 0.5 else 'N' if y0 >= mst.h - 0.5 else 'W' if x1 <= 0.5
                         else 'E' if x0 >= mst.w - 0.5 else 'xy')
        insts = [it for it in m['insts'] if it.master == n]
        out[n] = dict(master=n, die=die, w_um=round(mst.w, 4), h_um=round(mst.h, 4), obs_top=mst.obs_top,
                      domain=insts[0].domain, instances=len(insts), orients=sorted({it.orient for it in insts}),
                      ports=ports, generator=dict(file='tools/dsrom_s81_fulldie.py',
                                                  sha256=hashlib.sha256(gen.read_bytes()).hexdigest(), options=opts))
    return out


def io_tcl(rec):
    L = [f"# {rec['master']} ({rec['die']} die): every die pin at the generator's position (tools/s81_die_view_ports.py)"]
    for p in sorted(rec['ports']):
        for nm, layer, x0, y0, x1, y1 in rec['ports'][p]['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {layer} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    return '\n'.join(L) + '\n'


def cmd_ports(a):
    m = build(a.s81_opts, a.die)
    recs = records(m, a.die, a.s81_opts, a.master)
    for n, rec in recs.items():
        d = Path(a.out) / a.die / n
        d.mkdir(parents=True, exist_ok=True)
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        (d / 'io_place.tcl').write_text(io_tcl(rec))
    print(json.dumps({k: (v['w_um'], v['h_um'], v['instances'], {p: (q['direction'], q['bits'], q['face'])
                                                                for p, q in v['ports'].items()}) for k, v in recs.items()}))


def parse_lef(path):
    t = Path(path).read_text()
    name = re.search(r'^MACRO (\S+)', t, re.M).group(1)
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t).groups())
    pins = {}
    for pm in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n)', t, re.S):
        body = pm.group(2)
        if 'USE POWER' in body or 'USE GROUND' in body:
            continue
        rects, cur = [], None
        for ln in body.split('\n'):
            mm = re.match(r'\s*LAYER (\S+)', ln)
            if mm:
                cur = mm.group(1)
            mr = re.match(r'\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', ln)
            if mr and cur:
                rects.append((cur, tuple(float(v) for v in mr.groups())))
        pins[pm.group(1)] = rects
    return name, w, h, pins


def cmd_check(a):
    rec = json.loads((Path(a.ports) / a.die / a.master / 'ports.json').read_text())
    name, w, h, pins = parse_lef(a.lef)
    prob = []
    if name != a.master:
        prob.append(f'macro {name}')
    if abs(w - rec['w_um']) > 0.01 or abs(h - rec['h_um']) > 0.01:
        prob.append(f'size {w} x {h} != {rec["w_um"]} x {rec["h_um"]}')
    gen = {nm: (ly, (x0 + x1) / 2, (y0 + y1) / 2) for p in rec['ports'].values() for nm, ly, x0, y0, x1, y1 in p['pins']}
    missing, extra = sorted(set(gen) - set(pins)), sorted(set(pins) - set(gen))
    moved = [nm for nm in set(gen) & set(pins)
             if not any(ly == gen[nm][0] and b[0] - .0125 <= gen[nm][1] <= b[2] + .0125 and b[1] - .0125 <= gen[nm][2] <= b[3] + .0125
                        for ly, b in pins[nm])]
    if missing or extra or moved:
        prob.append(f'{len(missing)} missing, {len(extra)} extra, {len(moved)} moved')
    print(json.dumps(dict(master=a.master, die=a.die, lef=str(a.lef), gen_pins=len(gen), view_pins=len(pins),
                          missing=missing[:8], extra=extra[:8], moved=sorted(moved)[:8], problems=prob,
                          verdict='MATCH' if not prob else 'MISMATCH'), indent=1))
    return 0 if not prob else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='mode', required=True)
    p = sp.add_parser('ports')
    p.add_argument('--s81-opts', default=V5)
    p.add_argument('--die', default='layer', choices=['layer', 'layer1', 'head'])
    p.add_argument('--out', required=True)
    p.add_argument('--master', nargs='+', required=True)
    c = sp.add_parser('check')
    c.add_argument('--die', default='layer')
    c.add_argument('--master', required=True)
    c.add_argument('--lef', required=True)
    c.add_argument('--ports', default=str(ROOT / 'physical/s81_die_views/ports'))
    a = ap.parse_args()
    return cmd_ports(a) if a.mode == 'ports' else cmd_check(a)


if __name__ == '__main__':
    sys.exit(main() or 0)
