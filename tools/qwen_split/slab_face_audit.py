#!/usr/bin/env python3
"""Audit current source-exact slab faces against a pinned die graph.

Report every incident data bus before trying an orientation change.  Geometry
does not establish allocation, routing, native timing or a die contract grant.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_rom_fulldie import Master, pin_rects
from qwen_split import source_pin_plan as S


def grouped(pins):
    out = collections.defaultdict(list)
    for p in pins:
        r = p['rect']
        out[p['name'].split('[')[0]].append(((r[0]+r[2])/2, (r[1]+r[3])/2))
    return out


def audit(path):
    raw = path.read_bytes()
    graph = json.loads(raw)
    insts = {i['n']: i for i in graph['insts']}
    pins = {m: grouped(v['pins']) for m, v in graph['masters'].items()}
    masters = {}
    for name, v in graph['masters'].items():
        if not name.startswith('qfd_port_tiles_'):
            continue
        q = Master(name, v['w'], v['h'], 7, '')
        # Only the previous face is inherited for unspecified ports.  Every
        # final position and width is rebuilt by the actual source pin tool.
        for p, xy in pins[name].items():
            x = sum(a for a, _ in xy)/len(xy)
            y = sum(b for _, b in xy)/len(xy)
            face = min({'W': x, 'E': v['w']-x, 'S': y, 'N': v['h']-y}, key=lambda f: {'W': x, 'E': v['w']-x, 'S': y, 'N': v['h']-y}[f])
            q.face(p, len(xy), face, 'M4' if face in 'EW' else 'M5', 0)
        masters[name] = q
    S.apply_slabs(masters)
    faces = {}
    for name, q in masters.items():
        rects = pin_rects(q, 1, {})
        pins[name] = grouped([dict(name=n, layer=l, rect=r) for n, l, r in rects])
        face_ports = collections.defaultdict(dict)
        for p, (_, n, face, layer, centre, pitch) in q.ports.items():
            face_ports[face][p] = dict(bits=n, layer=layer, centre_um=centre)
        faces[name] = {f: dict(ports=ps, bits=sum(p['bits'] for p in ps.values()),
                              gross_cut_m5_m7=(sum(p['bits'] for p in ps.values())/(q.w/.096+q.w/.128) if f in 'NS' else None))
                       for f, ps in face_ports.items()}

    def points(ip, flipped):
        i, port = ip
        a = insts[i]
        orient = 'MX' if i == flipped else a['o']
        return [(a['x']+(a['w']-x if orient in ('MY', 'R180') else x),
                 a['y']+(a['h']-y if orient in ('MX', 'R180') else y)) for x, y in pins[a['m']][port]]

    candidates = []
    for band in range(3):
        target = f'sp_port_tiles_{band}_f1'
        if insts[target]['o'] == 'MX':
            continue
        rows = []
        for b in graph['buses']:
            if b['c'] in ('clock_trunk', 'reset') or len(b['e']) != 2 or target not in [i for i, _ in b['e']]:
                continue
            old = [points(ip, None) for ip in b['e']]
            new = [points(ip, target) for ip in b['e']]
            if any(len(p) != b['n'] for p in old+new):
                raise ValueError(f"{b['b']}: endpoint width mismatch")
            lengths = [[abs(x-u)+abs(y-v) for (x,y),(u,v) in zip(*pp)] for pp in (old,new)]
            rows.append(dict(bus=b['b'], bits=b['n'], endpoints=b['e'],
                             old_worst_um=max(lengths[0]), new_worst_um=max(lengths[1]),
                             old_bit_um=sum(lengths[0]), new_bit_um=sum(lengths[1]),
                             worst_stage_delta=math.ceil(max(lengths[1])/490)-math.ceil(max(lengths[0])/490)))
        before = sum(r['old_bit_um'] for r in rows)
        after = sum(r['new_bit_um'] for r in rows)
        candidates.append(dict(instance=target, from_orientation=insts[target]['o'], to_orientation='MX',
                               incident_data=rows, old_bit_um=before, new_bit_um=after,
                               delta_percent=100*(after/before-1),
                               decision='REJECT' if after >= before or any(r['worst_stage_delta'] > 0 for r in rows) else 'NEEDS_FULL_PHYSICAL_PROOF'))
    hashes = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
              ('tools/qwen_split/source_pin_plan.py', 'rtl/qwen_split/qfd_port_tiles.sv')}
    return dict(schema='opentallas.qwen.slab-face-audit.v1', graph=str(path),
                graph_sha256=hashlib.sha256(raw).hexdigest(), graph_source=graph.get('source_commit'),
                current_source_sha256=hashes, faces=faces, orientation_candidates=candidates,
                qualified=False, unresolved=['graph homes are source-pinned historical geometry, not the next contract',
                'actual PG blockage and detailed cut windows remain unmeasured',
                'train24 physical bank homes and native boundary timing remain unmeasured',
                'clock/reset transforms, allocator and detailed-route proof required before any adoption'],
                note='Main cd786fcce already moved primary rq to N: the old 13062-bit S-face budget is superseded. No additional port movement is granted by this audit.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('graph', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = audit(args.graph)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    for name, rec in result['faces'].items():
        print(name, {f: r['bits'] for f, r in rec.items()})
    for rec in result['orientation_candidates']:
        print(rec['instance'], rec['decision'], f"{rec['delta_percent']:+.3f}% incident bit-um")
