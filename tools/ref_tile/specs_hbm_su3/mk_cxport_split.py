"""HBM-SU3 10-17: kits for the cxport split (coordinator 0dc: the 13.2k-pin-bit hub is split): ot_hbm_su_static_cxport_dl
(x4 per quarter, beside each pgslice; representative QID 2 / G 0), ot_hbm_su_static_cxport_ij (inject gather, QID 2) and
ot_hbm_su_static_cxport_rc (RED_CARRY + SFU operand, beside sucore). Two related roots (clk_s stream core 1/1, clk_q serial
4/3), epoch reset per domain."""
import json
from pathlib import Path
SRC = ['rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv']
BENCH = {'extra_paths': ['tools/hbm_static/su_cxport_split_run.sh',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/tb_hbm_su_cxport_split.sv',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport.sv'],
         'benches': [
             {'name': 'cxport_split_lockstep', 'cmd': 'bash tools/hbm_static/su_cxport_split_run.sh {RUN}/bench/pos 2 0 0 0',
              'expect': 'pass', 'pass_regex': 'CXPORT_SPLIT PASS', 'pass_witness': 'results/rtl/hbm_su3_1017/cxport_split_q2_pos.log',
              'min_count_regex': 'checks=(\\d+)', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
             {'name': 'cxport_split_mut2', 'cmd': 'bash tools/hbm_static/su_cxport_split_run.sh {RUN}/bench/mut2 2 0 2 1',
              'expect': 'fail', 'fail_regex': 'CXPORT_SPLIT FAIL', 'fail_witness': 'results/rtl/hbm_su3_1017/cxport_split_mut2.log',
              'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']}]}


def bits(spec):
    return spec


def mk(name, top, params, W, H, pins, B, core_in, core_out, ser_in, ser_out, std, why):
    pr = {}
    for f, order in pins.items():
        span = (H if f in 'WE' else W)
        if f == 'N':
            lo, hi = span / 2 - 6, span / 2 + 6
        else:
            lo, hi = 4.0, span - 4.0
        tot = sum(max(B[p], 2) for p in order); y = lo; gap = 0.6 if f == 'N' else 1.2
        sp = hi - lo - gap * (len(order) - 1)
        for p in order:
            w = sp * max(B[p], 2) / tot; pr[p] = [round(y, 3), round(y + w, 3)]; y += w + gap
    s = {'name': name, 'top': top, 'kind': 'tile', 'sources': SRC, 'params': params,
         'clock': 'multiple_cts_roots', 'clock_ports': ['clk_s', 'clk_q'], 'clock_port': 'clk_s',
         'reset_ports': ['rst_s_n', 'rst_q_n'], 'clock_data_paths': 'related_pll_ratio',
         'clock_relationship': {'kind': 'same_pll_fixed_phase', 'ratio': [4, 3], 'phase_ps': 0},
         'clock_entry_domains': {'core': {'ratio': [1, 1], 'ports': ['clk_s'], 'inputs': core_in + ['rst_s_n'], 'outputs': core_out},
                                 'serial': {'ratio': [4, 3], 'ports': ['clk_q'], 'inputs': ser_in + ['rst_q_n'], 'outputs': ser_out + ['fault']}},
         'outline': {'w': W, 'h': H, 'exact': True}, 'std_area_um2': std, 'layer_cap': 'M5', 'recipe': 4,
         'macros': [], 'children': [], 'inter': [], 'pins': pins, 'pin_ranges': pr,
         'route': {'pd': 0.5, 'period_ps': 833.333, 'threads': 8, 'peak_ram_gb': 12, 'hold_margin_ns': 0.03, 'macro_halo_um': 5.4,
                   'pin_h': 'M4', 'pin_v': 'M3 M5', 'pin_balance': {'h': 'M4', 'v': 'M3 M5', 'group_max': 1}, 'io_hold_margin_ns': 0.0},
         'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': False, 'outhold': False, 'keep_pin_regs': True, 'hold_budget': 'die',
         'pin_regs': {'enable': False, 'reason': 'Every pin is registered in RTL (cxport rule: stream inputs land in phase-indexed '
                      'pin slots, serial inputs in pin registers, every output is a register); a wrapper stage would move the '
                      'fixed 3:4 crossing edges.'},
         'structural_change': why,
         'job': {'owner': 'Claude:HBM-SU3', 'branch': 'claude/hbm-su3-1017', 'tag': 's1',
                 'purpose': 'HBM die d4f cxport split (0dc): ' + top, 'record_to': 'results/rtl/ref_tile/' + name,
                 'views_to': f'physical/ref_tile/{name}/views', 'auto_merge': False, **BENCH}}
    out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
    out.write_text(json.dumps(s, indent=1) + '\n'); print(out)


WHY = ('HBM-SU3 10-17 cxport SPLIT (coordinator 0dc: hub of 13.2k pin bits on 264.6 um): the quarter hub becomes 4 '
       'delivery leaves beside the pgslices, one inject-gather leaf and one RED_CARRY/SFU-operand leaf beside sucore; same '
       'epoch counters, slots and edges (lockstep vs the hub PASS QID 2 and QID 0/B39, split-only mutants 1-4 FAIL); the '
       'delivery calendar rule (lane j -> slice j) now FAULTs if broken. Every 3:4 crossing is MUX-ONLY (decode before the '
       'slot on the writer side; STA times stream->serial at the 1-quantum pair, 278 ps): the hub-equivalent dl gate showed '
       '-266 ps (dw_d after the slot decode) and rc -277 ps (64:1 SFU lane select); the SFU operand is registered whole and '
       'lane-selected on the next serial edge (compiler: SFU-source reducer command at E+1). ')
B = dict(del_valid=1, del_flit=545, del_obase=40, dw_v=2, dw_row=18, dw_d=1024, clk_s=1, clk_q=1, rst_s_n=1, rst_q_n=1, fault=1)
mk('hbm_su_cx_dl_1017', 'ot_hbm_su_static_cxport_dl', {'QID': 2, 'G': 0}, 108.0, 216.0,
   {'W': ['del_valid', 'del_obase', 'del_flit'], 'E': ['dw_v', 'dw_row', 'dw_d'], 'N': ['clk_s', 'clk_q', 'rst_s_n', 'rst_q_n', 'fault']},
   B, ['del_valid', 'del_flit', 'del_obase'], [], [], ['dw_v', 'dw_row', 'dw_d'], 2600,
   WHY + 'Leaf dl (G param; die x16): W COLL delivery lane (586 b stream, 2.8/um), E slice-G write port (1,044 b serial, '
   '4.9/um), clocks/resets/fault at the N centre; pin-bound 108x216.')
B = dict(inj_rd=2, inj_addr=160, inj_d=1024, inj_q0=1024, inj_q1=1024, inj_q2=1024, inj_q3=1024, clk_s=1, clk_q=1, rst_s_n=1, rst_q_n=1, fault=1)
mk('hbm_su_cx_ij_1017', 'ot_hbm_su_static_cxport_ij', {'QID': 2, 'B39_NOOP': 0, 'INJ_RET': 11}, 388.8, 388.8,
   {'W': ['inj_q0', 'inj_q1'], 'S': ['inj_q2', 'inj_q3'], 'E': ['inj_d', 'inj_rd', 'inj_addr'], 'N': ['clk_s', 'clk_q', 'rst_s_n', 'rst_q_n', 'fault']},
   B, ['inj_rd', 'inj_addr'], ['inj_d'], ['inj_q0', 'inj_q1', 'inj_q2', 'inj_q3'], [], 9000,
   WHY + 'Leaf ij: the four slices\' port-5 data (4,096 b serial) is intrinsic to the inject gather; inj_q over the full W '
   'face would be 10.6/um, so it is four 1,024-b slice ports, two on W and two on S (5.3/um); E COLL side inj_d 1,024 + request 162.')
B = dict(rc_v=1, rc_tag=3, rc_d=256, rr_v=1, rr_tag=3, rr_d=256, red_sv=1, red_tag=32, red_x=32, rr_wv=1, rr_wa=5, rr_wd=256,
         ro_v=16, ro_x=512, red_sel=12, sfu_x=32, clk_s=1, clk_q=1, rst_s_n=1, rst_q_n=1, fault=1)
mk('hbm_su_cx_rc_1017', 'ot_hbm_su_static_cxport_rc', {}, 216.0, 216.0,
   {'W': ['rr_v', 'rr_tag', 'rr_d', 'rc_v', 'rc_tag', 'rc_d', 'ro_v', 'ro_x'],
    'E': ['red_sv', 'red_tag', 'red_x', 'red_sel', 'rr_wv', 'rr_wa', 'rr_wd', 'sfu_x'],
    'N': ['clk_s', 'clk_q', 'rst_s_n', 'rst_q_n', 'fault']},
   B, ['rr_v', 'rr_tag', 'rr_d', 'ro_v', 'ro_x'], ['rc_v', 'rc_tag', 'rc_d'], ['red_sv', 'red_tag', 'red_x', 'red_sel'],
   ['rr_wv', 'rr_wa', 'rr_wd', 'sfu_x'], 4200,
   WHY + 'Leaf rc: W COLL/SFU stream side (1,048 b, 4.9/um), E sucore serial side (373 b), clocks at the N centre.')
