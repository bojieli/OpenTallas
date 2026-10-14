#!/usr/bin/env python3
"""Source-pin geometric reach for private HC window placement; never a route grant."""
import argparse
import hashlib
import json
from pathlib import Path


def pin_centres(dump):
    return {name: [(layer, (box[0]+box[2])/2, (box[1]+box[3])/2)
                   for layer, box in shapes]
            for name, _, typ, _, shapes in dump['bterms'] if typ == 'SIGNAL'}


def evaluate(report_path, package_path):
    report = json.loads(report_path.read_text())
    package = json.loads(package_path.read_text())
    base = package_path.parent
    masters = {x['master']: x for x in package['inventory']}
    pin_maps = {}
    for master in ('ot_hgi_hc_win_ctl', 'ot_hgi_hc_win_sector'):
        meta = masters[master]
        path = Path(meta['actual_pin_coordinates_file'])
        if not path.is_absolute():
            path = Path.cwd()/path
        dump = json.loads(path.read_text())
        if dump['die'][2:4] != meta['measured_outline_um']:
            raise ValueError(f'{master}: inventory / pin-DB outline mismatch')
        pin_maps[master] = pin_centres(dump)
    placement = {x['source_path']: x for x in report['hc_scalar_proposals']}
    pairs = []
    for path, sector in placement.items():
        if sector['master'] != 'ot_hgi_hc_win_sector':
            continue
        prefix = path.rsplit('.g_sector[', 1)[0]
        sid = int(path.rsplit('.g_sector[', 1)[1].split(']', 1)[0])
        ctl_path = prefix+'.u_ctl'
        ctl = placement[ctl_path]
        if ctl['orientation'] != 'R0' or sector['orientation'] != 'R0':
            raise ValueError('Only explicit R0 private proposals are supported')
        links = [('sector_read', 'read_v'), ('sector_live', 'live')]
        links += [(f'sector_addr[{i}]', f'read_addr[{i}]') for i in range(7)]
        links += [(f'sector_fault[{sid}]', 'fault')]
        for ctl_pin, sector_pin in links:
            cp = pin_maps['ot_hgi_hc_win_ctl'][ctl_pin]
            sp = pin_maps['ot_hgi_hc_win_sector'][sector_pin]
            choices = [(abs(ctl['xy_um'][0]+cx-sector['xy_um'][0]-sx)
                        + abs(ctl['xy_um'][1]+cy-sector['xy_um'][1]-sy), cl, sl)
                       for cl,cx,cy in cp for sl,sx,sy in sp]
            dist,cl,sl = min(choices)
            is_feedback = sector_pin == 'fault'
            pairs.append({'source_path': path if is_feedback else ctl_path,
                          'source_pin': sector_pin if is_feedback else ctl_pin,
                          'target_path': ctl_path if is_feedback else path,
                          'target_pin': ctl_pin if is_feedback else sector_pin,
                          'source_layer': sl if is_feedback else cl,
                          'target_layer': cl if is_feedback else sl,
                          'private_pin_manhattan_um': round(dist, 6),
                          'geographic_mapping_proven': False,
                          'routed_face_window_qualified': False})
    return {'schema': 'opentallas.hc_window.private_pin_reach.v1',
            'geometry_sha256': report['geometry_sha256'],
            'geometry_source_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'pin_package_sha256': hashlib.sha256(package_path.read_bytes()).hexdigest(),
            'source_commit': report['hc_source_commit'],
            'pairs': pairs,
            'summary': {'count': len(pairs),
                        'max_private_manhattan_um': max(x['private_pin_manhattan_um'] for x in pairs),
                        'over100um_count': sum(x['private_pin_manhattan_um']>100 for x in pairs)},
            'missing_for_route_qualification': ['assigned quarter/peer endpoint graph',
                                               'routed child TT/FF per-bit P/Q windows',
                                               'actual clock/reset driver phase and slew',
                                               'retained bank logic placement and peer pin locations'],
            'qualified': False, 'assigned': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry_report', type=Path)
    parser.add_argument('pin_package', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = evaluate(args.geometry_report,args.pin_package)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary']))
