#!/usr/bin/env python3
"""HBM-B-RTL1 2026-10-17 (plan (b) d4g): kit + literal face plan of the QUADRANT writer hsm_smvm_wrq_t4_r1 =
ot_hbm_sm_vm_wr_q_t_lanes4 (4 SM lanes, each driving 2 bank halves wq_s<k> / wq_t<k>; strap lbase).  Derived from
writer_lanes_plan.py (hsm_smvm_wrq_t_r5); lane k owns one 95 um band of the W face (its SM) and of the E face (wq_s<k> +
wq_t<k>, 562 bits, cut 0.57).  Original description:
Kit + literal face plan of the lane-root writer hsm_smvm_wrq_t_r5 (H-WRQ 2026-10-17, results/rtl/hsm_wrq_1017/DESIGN_NOTE.md).

Top ot_hbm_sm_vm_wr_q_t_lanes: one clock root per SM lane (clk_l0..7), shared core root clk (calendar + N-face host pins),
raw SRAM entry clk_cal.  Outline stays 142.56 x 388.8: the authoritative 0.096 um/bit, cut <= 0.60 pin rule needs >= 344 um
of W face (2,152 bits) and >= 360 um of E face (2,248 bits), so a square outline cannot carry the faces.  Each lane owns one
47.5 um band of the W face (rv/rrow/rdata/smf/sms + its clock entry at the band centre) and the matching band of the E face
(wq_s<k>), so lane k's pin flops, FIFO, server and launch flops share one root.  Recipe 4 (hold_budget "die": flop-first
pins, no pin pads).  Same track grid / readback check as writer_faces4_plan.py.
"""
from pathlib import Path
import json, sys, math, hashlib, copy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
from spread_face_pins import port_widths

NAME = 'hsm_smvm_wrq_t4_r1'
NL = 4
base = json.loads((ROOT / 'physical/ref_tile/hsm_smvm_wrq_t_r4/spec.json').read_text())
s = copy.deepcopy(base)
D = 'rtl/hbm_accel/generic/vm/static'
s['name'] = NAME
s['top'] = 'ot_hbm_sm_vm_wr_q_t_lanes4'
s['outline'] = {'w': 142.56, 'h': 388.8}
s['sources'] = [f'{D}/ot_hbm_sm_vm_wr_q_t_lanes4.sv', f'{D}/ot_hbm_sm_vm_wr_q_lanes_n.sv',
                'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv',
                'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
lanes = [f'clk_l{k}' for k in range(NL)]
s['clock_ports'] = ['clk'] + lanes + ['clk_cal']
s['clock_cts_roots'] = ['clk'] + lanes
north = [x for x in base['pins']['N'] if x != 'clk']
north.insert(north.index('quad') + 1, 'lbase')
outs = lambda k: [f'wq_s{k}', f'wq_t{k}']
win = lambda k: [f'rv_s{k}', f'rrow_s{k}', f'rdata_s{k}', f'smf_s{k}', f'sms_s{k}']
s['pins'] = {'W': sum(([*win(k), f'clk_l{k}'] for k in range(NL)), []), 'E': sum((outs(k) for k in range(NL)), []),
             'N': ['clk', 'clk_cal'] + north}
s['clock_entry_domains'] = {
    'core': {'ratio': [1, 1], 'ports': ['clk'], 'inputs': [x for x in north if x not in ['configured', 'fault', 'active']],
             'outputs': ['configured', 'fault', 'active']},
    'cal': {'ratio': [1, 1], 'ports': ['clk_cal'], 'inputs': [], 'outputs': []}}
for k in range(NL):
    s['clock_entry_domains'][f'lane{k}'] = {'ratio': [1, 1], 'ports': [f'clk_l{k}'], 'inputs': win(k), 'outputs': outs(k)}
# recipe 4: die boundary hold budget, flop-first pins (no pin pads)
s['recipe'] = 4
s['hold_budget'] = 'die'
s['inhold'] = False
s['outhold'] = False
s.pop('hold_pad', None)
s['pin_reg_split'] = False      # recipe 4 has no pin hook: the RTL keeps one o_wr launch flop per wq data pin
s['keep_pin_regs'] = True
s['pin_regs'] = {'enable': False, 'reason': ('every input lands in a source pin flop (lane k: rv/rrow/rdata/smf/sms on clk_l<k>; core: F20 bus in the folded collar, tgt/quad/lbase strap flops, rst_n local reset-release flop) and every output is a source flop (lane k wq_s<k> / wq_t<k>: o_v/o_sec/o_m (o2_*) and 8 kept o_wr (o2_wr) copies, one per replicated data pin; collar configured/fault/active)')}
s.pop('pin_ranges', None)
s['purpose'] = ('HBM-B-RTL1 2026-10-17 (owner 0do, plan (b) d4g): the QUADRANT SM result -> VM writer smw_<Q> (one master, 4 '
                'instances, strap quad + lbase): 4 SM lanes (one clock root each: pin flops + DEPTH-4 FIFO + server + two '
                'launch-flop sets for the bank halves LB+k / LB+k+4, chosen per descriptor by cmd[26]), core root = calendar / '
                'N-face host pins, clk_cal = table SRAM.  Lockstep with the d4f 8-SM writer: same rows/data/timing (rv(t) -> '
                'wq slot 0 at t+3), 0 edges added.')
s['structural_change'] = ('Plan (b): ot_hbm_sm_vm_wr_q_t_lanes (8 SMs, stack) -> ot_hbm_sm_vm_wr_q_t_lanes4 (4 SMs, quadrant, 8 bank '
                          'outputs as before); lane k drives wq_s<k> (bank LB+k) and wq_t<k> (bank LB+k+4 mod 8); calendar '
                          'payload 27 b (cmd[26] = bank half); bank-base strap lbase.  Outline unchanged (E face 2,248 bits).')
s['job'] = {
    'owner': 'Claude HBM-B-RTL1 1017', 'branch': 'claude/hbm-b-rtl1-vm-1017', 'tag': 'q4',
    'purpose': s['purpose'],
    'benches': [
        {'name': 'wrq4_lockstep', 'cmd': f'bash {D}/run_sm_vm_wr_q_t_lanes4.sh {{RUN}}/bench/wrq4', 'expect': 'pass',
         'pass_regex': 'WRQ4_LOCKSTEP BENCH PASS', 'threads': 1, 'peak_ram_gb': 4,
         'min_count_regex': 'SM-writer emissions ([0-9]+),'},
        {'name': 'mut_bank_base',
         'cmd': ('mkdir -p {RUN}/mut && iverilog -g2012 -DMUT=6 -s tb_hbm_sm_vm_wr_q_t_lanes4_lockstep -o {RUN}/mut/tb6 '
                 f'{D}/tb_hbm_sm_vm_wr_q_t_lanes4_lockstep.sv {D}/ot_hbm_sm_vm_wr_q_t_lanes4.sv {D}/ot_hbm_sm_vm_wr_q_lanes_n.sv '
                 f'{D}/ot_hbm_sm_vm_wr_q_t_lanes.sv {D}/ot_hbm_sm_vm_wr_q_lanes.sv rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv '
                 'rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv '
                 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v '
                 '&& vvp -n {RUN}/mut/tb6 > {RUN}/mut/tb6.log 2>&1 && cat {RUN}/mut/tb6.log '
                 "&& grep -q '^TB_WRQ4_LOCKSTEP PASS MUT=6' {RUN}/mut/tb6.log"),
         'expect': 'fail', 'threads': 1, 'peak_ram_gb': 4,
         'fail_regex': '^TB_WRQ4_LOCKSTEP FAIL MUT=6 mismatches[+]faults=[1-9][0-9]*$'}],
    'extra_paths': base['job'].get('extra_paths', []),
    'views_to': f'physical/ref_tile/{NAME}/views',
    'record_to': f'results/rtl/ref_tile/{NAME}'}

widths = port_widths(s, ROOT)
H = s['outline']['h']
bw = (384.468 - 4.332) / NL                         # lane band on W / E
clocks = {'clk': ('N', 71.292), 'clk_cal': ('N', 24.012)}
windows = []
for k in range(NL):
    a, b = 4.332 + k * bw, 4.332 + (k + 1) * bw
    a, b = round(a + 0.3, 3), round(b - 0.3, 3)       # 0.6 um gap between lane bands
    clocks[f'clk_l{k}'] = ('W', round(0.012 + 0.048 * round(((a + b) / 2 - 0.012) / 0.048), 3))
    windows.append((f'W_lane{k}', 'W', win(k), a, b))
    windows.append((f'E_lane{k}', 'E', outs(k), a, b))
windows.append(('N_core', 'N', north, 4.332, 138.228))
lines = ['# hsm_smvm_wrq_t4_r1 quadrant writer (HBM-B-RTL1): literal source-derived plan. Allocation 0.096um/bit, max cut 0.60.']
pins, metrics = {}, []


def emit(name, face, pos, clock=False):
    layer = 'M4' if face in ['W', 'E'] else 'M5'
    x = 0 if face == 'W' else s['outline']['w'] if face == 'E' else pos
    y = H if face == 'N' else pos
    size = (.084, .024) if clock and face in ['W', 'E'] else (.192, .024) if face in ['W', 'E'] else (.024, .084)
    assert name not in pins, name
    rect = [x - size[0] / 2, y - size[1] / 2, x + size[0] / 2, y + size[1] / 2]
    if face == 'W': rect[0] = 0; rect[2] = size[0]
    if face == 'E': rect[0] = x - size[0]; rect[2] = x
    if face == 'N': rect[1] = y - size[1]; rect[3] = y
    pins[name] = {'face': face, 'layer': layer, 'position_um': pos, 'clock': clock, 'rectangle_um': [round(z, 6) for z in rect]}
    lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} '
                 f'-pin_size {{{size[0]:.3f} {size[1]:.3f}}} -force_to_die_boundary')


for label, face, ports, a, b in windows:
    bits = []
    for p in ports:
        n, vec = widths[p]
        bits += [f'{p}[{i}]' if vec else p for i in range(n)]
    notches = [v for f, v in clocks.values() if f == face and a <= v <= b]
    phase = .012
    tracks = [round(phase + .048 * k, 3) for k in range(math.ceil((a - phase) / .048), math.floor((b - phase) / .048) + 1)]
    tracks = [x for x in tracks if all(abs(x - v) >= 1.08 - 1e-8 for v in notches)]
    usable = b - a - len(notches) * 2.16
    cut = len(bits) * .096 / usable
    assert cut <= .60, (label, len(bits), usable, cut)
    chosen = [tracks[round(i * (len(tracks) - 1) / (len(bits) - 1))] for i in range(len(bits))] if len(bits) > 1 else [tracks[len(tracks) // 2]]
    assert len(chosen) == len(set(chosen))
    assert all(y - x >= .096 - 1e-7 for x, y in zip(chosen, chosen[1:]))
    for p, x in zip(bits, chosen):
        emit(p, face, x)
    metrics.append({'window': label, 'data_bits': len(bits), 'span_um': [a, b], 'reserved_clock_centres_um': notches,
                    'usable_face_um': round(usable, 6), 'allocation_um_per_bit': .096, 'cut': round(cut, 4),
                    'minimum_physical_pin_pitch_um': round(min(y - x for x, y in zip(chosen, chosen[1:])), 6)})
for p, (face, pos) in clocks.items():
    emit(p, face, pos, True)
# readback check of the actual DB (same proc as the faces4 plan)
src = (ROOT / 'tools/hbm_sm_repack_1015/writer_faces4_plan.py').read_text()
proc = src[src.index("lines += ['global fp_b"):src.index("for name,v in pins.items():")]
exec(proc)
for name, v in pins.items():
    axis = 'Y' if v['face'] in ['W', 'E'] else 'X'
    rect = ' '.join(f'{x:.3f}' for x in v['rectangle_um'])
    lines.append(f"writer_pin_check {{{name}}} {v['layer']} {axis} {v['position_um']:.3f} {{{rect}}}")
lines += [f'if {{$fp_checked != {len(pins)}}} {{incr fp_bad}}', 'puts "WRITER_FACE_PIN_READBACK checked=$fp_checked violations=$fp_bad"',
          'if {$fp_bad} {error "Writer literal pins violate actual track/location"}']
expected = sum(n for n, _ in widths.values())
assert len(pins) == expected, (len(pins), expected)
pf = ROOT / 'physical/ref_tile_specs/smh/smvm_writer_lanes4_pins.tcl'
pf.write_text('\n'.join(lines) + '\n')
s['io_tcl'] = str(pf.relative_to(ROOT))
p = ROOT / f'physical/ref_tile/{NAME}'
p.mkdir(exist_ok=True)
(p / 'spec.json').write_text(json.dumps(s, indent=2) + '\n')
r = {'schema': 'opentallas.writer_lanes_pin_plan.v1', 'actual_top': s['top'], 'actual_clock_ports': s['clock_ports'],
     'outline_um': [142.56, 388.8], 'normal_data_edges_added': 0, 'windows': metrics,
     'full_face_bits': {f: sum(1 for v in pins.values() if v['face'] == f) for f in ['W', 'E', 'N']},
     'all_ports_accounted': expected, 'pinfile_sha256': hashlib.sha256(pf.read_bytes()).hexdigest(), 'pins': pins}
(ROOT / 'results/rtl/hbm_b_rtl1_1017').mkdir(parents=True, exist_ok=True)
(ROOT / 'results/rtl/hbm_b_rtl1_1017/writer_lanes4_pins.json').write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps({k: v for k, v in r.items() if k not in ('pins', 'windows')}, indent=1))
print('max cut', max(m['cut'] for m in metrics))
