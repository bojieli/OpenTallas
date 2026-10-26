#!/usr/bin/env python3
"""KITS-SPARE (10-25 15:xx) S81 plan delta: extend the merged t23/t46 station treatment (delta_kitsspare2_1025 item 5,
main 3077f3738) to the remaining non-path slice_station types whose R1 A/B/C kits are on GEOM route HOLD for the
clock (GEOM-REVIEW-2 06:53/06:56, GEOM-REVIEW-4 07:01 (B)) or FAIL placement (t14 diagonal stations, R1 A (A)):
  - clock.tap_mode 'density' (taps at the sink sites: station banks + face pin-register strips, none empty, no grid),
    tap_target_sinks 600 / tap_max_sinks 1500 / tap_radius_um 150 (same values as t23/t46);
  - fixed Manhattan knee bit sites (tools/die_plan/ft_knee_sites.py) so every bank is a compact row on its tap.
0 added cycles is asserted per slot (types whose knee sites would add cycles take the clock part only, CLOCK_ONLY).  PATH-S81 types t18/t22 are NOT touched (path-owned).
Idempotent.  usage: delta_kitsspare3_1025.py LEDGER.json [types...]"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(W / "tools/die_plan"))
import compact_plan  # noqa: E402

PLAN = HERE / "die_plan.json"
STATION_TYPES = tuple(f"slice_station__t{n}" for n in (24, 26, 30, 38, 40, 42, 47, 25, 27, 36, 37, 41))
# Knee bit sites would ADD cycles here (ft0/ft1 +2 each on t25/t27/t36/t37/t41; t14 ft2 +1).  The R1 B/C placements of
# t25/t27/t36/t37/t41 are ACCEPTED (stations on the lattice, Manhattan), so they take the clock part only (density
# taps at the placed sink sites).  t14 (placement FAIL, +1 cycle on ft2) is left out: the cycle needs TOK-SCHED pricing.
CLOCK_ONLY = tuple(f"slice_station__t{n}" for n in (25, 27, 36, 37, 41))


def stations(raw, rep, types):
    import ft_knee_sites as K
    rep["knee"], rep["skipped"] = [], {}
    for tn in types:
        if tn in CLOCK_ONLY:
            continue
        if all("bit_sites_um" in s for s in raw["partition_types"][tn]["ft_slots"]):
            continue
        trial = copy.deepcopy(raw)
        try:
            led = K.place(trial, [tn])
        except (ValueError, IndexError) as e:
            rep["skipped"][tn] = f"{type(e).__name__}: {e}"
            continue
        bad = [(r["slot"], r["added_cycles"]) for r in led if r["added_cycles"]]
        if bad:
            rep["skipped"][tn] = f"added cycles {bad}"
            continue
        raw["partition_types"][tn] = trial["partition_types"][tn]
        rep["knee"] += led
    for tn in types:
        if tn in rep["skipped"]:
            continue
        ck = raw["partition_types"][tn].setdefault("clock", {})
        ck["tap_mode"] = "density"
        ck["tap_target_sinks"] = 600
        ck["tap_max_sinks"] = 1500
        ck["tap_radius_um"] = 150.0
    rep["station_clock"] = {tn: raw["partition_types"][tn]["clock"] for tn in types if tn not in rep["skipped"]}


def main():
    types = tuple(sys.argv[2:]) or STATION_TYPES
    raw = json.loads(PLAN.read_text())
    rep = {}
    stations(raw, rep, types)
    PLAN.write_text(compact_plan.dumps(raw))
    Path(sys.argv[1]).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print(json.dumps({"applied": sorted(rep["station_clock"]), "skipped": rep["skipped"],
                      "max_hop": {r["type"] + "/" + r["slot"]: round(r["worst_paired_bit_um"], 1) for r in rep["knee"]}}, default=str))


if __name__ == "__main__":
    main()
