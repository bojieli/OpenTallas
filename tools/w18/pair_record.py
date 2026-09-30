#!/usr/bin/env python3
"""W18: record the W10 p5 element-pair abstract, its tiling pitch, its power under activity scenarios and its
own IR drop (all measured on W10's routed 6_final.odb / .spef, copied unchanged).

    python3 tools/w18/pair_record.py --w10p5 /home/ubuntu/w18work/w10p5 --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/w18"))
import die_floorplan as DF  # noqa: E402

ABS = ROOT / "results/physical_abi3/asap7/chip/abstracts/ot_v41_rom_elem_q_w10p5"
FP = ROOT / "results/physical_abi3/asap7/chip/v41_w18"
PAIRS = 7102


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def power(log: str) -> dict:
    out = {}
    for tag, body in re.findall(r"OT_POWER_BEGIN (\S+)\n(.*?)OT_POWER_END", log, re.S):
        row = {}
        for grp in ("Sequential", "Combinational", "Clock", "Macro", "Total"):
            m = re.search(rf"^{grp}\s+([-0-9.e+]+)\s+([-0-9.e+]+)\s+([-0-9.e+]+)\s+([-0-9.e+]+)", body, re.M)
            if m:
                row[grp.lower()] = dict(internal_w=float(m.group(1)), switching_w=float(m.group(2)),
                                        leakage_w=float(m.group(3)), total_w=float(m.group(4)))
        out[tag] = row
    return out


def ir(log: str) -> dict:
    out = {}
    for net in ("VDD", "VSS"):
        seg = log.split(f"OT_IR_BEGIN net={net}")[1].split("OT_IR ")[0] if f"OT_IR_BEGIN net={net}" in log else ""
        g = lambda k: float(re.search(rf"{k}\s*:\s*([-0-9.e+]+)", seg).group(1)) if re.search(k, seg) else None  # noqa
        out[net] = dict(worst_ir_drop_v=g("Worstcase IR drop"), average_ir_drop_v=g("Average IR drop"),
                        percentage=g("Percentage drop"))
    out["check_power_grid"] = re.findall(r"OT_PSM net=(\S+) status=(\S+)", log)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--w10p5", type=Path, required=True, help="copy of W10's p5 ORFS work dir + W18 runs")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    base = next((a.w10p5 / "orfs/results/asap7").glob("*/base"))
    logs = next((a.w10p5 / "orfs/logs/asap7").glob("*/base"))
    lef = DF.lef_macro(ABS / "ot_v41_rom_elem_q.lef")
    exact = (ABS / "ot_v41_rom_elem_q_exact.lef").read_text()
    m7 = exact.split("  OBS")[1].split("LAYER M7 ;")[1].split("LAYER")[0]
    m7_area = sum((float(r[2]) - float(r[0])) * (float(r[3]) - float(r[1]))
                  for r in re.findall(r"RECT\s+([-0-9.]+) ([-0-9.]+) ([-0-9.]+) ([-0-9.]+)", m7))
    core = (511.596 - 2.16) * (129.6 - 2.16)
    pw = power((logs / "w18_pair_power.log").read_text())
    tiling = {}
    for f in sorted(FP.glob("die_floorplan_ch*.json")):
        r = json.loads(f.read_text())
        tiling[f.stem] = dict(record=str(f.relative_to(ROOT)), sha256=sha(f), rule=r["cluster_rule"],
                              pitch_um=r["pair"]["pitch_um"], pack_pitch_um=r["pair"]["pack_pitch_um"],
                              pitch_vs_pack=r["pair"]["pitch_vs_pack"],
                              area_vs_pack=round(r["pair"]["pitch_vs_pack"][0] * r["pair"]["pitch_vs_pack"][1], 4),
                              capacity=r["capacity"], vm_to_farthest_cluster=r["crossings"]["vm_to_farthest_cluster"])
    scen = {k: v["total"]["total_w"] for k, v in pw.items() if "total" in v}
    leak = pw["default"]["total"]["leakage_w"]
    rec = dict(
        schema="opentallas.v41.w18_pair_abstract.v1",
        element="W10 ROM-array element pair ot_v41_rom_elem_q (NB=2, MTP=1, EARLY=1), run p5 "
                "(results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json): routed, NOT closed "
                "(setup WNS -209 ps at 0.92 ns, 1 DRC)",
        sources=dict(odb_sha256=sha(base / "6_final.odb"), spef_sha256=sha(base / "6_final.spef"),
                     sdc_sha256=sha(base / "6_final.sdc"),
                     w10_record_sha256=sha(ROOT / "results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json")),
        abstract=dict(dir=str(ABS.relative_to(ROOT)),
                      files={p.name: sha(p) for p in sorted(ABS.iterdir())},
                      generator="ORFS do-generate_abstract (write_abstract_lef -bloat_occupied_layers, "
                                "write_timing_model) + write_abstract_lef without bloat (exact)",
                      size_um=[lef["w"], lef["h"]], signal_pins=lef["signal_pins"], pin_edges=lef["pin_edges"],
                      power_pin_layers=lef["power_layers"], obs_layers_bloated=lef["obs_layers"],
                      m7_signal_route_fraction=round(m7_area / core, 4)),
        defects=[
            "VDD/VSS are M6 straps under the bloated M7 OBS: a parent cannot drop vias onto them (the PDN-0006 "
            "class of the v1 PHY). Fix at re-harden: expose M7 power straps as pins (or keep M7 power channels).",
            "All 734 signal pins sit on the south edge: stacked rows need a pin channel under every pair; "
            "abutment requires pins that meet the neighbour (root's hard budget for W10 p9/q7: 485 x 121 um, "
            "abutment pins).",
        ],
        tiling=tiling,
        power_w_per_pair=dict(
            scenarios=scen, breakdown=pw,
            ideal_icg_idle_w=leak,
            die_x7102_w={k: round(v * PAIRS, 1) for k, v in scen.items()} | {"ideal_icg_idle": round(leak * PAIRS, 2)},
            basis="OpenSTA report_power on the routed odb + SPEF, TT 0.7 V, 1.087 GHz; idle_clock_gated could not "
                  "stop the clock in STA (same as idle_clock_on): ideal ICG idle = leakage only",
            model_comparison=dict(model_rom_field_clock_w=13.1, model_rom_field_leakage_w=13.2,
                                  measured_ungated_idle_w=round(scen["idle_clock_on"] * PAIRS, 1),
                                  measured_leakage_w=round(leak * PAIRS, 2))),
        ir=dict(ir((logs / "w18_pair_ir.log").read_text()),
                basis="PSM analyze_power_grid on the routed pair, sources = its M6 straps (STRAPS), ORFS default "
                      "activity power (0.239 W)"),
        tool_sha256=sha(Path(__file__)),
    )
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("abstract", "power_w_per_pair", "ir")}, indent=1)[:3000])


if __name__ == "__main__":
    main()
