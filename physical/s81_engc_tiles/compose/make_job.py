#!/usr/bin/env python3
"""dsfd_engram_c composition job spec (el1013-s81-engram 2026-10-13; replaces job_template.json).

    make_job.py --commit FULL_SHA --vclk PS --vclk-ff PS [--name N] > spec.json

The route command is ONE string: the closure loop runs it, and gate/cts_stop.sh runs the same string with
--pnr-stop-after cts for the CTS-stop gate (no second copy of the recipe)."""
import argparse, json

C = "physical/s81_engc_tiles/compose"
MACROS = ("dsfd_engram_lkp=physical/s81_ph_views/closed/dsfd_engram_lkp dsfd_engram_sink=physical/s81_ph_views/closed/dsfd_engram_sink "
          "ot_engc_t_win=physical/s81_engc_tiles/views/ot_engc_t_win ot_engc_t_io=physical/s81_engc_tiles/views/ot_engc_t_io "
          "ot_engc_t_ws=physical/s81_engc_tiles/views/ot_engc_t_ws ot_engc_t_pbb=physical/s81_engc_tiles/views/ot_engc_t_pbb "
          "ot_engc_t_pbc=physical/s81_engc_tiles/views/ot_engc_t_pbc")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True); ap.add_argument("--vclk", type=int, required=True)
    ap.add_argument("--vclk-ff", type=int, required=True); ap.add_argument("--name")
    ap.add_argument("--branch", default="claude/s81-engram-1013")
    a = ap.parse_args()
    name = a.name or f"el1013-engc-compose-{a.commit[:9]}-tc"
    K = f"{C}/ck_entry_keep.tcl"
    route = (
        f"export ENGC_VCLK_PS={a.vclk}; (cd physical/s81_ph_views/common && ./make_io_vclk_margin.sh $ENGC_VCLK_PS); "
        "export OT_ORFS_CORNER_OVERRIDE=TC; "
        f"export OT_CTS_FIX_HOOKS='{C}/spine_engc.tcl physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl {K}'; "
        "export OT_MM_FF_SDC='physical/s81_ph_views/common/signoff_unc60.sdc'; "
        "SDCM=physical/s81_ph_views/common/io_vclk_m_${ENGC_VCLK_PS}.sdc " f"SDCX={C}/engc_io.sdc HM=0.05 PD=0.45 SRC={{SRC}} OUT={{RUN}}/routes CORES=16 NEED=32 "
        f"SRCS='{C}/ot_engc_tiles_bb.v rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv rtl/lib/ot_hdly.sv rtl/lib/ot_reset_sync.sv' MACROS='{MACROS}' "
        f"PDN={C}/pdn_engc_t.tcl PRECTS={C}/pre_cts_engc.tcl POSTCTS={C}/post_cts_engc.tcl PREGRT={C}/pre_grt_engc.tcl "
        "CTSA='-sink_clustering_enable -repair_clock_nets -distance_between_buffers 150 -macro_clustering_size 1 -macro_clustering_max_diameter 20' CLK=ck "
        "bash physical/s81_ph_views/common/route_view.sh {LABEL}${CL_LABEL_SUFFIX} contract dsfd_engram_c rtl/dsrom_sys/engram/dsfd_engram_c.sv "
        f"--orfs-var MACRO_PLACEMENT_TCL=/src/{C}/macro_place.tcl --orfs-var DONT_BUFFER_PORTS=1 "
        "--orfs-var OT_SPINE_PORT=ck --orfs-var OT_SPINE_MACRO_LEAF=1 " f"--orfs-var ENGC_VCLK_PS={a.vclk} --orfs-var ENGC_VCLK_FF_PS={a.vclk_ff} "
        f"--step-tcl PRE_FLOORPLAN={K} --step-tcl PRE_GLOBAL_PLACE={K} --step-tcl PRE_RESIZE={K} --step-tcl PRE_DETAIL_PLACE={C}/ck_entry_place.tcl $CL_STOP_AFTER")
    mv = " ".join("--macro-view " + m.split("=")[1] for m in MACROS.split())
    spec = {
        "name": name, "block": "dsfd_engram_c", "element": "dsfd_engram_c", "owner": "Claude:el1013-s81-engram",
        "purpose": "S81 layer1e Engram cluster dsfd_engram_c, ALL-TILE composition (slot 1188 x 432): the top holds local reset synchronizers and a coherent return-status stage; "
                   "8 hardened children (closed lkp / sink leaves + T_WIN / T_IO / T_WS / T_PBB / T_PBC x2, all views child_lint clean) "
                   "clocked by a pre-placed balanced spine with a separate leaf at each child clock pin. CTS-stop gate: "
                   f"{C}/gate (leaf spread <= 80 ps TT and FF). IO against the fixed vclk {a.vclk} ps (no top register to measure).",
        "hosts": ["ot-epyc4", "ot-epyc1tb", "ot-agidock128"], "threads": 16, "peak_ram_gb": 32,
        "source": {"branch": a.branch, "commit": a.commit},
        "stages": {
            "bench": [
                {"name": "engram_c_exact_quick", "cmd": "python3 tools/s81_svceng/engram_c_gate.py --quick --out {RUN}/bench_engc",
                 "expect": "pass", "pass_regex": "^ENGRAM_C_GATE PASS", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"], "timeout_s": 10800},
                {"name": "engram_c_neg_earlydone", "cmd": "python3 tools/s81_svceng/engram_c_gate.py --quick --neg earlydone --out {RUN}/bench_engc_neg",
                 "expect": "fail", "fail_regex": "ENGRAM_C_NEG earlydone FAIL", "threads": 2, "peak_ram_gb": 6, "needs": ["verilator"], "timeout_s": 10800}],
            "calibrate": {"enabled": False, "reason": "no top-level register (all-tile): the IO reference is the fixed ENGC_VCLK_PS, chosen from the "
                                                      "CTS-stop gate's measured per-child IO slacks (" + C + "/gate)"},
            "route": {"cmd": route,
                      "ok": "grep -q '^rc=0' {RUN}/routes/{LABEL}/exit && grep -q '^corner_rc=0' {RUN}/routes/{LABEL}/exit",
                      "logs": ["{RUN}/routes/{LABEL}/run.log"], "threads": 16, "peak_ram_gb": 32},
            "collect": {"cmd": "mkdir -p {RUN}/record && cp {RUN}/routes/{LABEL}/view/* {RUN}/routes/{LABEL}/corner_sta.json {RUN}/routes/{LABEL}/check.json "
                               "{RUN}/routes/{LABEL}/args {RUN}/record/ && (python3 tools/tt_views/view_export.py --orfs-dir {RUN}/routes/{LABEL}/work/orfs "
                               f"--name dsfd_engram_c --out {{RUN}}/record --corners tt {mv} --image openroad/orfs:asap7lock "
                               "> {RUN}/record/export_tt_collect.log 2>&1 || echo TT_EXPORT_FAILED > {RUN}/record/TT_EXPORT_FAILED)"}},
        "cycles_added": 1,
        "cycles_note": "one coherent SINK ready/parity return cycle and one PB1-to-PB0 mask/address/data transit cycle; production exact bench must measure current window-to-slot-ready against unchanged 500-cycle price",
        "merge_target": "main", "route_hold_corners": "mm", "route_corner": "TC", "route_hold_margin_ns": 0.05,
        "verdict": {"corner_sta": "{RUN}/routes/{LABEL}/corner_sta.json",
                    "drc_metrics": "{RUN}/routes/{LABEL}/work/orfs/logs/asap7/*/base/5_2_route.json",
                    "checks": [{"name": "lef_check_MATCH", "cmd": "python3 -c \"import json,sys; sys.exit(json.load(open('{RUN}/routes/{LABEL}/check.json'))['verdict'] != 'MATCH')\""}],
                    "post_sdc": ["physical/s81_ph_views/common/signoff_unc60.sdc"]},
        "record": [{"from": "{RUN}/record", "to": "physical/s81_ph_views/closed/dsfd_engram_c"}],
        "structural_change": "all-tile cluster with local reset synchronizers and 8 hard clock pins; replaces the soft-tree monolith (12 failed routes: hold stalled "
                             "-206.5 ps at 16,258 sinks/root, SRAM read path -1568.6 ps). New in this submission: pre-placed clock spine with per-child insertion targets "
                             "(g13 measured leaf spread 67.4 ps TT / 64.8 ps FF after CTS, max clock-pin slew 21.7 ps, "
                             "was 400 ps with the bare top tree), children re-routed with face-pin keepout (child_lint 0 pins blocked), sliver rows "
                             "removed before the PDN, child seams that hold rows opened to >= 12 um (io +4.32 / lkp -4.32 um in y, pb0 -3.456 and sink -2.16 um in x), no port buffers, local per-child kept reset synchronizers, coherent SINK-to-WIN status pipeline (strict setup150 bidirectional deficit105.2ps), PB1-to-PB0 coherent write transit stage, data relays on ordinary functional-edge spine leaves, full local clock loads included before spine balancing, H1 hold100, no reset multicycle exceptions, fixed vclk.",
    }
    print(json.dumps(spec, indent=1))


if __name__ == "__main__":
    main()
