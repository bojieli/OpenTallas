#!/usr/bin/env python3
"""phys-intake 2026-10-09: closure-loop specs (2 variants: TC option B, HM 10 / HM 25, '-cl' line) for the elements
that had an implementation recorded but no physical job.  Recipe: physical/hbm_mtp/route_mtp.sh (generic TC route,
io_vclk_m IO budget, sign-off 833.333 / 60 ps + rule-H1 FF hold), as the struct-close mtp_fence_p2 '-cl' jobs.
Bench + mutant from physical/phys_intake/bench.sh, bound in every job.
    make_specs.py <source-commit> <outdir>"""
import json, sys
from pathlib import Path

COMMIT, OUT = sys.argv[1], Path(sys.argv[2])
BRANCH = "claude/phys-intake-20261009"
HOSTS = ["ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-epyc4", "ot-agidock128"]
HOOKS_LB = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl"
HOOKS = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl"
LT = "rtl/hbm_accel/tu/link_retry_sram_20261008"
M128 = "ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"
M256 = "ot_sram_1r1w_256x256_m2_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2"

E = [
 dict(el="ot_s81_host_dispatch", key="s81_host_dispatch", top="ot_s81_host_dispatch", tag="s81hdisp",
      srcs=["rtl/dsrom_sys/s81_ingest/ot_s81_host_dispatch.sv"], params=["ENABLE=1"], clk="ck", die=(150, 150),
      thr=8, ram=16, lb=1, cal=True,
      note="S81 host class dispatch + shared 8-credit ownership (ENABLE=1), as written at d61d74519 (0 cycles). "
           "Condition (REVIEW S4): the 1-bit state parity (state_p) is protected-control scope creep; strip it before adoption."),
 dict(el="ot_dsrom_hc_seed_join", key="hc_seed_join", top="ot_dsrom_hc_seed_join", tag="hcjoin",
      srcs=["rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_secded_pipe.sv",
            "rtl/experimental/dsrom_hc_capture_20261009/ot_dsrom_hc_seed_join.sv", "rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"],
      params=["ECC_PIPE=1"], clk="clk", die=(500, 500), macro=M256, halo=5, thr=12, ram=32, lb=1, cal=True,
      note="DS-ROM head-rank HC seed join, three real 256x256 SRAMs with SECDED72 (in rule: HC SRAM payload), ECC_PIPE=1 "
           "registered decoder (Codex c5dfa5e7f successor; its ad-hoc TC route join-route-r2 was NOT_MET TNS -254 ps, no loop job). "
           "REVIEW D6: no lease; epoch checks kept only as identity fields."),
 dict(el="HBM full-quarter VM collective publication", key="hbm_coll_vm_pub", top="ot_hbm_collective_vm_publication", tag="collvmpub",
      srcs=["rtl/common/ot_secded.sv", f"{LT}/ot_hbm_replay_sram.sv", f"{LT}/ot_hbm_collective_vm_publication.sv"],
      params=["ENABLE=1", "OWNER_W=74"], clk="clk", die=(520, 480), macro=M128, halo=4, thr=12, ram=40, lb=1, cal=True,
      note="Full 4096 FP32 collective VM publication, 24 x 128x256 SECDED replay SRAMs (in rule: SRAM payload), Qwen 74-bit owner "
           "(r25 runs Qwen, owner 10-09). The parent's VM read 'lease' is a static grant here (REVIEW S2: no lease hardware)."),
 dict(el="HBM protected TU PHY retry port", key="hbm_tu_retry_phy", top="ot_hbm_tu_retry_phy_port", tag="turetryphy",
      srcs=["rtl/common/ot_secded.sv", f"{LT}/ot_hbm_replay_sram.sv", f"{LT}/ot_hbm_link_retry_sram.sv", f"{LT}/ot_hbm_retry_pop_cdc.sv",
            f"{LT}/ot_hbm_retry_phy_ingress.sv", f"{LT}/ot_hbm_tu_retry_port.sv", f"{LT}/ot_hbm_tu_retry_phy_port.sv"],
      params=["ENABLE=1"], clk="clk", die=(440, 420), macro=M128, halo=4, thr=12, ram=40, lb=1, cal=True,
      sdcx="physical/phys_intake/tu_retry_pclk.sdc",
      note="TU PHY/core retry port: go-back-N replay + PHY ingress landing in 128x256 SECDED SRAMs (in rule: replay SRAM), two clocks "
           "(core clk + PHY pclk, async CDC groups, physical/phys_intake/tu_retry_pclk.sdc). REVIEW S4: retry-bookkeeping flop "
           "protection is not claimed."),
 dict(el="TA15 production clock controller readiness", key="ta15_prod_clock", top="ot_hbm_production_clock_digital_body", tag="ta15prod",
      srcs=["rtl/hbm_accel/control/ot_hbm_production_clock_digital_body.sv", "rtl/hbm_accel/control/ot_hbm_clock_reset_boundary.sv",
            "rtl/hbm_accel/control/ot_hbm_reset_seq.sv"],
      params=[], clk="clk_stream", die=(100.224, 99.36), thr=4, ram=12, lb=0, cal=False,
      sdcx="physical/hbm_accel_die_views/clock_boundary/production_body.sdc",
      note="TA15 full 91-FF digital boot/readiness body (analog PLL is a black box outside the block), five clocks per the owner's "
           "production_body.sdc (aon/stream/serial/hbm/link); first loop route of this composition (Codex r1-r4 were the 51-FF collar "
           "body only, TT -179 on async-intent inputs). W2: AON = reset/PLL-lock sync only, no power domain."),
 dict(el="hbm_native_mtp_emit_queue", key="hbm_mtp_emit_queue", top="ot_hbm_native_mtp_emit_queue", tag="mtpemitq",
      srcs=["rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue.sv"], params=["ENABLE=1"], clk="clk", die=(110, 110),
      thr=8, ram=12, lb=1, cal=True,
      note="Eight-entry native 38-bit emitted-token sink + ordered host 81-bit records (REVIEW M2: keep the emitted-token queue). "
           "Job epoch is carried as a record field only (MTP speculative identity, S3)."),
 dict(el="ot_hbm_native_ar_token_join", key="hbm_ar_token_join", top="ot_hbm_native_ar_token_join", tag="artokjoin",
      srcs=["rtl/hbm_accel/control/ot_hbm_token_loop.sv", "rtl/hbm_accel/control/ot_hbm_native_ar_token_join.sv",
            "rtl/hbm_accel/qwen/r25/ot_qwen_r25_cmdproc18.sv", "rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv"],
      params=["ENABLE=1", "QWEN=1"], clk="clk", die=None, util=40, thr=16, ram=64, lb=1, cal=True,
      note="Two 16-SM CP halves (Qwen r25 cmdproc18, QWEN=1: r25 runs Qwen TP4 per owner 10-09) joined to the native on-die AR token "
           "loop with TOKEN18 host records; core-utilisation 40 % auto-sized."),
 dict(el="ot_hbm_token_loop", key="hbm_token_loop", top="ot_hbm_token_loop", tag="tokloop",
      srcs=["rtl/hbm_accel/control/ot_hbm_token_loop.sv"], params=[], clk="clk", die=(130, 130), thr=8, ram=12, lb=1, cal=True,
      note="On-die AR/MTP token loop + stop rules + finite host-record FIFO (hbm-system R4 hfd_tloop, APPROVED S1; never queued)."),
]


def route_cmd(e, hm, cal):
    a = [f"--source {s}" for s in e["srcs"]] + [f"--param {p}" for p in e["params"]] + [f"--clock-port {e['clk']}"]
    env = [f"OUT={{RUN}}/routes", f"CORES={e['thr']}", f"UTIL={e.get('util', 40)}", "PD=0.55", f"HM={hm:.3f}", f"LB={e['lb']}"]
    if e.get("macro"):
        a += [f"--macro-view {e['macro']}", f"--macro-place-halo {e['halo']} {e['halo']}"]
        env += ["STAGES=pnr", f"MACRO={e['macro'].split('=')[1]}"]
    if e.get("sdcx"):
        env.append(f"SDCX={e['sdcx']}")
    if e.get("die"):
        w, h = e["die"]; m = 2.16 if w > 120 else 1.08
        a += [f"--die-area 0 0 {w} {h}", f"--core-area {m} {m} {round(w - m, 3)} {round(h - m, 3)}"]
    hooks = HOOKS_LB if e["lb"] else HOOKS
    pre = (f"export OT_TTB_CORNER_MARK={{CL}}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {{SRC}} && "
           f"export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='{hooks}'; ")
    lab = "{LABEL}${CL_LABEL_SUFFIX}" if cal else "{LABEL}"
    tail = " $CL_STOP_AFTER" if cal else ""
    return pre + " ".join(env) + f" bash physical/hbm_mtp/route_mtp.sh {lab} {e['top']} " + " ".join(a) + tail


def spec(e, hm):
    short = COMMIT[:9]
    name = f"pi-{e['tag']}-{short}-tc-hm{int(hm * 1000)}-cl"
    st = {
        "bench": [
            {"name": f"{e['key']}_exact", "cmd": f"bash physical/phys_intake/bench.sh {e['key']} pos {{RUN}}/bench_pos",
             "expect": "pass", "pass_regex": f"PHYSINTAKE_{e['key']}_PASS", "threads": 1, "peak_ram_gb": 4},
            {"name": f"{e['key']}_mutant", "cmd": f"bash physical/phys_intake/bench.sh {e['key']} neg {{RUN}}/bench_neg",
             "expect": "fail", "fail_regex": f"PHYSINTAKE_{e['key']}_NEG_FAIL", "threads": 1, "peak_ram_gb": 4},
        ],
        "route": {"cmd": route_cmd(e, hm, False),
                  "ok": "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                  "logs": ["{RUN}/routes/{LABEL}/run.log"]},
        "collect": {"cmd": "mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args "
                           "{RUN}/routes/{LABEL}/physical.json {RUN}/record/"},
    }
    if e["cal"]:
        st["calibrate"] = {"cmd": route_cmd(e, hm, True), "base": "{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base",
                           "clock": "core_clk", "threads": e["thr"], "peak_ram_gb": e["ram"]}
    else:
        st["calibrate"] = {"enabled": False, "reason": "multi-clock boot body (five clocks redefined by production_body.sdc): no single "
                           "core_clk insertion to calibrate; IO is the owner's provisional AON budget in that SDC"}
    post = ([e["sdcx"]] if e.get("sdcx") else []) + ["physical/hbm_accel_die_views/common/signoff_unc60.sdc",
                                                     "physical/hbm_accel_die_views/common/vclk_corner_true.sdc"]
    if e["lb"]:
        post.append("physical/common_flow/link_budget_consistent.sdc")
    return name, {
        "name": name, "block": e["top"], "element": e["el"], "owner": "Claude:phys-intake",
        "purpose": f"phys-intake 2026-10-09 (owner: start physical work on every 'implementation recorded (no physical job)' element; "
                   f"dual-track '-cl' line). {e['note']} Variant: TC route / option B (TT setup, FF hold, DRC 0), HM {int(hm * 1000)} ps. "
                   f"Exact bench + mutant: physical/phys_intake/bench.sh {e['key']} (pos PASS / mutant FAIL on this source).",
        "hosts": HOSTS, "threads": e["thr"], "peak_ram_gb": e["ram"],
        "source": {"branch": BRANCH, "commit": COMMIT},
        "stages": st,
        "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                    "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                    "checks": [{"name": "ttb_routed_at_TC", "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                    "post_sdc": post},
        "route_hold_corners": "mm", "route_hold_margin_ns": hm, "route_corner": "TC",
        "cycles_added": 0, "notes": "cycles added: 0 (RTL as written)", "merge_target": None,
    }


OUT.mkdir(parents=True, exist_ok=True)
for e in E:
    for hm in (0.010, 0.025):
        n, s = spec(e, hm)
        (OUT / f"{n}.json").write_text(json.dumps(s, indent=1) + "\n")
        print(n)
