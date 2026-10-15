#!/usr/bin/env python3
"""Assign complete new PQ producer leaf pins from source-pinned port requests."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


def get(root, commit, path):
    return subprocess.check_output(['git', '-C', str(root), 'show', commit + ':' + path])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--request-commit', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    path = 'tools/s81_static_control/pq_producer_physical_request.json'
    raw = get(args.root, args.request_commit, path)
    request = json.loads(raw)
    for name, sha in request['source_sha256'].items():
        assert hashlib.sha256(get(args.root, request['source_commit'], name)).hexdigest() == sha, name
    args.out.mkdir(parents=True, exist_ok=True)
    summary = dict(request_commit=args.request_commit, request_sha256=hashlib.sha256(raw).hexdigest(),
                   source_commit=request['source_commit'], source_sha256=request['source_sha256'], masters={})
    for master, item in request['masters'].items():
        reference = 'dsfd_stage_seq_static_c8' if master.endswith('_c9') else 'dsfd_host_c'
        specpath = 'tools/ref_tile/specs_s81_fill2/' + ('s81fill2_sseq_c8.json' if master.endswith('_c9') else 's81fill2_host_c.json')
        spec = json.loads(get(args.root, 'fa44c38ee', specpath))
        faces = {p: face for face, ports in spec['pins'].items() for p in ports}
        extra = dict(c13='E', d13='E', s13='E', f_pq_pw='N', t_pq_desc_pw='N',
                     calendar_prime='N', stage_start='N', calendar_base='N', calendar_length='N',
                     pq_image_sealed='N', pq_calendar_primed='N', pq_calendar_fault='N',
                     t_pq_pw='E', ck_ingest='S')
        faces.update(extra)
        assert set(item['ports']) <= set(faces), set(item['ports']) - set(faces)
        width, height = item['requested_outline_um']
        clock_bases = {re.sub(r'\[\d+\]$', '', x) for x in item['clock_entries'] + item['reset_entries']}
        order = {f: [p for p in spec['pins'].get(f, []) if p in item['ports']] for f in 'NSEW'}
        for port in item['ports']:
            if not any(port in ports for ports in order.values()):
                order[faces[port]].append(port)
        points, ports_record, report = {}, {}, {}
        for face, groups in order.items():
            layer = 'M5' if face in 'NS' else 'M4'
            length = width if face in 'NS' else height
            offset, pitch = (0.012, 0.048) if layer == 'M5' else (0.036, 0.048)
            pins = [(p, bit) for p in groups for bit in range(item['ports'][p]['width'])]
            roots = [(p, bit) for p, bit in pins if p in clock_bases]
            ordinary = [(p, bit) for p, bit in pins if p not in clock_bases]
            root_coordinates = {}
            for index, key in enumerate(roots):
                target = length / 2 + (index - (len(roots) - 1) / 2) * 0.192
                root_coordinates[key] = round(round((target - offset) / pitch) * pitch + offset, 3)
            available = [round(offset + index * pitch, 3)
                         for index in range(math.ceil((4.32-offset)/pitch), math.floor((length-4.32-offset)/pitch)+1)]
            available = [x for x in available if all(abs(x-c) >= 0.144-1e-6 for c in root_coordinates.values())]
            # At least two track pitches per ordinary pin: <=0.50 single-layer use.
            assert len(ordinary) * 2 <= len(available), (master, face, len(ordinary), len(available))
            coordinates = dict(root_coordinates)
            for index, key in enumerate(ordinary):
                coordinates[key] = available[math.floor((index+0.5)*len(available)/len(ordinary))]
            for port in groups:
                width_bits = item['ports'][port]['width']
                ports_record[port] = dict(bits=width_bits, per_bit=[[face, layer, coordinates[port, bit], 0.192] for bit in range(width_bits)])
                for bit in range(width_bits):
                    name = f'{port}[{bit}]' if width_bits > 1 else port
                    c = coordinates[port, bit]
                    x, y = ((c, height if face == 'N' else 0.) if face in 'NS' else (width if face == 'E' else 0., c))
                    points[name] = dict(layer=layer, face=face, location=[x,y], size=([0.024,0.192] if layer=='M5' else [0.192,0.024]))
            report[face] = dict(pins=len(pins), available_span_um=round(length-8.64,3),
                                total_track_share=round(len(pins)*pitch/(length-8.64),6), roots=len(roots))
        assert len(points) == item['total_pin_bits'], (master,len(points),item['total_pin_bits'])
        assert len({(v['layer'],*v['location']) for v in points.values()}) == len(points)
        record = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case='pq_producer_1417',
                      outline_um=[width,height], source=summary['source_sha256'], ports=ports_record,
                      rule='NEW source/outline; exact independent leaf assignment only; parent and die fit remain OPEN')
        (args.out/(master+'.json')).write_text(json.dumps(record,indent=2)+'\n')
        lines = ['# Exact die-owned new producer pins; source ' + request['source_commit']]
        for name,v in points.items():
            x,y=v['location'];sx,sy=v['size']
            lines.append(f"place_pin -pin_name {{{name}}} -layer {v['layer']} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sx} {sy}}} -force_to_die_boundary")
        (args.out/(master+'.tcl')).write_text('\n'.join(lines)+'\n')
        summary['masters'][master] = dict(outline_um=[width,height], pins=len(points), faces=report,
            clock_entries=item['clock_entries'], reset_entries=item['reset_entries'],
            assigned_sha256=hashlib.sha256((args.out/(master+'.json')).read_bytes()).hexdigest(),
            tcl_sha256=hashlib.sha256((args.out/(master+'.tcl')).read_bytes()).hexdigest())
    summary['grant'] = 'Independent new leaf outlines/exact pins; no inherited view. Parent/die fit, mapped root proof and native TT/FF/DRC qualification remain separate.'
    (args.out/'grant.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary['masters'],indent=2))


if __name__ == '__main__':
    main()
