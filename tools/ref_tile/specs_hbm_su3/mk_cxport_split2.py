"""HBM-CXDL 10-18: kits for the ONE-ROOT halves of the cxport dl and rc leaves (routes hbm_su_cx_dl_1017-s2-761317600 /
hbm_su_cx_rc_1017-s2-761317600 NEEDS_RTL: a 3:4 crossing inside a two-root leaf is timed at the VCO tick (1q setup,
coincident-edge hold) less the 150 / 100 distinct-entry reserve and cannot close; tools/ref_tile/README). Precedent: S81
ot_s81_vm_x34_s/_t (closed 10-16) and RBH-SFUS ot_hbm_su_bridge_release_s (closed 10-18). Each half has one clock root
(stream halves clk_s, serial halves clk_q; both signed off at 833.333 ps, the serial half conservatively at the stream
period as bridge_release_s). The 2-bank seam (>= 3 quanta both windows by the static calendar) is a die-level 3:4 seam
arc (epoch multicycle owned by die STA), the halves abut."""
import json
from pathlib import Path
SRC = ['rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv']
LOG = 'results/rtl/hbm_cxdl_1018/'
BENCH = {'extra_paths': ['tools/hbm_static/su_cxport_split_run.sh',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/tb_hbm_su_cxport_split.sv',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport.sv'],
         'benches': [
             {'name': 'cxport_split_lockstep', 'cmd': 'bash tools/hbm_static/su_cxport_split_run.sh {RUN}/bench/pos 2 0 0 0',
              'expect': 'pass', 'pass_regex': 'CXPORT_SPLIT PASS', 'pass_witness': LOG + 'cxport_split2_q2_pos.log',
              'min_count_regex': 'checks=(\\d+)', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
             {'name': 'cxport_split_mut4', 'cmd': 'bash tools/hbm_static/su_cxport_split_run.sh {RUN}/bench/mut4 2 0 4 1',
              'expect': 'fail', 'fail_regex': 'CXPORT_SPLIT FAIL', 'fail_witness': LOG + 'cxport_split2_mut4.log',
              'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']}]}
WHY = ('HBM-CXDL 10-18: the two-root cxport leaves failed route (dl 761317600: TT -166.7 / FF hold -95.1 on 1,045 '
       'dl_slot -> dw_d endpoints, hold repair stalled because the same endpoints fail setup; rc: TT -173.4 / FF -77.9 '
       'on ro_slot / rr_slot1 -> serial and rc_slot -> pend / rc_d). Cause: NOT tree skew (clk_s / clk_q leaf insertion '
       'differ ~47 ps) but the 3:4 crossing inside one leaf, which ordinary related-clock STA times at the VCO tick '
       '(setup 277.8 ps, hold at the coincident edge) less the 150 / 100 distinct-entry reserve. Fix (S81 x34 _s/_t and '
       'bridge_release_s precedent): each leaf splits into a stream half and a serial half with ONE root each; the '
       'crossing becomes a 2-bank seam (events alternate banks; static calendar windows >= 3 quanta for setup and for '
       'rewrite-after-read), a die-level 3:4 seam arc. Same edges and outputs: lockstep vs the hub PASS QID 2 and QID 0 '
       '(checks=24183, as before); mutants 2/3/4 FAIL. ')


def mk(name, top, params, ck, rst, W, H, pins, B, std, why):
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
         'clock_port': ck, 'reset_ports': [rst],
         'outline': {'w': W, 'h': H, 'exact': True}, 'std_area_um2': std, 'layer_cap': 'M5', 'recipe': 4,
         'macros': [], 'children': [], 'inter': [], 'pins': pins, 'pin_ranges': pr,
         'route': {'pd': 0.5, 'period_ps': 833.333, 'threads': 8, 'peak_ram_gb': 12, 'hold_margin_ns': 0.03, 'macro_halo_um': 5.4,
                   'pin_h': 'M4', 'pin_v': 'M3 M5', 'pin_balance': {'h': 'M4', 'v': 'M3 M5', 'group_max': 1}, 'io_hold_margin_ns': 0.03},
         'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': False, 'outhold': False, 'keep_pin_regs': True, 'hold_budget': 'die',
         'pin_regs': {'enable': False, 'reason': 'Every pin is registered in RTL (inputs land in pin registers / banks, every '
                      'output is a register); a wrapper stage would move the fixed 3:4 seam calendar edges.'},
         'structural_change': why,
         'job': {'owner': 'Claude:HBM-CXDL', 'branch': 'claude/hbm-cxdl-1018', 'tag': 'x1',
                 'purpose': 'HBM die d4g cxport one-root half: ' + top, 'record_to': 'results/rtl/ref_tile/' + name,
                 'views_to': f'physical/ref_tile/{name}/views', 'auto_merge': False,
                 'reroute_reason': {'kind': 'rtl_change', 'what': 'one-root split vs ' + ('hbm_su_cx_dl_1017-s2-761317600' if '_dl' in name else 'hbm_su_cx_rc_1017-s2-761317600'),
                                    'why': why[:600]},
                 **BENCH}}
    out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
    out.write_text(json.dumps(s, indent=1) + '\n'); print(out)


B = dict(clk_s=1, rst_s_n=1, del_valid=1, del_flit=545, del_obase=40, b0=524, b1=524, v0=8, v1=8, sfault_s=1)
mk('hbm_su_cx_dls_1018', 'ot_hbm_su_static_cxport_dl_s', {'QID': 2, 'G': 0}, 'clk_s', 'rst_s_n', 108.0, 216.0,
   {'W': ['del_valid', 'del_obase', 'del_flit'], 'E': ['v0', 'b0', 'v1', 'b1', 'sfault_s'], 'N': ['clk_s', 'rst_s_n']},
   B, 1500, WHY + 'dl_s (stream, die x16): W COLL delivery lane 586 b (2.7/um), E seam to dl_q 1,065 b (4.9/um); clock/reset N centre.')
B = dict(clk_q=1, rst_q_n=1, b0=524, b1=524, v0=8, v1=8, sfault_s=1, dw_v=2, dw_row=18, dw_d=1024, fault=1)
mk('hbm_su_cx_dlq_1018', 'ot_hbm_su_static_cxport_dl_q', {}, 'clk_q', 'rst_q_n', 108.0, 216.0,
   {'W': ['v0', 'b0', 'v1', 'b1', 'sfault_s'], 'E': ['dw_v', 'dw_row', 'dw_d'], 'N': ['clk_q', 'rst_q_n', 'fault']},
   B, 1500, WHY + 'dl_q (serial, die x16): W seam from dl_s 1,065 b (4.9/um), E slice-G write port 1,044 b (4.9/um).')
B = dict(clk_s=1, rst_s_n=1, rc_v=1, rc_tag=3, rc_d=256, rr_v=1, rr_tag=3, rr_d=256, ro_v=16, ro_x=512,
         ob0=528, ob1=528, rb0=268, rb1=268, cb0=261, cb1=261, sfault_s=1, rc_coll=1)
mk('hbm_su_cx_rcs_1018', 'ot_hbm_su_static_cxport_rc_s', {}, 'clk_s', 'rst_s_n', 172.8, 432.0,
   {'W': ['rr_v', 'rr_tag', 'rr_d', 'rc_v', 'rc_tag', 'rc_d', 'ro_v', 'ro_x'],
    'E': ['ob0', 'ob1', 'rb0', 'rb1', 'cb0', 'cb1', 'sfault_s', 'rc_coll'], 'N': ['clk_s', 'rst_s_n']},
   B, 3000, WHY + 'rc_s (stream, x4): W COLL/SFU side 1,048 b (2.4/um), E seam to rc_q 2,116 b (4.9/um); 172.8 x 432 so the '
   'seam stays <= 6/um (the pair abuts as a 345.6 x 432 block).')
B = dict(clk_q=1, rst_q_n=1, red_sv=1, red_tag=32, red_x=32, red_sel=12, rr_wv=1, rr_wa=5, rr_wd=256, sfu_x=32,
         ob0=528, ob1=528, rb0=268, rb1=268, cb0=261, cb1=261, sfault_s=1, rc_coll=1, fault=1)
mk('hbm_su_cx_rcq_1018', 'ot_hbm_su_static_cxport_rc_q', {}, 'clk_q', 'rst_q_n', 172.8, 432.0,
   {'W': ['ob0', 'ob1', 'rb0', 'rb1', 'cb0', 'cb1', 'sfault_s', 'rc_coll'],
    'E': ['red_sv', 'red_tag', 'red_x', 'red_sel', 'rr_wv', 'rr_wa', 'rr_wd', 'sfu_x'], 'N': ['clk_q', 'rst_q_n', 'fault']},
   B, 3000, WHY + 'rc_q (serial, x4): W seam from rc_s 2,116 b (4.9/um), E sucore side 373 b.')
