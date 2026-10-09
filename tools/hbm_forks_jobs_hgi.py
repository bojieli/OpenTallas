#!/usr/bin/env python3
"""hbm-forks (2026-10-09, owner: generic HBM die approved): closure-loop route specs, 2 -cl variants each (TC route,
option B: setup TT / hold FF, HM 10 and HM 25), for the forks this stream owns besides the svc PS segments
(tools/hbm_forks_jobs.py):
  seq     ot_hgi_seq (HGI-1 v1.0 record sequencer, indexed descriptors C3b, 18-bit END token; ring = one
          ot_sram_1r1w_256x256 macro)                      bench: tb_hgi_seq PASS + MUT_WAIT / stale-table FAIL
  cmdproc ot_hgi_cmdproc (config path busy/settle + range, TOKEN18 core, cp_vocab / cp_ctx_max)
                                                           bench: run_bench.sh cmdproc PASS + MUT RANGE FAIL
  attn    hfd_attn_half_lo with the PS entry port ks + strap ldk (half_ps pin plan)   bench: run_attn_ldk.sh
  front   ot_hbm_accel_smh_front_c ENABLE_INT8 = 1, PIPE_INT8 = 1 (two-beat INT8 front, DS formats bypass-matched),
          on the fmt3 wide geometry (570.24 um strip)       bench: in parallel (CF-SM / CF-1 smh lockstep)
  python3 tools/hbm_forks_jobs_hgi.py <commit> [--write DIR]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BR = 'claude/hbm-forks-20261009'
HOSTS = ['ot-epyc3', 'ot-epyc1tb', 'ot-epyc2']
TT = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
      "export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
      "physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; ")
CHK = [dict(name='ttb_routed_at_TC', cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")]
POST = ['physical/hbm_accel_die_views/common/signoff_unc60.sdc', 'physical/hbm_accel_die_views/common/vclk_corner_true.sdc',
        'physical/common_flow/link_budget_consistent.sdc']
G = 'rtl/hbm_accel/generic'
WIDE = [True]          # --nominal: the INT8 front in the 432-um front_c strip (keeps the qualified 4 x 2 SM grid)


def mtp_route(top, hm, args, macro, threads=8, ram=24):
    def cmd(cal):
        lab = '{LABEL}${CL_LABEL_SUFFIX}' if cal else '{LABEL}'
        return (TT + f"OUT={{RUN}}/routes CORES={threads} UTIL=40 PD=0.55 HM={hm} LB=1 STAGES=pnr MACRO={macro} "
                f"bash physical/hbm_mtp/route_mtp.sh {lab} {top} {args}" + (' $CL_STOP_AFTER' if cal else ''))
    return dict(
        calibrate=dict(cmd=cmd(True), base='{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base', clock='core_clk',
                       threads=threads, peak_ram_gb=ram),
        route=dict(cmd=cmd(False), ok="grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                   logs=['{RUN}/routes/{LABEL}/run.log']),
        collect=dict(cmd='mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args '
                         '{RUN}/routes/{LABEL}/physical.json {RUN}/record/'))


def seq_bench():
    b = (f"cd {G}/tb && iverilog -g2012 -DSEQ_MACRO -I. -o /tmp/seq_{{NAME}}_$$.vvp -s tb_hgi_seq tb_hgi_seq.sv ../ot_hgi_seq.sv "
         "../../../../physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v {D} && "
         "vvp -n /tmp/seq_{NAME}_$$.vvp | tail -3")
    return [dict(name='seq_exact', cmd=b.replace('{D}', ''), expect='pass', pass_regex='HGI_SEQ PASS', threads=1, peak_ram_gb=4),
            dict(name='seq_mut_wait', cmd=b.replace('{D}', '-DOT_HGI_SEQ_MUT_WAIT'), expect='fail', fail_regex='HGI_SEQ FAIL',
                 threads=1, peak_ram_gb=4)]


def specs(commit):
    out = []
    c9 = commit[:9]
    M256 = 'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2'
    M2RW = 'physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2'
    for hm, tag in (('0.010', 'hm10'), ('0.025', 'hm25')):
        # ---- sequencer
        args = (f"--source {G}/ot_hgi_seq.sv --param USE_MACRO=1 --clock-port clk "
                f"--macro-view ot_sram_1r1w_256x256_m2_r2c2={M256} --macro-place-halo 6 6 "
                "--die-area 0 0 360 360 --core-area 10.8 10.8 349.2 349.2")
        out.append(dict(name=f'hgi_seq-{c9}-tc-{tag}-cl', block='ot_hgi_seq', **common(commit),
                        purpose='hbm-forks item 4: HGI-1 v1.0 record sequencer (C2), indexed descriptors (C3b), 18-bit END '
                                'token; ring = ot_sram_1r1w_256x256 macro. TC route option B, HM ' + tag,
                        stages=dict(bench=seq_bench(), **mtp_route('ot_hgi_seq', hm, args, M256)),
                        route_hold_margin_ns=float(hm)))
        # ---- cmdproc (config path + TOKEN18 core)
        args = (f"--source {G}/ot_hgi_cfg.sv --source {G}/ot_hgi_cmdproc_core.sv --source {G}/ot_hgi_cmdproc_core_m.sv "
                f"--source {G}/ot_hgi_cmdproc.sv --clock-port clk "
                f"--macro-view ot_sram_2rw_512x64_m4_r2c2={M2RW} --macro-place-halo 6 6 "
                "--die-area 0 0 420 420 --core-area 10.8 10.8 409.2 409.2")
        bench = [dict(name='cmdproc_exact', cmd='bash physical/hbm_forks/run_bench.sh cmdproc out_cp', expect='pass',
                      pass_regex='HGI_CMDPROC PASS', threads=1, peak_ram_gb=4),
                 dict(name='cmdproc_mut_range', cmd='MUT=OT_HGI_MUT_RANGE bash physical/hbm_forks/run_bench.sh cmdproc out_cpm',
                      expect='fail', fail_regex='HGI_CMDPROC FAIL', threads=1, peak_ram_gb=4)]
        out.append(dict(name=f'hgi_cmdproc-{c9}-tc-{tag}-cl', block='ot_hgi_cmdproc', **common(commit),
                        purpose='hbm-forks item 4: cmdproc config path (busy/settle interlock + range checks, F-2) + '
                                'TOKEN18 core with cp_vocab / cp_ctx_max. TC route option B, HM ' + tag,
                        stages=dict(bench=bench, **mtp_route('ot_hgi_cmdproc', hm, args, M2RW)),
                        route_hold_margin_ns=float(hm)))
        # ---- the die command processor ot_hgi_cp (config path + sequencer): replaces ot_hgi_cmdproc on the die
        args = (f"--source {G}/ot_hgi_cfg.sv --source {G}/ot_hgi_seq.sv --source {G}/ot_hgi_cp.sv --param USE_MACRO=1 "
                f"--clock-port clk --macro-view ot_sram_1r1w_256x256_m2_r2c2={M256} --macro-place-halo 6 6 "
                "--die-area 0 0 420 420 --core-area 10.8 10.8 409.2 409.2")
        cpb = (f"cd {G}/tb && iverilog -g2012 -DSEQ_CP -DSEQ_MACRO {{D}} -I. -I.. -o /tmp/cp_{{NAME}}_$$.vvp -s tb_hgi_seq "
               "tb_hgi_seq.sv ../ot_hgi_seq.sv ../ot_hgi_cp.sv ../ot_hgi_cfg.sv "
               "../../../../physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v && "
               "vvp -n /tmp/cp_{NAME}_$$.vvp | tail -3")
        bench = [dict(name='cp_exact', cmd=cpb.replace('{D}', ''), expect='pass', pass_regex='HGI_SEQ PASS', threads=1,
                      peak_ram_gb=4),
                 dict(name='cp_mut_tokx', cmd=cpb.replace('{D}', '-DOT_HGI_SEQ_MUT_TOKX'), expect='fail',
                      fail_regex='HGI_SEQ FAIL', threads=1, peak_ram_gb=4)]
        out.append(dict(name=f'hgi_cp-{c9}-tc-{tag}-cl', block='ot_hgi_cp', **common(commit),
                        purpose='hbm-forks item 4: the die command processor ot_hgi_cp = config path (busy/settle + range) '
                                '+ v1.0 sequencer (indexed descriptors, TOKX, 18-bit token); replaces the LAUNCH-list '
                                'ot_hgi_cmdproc. TC route option B, HM ' + tag,
                        stages=dict(bench=bench, **mtp_route('ot_hgi_cp', hm, args, M256)),
                        route_hold_margin_ns=float(hm)))
        # ---- attention half_lo with the PS entry port + ldk strap
        hm_a = '0.030' if tag == 'hm25' else '0.010'
        rcmd = ("bash $(ls -d /srv/opentallas-scratch2/scratch/claude/ttviews/ttv_install.sh "
                "/srv/opentallas-scratch/claude/ttviews/ttv_install.sh 2>/dev/null | head -1) {SRC} "
                "ot_attn_tile_m6h1q=physical/hbm_attn_tile_r/quad_b/ot_attn_tile_m6h1q "
                "ot_attn_tile_m6h1q=physical/hbm_attn_tile_r/quad_b_cts/ot_attn_tile_m6h1q "
                "ot_attn_bank_sn544=physical/hbm_attn_tile_r/bank/ot_attn_bank_sn544 "
                "ot_attn_bank_ew544=physical/hbm_attn_tile_r/bank/ot_attn_bank_ew544 && " + TT +
                "export OT_MM_FF_SDC='physical/hbm_attn_tile_r/signoff_833_int.sdc'; "
                f"OUT={{RUN}}/routes CORES=16 TOP=hfd_attn_half_lo HALFDIR=physical/hbm_attn_tile_r/half_ps DH=814.32 "
                f"PARAMS=\"NK=4 NC=2 NR=3 PMID=2 NFR=3 NLL=3\" SLIVER=12 HM={hm_a} PD=0.40 "
                "CTSA=\"-sink_clustering_enable -repair_clock_nets -distance_between_buffers 150\" "
                "bash physical/hbm_attn_tile_r/half/route_half_cl.sh {LABEL} --orfs-var "
                "\"GLOBAL_ROUTE_ARGS=-congestion_iterations 30 -allow_congestion\"")
        out.append(dict(name=f'hgi_attn_half_lo_ps-{c9}-tc-{tag}-cl', block='hfd_attn_half_lo', **common(commit, ram=96, threads=16),
                        purpose='hbm-forks item 3: attention entry points (RQ-HF-4): hfd_attn_half_lo with the PS row '
                                'port ks (1,102 b) + the static ldk strap (half_ps pin plan). TC, HM ' + hm_a,
                        stages=dict(bench=[], calibrate=dict(enabled=False, reason='tile IO false-pathed: every face pin is '
                                                             'a pin-bank register (as the half-tile lines)'),
                                    route=dict(cmd=rcmd, ok="grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                                               logs=['{RUN}/routes/{LABEL}/run.log']),
                                    collect=dict(cmd='mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json '
                                                     '{RUN}/routes/{LABEL}/args {RUN}/routes/{LABEL}/physical.json {RUN}/record/')),
                        no_bench_reason='ldk lockstep bench (physical/hbm_forks/run_attn_ldk.sh: CF-1 roles 0-4 at ldk 0, '
                                        'ldk 1, mutant FAIL) PASS at 43dbec73e on the same RTL; re-run in parallel',
                        verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json',
                                     drc_metrics='{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json',
                                     checks=CHK, post_sdc=['physical/hbm_attn_tile_r/signoff_833_int.sdc'],
                                     macros=['physical/hbm_attn_tile_r/quad_b/ot_attn_tile_m6h1q',
                                             'physical/hbm_attn_tile_r/bank/ot_attn_bank_sn544',
                                             'physical/hbm_attn_tile_r/bank/ot_attn_bank_ew544']),
                        route_hold_margin_ns=float(hm_a)))
        # ---- SM INT8 front (front_c, wide fmt3 strip)
        geom = 'results/arch/qwen_on_r25_20261008/fmt3_physical_candidate/wide_geometry.json'
        fc = lambda cal: (TT + "python3 tools/hbm_accel_smh_physical.py block --piece front_c --variant one "  # noqa: E731
                          + (f"--geom {geom} " if WIDE[0] else "") + f"--top-param ENABLE_INT8=1 --top-param PIPE_INT8=1 --pd 0.45 --grt-allow "
                          f"--period 770 --skew 90 --die-skew 150 --hold-margin {0 if cal else int(float(hm) * 1000)} "
                          "--hold-buffer-pct 60 --no-admit --cores {THREADS} --src {SRC} "
                          + ("--label {LABEL}_cal --out {RUN}/routes/{LABEL}_cal --stop-after cts --lat-ff 100 && "
                             "bash {RUN}/routes/{LABEL}_cal/run.sh" if cal else
                             "--label {LABEL} --out {RUN}/routes/{LABEL} --lat ${CK_SS_MEAN:-720} --lat-ff ${CK_FF_MEAN:-430} "
                             "&& bash {RUN}/routes/{LABEL}/run.sh"))
        out.append(dict(name=f'hgi_smh_front_c_int8{"" if WIDE[0] else "_nom"}-{c9}-tc-{tag}-cl', block='ot_hbm_accel_smh_front_c',
                        **common(commit, ram=64, threads=16),
                        purpose='hbm-forks item 1: SM INT8 front (two-beat; one-beat re-layout NO_FIT per owner rule): '
                                'front_c ENABLE_INT8 = 1 PIPE_INT8 = 1, formats 0-2 bypass the adapter (CF-1 cycle-'
                                'identical), fmt3 wide strip 570.24 um. TC route option B, HM ' + tag,
                        stages=dict(bench=[],
                                    calibrate=dict(cmd=fc(True), base='{RUN}/routes/{LABEL}_cal/results/asap7/*/base',
                                                   clock='core_clk', threads=16, peak_ram_gb=64),
                                    route=dict(cmd=fc(False), ok="grep -q '^flow_rc=0' {RUN}/routes/{LABEL}/status && "
                                               "grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/status",
                                               logs=['{RUN}/routes/{LABEL}/flow.log']),
                                    collect=dict(cmd='mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json '
                                                     '{RUN}/routes/{LABEL}/config.mk {RUN}/routes/{LABEL}/geometry.json '
                                                     '{RUN}/record/')),
                        no_bench_reason='launch routes before benches (owner rule): CF-SM / CF-1 smh lockstep '
                                        '(tools/dshbm_sm_pq_seq.py --smh --int8, ENABLE_INT8 1 vs 0 on DS sequences, '
                                        'mutant OT_SMH_MUT_NOBYP) and the Codex INT8 gates run in parallel',
                        verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json',
                                     drc_metrics='{RUN}/routes/{LABEL}/logs/asap7/*/base/5_2_route.json', checks=CHK,
                                     post_sdc=[], macros=['physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2']),
                        budget=dict(enabled=False, reason='new fork; route-time consistent die-link budget via link_budget_hook'),
                        route_hold_margin_ns=float(hm)))
    sfx = '-cl2' if '--cl2' in sys.argv else '-cl'
    for s in out:
        s['name'] = s['name'][:-3] + sfx
        s.setdefault('verdict', dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json',
                                     drc_metrics='{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json',
                                     checks=CHK, post_sdc=POST))
        s.update(route_hold_corners='mm', route_corner='TC', cycles_added=0, merge_target=None)
    return out


def common(commit, ram=24, threads=8):
    return dict(owner='Claude:hbm-forks', hosts=HOSTS, threads=threads, peak_ram_gb=ram,
                source=dict(branch=BR, commit=commit,
                            extra_paths=['results/arch/qwen_on_r25_20261008/fmt3_physical_candidate']))


def main():
    commit = sys.argv[1]
    if '--nominal' in sys.argv:
        WIDE[0] = False
    out = specs(commit)
    if '--write' in sys.argv:
        d = Path(sys.argv[sys.argv.index('--write') + 1])
        for s in out:
            (d / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + '\n')
    for s in out:
        print(s['name'])


if __name__ == '__main__':
    main()
