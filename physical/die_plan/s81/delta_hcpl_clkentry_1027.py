"""S81 plan event (S81-CORES-R27, COORD 10-27 19:14 "HCPL: no waiver; the clock is the centred M5 entry"):
single-root master-plan CORE slice for ot_dsrom_su_hcpost_lane_pr (12.8a centre clock entry, 12.3 latency target).

HCPL is not a member of the S81-CORE-LAT families (core_lat/families_r13.json), so no family slice exists; this is the
minimal single-root form (precedent qwen_compute a0/slices/ot_qwen_tile_node.json): one island at the outline
geometric centre carrying the M5 clock_pin, core_clock_port clk, an empty pushdown section (in-core clock tree built
by CTS from the entry; no die feed-through ports, so the island is not a strip blockage, 12.2a1).  The plan pin table
and LEF keep clk as a face pin; gen_core_kit_legacy --master-slice rewrites the kit io.tcl clk to the entry
(master_slice._consume_io, GEOM-21 full-width M5 shape on track).  Fail-closed: plan outline must be 114.48^2 and
the module must be a single-instance-type hard core in die_plan.json; the entry is snapped onto the M5 track.
"""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOD = "ot_dsrom_su_hcpost_lane_pr"
OUT = HERE / "cores/legacy/slices" / f"{MOD}.json"
M5_OFF, M5_PITCH = 0.012, 0.048        # ASAP7 M5 x tracks (gen_core_kit_legacy make_tracks)
ISL = 4.32                             # island rect side (L2/L3 family slices: 4.32 um)


def main():
    plan = json.loads((HERE / "die_plan.json").read_text())
    ols = {tuple(h["outline_um"]) for t in plan["partition_types"].values() for h in t.get("hard_cores", [])
           if h["module"] == MOD}
    if ols != {(114.48, 114.48)}:
        raise SystemExit(f"{MOD}: plan outlines {ols} != {{(114.48, 114.48)}} (fail-closed)")
    w, h = 114.48, 114.48
    cx, cy = w / 2, h / 2
    x = round(M5_OFF + math.floor((cx - M5_OFF) / M5_PITCH + 0.5) * M5_PITCH, 4)
    y = round(cy, 4)
    sl = {"schema": "opentallas.master_plan_slice.v1", "kind": "core", "die": "s81", "type": MOD, "module": MOD,
          "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False,
          "outline_um": [w, h],
          "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20, "early_taps": False},
          "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [], "gates": {},
          "core_clock_port": "clk",
          "islands": [{"name": "ck_entry", "rect_um": [round(cx - ISL / 2, 4), round(cy - ISL / 2, 4),
                                                       round(cx + ISL / 2, 4), round(cy + ISL / 2, 4)],
                       "centre_um": [cx, cy], "use": "clock_driver", "via_stack": ["M9", "M5"],
                       "clock_pin": {"layer": "M5", "xy_um": [x, y]},
                       "note": "12.8a centre clock entry (S81-CORES-R27 HCPL clock-entry event; no waiver)"}],
          "pushdown": {"islands": [], "clock_repeaters": [],
                       "note": "in-core clock tree built by CTS from the centre entry; no feedthrough ports"},
          "event": "S81-CORES-R27 delta_hcpl_clkentry_1027.py"}
    sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
    import master_slice as MS
    errs = MS.validate(sl)
    if errs:
        raise SystemExit(f"slice invalid: {errs}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sl, indent=1) + "\n")
    rect = sl["islands"][0]["rect_um"]
    print(f"HCPL_CLKENTRY slice {OUT.relative_to(HERE.parents[2])} entry M5 ({x}, {y}) island {rect}")


if __name__ == "__main__":
    main()
