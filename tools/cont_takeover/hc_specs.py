#!/usr/bin/env python3
"""cont-takeover 2026-10-09: closure-loop specs for the distributed-HC structural successors (2 variants per block)."""
import json, sys
commit, branch, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
D = 'rtl/experimental/dsrom_hc_capture_20261009'
MV = 'ot_sram_1r1w_256x256_m2_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
MAC = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
COMMON = f'--source {D}/ot_dsrom_hc_skid.sv --source {D}/ot_dsrom_hc_secded_pipe.sv --source rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv'
FP = ' '.join(f'--source rtl/hdc/{f}' for f in ('ot_hdc_prefix.sv', 'ot_hdc_fastfp.sv', 'ot_hdc_fp32_add_lat.sv', 'ot_hdc_fp32_mul_lat.sv'))
V = {
  # name: (block, element, bench case, sources+params, die, macro tcl, HM, purpose, cycles)
  'hcjoin-mc500': ('ot_dsrom_hc_seed_join', 'ot_dsrom_hc_seed_join', 'join_mc',
                   f'{COMMON} --source {D}/ot_dsrom_hc_seed_join.sv --param ECC_PIPE=1 --param MACRO_CAP=1 --param IN_SKID=1', 500,
                   'physical/cont_takeover/hcjoin_500_macro_place.tcl', '0.025',
                   'registered macro capture before the SECDED pipe (eccpipe join r2: TT -42.7 ps rd_out -> parity tree); macros centred off the pin edges (pi-hcjoin FLOORPLAN_MARGIN)', '+1 cycle per joined-frame read (120 frames), +1 cycle input skid'),
  'hcjoin-mc420': ('ot_dsrom_hc_seed_join', 'ot_dsrom_hc_seed_join', 'join_mc',
                   f'{COMMON} --source {D}/ot_dsrom_hc_seed_join.sv --param ECC_PIPE=1 --param MACRO_CAP=1 --param IN_SKID=1', 420,
                   'physical/cont_takeover/hcjoin_420_macro_place.tcl', '0.010',
                   'same RTL, compact 420 um frame (shorter macro clock / data wires), HM 10', '+1 cycle per joined-frame read (120 frames), +1 cycle input skid'),
  'hcmean-mc560': ('ot_dsrom_hc_mean_capture', 'ot_dsrom_hc_mean_capture', 'mean_mc',
                   f'{COMMON} {FP} --source {D}/ot_dsrom_hc_mean_capture.sv --param SINGLE_CAPTURE=1 --param ECC_PIPE=1 --param MACRO_CAP=1 --param IN_SKID=1', 560,
                   'physical/cont_takeover/hcmean_560_macro_place.tcl', '0.025',
                   'registered macro read capture + registered write word (eccpipe r4: TT -235 ps rd_out -> parity tree, macro clk 753 ps insertion in a 1000 um frame at 3.5 % util); 560 um frame, macros centred', '+1 cycle per frame read (40 frames/capture), write 0, +1 cycle input skid (cmd, beat)'),
  'hcmean-mc700': ('ot_dsrom_hc_mean_capture', 'ot_dsrom_hc_mean_capture', 'mean_mc',
                   f'{COMMON} {FP} --source {D}/ot_dsrom_hc_mean_capture.sv --param SINGLE_CAPTURE=1 --param ECC_PIPE=1 --param MACRO_CAP=1 --param IN_SKID=1', 700,
                   'physical/cont_takeover/hcmean_700_macro_place.tcl', '0.010',
                   'same RTL, 700 um frame, HM 10', '+1 cycle per frame read (40 frames/capture), write 0, +1 cycle input skid (cmd, beat)'),
  'hcreader-plain300': ('ot_dsrom_hc_input_reader', 'ot_dsrom_hc_input_reader', 'reader_plain',
                   f'{COMMON} --source {D}/ot_dsrom_hc_input_reader.sv --param PLAIN_ROWS=1', 300, None, '0.025',
                   'plain row flops, no flop SECDED (REVIEW S4; reader r2: TT -554 ps rows -> decode -> output port)', '-2 cycles per row (no DECODE/DWAIT)'),
  'hcreader-ecc300': ('ot_dsrom_hc_input_reader', 'ot_dsrom_hc_input_reader', 'reader_ecc',
                   f'{COMMON} --source {D}/ot_dsrom_hc_input_reader.sv --param ECC_PIPE=1', 300, None, '0.025',
                   "Codex's registered SECDED encode/decode pipes (ECC_PIPE=1, never routed), compact frame: the parallel fallback if PLAIN_ROWS is not adopted (bench: VM-reader full-shape bench with ECC_PIPE)", 'ECC_PIPE as Codex priced'),
}
for n, (block, el, case, args, die, mtcl, hm, why, cyc) in V.items():
    name = f'{n}-{commit[:9]}-tc-cl'
    macro = ('--macro-view ' + MV + ' --macro-place-halo 5 5 ' + (f'--orfs-var MACRO_PLACEMENT_TCL=/src/{mtcl} ' if mtcl else '')) if 'join' in n or 'mean' in n else ''
    env = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && export OT_ORFS_CORNER_OVERRIDE=TC; "
           "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; "
           f"OUT={{RUN}}/routes CORES=12 UTIL=40 PD=0.55 HM={hm} LB=1 STAGES={'pnr' if macro else 'synth,pnr'} {'MACRO='+MAC if macro else ''} bash physical/hbm_mtp/route_mtp.sh ")
    tail = f"{block} {args} --clock-port clk {macro}--die-area 0 0 {die} {die} --core-area 2.16 2.16 {die-2.16:.2f} {die-2.16:.2f}"
    spec = {
        'name': name, 'block': block, 'element': el, 'owner': 'Claude:cont-takeover (distributed HC routes; registry rows: sys-takeover)',
        'purpose': f'cont-takeover 2026-10-09 DS HC distributed ({el}): {why}. Option B (TT setup / FF hold / DRC 0), TC route.',
        'hosts': ['ot-epyc1tb', 'ot-epyc2', 'ot-epyc3', 'ot-epyc4', 'ot-pve1'], 'threads': 12, 'peak_ram_gb': 32,
        'source': {'branch': branch, 'commit': commit},
        'stages': {
            'bench': [
                {'name': f'{case}_exact', 'cmd': f'bash tools/cont_takeover/hc_bench.sh {case} pos {{RUN}}/bench_pos', 'expect': 'pass',
                 'pass_regex': f'HCB_{case}_PASS', 'threads': 1, 'peak_ram_gb': 4},
                {'name': f'{case}_mutant', 'cmd': f'bash tools/cont_takeover/hc_bench.sh {case} neg {{RUN}}/bench_neg', 'expect': 'fail',
                 'fail_regex': f'HCB_{case}_NEG_FAIL', 'threads': 1, 'peak_ram_gb': 4}],
            'calibrate': {'cmd': env + '{LABEL}${CL_LABEL_SUFFIX} ' + tail + ' $CL_STOP_AFTER',
                          'base': '{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base', 'clock': 'core_clk', 'threads': 12, 'peak_ram_gb': 32},
            'route': {'cmd': env + '{LABEL} ' + tail,
                      'ok': "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                      'logs': ['{RUN}/routes/{LABEL}/run.log']},
            'collect': {'cmd': 'mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args {RUN}/routes/{LABEL}/physical.json {RUN}/record/'}},
        'verdict': {'corner_sta': '{RUN}/routes/{LABEL}/corner_sta.json',
                    'drc_metrics': '{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json',
                    'checks': [{'name': 'ttb_routed_at_TC', 'cmd': "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                    'post_sdc': ['physical/hbm_accel_die_views/common/signoff_unc60.sdc', 'physical/hbm_accel_die_views/common/vclk_corner_true.sdc',
                                 'physical/common_flow/link_budget_consistent.sdc']},
        'route_hold_corners': 'mm', 'route_hold_margin_ns': float(hm), 'route_corner': 'TC',
        'cycles_added': cyc, 'merge_target': None,
        'record': [{'from': '{RUN}/record', 'to': f'results/physical/cont_takeover_hc_20261009/{n}'}],
    }
    json.dump(spec, open(f'{outdir}/{name}.json', 'w'), indent=1)
    print(name)
