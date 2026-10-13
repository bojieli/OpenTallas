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
import math
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


def compose(outdir, attention_shift_um=436.32, track_legal=False, variant='r25gqn_v12_native_component_prototype'):
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
            ax = qx + 12333.6 + attention_shift_um + (index % 2) * 1821.744
            ay = qy + (index // 2) * 2008.8
            add('lo', f'hb_attn_{quarter}_{index}_lo', ax, ay)
            add('hi', f'hb_attn_{quarter}_{index}_hi', ax, ay + 1285.2)
        add('vm', f'hb_vms_{quarter}', qx + 12333.6 + attention_shift_um, qy + 9007.2)
        reservations.append({'instance': f'UNRESOLVED_HC_{quarter}',
                             'xy_um': [qx + 43.2, qy + 10800], 'w_um': 1356.48,
                             'h_um': 756, 'placed_instance': False,
                             'reason': 'Two SYS1 banks and residual LL8/reducer direct-leaf bindings/real views pending; reservation is not coverage.'})
    vm8_path='results/arch/hbm_native_1013/vm8/geometry_component.json'
    vm8=json.loads((ROOT/vm8_path).read_text())
    # One union region, beside the south-west VMS assembly, below neither ring band.
    vm8_origin=[round(13608.0+attention_shift_um-136.08,6),8229.6]
    regions.append(dict(instance='hb_vm8_union',component='vm8_geometry_only',xy_um=vm8_origin,
                        w_um=vm8['outline_um'][0]+0.048,h_um=vm8['outline_um'][1],bookkeeping_region_only=True,
                        inherited_outline_um=vm8['outline_um'],integration_grid_extent_adjustment_um=[0.048,0.0]))
    for child in vm8['children']:
        row=dict(child);logical='hb_vm8_union/'+child['instance']
        row.update(instance=physical_name(logical),logical_instance=logical,parent='die',
                   component_namespace='hb_vm8_union',component_child=child['instance'],
                   xy_um=[round(round((vm8_origin[a]+child['xy_um'][a])/GRID[a])*GRID[a],6) for a in [0,1]])
        raw=[vm8_origin[a]+child['xy_um'][a] for a in [0,1]]
        delta=[round(row['xy_um'][a]-raw[a],6) for a in [0,1]]
        if any(abs(v)>1e-7 for v in delta):
            grid_corrections.append({'instance':row['instance'],'delta_um':delta,'inherited_xy_um':raw})
            row['integration_grid_correction_um']=delta
        if row['instance'] in names:raise ValueError('VM8 instance collision')
        names.add(row['instance']);rows.append(row)
    track_shifts, track_unsolved = [], []
    if track_legal:
        import hbm_native_pin_track_audit_1013 as tracks
        lefs, solved = {}, {}
        for row in rows:
            if not row.get('view_lef'):
                continue
            ox, oy = tracks.nm(row['xy_um'][0]), tracks.nm(row['xy_um'][1])
            key = (row['view_lef'], row['orientation'], ox % 1728, oy % 8640)
            if key not in solved:
                if row['view_lef'] not in lefs:
                    lefs[row['view_lef']] = tracks.parse(ROOT / row['view_lef'])
                w, h, pins = lefs[row['view_lef']]
                nx, ny = tracks.legal_origin(pins, row['orientation'], w, h, ox, oy)
                solved[key] = (None if nx is None else nx - ox, None if ny is None else ny - oy)
            dx, dy = solved[key]
            if dx is None or dy is None:
                track_unsolved.append({'instance': row['instance'], 'master': row['logical_module'],
                                       'orientation': row['orientation'], 'axis_without_solution':
                                       [a for a, v in zip('xy', (dx, dy)) if v is None]})
                continue
            if dx or dy:
                row['pre_track_xy_um'] = list(row['xy_um'])
                row['xy_um'] = [round((ox + dx) / 1000, 6), round((oy + dy) / 1000, 6)]
                row['track_legal_shift_nm'] = [dx, dy]
                track_shifts.append((row['logical_module'], row['orientation'], dx, dy))
    corridors=[dict(name='ring_S_1100',direction='H',layer='M6',rect_um=[21.6,11721.6,32962.688,12821.6],keep_clear_new_devices=True),
               dict(name='ring_N_1100',direction='H',layer='M6',rect_um=[21.6,24703.2,32962.688,25803.2],keep_clear_new_devices=True)]
    device_columns=[]
    for quarter,qx,qy in [('SW',21.6,21.6),('SE',16513.632,21.6),('NW',21.6,13003.2),('NE',16513.632,13003.2)]:
        device_columns.append(dict(name='ring_device_'+quarter,rect_um=[qx+12169.44,qy,qx+12333.6+attention_shift_um,qy+10692.0],
                                   device_width_um=270.0,device_height_um=380.16,
                                   directed_lane_count=2,lane_width_um=(12333.6+attention_shift_um-12169.44)/2,
                                   nominal_forward_wire_segment_um=500.0,closed_view_available=False))
    def box_hits(box,row):
        a,b,c,d=box;x,y,X,Y=rect(row)
        return min(c,X)>max(a,x)+1e-7 and min(d,Y)>max(b,y)+1e-7
    corridor_device_hits=[{'corridor':c['name'],'instance':r['instance']} for c in corridors for r in rows if box_hits(c['rect_um'],r)]
    column_device_hits=[{'column':c['name'],'instance':r['instance']} for c in device_columns for r in rows if box_hits(c['rect_um'],r)]
    collisions = overlaps(rows)
    outside = [r['instance'] for r in rows if rect(r)[0] < 0 or rect(r)[1] < 0
               or rect(r)[2] > DIE[0] or rect(r)[3] > DIE[1]]
    offgrid = [r['instance'] for r in rows if 'track_legal_shift_nm' not in r and any(abs(v / g - round(v / g)) > 1e-5
               for v,g in zip(r['xy_um'], GRID))]
    reserved_collisions = overlaps(rows + reservations)
    boundary_bits = sum(sum(p['width'] for p in m['boundary_ports'].values()) for m in maps)
    gate = {'native_idx_control_integration':False, 'cross_component_source_netlist': False, 'native_hc_leaf_map': False,
            'all_child_closure': False, 'full_die_registered_seam_sta': False,
            'native_exact_mutant_throughput': False, 'native_pdn_ir': False,
            'signal_grt_drt': False, 'fixed_phy_service_station_integration': False, 'native_vm8_xload_integration': False}
    candidate = {'schema': 'opentallas.hbm.native_die_candidate.v1',
                 'variant': variant, 'die_um': list(DIE),
                 'placement_grid_um': list(GRID), 'closed': False,
                 'final_signoff_eligible': False, 'hard_parent_created': False,
                 'coverage': {'sm': 32, 'native_sm_tile_clusters': 512,
                              'attention_lo': 32, 'attention_hi': 32, 'vm_slices': 4,
                              'native_hard_children': len(rows),
                              'real_lef_children':sum(bool(r.get('view_lef')) for r in rows),
                              'geometry_only_open_tile_children':sum(not r.get('view_lef') for r in rows),
                              'hc': 'unresolved',
                              'fixed_phy_service_stations': 'not yet integrated',
                              'vm8': {'required_union_regions':1,'required_total_tiles':25,'logical_quarter_views':4,
                                      'unique_kits':19,'geometry_children_placed':25,'native_pin_bindings_closed':False,
                                      'contract':'results/arch/hbm_b2_1012/SPEC.md',
                                      'planning':'results/physical/vm8_codex_1013/inventory.json'}},
                 'component_regions': regions, 'children': rows,
                 'functional_namespace_maps': maps, 'unresolved_regions': reservations,
                 'qualification_gates': gate,
                 'attention_vm_shift_um':attention_shift_um,
                 'routing_corridor_reservations':corridors,
                 'ring_device_column_reservations':device_columns,
                 'vm8_geometry_source':{'path':vm8_path,'sha256':sha(ROOT/vm8_path),'native_bindings_valid':False},
                 'view_extraction_uncertainties':['Shared FF interface clock-reference extraction order under source audit; use actual re-exported model hashes when available, no invented min-delay corrections.'],
                 'typed_adapter_bindings':{'path':'results/arch/hbm_native_1013/adapters/bit_bindings.json','sha256':sha(ROOT/'results/arch/hbm_native_1013/adapters/bit_bindings.json'),'actual_global_join_closed':False},
                 'ring_cut_study':{'path':'results/arch/hbm_native_ring_cut_1013/study.json','sha256':sha(ROOT/'results/arch/hbm_native_ring_cut_1013/study.json'),'must_recompute_after_geometry_change':True,'native_parent_pg_export_closed':False},
                 'unresolved': ['Native SM weight req_addr32 is HBM160-byte line service, not VM; activation/publication VM service plus typed owner192/ACK192 joins need actual composed adapters.',
                     'SM FC_HIER changes interface latency by two cycles; exact/mutant and throughput gate pending.',
                     'SM and VM internal long seams require protocol-preserving registered transport and timing proof.',
                     'Native IDX IXW1 control requires real source/geometry/leaf views; SW slot5 xload tap widths137/2249 are current, old129/2241 is ineligible.',
                     'Native HC two SYS1 banks/quarter plus LL8 local and central reducer map pending.',
                     'B2 retains VM8 for SM xload hb_vm_q: one current VM8 union region (25 total direct tiles/19 kits across four logical quarters) require native source pin/geometry mapping; do not omit or replace by guessed VMS aliases.',
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
               'vm8_packed_hop_endpoint_upper_bound_after_grid_um':497.568,
               'vm8_actual_per_bit_route_proof':False,
               'ring_band_device_collision_count':len(corridor_device_hits),
               'ring_device_column_collision_count':len(column_device_hits),
               'placement_subset_pass': not (collisions or outside or offgrid or reserved_collisions or corridor_device_hits or column_device_hits),
               'full_die_placement_pass': False,
               'missing_lef_children':sum(not r.get('view_lef') for r in rows),
               'track_legalisation': {'applied': track_legal,
                   'rule': 'every signal/clock pin of a real-LEF child has an on-track RECT at its die origin; nearest origin within +-288 nm x / +-96 nm y',
                   'shifted_instances': len(track_shifts),
                   'shift_classes': [dict(master=k[0], orientation=k[1], shift_nm=[k[2], k[3]], instances=v)
                                     for k, v in sorted(collections.Counter(track_shifts).items())],
                   'unsolved_instances': len(track_unsolved),
                   'unsolved_classes': [dict(master=k[0], orientation=k[1], axes=list(k[2]), instances=v) for k, v in sorted(
                       collections.Counter((u['master'], u['orientation'], tuple(u['axis_without_solution'])) for u in track_unsolved).items())],
                   'geometry_only_children_not_audited': sum(not r.get('view_lef') for r in rows)},
               'missing_tt_children': sum(not r.get('view_lib',{}).get('tt') for r in rows),
               'qualification_gates': gate}
    if not receipt['placement_subset_pass']:
        raise ValueError(json.dumps(receipt))
    # Source-derived VM ring topology, separate from unimplemented physical relays.
    from hbm_native_vm_component import leaf
    vmchildren = {c['instance']: c for c in data['vm']['children']}
    ringstop = vmchildren['u_cw']
    _, _, pinsets, _ = leaf(ROOT / ringstop['view_lef'])
    quarters = ['SW', 'SE', 'NW', 'NE']
    by_namespace = {r['instance']: r for r in regions}
    links = []
    for sid, quarter in enumerate(quarters):
        for direction, delta, stop in [('cw',1,'u_cw'), ('ccw',3,'u_ccw')]:
            target_sid = (sid+delta)%4
            source_ns = f'hb_vms_{quarter}'
            target_ns = f'hb_vms_{quarters[target_sid]}'
            a = by_namespace[source_ns]['xy_um']
            b = by_namespace[target_ns]['xy_um']
            local = vmchildren[stop]['xy_um']
            distances = [sum(abs(a[axis]+local[axis]+pinsets['l_out']['bits'][bit][axis]
                                 -b[axis]-local[axis]-pinsets['l_in']['bits'][bit][axis])
                             for axis in [0,1]) for bit in range(2224)]
            reach = max(distances)
            relay_stages = max(0,math.ceil(reach/500)-1)
            links.append({'direction':direction, 'source_sid':sid, 'target_sid':target_sid,
                          'source_boundary':[source_ns,direction+'_out'],
                          'target_boundary':[target_ns,direction+'_in'],
                          'source_leaf':[source_ns+'/'+stop,'l_out'],
                          'target_leaf':[target_ns+'/'+stop,'l_in'],
                          'forward_bits':2224, 'reverse_credit_bits':2,
                          'max_actual_pin_manhattan_um':round(reach,6),
                          'minimum_flop_relay_stages_at_500um':relay_stages,
                          'actual_hard_receiver_credits_per_vc':3,
                          'optimistic_per_vc_flits_per_cycle_upper_bound_with_raw_flop_relays':
                              round(min(1,3/max(1,2*relay_stages)),6),
                          'physical_transport_implemented':False})
    ring_source = 'rtl/hbm_accel/generic/vm/b2/tb_vms_ring4.sv'
    transport = {'schema':'opentallas.hbm.native_transport_requirements.v1',
                 'source_path':ring_source,'source_sha256':sha(ROOT/ring_source),
                 'ringstop_source_sha256':sha(ROOT/'rtl/hbm_accel/generic/vm/b2/ot_vms_rstop.sv'),
                 'quarter_to_sid_candidate':dict(zip(quarters,range(4))),
                 'quarter_to_sid_status':'Candidate order follows component replicated_instances; production stack mapping gate remains open.',
                 'ring_links':links,
                 'requirements':['CW sid+1 and CCW sid-1, with two separate per-VC return credits, are source-derived.',
                     'Physical relays must retain per-VC credits and bubble injection; no added global barrier.',
                     'D3 receiver credits cannot cover the long raw-flop loop at full rate. Require elastic credit termination or new qualified buffer views.',
                     'COLL star producer and all consumer-to-VM adapters still require actual native source bindings and throughput gates.'],
                 'closed':False}
    outdir.mkdir(parents=True, exist_ok=True)
    for filename, value in [('candidate.json',candidate), ('receipt.json',receipt), ('transport_requirements.json',transport)]:
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
    parser.add_argument('--attention-shift-um',type=float,default=436.32)
    parser.add_argument('--track-legal',action='store_true',help='move each real-LEF child to its nearest pin-on-track origin (v13)')
    parser.add_argument('--variant',default='r25gqn_v12_native_component_prototype')
    args=parser.parse_args()
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    compose(args.out,args.attention_shift_um,args.track_legal,args.variant)
