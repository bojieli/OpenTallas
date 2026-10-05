#!/usr/bin/env python3
"""What does operand reuse buy per unit area, at the array level, from routed records?

THE UNIT OF ACCOUNT is throughput per unit area of a 16-unit array, because that is
what an iso-area comparison against a GPU die actually measures. A lane figure is
not that: ``tools/audit_energy_attribution.py`` measures a BF16 packed lane at 6.591
TFLOP/s per mm2 while the array it sits in delivers 0.842, and the difference is
everything around the multipliers.

THE CHANGE BEING PRICED. ``ot_compute_unit`` is a GEMV engine -- one weight column
per cycle broadcast to LANES lanes, each weight used once. ``ot_compute_unit_gemm``
holds the weight column and walks NCOL activation columns against it, so the weight
store, the sequencer, the column counter and the refill port are amortised over NCOL
times the arithmetic. ``tools/rtl_gemm_operand_reuse_campaign.py`` measures the cycle
side; this tool measures the area and frequency side and composes the array.

ARRAY COMPOSITION follows ``tools/audit_chip_level_density.py`` exactly -- same
components, same instance counts, same peak-arithmetic throughput basis
(lanes x 2 x the slowest datapath clock), same exclusions -- with the tensor compute
unit swapped. Anything else would be comparing two different accounting rules and
calling the difference a result.

TWO ARRAYS ARE REPORTED, and the honest one is the second.

  elementwise_held   the vector and reduction blocks are instanced as today, 16 of
                     each. This is what the existing audit's basis licenses, because
                     that basis charges nothing for elementwise throughput -- but at
                     NCOL=8 each weight pass produces NCOL times the output columns,
                     so the post-GEMM stages are NCOL times more loaded.
  elementwise_scaled the same blocks scaled by NCOL, which is what keeping the
                     elementwise stages at parity with the MAC array costs.

Neither is a workload measurement. The throughput on both sides is peak arithmetic.

REFUSALS. ASAP7 is a predictive, non-manufacturable academic PDK and the comparator
is silicon on TSMC N7. The FakeRAM parts are plausible geometry with a black-box
timing model, so no memory energy figure follows from them. Power is ORFS's
default-activity estimate, not a workload measurement. The activation store fill is
not charged: NCOL activation columns must be written per weight pass, so a GEMM unit
is only worth its area when the activation tile is itself reused across weight
columns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

A100_DIE_AREA_MM2 = 826.0
A100_POWER_W = 400.0
A100_TFLOPS = 312.0
GPU_LOGIC_FRACTION = 0.6
FLOPS_PER_MAC = 2
A100_OPS_S_PER_MM2 = A100_TFLOPS * 1e12 / A100_DIE_AREA_MM2
A100_OPS_S_PER_W = A100_TFLOPS * 1e12 / A100_POWER_W

#: FakeRAM 2.0 macro areas, from the LEF each part ships inside the pinned ORFS
#: image (rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv records where they were read).
#: ORFS reports macro_area_um2 in the routed record, so these are only used to
#: attribute that total between the weight and the activation store.
FAKERAM_AREA_UM2 = {
    "fakeram_256x128": 1375.941, "fakeram_512x128": 2751.883,
    "fakeram_2048x128": 11007.531, "fakeram_256x64": 687.971,
    "fakeram7_256x32": 343.985,
}

UNITS_PER_ARRAY = 16
VECTOR_RECORD = "results/physical_abi3/asap7/vector_add_unit/pnr.json"
REDUCTION_RECORD = "results/physical_abi3/asap7/reduction_s8_g2/pnr.json"
DISPATCHER_RECORD = "results/physical_abi3/asap7/cluster_dispatcher/pnr.json"
SEQUENCER_RECORD = "results/physical_abi3/asap7/a3_microsequencer/pnr.json"


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def source_currency(body: dict[str, Any]) -> dict[str, Any]:
    """Do the RTL files this record was produced from still hash to what it recorded?

    A routed record names its sources and their sha256 at the moment the run
    started. If a file has moved since, the record is evidence for a tree that no
    longer exists, and this repository has measured that drift at 64 of 96 pinning
    artifacts. Reporting it per record is cheaper than discovering it later.
    """
    drifted, missing = [], []
    for entry in body["design"].get("sources", []):
        path = ROOT / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            drifted.append(entry["path"])
    return {"current": not drifted and not missing,
            "drifted": drifted, "missing": missing}


def load(rel_or_abs: str) -> dict[str, Any]:
    path = Path(rel_or_abs)
    if not path.is_absolute():
        path = ROOT / path
    body = json.loads(path.read_text())
    pnr = body.get("place_and_route")
    if not pnr or "metrics" not in pnr:
        raise SystemExit(f"{path}: no place_and_route.metrics -- a pre-layout record "
                         "cannot support a frequency or density claim")
    m = pnr["metrics"]
    for key in ("fmax_hz", "core_area_um2", "power_total_w"):
        if not m.get(key):
            raise SystemExit(f"{path}: place_and_route.metrics.{key} missing")
    return {
        "record": str(path), "block": body["design"]["block"],
        "closed": bool(body["design"].get("closed")),
        "status": body.get("status"), "purpose": body.get("purpose"),
        "clock_period_ns": body["design"].get("clock_period_ns"),
        "fmax_hz": float(m["fmax_hz"]),
        "core_area_um2": float(m["core_area_um2"]),
        "standard_cell_area_um2": float(body["design"]["area_um2"]),
        "macro_area_um2": float(m.get("macro_area_um2") or 0.0),
        "macro_count": int(m.get("macro_count") or 0),
        "power_total_w": float(m["power_total_w"]),
        "instance_count": int(m.get("instance_count") or 0),
        "setup_wns_ns": m.get("setup_wns_ns"),
        "max_slew_violations": m.get("max_slew_violations"),
        "drc_errors": m.get("drc_errors"),
        "sources_current": source_currency(body),
        "core_utilization_arg": next(
            (body["runner"]["argv"][i + 1]
             for i, a in enumerate(body["runner"]["argv"])
             if a == "--core-utilization"), None),
    }


def array(unit: dict[str, Any], mac_per_cycle: int, elementwise_multiple: int,
          vec: dict[str, Any], red: dict[str, Any], disp: dict[str, Any],
          seq: dict[str, Any]) -> dict[str, Any]:
    """One array, composed exactly as tools/audit_chip_level_density.py composes it."""
    datapath = {"tensor_compute_unit": unit["fmax_hz"],
                "vector_add_unit": vec["fmax_hz"],
                "reduction_endpoint": red["fmax_hz"],
                "cluster_dispatcher": disp["fmax_hz"]}
    binding = min(datapath, key=lambda k: datapath[k])
    clock = datapath[binding]

    per_unit_area = (unit["core_area_um2"]
                     + elementwise_multiple * (vec["core_area_um2"] + red["core_area_um2"]))
    area_um2 = (UNITS_PER_ARRAY * per_unit_area
                + disp["core_area_um2"] + seq["core_area_um2"])
    power_w = (UNITS_PER_ARRAY * (unit["power_total_w"]
                                  + elementwise_multiple * (vec["power_total_w"]
                                                            + red["power_total_w"]))
               + disp["power_total_w"] + seq["power_total_w"])
    mac = UNITS_PER_ARRAY * mac_per_cycle
    ops = mac * FLOPS_PER_MAC * clock
    return {
        "units": UNITS_PER_ARRAY, "mac_per_cycle_per_unit": mac_per_cycle,
        "mac_per_cycle": mac, "elementwise_multiple": elementwise_multiple,
        "datapath_clock_hz": clock, "datapath_clock_binding_block": binding,
        "datapath_fmax_candidates": datapath,
        "area_mm2": area_um2 / 1e6, "power_w": power_w, "ops_s": ops,
        "tflops": ops / 1e12,
        "ops_s_per_mm2": ops / (area_um2 / 1e6),
        "ops_s_per_w": ops / power_w,
        "vs_a100_area": (ops / (area_um2 / 1e6)) / A100_OPS_S_PER_MM2,
        "vs_a100_area_logic_only": ((ops / (area_um2 / 1e6))
                                    / (A100_OPS_S_PER_MM2 / GPU_LOGIC_FRACTION)),
        "vs_a100_energy": (ops / power_w) / A100_OPS_S_PER_W,
        "area_breakdown_um2": {
            "compute_units": UNITS_PER_ARRAY * unit["core_area_um2"],
            "vector_add_units": UNITS_PER_ARRAY * elementwise_multiple * vec["core_area_um2"],
            "reduction_endpoints": UNITS_PER_ARRAY * elementwise_multiple * red["core_area_um2"],
            "cluster_dispatcher": disp["core_area_um2"],
            "microsequencer": seq["core_area_um2"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gemv", default="results/physical_abi3/asap7/compute_unit/pnr.json",
                    help="routed record for the 1-column baseline unit")
    ap.add_argument("--gemv-mac", type=int, default=16)
    ap.add_argument("--gemm", action="append", default=[], metavar="NCOL=RECORD",
                    help="routed record for a GEMM unit, repeatable")
    ap.add_argument("--lanes", type=int, default=16)
    ap.add_argument("--output")
    a = ap.parse_args()

    vec, red = load(VECTOR_RECORD), load(REDUCTION_RECORD)
    disp, seq = load(DISPATCHER_RECORD), load(SEQUENCER_RECORD)

    designs = [{"name": "gemv_ncol1", "ncol": 1, "unit": load(a.gemv),
                "mac_per_cycle": a.gemv_mac}]
    for spec in a.gemm:
        ncol_s, _, rel = spec.partition("=")
        ncol = int(ncol_s)
        designs.append({"name": f"gemm_ncol{ncol}", "ncol": ncol,
                        "unit": load(rel), "mac_per_cycle": a.lanes * ncol})

    for d in designs:
        u = d["unit"]
        d["unit_cell_area_um2"] = u["standard_cell_area_um2"] + u["macro_area_um2"]
        d["unit_cell_area_per_mac"] = d["unit_cell_area_um2"] / d["mac_per_cycle"]
        d["unit_core_area_per_mac"] = u["core_area_um2"] / d["mac_per_cycle"]
        d["unit_ops_s"] = d["mac_per_cycle"] * FLOPS_PER_MAC * u["fmax_hz"]
        d["unit_ops_s_per_mm2"] = d["unit_ops_s"] / (u["core_area_um2"] / 1e6)
        d["weight_bits_per_cycle"] = 16 * a.lanes
        d["weight_bytes_per_mac"] = (16 * a.lanes / 8) / d["mac_per_cycle"]
        for mult, key in ((1, "elementwise_held"), (d["ncol"], "elementwise_scaled")):
            d[key] = array(u, d["mac_per_cycle"], mult, vec, red, disp, seq)

    base = designs[0]
    for d in designs:
        d["vs_gemv"] = {
            "unit_density": d["unit_ops_s_per_mm2"] / base["unit_ops_s_per_mm2"],
            "unit_area": d["unit"]["core_area_um2"] / base["unit"]["core_area_um2"],
            "array_density_elementwise_held":
                d["elementwise_held"]["ops_s_per_mm2"]
                / base["elementwise_held"]["ops_s_per_mm2"],
            "array_density_elementwise_scaled":
                d["elementwise_scaled"]["ops_s_per_mm2"]
                / base["elementwise_scaled"]["ops_s_per_mm2"],
            "array_energy_elementwise_held":
                d["elementwise_held"]["ops_s_per_w"]
                / base["elementwise_held"]["ops_s_per_w"],
        }

    record = {
        "audit_id": "opentallas-gemm-operand-reuse-density-v1",
        "schema_version": 1,
        "git": git_state(),
        "comparator": {"name": "a100_sxm_80gb", "node": "TSMC N7",
                       "tflops_bf16_dense": A100_TFLOPS,
                       "die_area_mm2": A100_DIE_AREA_MM2, "power_w": A100_POWER_W,
                       "logic_fraction": GPU_LOGIC_FRACTION,
                       "ops_s_per_mm2": A100_OPS_S_PER_MM2},
        "shared_components": {"vector_add_unit": vec, "reduction_endpoint": red,
                              "cluster_dispatcher": disp, "microsequencer": seq},
        "fakeram_area_um2": FAKERAM_AREA_UM2,
        "designs": designs,
        "closed_everywhere": all(d["unit"]["closed"] for d in designs),
        "sources_current_everywhere": all(
            d["unit"]["sources_current"]["current"] for d in designs),
        "refusals": [
            "ASAP7 is a predictive, non-manufacturable academic PDK; the comparator is silicon on TSMC N7",
            "throughput on both sides is PEAK ARITHMETIC, lanes x 2 x clock, not a workload",
            "power is the ORFS default-activity estimate, not a measured workload",
            "the FakeRAM parts are plausible geometry with a black-box timing model, so no memory energy figure follows",
            "the activation store fill is not charged; a GEMM unit needs the activation tile reused across weight columns to be worth its area",
            "KV-cache SRAM, the global activation buffer, HBM PHY, the ROM array, clock and power distribution and the pad ring are outside the composed area, on both sides of the comparison",
        ],
    }

    print(f"comparator: A100, {A100_TFLOPS} TFLOP/s over {A100_DIE_AREA_MM2} mm2 "
          f"= {A100_OPS_S_PER_MM2/1e12:.3f} TFLOP/s per mm2\n")
    print("The compute unit, post-route:\n")
    print(f"  {'design':<14} {'MAC/cy':>7} {'fmax':>7} {'core um2':>10} {'cell um2':>10} "
          f"{'macro':>8} {'um2/MAC':>8} {'T/s/mm2':>8} {'wgtB/MAC':>9} {'closed':>7}")
    for d in designs:
        u = d["unit"]
        print(f"  {d['name']:<14} {d['mac_per_cycle']:>7} {u['fmax_hz']/1e6:>6.0f}M "
              f"{u['core_area_um2']:>10.1f} {d['unit_cell_area_um2']:>10.1f} "
              f"{u['macro_area_um2']:>8.1f} {d['unit_core_area_per_mac']:>8.1f} "
              f"{d['unit_ops_s_per_mm2']/1e12:>8.3f} {d['weight_bytes_per_mac']:>9.3f} "
              f"{str(u['closed']):>7}")
    for key in ("elementwise_held", "elementwise_scaled"):
        print(f"\nThe 16-unit array, {key.replace('_', ' ')}:\n")
        print(f"  {'design':<14} {'MAC/cy':>7} {'clock':>7} {'mm2':>7} {'TFLOP/s':>8} "
              f"{'T/s/mm2':>8} {'vs A100':>8} {'watt':>8} {'T/s/W':>7} {'vs A100':>8} {'vs GEMV':>8}")
        for d in designs:
            r = d[key]
            print(f"  {d['name']:<14} {r['mac_per_cycle']:>7} {r['datapath_clock_hz']/1e6:>6.0f}M "
                  f"{r['area_mm2']:>7.3f} {r['tflops']:>8.2f} {r['ops_s_per_mm2']/1e12:>8.3f} "
                  f"{r['vs_a100_area']:>7.2f}x {r['power_w']:>8.3f} {r['ops_s_per_w']/1e12:>7.3f} "
                  f"{r['vs_a100_energy']:>7.2f}x "
                  f"{d['vs_gemv']['array_density_' + key]:>7.2f}x")
        print(f"  clock bound by: {designs[-1][key]['datapath_clock_binding_block']}")
    print("\nArray area breakdown, elementwise held, um2:")
    for d in designs:
        b = d["elementwise_held"]["area_breakdown_um2"]
        tot = sum(b.values())
        print(f"  {d['name']:<14} " + "  ".join(
            f"{k}={v/tot*100:.1f}%" for k, v in b.items()))
    stale = [d["name"] for d in designs if not d["unit"]["sources_current"]["current"]]
    print("\nsource currency: "
          + ("every routed record still hashes to the RTL on disk"
             if not stale else f"DRIFTED, do not quote: {stale}"))
    print("\nrefusals:")
    for r in record["refusals"]:
        print(f"  - {r}")

    if a.output:
        out = Path(a.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {out}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
