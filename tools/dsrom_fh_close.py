#!/usr/bin/env python3
"""DS-ROM L1 fused draft head: 1.2 GHz SS / FF closure record (ot_hdc_v41_fh_ctx route + bench exactness).

    python3 tools/dsrom_fh_close.py record --routes R1 [R2 ...] --screens S1 [S2 ...] --bench B0 B7 \
        --out results/rtl/dsrom_fh_close_20261004

  --routes   run_abi3_physical run dirs, each with physical.json and sta.json (per-corner OpenSTA on the routed
             6_final.odb + spef: tools/qwen_async_seq_incontext_physical.py sta)
  --screens  tools/dsrom_reindex_screen.py work dirs (screen.json; pre-layout, not sign-off)
  --bench    tools/dsrom_fused_draft_head.py run dirs per fused-add latency (alat<N>/<slice>/result.json)

The composition is the fused-head record's: l1_chain_ratio = 1 + 32/4096 + fused ME tail / (12.37 us x 1.2 GHz),
recomposed through tools/dsrom_dspark_l1l2_compose.py, and the 1M token (tools/dsrom_1m_measure.py compose:
MTP = tau / (verify + draft + seed_commit)) on the committed composition's verify times.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FH_REC = ROOT / "results/rtl/dsrom_fused_draft_head_20261004/record.json"
M1 = ROOT / "results/rtl/dsrom_reindex_candidates_20261004/composition.json"
SOURCES = ["rtl/hdc/v41/dspark_fused_head/ot_hdc_v41_matvec.sv", "rtl/hdc/v41/dspark_fused_head/ot_hdc_v41_fh_ctx.sv",
           "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv",
           "tools/dsrom_fused_draft_head.py", "tools/dsrom_fh_close.py"]
FULL_DIM, MARKOV_IN, FULL_HEAD_CYC = 4096, 32, 12.37 * 1200


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def route(d):
    d = Path(d)
    ph = json.loads((d / "physical.json").read_text())
    st = json.loads((d / "sta.json").read_text())
    g, pr = ph["design"], ph.get("place_and_route", {})
    ss, ff = st["corners"]["ss"], st["corners"]["ff"]
    return dict(params={k: v for k, v in (ph.get("runner", {}).get("params") or {}).items()} or None,
                core_utilization_percent=pr.get("core_utilization_percent"), cells=g.get("cells"),
                std_cell_area_um2=g.get("area_um2"), core_area_um2=g.get("core_area_um2"), drc=g.get("drc"),
                antenna=g.get("antenna"), flow_completed=ph.get("flow_completed"), flow_closed=g.get("closed"),
                flow_setup_wns_ns=g.get("setup_wns_ns"), flow_hold_wns_ns=g.get("hold_wns_ns"),
                ss_setup_wns_ns=ss.get("setup_wns_ns"), ss_setup_tns_ns=ss.get("setup_tns_ns"),
                ss_failing_setup_endpoints=ss.get("failing_setup_endpoints"),
                ss_worst_setup_path=ss.get("worst_setup_path"),
                ff_hold_wns_ns=ff.get("hold_wns_ns"), ff_failing_hold_endpoints=ff.get("failing_hold_endpoints"),
                ff_worst_hold_path=ff.get("worst_hold_path"), ss_hold_wns_ns=ss.get("hold_wns_ns"),
                ff_setup_wns_ns=ff.get("setup_wns_ns"),
                signoff=dict(ss_setup_met=st["signoff"]["ss_setup_met"], ff_hold_met=st["signoff"]["ff_hold_met"]),
                sta_basis=st.get("basis"), artifacts_sha256=st.get("artifacts_sha256"))


def bench(d):
    d = Path(d)
    out = {}
    for r in sorted(d.glob("*/result.json")):
        j = json.loads(r.read_text())
        s = j["slices"][0]
        out[r.parent.name] = dict(pass_=j["all_pass"], defines=j["defines"], cycles=s.get("cycles"),
                                  busy_me=s.get("busy_me"), tokx=s.get("tokx"), tokx_bad=s.get("tokx_bad"),
                                  stok_bad=s.get("stok_bad"), vm_mismatch=s.get("vm_mismatch"),
                                  kv_mismatch=s.get("kv_mismatch"), fault=s.get("fault"),
                                  drafts_equal_golden=j["manifest"].get("drafts_equal_golden"),
                                  values_equal_golden=j["manifest"].get("values_equal_golden"))
    return out


def cmd_record(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fh = json.loads(FH_REC.read_text())
    routes = {Path(r).name: route(r) for r in a.routes}
    screens = {}
    for s in a.screens:
        j = json.loads((Path(s) / "screen.json").read_text())
        screens[Path(s).name] = {k: j[k] for k in ("params", "ss_setup_wns_ps", "ff_hold_wns_ps", "cell_area_um2",
                                                   "worst_start", "worst_end", "worst_slack_by_stage_ps")}
    benches = {Path(b).name: bench(b) for b in a.bench}
    old = fh["measured_reduced"]
    sel = benches[a.selected_bench]
    fused = [v for k, v in sel.items() if k.startswith("fused-")]
    asb = [v for k, v in sel.items() if k.startswith("as_built-")]
    f_cyc, f_me = fused[0]["cycles"], fused[0]["busy_me"]
    a_me = 61600                                  # as-built core, as-built program (fused-head record runs)
    me_tail = (f_me - a_me) / 5
    r_full = 1 + MARKOV_IN / FULL_DIM + me_tail / FULL_HEAD_CYC
    comp = out / "l1_compose.json"
    subprocess.run([sys.executable, str(ROOT / "tools/dsrom_dspark_l1l2_compose.py"), "--out", str(comp),
                    "--l1-chain-ratio", f"{r_full:.6f}"], check=True, capture_output=True)
    l1 = json.loads(comp.read_text())["result"]["reference"]["l1"]
    l1_old = fh["full_shape"]["compose"]["result"]["reference"]["l1"]
    m1 = json.loads(M1.read_text())
    d = m1["constants"]["draft"]
    fused_us = round(d["fused_us"] * r_full / fh["full_shape"]["l1_chain_ratio"], 2)
    mtp = {k: dict(verify_us=v["verify_us"], before=v["MTP_tok_s"]["fused_us"],
                   closed=round(d["tau"] * 1e6 / (v["verify_us"] + fused_us + d["seed_commit_us"]), 1))
           for k, v in m1["variants"].items()}
    sel_route = routes[a.selected_route]
    closed = sel_route["signoff"]["ss_setup_met"] and sel_route["signoff"]["ff_hold_met"]
    exact = all(v["pass_"] for b in benches.values() for v in b.values()) and all(
        v["drafts_equal_golden"] and v["values_equal_golden"] for b in benches.values()
        for k, v in b.items() if k.startswith("fused-"))
    rec = dict(
        schema="opentallas.dsrom-fh-close.v1",
        block="L1 fused DSpark draft head: ot_hdc_v41_fh_add (64 FP32 adds per copy, addend address, result hold) "
              "and the selects it adds to ot_hdc_v41_matvec (rtl/hdc/v41/dspark_fused_head)",
        target=dict(clock_ghz=1.2, period_ns=0.833, ss_setup_uncertainty_ps=60, ff_hold_uncertainty_ps=25,
                    flow="ORFS asap7, CORNER WC (SS) primary, hold corners WC+BC, ADDER_MAP_FILE off, io delay 0.2"),
        context=("ot_hdc_v41_fh_ctx: every register-to-register path the fused head adds, bounded by the engine's own "
                 "registers (early tag, valid lines, split-tree result word, result-port stage, argmax index); the "
                 "addend read data is a port (SRAM, I/O budget). The as-built engine's own lane-mask/address/argmax "
                 "logic is excluded: it is not part of the fused head (screen A0 shows it is not a 1.2 GHz SS engine "
                 "either: the reduced-vehicle ot_hdc_v41_matvec)"),
        changes=["fused adds: ot_hdc_fp32_add_lat #(7) (keep-prefix, bit-identical to the as-built five-stage pipe; "
                 "LAT 5 fails in context, screen A5 -283 ps in the adder) -- +2 cycles per fused op (DF 7 -> 9)",
                 "zero cycles: the tag line ends in a register so the fused selects (r_tag, r_v) are made a cycle "
                 "ahead and registered; iw_go registered from drained_nx (proved equal: no op is accepted while a "
                 "fused op pends, and tv[LV] is tv[LV-1] a cycle earlier); the addend address in two stages from "
                 "the early tag with keep-prefix adders (3:2 + Kogge-Stone)"],
        screens=screens, routes=routes, selected_route=a.selected_route,
        exactness=dict(benches=benches, all_exact=exact,
                       basis="tools/dsrom_fused_draft_head.py run: reduced V4.1 core chain slice, RTL state and the "
                             "golden Model.draft drafts/argmax values; as_built-* = the as-built program on the "
                             "successor core (default-off: cycle-identical to the as-built core, 85,708)"),
        cycles=dict(fused_chain5_before=old["fused_chain5_cycles"], fused_chain5_closed=f_cyc,
                    added_cycles_per_fused_op=(f_cyc - old["fused_chain5_cycles"]) / 5,
                    fused_me_tail_per_step_before=old["fused_me_tail_cycles_per_step"], fused_me_tail_per_step=me_tail,
                    as_built_program_on_successor=sorted({v["cycles"] for v in asb})),
        composition=dict(l1_chain_ratio_before=fh["full_shape"]["l1_chain_ratio"], l1_chain_ratio=round(r_full, 6),
                         l1_draft_us_before=l1_old["draft_us"], l1_draft_us=l1["draft_us"],
                         l1_mtp_1M_tok_s_before=l1_old["ctx"]["1048576"]["occupancy"]["mtp_tok_s"],
                         l1_mtp_1M_tok_s=l1["ctx"]["1048576"]["occupancy"]["mtp_tok_s"],
                         dsrom_1m_measure_fused_us_before=d["fused_us"], dsrom_1m_measure_fused_us=fused_us,
                         dsrom_1m_measure_mtp=mtp,
                         basis="tools/dsrom_dspark_l1l2_compose.py at the measured ratio; tools/dsrom_1m_measure.py "
                               "compose formula on the committed 1M composition's verify times"),
        verdict=("CLOSED" if closed and exact else "NOT_CLOSED"),
        source_sha256={p: sha(ROOT / p) for p in SOURCES},
        source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                     text=True).stdout.strip())
    (out / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("verdict", "cycles", "composition")}, indent=1)[:3000])
    print(json.dumps({k: {x: v[x] for x in ("ss_setup_wns_ns", "ff_hold_wns_ns", "cells", "std_cell_area_um2", "drc")}
                      for k, v in routes.items()}, indent=1))
    return 0 if rec["verdict"] == "CLOSED" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--routes", nargs="+", required=True)
    r.add_argument("--selected-route", required=True)
    r.add_argument("--screens", nargs="*", default=[])
    r.add_argument("--bench", nargs="+", required=True)
    r.add_argument("--selected-bench", required=True)
    r.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return {"record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
