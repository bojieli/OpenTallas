#!/usr/bin/env python3
"""Writer r5 (H-SM 1817): square-ish successor of hsm_smvm_wrq_t_r4 (142.56 x 388.8, 2.7:1, pin-limited).

Same RTL as f4hc (ot_hbm_sm_vm_wr_q_t_faces4 with the clk_hcfg host pin-flop entry).  Outline 265.68 x 265.68; every
face carries ONE half-bus group over its full length at <= 6 pins/um (0.096 um/bit allocation, cut <= 0.60):
  W  host bus (cfg/desc/launch/tgt/quad/rst/status) + clk + clk_hcfg | rdata_lo group + clk_in_lo + clk_cal
  S  rdata_hi group + clk_in_hi
  E  wq_lo + clk_out_lo
  N  wq_hi + clk_out_hi
Each half-bus keeps its own face clock entry at the centre of its window (register mass next to the entry).
Recipe 4: flop-first pins (RTL registers every pin), no in/out hold pads, hold_budget die.
"""
from pathlib import Path
import json, math, hashlib

ROOT = Path(__file__).resolve().parents[2]
S = 265.68
base = json.loads((ROOT / 'physical/ref_tile/hsm_smvm_wrq_t_r4/spec.json').read_text())
s = json.loads(json.dumps(base))
s['name'] = 'hsm_smvm_wrq_t_r5'
s['outline'] = {'w': S, 'h': S}
# table SRAM (94.824 x 41.04) on the 43.2 um lattice, centred in x, >= 20 um from every pin face
s['macros'][0]['at'] = [86.4, 172.8]

W = {'rv': 4, 'rrow': 48, 'rdata': 1024, 'sm_fault': 4, 'sm_sched_fault': 4}
low = ['rv_lo', 'rrow_lo', 'rdata_lo', 'sm_fault_lo', 'sm_sched_fault_lo']
high = [x.replace('_lo', '_hi') for x in low]
host = ['rst_n', 'tgt', 'quad', 'cfg_v', 'cfg_target', 'cfg_addr', 'cfg_data', 'desc_v', 'desc_base', 'desc_limit',
        'desc_loops', 'launch_v', 'configured', 'fault', 'active']
widths = {'rst_n': 1, 'tgt': 8, 'quad': 2, 'cfg_v': 1, 'cfg_target': 8, 'cfg_addr': 12, 'cfg_data': 256, 'desc_v': 1,
          'desc_base': 12, 'desc_limit': 13, 'desc_loops': 16, 'launch_v': 1, 'configured': 1, 'fault': 1, 'active': 1,
          'wq_lo': 1124, 'wq_hi': 1124}
for p in low + high:
    widths[p] = W[p.rsplit('_', 1)[0]]
vec = {p: not (widths[p] == 1 and p in ('rst_n', 'cfg_v', 'desc_v', 'launch_v', 'configured', 'fault', 'active'))
       for p in widths}

s['pins'] = {'W': ['clk', 'clk_hcfg'] + host + low + ['clk_in_lo', 'clk_cal'], 'S': high + ['clk_in_hi'],
             'E': ['wq_lo', 'clk_out_lo'], 'N': ['wq_hi', 'clk_out_hi']}
a0, a1 = 4.332, round(S - 4.332, 3)
HOST_END = 68.012
clocks = {'clk': ('W', 30.012), 'clk_hcfg': ('W', 42.012), 'clk_in_lo': ('W', 165.612), 'clk_cal': ('W', 194.412),
          'clk_in_hi': ('S', 132.012), 'clk_out_lo': ('E', 132.012), 'clk_out_hi': ('N', 132.012)}
windows = [('W_host', 'W', host, a0, HOST_END), ('W_lo', 'W', low, HOST_END + 2.16, a1),
           ('S_hi', 'S', high, a0, a1), ('E_lo', 'E', ['wq_lo'], a0, a1), ('N_hi', 'N', ['wq_hi'], a0, a1)]

lines = ['# Writer r5 square plan (tools/hbm_sm_repack_1015/writer_r5_square_plan.py). Allocation 0.096 um/bit, cut <= 0.60, <= 6 pins/um.']
pins, metrics = {}, []


def emit(name, face, pos, clock=False):
    layer = 'M4' if face in ('W', 'E') else 'M5'
    x = 0 if face == 'W' else S if face == 'E' else pos
    y = 0 if face == 'S' else S if face == 'N' else pos
    size = (.084, .024) if clock and face in ('W', 'E') else (.192, .024) if face in ('W', 'E') else (.024, .084)
    assert name not in pins, name
    rect = [x - size[0] / 2, y - size[1] / 2, x + size[0] / 2, y + size[1] / 2]
    if face == 'W': rect[0], rect[2] = 0, size[0]
    if face == 'E': rect[0], rect[2] = x - size[0], x
    if face == 'N': rect[1], rect[3] = y - size[1], y
    if face == 'S': rect[1], rect[3] = 0, size[1]
    pins[name] = {'face': face, 'layer': layer, 'position_um': pos, 'clock': clock, 'rectangle_um': [round(z, 6) for z in rect]}
    lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} '
                 f'-pin_size {{{size[0]:.3f} {size[1]:.3f}}} -force_to_die_boundary')


for label, face, ports, a, b in windows:
    bits = []
    for p in ports:
        n = widths[p]
        bits += [f'{p}[{i}]' if vec[p] else p for i in range(n)]
    notches = [v for f, v in clocks.values() if f == face and a <= v <= b]
    phase = .012
    tracks = [round(phase + .048 * k, 3) for k in range(math.ceil((a - phase) / .048), math.floor((b - phase) / .048) + 1)]
    tracks = [x for x in tracks if all(abs(x - v) >= 1.08 - 1e-8 for v in notches)]
    usable = b - a - len(notches) * 2.16
    cut = len(bits) * .096 / usable
    dens = len(bits) / usable
    assert cut <= .60 and dens <= 6.0, (label, len(bits), usable, cut, dens)
    chosen = [tracks[round(i * (len(tracks) - 1) / (len(bits) - 1))] for i in range(len(bits))]
    assert len(chosen) == len(set(chosen)) and all(y - x >= .096 - 1e-7 for x, y in zip(chosen, chosen[1:]))
    for p, x in zip(bits, chosen):
        emit(p, face, x)
    metrics.append({'window': label, 'face': face, 'data_bits': len(bits), 'span_um': [a, b], 'clock_notches_um': notches,
                    'usable_um': round(usable, 3), 'pins_per_um': round(dens, 3), 'cut': round(cut, 4)})
for p, (face, pos) in clocks.items():
    emit(p, face, pos, True)

lines += ['global fp_b fp_u fp_bad fp_checked', 'set fp_b [ord::get_db_block]', 'set fp_u [$fp_b getDbUnitsPerMicron]',
          'set fp_bad 0', 'set fp_checked 0', '''
proc writer_pin_check {name layer axis pos rect} {
 global fp_b fp_u fp_bad fp_checked
 set t [$fp_b findBTerm $name]
 if {$t eq "NULL" || $t eq ""} {incr fp_bad; puts "WRITER_FACE_PIN_MISSING $name";return}
 if {[llength [$t getBPins]] != 1} {incr fp_bad; puts "WRITER_FACE_BPIN_COUNT $name";return}
 set p [lindex [$t getBPins] 0]
 if {[llength [$p getBoxes]] != 1} {incr fp_bad; puts "WRITER_FACE_BOX_COUNT $name";return}
 set q [lindex [$p getBoxes] 0]
 incr fp_checked
 set l [$q getTechLayer]
 set actual [list [expr {[$q xMin]/double($fp_u)}] [expr {[$q yMin]/double($fp_u)}] [expr {[$q xMax]/double($fp_u)}] [expr {[$q yMax]/double($fp_u)}]]
 foreach a $actual e $rect {if {abs($a-$e)>0.0001} {incr fp_bad; puts "WRITER_FACE_RECT_ERROR $name $actual expected $rect";break}}
 if {$axis eq "Y"} {set c [expr {([$q yMin]+[$q yMax])/2.0}]} else {set c [expr {([$q xMin]+[$q xMax])/2.0}]}
 set g [[$fp_b findTrackGrid $l] getGrid$axis]
 if {abs($c/double($fp_u)-$pos)>0.0001 || [$l getName] ne $layer || [lsearch -exact $g [expr {int(round($c))}]]<0} {
  incr fp_bad; puts "WRITER_FACE_PIN_ERROR $name"
 }
}
''']
for name, v in pins.items():
    axis = 'Y' if v['face'] in ('W', 'E') else 'X'
    rect = ' '.join(f'{x:.3f}' for x in v['rectangle_um'])
    lines.append(f"writer_pin_check {{{name}}} {v['layer']} {axis} {v['position_um']:.3f} {{{rect}}}")
lines += [f'if {{$fp_checked != {len(pins)}}} {{incr fp_bad}}',
          'puts "WRITER_FACE_PIN_READBACK checked=$fp_checked violations=$fp_bad"',
          'if {$fp_bad} {error "Writer literal pins violate actual track/location"}']
expected = sum(widths.values()) + len(clocks)
assert len(pins) == expected, (len(pins), expected)

pf = ROOT / 'physical/ref_tile_specs/smh/smvm_writer_r5_square_pins.tcl'
pf.write_text('\n'.join(lines) + '\n')
s['io_tcl'] = str(pf.relative_to(ROOT))
# recipe 4: flop-first pins, no in/out hold pads, die boundary hold budget
s['recipe'] = 4
s['hold_budget'] = 'die'
s['inhold'] = False
s['outhold'] = False
for k in ('hold_pad', 'pin_reg_split'):
    s.pop(k, None)
s['route']['io_hold_margin_ns'] = 0.0
s['route']['hold_margin_ns'] = 0.03
j = s['job']
j.update(owner='Claude H-SM 1817', branch='claude/hsm-wrq-r5-1817', tag='sq1',
         views_to='physical/ref_tile/hsm_smvm_wrq_t_r5/views', record_to='results/rtl/ref_tile/hsm_smvm_wrq_t_r5',
         purpose='writer r5: square 265.68 x 265.68 (was 142.56 x 388.8, 2.7:1 pin-limited), one half-bus group per full '
                 'face at <= 6 pins/um, face clock entry at each window centre, clk_hcfg host pin-flop entry (f4hc RTL), '
                 'recipe 4 (no pin hold pads, hold_budget die).')
j.pop('hold_eco', None)
j['reroute_reason'] = {
    'kind': 'slot_change', 'source': 'results/hbm_sm_attention_1015/hsm_1815/writer_c8e94d78d_native.json',
    'cell': 'ot_hbm_sm_vm_wr_q_t_faces4',
    'fix': 'c8e94d78d native capture 213.2 (late core-root leaf -> 6 hold BUFx2 per host input); f4e5 (hold ECO goal 5) '
           'NEEDS_RTL TT -37.85/FF -27.04; f4hc (clk_hcfg entry) NEEDS_RTL TT -46.54/FF -9.57 in the 2.7:1 pin-limited '
           'outline. r5 = square 265.68 x 265.68, each half-bus on its own full face (<= 6 pins/um), recipe 4.'}
s['structural_change'] = (s.get('structural_change', '') + ' r5 (Claude H-SM 1817): square 265.68 x 265.68 outline, '
                          'faces W host+rdata_lo / S rdata_hi / E wq_lo / N wq_hi, <= 6 pins/um, recipe 4 (no pin hold pads, '
                          'hold_budget die), clk_hcfg host entry kept.')
p = ROOT / 'physical/ref_tile/hsm_smvm_wrq_t_r5'
p.mkdir(exist_ok=True)
(p / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
r = {'schema': 'opentallas.writer_r5_square_pins.v1', 'outline_um': [S, S], 'windows': metrics,
     'face_bits': {f: sum(1 for v in pins.values() if v['face'] == f) for f in 'WSEN'},
     'pinfile_sha256': hashlib.sha256(pf.read_bytes()).hexdigest()}
(p / 'pin_plan.json').write_text(json.dumps(r, indent=1) + '\n')
print(json.dumps(r, indent=1))
