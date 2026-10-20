#!/usr/bin/env python3
"""Source-pinned slot lower bounds, not a new die plan or a closure receipt."""
import collections
import hashlib
import json
import math
from pathlib import Path
import runpy
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'sources'
PITCH = 43.2
LIMIT = 6.0


def snap_up(x):
    return round(math.ceil((x - 1e-8) / PITCH) * PITCH, 6)


def production_ports(entry):
    """Parse the exact production declaration with RS_OBS absent; retain every declared bit."""
    source = (SRC / 'dsdv_svc_rs.sv').read_text()
    module = 'dsdv_svc_rs_entry' if entry else 'dsdv_svc_rs'
    text = source.split('module ' + module + ' #(', 1)[1].split(');', 1)[0]
    text = text.split(') (', 1)[1]
    text = re.sub(r'`ifdef RS_OBS.*?`endif', '', text, flags=re.S)
    ports = {}
    direction, width = None, None
    for item in text.split(','):
        item = item.strip()
        match = re.match(r'(input|output)\s+wire\s*(\[[^]]+\])?\s*(\w+)\s*$', item)
        if match:
            direction, span, name = match.groups()
            if span:
                hi, lo = span[1:-1].split(':')
                assert re.fullmatch(r'[0-9*+ -]+', hi + lo), span
                width = eval(hi, {'__builtins__': {}}) - eval(lo, {'__builtins__': {}}) + 1
            else:
                width = 1
        else:
            assert re.fullmatch(r'\w+', item), item
            name = item
        assert direction and width and name not in ports
        ports[name] = {'direction': direction, 'bits': width}
    return ports


def production_faces(entry):
    ports = production_ports(entry)
    faces = {f: [] for f in 'NESW'}
    lanes = ['dn_i', 'dn_o', 'up_i', 'up_o', 'ri', 'ro', 'gi_v', 'gi_d', 'go_v', 'go_d',
             'si_v', 'si_d', 'so_v', 'so_d']
    for p in lanes:
        n = ports[p]['bits']
        assert n % 4 == 0
        for i, f in enumerate('NESW'):
            faces[f] += [f'{p}[{j}]' for j in range(i * n // 4, (i + 1) * n // 4)]
    extra = {'S': ['rq', 'rk', 'wd', 'rv', 'r_data', 'r_tag', 'r_beat', 'hs', 'ck', 'rst', 'sid']}
    if entry:
        extra.update(N=['j', 'jd', 'q', 'hc', 'fault', 'st_rg'], W=['hw'], E=['pv_v', 'pv_d', 'pv_x'])
    for f, ps in extra.items():
        for p in ps:
            faces[f] += [p] if ports[p]['bits'] == 1 else [f'{p}[{j}]' for j in range(ports[p]['bits'])]
    assert set(lanes + [p for ps in extra.values() for p in ps]) == set(ports)
    actual = [b for bits in faces.values() for b in bits]
    assert len(actual) == len(set(actual)) == sum(p['bits'] for p in ports.values())
    return ports, faces


def pin_geometry(faces, width=1728.0, height=1641.6):
    """Literal candidate geometry on the archived PDK grid, without changing any RTL bit."""
    pitch = {'M3': .036, 'M4': .048, 'M5': .048, 'M6': .064}
    offset = {'M3': .009, 'M4': .012, 'M5': .012, 'M6': .016}
    size = {'M3': (.018, .144), 'M4': (.192, .024), 'M5': (.024, .192), 'M6': (.192, .032)}
    pins = []
    used = set()
    for face, bits in faces.items():
        horiz = face in 'NS'
        span = (width if horiz else height) - 8.64
        for i, bit in enumerate(bits):
            layer = ('M3', 'M5')[i % 2] if horiz else ('M4', 'M6')[i % 2]
            desired = 4.32 + span * (i + .5) / len(bits)
            track = round((desired - offset[layer]) / pitch[layer])
            along = round(track * pitch[layer] + offset[layer], 6)
            assert (face, layer, track) not in used
            used.add((face, layer, track))
            x, y = (along, 0 if face == 'S' else height) if horiz else (0 if face == 'W' else width, along)
            assert 4.0 < along < (width if horiz else height) - 4.0
            pins.append({'pin': bit, 'face': face, 'layer': layer, 'track_index': track,
                         'xy_um': [x, y], 'size_um': size[layer]})
    assert len(pins) == sum(len(bs) for bs in faces.values())
    tcl = ['# MODEL ONLY: source-exact production ABI pin geometry; not a closed or generated ref_tile kit.']
    for p in pins:
        x, y = p['xy_um']; sx, sy = p['size_um']
        tcl.append(f"place_pin -pin_name {{{p['pin']}}} -layer {p['layer']} -location {{{x:.6f} {y:.6f}}} -pin_size {{{sx} {sy}}} -force_to_die_boundary")
    return pins, '\n'.join(tcl) + '\n'


def main():
    plan = json.loads((SRC / 'p4l_plan.json').read_text())
    blocks = plan['blocks']
    counts = collections.defaultdict(collections.Counter)
    lanes = collections.defaultdict(lambda: collections.defaultdict(list))
    for link in plan['links']:
        for end in link['e']:
            block = blocks[end[0]]
            if block['kind'] != 'svc':
                continue
            x, y = end[2:4]
            distance = {'W': abs(x - block['x']), 'E': abs(x - block['x'] - block['w']),
                        'S': abs(y - block['y']), 'N': abs(y - block['y'] - block['h'])}
            face = min(distance, key=distance.get)
            counts[block['name']][face] += link['b']
            lanes[block['name']][face].append({'link': link['i'], 'bits': link['b']})
    rows = []
    for block in blocks:
        if block['kind'] != 'svc':
            continue
        name = block['name']
        rows.append({'instance': name, 'slot_um': [block['w'], block['h']],
                     'faces': {f: {'active_lane_bits': n,
                                   'pins_per_um': n / (block['w'] if f in 'SN' else block['h']),
                                   'lanes': lanes[name][f]}
                               for f, n in counts[name].items()}})
    max_ns = max(n for c in counts.values() for f, n in c.items() if f in 'NS')
    max_ew = max(n for c in counts.values() for f, n in c.items() if f in 'EW')
    minimum = [snap_up(max_ns / LIMIT), snap_up(max_ew / LIMIT)]
    old = next(b for b in blocks if b['kind'] == 'svc')
    # Execute only the archived generator's definitions. Its __main__ is not run.
    kit = runpy.run_path(str(SRC / 'svc_rs_lp_kit.py'), run_name='archived_kit_inventory')
    full = {}
    for entry in [False, True]:
        faces = kit['face_bits'](entry)
        full['entry' if entry else 'nonentry'] = {
            'face_bits': {f: len(bits) for f, bits in faces.items()},
            'pins_per_um_at_archived_kit': {f: len(bits) / (kit['W'] if f in 'NS' else kit['H'])
                                          for f, bits in faces.items()},
            'pins_per_um_at_active_lane_minimum': {f: len(bits) / (minimum[0] if f in 'NS' else minimum[1])
                                                 for f, bits in faces.items()}}
    production = {}
    prod_w = prod_h = 0
    caller = json.loads((SRC / 'bind_table_p4l3_mu.json').read_text())
    assert 'RS_OBS' not in caller['defines'], caller['defines']
    assert caller['masters']['dsdv_svc_rs']['inst_module'] == {
        'rsv_05': 'dsdv_svc_rs_entry', 'rsv_11': 'dsdv_svc_rs_entry'}
    for entry in [False, True]:
        ports, faces = production_faces(entry)
        module = 'dsdv_svc_rs_entry' if entry else 'dsdv_svc_rs'
        assert {name: p['bits'] for name, p in ports.items()} == caller['rtl_widths'][module]
        need_w = snap_up(max(len(faces[f]) for f in 'NS') / LIMIT)
        need_h = snap_up(max(len(faces[f]) for f in 'EW') / LIMIT)
        prod_w, prod_h = max(prod_w, need_w), max(prod_h, need_h)
        production['entry' if entry else 'nonentry'] = {
            'ports': ports, 'total_bits': sum(len(bs) for bs in faces.values()),
            'face_bits': {f: len(bs) for f, bs in faces.items()}, 'min_slot_um': [need_w, need_h]}
        (ROOT / ('production_entry_pins.json' if entry else 'production_pins.json')).write_text(
            json.dumps(faces, indent=2) + '\n')
        geometry, tcl = pin_geometry(faces)
        name = 'entry' if entry else 'nonentry'
        (ROOT / f'candidate_{name}_pins.tcl').write_text(tcl)
        (ROOT / f'candidate_{name}_geometry.json').write_text(json.dumps(geometry, separators=(',', ':')) + '\n')
        production[name]['candidate_literal_grid'] = {
            'pins': len(geometry), 'unique_face_layer_tracks': len(geometry), 'all_source_bits_exactly_once': True,
            'outline_um': [1728.0, 1641.6],
            'pin_layers': {'NS': ['M3', 'M5'], 'EW': ['M4', 'M6']},
            'scope': 'track snapping and pin uniqueness only; PG spacing/route capacity/parent correspondence still owed'}
    output = {
        'status': 'MODEL_ONLY_NOT_A_DIE_PLAN_OR_CLOSURE',
        'sources': {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                    for p in sorted(SRC.iterdir()) if p.is_file()},
        'source_refs': {'main_plan_and_generators': 'dd875958b0119c9739332101b4e19334f643fa66',
                        'historical_landed_kit': 'c8cb29cf3', 'prior_placefix': '6e3559855'},
        'aggregate_face_limit_pins_per_um': LIMIT,
        'active_lane_rows': rows,
        'active_lane_lower_bound': {
            'max_NS_bits': max_ns, 'max_EW_bits': max_ew, 'lattice_um': PITCH,
            'minimum_uniform_slot_um': minimum,
            'max_density_at_minimum': max(max_ns / minimum[0], max_ew / minimum[1]),
            'additional_total_8column_width_um_preserving_gaps': 8 * (minimum[0] - old['w']),
            'additional_total_2row_height_um_preserving_gap': 2 * (minimum[1] - old['h']),
            'additional_16slot_area_mm2': 16 * (minimum[0] * minimum[1] - old['w'] * old['h']) / 1e6,
            'limitation': 'Counts plan lane endpoints only; excludes clock/reset, role-active side ports, pin rectangles and PG.'},
        'archived_full_port_kit': {
            'slot_um': [kit['W'], kit['H']], 'inventory': full,
            'warning': 'Historical landed wrapper ports differ from main dsdv_svc_rs. No current production ABI equivalence or full-source adoption is claimed.'},
        'current_production_ABI': {
            'define': 'RS_OBS absent; main existing SM target internalization retained',
            'actual_saved_caller': {'table': 'bind_table_p4l3_mu.json', 'defines': caller['defines'],
                                   'widths_equal_source_declarations': True,
                                   'entry_callers': caller['masters']['dsdv_svc_rs']['inst_module'],
                                   'source_parameters': 'MUT=0,DIE_ID=0,ST=0,SRAM_MACRO=0,SMT=1 defaults; table sets no parameter override',
                                   'view': caller['masters']['dsdv_svc_rs']['view'],
                                   'admission_gap': 'Table has no hardened svc view; model main source is pinned but runtime RTL-ref resolution and native SRAM configuration remain owed.'},
            'inventory': production,
            'uniform_full_ABI_pin_lower_bound_um': [prod_w, prod_h],
            'additional_16slot_area_mm2': 16 * (prod_w * prod_h - old['w'] * old['h']) / 1e6,
            'additional_8column_width_preserving_gaps_um': 8 * (prod_w - old['w']),
            'additional_2row_height_preserving_gap_um': 2 * (prod_h - old['h']),
            'packing_comparator_1728x2073p6_area_delta_16slots_mm2':
                16 * (1728 * 2073.6 - old['w'] * old['h']) / 1e6,
            'limitation': 'Source ports exactly enumerated; candidate face assignment only. No track/PG/macro packing/reach/STA/CTS qualification.'},
        'saved_plan_overlap_evidence': plan['facts']['lane_band_over_block'],
        'structural_obligations': [
            'Retain every active source bit. Two physical pin layers do not halve aggregate face density.',
            'Select the exact production svc/entry/owner module and derive every port, role, direction and pin from that source before choosing a final slot.',
            'Repack all sixteen slots and gaps jointly with CTRL height/array +86.4 and TOPK quarter 518.4x648; do not add old +70 blindly.',
            'Re-run exact lane-band/body/relay collision and Manhattan405 checks after placement; the saved74 overlaps are not fixed by this sizing lower bound.',
            'Actual two-layer pin grid must retain bit order, legal tracks, spacing and register landing; mapped source must qualify native32/storage/reset/clock.',
            'Recompute station counts, per-lane ages and compiler price before full protocol/token verification; no cycle delta has been measured here.',
            'Require full source identity, strict bind, actual die physical GRT/TT/FF/SS/clock/reach and parent/hardened child qualification before adoption.'
        ]}
    (ROOT / 'model.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'lower_bound': output['active_lane_lower_bound'],
                      'current_production_ABI': output['current_production_ABI']}, indent=2))


if __name__ == '__main__':
    main()
