#!/usr/bin/env python3
"""Measure the retained G4W16 fused-head route with a VM macro boundary.

This is a conditional child measurement: the reference clock is an existing
local capture leaf, not a routed SRAM clock. It cannot qualify the parent.
Original SDC/ODB/SPEF and failed verdicts are read-only. No arithmetic changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACRO = "ot_sram_1r1w_512x128_m4_r2c2"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def boundary_sdc(original):
    replacements = {
        "set_false_path -to [all_outputs]":
        "set_false_path -to [get_ports {r_tag[*] r_v leaf[*] o_we[*] o_addr[*] o_mask[*] o_data[*] fault}]",
        "set_false_path -hold -from [get_ports {ra_q[*]}]":
        "# SRAM input hold is checked in this child measurement.",
    }
    for before, after in replacements.items():
        if original.count(before) != 1:
            raise ValueError(f"expected exactly one retained context exception: {before}")
        original = original.replace(before, after)
    return original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route-base", type=Path, required=True)
    parser.add_argument("--context-sdc", type=Path, required=True,
                        help="Original constraint.sdc before ORFS expands port collections")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.route_base.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = [base / f"6_final.{ext}" for ext in ("odb", "sdc", "spef", "v")]
    macro_dir = ROOT / "physical/asap7_memory_macros" / MACRO
    spec = json.loads((macro_dir / f"{MACRO}.json").read_text())
    original = args.context_sdc.read_text()
    final = inputs[1].read_text()
    for pattern in (r"-period 833\.0000", r"-setup 60\.0000", r"-hold 25\.0000"):
        if not re.search(pattern, final):
            raise ValueError("retained clock/uncertainty mismatch")
    (out / "boundary.sdc").write_text(boundary_sdc(original))
    record = dict(scope="conditional G4W16 child boundary; not parent closure",
                  route=str(base), original_sha256={p.name: digest(p) for p in inputs},
                  original_context_sdc_sha256=digest(args.context_sdc),
                  constraints=dict(period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25),
                  tool_sha256={p: digest(ROOT / p) for p in (
                      "tools/dsrom_fh_boundary_sta.py", "tools/run_abi3_physical.py",
                      "tools/orfs_allcorner_spef.py")},
                  model_macro=MACRO, physical_closed=False, adopted=False, corners={})
    for corner in ("ss", "ff"):
        timing = spec["timing"][corner]
        lib = macro_dir / f"{MACRO}_{corner}.lib"
        # All 64 FP32 lanes. Four 128-bit macro slices feed each 512-bit group.
        # Address/CE therefore drive four macro inputs. SRAM clock capacitance
        # is recorded as unresolved CTS demand, never credited to the old tree.
        cap = 4 * timing["pin_cap_ff"]
        tcl = f'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_{corner.upper()}_*.lib*]] {{ read_liberty $f }}
read_verilog /route/6_final.v
link_design ot_hdc_v41_fh_ctx
read_sdc /out/boundary.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
set refs [get_pins -hierarchical {{u_fh.u_rh*/*CLK}}]
if {{[llength $refs] == 0}} {{ error "missing result-hold local clock leaf" }}
set ref [lindex $refs 0]
puts "FHBOUND reference [get_full_name $ref]"
set q [get_ports {{ra_q[*]}}]
if {{[llength $q] != 2048}} {{ error "not full G4W16" }}
set_input_delay -min {timing['clk_to_q_ps']:.9f} -clock core_clk -reference_pin $ref $q
set_input_delay -max {timing['clk_to_q_ps']:.9f} -clock core_clk -reference_pin $ref $q
set_input_transition {timing['out_slew_intrinsic_ps']:.9f} $q
set a [get_ports {{ra_addr[*] ra_re[*]}}]
set_load {cap:.9f} $a
set_output_delay -max {timing['setup_ps']:.9f} -clock core_clk -reference_pin $ref $a
set_output_delay -min {-timing['hold_ps']:.9f} -clock core_clk -reference_pin $ref $a
report_units
puts "FHBOUND input_setup"
report_checks -from $q -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND input_hold"
report_checks -from $q -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND address_setup"
report_checks -to $a -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND address_hold"
report_checks -to $a -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND checks"
report_check_types -max_slew -max_capacitance -violators
puts "FHBOUND end"
'''
        (out / f"{corner}.tcl").write_text(tcl)
        command = ["docker", "run", "--rm", "-e", "OMP_NUM_THREADS=16", "-v", f"{ROOT}:/src:ro",
                   "-v", f"{base}:/route:ro", "-v", f"{out}:/out",
                   "openroad/orfs:latest", "bash", "-lc",
                   f"source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
                   f"sta -exit /out/{corner}.tcl"]
        proc = subprocess.run(command, capture_output=True, text=True)
        log = proc.stdout + proc.stderr
        (out / f"{corner}.log").write_text(log)
        paths = {}
        parts = re.split(r"FHBOUND (input_setup|input_hold|address_setup|address_hold|checks)\n", log)
        for i in range(1, len(parts)-1, 2):
            name, body = parts[i], parts[i+1]
            m = re.search(r"(-?[\d.]+)\s+slack \((?:MET|VIOLATED)\)", body)
            if name != "checks":
                paths[name] = float(m.group(1)) if m else None
        valid = proc.returncode == 0 and len(paths) == 4 and all(v is not None for v in paths.values())
        record["corners"][corner] = dict(exit=proc.returncode, paths_slack_ps=paths,
            valid=valid, boundary_met=valid and all(v >= 0 for v in paths.values()),
            macro_lib_sha256=digest(lib), macro_nominal_clkq_ps=timing["clk_to_q_ps"],
            address_and_ce_load_ff=cap, unrouted_macro_clock_load_ff=16*timing["clk_cap_ff"],
            capture_relation="same local reference leaf, zero additional SRAM clock skew; unresolved parent CTS",
            macro_output_driver="corner macro nominal clkQ and intrinsic slew; optimistic unloaded source",
            unresolved_macro_output_load="Macro output resistance/load delay is absent; a passing screen cannot qualify this boundary",
            macro_constraint_reference="nominal macro setup/hold; parent input/clock slew tables remain unresolved")
        print(json.dumps({corner: record["corners"][corner]}), flush=True)
    record["valid"] = all(c["valid"] for c in record["corners"].values())
    record["verdict"] = ("EVALUATOR_FAILED" if not record["valid"] else
        "CONDITIONAL_BOUNDARY_PASS" if all(c["boundary_met"] for c in record["corners"].values())
        else "BOUNDARY_NOT_CLOSED")
    record["original_unchanged"] = record["original_sha256"] == {p.name: digest(p) for p in inputs}
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    if not record["valid"] or not record["original_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
