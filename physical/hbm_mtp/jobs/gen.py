import json, sys
C1 = "d30fa5f390491bf8059e4af8d7d7ea7ce383d33a"; C2 = "fc1b8a377bfd9676a35e3fec7b87bc1b7316288c"
BR = "claude/mtp-hbm-20261008"
FP = ("rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv "
      "rtl/gpu/ot_gpu_fadd.sv")
M = "physical/hbm_mtp/rtl/"
TOPM = (M + "hfd_mtp_tops.sv " + M + "ot_hfd_mtp_core.sv " + M + "ot_hfd_mtp_skid.sv " + M + "ot_dshbm_dspark_top_m.sv " +
        M + "ot_dshbm_dspark_ctl_m.sv " + M + "ot_dshbm_argmax_m.sv " + M + "ot_dshbm_expert_union_m.sv " +
        "rtl/gpu/dshbm/ot_dshbm_accept_port.sv rtl/hdc/ot_hdc_accept.sv rtl/gpu/dshbm/ot_dshbm_spec_state.sv "
        "rtl/gpu/dshbm/ot_dshbm_spec_state_f.sv rtl/gpu/ot_gpu_router_topk.sv rtl/gpu/ot_gpu_router_topk_f.sv " + FP)
def srcs(s): return " ".join(f"--source {x}" for x in s.split())
def params(p): return " ".join(f"--param {k}={v}" for k, v in p.items())
def job(name, block, top, src, prm, purpose, commit=C1, lvt=False, util=40, threads=16, ram=40, lb=0, extra="",
        env="", macro=None, cycles=0, bench=None, no_bench=None, hm="0.025", die=None):
    pre = ("export OT_TTB_CORNER_MARK={CL}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {SRC} && "
           "export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
           "physical/common_flow/clk_net_protect.tcl" + (" physical/common_flow/link_budget_hook.tcl" if lb else "") + "'; "
           + ("export OT_MULTI_VT=lvt; " if lvt else ""))
    da = f"--die-area 0 0 {die} {die} --core-area 6 6 {die-6} {die-6}" if die else ""
    mv = f"--macro-view {macro.split('/')[-1]}={macro} --macro-place-halo 10 10" if macro else ""
    base = (f"{env} OUT={{RUN}}/routes CORES={threads} UTIL={util} PD=0.55 HM={hm} LB={lb} "
            + (f"MACRO={macro} " if macro else "") + f"bash physical/hbm_mtp/route_mtp.sh {{LABEL}}${{CL_LABEL_SUFFIX}} {top} "
            f"{srcs(src)} {params(prm)} {mv} {da} {extra}")
    cal = pre + base.replace("${CL_LABEL_SUFFIX}", "${CL_LABEL_SUFFIX}") + " $CL_STOP_AFTER"
    rte = pre + base.replace("${CL_LABEL_SUFFIX}", "")
    post = ["physical/hbm_accel_die_views/common/signoff_unc60.sdc", "physical/hbm_accel_die_views/common/vclk_corner_true.sdc"]
    if lb: post.append("physical/common_flow/link_budget_consistent.sdc")
    d = dict(name=name, block=block, owner="Claude:mtp-hbm", purpose=purpose, hosts=["ot-epyc2", "ot-epyc1tb", "ot-epyc3"],
             threads=threads, peak_ram_gb=ram, source=dict(branch=BR, commit=commit),
             stages=dict(bench=bench or [],
                         calibrate=dict(cmd=cal, base="{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base", clock="core_clk",
                                        threads=threads, peak_ram_gb=ram),
                         route=dict(cmd=rte, ok="grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                                    logs=["{RUN}/routes/{LABEL}/run.log"]),
                         collect=dict(cmd="mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args {RUN}/routes/{LABEL}/physical.json {RUN}/record/")),
             verdict=dict(corner_sta="{RUN}/routes/{LABEL}/corner_sta.json",
                          drc_metrics="{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                          checks=[dict(name="ttb_routed_at_TC", cmd="test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt")],
                          post_sdc=post, **({"macros": [macro]} if macro else {})),
             record=[{"from": "{RUN}/record", "to": f"results/rtl/hbm_mtp_20261008/routes/{name}"}],
             merge_target=None, route_hold_corners="mm", route_hold_margin_ns=float(hm), route_corner="TC",
             cycles_added=cycles, notes=f"cycles added: {cycles}")
    if no_bench: d["no_bench_reason"] = no_bench
    return d
NB_REQ = ("RTL byte-identical to the 10-05 closure (results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/"
          "closure.json observed_* + its lockstep benches, rtl/test/hbm_fmax_ctl); TC requeue on the current flow only")
REQ = ("mtp-hbm 2026-10-08 REQUEUE at TC (owner directive): 10-05 SS-era closure re-STA'd on its routed DB under the current "
       "IO model (results/rtl/hbm_mtp_20261008/resta): internal reg->reg closes at TT, the misses are IO-model only "
       "(0.2 T vs the ideal clock edge -> vclk at the routed insertion + consistent die-link split; H1 input hold). "
       "Sub-block of the die block hfd_mtp: IO judged at the die-view convention (io_vclk_m 0.2 T + 150 ps vs vclk), "
       "the die-link budget applies at hfd_mtp's registered pins. ")
J = []
J.append(job("mtp_accept_a0-d30fa5f39-tc", "ot_hdc_accept", "ot_hdc_accept", "rtl/hdc/ot_hdc_accept.sv", dict(NSLOT=8, NW=17),
             REQ + "re-STA: TT -125.5 (in->reg, link split) / r2r +297.2; FF -1.9 (in, H1).", no_bench=NB_REQ))
J.append(job("mtp_ctl_f2-d30fa5f39-tc", "ot_dshbm_dspark_ctl", "ot_dshbm_dspark_ctl",
             "rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_accept.sv rtl/gpu/dshbm/ot_dshbm_accept_port.sv rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv",
             dict(TW=17, NL=40, MAXPOS=1048576, ACCEPT_LEAF=0, FAST=1),
             REQ + "re-STA: TT -364.0 (out cmd_toks: p_tok feedthrough) / r2r +271.4; FF -3.4 (in).", no_bench=NB_REQ))
J.append(job("mtp_argmax_f1-d30fa5f39-tc", "ot_dshbm_argmax_m", "ot_dshbm_argmax_m", FP + " " + M + "ot_dshbm_argmax_m.sv",
             dict(LP=8, IW=17, FLAT=7, FAST=1), REQ + "routed DB of argmax_f1 deleted (localhost cleanup): no re-STA possible; "
             "module renamed _m (byte-identical body to the 10-05 source_set file).", no_bench=NB_REQ, cycles=1))
J.append(job("mtp_union_f3-d30fa5f39-tc", "ot_dshbm_expert_union_m", "ot_dshbm_expert_union_m", M + "ot_dshbm_expert_union_m.sv",
             dict(NE=384, K=6, PM=8, IW=9, FAST=1), REQ + "routed DB of union_f3 deleted: no re-STA; union_a0 (non-FAST) re-STA "
             "r2r -135.7 confirms FAST is needed.", no_bench=NB_REQ, cycles=1))
MAC = "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2"
J.append(job("mtp_scratch_c2-d30fa5f39-tc", "ot_gpu_scratch_service_m", "ot_gpu_scratch_service_m",
             M + "ot_gpu_scratch_service_m.sv " + MAC + "/ot_sram_1r1w_1024x256_m2_r2c2_bb.v", dict(CAP2=1),
             REQ + "routed DB of scratch_c2 deleted; scratch_a1 (CAP2 0) re-STA r2r +84.3 / in -142.2. CAP2 multicycle SDC "
             "physical/hbm_mtp/scratch_cap2.sdc (design intent).", no_bench=NB_REQ, cycles=1, util=15, macro=MAC,
             env="SDCX=physical/hbm_mtp/scratch_cap2.sdc"))
FB = [dict(name="fence_p_exact", cmd="bash physical/hbm_mtp/run_fence_bench.sh {RUN}/bench 0", expect="pass",
           pass_regex=r"seed 29: FENCE_P PASS", threads=1, peak_ram_gb=2),
      dict(name="fence_p_mutant", cmd="bash physical/hbm_mtp/run_fence_bench.sh {RUN}/bench_neg 1 7", expect="fail",
           fail_regex=r"FENCE_P FAIL", threads=1, peak_ram_gb=2)]
FEN = ("mtp-hbm 2026-10-08 fence (owner: pipeline-cut variant + LVT variant). fence_a1 re-STA TT -613.6 = in->out "
       "feedthrough cap_addr -> cap_legal -> host_wr_valid (and 4,096-bit cap_data -> host_wdata wire); r2r +258.3. ")
J.append(job("mtp_fence_p-d30fa5f39-tc", "ot_gpu_rf_visibility_fence_p", "ot_gpu_rf_visibility_fence_p",
             "rtl/gpu/ot_gpu_rf_visibility_fence.sv " + M + "ot_hfd_mtp_skid.sv " + M + "ot_gpu_rf_visibility_fence_p.sv", {},
             FEN + "PIPELINE CUT (template D): the unmodified fence between registered skid slices / pin flops; exact vs "
             "the original (tb_fence_p, 4 seeds, mutant detected). Die-boundary block: link budget on.",
             bench=FB, cycles=2, die=300, lb=1, ram=40))
J.append(job("mtp_fence_a1_lvt-fc1b8a377-tc", "ot_gpu_rf_visibility_fence", "ot_gpu_rf_visibility_fence",
             "rtl/gpu/ot_gpu_rf_visibility_fence.sv", dict(ENABLE=1),
             FEN + "LVT variant of the ORIGINAL RTL (owner directive). Expected NOT to close: the miss is a structural IO "
             "feedthrough, not a near-miss; kept as the comparison row.", commit=C2, lvt=True, die=230, lb=1,
             no_bench="RTL unchanged (rtl/gpu/ot_gpu_rf_visibility_fence.sv, benched by rtl/test/hbm_rf_visibility); flow variant"))
TK = ("mtp-hbm 2026-10-08 router_topk (owner: fix the Yosys issue and route). topk_f1 (REG_IN=1, 10-04) died in Yosys 0.68 "
      "'modules_.count(module->name) == 0' under run_abi3 --param on a parameterised top; fix = parameter-free wrapper "
      "physical/hbm_mtp/rtl/mtp_topk_tops.sv (route-tops lesson). Successor ot_gpu_router_topk_f (topk_f3 10-05 routed "
      "SS -369.8 r2r; lockstep 2,000 vectors exact). ")
NBT = "RTL = ot_gpu_router_topk_f (rtl/test/hbm_fmax_ctl/tb_router_topk_lockstep.sv: N 384 P 16 K 6, 2,000 vectors, 0 mismatches vs ot_gpu_router_topk)"
J.append(job("mtp_topk_f384-d30fa5f39-tc", "mtp_topk_f384", "mtp_topk_f384",
             "rtl/gpu/ot_gpu_router_topk.sv rtl/gpu/ot_gpu_router_topk_f.sv physical/hbm_mtp/rtl/mtp_topk_tops.sv", {},
             TK, threads=24, ram=60, util=35, no_bench=NBT, cycles=1))
J.append(job("mtp_topk_f384_lvt-fc1b8a377-tc", "mtp_topk_f384", "mtp_topk_f384",
             "rtl/gpu/ot_gpu_router_topk.sv rtl/gpu/ot_gpu_router_topk_f.sv physical/hbm_mtp/rtl/mtp_topk_tops.sv", {},
             TK + "LVT variant.", commit=C2, lvt=True, threads=24, ram=60, util=35, no_bench=NBT, cycles=1))
HB = ("mtp-hbm 2026-10-08 hfd_mtp (HBM die block of the DSpark control plane; owner: route as soon as it lints, 2-3 safe "
      "variants). ot_hfd_mtp_core = ot_dshbm_dspark_top_m (ctl FAST + accept, spec_state_f, argmax FAST, union FAST) "
      "behind registered pins (template D): pin flops, 3 skid slices (cmd out, spec-state request in, union out), "
      "token reads PRL 2. Exactness: physical/hbm_mtp/run_bench.sh on the golden traces (results/rtl/hbm_mtp_20261008/"
      "bench), gates adoption; spec_state_f's 2-mismatch fix is mtp-exact's (re-route on its commit). Die-link budget on "
      "(consistent split until mtp-die publishes the hfd_mtp budget). ")
NBH = ("golden-trace benches (tb_hfd_mtp_dspark, traces from tools/dshbm_dspark_trace.py, ~10 MB scripts not in the repo) "
       "run beside the route: results/rtl/hbm_mtp_20261008/bench (PASS required for adoption; MUT 1/2 must FAIL)")
J.append(job("hfd_mtp-d30fa5f39-tc", "hfd_mtp", "hfd_mtp", TOPM, {}, HB + "VARIANT A: both router selectors inside "
             "(2 x ot_gpu_router_topk_f 384/6, ~29k um2 each).", threads=32, ram=120, util=45, lb=1, no_bench=NBH, cycles=4))
J.append(job("hfd_mtp_x-d30fa5f39-tc", "hfd_mtp_x", "hfd_mtp_x", TOPM, {}, HB + "VARIANT X: selections from the die's "
             "hfd_router selector (x_* pins), no selectors inside (smaller, fewer pins: rv 512 b -> x 58 b).",
             threads=24, ram=60, util=45, lb=1, no_bench=NBH, cycles=4))
J.append(job("hfd_mtp_x_lvt-fc1b8a377-tc", "hfd_mtp_x", "hfd_mtp_x", TOPM, {}, HB + "VARIANT X + LVT.", commit=C2, lvt=True,
             threads=24, ram=60, util=45, lb=1, no_bench=NBH, cycles=4))
for j in J:
    json.dump(j, open(f"/tmp/mtphbm_jobs/{j['name']}.json", "w"), indent=1)
    print(j["name"])
