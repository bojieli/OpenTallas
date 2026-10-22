#!/usr/bin/env python3
"""XDIE-QTP8-2 (10-19): fold the f15r_* TP8 co-sim cases (newest Qwen compute GEN dv2f15r: real forwarded SerDes lanes +
the GEN's compiled collective calendar LS 378) into results/rtl/xdie_qtp8_2_1019/record.json with a token_compose block
(results/arch/token_path_1018/README.md) for tools/token_compose_xdie.py.

E_meas(AR) = first output word landing at the consumer - last producer word issued (tools/xdie_qtp8/record.py); every word is
checked at its compiled cycle, so E is the compiled = measured exchange.  Split per grade in proportion to the exchange's
latency path (first in -> first out): the modelled PHY frame pipes (UCIe PU 20 core edges + SerDes PS 339, the calendar's
own fields) vs the rest (on-die collective, linkcal, CDC, codecs, gearbox, real forwarded lanes = current dv2f15r RTL).
O = 0: each TP8 all-reduce (o_proj, down_proj) feeds the residual add the next op needs (serial token path); the compiled
collective calendar (lane_groups.collective_calendar, GEN coll_lane_latency.json) issues no compute inside it."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/rtl/xdie_qtp8_2_1019"
RUNS = OUT / "runs"
GEN = OUT / "gen_dv2f15r/coll_lane_latency.json"
LAYERS = 36
sys.path.insert(0, str(Path(__file__).resolve().parent))
from record import case_terms  # noqa: E402


def main():
    runs, verdicts = {}, {}
    for d in sorted(RUNS.glob("f15r_*/record.json")):
        r = json.loads(d.read_text())
        cases = {c["name"]: dict(passed=c["passed"], **(c["result"] or {}), **case_terms(c)) for c in r["cases"]}
        allpass = bool(r["cases"]) and all(c["passed"] for c in r["cases"])
        ok = (not any(c["passed"] for c in r["cases"])) if r["expect_fail"] else allpass
        runs[d.parent.name] = dict(expect_fail=r["expect_fail"], ok=ok, lats=r["lats"], latu=r["latu"], mutant=r["mutant"],
                                   calendar_lane_cycles=r.get("calendar_lane_cycles"), real_lanes=r.get("real_lanes"),
                                   real_lanes_source=r.get("real_lanes_source"), lane_meas=r.get("lane_meas"),
                                   sequencer_face=r.get("sequencer_face"), verilator=r.get("verilator_version"),
                                   cases=cases, source_sha256=r["source_sha256"])
        verdicts[d.parent.name] = "OK" if ok else "UNEXPECTED"
    cal = json.loads(GEN.read_text())["calendar"]
    phy = cal["PU"] + cal["PS"]
    meas, tc = None, None
    su = runs.get("f15r_cal")
    if su and su["ok"]:
        c = su["cases"]
        ar, ar2, am, lay = c["qwen_ar_256w"], c["qwen_layer_2x256w"], c["qwen_argmax_1w"], c["qwen_layer_2x256w_argmax"]
        e, lat = ar["E_meas_first"], ar["latency_first_in_to_first_out"]
        e_phy = round(e * phy / lat, 1)
        e_rtl = round(e - e_phy, 1)
        meas = dict(
            configuration=f"f15r_cal: dv2f15r GEN lanes (real qfd_fwd_lane, LX {cal['ports']['0']['LX']}/{cal['ports']['1']['LX']}/"
                          f"{cal['ports']['2']['LX']}), compiled calendar LS {cal['LS']} / LU {cal['LU']}, hardened face TOK_REG 1, 50%-duty clocks",
            AR256=dict(span=ar["span"], E_meas=e, O_meas=0, E_exposed=e, first_in_to_first_out=lat,
                       E_split=dict(measured_current_RTL=e_rtl, modelled_PHY=e_phy, phy_path_cycles=phy,
                                    rule="E shared in proportion to the first-in -> first-out path: PHY = PU + PS")),
            AR256x2_back_to_back=dict(span=ar2["span"]),
            argmax_gather_1w=dict(span=am["span"], E_meas=am["E_meas_first"], O_meas=0, E_exposed=am["E_meas_first"]),
            layer_2xAR_plus_argmax=dict(span=lay["span"]),
            token_E_exposed_cycles=LAYERS * 2 * e + am["E_meas_first"],
            token_tp_allreduce_cycles=LAYERS * 2 * e,
            token_span_cycles=LAYERS * 2 * ar["span"] + am["span"],
            pilot_ls376_fixed_lanes=dict(AR256_E=284, argmax_E=436, token_E_exposed=20884, record="results/rtl/xdie_qtp8_1018/record.json"),
        )
        mu = runs.get("f15r_mu")
        if mu:
            mc = mu["cases"]
            w, ref = mc.get("mu_window", {}), mc.get("mu_window_ref_user0", {})
            meas["multi_user_4"] = dict(ok=mu["ok"], words_out=w.get("words_out"), span=w.get("span"), E_meas=w.get("E_meas_first"),
                                        latency_user_alone_span=ref.get("span"), latency_user_alone_E=ref.get("E_meas_first"),
                                        calendar="results/rtl/mu_qwen_1018/coll/mu_cal.json (MU-QWEN mu_calendar, LS 378)")
        o_src = (f"compiled collective calendar of GEN dv2f15r (tools/qwen_split/lane_groups.collective_calendar, LS {cal['LS']}, "
                 "results/rtl/xdie_qtp8_2_1019/gen_dv2f15r/coll_lane_latency.json): each TP8 all-reduce (o_proj, down_proj) feeds the "
                 "residual add the next op needs and the calendar issues no compute-die op inside it (serial token path) -> O 0")
        parts = []
        for k in ("#1 o_proj", "#2 down_proj"):
            parts += [dict(grade="measured-current-RTL", E=e_rtl, note=f"TP8 all-reduce {k}: dv2f15r collective/IO masters + real forwarded "
                           "SerDes lanes at the compiled LS, 8 dies, exact at compiled cycles (Verilator 5.050)"),
                      dict(grade="modelled-PHY", E=e_phy, note=f"TP8 all-reduce {k}: PHY frame pipes UCIe {cal['PU']} + SerDes {cal['PS']} "
                           "core cycles (results/arch/qwen_tp8_1012/SPEC.md), E share by path")]
        tc = dict(note="Qwen ROM TP8 array all-reduce term from the 8-die co-sim on the newest compute GEN dv2f15r (XDIE-QTP8-2)",
                  terms=[dict(design="qwen_rom", workload="ar", slot=s, E=parts, O=0.0, O_source=o_src,
                              pointer="measured.AR256.E_split") for s in ("L0.xdie.tp_allreduce", "Lc.xdie.tp_allreduce")])
    rec = dict(schema="opentallas.token_xdie.qwen_tp8.v2", lane="XDIE-QTP8-2", date="2026-10-19",
               gen=dict(name="dv2f15r", src="5a789562d (origin/claude/die-qwen-lead-1019)",
                        coll_lane_latency="results/rtl/xdie_qtp8_2_1019/gen_dv2f15r/coll_lane_latency.json",
                        copied_from="ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/dv2f15r/out/case/coll_lane_latency.json",
                        sha256="2a981319f012c8d7cecd6799900d9f9aef0bac3c932c731157689e2f8f64fc44",
                        bench_rtl="collective/IO/lane RTL the bench reads byte-identical to 5a789562d (tb adds ISSUE_DEPTH only)"),
               vehicle="tools/qwen_coll_tp8_static_links_bench.py --production --real-lanes (8 dies, 4 packages x 2, UCIe pair + SerDes full mesh)",
               modelled="PHY frame pipes only (UCIe 20 core edges, SerDes 339)",
               measured=meas, verdicts=verdicts, runs=runs)
    if tc:
        rec["token_compose"] = tc
    (OUT / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    bad = [k for k, v in verdicts.items() if v != "OK"]
    print("verdicts", verdicts)
    print("measured", json.dumps(meas, indent=1) if meas else None)
    return 1 if (bad or not meas) else 0


if __name__ == "__main__":
    sys.exit(main())
