#!/usr/bin/env python3
"""Summarise the routed ASAP7 express-link records into the wafer fabric's
per-field-crossing latency.

Reads results/physical_abi3/asap7/rom/ot_rom_express_link/<run>/ -- each a
tools/run_abi3_physical.py record (physical.json), its retained ORFS finish
report (physical_artifacts/6_finish.rpt) and geometry.json (register columns
and per-layer routed wirelength read from that run's 6_final.def, whose
sha256 the record carries) -- and writes
results/architecture/wafer_express_link_measurement.json.

Every delay here is read from a post-route OpenSTA report on RCX-extracted
parasitics; the only arithmetic is the linear fit of delay against span, the
extrapolation to one reticle field, and the track-budget wire count, each of
which is stated in the output.

    python3 tools/wafer_express_link_summary.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "results/physical_abi3/asap7/rom/ot_rom_express_link"
OUTPUT = ROOT / "results/architecture/wafer_express_link_measurement.json"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"

FIELD_PITCH_MM = math.sqrt(815.0)  # reticle.area_mm2, a 28.55 mm square field
TARGET_CLOCK_PS = 1000.0           # the ~1 GHz fabric clock the question names
# OpenSTA's default switching activity when no activity is annotated (ORFS sets
# none): 0.1 transitions per clock on every input, propagated through the flops.
OPENSTA_DEFAULT_ACTIVITY = 0.1
# ASAP7 (the ORFS platform's tech LEF) horizontal routing pitches, um.
ASAP7_PITCH_UM = {"M2": 0.036, "M4": 0.048, "M6": 0.064, "M8": 0.080}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worst_setup_path(rpt: str) -> dict:
    """Decompose the worst max path of an ORFS 6_finish.rpt (asap7: ps)."""
    sec = rpt.split("finish report_checks -path_delay max\n", 1)[1].split("==========", 1)[0]
    start = re.search(r"Startpoint: (\S+)", sec).group(1)
    end = re.search(r"Endpoint: (\S+)", sec).group(1)
    launch, capture = sec.split("data arrival time", 1)

    def pin_row(text: str, pin: str) -> tuple[float, float]:
        for line in text.splitlines():
            parts = line.split()
            for i, tok in enumerate(parts):
                if tok in ("^", "v") and i + 1 < len(parts) and parts[i + 1] == pin:
                    return float(parts[i - 1]), float(parts[i - 2])
        raise ValueError(f"pin {pin} not in path")

    launch_ck, _ = pin_row(launch, start + "/CLK")
    q_pin = start + ("/QN" if start + "/QN" in launch else "/Q")
    q_time, clk_to_q = pin_row(launch, q_pin)
    arrival = float(re.search(r"([-\d.]+)\s+data arrival time", sec).group(1))
    capture_ck, _ = pin_row(capture, end + "/CLK")
    period = float(re.search(r"([-\d.]+)\s+[-\d.]+\s+clock core_clk \(rise edge\)", capture).group(1))
    setup = -float(re.search(r"([-\d.]+)\s+[-\d.]+\s+library setup time", capture).group(1))
    slack = float(re.search(r"([-\d.]+)\s+slack", sec).group(1))
    repeaters = 0
    for line in launch.split(start + "/CLK", 1)[1].splitlines():
        if re.search(r"/Y \((BUF|INV|HB)", line):
            repeaters += 1
    return {
        "startpoint": start,
        "endpoint": end,
        "clock_period_ps": period,
        "slack_ps": slack,
        "clk_to_q_ps": clk_to_q,
        "wire_and_repeaters_ps": round(arrival - q_time, 2),
        "register_to_register_ps": round(arrival - launch_ck, 2),
        "library_setup_ps": setup,
        "clock_skew_capture_minus_launch_ps": round(capture_ck - period - launch_ck, 2),
        "repeaters_on_path": repeaters,
    }


def power_groups(rpt: str) -> dict:
    sec = rpt.split("finish report_power", 1)[1]
    out = {}
    for group in ("Sequential", "Combinational", "Clock", "Total"):
        m = re.search(rf"\n{group}\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", sec)
        out[group.lower() + "_w"] = float(m.group(4))
    return out


def load_run(run_dir: Path) -> dict:
    record = json.loads((run_dir / "physical.json").read_text())
    rpt_path = run_dir / "physical_artifacts/6_finish.rpt"
    rpt = rpt_path.read_text()
    geometry = json.loads((run_dir / "geometry.json").read_text())
    params = record["design"]["parameters"]
    pnr = record["place_and_route"]
    cols = geometry["register_columns_um"]
    span_um = cols[-1]["x_min"] - cols[0]["x_min"]
    segments = len(cols) - 1
    m = pnr["metrics"]
    return {
        "run": run_dir.name,
        "record": str((run_dir / "physical.json").relative_to(ROOT)),
        "record_sha256": sha256(run_dir / "physical.json"),
        "finish_report_sha256": sha256(rpt_path),
        "W": params["W"],
        "LINK_UM": params["LINK_UM"],
        "SPACING_UM": params["SPACING_UM"],
        "BOUNDARY_ADD": params["BOUNDARY_ADD"],
        "routing_layers": (pnr.get("floorplan") or {}).get("routing_layers") or ["M2", "M7"],
        "max_transition_ns": (pnr.get("signal_integrity_constraints") or {}).get("max_transition_ns"),
        "target_clock_period_ns": record["target_clock_period_ns"],
        "status": record["status"],
        "span_um": round(span_um, 3),
        "segments": segments,
        "segment_um": round(span_um / segments, 3),
        "register_columns_um": cols,
        "signal_wirelength_um_by_layer": geometry["signal_wirelength_um_by_layer"],
        "worst_setup_path": worst_setup_path(rpt),
        "power": power_groups(rpt),
        "standard_cell_area_um2": m["standard_cell_area_um2"],
        "timing_repair_buffer_area_um2": json.loads((run_dir / "physical_artifacts/metadata.json").read_text())
        .get("finish__design__instance__area__class__timing_repair_buffer"),
        "setup_wns_ns": m["setup_wns_ns"],
        "hold_wns_ns": m["hold_wns_ns"],
        "drc_errors": m["drc_errors"],
        "max_slew_violations": m["max_slew_violations"],
    }


def fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    runs = [load_run(d) for d in sorted(RECORDS.iterdir()) if (d / "physical.json").is_file()]
    by_name = {r["run"]: r for r in runs}

    # ---- delay per mm: single-segment spans, default layers, default slew ---
    single = [r for r in runs if r["segments"] == 1 and r["W"] == 64 and r["BOUNDARY_ADD"] == 0
              and r["routing_layers"] == ["M2", "M7"] and r["max_transition_ns"] is None]
    single.sort(key=lambda r: r["span_um"])
    xs = [r["span_um"] / 1000.0 for r in single]
    wire = [r["worst_setup_path"]["wire_and_repeaters_ps"] for r in single]
    r2r = [r["worst_setup_path"]["register_to_register_ps"] for r in single]
    slope_wire, icpt_wire = fit(xs, wire)
    slope_r2r, icpt_r2r = fit(xs, r2r)
    residual = max(abs(y - (slope_r2r * x + icpt_r2r)) for x, y in zip(xs, r2r))
    setup_ps = max(r["worst_setup_path"]["library_setup_ps"] for r in single)
    skew_ps = max(abs(r["worst_setup_path"]["clock_skew_capture_minus_launch_ps"]) for r in single)

    # Reach at 1 GHz from the fit: register-to-register + setup + skew <= 1 ns.
    reach_fit_mm = (TARGET_CLOCK_PS - icpt_r2r - setup_ps - skew_ps) / slope_r2r

    # ---- register-spacing sweep at the 1 ns clock ---------------------------
    sweep = sorted(
        (r for r in runs if r["target_clock_period_ns"] == TARGET_CLOCK_PS / 1000.0 and r["BOUNDARY_ADD"] == 0),
        key=lambda r: r["segment_um"],
    )
    closed = [r for r in sweep if r["status"] == "pass"]
    reach_closed_um = max((r["segment_um"] for r in closed), default=None)

    # ---- energy per bit per mm: combinational power slope over span ---------
    comb = [r["power"]["combinational_w"] for r in single]
    slope_p, _ = fit(xs, comb)  # W per mm
    f_hz = 1e12 / single[0]["worst_setup_path"]["clock_period_ps"]
    wires = single[0]["W"] + 1  # data + valid
    e_toggle_mm = slope_p / (f_hz * wires * OPENSTA_DEFAULT_ACTIVITY)
    area_slope, _ = fit(xs, [r["standard_cell_area_um2"] for r in single])

    # ---- field crossing -----------------------------------------------------
    reach_used_um = reach_closed_um if reach_closed_um is not None else reach_fit_mm * 1000.0
    field_um = FIELD_PITCH_MM * 1000.0
    cycles_wire = math.ceil(field_um / reach_used_um)
    boundary = {
        "forwarding_mux": {"cycles": 1},
        "fp32_reduction": {"cycles": 6},
    }
    for name, b in boundary.items():
        add_runs = [r for r in runs if r["BOUNDARY_ADD"] == (1 if name == "fp32_reduction" else 0)
                    and r["target_clock_period_ns"] == TARGET_CLOCK_PS / 1000.0]
        b["routed_evidence"] = [
            {"run": r["run"], "status": r["status"], "setup_wns_ns": r["setup_wns_ns"]} for r in add_runs
        ]
    # The reduction boundary was not routed inside the link; its only new logic is
    # the project's pipelined adder, which has its own routed ASAP7 record.
    adder = ROOT / "results/physical_abi3/asap7/hdc/ot_fp32_add_rne_pipe/physical.json"
    adder_rec = json.loads(adder.read_text())
    boundary["fp32_reduction"]["routed_evidence"].append({
        "record": str(adder.relative_to(ROOT)),
        "record_sha256": sha256(adder),
        "top": adder_rec["design"]["top"],
        "status": adder_rec["status"],
        "target_clock_period_ns": adder_rec["target_clock_period_ns"],
        "fmax_hz": adder_rec["place_and_route"]["metrics"]["fmax_hz"],
        "note": (
            "the 5-stage binary32 adder the reduction boundary instantiates closes "
            "routed at 0.7 ns on its own, so 5 adder cycles + 1 output register at 1 GHz "
            "is supported; the link with BOUNDARY_ADD=1 was not itself routed"
        ),
    })
    boundary["forwarding_mux"]["note"] = (
        "the mux is the boundary register's D-input in every routed link above "
        "(the NOR2/AO21 ahead of out_data on each worst path), so it is inside the measurement"
    )
    per_field = {
        name: {
            "cycles": cycles_wire + b["cycles"],
            "ns_at_1ghz": (cycles_wire + b["cycles"]) * TARGET_CLOCK_PS / 1000.0,
        }
        for name, b in boundary.items()
    }

    # ---- wires per field edge -----------------------------------------------
    track_budget = {
        "layers": ["M6", "M8"],
        "fraction_of_tracks": 0.25,
        "tracks_per_wire": 2,
        "basis": (
            "an east-west express bus crossing a 28.55 mm field edge on the two "
            "upper horizontal ASAP7 layers, given a quarter of their tracks (the rest "
            "carry power, the clock and local routing) and one spacing track per wire "
            "(shielding/crosstalk), a conventional budget for long parallel buses"
        ),
    }
    tracks = sum(field_um / ASAP7_PITCH_UM[l] for l in track_budget["layers"])
    wires_per_edge = int(tracks * track_budget["fraction_of_tracks"] / track_budget["tracks_per_wire"])
    repeater_area_um2_per_wire_mm = area_slope / wires
    repeater_area_mm2 = wires_per_edge * repeater_area_um2_per_wire_mm * FIELD_PITCH_MM / 1e6

    tech = json.loads(TECHNOLOGY.read_text())
    assumed_s_per_mm = tech["latency"]["global_wire_delay_s_per_mm"]["value"]
    hop_n5_s = tech["links"]["on_wafer_n5"]["hop_latency_s"]["value"]

    measured_ps_per_mm = slope_r2r
    summary = {
        "schema_version": 1,
        "grade": "measured",
        "grade_scope": (
            "measured on ASAP7 -- a PREDICTIVE 7 nm academic PDK (ORFS platform asap7, "
            "RVT, TT corner) -- standing in for N5; no N5 wire has been routed. The "
            "numbers are this flow's post-route, RCX-extracted OpenSTA timing of a real "
            "placed and routed link, not a model"
        ),
        "question": (
            "what a pipelined, repeated on-wafer express link costs per mm and per "
            "28.55 mm reticle-field crossing, so technology.json latency."
            "global_wire_delay_s_per_mm (assumed 150 ps/mm) and the wafer fabric's "
            "125 ns field crossing (links.on_wafer_n5) can rest on a measurement"
        ),
        "design": {
            "rtl": "rtl/rom/ot_rom_express_link.sv",
            "placement_hook": "tools/rom_express_link_place.tcl",
            "method": (
                "a W-bit register-to-register link on a long thin die (height 40 um), "
                "input pins on the west edge and output pins on the east edge "
                "(--pin-region), every register column FIXED at its distance along the "
                "die by the POST_PDN hook so the wire between columns really spans it; "
                "repeaters are inserted and sized by ORFS (repair_design/repair_timing), "
                "not hand-placed. Pin-to-register paths are false-pathed "
                "(--false-path-io) because the registers sit at the pins; the link "
                "itself is register-to-register and fully timed"
            ),
        },
        "measured": {
            "ps_per_mm": round(measured_ps_per_mm, 1),
            "ps_per_mm_wire_and_repeaters_only": round(slope_wire, 1),
            "fit": {
                "model": "register_to_register_ps = intercept + slope * span_mm, single-segment 64-bit links, default layers M2-M7",
                "points": [
                    {"run": r["run"], "span_mm": round(x, 4), "register_to_register_ps": y}
                    for r, x, y in zip(single, xs, r2r)
                ],
                "slope_ps_per_mm": round(slope_r2r, 2),
                "intercept_ps": round(icpt_r2r, 2),
                "max_residual_ps": round(residual, 2),
            },
            "max_register_spacing_at_1ghz_um": {
                "from_fit": round(reach_fit_mm * 1000.0, 1),
                "fit_budget": (
                    f"1000 ps - intercept {icpt_r2r:.1f} - setup {setup_ps:.1f} - "
                    f"worst |skew| {skew_ps:.1f} ps, divided by the slope"
                ),
                "largest_spacing_routed_closed_at_1ns": reach_closed_um,
                "sweep": [
                    {
                        "run": r["run"], "segment_um": r["segment_um"], "segments": r["segments"],
                        "status": r["status"], "setup_wns_ns": r["setup_wns_ns"],
                        "hold_wns_ns": r["hold_wns_ns"],
                        "worst_register_to_register_ps": r["worst_setup_path"]["register_to_register_ps"],
                        "worst_path_clock_skew_ps": r["worst_setup_path"]["clock_skew_capture_minus_launch_ps"],
                        "worst_path": f'{r["worst_setup_path"]["startpoint"]} -> {r["worst_setup_path"]["endpoint"]}',
                    }
                    for r in sweep
                ],
                "reading": (
                    "1.0 mm register spacing closes at 1 GHz with the flow's own clock tree "
                    "(setup, hold, slew and DRC all clean). 1.5 mm does NOT close, but its "
                    "worst data path is under 1 ns: what fails it is ~330 ps of clock skew "
                    "from a conventional tree spread over 3 mm. With a clock forwarded "
                    "alongside the data (source-synchronous, the normal choice for a long "
                    "link) the reach is the zero-skew fit value, ~1.3 mm. The field crossing "
                    "below uses the routed-and-closed 1.0 mm, the conservative figure"
                ),
            },
            "energy_per_bit_per_mm": {
                "fj_per_transition_per_mm": round(e_toggle_mm * 1e15, 2),
                "fj_per_bit_per_mm_random_data": round(e_toggle_mm * 0.5 * 1e15, 2),
                "basis": (
                    "slope of the post-route Combinational power group (repeaters plus the "
                    "wire they drive) over span, at the route's clock and OpenSTA's default "
                    f"activity {OPENSTA_DEFAULT_ACTIVITY} transitions/cycle on {wires} wires; "
                    "random data toggles a wire 0.5 times per bit. Clock-tree power excluded"
                ),
            },
            "repeater_area_um2_per_wire_per_mm": round(repeater_area_um2_per_wire_mm, 3),
        },
        "extrapolation_to_one_field": {
            "field_pitch_mm": round(FIELD_PITCH_MM, 3),
            "statement": (
                "a linear extrapolation of the ASAP7 per-mm fit from 1-3 mm to 28.55 mm: "
                "a repeated, registered wire's delay is linear in length (every segment is "
                "the same), so the per-mm slope carries; what does NOT carry is the node "
                "-- N5's thick upper metals are several times less resistive than ASAP7's "
                "M6/M8, so N5 would be faster, not slower"
            ),
            "unregistered_flight_time_ns": round(measured_ps_per_mm * FIELD_PITCH_MM / 1000.0, 2),
            "register_spacing_used_um": round(reach_used_um, 1),
            "register_spacing_source": "routed-closed" if reach_closed_um is not None else "fit",
            "wire_cycles_at_1ghz": cycles_wire,
            "boundary_stage_cycles": {k: v["cycles"] for k, v in boundary.items()},
            "boundary_evidence": {k: v["routed_evidence"] for k, v in boundary.items()},
            "per_field_crossing": per_field,
        },
        "wires_per_field_edge": {
            "track_budget": track_budget,
            "wires": wires_per_edge,
            "bandwidth_per_edge_tbit_s_at_1ghz": round(wires_per_edge * 1e9 / 1e12, 1),
            "bandwidth_per_wire": "one bit per cycle per wire: 1 Gbit/s at the 1 GHz fabric clock",
            "repeater_area_mm2_for_those_wires_across_one_field": round(repeater_area_mm2, 2),
            "field_area_mm2": 815.0,
        },
        "comparison": {
            "technology_global_wire_delay_ps_per_mm": assumed_s_per_mm * 1e12,
            "measured_over_assumed": round(measured_ps_per_mm / (assumed_s_per_mm * 1e12), 2),
            "technology_field_crossing_at_assumed_ps_per_mm_ns": round(assumed_s_per_mm * 1e12 * FIELD_PITCH_MM / 1000.0, 2),
            "cerebras_mesh_field_crossing_ns": hop_n5_s * 1e9,
            "cerebras_mesh_source": "configs/hardware/technology.json#links.on_wafer_n5.hop_latency_s",
            "express_link_field_crossing_ns": per_field["forwarding_mux"]["ns_at_1ghz"],
            "speedup_over_cerebras_mesh": round((hop_n5_s * 1e9) / per_field["forwarding_mux"]["ns_at_1ghz"], 2),
        },
        "conclusion": (
            f"On ASAP7 a flow-repeated wire costs {measured_ps_per_mm:.0f} ps/mm register to "
            f"register, {measured_ps_per_mm / (assumed_s_per_mm * 1e12):.1f}x the 150 ps/mm "
            "technology.json assumes and well above its 100-250 range: ASAP7's routing "
            "metals are thin (M6/M8 at 64/80 nm pitch) and ORFS repeats with buffers it "
            "sizes for timing, not an optimally sized inverter chain, so this is a "
            "pessimistic 7 nm point and an N5 top-metal link would be faster. Even so a "
            f"purpose-built express link crosses a 28.55 mm field in "
            f"{per_field['forwarding_mux']['cycles']} cycles = "
            f"{per_field['forwarding_mux']['ns_at_1ghz']:.0f} ns at 1 GHz with a forwarding "
            f"boundary ({per_field['fp32_reduction']['ns_at_1ghz']:.0f} ns with a one-shot FP32 "
            f"reduction), about {(hop_n5_s * 1e9) / per_field['forwarding_mux']['ns_at_1ghz']:.1f}x "
            "less than the 125 ns Cerebras-mesh crossing the model charges. The latency "
            "a field crossing should carry for a purpose-built collective network is "
            "therefore ~30 ns (35 ns reducing), and a single unregistered reticle "
            f"traversal at the measured slope is {measured_ps_per_mm * FIELD_PITCH_MM / 1000.0:.1f} ns, "
            "not the 4.28 ns the 150 ps/mm assumption gives"
        ),
        "variants": [
            {
                "run": r["run"], "span_um": r["span_um"], "routing_layers": r["routing_layers"],
                "max_transition_ns": r["max_transition_ns"], "W": r["W"],
                "register_to_register_ps": r["worst_setup_path"]["register_to_register_ps"],
                "fit_at_this_span_ps": round(icpt_r2r + slope_r2r * r["span_um"] / 1000.0, 1),
                "signal_wirelength_um_by_layer": r["signal_wirelength_um_by_layer"],
            }
            for r in runs if r["segments"] == 1 and r not in single
        ],
        "variants_reading": (
            "the per-mm cost is set by the flow's repeater insertion, not by the metal: "
            "opening M8/M9 moved the long wire from M6 to M8 (lower RC) and a 60 ps "
            "max-transition limit forced denser buffering, and neither moved the "
            "register-to-register delay by more than a few percent. A run restricted "
            "to M4-M9 failed detailed routing (pin access, DRT-0255) and has no record"
        ),
        "runs": runs,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=False) + "\n")
    print(f"wrote {out}")
    print(f"  measured {measured_ps_per_mm:.1f} ps/mm (register-to-register slope), "
          f"reach at 1 GHz {reach_used_um:.0f} um, {cycles_wire} wire cycles per field, "
          f"{per_field['forwarding_mux']['ns_at_1ghz']:.0f} ns per crossing with the mux boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
