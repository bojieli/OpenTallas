#!/usr/bin/env python3
"""Plan native PC mux faces/row against source-pinned historical geometry.

This emits a proposed pin assignment and analytical fit receipt, never a LEF,
functional binding, timing verdict, or replacement for failed route evidence.
Run through the remote admission guard; geometry extraction is a separate job.
"""
import argparse
import ast
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integer(expr):
    tree = ast.parse(expr, mode='eval').body
    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return n.value
        if isinstance(n, ast.BinOp):
            a, b = walk(n.left), walk(n.right)
            if isinstance(n.op, ast.Mult): return a * b
            if isinstance(n.op, ast.Add): return a + b
            if isinstance(n.op, ast.Sub): return a - b
        raise ValueError(expr)
    return walk(tree)


def rtl_ports(path):
    text = re.sub(r'//[^\n]*', '', path.read_text())
    header = text.split(')(', 1)[1].split(');', 1)[0]
    result, direction, width = {}, None, 1
    for entry in header.split(','):
        entry = entry.strip()
        match = re.match(r'(input|output)\s+(?:wire|reg)\s*(?:\[([^:]+):([^]]+)\])?\s*(\w+)$', entry)
        if match:
            direction, hi, lo, name = match.groups()
            width = integer(hi) - integer(lo) + 1 if hi else 1
        else:
            assert re.fullmatch(r'\w+', entry), entry
            name = entry
        assert direction and name not in result
        result[name] = (direction, width)
    return result


def lef_pins(path):
    text = path.read_text()
    size = tuple(map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups()))
    pins = {}
    for match in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1\s', text, re.S):
        name, body = match.groups()
        rect = tuple(map(float, re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', body).groups()))
        pins[name] = ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
    return size, pins


def main():
    ap = argparse.ArgumentParser()
    for name in ('geometry', 'contract', 'rtl', 'ctrl-lef', 'svc-lef', 'output'):
        ap.add_argument('--' + name, required=True, type=Path)
    args = ap.parse_args()
    assert not args.output.exists(), 'preserve previous receipts: select a new output directory'
    geo_record = json.loads(args.geometry.read_text())
    contract = json.loads(args.contract.read_text())
    geo = geo_record['geometry']
    shape = contract['physical_slot_proposal']
    w, h = shape['width_um'], shape['height_um']
    ports = rtl_ports(args.rtl)
    ctrl_size, ctrl = lef_pins(args.ctrl_lef)
    svc_size, svc = lef_pins(args.svc_lef)
    pins = {}
    def add(port, bit, face, coord, reference):
        assert port in ports and 0 <= bit < ports[port][1]
        key = (port, bit)
        assert key not in pins, key
        assert 0 < coord < (w if face in 'NS' else h), (key, face, coord)
        pins[key] = dict(port=port, bit=bit, direction=ports[port][0], face=face,
                         coordinate_um=round(coord, 6), reference=reference)
    def leaf(name, bit):
        return f'{name}[{bit}]'
    # Existing controller N pins and service S pins are already bit aligned.
    for name in ('rq', 'r_data', 'r_tag', 'r_beat', 'rk', 'wd', 'rv'):
        for bit in range(ports[name][1]):
            ref = leaf(name, bit)
            assert ctrl[ref][1] > ctrl_size[1] - 0.2
            assert svc[ref][1] < 0.2
            assert abs(ctrl[ref][0] - svc[ref][0]) < 1e-6, ref
            add(name, bit, 'S', ctrl[ref][0], 'dsfd_ctrl_pc.' + ref)
            src_name = dict(rq='src_rq', r_data='src_rdata', r_tag='src_rtag',
                            r_beat='src_rbeat', rk='src_rk', wd='src_wd', rv='src_rv')[name]
            add(src_name, bit, 'N', svc[ref][0], 'dsfd_svc_pc.' + ref)
    # Source1/2 are west, source3 east; every native bit is explicitly named.
    lane_widths = dict(src_rq=341, src_rk=1, src_wd=1, src_rv=1,
                       src_rdata=256, src_rtag=17, src_rbeat=4)
    for face, sources in [('W', (1, 2)), ('E', (3,))]:
        total = sum(lane_widths.values()) * len(sources)
        start = (h - (total - 1) * 0.192) / 2
        index = 0
        for source in sources:
            for name, count in lane_widths.items():
                for bit in range(count):
                    add(name, source * count + bit, face, start + index * 0.192,
                        f'native source{source}; aperture binding pending')
                    index += 1
    # Status comes from the real released-domain co_w0, via an unmeasured
    # combinational buffer corridor; it is not a tied constant or new cycle.
    for n, name in enumerate(('ctrl_live', 'ck', 'rst_n', 'pending', 'ce', 'fault')):
        add(name, 0, 'E', 8.64 + n * 0.192,
            'dsfd_ctrl_pc.co_w[0]; buffer corridor pending' if name == 'ctrl_live'
            else 'clock/reset/status contextual source or sink pending')
    assert len(pins) == sum(width for _, width in ports.values())
    positions = [(p['face'], p['coordinate_um']) for p in pins.values()]
    assert len(positions) == len(set(positions)), 'overlapping face pins'
    gap = 8.64
    row_delta = h + gap  # one old gap becomes gap+new row+gap
    field_edge_slack = geo['y_f'] - geo['band_depth']
    required_gap = 4.32
    per_side_deficit = max(0, row_delta + required_gap - field_edge_slack)
    stacks = contract['controller_replication']['scan_stacks']
    pcs = contract['controller_replication']['pcs_per_stack'] * stacks
    source = geo_record['historical_failure_points']['source']
    destination = geo_record['historical_failure_points']['destination']
    s14 = geo_record['corridors']['s14W']
    corridor_x = (s14[0] + s14[2]) / 2
    ctrl_sw = next(s['box'] for s in geo_record['slabs'] if s['name'] == 'ctrl_SW')
    native_row_center = ctrl_sw[3] + gap + h / 2
    vertical_first = [source, [corridor_x, source[1]],
                      [corridor_x, native_row_center], [destination[0], native_row_center]]
    length = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(vertical_first, vertical_first[1:]))
    cap, spacing, end_cap = 215, 195, 90
    stations = max(1, math.ceil((length - 2 * end_cap) / spacing) + 1)
    # Physical route width is a floor, not available multilayer capacity.
    host_groups = {tuple(p['names']): p for p in contract['host_ports']}
    long_bits = host_groups[('o_v', 'o_we', 'o_addr', 'o_d')]['bits']
    assert long_bits == 290 and host_groups[('o_cr',)]['bits'] == 1
    long_bits += 1 + 8  # reverse credit and true write-visibility count
    channel_ledger = []
    for n, bottom in enumerate(geo['ch_y']):
        top = geo['tier_y'][n] if n < len(geo['tier_y']) else geo['y_top']
        corridor = geo_record['corridors'][f'ch{n}']
        free_height = corridor[3] - corridor[1]
        affected = [o['name'] for o in geo_record['all_occupancy']
                    if bottom <= (o['box'][1]+o['box'][3])/2 <= top
                    and o['box'][3] > top - 64.8]
        channel_ledger.append(dict(channel=n, old_height_um=top-bottom,
            proposed_height_um=top-bottom-64.8,
            historical_generic_corridor_height_um=free_height,
            proposed_generic_corridor_height_um=free_height-64.8,
            historical_horizontal_tracks_per_layer_floor=math.floor(free_height/0.048),
            proposed_horizontal_tracks_per_layer_floor=math.floor((free_height-64.8)/0.048),
            objects_requiring_relocation_count=len(affected),
            objects_requiring_relocation=affected))
    receipt = dict(schema='opentallas.s81-native-pc-floorplan-budget.v1',
        source_geometry=geo_record['source_commit'], source_inputs=geo_record['inputs_commit'],
        native_source=contract['source_pin'], adopted=False, physical_qualified=False,
        hashes={n: digest(getattr(args, n)) for n in ('geometry', 'contract', 'rtl', 'ctrl_lef', 'svc_lef')},
        pin_plan=dict(bits=len(pins), groups=len(ports), outline_um=[w, h],
            pitch_um=shape['per_pc_pitch_um'], controller_face='S', runtime_source0_face='N',
            host_source1_and_rope_source2_face='W', engram_source3_face='E',
            ctrl_live_producer='dsfd_ctrl_pc.co_w[0]', ctrl_live_leaf_coordinate_um=ctrl['co_w[0]'],
            ctrl_live_buffer_corridor_measured=False, per_face_minimum_pitch_um=0.096),
        row_model=dict(pcs=pcs, added_slot_area_mm2=pcs*w*h/1e6,
            protected_queue_bits=pcs*4*8*432, row_height_added_um=row_delta,
            old_band_depth_um=geo['band_depth'], new_band_depth_um=geo['band_depth']+row_delta,
            old_field_edge_slack_um=field_edge_slack, minimum_clearance_um=required_gap,
            fixed_field_per_side_deficit_um=per_side_deficit,
            minimum_die_height_growth_um=2*per_side_deficit,
            unchanged_outline_and_field_fits=per_side_deficit == 0,
            margin_change_alone_moves_centered_field=False,
            required_field_height_reduction_for_pq108_um=max(0, 2*(row_delta+108-field_edge_slack)),
            required_field_height_reduction_for_margin216_um=max(0, 2*(row_delta+216-field_edge_slack)),
            remedy='fixed outline requires explicit field/channel reshape; no dropped functional instances'),
        corridor_proposal=dict(path='vertical first inside s14W, then reserved new controller/mux band',
            historical_anchor_polyline_um=vertical_first, historical_anchor_length_um=length,
            native_host_source_and_destination_coordinates_pending=True,
            request_bits=290, reverse_credit_bits=1, true_ack_count_bits=8,
            nominal_reach_cap_um=cap, interior_spacing_um=spacing, endpoint_segment_cap_um=end_cap,
            estimated_stations_per_direction=stations, register_bits_floor=stations*long_bits,
            horizontal_track_width_floor_um=long_bits*0.048,
            initial_host_seats=8, boot_sector_rate_upper_bound_per_cycle=8/(2*stations+2),
            runtime_pc_added_cycles=contract['added_pipeline_cycles'],
            slot_reservation_before_generic_hops_required=True,
            native_pin_positions_clock_context_writeack_binding_pending=True),
        channel_reshape_candidate=dict(adopted=False,
            description='reduce each of seven channels64.8um while keeping all field frames and slots; placement/route capacity not yet qualified',
            proposed_reduction_per_channel_um=64.8, total_height_recovered_um=7*64.8,
            resulting_field_band_gap_um=field_edge_slack-row_delta+7*64.8/2,
            pq108_geometric_fit=field_edge_slack-row_delta+7*64.8/2 >=108,
            tracks_lost_per_channel_per_horizontal_layer=64.8/0.048,
            channel_ledger=channel_ledger,
            independent_current_channel_occupancy_must_be_repacked=True,
            fixed_field_instance_inventory_preserved_by_model=True),
        limitations=['analytical proposal only; no native die generation',
            'historical HOST anchors price a length estimate, not native endpoints',
            'source1/2/3 aperture and actual writeACK aggregation remain unbound',
            'routing layer capacity and buffers/CTS remain to measure',
            'protected queue sizing excludes other sequential state and logic'])
    args.output.mkdir(parents=True)
    (args.output/'budget.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (args.output/'pin_plan.csv').open('w') as out:
        writer = csv.DictWriter(out, fieldnames=list(next(iter(pins.values()))))
        writer.writeheader()
        writer.writerows(pins.values())
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
