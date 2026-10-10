#!/usr/bin/env python3
"""Closure-loop route specs of the mtp-rollback blocks (review MR-1/MR-6/MR-7 APPROVED 2026-10-09), 2 variants each.
Standalone element routes on the current HBM-die element flow (physical/hbm_mtp/route_mtp.sh: TC route, IO vs vclk at
the calibrated insertion, sign-off 833.333 / 60 ps, rule-H1 FF hold).  The bench gate is tools/mtp_rollback_bench.py
(record results/rtl/mtp_rollback_20261008/record.json).
    python3 physical/mtp_rollback/jobs/gen.py COMMIT [--drop DIR]"""
import json, sys, shutil
from pathlib import Path
commit = sys.argv[1]
short = commit[:9]
BLOCKS = [
 ("dskvwb_spec", "ot_hbm_accel_dskv_wb_spec", "rtl/hbm_accel/service/ot_hbm_accel_dskv_wb_spec.sv", "--param ENABLE=1 --param STACK=0",
  "MR-7 + MR-6: per-token KV / index-key writer, window slot pos mod 256, shadow lock (HBM accelerator die, every stack)", 40),
 ("dswin_rd", "ot_hbm_accel_dswin_rd", "rtl/hbm_accel/service/ot_hbm_accel_dswin_rd.sv", "",
  "MR-7: window / DSpark-window read address stream, slot pos mod 256 (HBM accelerator die)", 16),
 ("hist_ring", "ot_mtp_hist_ring", "rtl/mtp/rollback/ot_mtp_hist_ring.sv", "",
  "MR-3: Engram token-history ring (TR 16, NG 4), rollback by commit pointer (with the Engram hash unit)", 16),
 ("commit", "ot_mtp_commit", "rtl/mtp/rollback/ot_mtp_commit.sv", "",
  "commit / rollback sequencer: n = q+2+a, q_next, squash range, epoch (head-die sequencer side)", 16),
]
VARS = {"a": dict(UTIL=40, PD=0.55, HM=0.025), "b": dict(UTIL=30, PD=0.45, HM=0.010)}
out = Path(__file__).parent
names = []
for tag, top, src, params, why, ram in BLOCKS:
    for v, k in VARS.items():
        name = f"mtprb-{tag}-{v}-{short}-tc"
        env = f"UTIL={k['UTIL']} PD={k['PD']} HM={k['HM']}"
        base = (f"export OT_TTB_CORNER_MARK={{CL}}/ttb_corner.txt && python3 tools/closure_loop/tt_overlay.py {{SRC}} && "
                f"export OT_ORFS_CORNER_OVERRIDE=TC; export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl "
                f"physical/common_flow/clk_net_protect.tcl'; OUT={{RUN}}/routes CORES=16 {env} LB=0 bash physical/hbm_mtp/route_mtp.sh ")
        args = f"{top} --source {src} {params}".strip()
        spec = {
         "name": name, "block": top, "owner": "Claude:mtp-rollback",
         "purpose": f"mtp-rollback 2026-10-09 ({why}). Variant {v}: {env}. Bench gate: tools/mtp_rollback_bench.py campaign "
                    "(28+ runs, good PASS / mutants FAIL).",
         "hosts": ["ot-epyc1tb", "ot-epyc2", "ot-epyc3"], "threads": 16, "peak_ram_gb": ram,
         "source": {"branch": "claude/mtp-rollback-20261008", "commit": commit},
         "stages": {
          "bench": [],
          "calibrate": {"cmd": base + "{LABEL}${CL_LABEL_SUFFIX} " + args + " $CL_STOP_AFTER",
                        "base": "{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base", "clock": "core_clk",
                        "threads": 16, "peak_ram_gb": ram},
          "route": {"cmd": base + "{LABEL} " + args,
                    "ok": "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                    "logs": ["{RUN}/routes/{LABEL}/run.log"]},
          "collect": {"cmd": "mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/args "
                             "{RUN}/routes/{LABEL}/physical.json {RUN}/record/"}},
         "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                     "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                     "checks": [{"name": "ttb_routed_at_TC", "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"}],
                     "post_sdc": ["physical/hbm_accel_die_views/common/signoff_unc60.sdc",
                                  "physical/hbm_accel_die_views/common/vclk_corner_true.sdc"]},
         "record": [{"from": "{RUN}/record", "to": f"results/rtl/mtp_rollback_20261008/routes/{name}"}],
         "merge_target": None, "route_hold_corners": "mm", "route_hold_margin_ns": k["HM"], "route_corner": "TC",
         "cycles_added": 0,
         "no_bench_reason": "bench gate run outside the loop: tools/mtp_rollback_bench.py campaign (record results/rtl/mtp_rollback_20261008/record.json)"}
        (out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n")
        names.append(name)
if "--drop" in sys.argv:
    d = Path(sys.argv[sys.argv.index("--drop") + 1])
    for n in names:
        shutil.copy(out / f"{n}.json", d / f"{n}.json")
print("\n".join(names))
