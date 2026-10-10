#!/usr/bin/env python3
"""strip-protect 2026-10-09: closure-loop specs for the unprotected successors (PROTECT=0) and the TA15 collar successor.
Two variants per element (TC route / option B: TT setup, FF hold, DRC 0; mm hold, HM 10 and HM 25; '-cl' line), recipe as
phys-intake (physical/hbm_mtp/route_mtp.sh; dsfd_host_native on the ingest recipe physical/rom_host_ingest/route.sh).
Exact bench + mutant: physical/strip_protect/bench.py <key> pos|neg.
    make_specs.py <source-commit> <outdir> [<scan-commit>]
The two ot_hbm_index_global_order elements share one top; the loop allows 3 routes per (block, commit), so the
STATIC_SCAN pair is pinned to a later commit of this branch with the same RTL (<scan-commit>)."""
import json, sys
from pathlib import Path

COMMIT, OUT = sys.argv[1], Path(sys.argv[2])
SCAN_COMMIT = sys.argv[3] if len(sys.argv) > 3 else COMMIT
BRANCH = "claude/strip-protect-20261009"
HOSTS = ["ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-epyc4", "ot-agidock128"]
HOOKS_LB = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl"
HOOKS = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl"
IDX = "rtl/hbm_accel/index/"
S4 = "REVIEW_20261009 S4/X3 (CONFIRMED): no mirrors / complement copies / TMR / parity on control flops"
E = [
 dict(el="ot_hbm_native_candidate_format", key="cand_format", top="ot_hbm_native_candidate_format", tag="candfmt",
      srcs=[IDX + "ot_hbm_native_candidate_format.sv"], params=["ENABLE=1", "PROTECT=0"], die=(150, 150), thr=8, ram=12, lb=1,
      note=f"Unprotected successor: the complemented mirror of every payload/control flop and FIFO entry removed ({S4}); "
           "1,219 flop bits vs 2,438 protected (Yosys). Same TU545 output, cycle for cycle."),
 dict(el="ot_hbm_native_candidate_parse", key="cand_parse", top="ot_hbm_native_candidate_parse", tag="candparse",
      srcs=[IDX + "ot_hbm_native_candidate_parse.sv"], params=["ENABLE=1", "PROTECT=0"], die=(150, 150), thr=8, ram=12, lb=1,
      note=f"Unprotected successor: held-flit/owner/slot complemented mirrors removed ({S4}); 624 flop bits vs 1,248."),
 dict(el="ot_hbm_native_index_query_credit", key="query_credit", top="ot_hbm_native_index_query_credit", tag="qcredit",
      srcs=[IDX + "ot_hbm_native_index_query_credit.sv"], params=["ENABLE=1", "PROTECT=0"], die=(200, 200), thr=8, ram=12, lb=1,
      note=f"Unprotected successor: credit/order/qb complemented mirrors removed ({S4}); 1,061 flop bits vs 2,121."),
 dict(el="ot_hbm_native_index_control", key="index_control", top="ot_hbm_native_index_control", tag="ictl",
      srcs=["rtl/hbm_accel/control/ot_hbm_native_index_control.sv"], params=["ENABLE=1", "PREFETCH=1", "PROTECT=0"], die=(180, 180),
      thr=8, ram=12, lb=1,
      note=f"Unprotected successor: desc_n/mask_n/ctl_n complemented mirrors removed ({S4}); 484 flop bits vs 968. PREFETCH=1 (native key prefetch)."),
 dict(el="ot_hbm_index_global_order", key="global_order", top="ot_hbm_index_global_order", tag="gorder",
      srcs=[IDX + "ot_hbm_index_global_order.sv"], params=["ENABLE=1", "STATIC_SCAN=0", "PROTECT=0"], die=None, util=40, thr=16, ram=32, lb=1,
      note=f"Unprotected successor of the Full96 order merge: head_n/ordinal_n/valid_n/last_n and tournament-node complemented mirrors removed ({S4})."),
 dict(el="ot_hbm_index_global_order_scan", key="global_order_scan", top="ot_hbm_index_global_order", tag="gorderscan", scan=True,
      srcs=[IDX + "ot_hbm_index_global_order.sv"], params=["ENABLE=1", "STATIC_SCAN=1", "PROTECT=0"], die=None, util=40, thr=16, ram=32, lb=1,
      note=f"Unprotected successor, STATIC_SCAN=1 (no tournament): head/valid/ordinal complemented mirrors removed ({S4})."),
 dict(el="ot_s81_ingest_visibility_fence", key="vis_fence", top="ot_s81_ingest_visibility_fence", tag="visfence",
      srcs=["rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv", "rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"],
      params=["ENABLE=1", "PROTECT=0"], clk="ck", die=(120, 120), thr=8, ram=12, lb=0, sdcx="physical/strip_protect/fence_clkh.sdc",
      note=f"Unprotected successor: SECDED on the 8-entry FLOP completion queue (X2: SECDED is for SRAM only) and the pointer/credit/"
           f"commit/snapshot/landed parity removed ({S4}); the visibility fence itself, overflow / monotonic / credit range checks kept. "
           "Two clocks (ck ack counting, clk_h host), async groups (physical/strip_protect/fence_clkh.sdc)."),
 dict(el="dsfd_host_native", key="host_native", top="dsfd_host_native", tag="hostnative", hing=True,
      srcs=["rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv", "rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv",
            "rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"], params=["ENABLE=1", "PROTECT=0"], thr=12, ram=24,
      note="Native S81 host ABI (dsfd_host + visibility fence) with the unprotected fence (PROTECT=0, as ot_s81_ingest_visibility_fence). "
           "Ingest recipe (physical/rom_host_ingest/route.sh, clk_i = ck/2, UTIL 30 / PD 0.45 like hing_dsfd_C -cl), top overridden."),
 dict(el="ot_qwen_r25_causal_mask", key="causal_mask", top="ot_qwen_r25_causal_mask", tag="cmask",
      srcs=["rtl/qwen_r25_su_dispatch/ot_qwen_r25_causal_mask_flat.sv"], params=["ENABLE=1", "CAPACITY=8224", "PROTECT=0"],
      die=(130, 130), thr=8, ram=12, lb=1,
      note=f"Unprotected successor: SECDED8 on the six transient mask/context seats removed (U3/S4: flops, not SRAM); 384 seat flop "
           "bits vs 432. NOTE U3: the p4 (DSpark verify) mask itself waits for tau; route is pathfinding for that line."),
 dict(el="ot_s81_host_dispatch", key="host_dispatch", top="ot_s81_host_dispatch", tag="s81hdispnp",
      srcs=["rtl/dsrom_sys/s81_ingest/ot_s81_host_dispatch.sv"], params=["ENABLE=1", "PROTECT=0"], die=(150, 150), thr=8, ram=16, lb=1,
      note=f"Successor of pi-s81hdisp (queued as written): the 1-bit state parity state_p stripped ({S4}), alongside that job."),
 dict(el="TA15 digital clock reset collars", key="ta15_rs", top="ot_hbm_clock_reset_collars_rs", tag="ta15rs", ta15=True,
      srcs=["rtl/hbm_accel/control/ot_hbm_clock_reset_collars_rs.sv"], params=["LINK_PORTS=9"], clk="clk_stream",
      die=(100.224, 99.36), thr=4, ram=12, lb=0, sdcx="physical/strip_protect/ta15_collars_rs.sdc",
      note="TA15 collars, standard reset structure: per-endpoint 2-flop synchroniser (async assert / sync deassert, the only flops "
           "on a raw async input) + 1 registered tree stage reset by the SYNCHRONISED reset (recovery/removal timed in the "
           "destination clock) driving the port; AON inputs on a virtual clock aon_v, only false path = raw assert edge, raw "
           "deassert into the synchroniser bounded 500/0 ps. Same 3-edge release. Fixes r4 TT -179 (cross-clock recovery at a 1.35 ps "
           "LCM edge). review_queue/strip-protect.md."),
]


def route_cmd(e, hm, cal):
    if e.get("hing"):
        xs = " ".join(e["srcs"])
        return (f"export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='{HOOKS}'; SRC=\"{{SRC}}\" OUT=\"{{RUN}}/routes\" DIV=\"2\" "
                f"UTIL=\"30\" PD=\"0.45\" HM=\"{hm:.3f}\" NEED=\"24\" XSRCS=\"{xs}\" bash physical/rom_host_ingest/route.sh {{LABEL}} dsfd_host "
                f"--top {e['top']} " + " ".join(f"--param {p}" for p in e["params"]))
    a = [f"--source {s}" for s in e["srcs"]] + [f"--param {p}" for p in e["params"]] + [f"--clock-port {e.get('clk', 'clk')}"]
    env = ["OUT={RUN}/routes", f"CORES={e['thr']}", f"UTIL={e.get('util', 40)}", "PD=0.55", f"HM={hm:.3f}", f"LB={e['lb']}"]
    if e.get("sdcx"):
        env.append(f"SDCX={e['sdcx']}")
    if e.get("die"):
        w, h = e["die"]; m = 2.16 if w > 120 else 1.08
        a += [f"--die-area 0 0 {w} {h}", f"--core-area {m} {m} {round(w - m, 3)} {round(h - m, 3)}"]
    hooks = HOOKS_LB if e["lb"] else HOOKS
    pre = (f"export OT_TTB_CORNER_MARK={{CL}}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {{SRC}} && "
           f"export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='{hooks}'; ")
    lab = "{LABEL}${CL_LABEL_SUFFIX}" if cal else "{LABEL}"
    return pre + " ".join(env) + f" bash physical/hbm_mtp/route_mtp.sh {lab} {e['top']} " + " ".join(a) + (" $CL_STOP_AFTER" if cal else "")


def spec(e, hm):
    commit = SCAN_COMMIT if e.get("scan") else COMMIT
    name = f"sp-{e['tag']}-{commit[:9]}-tc-hm{int(hm * 1000)}-cl"
    b = "python3 physical/strip_protect/bench.py"
    st = {
        "bench": [
            {"name": f"{e['key']}_exact", "cmd": f"{b} {e['key']} pos {{RUN}}/bench_pos", "expect": "pass",
             "pass_regex": f"STRIP_{e['key']}_PASS", "threads": 1, "peak_ram_gb": 4},
            {"name": f"{e['key']}_mutant", "cmd": f"{b} {e['key']} neg {{RUN}}/bench_neg", "expect": "fail",
             "fail_regex": f"STRIP_{e['key']}_NEG_FAIL", "threads": 1, "peak_ram_gb": 4},
        ],
        "route": {"cmd": route_cmd(e, hm, False),
                  "ok": "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                  "logs": ["{RUN}/routes/{LABEL}/run.log"]},
        "collect": {"cmd": "mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/physical.json {RUN}/record/"},
    }
    if e.get("ta15") or e.get("hing") or e.get("sdcx"):
        st["calibrate"] = {"enabled": False, "reason": "multi-clock block (second clock / virtual AON clock defined in its own SDC): "
                           "no single core_clk insertion to calibrate; block-internal closure at the generic IO budget first"}
    else:
        st["calibrate"] = {"cmd": route_cmd(e, hm, True), "base": "{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base",
                           "clock": "core_clk", "threads": e["thr"], "peak_ram_gb": e["ram"]}
    if e.get("hing"):
        post = ["physical/rom_host_ingest/sdc/hing_clocks_div2.sdc"]
    else:
        post = ([e["sdcx"]] if e.get("sdcx") else []) + ["physical/hbm_accel_die_views/common/signoff_unc60.sdc",
                                                         "physical/hbm_accel_die_views/common/vclk_corner_true.sdc"]
        if e["lb"]:
            post.append("physical/common_flow/link_budget_consistent.sdc")
    s = {
        "name": name, "block": e["top"], "element": e["el"], "owner": "Claude:strip-protect",
        "purpose": f"strip-protect 2026-10-09 ('-cl' line). {e['note']} Variant: TC route / option B (TT setup, FF hold, DRC 0), mm hold "
                   f"HM {int(hm * 1000)} ps. Exact bench + mutant: physical/strip_protect/bench.py {e['key']} (lock-step vs the original "
                   "+ the committed functional golden; the mutant must FAIL).",
        "hosts": HOSTS, "threads": e["thr"], "peak_ram_gb": e["ram"],
        "source": {"branch": BRANCH, "commit": commit},
        "stages": st,
        "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                    "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json", "post_sdc": post},
        "route_hold_corners": "mm", "route_hold_margin_ns": hm, "route_corner": "TC",
        "cycles_added": 0, "notes": "cycles added: 0 (protection stripped; TA15: same 3-edge release)", "merge_target": None,
    }
    if not e.get("hing"):
        s["verdict"]["checks"] = [{"name": "ttb_routed_at_TC", "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}]
    if e.get("ta15"):
        s["source"]["paths"] = ["tools", "rtl", "physical", "Makefile", "tests"]
    return name, s


OUT.mkdir(parents=True, exist_ok=True)
for e in E:
    for hm in (0.010, 0.025):
        n, s = spec(e, hm)
        (OUT / f"{n}.json").write_text(json.dumps(s, indent=1) + "\n")
        print(n)
