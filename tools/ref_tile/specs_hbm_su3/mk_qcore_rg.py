"""HBM-SU3 10-17: qcore successor r5 kit (coordinator 0dc: regional roots, not 66; re-homed beside its pgslices by
H-DIE-R7b/R8b). ot_hbm_su_static_qcore_r5 (COLLPORT 1, RF_LOCAL 1): single-copy RF + selected read pipeline (~77k ->
~10k flops), pins first; one root clk_ctl. Faces as the die grant (W slice side, E channel side, N clocks),
pins spread over the full faces (<= 6/um). Outline 216^2 (slot 330.48^2 -> slot_change_request)."""
import json
from pathlib import Path
name = 'hbm_su_qcore_r5_1017'
W = H = 216.0
B = dict(rf_bword=128, rf_bcmd=36, rf_dsec=256, slice_x=128, rf_drain_cmd=2, rf_rd_cmd=54, red_cmd=74, fault=1,
         rf_wv=4, rf_wa=32, rf_wd=128, red_sv=1, red_tag=32, red_x=32, red_rf_v=1, rr_wv=1, rr_wa=5, rr_wd=256, sfu_x=32,
         clk_ctl=1, rst_n=1)
pins = {'W': ['rf_bword', 'rf_bcmd', 'rf_dsec', 'slice_x', 'rf_drain_cmd', 'rf_rd_cmd', 'red_cmd', 'fault'],
        'E': ['rf_wv', 'rf_wa', 'rf_wd', 'red_sv', 'red_tag', 'red_x', 'red_rf_v', 'rr_wv', 'rr_wa', 'rr_wd', 'sfu_x'],
        'N': ['clk_ctl', 'rst_n']}


def ranges(order, lo, hi, gap=1.2):
    tot = sum(max(B[p], 2) for p in order); span = hi - lo - gap * (len(order) - 1); out = {}; y = lo
    for p in order:
        w = span * max(B[p], 2) / tot; out[p] = [round(y, 3), round(y + w, 3)]; y += w + gap
    return out


pr = {}
pr.update(ranges(pins['W'], 6.0, H - 6.0)); pr.update(ranges(pins['E'], 6.0, H - 6.0))
pr.update(ranges(pins['N'], W / 2 - 8, W / 2 + 8, gap=0.6))
SRC = ['rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore_r5.sv',

       'rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv',
       'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
       'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
s = {
    'name': name, 'top': 'ot_hbm_su_static_qcore_r5', 'kind': 'tile', 'sources': SRC,
    'params': {'MUT': 0, 'COLLPORT': 1, 'RF_LOCAL': 1},
    'clock_port': 'clk_ctl', 'reset_ports': ['rst_n'],
    'outline': {'w': W, 'h': H, 'exact': True}, 'std_area_um2': 16500, 'slot_change_request': 'HBM-SU3 10-17 -> H-DIE: sucore_<q> r5 is 216x216 (was 330.48^2): ~10k flops instead of ~77k; faces unchanged (W slice, E channel, N clocks); clk_rf[63:0] entries removed', 'layer_cap': 'M5', 'recipe': 3,
    'macros': [{'view': 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2', 'count': 1, 'at': [86.4, 43.2], 'inst': 'u_red.ma'},
               {'view': 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2', 'count': 1, 'at': [86.4, 129.6], 'inst': 'u_red.mb'}],
    'children': [], 'inter': [], 'pins': pins, 'pin_ranges': pr,
    'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': True, 'outhold': True, 'keep_pin_regs': True,
    'pin_reg_split': True, 'hold_pad': {'cell': 'HB2xp67_ASAP7_75t_R'},
    'pin_regs': {'enable': False, 'reason': 'The RF read commands, relay writers and COLL writer are captured raw at the '
                 'pins (the hub bank rung moved to the pin); reducer command, slice/SFU '
                 'operands and drain decode land in clk_ctl registers; every output is a flop. A wrapper stage would add '
                 'an edge to the fixed n+1 commit / n+3 read / E+11 scalar calendar.'},
    'route': {'pd': 0.52, 'threads': 8, 'peak_ram_gb': 32, 'period_ps': 1111.111,
              'pin_balance': {'group_max': 1, 'h': 'M4', 'v': 'M3 M5'}, 'hold_margin_ns': 0.03, 'macro_halo_um': 5.4},
    'structural_change': ('HBM-SU3 10-17 qcore r5 (coordinator 0dc): ot_hbm_su_static_qcore_r5 replaces the 66-root '
        'qcore (64 per-bank clk_rf + ctl + red; codex hbm_qcore_s_pinrung_r2, 76k FF on 330.48^2). One RF copy (8,192 '
        'flops) instead of six per-reader replicas, and only the selected word per read class is registered (raw k+1, '
        'rd k+2) instead of a raw/read_data register per (bank, reader) + bank-select mux: ~11.5k flops, ONE root '
        'clk_ctl (reducer SRAMs on it; g1 gate: clk_red reached SRAM clock pins, CTS refused a separate root). Read: '
        'per-sector word at k+1 from a per-sector address copy, sector select at k+2 (g1: 8,192-load address nets). Pins first (raw command/writer capture at k, decode after the flop). Same edges: commit '
        'k+1, rf_bword/rf_dsec k+3, scalar E+11; write-conflict FAULT +1 edge; invalid-read output words are don\'t-care '
        '(documented). Reducer SRAMs stacked on the 43.2 lattice; die faces kept (W slice, E channel, N clocks). '
        'Re-home: H-DIE-R7b/R8b grants put sucore_<q> beside its pgslices.'),
    'job': {'owner': 'Claude:HBM-SU3', 'branch': 'claude/hbm-su3-1017', 'tag': 'r5',
            'purpose': 'HBM die d4f sucore_<q> = ot_hbm_su_static_qcore_r5 (2 roots, single-copy RF, pins first)',
            'record_to': 'results/rtl/ref_tile/' + name, 'views_to': f'physical/ref_tile/{name}/views', 'auto_merge': False,
            'extra_paths': ['tools/hbm_static/su_qcore_rg_run.sh', 'rtl/test/hbm_qcore_physical_1016/tb_qcore_rg_lockstep.sv'],
            'benches': [
                {'name': 'qcore_r5_lockstep', 'cmd': 'bash tools/hbm_static/su_qcore_rg_run.sh {RUN}/bench/pos 0', 'expect': 'pass',
                 'pass_regex': 'QCORE_RG PASS', 'pass_witness': 'results/rtl/hbm_su3_1017/qcore_r5_pos.log',
                 'min_count_regex': 'checks=(\\d+)', 'threads': 1, 'peak_ram_gb': 4, 'needs': ['iverilog']},
                {'name': 'qcore_r5_mut256', 'cmd': 'bash tools/hbm_static/su_qcore_rg_run.sh {RUN}/bench/mut 256', 'expect': 'fail',
                 'fail_regex': 'QCORE_RG FAIL', 'fail_witness': 'results/rtl/hbm_su3_1017/qcore_r5_mut256.log',
                 'threads': 1, 'peak_ram_gb': 4, 'needs': ['iverilog']}]},
}
out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
out.write_text(json.dumps(s, indent=1) + '\n'); print(out)
