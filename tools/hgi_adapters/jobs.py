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
V41 = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fastfp_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/v41/ot_hdc_fsqrt.sv', 'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/hdc/v41/ot_hdc_softplus.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv']
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
    'fused': ('ot_hgi_fused_record', [f'{A}/ot_hgi_su_record.sv', f'{A}/ot_hgi_fused_record.sv'], (320, 320), (420, 260),
              'run_small.sh fused (HGI_FUSED: CF-NORM d4096 BF16 + QK-norm seg 128 FP32 EXACT on the real vec + mover model; '
              'Qwen ROW_NORM shapes vs hgi_sim row_norm; MUT_SEG FAIL)'),
    'mover': ('ot_hgi_dma_mover', ['rtl/hbm_accel/generic/peers/ot_hgi_dma_mover.sv'], (300, 300), (400, 240),
              'run_small.sh mover (HGI_MOVER: DMA adapter + mover on the real HGI VM + kport HBM model: CF-IDXD / CF-KV x 3 '
              'exact + 60 random LOAD / STORE over every format; MUT_RNE FAIL)'),
    'xload': ('ot_hgi_sm_xload', ['rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv'], (520, 520), (640, 420),
              'run_small.sh sm_e2e (HGI_SM_E2E: record -> adapter -> x-load -> 2 real smh -> publication -> real VM; MUT_T FAIL)'),
    'pub': ('ot_hgi_sm_pub', ['rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv'], (700, 700), (860, 560),
            'run_small.sh sm_e2e (HGI_SM_E2E; MUT_ROW FAIL)'),
    'hc': ('ot_hgi_hc_record', [f'{A}/ot_hgi_hc_record.sv'], (200, 200), (260, 180),
           'run_small.sh hc (HGI_HC: DS HC_MIX shapes; MUT_NF FAIL)'),
    # D1 die bodies at reduced memory / lane parameters: the routes time the NEW stage / sequence / drain logic around
    # the r25 engines (the full-size local memories are macros in the die, not flops)
    'hc_unit': ('ot_hgi_hc_unit', V41 + ['rtl/hdc/v41x/ot_hdc_v41x_hcp.sv', 'rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv',
                'rtl/hdc/v41/ot_hdc_sk_arith.sv', 'rtl/hdc/v41/ot_hdc_sk_recip_rom.sv', 'rtl/hdc/v41/ot_hdc_sinkhorn.sv',
                'rtl/hdc/v41/ot_hdc_sinkhorn_mc.sv', f'{A}/ot_hgi_hc_record.sv',
                'rtl/hbm_accel/generic/peers/ot_hgi_hc_unit.sv'], (900, 900), (1100, 800),
                'run_hc_unit.sh (HGI_HC_UNIT: Model.hc_mixes exact incl. Sinkhorn, K 256 / 800 / 28,672 on the real VM + a '
                'reordering HBM model; MUT_POST FAIL); routed at W 8, RMAX 8'),
    'su_unit': ('ot_hgi_su_unit', V41 + ['rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv', 'rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv',
                'rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv', 'rtl/hdc/v41x/ot_hdc_v41x_vec.sv', f'{A}/ot_hgi_su_record.sv',
                'rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv'], (1500, 1500), (1800, 1400),
                'run_small.sh su_unit / sfu_unit, run_su_stream.sh [PUB], run_fused_unit.sh (HGI_SU_UNIT / SFU_UNIT / '
                'SU_STREAM / PUB_STREAM / FUSED_UNIT PASS on the real VM; MUT_DIRTY FAIL); routed at N 8, LV 5, 1K words'),
}
PARAMS = {'ot_hgi_hc_unit': ' --param W=8 --param RMAX=8',
          'ot_hgi_su_unit': ' --param N=8 --param LV=5 --param LWB=10 --param SLB=8'}


NOLEG = {'ot_hgi_su_unit', 'ot_hgi_hc_unit', 'ot_hgi_att_issue', 'ot_hgi_argmax_record', 'ot_hgi_fused_record', 'ot_hgi_dma_mover', 'ot_hgi_sm_xload', 'ot_hgi_sm_pub'}     # no legacy pass-through parameter


def route(top, srcs, die, hm, pd):
    w, h = die
    par = ('' if top in NOLEG else ' --param LEGACY=0') + PARAMS.get(top, '')
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
