#!/usr/bin/env python3
"""TOKEN-XDIE-QTP8: fold the per-case bench records (results/rtl/xdie_qtp8_1018/<case>/record.json) into the lane record
results/rtl/xdie_qtp8_1018/record.json with E_meas / O_meas for the TOKEN-XDIE composition (lanes/TOKEN-XDIE.md s3).

E_meas(x) = first output word landing at the consumer pin - last producer word issued into the collective (core cycles,
            1.2 GHz), read from the compiled program the RTL met EXACTLY (every word is checked at its compiled cycle).
span(x)   = first producer word -> last output word (the collective's whole occupancy incl. the 256-word stream).
O_meas    = cycles a compiled compute schedule overlaps x: NO compiled Qwen compute-die schedule that issues the TP8
            collective exists yet (TOKEN-PASS-QWEN has none; the bench issuer is the collective's own stage program),
            so O_meas = 0 (not assumed), E_exposed = E_meas.
Token terms (Qwen3-8B, 36 layers, TP8 o_proj + down_proj all-reduce per layer, LM-head argmax gather):
  T_xdie_tp8 = 36 * 2 * E_exposed(AR256) + E_exposed(argmax)   and the span form 36 * 2 * span(AR256) + span(argmax)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import os
OUT = ROOT / os.environ.get("QTP8_OUT", "results/rtl/xdie_qtp8_1018")
LAYERS = 36


def case_terms(c):
    p = c["program"]
    t = {}
    for m in p:
        gc = 8 if m["mode"] else 1
        m["last_in"] = m["first_slot"] + gc * (m["words"] - 1)
    t["span"] = c["compiled_span_cycles"]
    t["E_meas_first"] = p[0]["first_out"] - p[0]["last_in"]
    t["E_meas_last"] = p[-1]["first_out"] - p[-1]["last_in"]
    t["latency_first_in_to_first_out"] = p[0]["first_out"] - p[0]["first_slot"]
    return t


def main():
    runs, verdicts = {}, {}
    for d in sorted(OUT.glob("*/record.json")):
        r = json.loads(d.read_text())
        name = d.parent.name
        cases = {c["name"]: dict(passed=c["passed"], **(c["result"] or {}), **case_terms(c)) for c in r["cases"]}
        allpass = all(c["passed"] for c in r["cases"])
        ok = (not any(c["passed"] for c in r["cases"])) if r["expect_fail"] else allpass
        runs[name] = dict(expect_fail=r["expect_fail"], ok=ok, lats=r["lats"], latu=r["latu"], mutant=r["mutant"],
                          die_lanes=r.get("die_lanes"), valid_skew_port2=r.get("valid_skew_port2"), tok_reg=r.get("tok_reg"),
                          calendar_lane_cycles=r.get("calendar_lane_cycles"), sequencer_face=r.get("sequencer_face"),
                          fdi_phase=r.get("FDI_phase_ticks"), verilator=r.get("verilator_version"), cases=cases,
                          source_sha256=r["source_sha256"])
        verdicts[name] = "OK" if ok else "UNEXPECTED"
    sweep = sorted((v["lats"], k) for k, v in runs.items() if k.startswith("lx_ls"))
    passing = [ls for ls, k in sweep if runs[k]["ok"]]
    ls_min = min(passing) if passing else None
    d50_sweep = {runs[k]["lats"]: runs[k]["ok"] for k in runs if k.startswith("d50_rec_ls")}
    rec_case = "d50_rec_ls376" if runs.get("d50_rec_ls376", {}).get("ok") else None
    meas = None
    if rec_case:
        c = runs[rec_case]["cases"]
        ar, ar2, am, lay = c["qwen_ar_256w"], c["qwen_layer_2x256w"], c["qwen_argmax_1w"], c["qwen_layer_2x256w_argmax"]
        e_ar, e_am = ar["E_meas_first"], am["E_meas_first"]
        meas = dict(
            configuration=rec_case + ": dv2f14bf die lanes (ET/ER 2/0/5, calendar LX 7/0/7), hardened face TOK_REG 1, "
                          "production calendar LU 53 / LS 376, 50%-duty clocks, FDI phase 0 (clock contract)",
            LS_min_pulse_harness=ls_min, LS_sweep_pulse_harness={ls: runs[k]["ok"] for ls, k in sweep},
            LS_d50=d50_sweep,
            AR256=dict(span=ar["span"], E_meas=e_ar, O_meas=0, E_exposed=e_ar, first_in_to_first_out=ar["latency_first_in_to_first_out"]),
            AR256x2_back_to_back=dict(span=ar2["span"]),
            argmax_gather_1w=dict(span=am["span"], E_meas=e_am, O_meas=0, E_exposed=e_am),
            layer_2xAR_plus_argmax=dict(span=lay["span"]),
            token_E_exposed_cycles=LAYERS * 2 * e_ar + e_am,
            token_span_cycles=LAYERS * 2 * ar["span"] + am["span"],
            price_cycles=dict(AR1=1121, AR2=979, source="results/arch/qwen_tp8_1012/SPEC.md s3/s6 (span form)"),
            fdi_phases={k: runs[k]["ok"] for k in sorted(runs) if "phase" in k},
            grade="measured-current-RTL (dv2f14-lineage collective + IO masters, Verilator 5.050); die lanes = fixed E-cycle "
                  "delays from the dv2f14bf GEN (qfd_fwd_lane RTL qualified separately, tools/qwen_split/bench_fwd_lane.sh); "
                  "PHY modelled (SerDes 339, UCIe 4 FDI)",
        )
    base = runs.get("base_ls376", {}).get("cases", {})
    rec = dict(schema="opentallas.token_xdie.qwen_tp8.v1", lane="TOKEN-XDIE-QTP8", date="2026-10-18",
               vehicle="tools/qwen_coll_tp8_static_links_bench.py (8 dies, rtl/test/tb_coll_tp8_static_links.sv, "
                       "+define OT_TP8S_PRODUCTION_WRAPPER = qfd_collective_static_io_production per die)",
               topology="4 packages x 2 dies; UCIe die pair per package (one shared 1043-b six_five link); SerDes full mesh "
                        "between packages (3 ports/die, port j of package P -> package (P+1+j)%4); no switch",
               modelled="PHY frame pipes only: UCIe 4 FDI cycles (+20 core-edge calendar), SerDes 339 core cycles (board PHY+FEC+cable, "
                        "results/arch/qwen_tp8_1012/SPEC.md); die lanes as fixed delays",
               golden="tools/hdc_golden: package sum lo+hi, cross ((p0+p1)+p2)+p3 in package-rank order; gather word 8i+4d+r",
               checks="every output word at EXACTLY its compiled cycle with the exact value; every issuer command at its compiled "
                      "cycle; zero faults in collective / issuer / 10 CDC channels / 5 codecs; no credit/ready on die (flow "
                      "control only at the PHY boundary: the codec CRC/abort)",
               baseline_ls376_no_lanes={k: dict(passed=v["passed"], span=v["span"], E_meas=v["E_meas_first"]) for k, v in base.items()},
               measured=meas, verdicts=verdicts, runs=runs,
               notes=["LS below the minimum (lx_ls370..373, d50_rec_ls373) FAIL by design: tight witnesses that LS 374 is the minimum with the lanes absorbed (production LS 376 keeps 2 cycles slack)",
                      "FDI phase != 0: pulse harness fails every phase 1..5 (the r11..r15 gearbox negedge registers are not clocked by 1-tick pulses); "
                      "50%-duty harness passes phases 0/4/5 and FAILS 1/2/3 on the BASELINE too (no lanes, TOK_REG 0) -> property of the current "
                      "qfd_ucie_six_five (r15), not of this lane's edits; the 10-15 r10 gearbox passed 0..5. The clock contract is phase 0 "
                      "(related group, Q-DIE11-COLL); phase robustness is owed by the gearbox owner",
                      "as-built dv2f14 lanes without LX FAIL (d50_asbuilt_ls376, asbuilt_*): every die faults (frames land 7 cycles after the compiled slot on S0<->S2)",
                      "serdes2_txv E 6 vs serdes2_tx E 5 FAILS (lx_skew, d50_rec_skew): the die GEN must give a bus group one E/K"],
               O_meas_source="none: no compiled Qwen compute schedule issues the TP8 collective yet; O_meas = 0, not assumed")
    (OUT / "record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdicts=verdicts, measured=meas), indent=1))
    return 0 if meas and all(v == "OK" for k, v in verdicts.items() if k.startswith("d50_") and "phase" not in k and "ls37" not in k) else 1


if __name__ == "__main__":
    sys.exit(main())
