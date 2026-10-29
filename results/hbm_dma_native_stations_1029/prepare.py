#!/usr/bin/env python3
"""Project the sixteen actual DMA edges onto exact plan pins; no aliases/epochs.

Geometry/count preparation only. Source RTL, parent plan and historical failures
remain unchanged. Physical body placement and token pricing are separate work.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan-dir', required=True)
    ap.add_argument('--native', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    base = Path(a.plan_dir)
    plan = json.loads((base / 'die_plan.json').read_text())
    native = json.loads(Path(a.native).read_text())
    mapping = json.loads(Path(a.map).read_text())['parts']
    parts = {p['name']: p for p in plan['partitions']}
    pins = {}

    def endpoint(name, port, bit):
        if name not in mapping:
            raise ValueError(f'actual native member {name} has no explicit map')
        part, inst = mapping[name]
        typ = parts[part]['type']
        matches = [h for h in plan['partition_types'][typ]['hard_cores'] if h['inst'] == inst]
        if len(matches) != 1:
            raise ValueError(f'{name} explicit {part}/{inst} matched {len(matches)} physical cores')
        h = matches[0]
        path = base / h['pins_file']
        if str(path) not in pins:
            doc = json.loads(path.read_text())
            rows = doc.get('pins', []) if isinstance(doc, dict) else doc
            pins[str(path)] = {p.get('name') or f"{p['bus']}[{p.get('bit', 0)}]": p for p in rows}
            if len(pins[str(path)]) != len(rows):
                raise ValueError(f'duplicate physical pin identities in {path}')
        pin = f'{port}[{bit}]'
        if pin not in pins[str(path)]:
            raise ValueError(f'{name}.{pin} has no actual physical pin in {path}')
        p = pins[str(path)][pin]
        x, y = p['x'], p['y']
        w, ht = h['outline_um']
        orient = h.get('orient', 'R0')
        if orient not in ('R0', 'MX', 'MY', 'R180'):
            raise ValueError(f'unsupported explicit core orientation {orient}')
        if orient in ('MY', 'R180'):
            x = w - x
        if orient in ('MX', 'R180'):
            y = ht - y
        ox, oy = h['origin_um']
        dx, dy = h.get('track_offset_um', (0, 0))
        return dict(native=name, part=part, type=typ, inst=inst, module=h['module'],
                    pin=pin, pins_file=h['pins_file'], layer=p['layer'], orient=orient,
                    xy_um=[round(ox + dx + x, 6), round(oy + dy + y, 6)])

    groups = []
    for g in native['groups']:
        if g['width'] not in (17, 257) or len(g['src_bits']) != g['width'] or len(g['dst_bits']) != g['width']:
            raise ValueError('actual source contract width/bit list mismatch')
        pairs = []
        for sb, db, net in zip(g['src_bits'], g['dst_bits'], g['source_nets']):
            s, d = endpoint(g['src'], g['src_port'], sb), endpoint(g['dst'], g['dst_port'], db)
            if s['part'] != d['part']:
                raise ValueError('DMA native edge crosses plan partitions')
            pairs.append(dict(src=s, dst=d, native_net=net, src_bit=sb, dst_bit=db))
        groups.append(dict(bank=g['bank'], kind='request' if g['width'] == 17 else 'return',
                           width=g['width'], valid_src_bit=g['valid_src_bit'], valid_dst_bit=g['valid_dst_bit'],
                           actual_source_stages=g['actual_source_stages'], source=g['src'], sink=g['dst'], pairs=pairs))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tn = groups[0]['pairs'][0]['src']['type']
    t = plan['partition_types'][tn]
    # Keep the exact type and core tables for the existing station_resite solver.
    (out / 'type.json').write_text(json.dumps(t, indent=1) + '\n')
    result = dict(schema='hbm.dma.native_pin_projection.v1', type=tn, groups=groups,
                  source=dict(plan_sha256=digest(base/'die_plan.json'), native_sha256=digest(a.native),
                              map_sha256=digest(a.map)), bits=sum(g['width'] for g in groups),
                  qualification='native bit identity + exact plan pin projection; no adopted source/physical pipeline')
    (out / 'pin_projection.json').write_text(json.dumps(result, indent=1) + '\n')
    subset = {name: mapping[name] for name in {g['source'] for g in groups} | {g['sink'] for g in groups}}
    (out / 'map_subset.json').write_text(json.dumps(subset, indent=1) + '\n')
    print(json.dumps(dict(groups=len(groups), bits=result['bits'], type=tn, missing_physical_pins=0)))


if __name__ == '__main__':
    main()
