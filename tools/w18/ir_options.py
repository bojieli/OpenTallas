#!/usr/bin/env python3
"""W18: price PDN options that bring the 50%-cap peak IR (rail to rail) within the 70 mV SS budget.

Levels and sources (all committed): element -- the routed pair's measured worst node (25.1 mV/rail at
1.2 GHz), scaled by the synthetic element-grid sweep's ratio for each grid variant (ir/options/element_grid_sweep.json);
switch ring -- 10 mV design at full current, scaled by the cap; cluster -- cluster PSM (ir/cluster16_1p2) scaled by the
cap; die -- mesh sweep at the 50% cap (ir/options/die_cap50_*.json), VSS taken equal to VDD.

    python3 tools/w18/ir_options.py --output results/physical_abi3/asap7/chip/v41_w18/ir/ir_options.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "results/physical_abi3/asap7/chip/v41_w18/ir"
BUDGET = 70.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    st = json.loads((D / "ir_stack.json").read_text())["scenarios"]["peak_all_busy_1p2"]
    eg = json.loads((D / "options/element_grid_sweep.json").read_text())["variants"]
    base_e = eg["base"]["worst_mv"]["VDD"]
    die = {p.stem.replace("die_cap50_", ""): json.loads(p.read_text()) for p in (D / "options").glob("die_cap50_*.json")}
    cl = st["cluster_mv"]
    elem = st["element_mv"]

    def total(cap, egv, dv):
        ef = eg[egv]["worst_mv"]["VDD"] / base_e
        e = (elem["VDD"] + elem["VSS"]) * ef
        sw = 10.0 * cap
        c = (cl["VDD"] + cl["VSS"]) * cap
        dd = 2 * die[dv]["vdd_drop_mv"]["worst"] * (cap / 0.5 if dv != "cap40" else 1.0)
        return dict(element_mv=round(e, 1), switch_mv=round(sw, 1), cluster_mv=round(c, 1), die_mv=round(dd, 1),
                    rail_to_rail_mv=round(e + sw + c + dd, 1), within_70mv=e + sw + c + dd <= BUDGET)

    cost = {
        "base": "none", "m5x2": "pair M5 power share 4.4% -> 8.9% of tracks (W10 re-harden)",
        "m6x2": "pair M6 power share 10.7% -> 21.3%", "m5m6x2": "pair M5 8.9% + M6 21.3% of tracks",
        "vdd2": "1/2 of the field's micro-bumps VDD/VSS instead of 1/3 (no signal bumps over the ROM field)",
        "w3": "die M8/M9 power share 25% -> 37.5% (trunks keep 62.5%)", "w4": "die M8/M9 power 50%",
        "p8": "die M8/M9 power 50% (denser)", "bp30": "30 um micro-bump pitch (package change)",
        "thick": "production thick top metal (~0.1x ASAP7 M8/M9 sheet resistance) -- PDK, not a design change",
        "thick_vdd2": "thick top metal + 1/2 bumps", "w3_vdd2": "37.5% M8/M9 + 1/2 bumps",
    }
    combos = {
        "baseline (cap 50%)": (0.5, "base", "base"),
        "cap 40% only": (0.4, "base", "cap40"),
        "element M5 x2": (0.5, "m5x2", "base"),
        "element M5+M6 x2": (0.5, "m5m6x2", "base"),
        "bumps 1/2 VDD/VSS": (0.5, "base", "vdd2"),
        "die M8/M9 37.5%": (0.5, "base", "w3"),
        "RECOMMENDED: element M5 x2 + bumps 1/2": (0.5, "m5x2", "vdd2"),
        "element M5+M6 x2 + bumps 1/2": (0.5, "m5m6x2", "vdd2"),
        "element M5 x2 + M8/M9 37.5% + bumps 1/2": (0.5, "m5x2", "w3_vdd2"),
        "production thick top metal, element as-is": (0.5, "base", "thick"),
        "production thick top metal + element M5 x2": (0.5, "m5x2", "thick"),
    }
    rows = {k: dict(cap=c, element_variant=e, die_variant=d, cost=dict(element=cost.get(e), die=cost.get(d)),
                    **total(c, e, d)) for k, (c, e, d) in combos.items()}
    rec = dict(schema="opentallas.v41.w18_ir_options.v1", budget_mv=BUDGET, case="50% cap peak, 1.2 GHz, rail to rail",
               options=rows,
               asap7_pessimism=dict(
                   note="ASAP7 M8/M9 are thin (0.34 ohm/sq, the same 0.08 um pitch class as M4-M7); a production 5 nm-class "
                        "stack has thick top metals (~0.02-0.04 ohm/sq) and an RDL.  At 0.1x sheet resistance the die term of the "
                        "50%-cap case falls from 16.1 to 2.2 mV per rail (32 -> 4.4 mV rail to rail).  The 'thick' rows are "
                        "that sensitivity, ASSUMED ratio, not an ASAP7 result."),
               element_hotspot=("the pair's 25 mV worst node is a local hotspot (full-adder cells of the arithmetic core at "
                                "x 200-340, y 40-70 um; only 3,589 of 339k nodes exceed 10 mV); the pair's M5/M6 grid is the "
                                "regular ORFS asap7 strategy (5.4 um per net) and a uniform load at the pair's average density "
                                "drops 2.9 mV, so the variant ratios are applied to the measured worst node"),
               sources={p.name: sha(p) for p in [D / "ir_stack.json", D / "options/element_grid_sweep.json"] +
                        sorted((D / "options").glob("die_cap50_*.json"))},
               tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    for k, v in rows.items():
        print(f"{k:45s} {v['rail_to_rail_mv']:6.1f} mV  (elem {v['element_mv']}, sw {v['switch_mv']}, cl {v['cluster_mv']}, die {v['die_mv']})  {'OK' if v['within_70mv'] else ''}")


if __name__ == "__main__":
    main()
