#!/usr/bin/env python3
"""W18: peak current, bump/package current and first-droop of a field-wide matvec on the V4.1 ROM layer die,
and the price of the lever (staggering the field) in cycles per token.

Measured inputs (source-pinned): the busy/idle pair power of W10 p5 (results/.../v41_w18/pair_w10p5_abstract.json)
and the model's per-op holding macros (results/uarch/v41_rom.json, row proposal, layer20_matvecs).  Everything
else is an explicit ASSUMPTION swept over a range: package loop inductance, die capacitance (intrinsic
non-switching + explicit decap), bump assignment.

Droop model: a lumped series L (package + bumps) feeding the die capacitance C, with the die load stepping by
dI = peak current.  An instantaneous step rings at Z0 = sqrt(L/C) (first droop dI * Z0).  A linear current ramp
over t_r reduces the first droop to dI * Z0 * |sin(pi t_r / T)| / (pi t_r / T) (T = 2 pi sqrt(LC)), bounded
above by dI * Z0 * min(1, T / (pi t_r)); the resistive part is the PSM IR drop.  A ramp of t_r costs t_r cycles
at the start of every field-wide op (the last pair group starts t_r later), which is the price in the model.

    python3 tools/w18/peak_current.py --output results/physical_abi3/asap7/chip/v41_w18/peak_current.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIR_REC = ROOT / "results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json"
UARCH = ROOT / "results/uarch/v41_rom.json"
VDD = 0.7
F_HZ = 1.087e9
DIE_MM2 = 815.0
BUMP_PITCH_UM = 40.0
POWER_BUMP_FRACTION = 1 / 3           # ASSUMED: 1/3 VDD, 1/3 VSS, 1/3 signal/other
B200_ENVELOPE = dict(power_w=1000.0, current_a=(1300.0, 1500.0),
                     basis="root's B200-class envelope (~1 kW, ~1,300-1,500 A) -- ASSUMED reference, not measured")
L_PH = (2.0, 5.0, 10.0, 20.0)         # ASSUMED package + bump loop inductance, effective
C_UF = (5.0, 15.0, 30.0)              # ASSUMED die capacitance: intrinsic non-switching + explicit decap
DROOP_BUDGET_V = 0.035                # 5% of VDD
RAMPS = (1, 17, 32, 64, 128, 256, 512)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def droop(di, L, C, tr):
    z0 = math.sqrt(L / C)
    T = 2 * math.pi * math.sqrt(L * C)
    x = math.pi * tr / T
    f = 1.0 if tr <= 0 else abs(math.sin(x)) / x
    env = 1.0 if tr <= 0 else min(1.0, T / (math.pi * tr))
    return dict(z0_mohm=round(z0 * 1e3, 4), period_ns=round(T * 1e9, 2), droop_v=round(di * z0 * f, 4),
                droop_envelope_v=round(di * z0 * env, 4))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--uarch", type=Path, default=UARCH, help="model record (default: this tree's)")
    ap.add_argument("--uarch-origin", default="", help="e.g. main b3c9e533:results/uarch/v41_rom.json")
    a = ap.parse_args(argv)
    pr = json.loads(PAIR_REC.read_text())
    busy = pr["power_w_per_pair"]["scenarios"]["busy_in0p5"]
    idle = pr["power_w_per_pair"]["ideal_icg_idle_w"]
    sw = busy - pr["power_w_per_pair"]["breakdown"]["busy_in0p5"]["total"]["leakage_w"]
    row = next(r for r in json.loads(a.uarch.read_text())["rows"] if r["design"] == "proposal")
    mv = row["layer20_matvecs"]
    field_macros = max(v["holding"] for v in mv.values())
    ops = []
    for k, v in mv.items():
        pairs = v["holding"] / 2
        i = pairs * busy / VDD
        ops.append(dict(op=k, holding_macros=v["holding"], pairs=pairs, issue_cycles=v["issue"],
                        current_a=round(i, 1), power_w=round(pairs * busy, 1)))
    peak = max(ops, key=lambda o: o["current_a"])
    field_wide = [o for o in ops if o["holding_macros"] >= 0.5 * field_macros]
    di = peak["current_a"]
    n_bumps = DIE_MM2 * 1e6 / BUMP_PITCH_UM ** 2
    vdd_bumps = n_bumps * POWER_BUMP_FRACTION
    # die capacitance cross-check from the measured switched capacitance
    c_sw_pair = sw / (VDD ** 2 * F_HZ)
    table = []
    for L in L_PH:
        for C in C_UF:
            for tr in RAMPS:
                d = droop(di, L * 1e-12, C * 1e-6, tr / F_HZ)
                table.append(dict(L_pH=L, C_uF=C, ramp_cycles=tr, **d, within_5pct=d["droop_envelope_v"] <= DROOP_BUDGET_V))
    need = {}
    for L in L_PH:
        for C in C_UF:
            ok = [t["ramp_cycles"] for t in table if t["L_pH"] == L and t["C_uF"] == C and t["within_5pct"]]
            # continuous minimum ramp for the envelope bound
            z0 = math.sqrt(L * 1e-12 / (C * 1e-6))
            T = 2 * math.pi * math.sqrt(L * 1e-12 * C * 1e-6)
            tr_min = max(0.0, di * z0 * T / (math.pi * DROOP_BUDGET_V))
            need[f"L{L}pH_C{C}uF"] = dict(min_ramp_cycles_envelope=math.ceil(tr_min * F_HZ),
                                          first_table_ramp_within=min(ok) if ok else None)
    phases = len(field_wide)
    stages = 28
    token_cycles = row["T_us"] * 1e-6 * F_HZ
    price = {n: dict(cycles_per_die_token=n * phases, cycles_per_token_all_stages=n * phases * stages,
                     token_latency_pct=round(100 * n * phases * stages / token_cycles, 2)) for n in RAMPS}
    cap = {}
    for f in (1.0, 0.75, 0.5):
        extra = sum(o["issue_cycles"] * (1 / f - 1) for o in field_wide)
        cap[f"cap_{int(f * 100)}pct"] = dict(peak_current_a=round(di * f, 1), extra_issue_cycles_per_die_token=round(extra, 1),
                                             token_latency_pct=round(100 * extra * stages / token_cycles, 2),
                                             within_b200_current=di * f <= B200_ENVELOPE["current_a"][1])
    rec = dict(
        schema="opentallas.v41.w18_peak_current.v1",
        inputs=dict(pair_record=str(PAIR_REC.relative_to(ROOT)), pair_record_sha256=sha(PAIR_REC),
                    uarch=a.uarch_origin or str(a.uarch), uarch_sha256=sha(a.uarch), pair_busy_w=busy, pair_idle_icg_w=idle,
                    vdd_v=VDD, clock_hz=F_HZ),
        per_op=ops, peak_op=peak["op"], field_wide_ops_per_layer=[o["op"] for o in field_wide],
        peak=dict(pairs=peak["pairs"], power_w=peak["power_w"], current_a=di,
                  vs_b200=dict(B200_ENVELOPE, ratio_to_upper=round(di / B200_ENVELOPE["current_a"][1], 2)),
                  basis="every holding pair busy at the measured busy power; the hub, PHYs and links add to it"),
        bumps=dict(pitch_um=BUMP_PITCH_UM, total=round(n_bumps), vdd_bumps=round(vdd_bumps),
                   peak_ma_per_vdd_bump=round(di / vdd_bumps * 1e3, 2),
                   basis="ASSUMED uniform 40 um micro-bump array, 1/3 VDD; a Cu micro-bump carries ~100 mA class"),
        die_capacitance=dict(measured_switched_c_per_pair_nf=round(c_sw_pair * 1e9, 3),
                             switched_c_field_uf=round(c_sw_pair * peak["pairs"] * 1e6, 2),
                             swept_uF=C_UF, note="intrinsic non-switching capacitance is typically several times the "
                                                 "per-cycle switched capacitance; explicit MOS decap in the 132 mm2 of "
                                                 "whitespace adds ~1-5 uF at 10-40 fF/um2 (ASSUMED)"),
        droop=dict(budget_v=DROOP_BUDGET_V, swept_L_pH=L_PH, table=table, min_ramp=need),
        lever_stagger=dict(basis="ramp the field over N cycles at every field-wide op start (the last group starts N "
                                 f"cycles late): {phases} field-wide ops per layer die x {stages} stages",
                           natural_ramp_cycles=17, natural_basis="the x broadcast already reaches clusters over 1-17 "
                           "cycles (routed probes, die route) -- a free 17-cycle ramp if each pair starts on its x "
                           "arrival", price=price),
        lever_cap=dict(basis="cap concurrent busy pairs to a fraction of the field; read-bound field-wide ops take "
                             "1/f of their issue cycles", options=cap),
        claim_boundary="lumped first-droop estimate with assumed package inductance and die capacitance; no package "
                       "model, no board/VRM, no adaptive clocking",
        tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(peak=rec["peak"], bumps=rec["bumps"], cap=rec["die_capacitance"], need=need, price=price,
                          caps=cap), indent=1))


if __name__ == "__main__":
    main()
