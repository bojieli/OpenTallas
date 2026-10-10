#!/usr/bin/env python3
"""hbm-forks (2026-10-09): closure-loop job specs for the PS (per-PC stream) svc segment successors.

Two variants per segment master (owner: 2 variants per fork): TC route (option B: setup at TT, hold at FF), rule-H1
budget SDCs + the consistent die-link budget, flow-hold mm FF hold with HM 10 and HM 25, suffix -cl.  The PS RTL,
ws fences, pin plans (OT_SVC_SPLIT=split_ps) and forwarded-clock SDCs are the gen_svc_seg.py --ps outputs.
Benches: bound by `no_bench_reason` to the committed PS bench record (run_bench_ps.sh), because one PS bench run covers
every segment (the segments are only simulated joined).
  python3 tools/hbm_forks_jobs.py <commit> [--write]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = 'physical/hbm_accel_die_views'
REC = 'results/rtl/hbm_forks_20261009/svc_ps_bench'
MASTERS = [f'hfd_svc_SW_s{j}' for j in range(8)] + [f'hfd_svc_SE_s{j}' for j in range(9)]


def stage_cmd(m, hm):
    srcs = (f'rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv '
            f'{V}/svc/rtl/ot_hbm_svc_core.sv {V}/svc/rtl/ot_hbm_svc_seg_lib.sv {V}/svc/rtl/ot_hbm_svc_ps_lib.sv')
    return ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
            "export OT_ORFS_CORNER_OVERRIDE=TC; export OT_SVC_SPLIT=split_ps; "
            "export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl "
            "physical/common_flow/link_budget_hook.tcl'; "
            f"export OT_MM_FF_SDC='{V}/common/budget_signoff.sdc {V}/common/budget_ff_guarded.sdc'; "
            f"cp $BUDGET_SDC {V}/common/budget_route.sdc && cp $BUDGET_SDC_SIGNOFF {V}/common/budget_signoff.sdc && "
            "{ echo 'if {[llength [get_libs -quiet *_FF_*]]} {'; cat $BUDGET_SDC_FF; echo '}'; } > "
            f"{V}/common/budget_ff_guarded.sdc && "
            f'SRC="{{SRC}}" OUT="{{RUN}}/routes" PD="0.55" CORES="8" NEED="40" PER="0.833" IOF="0.2" MAXL="M7" HM="{hm}" '
            f'SDCA="{V}/common/budget_route.sdc" POSTSDC="{V}/common/budget_signoff.sdc {V}/common/budget_ff_guarded.sdc" '
            f'PRECTS="{V}/common/pre_cts_fclk_root_buf.tcl" WSF="0.12" WSFILE="{V}/svc/split_ps/{m}/ws.tcl" SRCS="{srcs}" '
            f'{V}/common/route_view.sh {{LABEL}}${{CL_LABEL_SUFFIX}} {m} {V}/svc/rtl/seg_ps/{m}.sv '
            '--orfs-var GPL_ROUTABILITY_DRIVEN=0 --orfs-var SYNTH_CANONICALIZE_TCL=/src/' + V + '/svc/keep_vpipe_dff.tcl' + (f' --sdc-append {V}/svc/sdc_ps/{m}_fwd.sdc'
                                                     if (ROOT / f'{V}/svc/sdc_ps/{m}_fwd.sdc').exists() else '')
            + ' $CL_STOP_AFTER')


def spec(m, commit, hm, tag):
    name = f'hbm_svc_{m[8:]}_ps_{commit[:9]}_tc_{tag}-cl'
    cmd = stage_cmd(m, hm)
    return name, dict(
        name=name, block=m, owner='Claude:hbm-forks',
        purpose=(f'hbm-forks RQ-HF-1: {m} PER-PC STREAM successor (HGI-1 svc striping, all 32 PCs; DS mode first: the '
                 f'legacy paths are lockstep-identical). TC route, option B, rule H1 budget + link_budget_consistent, mm '
                 f'FF hold HM {int(float(hm) * 1000)}, current flow, submit-time lint.'),
        hosts=['ot-epyc3', 'ot-epyc1tb', 'ot-epyc2'], threads=8, peak_ram_gb=40,
        source=dict(branch='claude/hbm-forks-20261009', commit=commit, extra_paths=[
            'results/uarch/hbm_current_target_portmap_20261005', 'results/rtl/hbm_accel_die_floorplan_20261005',
            'results/rtl/die_top_lint_20261006', 'results/rtl/dshbm_matched_reference_20261005']),
        stages=dict(
            bench=[],
            calibrate=dict(cmd=cmd, base='{RUN}/routes/{NAME}_cal/work/orfs/results/asap7/*/base', clock='core_clk',
                           threads=8, peak_ram_gb=40),
            route=dict(cmd=cmd, ok="grep -q '^rc=0' {RUN}/routes/{NAME}/exit && grep -q '^corner_rc=0' {RUN}/routes/{NAME}/exit",
                       logs=['{RUN}/routes/{NAME}/run.log']),
            collect=dict(cmd=(f'mkdir -p {{RUN}}/record && cp {{RUN}}/routes/{{NAME}}/view/{m}.lef '
                              f'{{RUN}}/routes/{{NAME}}/view/{m}_ss.lib {{RUN}}/routes/{{NAME}}/view/{m}_ff.lib '
                              '{RUN}/routes/{NAME}/corner_sta.json {RUN}/routes/{NAME}/check.json {RUN}/record/ && '
                              'cp {RUN}/routes/{NAME}/args {RUN}/record/route_args_{NAME}.txt && cp {CL}/calib.json {RUN}/record/calib.json'))),
        verdict=dict(corner_sta='{RUN}/routes/{NAME}/corner_sta.json',
                     drc_metrics='{RUN}/routes/{NAME}/work/orfs/logs/asap7/*/base/5_2_route.json',
                     checks=[dict(name='lef_check_MATCH', cmd=("OT_SVC_SPLIT=split_ps python3 -c \"import json,sys; "
                                   "sys.exit(json.load(open('{RUN}/routes/{NAME}/check.json'))['verdict'] != 'MATCH')\"")),
                             dict(name='ttb_routed_at_TC', cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")],
                     post_sdc=[f'{V}/common/budget_signoff.sdc', f'{V}/common/budget_ff_guarded.sdc',
                               'physical/common_flow/link_budget_consistent.sdc']),
        record=[dict(**{'from': '{RUN}/record', 'to': f'{V}/svc/split_ps/{m}'})],
        cycles_added=0, merge_target=None, budget=dict(master=m, clock='core_clk'),
        no_bench_reason=(f'PS successor benched as one joined service ({REC}/summary.txt, {V}/svc/run_bench_ps.sh: '
                         '17 lints, SW + NE legacy traffic + 12 per-PC streams PASS, SW + NE lockstep vs the legacy '
                         'segments PASS, slot / done / PC-collapse mutants FAIL)'),
        cycles_note='legacy SM / W / KV / IK paths cycle-identical (lockstep); streams: +2 row cycles over the core lanes',
        route_hold_corners='mm', route_hold_margin_ns=float(hm), route_corner='TC')


def main():
    commit = sys.argv[1]
    out = []
    for m in MASTERS:
        for hm, tag in (('0.010', 'hm10'), ('0.025', 'hm25')):
            n, s = spec(m, commit, hm, tag)
            out.append(n)
            if '--write' in sys.argv:
                (ROOT / 'tools/closure_loop/jobs' / f'{n}.json').write_text(json.dumps(s, indent=1) + '\n')
    print(len(out), 'jobs:', out[:2], '...')


if __name__ == '__main__':
    main()
