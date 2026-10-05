#!/usr/bin/env python3
"""Re-run or collect the bounded, registered-ROM Qwen INT8 shard route."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUTS = (
    "physical/qwen_o4_int8_shard/ot_qwen_o4_int8_shard.sv",
    "physical/qwen_o4_int8_shard/constraint.sdc",
    "physical/qwen_o4_int8_shard/synth.ys",
    "physical/qwen_o4_int8_shard/place_route.tcl",
    "physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8_tt.lib",
    "rtl/hdc/ot_hdc_qwen_int8_arith.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "tools/qwen_o4_int8_shard_pipeline_physical.py",
)
ARTIFACTS = pathlib.Path("results/physical_hdc/asap7/qwen_o4_int8_shard_pipeline/artifacts")


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(work: pathlib.Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    for name in ("synth.ys", "place_route.tcl"):
        source = (ROOT / "physical/qwen_o4_int8_shard" / name).read_text()
        source = source.replace("/tmp/opentallas-qwen-o4-physical-lane", str(ROOT))
        source = source.replace("/tmp/qwen-o4-shard-route", str(work))
        (work / name).write_text(source)
    sta = f"""set root {ROOT}
set work {work}
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {{ if {{![string match *FAKE* $lib]}} {{ read_liberty $lib }} }}
read_liberty $root/physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8_tt.lib
read_db $work/grt.odb
read_sdc $root/physical/qwen_o4_int8_shard/constraint.sdc
source $platform/setRC.tcl
estimate_parasitics -global_routing
set pins [get_pins -hierarchical u_weight_rom/rd_out*]
puts "ROM_OUT_PINS [llength $pins]"
report_checks -from $pins -path_delay max
"""
    (work / "macro_sta.tcl").write_text(sta)


def run(work: pathlib.Path) -> None:
    yosys = "/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys"
    with (work / "synth.log").open("w") as log:
        subprocess.run([yosys, "-s", str(work / "synth.ys")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    mapped = work / "mapped.v"
    mapped.write_text(mapped.read_text().replace("wire signed ", "wire "))
    with (work / "place_route.log").open("w") as log:
        subprocess.run(["openroad", "-exit", str(work / "place_route.tcl")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    with (work / "macro_sta.log").open("w") as log:
        subprocess.run(["openroad", "-exit", str(work / "macro_sta.tcl")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)


def collect(work: pathlib.Path) -> None:
    place = (work / "place_route.log").read_text()
    macro = (work / "macro_sta.log").read_text()
    if "POST_GRT_SETUP" not in place or "ROM_OUT_PINS 266" not in macro:
        raise RuntimeError("global route or macro STA did not complete")
    grt = place.split("POST_GRT_SETUP", 1)[1].split("POST_GRT_HOLD", 1)[0]
    grt_slack = re.findall(r"([-\d.]+)\s+slack \((?:VIOLATED|MET)\)", grt)
    macro_slack = re.findall(r"([-\d.]+)\s+slack \((?:VIOLATED|MET)\)", macro)
    if not grt_slack or not macro_slack:
        raise RuntimeError("STA slack not found")
    inst = re.search(r"NumInstances:\s+(\d+)", place)
    std_area = re.search(r"StdInstsArea:\s+([\d.]+)", place)
    if not inst or not std_area:
        raise RuntimeError("placed instance count or standard-cell area not found")
    output = ROOT / ARTIFACTS
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name in ("synth.log", "mapped.v", "place_route.log", "macro_sta.log"):
        dest = output / f"{name}.gz"
        with gzip.open(dest, "wb", compresslevel=9) as f:
            f.write((work / name).read_bytes())
        artifacts[str(dest.relative_to(ROOT))] = sha(dest)
    record = {
        "schema": "qwen-o4-int8-registered-rom-shard-grt/1",
        "scope": "one analytical 266-bit ROM, 32 INT8 lanes, ROM-output register; not full G6144 tile or token",
        "target_clock_ns": 0.92,
        "placed_instances": int(inst.group(1)),
        "standard_cell_area_um2_before_cts": float(std_area.group(1)),
        "source_hashes_sha256": {name: sha(ROOT / name) for name in INPUTS},
        "artifact_hashes_sha256": artifacts,
        "stages": {"synthesis": "PASS", "placement": "PASS", "clock_tree": "PASS", "global_route": "PASS", "detailed_route": "NOT_RUN"},
        "global_route_worst_setup_slack_ps": float(grt_slack[-1]),
        "rom_output_to_capture_slack_ps": float(macro_slack[-1]),
        "limitations": ["analytical ROM compiler timing/current", "no full reduction tree or die route", "no DRC or extracted post-route timing"],
    }
    dest = ROOT / "results/physical_hdc/asap7/qwen_o4_int8_shard_pipeline/global_route.json"
    dest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"record": str(dest.relative_to(ROOT)), "worst_slack_ps": record["global_route_worst_setup_slack_ps"], "rom_slack_ps": record["rom_output_to_capture_slack_ps"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=pathlib.Path, default=pathlib.Path("/tmp/qwen-o4-shard-pipeline-route"))
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()
    prepare(args.workdir)
    if not args.collect_only:
        run(args.workdir)
    collect(args.workdir)


if __name__ == "__main__":
    main()
