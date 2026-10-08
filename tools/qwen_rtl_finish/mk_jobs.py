#!/usr/bin/env python3
"""Closure-loop job specs of stream qwen-rtl-finish (2026-10-07): one OPTION-B TT route per master variant (ORFS corner
TC = setup repair at TT, MM hold at FF with HM 50 ps, rule H1 and the CTS fix hooks + the consistent die-link budget
through tools/closure_loop/tt_overlay.py of the job's own source snapshot), each with its exact benches + mutants.

    mk_jobs.py --commit <sha> [--out /tmp/claude-review-20261003/closure_jobs]
"""
import argparse
import json
from pathlib import Path

HOSTS = ["ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-pve1", "ot-agidock128"]
VER = "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
VFL = ("--binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH "
       "-Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT")
HDC_SU = ("rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv "
          "rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv "
          "rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv "
          "rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_vstream.sv "
          "rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_reduce.sv "
          "rtl/hdc/ot_hdc_reduce_q.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/proto/ot_fp32_mul_rne_pipe.sv")
VM_SRC = ("rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv "
          "rtl/hdc/ot_hdc_delay.sv")
EMB_SRC = "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_io_embedding_rom.sv"
SEQ_SRC = ("rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer.sv "
           "rtl/qwen_sys/missing_masters_20261007/gen/ot_qwen_rom_core_ctrl.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv "
           "rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv rtl/rom/ot_qwen_tp_seq_w12.sv rtl/hdc/ot_hdc_dyn_ttiles.sv "
           "rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_cg.sv rtl/hdc/ot_hdc_delay.sv")


def vbench(name, top, tb, srcs, params, expect, tag, threads=8, ram=8):
    g = " ".join(f"-G{k}={v}" for k, v in params.items())
    cmd = (f"mkdir -p {{RUN}}/bench && {VER} {VFL} -j {threads} --top-module {top} {g} --Mdir {{RUN}}/bench/{name} "
           f"{tb} {srcs} && {{RUN}}/bench/{name}/V{top}")
    b = dict(name=name, cmd=cmd, expect=expect, threads=threads, peak_ram_gb=ram, needs=["verilator"])
    b["pass_regex" if expect == "pass" else "fail_regex"] = f"^{'PASS' if expect == 'pass' else 'FAIL'} {tag}"
    return b


def tree_benches():
    run = "rtl/test/qwen_rtl_finish/run_tree_top.sh"
    out = []
    for name, g, exp in (("tt_lockstep", "", "pass"),
                         ("tt_lockstep_g192", "-GGT=192 -GSMIN=4 -GSMAX=6 -GTCUT=4 -GBD=6 -GTWS=3 -GORD=2 -GSEED=3", "pass"),
                         ("tt_mutant", "-GMUT=1", "fail")):
        b = dict(name=name, cmd=f"mkdir -p {{RUN}}/bench && JOBS=8 bash {run} {{RUN}}/bench/{name} 30000 {g}; "
                 f"grep -q '\"mismatch_cycles\": 0,' {{RUN}}/bench/{name}/result.json && echo PASS qfd_tree_top || echo FAIL qfd_tree_top",
                 expect=exp, threads=8, peak_ram_gb=16, needs=["verilator"])
        b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_tree_top"
        out.append(b)
    return out


def vm_benches(full=True):
    tb = "rtl/test/qwen_rtl_finish/tb_qfd_vector_memory.sv"
    out = [vbench("vm_exact_s5", "tb_qfd_vector_memory", tb, VM_SRC, {"SEED": 5}, "pass", "qfd_vector_memory")]
    if full:
        out += [vbench("vm_exact_s9", "tb_qfd_vector_memory", tb, VM_SRC, {"SEED": 9, "CYCLES": 60000}, "pass", "qfd_vector_memory"),
                vbench("vm_big", "tb_qfd_vector_memory", tb, VM_SRC,
                       {"ELEMS": 65536, "NRB": 64, "SMAX": 9, "SMIN": 5, "BMAX": 8, "XVM": 15, "SEED": 7, "CYCLES": 20000},
                       "pass", "qfd_vector_memory", ram=24),
                vbench("vm_mutant", "tb_qfd_vector_memory", tb, VM_SRC, {"MUT": 1}, "fail", "qfd_vector_memory")]
    return out


def emb_benches(full=True):
    tb = "rtl/test/qwen_rtl_finish/tb_qfd_embedding_rom.sv"
    out = [vbench("emb_exact", "tb_qfd_embedding_rom", tb, EMB_SRC, {}, "pass", "qfd_embedding_rom", threads=4)]
    if full:
        out += [vbench("emb_big", "tb_qfd_embedding_rom", tb, EMB_SRC,
                       {"NCOL": 8, "NTAP": 12, "NCODE": 90, "NSCALE": 3, "LWB": 12, "LSB": 16, "NREQ": 20000, "SEED": 4},
                       "pass", "qfd_embedding_rom", threads=4),
                vbench("emb_mutant", "tb_qfd_embedding_rom", tb, EMB_SRC, {"MUT": 1}, "fail", "qfd_embedding_rom", threads=4)]
    return out


def su_benches(full=True):
    tb = "rtl/test/tb_qfd_su_master_ab.sv"
    out = [vbench("su_ab_exact", "tb_qfd_su_master_ab", tb, HDC_SU, {"SEED": 11}, "pass", "qfd_su_master_ab", ram=16)]
    if full:
        out += [vbench("su_ab_s2", "tb_qfd_su_master_ab", tb, HDC_SU, {"IS": 2, "OS": 2, "CRX": 3, "SEED": 12}, "pass",
                       "qfd_su_master_ab", ram=16),
                vbench("su_ab_mutant", "tb_qfd_su_master_ab", tb, HDC_SU, {"MUT": 1}, "fail", "qfd_su_master_ab", ram=16)]
    return out


def seq_benches():
    out = []
    for name, extra, exp in (("seq_exact", "", "pass"), ("seq_mutant", "-Ptb_qfd_constants_sequencer.MUT=1", "fail")):
        b = dict(name=name, cmd=(f"mkdir -p {{RUN}}/bench && python3 tools/qwen_missing/emit_partition.py --check && "
                                 f"iverilog -g2012 -s tb_qfd_constants_sequencer {extra} -o {{RUN}}/bench/{name} "
                                 f"rtl/test/tb_qfd_constants_sequencer.sv {SEQ_SRC} && vvp -n {{RUN}}/bench/{name}"),
                 expect=exp, threads=1, peak_ram_gb=4, needs=["iverilog"])
        b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_constants_sequencer"
        out.append(b)
    return out


def job(cfg, commit, purpose, benches, ram, macros=(), cycles="", threads=16):
    name = f"{cfg}-{commit[:9]}tt"
    sdc = f"physical/qwen_die_masters/signoff/{cfg}.sdc"
    route = (f"export OT_TTB_CORNER_MARK={{CL}}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {{SRC}} && "
             f"export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl "
             f"physical/common_flow/link_budget_hook.tcl'; export OT_ORFS_CORNER_OVERRIDE=TC; OT_MM_FF_SDC='{sdc}' "
             f"SRC={{SRC}} bash physical/qwen_die_masters/jobs/route_master.sh {cfg} {{LABEL}} {{RUN}}/routes")
    spec = dict(
        name=name, block=cfg, owner="Claude:qwen-rtl-finish",
        purpose=purpose + " | OPTION B TT route (ORFS corner TC = setup repair at TT, MM FF hold HM 50 ps, rule H1, "
                          "CTS fix hooks + consistent die-link budget via tt_overlay)",
        hosts=HOSTS, threads=threads, peak_ram_gb=ram,
        source=dict(branch="claude/qwen-rtl-finish-20261007", commit=commit),
        stages=dict(
            bench=benches,
            calibrate=dict(enabled=False, reason="die-context IO referenced in-run (io_ref_skew.sdc) as every Qwen die master"),
            route=dict(cmd=route, ok="grep -q '^flow_rc=0' {RUN}/routes/{LABEL}/status && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/status",
                       logs=["{RUN}/routes/{LABEL}/flow.log"], threads=threads, peak_ram_gb=ram),
            collect=dict(cmd=("mkdir -p {RUN}/record/route {RUN}/record/views && cp {RUN}/routes/{LABEL}/corner_sta.json "
                              "{RUN}/routes/{LABEL}/status {RUN}/routes/{LABEL}/STATUS {RUN}/routes/{LABEL}/signoff.sdc "
                              "{RUN}/record/route/ && python3 tools/w18/export_view.py --orfs-dir {RUN}/routes/{LABEL}/work/orfs "
                              f"--name {cfg} --post-sdc {sdc} --corners ss,tt,ff --out {{RUN}}/record/views/{cfg} "
                              "> {RUN}/record/route/export.log 2>&1"))),
        verdict=dict(corner_sta="{RUN}/routes/{LABEL}/corner_sta.json",
                     drc_metrics="{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                     checks=[dict(name="ttb_routed_at_TC", cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")],
                     post_sdc=[sdc], macros=list(macros)),
        hold_eco={}, budget=dict(enabled=False, reason="no Qwen r21 budget sheet; die-master kit budgets applied in-run"),
        record=[dict(to="physical/qwen_die_masters/views", **{"from": "{RUN}/record/views"}),
                dict(to=f"results/rtl/qwen_rtl_finish_20261007/routes/{name}", **{"from": "{RUN}/record/route"})],
        cycles_added=cycles, merge_target=None, route_hold_corners="mm", route_hold_margin_ns=0.05, route_corner="TC")
    return name, spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=Path("/tmp/claude-review-20261003/closure_jobs"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    c = a.commit
    M = ["physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2"]
    jobs = [
        job("qfd_sp_tree_top", c, "r21 qfd_sp_tree_top: W12 spine control element + x descriptor, IS=OS=1 (the spine "
            "re-partitioned: lanes / port elements / VM x root are separate masters)", tree_benches(), 96,
            cycles="0 in the partition (IS=OS=0 composition cycle-identical to ot_qwen_me_spine_h_w12); stations IS+OS on "
                   "the issue loop (absorbed by the split controller's issue shell RT); x_rdy gate <= BMAX-2 = 6 edges per back-to-back ME op"),
        job("qfd_sp_tree_top_s2", c, "r21 qfd_sp_tree_top variant: IS=OS=2, PD 0.45", tree_benches()[:1], 96,
            cycles="as qfd_sp_tree_top with IS=OS=2"),
        job("qfd_sp_vector_memory", c, "r21 qfd_sp_vector_memory: banked VM (64 row banks x 2 ot_sram_1r1w_256x256), "
            "parallel ME x service (beats + stride decimation, XVM=15), row ports; 777.6 x 3110.4", vm_benches(), 256, M,
            cycles="XVM 1 -> 15 inside the fixed BD x-network budget (0 added); x_rdy issue gap <= 6 edges per back-to-back ME op"),
        job("qfd_sp_vector_memory_sq", c, "r21 qfd_sp_vector_memory variant: 1555.2 x 1555.2, PD 0.45", vm_benches(False), 256, M,
            cycles="as qfd_sp_vector_memory"),
        job("qfd_io_emb_root", c, "r21 qfd_io_embedding_rom root (die-face request FIFO + credits, bank decode, in-order "
            "one-bank issue over 8 column chains, response merge)", emb_benches(), 32, threads=8,
            cycles="token row fetch ~2 x 64 + 2 x 297 chain edges, hidden behind the SU embedding op's go hold"),
        job("qfd_io_emb_tap", c, "r21 qfd_io_embedding_rom column tap (one per bank parent)", emb_benches(False), 16,
            threads=8, cycles="one chain hop each way per tap"),
        job("qfd_sp_su64_sfu_ab", c, "r21 qfd_sp_su64_sfu RE-CUT (split-exact): control IS=OS=1, VM abutted, constant ROM "
            "ML=4, embedding row buffer; sign-off 1.111 ns (serial_0p9); REPLACES qfd_sp_su64_sfu-646cf264dtt",
            su_benches(), 160, cycles="SU element latency +ML (4) edges; embedding op go held for the row fetch (once per token)"),
        job("qfd_sp_su64_sfu_ab_s2", c, "r21 qfd_sp_su64_sfu RE-CUT variant IS=OS=2 (ML=6), sign-off 0.833 ns; REPLACES "
            "qfd_sp_su64_sfu_s2-646cf264dtt", su_benches(False), 160, cycles="SU element latency +6 edges"),
        job("qfd_sp_constants_sequencer", c, "r21 qfd_sp_constants_sequencer RE-CUT (split-exact): issue shell inside, "
            "me_mem_ok -> me_clk_en unstationed, embedding decode moved to the SU; REPLACES "
            "qfd_sp_constants_sequencer-646cf264dtt", seq_benches(), 96,
            cycles="issue shell RT window per go (split-exact classes A-C)"),
    ]
    a.out.mkdir(parents=True, exist_ok=True)
    for name, spec in jobs:
        if a.only and a.only not in name:
            continue
        (a.out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n")
        print(a.out / f"{name}.json")


if __name__ == "__main__":
    main()
