"""HBM-B-RTL2b 10-17: ref_tile specs for the HC quarter-engine 3x3 ring (5 bank masters + hub). Run in the worktree."""
import json, copy, sys
from pathlib import Path
RT = Path('physical/ref_tile'); H = 'rtl/hbm_accel/generic/peers/static_hc'
M2 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2'
M1 = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
LEAF = 'physical/ref_tile/hc_lanes_ref/views/ot_hdc_v41x_hcp_lanes'
BR = 'claude/hbm-b-rtl2-1017'
BANK_SRC = [f'{H}/ot_hbm_hc_bankq_static.sv', f'{H}/ot_hbm_hc_bank_static.sv', 'rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
            'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
            'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fastfp_lat.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/lib/ot_rst_relay.sv',
            f'{M2}/ot_sram_1r1w_1024x256_m2_r2c2_bb.v', f'{M1}/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
EXTRA = ['rtl/test/run_hbm_hc_eng4_ring.sh', 'rtl/test/tb_hbm_hc_eng4_static.sv', 'rtl/test/tb_hbm_hc_eng4_static_hier.vlt',
         'tools/rtl_hbm_hc_eng_static_gate.py', 'tools/hdc_golden_v41.py', 'tools/hdc_golden.py',
         'tools/rtl_hdc_v41x_hcp_campaign.py', H, 'rtl/hdc', 'rtl/lib', 'rtl/hbm_accel/generic/vm/static',
         'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2', 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2']
BENCH = [
 {"name": "hc_ring_exact", "cmd": "bash rtl/test/run_hbm_hc_eng4_ring.sh {RUN}/bench/m0 0", "expect": "pass",
  "pass_regex": "^HC_RING_LOCKSTEP MUT=0 rc=0", "min_count_regex": "HC_ENG_DONE mode=0 npos=1 mixes=(\\d+) mixbad=0",
  "threads": 16, "peak_ram_gb": 64, "needs": ["verilator"]},
 {"name": "hc_ring_mut1", "cmd": "bash rtl/test/run_hbm_hc_eng4_ring.sh {RUN}/bench/m1 1", "expect": "fail",
  "pass_regex": "^HC_RING_LOCKSTEP MUT=1 rc=0", "fail_regex": "HC_ENG FAIL", "threads": 16, "peak_ram_gb": 64,
  "needs": ["verilator"], "note": "bank 3 (ring corner, fed through bank 2) weight slice rotated"}]
S = 734.4   # bank / hub cell (17 x 43.2), square
CH = ['d_v', 'd_ss', 'd_nv', 'd_wa', 'd_xa', 'sum_in', 'f_in']
CO = ['o_v', 'o_ss', 'o_nv', 'o_wa', 'o_xa', 'sum_out', 'f_out']
WR = ['xb_v', 'xb_beat', 'xb_d', 'wv', 'xv', 'j', 'wa']
def fa(p, out):
    b = [f'{p}_xb_v', f'{p}_xb_beat', f'{p}_xb_d', f'{p}_wv', f'{p}_xv', f'{p}_j', f'{p}_wa']
    return [x + '_o' for x in b] + [f'{p}_rst_n_o', f'{p}_wfault'] if out else b + [f'{p}_rst_n', f'{p}_wfault_o']
def bank_layout():
    ch = []
    for g in range(8):   # lane group g: row g//2, col g%2 (2 cols x 4 rows on the 43.2 lattice)
        ch.append({"view": LEAF, "count": 1, "inst": f"*g_grp?{g}?.u_lg", "at": [259.2 + 172.8 * (g % 2), 43.2 + 172.8 * (g // 2)], "orient": "R0"})
    mac = []
    for g in range(8):   # weight macro g: one abutted N-S stack W of the leaves (E pins face the leaves)
        mac.append({"view": M2, "count": 1, "inst": f"*g_w?{g}?.u_m", "at": [43.2, round(86.4 + 70.512 * g, 3)], "at_exact": True})
    for h in range(4):   # x macro h feeds leaf row h (groups 2h, 2h+1): E of the leaf columns, at its row
        mac.append({"view": M1, "count": 1, "inst": f"*g_x?{h}?.u_m", "at": [600.48, round(92.016 + 172.8 * h, 3)], "at_exact": True})
    return ch, mac
def bank(name, top, pins, purpose, struct):
    ch, mac = bank_layout()
    s = {"name": name, "top": top, "kind": "cluster", "sources": BANK_SRC, "params": {}, "clock_port": "clk",
         "reset_ports": ["rst_n"], "outline": {"w": S, "h": S, "exact": True}, "children": ch, "macros": mac,
         "pins": pins, "inter": [], "refglob": "*", "recipe": 3,
         "route": {"pd": 0.5, "period_ps": 833.333, "threads": 16, "peak_ram_gb": 64, "hold_margin_ns": 0.03, "macro_halo_um": 5.4},
         "io_flop_at_pins": {"cols": 4, "allow_none": True}, "inhold": False, "outhold": False, "keep_pin_regs": True,
         "pin_regs": {"enable": False, "reason": "every bank-tile input lands in RTL pin flops (beat landing v/beat/data, the stage's descriptor/partial-sum seam flops, the write-port flops wv_q/xv_q/j_q/wa_q in ot_hbm_hc_bank_static, feed registers) and every output is a flop (stage SOR seam register, feed registers, wfault); a kit flop stage would shift the compiled systolic schedule"},
         "structural_change": struct,
         "job": {"owner": "Claude:HBM-B-RTL2b", "branch": BR, "tag": "ring1", "purpose": purpose,
                 "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}",
                 "extra_paths": EXTRA, "benches": BENCH}}
    return s
RING = ('HC quarter engine (plan (b) d4g, HBM-B-RTL2b): 3x3 ring of 8 bank tiles around the hub (hc_<q> + centre, '
        'coordinator 10-17 23:45: no empty middle). Chain clockwise from W: b0 W, b1 NW, b2 N, b3 NE, b4 E, b5 SE, b6 S, b7 SW; '
        'masters by pin plan (R0 / R180 only): e2 = b2 / b6, e0 = b4, b0 = b0, ca = b1 / b5, cb = b3 / b7. ')
INT = ('Inside: 8 closed lane leaves hc_lanes_ref (2 cols x 4 rows, 43.2 lattice), the 8 weight macros as ONE abutted N-S '
       'stack W of the leaves (pins E, facing them; macro g beside leaf row g//2), the 4 x macros E of the leaves at their rows. ')
SPECS = [
 bank('hbm_hcq_bank_e2_1017', 'ot_hbm_hc_bankq_ft_static',
      {"W": CH + fa('fa', True), "E": CO + fa('fb', True),
       "S": ['clk', 'rst_n'] + WR + ['wfault'] + fa('fa', False) + fa('fb', False)},
      'HC ring edge bank N/S (b2 R0, b6 R180) + registered feeds of its two corners (W -> b1, E -> b3)',
      RING + INT + 'e2: chain in W / out E; hub on S carries its own beat slice + write control and both corner feeds.'),
 bank('hbm_hcq_bank_e0_1017', 'ot_hbm_hc_bankq_static',
      {"N": CH, "S": CO, "W": ['clk', 'rst_n'] + WR + ['wfault']},
      'HC ring edge bank E (b4): chain in N (from b3) / out S (to b5), hub on W',
      RING + INT + 'e0: chain in N / out S; hub on W.'),
 bank('hbm_hcq_bank_b0_1017', 'ot_hbm_hc_bankq0_static',
      {"E": ['clk', 'rst_n', 'd_v', 'd_ss', 'd_nv', 'd_wa', 'd_xa'] + WR + ['wfault', 's_o'],
       "N": CO, "S": ['s_i']},
      'HC ring first bank W (b0): descriptor from the hub (E), chain out N (to b1), bank 7 chain exit S -> relay -> hub E',
      RING + INT + 'b0: first = 1 (no sum_in/f_in ports); the DRLY chain-exit relay of bank 7 sits here (S -> E).'),
 bank('hbm_hcq_bank_ca_1017', 'ot_hbm_hc_bankq_static',
      {"S": CH, "E": CO + ['clk', 'rst_n'] + WR + ['wfault']},
      'HC ring corner bank NW/SE (b1 R0, b5 R180): chain in S / out E, feed from the edge bank on E',
      RING + INT + 'ca: chain in S / out E; beat slice + write control + reset arrive from b2 (E) through its feed register.'),
 bank('hbm_hcq_bank_cb_1017', 'ot_hbm_hc_bankq_static',
      {"W": CH + ['clk', 'rst_n'] + WR + ['wfault'], "S": CO},
      'HC ring corner bank NE/SW (b3 R0, b7 R180): chain in W / out S, feed from the edge bank on W',
      RING + INT + 'cb: chain in W / out S; feed from b2 (W).'),
]
# hub: leaf tile (hc_q soft + centre), hc_q's programme SRAM
hq = json.loads((RT / 'hbm_hc_q_static/spec.json').read_text())
hub = copy.deepcopy(hq)
hub.update({"name": "hbm_hcq_hub_1017", "top": "ot_hbm_hc_qhub_static", "kind": "tile",
            "sources": hq["sources"] + [f'{H}/ot_hbm_hc_qhub_static.sv', f'{H}/ot_hbm_hc_qcen_static.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv',
                                        'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_prefix.sv'],
            "outline": {"w": S, "h": S, "exact": True},
            "macros": [{"view": M2, "count": 1, "at": [280.8, 332.64], "at_exact": True}],
            "route": {"pd": 0.3, "period_ps": 833.333, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03, "macro_halo_um": 5.4, "io_hold_margin_ns": 0.0}})
hub["sources"] = list(dict.fromkeys(hub["sources"]))
hub["pins"] = {
 "W": ['clk', 'rst_n', 'bd_v', 'bd_ss', 'bd_nv', 'bd_wa', 'bd_xa', 's_i', 'xb_v', 'xb_beat', 'xb_d0', 'wc_w', 'rstb_w', 'wf_w'],
 "N": ['lg_rr', 'lg_w_done', 'xb_v_n', 'xb_beat_n', 'xb_d1', 'xb_d2', 'xb_d3', 'wc_n', 'rstb_n', 'wf_n'],
 "E": ['lg_wq', 'lg_rq', 'xb_v_e', 'xb_beat_e', 'xb_d4', 'wc_e', 'rstb_e', 'wf_e'],
 "S": ['tgt', 'cfg_v', 'cfg_target', 'cfg_addr', 'cfg_data', 'desc_v', 'desc_base', 'desc_limit', 'desc_loops', 'launch_v',
       'configured', 'residual_done', 'gathered_mix_v', 'gathered_mix_row', 'gathered_mix_pos', 'gathered_mix_data', 'gather_done',
       'result_v', 'result_position', 'result', 'program_active', 'program_done', 'hcq_fault',
       'd_v', 'd_ss', 'd_nv', 'd_wa', 'd_xa', 'i_v', 'i_kind', 'i_slot', 'i_lo', 'i_w', 'i_cnt', 'i_word', 'ps_v', 'ps', 'ps_f', 'eng_fault',
       'xb_v_s', 'xb_beat_s', 'xb_d5', 'xb_d6', 'xb_d7', 'wc_s', 'rstb_s', 'wf_s']}
hub["pin_regs"] = {"enable": False, "reason": "ot_hbm_hc_qhub_static = ot_hbm_hc_q_static (every pin registered in RTL, see hbm_hc_q_static) + ot_hbm_hc_qcen_static (descriptor/event/beat-control/s_i/wfault pin flops; bd_*, wc_*, rstb_*, ps* are flops); the bank beat slices xb_* leave hc_q's x_wave output register directly; a kit flop stage would shift the compiled schedule"}
hub["structural_change"] = (RING + 'HUB = the ring hole: hc_<q> (ot_hbm_hc_q_static, was its own 432^2 tile hc_<q>) + the quarter-engine '
    'centre (control-only x_wave rx, ingest sequencer, descriptor relay, 6-level partial-sum subtree TLA 7, 9-region reset). '
    'The 2,048-b x_wave link is now internal (hc_q output register -> the 8 bank beat slices 256 b each); faces: W bank 0 '
    '(+ chain exit s_i 2,049 b), N lg_rr + banks 1-3, E lg_wq/lg_rq + bank 4, S F20 / result / gathered / root links + banks 5-7. '
    'NOTE for H-D4G: the hc_q LG link (4,448 b) must leave the ring through the inter-tile channels.')
hub["job"] = {"owner": "Claude:HBM-B-RTL2b", "branch": BR, "tag": "ring1",
              "purpose": "HC quarter hub (ring hole): hc_<q> + quarter-engine centre, one master x4 (hce_<q>_hub)",
              "views_to": "physical/ref_tile/hbm_hcq_hub_1017/views", "record_to": "results/rtl/ref_tile/hbm_hcq_hub_1017",
              "extra_paths": EXTRA + hq["job"]["extra_paths"], "benches": BENCH + [b for b in hq["job"]["benches"] if b["name"] in ("hcq_exact", "hcq_mut1")]}
SPECS.append(hub)
for s in SPECS:
    d = RT / s["name"]; d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n'); print(d / 'spec.json')
