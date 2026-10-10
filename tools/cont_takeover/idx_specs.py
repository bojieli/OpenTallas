#!/usr/bin/env python3
"""cont-takeover 2026-10-09: closure-loop specs for the NK4 registered score slice (hardened element of the scorer)."""
import json, sys
commit, branch, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
V, H = 'rtl/hdc/v41x', 'rtl/hdc'
SRC = ' '.join('--source ' + f for f in (f'{V}/ot_hdc_v41x_idx_lat.sv', f'{V}/ot_hdc_v41x_idx_arith_lat.sv', f'{V}/ot_hdc_v41x_idx_arith.sv',
      f'{H}/ot_hdc_delay.sv', f'{H}/ot_hdc_fastfp.sv', f'{H}/ot_hdc_fp32_add_lat.sv', f'{H}/ot_hdc_prefix.sv', f'{V}/ot_hdc_v41x_idx_score_slice_reg.sv'))
PAR = ' '.join(f'--param {k}={v}' for k, v in dict(NK=4, NB=4, IH=32, IW=30, MD=64, FPL=7, FML=5, QL=5).items())
for (w, h, hm, util) in ((1000, 1500, '0.025', 40), (1200, 1600, '0.010', 35)):
    name = f'idxslice-nk4-{w}x{h}-{commit[:9]}-tc-cl'
    env = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && export OT_ORFS_CORNER_OVERRIDE=TC; "
           "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; "
           f"OUT={{RUN}}/routes CORES=32 UTIL={util} PD=0.55 HM={hm} LB=1 STAGES=synth,pnr bash physical/hbm_mtp/route_mtp.sh ")
    tail = f"ot_hdc_v41x_idx_score_slice_reg {SRC} {PAR} --clock-port clk --die-area 0 0 {w} {h} --core-area 2.16 2.16 {w-2.16:.2f} {h-2.16:.2f}"
    spec = {'name': name, 'block': 'ot_hdc_v41x_idx_score_slice_reg', 'element': 'NK4 scorer slice (ot_hdc_v41x_idx_score_slice_reg)',
            'owner': 'Claude:cont-takeover (hbm_continuation NK4)',
            'purpose': f'cont-takeover: hardened element of the NK4 index scorer = one registered full-geometry score slice (NK4 x IH32 x NB4 = 512 FP4 block dots/cycle, FPL7/FML5/QL5 streaming), 16 per stack (Codex hierarchical map 39b818fdd: 6.28 M cells / 16). Frame {w}x{h} um, HM {hm}. Option B.',
            'hosts': ['ot-epyc1tb', 'ot-epyc2', 'ot-epyc3', 'ot-epyc4'], 'threads': 32, 'peak_ram_gb': 120,
            'source': {'branch': branch, 'commit': commit},
            'stages': {'bench': [
                {'name': 'idxslice_equiv', 'cmd': 'bash tools/cont_takeover/idx_bench.sh pos {RUN}/bench_pos', 'expect': 'pass', 'pass_regex': 'IDXB_PASS', 'threads': 1, 'peak_ram_gb': 16},
                {'name': 'idxslice_mutant', 'cmd': 'bash tools/cont_takeover/idx_bench.sh neg {RUN}/bench_neg', 'expect': 'fail', 'fail_regex': 'IDXB_NEG_FAIL', 'threads': 1, 'peak_ram_gb': 16}],
                'calibrate': {'cmd': env + '{LABEL}${CL_LABEL_SUFFIX} ' + tail + ' $CL_STOP_AFTER', 'base': '{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base',
                              'clock': 'core_clk', 'threads': 32, 'peak_ram_gb': 120},
                'route': {'cmd': env + '{LABEL} ' + tail, 'ok': "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                          'logs': ['{RUN}/routes/{LABEL}/run.log']},
                'collect': {'cmd': 'mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args {RUN}/routes/{LABEL}/physical.json {RUN}/record/'}},
            'verdict': {'corner_sta': '{RUN}/routes/{LABEL}/corner_sta.json', 'drc_metrics': '{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json',
                        'checks': [{'name': 'ttb_routed_at_TC', 'cmd': "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                        'post_sdc': ['physical/hbm_accel_die_views/common/signoff_unc60.sdc', 'physical/hbm_accel_die_views/common/vclk_corner_true.sdc', 'physical/common_flow/link_budget_consistent.sdc']},
            'route_hold_corners': 'mm', 'route_hold_margin_ns': float(hm), 'route_corner': 'TC',
            'cycles_added': '+1 per channel (q load, key, score); query load 2 beats per 4 cycles (+~32 cycles per token)',
            'merge_target': None, 'record': [{'from': '{RUN}/record', 'to': f'results/physical/cont_takeover_idxslice_20261009/{w}x{h}'}]}
    json.dump(spec, open(f'{outdir}/{name}.json', 'w'), indent=1); print(name)
