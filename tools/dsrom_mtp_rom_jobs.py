#!/usr/bin/env python3
"""Closure-loop job specs of the DS-ROM MTP elements (stream mtp-rom, 2026-10-08; OWNER 21:00 PT: route MTP blocks
at once, in parallel with benches, TC + mm FF hold, current flow, HM 0-25, 2-3 safe variants; benches gate adoption).

    python3 tools/dsrom_mtp_rom_jobs.py --commits A,B,C --branch claude/mtp-rom-20261008 --out DIR

One job per (element, variant); variant v uses source commit v (the loop allows one route per (block, commit), so the
variants sit on identical-tree child commits).  Recipe = the S81-PH contract-tile flow (physical/s81_ph_views/common/
route_view.sh, contract pin plan from tools/s81_ph/s81_ph_mtp_plan.py), the TC route corner (OT_ORFS_CORNER_OVERRIDE),
mm FF hold (OT_MM_FF_SDC), the CTS fix hooks incl. link_budget_hook, a CTS-only calibrate -> make_io_vclk_margin.sh at
the measured insertion.  No budget sheet yet (stream mtp-die publishes it; the loop's budget stays off with the reason).
"""
import argparse
import json
from pathlib import Path

M = "rtl/dsrom_sys/mtp"
SRCS_ALL = (f"{M}/ot_dsrom_mtp_link_pair.sv {M}/ot_dsrom_mtp_skid.sv {M}/ot_dsrom_mtp_seq.sv {M}/ot_dsrom_wfc_tok.sv "
            f"{M}/ot_dsrom_wfc_lnk.sv {M}/ot_dsrom_wfc_vmx.sv {M}/ot_dsrom_drf_fan.sv rtl/common/ot_ratio_cdc_fifo.sv")
HOOKS = ("export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl "
         "physical/common_flow/link_budget_hook.tcl'; ")
B = "python3 tools/dsrom_mtp_rom_bench.py one {case} --out {{RUN}}/bench"

ELEMS = {
    "dsfd_mtp_seq": dict(
        what="head-die MTP sequencer (ot_dsrom_mtp_seq: streamed greedy prefix accept mirroring the WFC, hold of the "
             "closing + squashed RESULTs, seed / draft-head chain, DRAFT flit then release); every port behind the "
             "WFC's registered link pair; 6-cycle registered event pipeline",
        benches=[("s0_tr_forced", "pass"), ("s0_hash_u3", "pass"), ("s0_neg_off1", "fail"), ("s0_neg_nohold", "fail")],
        threads=12, ram=32, cycles=0),
    "dsfd_wfc_tok": dict(
        what="S0 cfg / prompt producer + draft-block store (WFC binding 2: cfg_* pr_*), registered response on the "
             "WFC's fixed one-edge prompt read",
        benches=[("tok_r1", "pass"), ("s0_tr_dspark", "pass"), ("tok_neg_noepoch", "fail")],
        threads=8, ram=24, cycles=0),
    "dsfd_wfc_lnk": dict(
        what="WFC link bridge (binding 4: in_* out_*): valid/ready die link <-> the WFC's grant pair, DRAFT divert to "
             "the store, VM write credits",
        benches=[("stg_r1", "pass"), ("s0_tr_forced_w16", "pass"), ("stg_neg_nocred", "fail"),
                 ("s0_neg_draft2wfc", "fail")],
        threads=12, ram=32, cycles=6),
    "dsfd_wfc_vmx": dict(
        what="WFC VM + core-endpoint transport across the related 1.2 / 0.9 GHz boundary (bindings 1 vm_* and 3 "
             "core_*): ordered ratio-FIFO crossing of writes + start, ACK-gated start, outbound prefetch into a "
             "staging buffer before core_done",
        benches=[("stg_vmnat", "pass"), ("stg_lag1", "pass"), ("stg_neg_startearly", "fail"), ("s0_neg_doneearly", "fail")],
        threads=16, ram=48, cycles=94, two_clock=True),
    "dsfd_drf_fan": dict(
        what="draft-die 2-level link fan-out / fan-in node (N 4): routed whole messages down, round-robin whole-message "
             "merge up; replaces the 15-link star per primary rank die",
        benches=[("fan_r1", "pass"), ("fan_neg_interleave", "fail"), ("fan_neg_dest", "fail")],
        threads=16, ram=40, cycles=4),
}
# variant: (tag, HM, PD, extra run_abi3_physical args, purpose)
VARIANTS = [
    ("a", "0.000", "0.45", "", "HM 0 (acceptance FF >= 0; post-route hold ECO), PD 0.45"),
    ("b", "0.025", "0.45", "", "HM 25 (design margin), PD 0.45"),
    ("c", "0.010", "0.30", "", "HM 10, PD 0.30 (spread: wire-dominated pin-to-flop paths shorter in a sparse core)"),
]
VMX_VARIANTS = [
    ("a", "0.000", "0.45", "", "HM 0, LAG 0"),
    ("b", "0.010", "0.45", "--param LAG=1", "HM 10, LAG 1 (ratio-FIFO mem -> shadow as a max-delay path, no hold check; "
                                           "+1 write cycle each way)"),
    ("c", "0.025", "0.35", "--param LAG=1", "HM 25, LAG 1, PD 0.35"),
]


def job(elem, e, vi, commit, branch, v):
    tag, hm, pd, extra, vdesc = v
    name = f"mtp-{elem.replace('dsfd_', '')}-{tag}-{commit[:9]}-tc"
    two = e.get("two_clock", False)
    clk = ("CLK=ck SDCX=physical/s81_ph_views/mtp/ser_clock_vmx.sdc PRECTS=physical/s81_ph_views/tiles/pre_cts_ser_balance.tcl "
           "POSTCTS=physical/s81_ph_views/tiles/post_cts_ser_vclk2.tcl" if two else "CLK=ck")
    base = (f"{HOOKS}export OT_MM_FF_SDC='physical/s81_ph_views/common/signoff_unc60.sdc'; HM={hm} PD={pd} SRC={{SRC}} "
            f"OUT={{RUN}}/routes CORES={e['threads']} NEED={e['ram']} SRCS='{SRCS_ALL}' {clk} bash "
            f"physical/s81_ph_views/common/route_view.sh {{LABEL}}{{SUFFIX}} contract {elem} {M}/dsfd_mtp_tops.sv {extra}")
    cal = base.replace("{SUFFIX}", "${CL_LABEL_SUFFIX}") + " $CL_STOP_AFTER"
    route = ("export OT_ORFS_CORNER_OVERRIDE=TC; SDCM=physical/s81_ph_views/common/io_vclk_m_${CK_SS_MEAN}.sdc "
             + base.replace("{SUFFIX}", ""))
    cal = "export OT_ORFS_CORNER_OVERRIDE=TC; " + cal
    benches = [dict(name=f"{exp}_{case}", cmd=B.format(case=case), expect=exp,
                    **({"pass_regex": f"MTP_BENCH {case} PASS"} if exp == "pass" else {"fail_regex": f"MTP_BENCH {case} FAIL"}),
                    threads=2, peak_ram_gb=4, needs=["iverilog"]) for case, exp in e["benches"]]
    return dict(
        name=name, block=elem, owner="Claude:mtp-rom",
        purpose=(f"MTP-ROM 2026-10-08 (CRITICAL PATH item 0; OWNER 21:00: route MTP blocks immediately, benches gate "
                 f"adoption): {elem} = {e['what']}. Variant {tag}: {vdesc}. TC route corner, mm FF hold, H1 + CTS fix "
                 f"hooks + link budget hook, CTS-only calibrate -> IO SDC at the measured insertion; contract pin plan "
                 f"tools/s81_ph/s81_ph_mtp_plan.py; bench tools/dsrom_mtp_rom_bench.py (real closed WFC in the S0 / stage "
                 f"benches, golden V4.1 speculative traces, negative mutants)."),
        hosts=["ot-epyc1tb", "ot-epyc2", "ot-epyc3"], threads=e["threads"], peak_ram_gb=e["ram"],
        source=dict(branch=branch, commit=commit, extra_paths=["results/rtl/dshbm_dspark_rtl_20261003/traces"]),
        stages=dict(
            bench=benches,
            calibrate=dict(cmd=cal, base="{RUN}/routes/{LABEL}_cal/work/orfs/results/asap7/*/base", clock="core_clk",
                           sdc_cmd="physical/s81_ph_views/common/make_io_vclk_margin.sh $CK_SS_MEAN && ls "
                                   "physical/s81_ph_views/common/io_vclk_m_$CK_SS_MEAN.sdc",
                           threads=e["threads"], peak_ram_gb=e["ram"]),
            route=dict(cmd=route, ok="grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                       logs=["{RUN}/routes/{LABEL}/run.log"]),
            collect=dict(cmd="mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/view/* {RUN}/routes/{LABEL}/corner_sta.json "
                             "{RUN}/routes/{LABEL}/check.json {RUN}/routes/{LABEL}/args {RUN}/record/ && "
                             "(cp {CL}/calib.json {RUN}/record/calib.json || true)")),
        verdict=dict(corner_sta="{RUN}/routes/{LABEL}/corner_sta.json",
                     drc_metrics="{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                     checks=[dict(name="lef_check_MATCH",
                                  cmd="python3 -c \"import json,sys; sys.exit(json.load(open('{RUN}/routes/{LABEL}/check.json'))['verdict'] != 'MATCH')\"")],
                     post_sdc=["physical/s81_ph_views/common/signoff_unc60.sdc",
                               "physical/common_flow/link_budget_consistent.sdc"]),
        record=[{"from": "{RUN}/record", "to": f"physical/s81_ph_views/closed/{elem}_{tag}"}],
        cycles_added=e["cycles"], merge_target=None,
        budget=dict(enabled=False, reason="new MTP element: no budget sheet yet (stream mtp-die owns the MTP die/array "
                                          "budget); routed on the calibrated measured insertion (standard S81-PH flow)"),
        route_hold_corners="mm", route_hold_margin_ns=float(hm))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commits", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    commits = a.commits.split(",")
    a.out.mkdir(parents=True, exist_ok=True)
    names = []
    for elem, e in ELEMS.items():
        vs = VMX_VARIANTS if elem == "dsfd_wfc_vmx" else VARIANTS
        for vi, v in enumerate(vs):
            j = job(elem, e, vi, commits[vi], a.branch, v)
            (a.out / f"{j['name']}.json").write_text(json.dumps(j, indent=1) + "\n")
            names.append(j["name"])
    print("\n".join(names))


if __name__ == "__main__":
    main()
