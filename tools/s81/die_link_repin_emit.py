#!/usr/bin/env python3
"""Turn a die_link_repin_search.py report into generator-consumable die-assigned pin records (screen candidate).

Output: one `opentallas.s81.assigned_pins.v1` JSON per re-pinned master, the format tools/dsrom_s81_fulldie.py
consumes through --assigned-pins-dir (':' overlay, first directory holding <master>.json wins; see
_assigned_record/_assigned_physical_pins).  Every port of the master's die port set (port_usage over the plan buses,
the generator's pdir) is written explicitly with exact per-bit [face, layer, coord, depth] taken from the search base
LEF, plus the master-frame translation of the search for the moved slices.  Ports absent from the die port set
(none expected) are reported, never written.

Fail-closed checks (master is refused, not written, on any failure):
  * master already has a die-assigned record in one of --existing-dirs (owned by another stream; overriding it in an
    overlay would drop that owner's clock/reset entries) -- unless listed in --allow-existing;
  * port aliases (non port[i] pin names), area / multi-face ports;
  * --target-plan (the next generation's construction plan, e.g. GEN18a pass1): every port of the record must exist
    there with the same width and the master outline must match (assert in _assigned_physical_pins);
  * coordinate range 0.012 .. edge-0.012 and no two pins of a face/layer closer than the base minimum pitch.
"""
import argparse, collections, gzip, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import pin_align as PA

SCHEMA = 'opentallas.s81.assigned_pins.v1'
_BIT = re.compile(r'^(.*)\[(\d+)\]$')


def rd(p):
    b = Path(p).read_bytes()
    return (gzip.decompress(b) if b[:2] == b'\x1f\x8b' else b).decode()


def pslice(port):
    mm = PA._PSL.match(port)
    return (mm.group(1), int(mm.group(2)), int(mm.group(3))) if mm else (port, None, None)


def die_ports(plan):
    """master -> port -> bits, exactly as dsrom_s81_fulldie.port_usage + finalize_r8 build pdir"""
    master = {r[0]: r[1] for r in plan['insts']}
    out = collections.defaultdict(dict)
    for bid, cls, bits, eps in plan['buses']:
        for inst, port in eps:
            if inst == 'TOP' or inst not in master:
                continue
            base, lo, hi = pslice(port)
            w = bits if lo is None else hi + 1
            m = master[inst]
            out[m][base] = max(out[m].get(base, 0), w)
    return out


def lef_rects(text, want):
    """macro -> (W, H, {pin: (layer, x0, y0, x1, y1)}) first rect of each pin"""
    out, m, pin, lay = {}, None, None, None
    for line in text.splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == 'MACRO':
            m = s[1] if s[1] in want else None
            if m:
                out[m] = [0, 0, {}]
        elif m is None:
            continue
        elif s[0] == 'SIZE':
            out[m][0], out[m][1] = float(s[1]), float(s[3])
        elif s[0] == 'PIN':
            pin = s[1]
        elif s[0] == 'LAYER' and pin:
            lay = s[1]
        elif s[0] == 'RECT' and pin and pin not in out[m][2]:
            x0, y0, x1, y1 = map(float, [x for x in s[1:] if x not in ('MASK', ';')][-4:])
            out[m][2][pin] = (lay, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        elif s[0] == 'END' and len(s) > 1 and s[1] == pin:
            pin = None
        elif s[0] == 'END' and len(s) > 1 and s[1] == m:
            m = None
    return out


def compact(bits, per):
    """uniform face/layer/depth and constant pitch -> the generator's {face, layer, at:[c0, pitch], uniform, depth}
    form (dsrom_s81_fulldie._assigned_physical_pins expands it to the same per-bit rects); else per_bit"""
    f, lay, c0, dep = per[0]
    if all(q[0] == f and q[1] == lay and q[3] == dep for q in per):
        pitch = round(per[1][2] - c0, 4) if bits > 1 else 0.0
        if all(abs(c0 + i * pitch - q[2]) < 5e-4 for i, q in enumerate(per)):
            return dict(face=f, layer=lay, bits=bits, at=[c0, pitch], uniform=True, depth=dep)
    return dict(bits=bits, per_bit=per)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', type=Path, required=True, help='die_link_repin_search.py output')
    ap.add_argument('--plan', type=Path, required=True, help='search base plan (same as the report)')
    ap.add_argument('--lef', type=Path, required=True, help='search base pins LEF (same as the report)')
    ap.add_argument('--target-plan', type=Path, help='next-generation plan to check port sets/widths against')
    ap.add_argument('--target-lef', type=Path, help='next-generation LEF to check outlines against')
    ap.add_argument('--existing-dirs', default='', help="':' list of assigned-pin dirs already in the overlay chain")
    ap.add_argument('--allow-existing', default='')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--case', default='geo-s')
    ap.add_argument('--masters', default='', help='only these masters (comma list)')
    ap.add_argument('--exclude', default='', help='skip these masters (comma list)')
    a = ap.parse_args()
    rep = json.loads(a.report.read_text())
    for p in (a.plan, a.lef):
        assert hashlib.sha256(p.read_bytes()).hexdigest() == rep['source_sha256'][p.name], (p, 'report built on another file')
    plan = json.loads(rd(a.plan))
    shifts = collections.defaultdict(dict)
    for r in rep['port_shifts_master_frame_um']:
        shifts[r['master']][r['port']] = r['shift_um']
    pdir = die_ports(plan)
    tdir = die_ports(json.loads(rd(a.target_plan))) if a.target_plan else None
    lef = lef_rects(rd(a.lef), set(shifts))
    tlef = lef_rects(rd(a.target_lef), set(shifts)) if a.target_lef else None
    existing = {p.stem for d in a.existing_dirs.split(':') if d for p in Path(d).glob('*.json')}
    allow = set(filter(None, a.allow_existing.split(',')))
    aliases = plan.get('port_aliases', {})
    a.out_dir.mkdir(parents=True, exist_ok=True)
    summary = dict(schema='opentallas.s81.die_link_repin_emit.v1', report=str(a.report),
                   report_sha256=hashlib.sha256(a.report.read_bytes()).hexdigest(), source_sha256=rep['source_sha256'],
                   tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   target_plan_sha256=hashlib.sha256(a.target_plan.read_bytes()).hexdigest() if a.target_plan else None,
                   written={}, refused={})
    only = set(filter(None, a.masters.split(','))); skip = set(filter(None, a.exclude.split(',')))
    for mst in sorted(shifts):
        if (only and mst not in only) or mst in skip:
            continue
        why = []
        if mst in existing and mst not in allow:
            why.append('existing die-assigned record in the overlay chain (owned elsewhere)')
        if aliases.get(mst):
            why.append('port aliases')
        W, H, rects = lef[mst]
        ports = pdir.get(mst, {})
        pin_shift = {}
        for port, d in shifts[mst].items():
            base, lo, hi = pslice(port)
            lo = 0 if lo is None else lo
            hi = ports.get(base, 0) - 1 if hi is None else hi
            for i in range(lo, hi + 1):
                pin_shift[f'{base}[{i}]'] = d
        rec_ports, bad = {}, []
        for port, bits in sorted(ports.items()):
            per = []
            for i in range(bits):
                nm = f'{port}[{i}]'
                r = rects.get(nm) or (rects.get(port) if bits == 1 else None)
                if r is None:
                    bad.append(f'{nm} not in LEF'); break
                lay, x0, y0, x1, y1 = r
                f = PA._face(r, W, H)
                if f is None:
                    bad.append(f'{nm} area pin'); break
                d = pin_shift.get(nm, 0.0)
                if f in 'EW':
                    c, depth = (y0 + y1) / 2 + d, (x1 if f == 'W' else W - x0)
                else:
                    c, depth = (x0 + x1) / 2 + d, (y1 if f == 'S' else H - y0)
                per.append([f, lay, round(c, 4), round(depth, 4)])
            if len(per) == bits:
                rec_ports[port] = dict(bits=bits, per_bit=per, moved_um=sorted({pin_shift[f'{port}[{i}]'] for i in range(bits)
                                                                               if f'{port}[{i}]' in pin_shift}))
        why += bad
        # range + spacing per face/layer (base minimum pitch of that face/layer, at most 0.048)
        occ = collections.defaultdict(list)
        base_occ = collections.defaultdict(list)
        for port, spec in rec_ports.items():
            for i, (f, lay, c, depth) in enumerate(spec['per_bit']):
                lim = H if f in 'EW' else W
                if not (0.012 <= c <= lim - 0.012):
                    why.append(f'{port}[{i}] off face {c}')
                occ[(f, lay)].append((c, f'{port}[{i}]'))
                base_occ[(f, lay)].append(c - pin_shift.get(f'{port}[{i}]', 0.0))
        for k, v in occ.items():
            bs = sorted(base_occ[k]); pitch = min([y - x for x, y in zip(bs, bs[1:])] + [0.048])
            v.sort()
            for (c0, n0), (c1, n1) in zip(v, v[1:]):
                if c1 - c0 < pitch - 1e-4:
                    why.append(f'spacing {n0}@{c0} {n1}@{c1} < {pitch:.3f} on {k}'); break
        # non-die-port pins of the LEF (clock/reset etc. are die ports too; anything else is reported)
        extra = sorted({(_BIT.match(p).group(1) if _BIT.match(p) else p) for p in rects} - set(ports))
        if tdir is not None:
            tp = tdir.get(mst)
            if tp is None:
                why.append('master absent from target plan')
            else:
                diff = {p: (ports.get(p), tp.get(p)) for p in set(ports) | set(tp) if ports.get(p) != tp.get(p)}
                if diff:
                    why.append(f'port set differs in target: {diff}')
        if tlef is not None and mst in tlef and (abs(tlef[mst][0] - W) > .025 or abs(tlef[mst][1] - H) > .025):
            why.append(f'outline differs in target {tlef[mst][:2]} vs {(W, H)}')
        if why:
            summary['refused'][mst] = why[:6]
            continue
        rec = dict(schema=SCHEMA, master=mst, case=a.case, outline_um=[W, H],
                   rule='GEO-S screen candidate: die-assigned data pins re-packed by tools/s81/die_link_repin_search.py '
                        '(total incident bit-um, partner stations/relays/field/IP fixed); clock/reset/other pins stand '
                        'where the generator lays them (anchored in the search). Die lead adopts or refuses.',
                   source=dict(report=summary['report_sha256'], **rep['source_sha256']),
                   non_die_port_pins=extra,
                   ports={p: compact(s['bits'], s['per_bit']) for p, s in rec_ports.items()},
                   moved={p: s['moved_um'] for p, s in rec_ports.items() if s['moved_um']})
        (a.out_dir / f'{mst}.json').write_text(json.dumps(rec, indent=0) + '\n')
        summary['written'][mst] = dict(ports=len(rec_ports), moved_ports=len(rec['moved']),
                                       max_shift_um=max((abs(x) for v in rec['moved'].values() for x in v), default=0))
    (a.out_dir / 'EMIT_SUMMARY.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(dict(written=len(summary['written']), refused=summary['refused']), indent=1))


if __name__ == '__main__':
    main()
