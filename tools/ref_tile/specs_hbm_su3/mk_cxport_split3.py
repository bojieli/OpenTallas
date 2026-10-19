"""CX-IJ 10-18: kits for the ONE-ROOT halves of the cxport ij leaf (ot_hbm_su_static_cxport_ij_s stream / _ij_q serial).
The two-root ij leaf (kit hbm_su_cx_ij_1017) holds two 3:4 crossings inside one leaf (ijd_slot -> inject pipe and
io_slot -> idl), the same defect that failed routes hbm_su_cx_dl_1017-s2-761317600 / hbm_su_cx_rc_1017-s2-761317600
(related-clock STA at the VCO tick less the 150 / 100 distinct-entry reserve). Same split as mk_cxport_split2.py (dl/rc):
2-bank seams with >= 3-quantum calendar windows, a die-level 3:4 seam arc; the halves abut (ij_q W of ij_s)."""
import json
from pathlib import Path
SRC = ['rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv']
LOG = 'results/rtl/hbm_cxij_1018/'
_b = lambda n, cmd, exp, w: dict({'name': n, 'cmd': 'bash tools/hbm_static/su_cxport_split_vl_run.sh {RUN}/bench/' + cmd,
                                  'expect': exp, ('pass_regex' if exp == 'pass' else 'fail_regex'): 'CXPORT_SPLIT ' + exp.upper(),
                                  ('pass_witness' if exp == 'pass' else 'fail_witness'): LOG + w,
                                  'threads': 4, 'peak_ram_gb': 6, 'needs': ['verilator']},
                                 **({'min_count_regex': 'checks=(\\d+)'} if exp == 'pass' else {}))
BENCH = {'extra_paths': ['tools/hbm_static/su_cxport_split_vl_run.sh',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/tb_hbm_su_cxport_split.sv',
                         'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport.sv'],
         'benches': [_b('cxport_split_lockstep', 'pos 2 0 0 0', 'pass', 'cxport_split3_vl_q2_pos.log'),
                     _b('cxport_split_lockstep_q0', 'q0 0 1 0 0', 'pass', 'cxport_split3_vl_q0_pos.log'),
                     _b('cxport_split_mut1', 'mut1 2 0 1 1', 'fail', 'cxport_split3_vl_mut1.log'),
                     _b('cxport_split_mut4', 'mut4 2 0 4 1', 'fail', 'cxport_split3_vl_mut4.log')]}
WHY = ('CX-IJ 10-18: the two-root ij leaf carries two 3:4 crossings inside one leaf (ijd_slot clk_s -> ipv / ipgb / ibad '
       'clk_q, and io_slot clk_q -> idl clk_s, 3 x 1,024 b), the defect that failed routes hbm_su_cx_dl_1017-s2-761317600 '
       '(TT -166.7 / FF -95.1) and hbm_su_cx_rc_1017-s2-761317600 (TT -173.4 / FF -77.9): related-clock STA times a 3:4 '
       'crossing at the VCO tick (setup 277.8 ps, coincident-edge hold) less the 150 / 100 distinct-entry reserve. Fix (dl/rc '
       'split, S81 x34 _s/_t precedent): one root per half; the crossings become 2-bank seams (static calendar windows >= 3 '
       'quanta for setup and rewrite-after-read), die-level 3:4 seam arcs. Lockstep vs the hub on Verilator 5.050 PASS QID 2 '
       'and QID 0 (checks=24183); mutants 1/2/3/4 FAIL. ')


def mk(name, top, params, ck, rst, W, H, pins, B, std, why, cts=None):
    pr = {}
    for f, order in pins.items():
        span = (H if f in 'WE' else W)
        if f == 'N' and all(B[p] <= 2 for p in order):
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
                   'pin_h': 'M4', 'pin_v': 'M3 M5', 'pin_balance': {'h': 'M4', 'v': 'M3 M5', 'group_max': 1}, 'io_hold_margin_ns': 0.03,
                   **({'cts_sink': cts} if cts else {})},
         'orfs_vars': {'GPL_ROUTABILITY_DRIVEN': '0'},
         'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': False, 'outhold': False, 'keep_pin_regs': True, 'hold_budget': 'die',
         'pin_regs': {'enable': False, 'reason': 'Every pin is registered in RTL (inputs land in pin registers / banks, every '
                      'output is a register); a wrapper stage would move the fixed 3:4 seam calendar edges.'},
         'structural_change': why,
         'job': {'owner': 'Claude:CX-IJ', 'branch': 'claude/hbm-cxij-1018', 'tag': 'x1',
                 'purpose': 'HBM die d4g cxport one-root half: ' + top, 'record_to': 'results/rtl/ref_tile/' + name,
                 'views_to': f'physical/ref_tile/{name}/views', 'auto_merge': False,
                 'reroute_reason': {'kind': 'rtl_change', 'what': 'one-root split of the two-root leaf hbm_su_cx_ij_1017 (never routed; same defect as hbm_su_cx_dl/rc_1017-s2-761317600)',
                                    'why': why[:600]},
                 **BENCH}}
    if name == 'hbm_su_cx_ijq_1018u':
        s['job']['purpose'] += ' (variant: unclustered CTS H-tree; submit only the variant that passes)'
    out = Path('tools/ref_tile/specs_hbm_su3') / f'{name}.json'
    out.write_text(json.dumps(s, indent=1) + '\n'); print(out)


B = dict(clk_s=1, rst_s_n=1, inj_rd=2, inj_addr=160, inj_d=1024, ob0=1024, ob1=1024, jb0=32, jb1=32, sfault_s=1, ins_coll=1)
SEAM = ['jb0', 'jb1', 'sfault_s', 'ins_coll', 'ob0', 'ob1']
mk('hbm_su_cx_ijs_1018', 'ot_hbm_su_static_cxport_ij_s', {'QID': 2, 'B39_NOOP': 0, 'INJ_RET': 11}, 'clk_s', 'rst_s_n', 108.0, 388.8,
   {'W': SEAM, 'E': ['inj_d', 'inj_rd', 'inj_addr'], 'N': ['clk_s', 'rst_s_n']},
   B, 3000, WHY + 'ij_s (stream, x1 per quarter): W seam to ij_q 2,114 b (5.6/um), E inj_d / request 1,186 b (3.1/um); '
   'clock/reset N centre. HH-1 10-18 regate: 216 -> 108 um wide (gate 216 x 388.8, util 1.7%: GPL-0305 RePlAce '
   'divergence, no CTS / GRT); 108 x 388.8 keeps both faces <= 6/um, util ~3.5% (closed dl_s 2.6%), ob -> idl -> inj_d '
   'runs W -> E over 108 um; the pair abuts as a 324 x 388.8 block (old two-root leaf 388.8 x 388.8).')
B = dict(clk_q=1, rst_q_n=1, inj_q0=1024, inj_q1=1024, inj_q2=1024, inj_q3=1024, ob0=1024, ob1=1024, jb0=32, jb1=32,
         sfault_s=1, ins_coll=1, fault=1)
QWHY = (WHY + 'ij_q (serial, x1 per quarter): E seam to ij_s 2,114 b (5.6/um); the four slices port-5 data 4,096 b on W '
        '(inj_q0/1, 5.4/um), S (inj_q2, 4.9/um) and N (inj_q3, 4.9/um, clock/reset/fault at the NE end beside the ob '
        'seam banks). HH-1 10-18 regate: 388.8 x 388.8 -> 216 x 388.8 (gate 388.8^2: pin flops ring a 389 um square, '
        'TT / FF pin-flop spread 97.2 / 92.7 ps > 80, util 2.7%); the ring now spans 216 x 389 um.')
for nm, cts in (('hbm_su_cx_ijq_1018', None), ('hbm_su_cx_ijq_1018u', {'sink_clustering': False})):
    mk(nm, 'ot_hbm_su_static_cxport_ij_q', {}, 'clk_q', 'rst_q_n', 216.0, 388.8,
       {'W': ['inj_q0', 'inj_q1'], 'S': ['inj_q2'], 'N': ['inj_q3', 'clk_q', 'rst_q_n', 'fault'], 'E': SEAM},
       B, 4000, QWHY + ('' if cts is None else ' Variant u: unclustered TritonCTS H-tree over the pin-band sinks '
                        '(qkd_d2d_static 10-15 precedent: sparse pin-band tile, unclustered tree 442..508 ps).'), cts)
