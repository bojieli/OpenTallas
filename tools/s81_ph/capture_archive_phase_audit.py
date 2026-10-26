#!/usr/bin/env python3
"""Measure the archived, immutable capture route at compensated clock phases.

Input directory contains archive_manifest.json, insertion.json and base/6_final.*.
The files must hash to the CLOSED archive manifest. No route is rebuilt, no
internal path exception is added, and the receipt does not adopt a parent.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    stage = args.directory.resolve()
    manifest = json.loads((stage / "archive_manifest.json").read_text())
    ins = json.loads((stage / "insertion.json").read_text())
    base = stage / "base"
    expected = {Path(f["path"]).name: f["sha256"] for f in manifest["files"]
                if "/6_final." in f["path"]}
    hashes = {n: sha(base / n) for n in ("6_final.odb", "6_final.sdc", "6_final.spef")}
    for n, h in hashes.items():
        if h != expected[n]:
            raise ValueError("archive file changed: " + n)
    paths = []
    scripts = {}
    for corner in ("tt", "ff", "ss"):
        R = {p: ins["clock_measurements"][p + "[0]"][corner]["boundary"]["mean"] for p in ("ck", "ckv")}
        script = r'''
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_@C@*] {read_liberty $l}
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_@C@_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_@C@_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
create_clock -name ser_clk -period 1111.110667 [get_ports {ckv[0]}]
set_clock_uncertainty -setup 60 [get_clocks {core_clk ser_clk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk ser_clk}]
set_propagated_clock [all_clocks]
set_clock_latency -source @CR@ [get_clocks core_clk]
set_clock_latency -source @SR@ [get_clocks ser_clk]
report_clock_properties [all_clocks]
foreach pin {ck[0] ckv[0]} {
 foreach prop {slew_max_rise slew_min_rise} {
  puts "OT_CAPTURE_ROOT_SLEW $pin $prop [get_property [get_ports $pin] $prop]"
 }
}
foreach pair {{core_clk core_clk core core} {ser_clk ser_clk serial serial} {core_clk ser_clk core serial} {ser_clk core_clk serial core}} {
 lassign $pair launch capture a b
 foreach sense {max min} {
  set starts [all_registers -clock_pins -clock [get_clocks $launch]]
  set ends [all_registers -data_pins -clock [get_clocks $capture]]
  set found [find_timing_paths -from $starts -to $ends -path_delay $sense -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
  if {![llength $found]} {error "missing actual path $launch/$capture/$sense"}
  set p [lindex $found 0]
  puts "OT_CAPTURE_ARCHIVE_PHASE {\"corner\":\"@CORNER@\",\"launch\":\"$a\",\"capture\":\"$b\",\"sense\":\"$sense\",\"startpoint\":\"[get_full_name [get_property $p startpoint]]\",\"endpoint\":\"[get_full_name [get_property $p endpoint]]\",\"slack_ps\":[get_property $p slack]}"
  report_checks -from $starts -to $ends -path_delay $sense -format full_clock_expanded -fields {slew capacitance fanout} -group_path_count 1 -endpoint_path_count 1
 }
}
report_checks -path_delay min -format full_clock_expanded -group_path_count 3
exit
'''
        for k, v in {"@C@": corner.upper(), "@CORNER@": corner, "@CR@": -R["ck"], "@SR@": -R["ckv"]}.items():
            script = script.replace(k, str(v))
        tcl = stage / (corner + ".tcl")
        tcl.write_text(script)
        cmd = ["docker", "run", "--rm", "-v", str(base) + ":/base:ro", "-v", str(stage) + ":/audit:ro",
               "openroad/orfs:latest", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad",
               "-no_init", "-exit", "/audit/" + tcl.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        log = stage / (corner + ".log")
        log.write_text(result.stdout + result.stderr)
        print("CORNER", corner, "rc", result.returncode, flush=True)
        if result.returncode:
            raise RuntimeError(str(log))
        current = [json.loads(line.removeprefix("OT_CAPTURE_ARCHIVE_PHASE ")) for line in result.stdout.splitlines()
                   if line.startswith("OT_CAPTURE_ARCHIVE_PHASE ")]
        if len(current) != 8:
            raise ValueError("missing actual domain-pair paths")
        paths.extend(current)
        scripts[corner] = {"tcl_sha256": sha(tcl), "log_sha256": sha(log)}
        for p in current:
            print("PHASE", corner, p["launch"], p["capture"], p["sense"], p["slack_ps"], flush=True)
    receipt = dict(schema="opentallas.capture.archived_phase_diagnostic.v1", job=manifest["job"],
                   source_commit=manifest["commit"], archive_manifest_sha256=sha(stage / "archive_manifest.json"),
                   routed_sha256=hashes, insertion_sha256=sha(stage / "insertion.json"),
                   phase="pin_source_latency_minus_boundary_R", parasitics="spef", paths=paths,
                   period_ps=dict(core=833.333, serial=1111.110667), setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                   scripts=scripts, parent_adopted=False,
                   note="Actual archived route. Parent pin binding, source compatibility and die seams remain required.")
    (stage / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
