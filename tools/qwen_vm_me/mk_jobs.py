#!/usr/bin/env python3
"""Closure-loop job specs of stream qwen-vm-me (2026-10-08): one OPTION-B TT route per new / changed master variant
(ORFS corner TC = setup repair at TT, MM hold at FF with HM 50 ps, rule H1 and the CTS fix hooks + the consistent
die-link budget through tools/closure_loop/tt_overlay.py of the job's own source snapshot), each with its exact benches
and negative mutants (benches gate adoption, not launch).

    mk_jobs.py --commit <sha> [--out /tmp/claude-review-20261003/closure_jobs] [--only <substr>]
"""
import argparse
import json
from pathlib import Path

HOSTS = ["ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-pve1", "ot-agidock128"]
VER = "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
VFL = ("--binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH "
       "-Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT")
VM_SRC = ("rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv "
          "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv "
          "rtl/hdc/ot_hdc_delay.sv")
SU_SRC = ("rtl/qwen_sys/vm_me_20261008/ot_qfd_su_master_bv.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv "
          "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv "
          "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv "
          "rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv "
          "rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv "
          "rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_vstream.sv rtl/hdc/ot_hdc_fp32_add_lat.sv "
          "rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_reduce.sv rtl/hdc/ot_hdc_reduce_q.sv "
          "rtl/proto/ot_fp32_add_rne_pipe.sv rtl/proto/ot_fp32_mul_rne_pipe.sv")


def vbench(name, top, tb, srcs, params, expect, tag, threads=8, ram=8):
    g = " ".join(f"-G{k}={v}" for k, v in params.items())
    cmd = (f"mkdir -p {{RUN}}/bench && {VER} {VFL} -j {threads} --top-module {top} {g} --Mdir {{RUN}}/bench/{name} "
           f"{tb} {srcs} && {{RUN}}/bench/{name}/V{top}")
    b = dict(name=name, cmd=cmd, expect=expect, threads=threads, peak_ram_gb=ram, needs=["verilator"])
    b["pass_regex" if expect == "pass" else "fail_regex"] = f"^{'PASS' if expect == 'pass' else 'FAIL'} {tag}"
    return b



def vm_benches(full=True):
    tb = "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv"
    t, tag = "tb_qfd_vm_bv_ports", "qfd_vm_bv_ports"
    out = [vbench("vm_ports_s5", t, tb, VM_SRC, {"SEED": 5}, "pass", tag),
           vbench("vm_ports_mut", t, tb, VM_SRC, {"MUT": 1}, "fail", tag)]
    if full:
        out += [vbench("vm_ports_s9", t, tb, VM_SRC, {"SEED": 9, "CYCLES": 60000, "RSD": 8}, "pass", tag),
                vbench("vm_ports_big", t, tb, VM_SRC, {"ELEMS": 65536, "NRB": 64, "SW": 64, "SMAX": 9, "SMIN": 5, "BMAX": 8,
                                                       "XVM": 15, "XRN": 16384, "SEED": 7, "CYCLES": 20000}, "pass", tag, ram=24),
                vbench("vm_ports_xmut", t, tb, VM_SRC, {"MUT": 2}, "fail", tag)]
    return out


def ser_benches():
    tb = "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv"
    return [vbench("res_ports_s3", "tb_qfd_vm_bv_ports", tb, VM_SRC, {"SEED": 3, "CYCLES": 40000}, "pass", "qfd_vm_bv_ports"),
            vbench("res_ports_smut", "tb_qfd_vm_bv_ports", tb, VM_SRC, {"SMUT": 1}, "fail", "qfd_vm_bv_ports")] + \
        landed_benches()


def su_benches(full=True):
    tb = "rtl/test/qwen_vm_me/tb_qfd_su_vm_bv.sv"
    t, tag = "tb_qfd_su_vm_bv", "qfd_su_vm_bv"
    out = [vbench("su_vm_exact", t, tb, SU_SRC, {"SEED": 11}, "pass", tag, ram=16),
           vbench("su_vm_mut", t, tb, SU_SRC, {"MUT": 1}, "fail", tag, ram=16)]
    if full:
        out += [vbench("su_vm_s2", t, tb, SU_SRC, {"IS": 2, "OS": 2, "CRX": 3, "SEED": 12}, "pass", tag, ram=16),
                vbench("su_vm_vmut", t, tb, SU_SRC, {"VMUT": 1}, "fail", tag, ram=16)]
    return out


def landed_benches():
    run = "rtl/test/qwen_vm_me/run_spine_landed.sh"
    out = []
    for name, g, exp in (("landed_exact", "-GCYCLES=40000", "pass"), ("landed_smut", "-GSMUT=1", "fail")):
        b = dict(name=name, cmd=f"mkdir -p {{RUN}}/bench && JOBS=8 bash {run} {{RUN}}/bench/{name} {g}",
                 expect=exp, threads=8, peak_ram_gb=16, needs=["verilator"])
        b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_spine_landed"
        out.append(b)
    return out


def tt_benches():
    run = "rtl/test/qwen_rtl_finish/run_tree_top.sh"
    out = landed_benches()
    for name, g, exp in (("tt_lockstep", "", "pass"), ("tt_mutant", "-GMUT=1", "fail")):
        b = dict(name=name, cmd=f"mkdir -p {{RUN}}/bench && JOBS=8 bash {run} {{RUN}}/bench/{name} 30000 {g}; "
                 f"grep -q '\"mismatch_cycles\": 0,' {{RUN}}/bench/{name}/result.json && echo PASS qfd_tree_top || echo FAIL qfd_tree_top",
                 expect=exp, threads=8, peak_ram_gb=16, needs=["verilator"])
        b["pass_regex" if exp == "pass" else "fail_regex"] = f"^{'PASS' if exp == 'pass' else 'FAIL'} qfd_tree_top"
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
        name=name, block=cfg, owner="Claude:qwen-vm-me",
        purpose=purpose + " | OPTION B TT route (ORFS corner TC = setup repair at TT, MM FF hold HM 50 ps, rule H1, "
                          "CTS fix hooks + consistent die-link budget via tt_overlay)",
        hosts=HOSTS, threads=threads, peak_ram_gb=ram,
        source=dict(branch="claude/qwen-vm-me-20261007", commit=commit),
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
                dict(to=f"results/rtl/qwen_vm_me_20261008/routes/{name}", **{"from": "{RUN}/record/route"})],
        cycles_added=cycles, merge_target=None, route_hold_corners="mm", route_hold_margin_ns=0.05, route_corner="TC")
    return name, spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", type=Path, default=Path("/tmp/claude-review-20261003/closure_jobs"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    c = a.commit
    MV = ["physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2", "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2"]
    MS = ["physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2"]
    vm_cost = ("SU operand reads at 1 + VL = 8 edges (base 1): the SU lanes run at ML = 7 (ab: 4), +3 edges per SU element; "
               "result rows reach the memory one a cycle (6:1 merge) and the tree top counts LANDED bursts (an op's progress "
               "/ idle wait for its rows); a result burst costs max(rows, 1) merge cycles, the engine stalls (me_mem_ok) when a "
               "band store has < RS + 2 bursts of room")
    jobs = [
        job("qfd_sp_vector_memory_bv", c, "r21m qfd_sp_vector_memory_bv: banked VM + 3 SU replica copies (16 banks x 2 "
            "ot_sram_1r1w_1024x256 each, descriptor reads VL 7), bank-write arbiter with skid queues, 6:1 ME result merge "
            "(CRB 16), land_cnt / me_ok; 777.6 x 6220.8 PD 0.50", vm_benches(), 320, MV, cycles=vm_cost),
        job("qfd_sp_vector_memory_bv_t", c, "r21m qfd_sp_vector_memory_bv AGGRESSIVE variant: 777.6 x 7776 PD 0.42",
            vm_benches(full=False), 320, MV, cycles=vm_cost),
        job("qfd_sp_su64_sfu_bv", c, "r21m qfd_sp_su64_sfu_bv: SU master with banked-VM descriptor ports (VL 7, ML 7), "
            "IS=OS=1, core clock 0.833 ns; REPLACES qfd_sp_su64_sfu_ab in r21m", su_benches(), 160,
            cycles="SU element latency ML 7 (ab 4): +3 edges per element"),
        job("qfd_sp_su64_sfu_bv_s2", c, "r21m qfd_sp_su64_sfu_bv variant IS=OS=2 (ML 7), PD 0.45", su_benches(full=False), 160,
            cycles="as qfd_sp_su64_sfu_bv; IS+OS 4"),
        job("qfd_sp_res_ser", c, "r21m qfd_sp_res_ser: band result serializer (8 x ot_sram_1r1w_64x512, DB 64, RS 40, CRB 16); "
            "777.6 x 518.4 PD 0.50", ser_benches(), 64, MS, threads=8,
            cycles="results one row a cycle per band into the merge; engine stall when < RS + 2 bursts of room"),
        job("qfd_sp_res_ser_t", c, "r21m qfd_sp_res_ser AGGRESSIVE variant: 777.6 x 691.2 PD 0.40", ser_benches()[:2], 64, MS,
            threads=8, cycles="as qfd_sp_res_ser"),
        job("qfd_sp_tree_top_l", c, "r21m qfd_sp_tree_top_l: tree top with LANDED progress / idle (land_cnt IS-stationed); "
            "REPLACES qfd_sp_tree_top in r21m", tt_benches(), 96,
            cycles="progress / idle wait for landed result bursts (the merge's landing, priced with the VM)"),
        job("qfd_sp_tree_top_l_s2", c, "r21m qfd_sp_tree_top_l variant IS=OS=2, PD 0.45", tt_benches()[:2], 96,
            cycles="as qfd_sp_tree_top_l with IS=OS=2"),
    ]
    a.out.mkdir(parents=True, exist_ok=True)
    for name, spec in jobs:
        if a.only and a.only not in name:
            continue
        (a.out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n")
        print(a.out / f"{name}.json")


if __name__ == "__main__":
    main()
