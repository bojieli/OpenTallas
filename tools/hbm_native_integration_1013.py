#!/usr/bin/env python3
"""Compose source-pinned native B2 leaf placement without inventing boundary wiring.

Component regions are bookkeeping only. Every placed instance is a direct die
child. Cross-component nets are deliberately an open gate until native consumers
and VM/HC interfaces have a source-derived bridge; this is a placement prototype.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = {
    'sm': 'results/arch/hbm_native_1013/sm/component.json',
    'lo': 'results/arch/hbm_native_1013/attention/lo.component.json',
    'hi': 'results/arch/hbm_native_1013/attention/hi.component.json',
    'vm': 'results/arch/hbm_native_1013/vm/component.json',
}
DIE = (32984.288, 25980.528)
GRID = (0.432, 2.16)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outline(component):
    value = component['outline_um']
    return (value['w'], value['h']) if isinstance(value, dict) else tuple(value)


def physical_name(logical):
    return 'native_' + re.sub(r'[^a-zA-Z0-9_]', '_', logical)


def rect(row):
    x, y = row['xy_um']
    return x, y, x + row['w_um'], y + row['h_um']


def overlaps(rows):
    found = []
    active = []
    for row in sorted(rows, key=lambda r: rect(r)[0]):
        x0, y0, x1, y1 = rect(row)
        active = [other for other in active if rect(other)[2] > x0 + 1e-7]
        for other in active:
            ox0, oy0, ox1, oy1 = rect(other)
            if min(y1, oy1) > max(y0, oy0) + 1e-7:
                found.append([other['instance'], row['instance']])
        active.append(row)
    return found


def compose(outdir):
    data = {key: json.loads((ROOT / value).read_text()) for key, value in COMPONENTS.items()}
    rows, regions, maps = [], [], []
    names = set()
    grid_corrections = []
    for key, component in data.items():
        child_names = {child['instance'] for child in component['children']}
        for conn in component['connections']:
            for endpoint in conn['endpoints']:
                if endpoint['instance'] not in child_names | {'$boundary'}:
                    raise ValueError(f"{key}: unknown connection child {endpoint['instance']}")
        for binding in component['boundary_binding']:
            if binding['child_instance'] not in child_names:
                raise ValueError(f"{key}: unknown boundary child {binding['child_instance']}")

    def add(key, instance, x, y):
        component = data[key]
        w, h = outline(component)
        regions.append({'instance': instance, 'component': key, 'xy_um': [x, y],
                        'w_um': w, 'h_um': h, 'bookkeeping_region_only': True})
        maps.append({'namespace': instance, 'component_path': COMPONENTS[key],
                     'component_sha256': sha(ROOT / COMPONENTS[key]),
                     'connection_net_prefix': instance + '/',
                     'endpoint_instance_prefix': instance + '/',
                     'boundary_endpoint': instance + '/$boundary',
                     'boundary_ports': component['boundary_ports'],
                     'internal_connection_count': len(component['connections']),
                     'boundary_binding_count': len(component['boundary_binding']),
                     'constant_binding_key': next((k for k in ['constants', 'constant_binding'] if k in component), None),
                     'source_commit': component['source_commit'],
                     'defines': component.get('defines', []),
                     'parameters': component.get('parameters', component.get('params', {}))})
        for child in component['children']:
            row = dict(child)
            logical = instance + '/' + child['instance']
            row['logical_instance'] = logical
            row['instance'] = physical_name(logical)
            if row['instance'] in names:
                raise ValueError('physical instance collision: ' + logical)
            names.add(row['instance'])
            row['parent'] = 'die'
            row['component_namespace'] = instance
            row['component_child'] = child['instance']
            raw = [x + child['xy_um'][0], y + child['xy_um'][1]]
            row['xy_um'] = [round(round(v/g)*g, 6) for v,g in zip(raw, GRID)]
            delta = [round(a-b,6) for a,b in zip(row['xy_um'],raw)]
            if any(abs(v)>1e-7 for v in delta):
                grid_corrections.append({'instance': row['instance'], 'delta_um': delta, 'inherited_xy_um': raw})
                row['integration_grid_correction_um'] = delta
            rows.append(row)

    reservations = []
    for quarter, qx, qy in [('SW',21.6,21.6), ('SE',16513.632,21.6),
                            ('NW',21.6,13003.2), ('NE',16513.632,13003.2)]:
        for index in range(8):
            add('sm', f'hb_sm_{quarter}_{index}', qx + (index % 2) * 6156.0,
                qy + (index // 2) * 2646.0)
            ax = qx + 12333.6 + (index % 2) * 1821.744
            ay = qy + (index // 2) * 2008.8
            add('lo', f'hb_attn_{quarter}_{index}_lo', ax, ay)
            add('hi', f'hb_attn_{quarter}_{index}_hi', ax, ay + 1285.2)
        add('vm', f'hb_vms_{quarter}', qx + 12333.6, qy + 9007.2)
        reservations.append({'instance': f'UNRESOLVED_HC_{quarter}',
                             'xy_um': [qx + 43.2, qy + 10800], 'w_um': 1356.48,
                             'h_um': 756, 'placed_instance': False,
                             'reason': 'Two SYS1 banks and residual LL8/reducer direct-leaf bindings/real views pending; reservation is not coverage.'})
    collisions = overlaps(rows)
    outside = [r['instance'] for r in rows if rect(r)[0] < 0 or rect(r)[1] < 0
               or rect(r)[2] > DIE[0] or rect(r)[3] > DIE[1]]
    offgrid = [r['instance'] for r in rows if any(abs(v / g - round(v / g)) > 1e-5
               for v,g in zip(r['xy_um'], GRID))]
    reserved_collisions = overlaps(rows + reservations)
    boundary_bits = sum(sum(p['width'] for p in m['boundary_ports'].values()) for m in maps)
    gate = {'cross_component_source_netlist': False, 'native_hc_leaf_map': False,
            'all_child_closure': False, 'full_die_registered_seam_sta': False,
            'native_exact_mutant_throughput': False, 'native_pdn_ir': False,
            'signal_grt_drt': False, 'fixed_phy_service_station_integration': False}
    candidate = {'schema': 'opentallas.hbm.native_die_candidate.v1',
                 'variant': 'r25gqn_v12_native_component_prototype', 'die_um': list(DIE),
                 'placement_grid_um': list(GRID), 'closed': False,
                 'final_signoff_eligible': False, 'hard_parent_created': False,
                 'coverage': {'sm': 32, 'native_sm_tile_clusters': 512,
                              'attention_lo': 32, 'attention_hi': 32, 'vm_slices': 4,
                              'direct_hard_children': len(rows), 'hc': 'unresolved',
                              'fixed_phy_service_stations': 'not yet integrated'},
                 'component_regions': regions, 'children': rows,
                 'functional_namespace_maps': maps, 'unresolved_regions': reservations,
                 'qualification_gates': gate,
                 'unresolved': ['Cross-component SM/attention/HC-to-native-VM port bridge must come from source, not old opaque bundle aliases.',
                     'SM FC_HIER changes interface latency by two cycles; exact/mutant and throughput gate pending.',
                     'SM and VM internal long seams require protocol-preserving registered transport and timing proof.',
                     'Native HC two SYS1 banks/quarter plus LL8 local and central reducer map pending.',
                     'Real PHY, service, stations, clocks/reset and their nets must be integrated before full-die route.',
                     'Native tile PG exports and all-child TT/FF/lint closure pending; prior upper-grid and historical PG pilot IR is not native die IR.']}
    receipt = {'schema': 'opentallas.hbm.native_candidate_receipt.v1',
               'variant': candidate['variant'], 'closed': False,
               'children': len(rows), 'component_instances': len(maps),
               'component_input_hashes': {k: sha(ROOT / v) for k,v in COMPONENTS.items()},
               'child_master_counts': dict(sorted(collections.Counter(r['logical_module'] for r in rows).items())),
               'internal_connection_groups': sum(m['internal_connection_count'] for m in maps),
               'boundary_binding_groups': sum(m['boundary_binding_count'] for m in maps),
               'boundary_bits_exposed_not_connected': boundary_bits,
               'child_rect_overlap_count': len(collisions), 'child_rect_overlaps': collisions[:30],
               'outside_count': len(outside), 'outside': outside[:30],
               'explicit_inherited_origin_grid_corrections': grid_corrections,
               'offgrid_count': len(offgrid), 'offgrid': offgrid[:30],
               'hc_reservation_overlap_count': len(reserved_collisions),
               'placement_subset_pass': not (collisions or outside or offgrid or reserved_collisions),
               'full_die_placement_pass': False,
               'missing_tt_children': sum(not r.get('view_lib',{}).get('tt') for r in rows),
               'qualification_gates': gate}
    if not receipt['placement_subset_pass']:
        raise ValueError(json.dumps(receipt))
    outdir.mkdir(parents=True, exist_ok=True)
    for filename, value in [('candidate.json',candidate), ('receipt.json',receipt)]:
        (outdir/filename).write_text(json.dumps(value, indent=2)+'\n')
    with (outdir/'placement.tcl').open('w') as f:
        f.write('# Native direct die children only. Partial placement prototype; no full-die closure.\n')
        for row in rows:
            f.write('place_macro -macro_name {%s} -location {%.6f %.6f} -orientation %s\n' %
                    (row['instance'], *row['xy_um'], row['orientation']))
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'results/arch/hbm_native_1013/die_v12')
    compose(parser.parse_args().out)
