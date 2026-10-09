#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): closure-loop route specs, 2 -cl variants per HGI-1 record adapter (TC route, option B:
setup TT / hold FF; variant a = compact outline HM 10 PD .55, variant b = relaxed outline HM 25 PD .45).
Benches run in parallel (owner rule: routes before benches); each spec names its bench record in no_bench_reason.
  python3 tools/hgi_adapters/jobs.py <commit> [--write DIR] [--only su,sm,...]
"""
import json
import sys
from pathlib import Path

BR = 'claude/hgi-adapters-20261009'
HOSTS = ['ot-epyc3', 'ot-epyc1tb', 'ot-epyc2']
A = 'rtl/hbm_accel/generic/adapters'
TT = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
      "export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
      "physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'; ")
CHK = [dict(name='ttb_routed_at_TC', cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")]
POST = ['physical/hbm_accel_die_views/common/signoff_unc60.sdc', 'physical/hbm_accel_die_views/common/vclk_corner_true.sdc',
        'physical/common_flow/link_budget_consistent.sdc']
# unit -> (top, sources, (die a), (die b), bench record)
UNITS = {
    'su': ('ot_hgi_su_record', [f'{A}/ot_hgi_su_record.sv'], (300, 300), (380, 260),
           'rtl/hbm_accel/generic/adapters/tb/run_su.sh (HGI_SU: 4 hbm-sim conformance vectors exact on the real '
           'ot_hdc_v41x_vec + legacy lockstep; MUT_ISTRIDE / MUT_EARLY FAIL); results/rtl/hgi_adapters_20261009'),
    'sfu': ('ot_hgi_sfu_record', [f'{A}/ot_hgi_su_record.sv', f'{A}/ot_hgi_sfu_record.sv'], (300, 300), (380, 260),
            'UNIT=sfu run_su.sh (HGI_SFU: CF-GLU vectors exact on the real vec; MUT_SWAP FAIL)'),
    'sm': ('ot_hgi_sm_record', [f'{A}/ot_hgi_sm_record.sv'], (620, 620), (760, 560),
           'rtl/hbm_accel/generic/adapters/tb/run_sm.sh (HGI_SM: 223 records on 32 stub SMs; MUT_ROWS / MUT_EARLY FAIL)'),
    'att': ('ot_hgi_att_issue', [f'{A}/ot_hgi_att_issue.sv'], (260, 260), (340, 220),
            'run_small.sh att (HGI_ATT: 43 CF-ATT + 144 Qwen + 38 DS 16-lane records; MUT_LANES FAIL)'),
    'dma': ('ot_hgi_dma_record', [f'{A}/ot_hgi_dma_record.sv'], (260, 260), (340, 220),
            'run_small.sh dma (HGI_DMA: CF-EMB / CF-IDXD / CF-KV + 257 Qwen + DS KVWB; MUT_SLOT / MUT_EARLY FAIL)'),
    'argmax': ('ot_hgi_argmax_record', [f'{A}/ot_hgi_argmax_record.sv'], (260, 260), (340, 220),
               'run_small.sh argmax (HGI_ARGMAX: CF-ARG x 2 + Qwen head + 40 random rows on the real argmax18 engine and '
               'the real HGI VM; MUT_OFFSET FAIL)'),
    'hc': ('ot_hgi_hc_record', [f'{A}/ot_hgi_hc_record.sv'], (200, 200), (260, 180),
           'run_small.sh hc (HGI_HC: DS HC_MIX shapes; MUT_NF FAIL)'),
}


NOLEG = {'ot_hgi_att_issue', 'ot_hgi_argmax_record'}     # no legacy pass-through parameter


def route(top, srcs, die, hm, pd):
    w, h = die
    par = '' if top in NOLEG else ' --param LEGACY=0'
    args = ' '.join(f'--source {s}' for s in srcs) + (f"{par} --clock-port clk --die-area 0 0 {w} {h} "
                                                     f"--core-area 10.8 10.8 {w - 10.8:.1f} {h - 10.8:.1f}")

    def cmd(cal):
        lab = '{LABEL}${CL_LABEL_SUFFIX}' if cal else '{LABEL}'
        return (TT + f"OUT={{RUN}}/routes CORES={{THREADS}} UTIL=40 PD={pd} HM={hm} LB=1 "
                f"bash physical/hbm_mtp/route_mtp.sh {lab} {top} {args}" + (' $CL_STOP_AFTER' if cal else ''))
    return dict(
        calibrate=dict(cmd=cmd(True), base='{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base', clock='clk',
                       threads=8, peak_ram_gb=24),
        route=dict(cmd=cmd(False), ok="grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                   logs=['{RUN}/routes/{LABEL}/run.log']),
        collect=dict(cmd='mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args '
                         '{RUN}/routes/{LABEL}/physical.json {RUN}/record/'))


def specs(commit, only=None):
    out = []
    for u, (top, srcs, da, db, bench) in UNITS.items():
        if only and u not in only:
            continue
        for tag, die, hm, pd in (('a', da, '0.010', '0.55'), ('b', db, '0.025', '0.45')):
            out.append(dict(name=f'hgi_adp_{u}_{tag}-{commit[:9]}-tc-cl', block=top, owner='Claude:hgi-adapters',
                            hosts=HOSTS, threads=8, peak_ram_gb=24,
                            source=dict(branch=BR, commit=commit),
                            purpose=f'hgi-adapters: HGI-1 record adapter {top} (decode + handshake onto the existing unit '
                                    f'port). TC route option B, variant {tag}: {die[0]} x {die[1]} um, HM {hm}, PD {pd}',
                            stages=dict(bench=[], **route(top, srcs, die, hm, pd)),
                            no_bench_reason='routes before benches (owner rule): ' + bench,
                            verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json',
                                         drc_metrics='{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json',
                                         checks=CHK, post_sdc=POST),
                            budget=dict(enabled=False, reason='new adapter master; die-link budget via link_budget_hook'),
                            route_hold_margin_ns=float(hm), route_hold_corners='mm', route_corner='TC', cycles_added=0,
                            merge_target=None))
    return out


def main():
    commit = sys.argv[1]
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    out = specs(commit, only)
    if '--write' in sys.argv:
        d = Path(sys.argv[sys.argv.index('--write') + 1])
        for s in out:
            (d / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + '\n')
    for s in out:
        print(s['name'])


if __name__ == '__main__':
    main()
