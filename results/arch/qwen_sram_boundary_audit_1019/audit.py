#!/usr/bin/env python3
"""Bounded source/view inspection, not synthesis, STA or behavioral simulation."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
MASTER = 'ot_sram_1r1w2c_32x64_m1'
BASE = ROOT / 'physical/asap7_memory_macros_v2' / MASTER
MODEL = ROOT / 'results/arch/qwen_d8_hybrid_model_1019/model.json'

def blocks(text, kind):
    found = []
    for match in re.finditer(r'\b' + kind + r'\s*\(([^)]*)\)\s*\{', text):
        start = cursor = match.end()
        depth = 1
        while depth:
            depth += (text[cursor] == '{') - (text[cursor] == '}')
            cursor += 1
        found.append((match.group(1).strip(), text[start:cursor - 1]))
    return found

def prop(text, name):
    match = re.search(r'\b' + name + r'\s*:\s*([^;]+);', text)
    return match.group(1).strip().strip('"') if match else None

def table(text, name):
    matches = blocks(text, name)
    if not matches:
        return None
    body = matches[0][1]
    values = re.search(r'values\s*\((.*?)\)\s*;', body, re.S).group(1)
    rows = [[float(x) for x in row.split(',')] for row in re.findall(r'"([^"]+)"', values)]
    indexes = {f'index_{n}': [float(v) for v in re.search(
        rf'index_{n}\s*\("([^"]+)"\)', body).group(1).split(',')] for n in (1, 2)}
    return {'rows': rows, 'min_ps': min(map(min, rows)), 'max_ps': max(map(max, rows)),
            **indexes}

model = json.loads(MODEL.read_text())
hashes = {}
for path, expected in model['macro']['view_sha256'].items():
    actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert actual == expected, (path, actual, expected)
    hashes[path] = actual

corners = {}
for corner in ('tt', 'ff', 'ss'):
    text = (BASE / f'{MASTER}_{corner}.lib').read_text()
    assert 'time_unit : "1ps"' in text
    pins = {}
    for name, body in blocks(text, '(?:bus|pin)'):
        arcs = []
        for _, timing in blocks(body, 'timing'):
            arcs.append({'related_pin': prop(timing, 'related_pin'),
                         'timing_type': prop(timing, 'timing_type'),
                         **{key: table(timing, key) for key in
                            ('rise_constraint', 'fall_constraint', 'cell_rise', 'cell_fall')}})
        cap = prop(body, 'capacitance')
        pins[name] = {'direction': prop(body, 'direction'), 'arcs': arcs,
                      'clock': prop(body, 'clock'), 'capacitance_fF': float(cap) if cap else None,
                      'min_period_ps': prop(body, 'min_period'),
                      'min_pulse_high_ps': prop(body, 'min_pulse_width_high'),
                      'min_pulse_low_ps': prop(body, 'min_pulse_width_low')}
    for name in ('wd_in', 'w_addr_in', 'w_ce_in', 'w_mask_in', 'r_addr_in', 'r_ce_in'):
        clock = 'rclk' if name.startswith('r_') else 'wclk'
        assert {(a['related_pin'], a['timing_type']) for a in pins[name]['arcs']} == {
            (clock, 'setup_rising'), (clock, 'hold_rising')}
    assert {(a['related_pin'], a['timing_type']) for a in pins['rd_out']['arcs']} == {('rclk', 'rising_edge')}
    corners[corner] = pins

lef = (BASE / f'{MASTER}.lef').read_text()
contacts = []
for match in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$', lef, re.M | re.S):
    name, body = match.groups()
    layer = re.search(r'LAYER (\S+) ;', body).group(1)
    rects = [[float(v) for v in row.split()] for row in re.findall(r'RECT ([\d. ]+) ;', body)]
    group = name.split('[')[0]
    if name in ('VDD', 'VSS'):
        role, edge, clock, qualified = 'power', None, None, False
    else:
        edge = 'W' if rects[0][0] == 0 else 'E'
        clock = ('rclk' if group in ('r_addr_in', 'r_ce_in', 'rd_out') else 'wclk')
        role = ('clock' if group in ('rclk', 'wclk') else
                'registered_read_output' if group == 'rd_out' else
                'write_payload' if group == 'wd_in' else
                'write_address' if group == 'w_addr_in' else
                'write_enable' if group == 'w_ce_in' else
                'write_mask' if group == 'w_mask_in' else
                'read_address' if group == 'r_addr_in' else 'read_enable')
        qualified = role not in ('clock',)
        assert group in corners['tt']
    contacts.append({'pin': name, 'group': group, 'role': role, 'layer': layer,
                     'rects_um': rects, 'face': edge, 'capture_clock': clock,
                     'native_edge_endpoint_semantics': qualified,
                     'candidate_physical_binding': None, 'routed_contact_access': None})
assert len(contacts) == 208
assert sum(c['face'] == 'W' for c in contacts) == 103
assert sum(c['face'] == 'E' for c in contacts) == 103
face_occupancy = {}
for face in ('W', 'E'):
    centers = sorted((c['rects_um'][0][1] + c['rects_um'][0][3]) / 2
                     for c in contacts if c['face'] == face)
    pitch = min(b - a for a, b in zip(centers, centers[1:]))
    face_occupancy[face] = {'contacts': len(centers), 'full_face_um': 17.304,
                            'full_face_average_per_um': len(centers) / 17.304,
                            'first_center_y_um': centers[0], 'last_center_y_um': centers[-1],
                            'min_pitch_um': pitch,
                            'populated_interval_density_per_um': (len(centers)-1)/(centers[-1]-centers[0]),
                            'full_face_spread_le6_per_um': False}

behavior = (BASE / f'{MASTER}.v').read_text()
write = 'always @(posedge wclk) if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);'
read = 'always @(posedge rclk) if (r_ce_in) rd_out <= word_read(r_addr_in);'
assert write in behavior and read in behavior
assert 'if (m[b] && n != 0)' in behavior
assert '`ifndef OT_MEM_NO_INIT' in behavior
assert not re.search(r'assign\s+rd_out\b', behavior)

banks = []
for lane in model['rows']:
    if not lane['macros']:
        continue
    width = lane['width']; record = width + 5
    for bank in range(lane['macros']):
        lo, hi = 64 * bank, min(record - 1, 64 * bank + 63)
        banks.append({'candidate_id': f"{lane['historical']['bid']}.bank{bank}",
                      'instance': None, 'bus': lane['bus'], 'master': MASTER,
                      'record_lo': lo, 'record_hi': hi, 'live_bits': hi - lo + 1,
                      'payload_bits': max(0, min(width - 1, hi) - lo + 1),
                      'epoch_record_bits': list(range(max(lo, width), min(hi, width + 3) + 1)),
                      'written_record_bit': width + 4 if lo <= width + 4 <= hi else None,
                      'inactive_high_bits': 64 - (hi - lo + 1),
                      'write_address_model': "{2'b00,wc[2:0]}",
                      'write_clock_pin': 'wclk', 'read_clock_pin': 'rclk',
                      'actual_final_forwarded_write_clock': None,
                      'actual_receiver_read_clock': None,
                      'historical_source_root_not_binding': lane['source_root'],
                      'historical_receiver_root_not_binding': lane['receiver_root'],
                      'production_K': None, 'reset_epoch': None, 'first_use': None,
                      'physical_origin_orientation': None,
                      'all_contact_access': None, 'PG_connected': None,
                      'boundary_permission': 'CONDITIONAL_NATIVE_STORAGE_ENDPOINT_ONLY'})
assert len(banks) == 26 and sum(b['payload_bits'] for b in banks) == 1521
assert sum(b['live_bits'] for b in banks) == 1536

result = {'status': 'NATIVE_VIEW_ENDPOINT_SEMANTICS_ONLY; PRODUCTION_BOUNDARY_HOLD',
          'model_commit': 'dee8d6b3a0b725535b001a12527da11c2f0c87d8',
          'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
          'exact_source_hashes': hashes, 'corners': corners, 'master_contacts': contacts,
          'physical_face_occupancy': face_occupancy,
          'candidate_banks': banks, 'candidate_macro_clock_contacts': 52,
          'candidate_signal_contacts_including_clocks': 5356, 'candidate_PG_pins': 52,
          'behavioral_write_statement': write, 'behavioral_read_statement': read,
          'collision_policy': 'FORBIDDEN simultaneous cross-clock same-address R/W; no OLD guarantee',
          'initialization': 'OT_MEM_NO_INIT; arbitrary memory and rd_out; external eight valid bits per lane required',
          'write_edge': 'W at macro wclk, conditional actual producer setup/hold/ownership proof',
          'read_output_edges': 'macro samples at R; separate output FF captures prior macro output at R+1',
          'extra_input_FF_justified_by_this_audit': False,
          'new_RTL': False, 'new_heavy_jobs': False, 'timing_qualified': False,
          'physical_qualified': False, 'production_qualified': False}
(OUT / 'ledger.json').write_text(json.dumps(result, indent=2) + '\n')
with (OUT / 'candidate_contacts.csv').open('w') as stream:
    writer = csv.writer(stream)
    writer.writerow(['candidate_bank', 'actual_instance', 'pin', 'role', 'capture_clock',
                     'layer', 'face', 'native_semantics', 'physical_binding', 'routed_access'])
    for bank in banks:
        for pin in contacts:
            writer.writerow([bank['candidate_id'], '', pin['pin'], pin['role'], pin['capture_clock'],
                             pin['layer'], pin['face'], pin['native_edge_endpoint_semantics'], '', ''])
with (OUT / 'clock_contacts.csv').open('w') as stream:
    writer = csv.writer(stream)
    writer.writerow(['candidate_bank', 'pin', 'actual_net', 'native_phase', 'reset_epoch'])
    for bank in banks:
        for clock in ('wclk', 'rclk'):
            writer.writerow([bank['candidate_id'], clock, '', '', ''])
print('PASS inspection: exact 7 macro views + 6 compiler/calibration hashes; 206 signal + 2 PG pins; 26 banks, 52 clocks')
print('HOLD physical: 0.096um local face pitch / 10.4167 contacts per um; full-face average hides clustering')
