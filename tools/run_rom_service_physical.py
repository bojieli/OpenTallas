#!/usr/bin/env python3
"""Synthesise, place and route the ROM read service in IHP SG13G2.

WHY THIS EXISTS.  A synthesised cell area is an estimate; a routed area carries
the wires.  The ROM read path is the block that makes this architecture
different from a GPU, and until now it had neither.  This runs the whole open
flow -- yosys through OpenROAD floorplan, PDN, placement, clock tree, global
route and TritonRoute detailed route -- against the exact installed IHP Open PDK
v0.3.0 collateral and records what came out, including whether it converged.

WHAT IS ACTUALLY BEING ROUTED.  ``ot_rom_read_service`` is the addressing,
masking and repair-translation front end of the weight store.  It contains no
ROM array: the array sits behind the sense request/response interface, and in a
product it is a foundry macro.  So this establishes the cost of the *control*
that reads a mask ROM, not the cost of the mask ROM.

The tables it holds are register files here because that is the only storage
this open flow can build.  In a product the object and shard tables are a small
SRAM loaded at deployment admission, so the area below over-counts them, and by
how much is not established here either.

WHAT THIS IS NOT.  IHP SG13G2 is a 130-nm open foundry PDK.  Nothing here may be
scaled to N6, N5, N7 or N4 by any feature-size, gate-pitch or density ratio;
docs/OPEN_PDK_SELECTION.md forbids it and docs/METHODOLOGY.md section 9 makes it
a rule rather than a preference.  No number from this run enters the iso-node or
roofline comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/rtl/rom_service_physical.json"
PDK_ROOT = Path(
    os.environ.get("OPENTALLAS_PDK_ROOT", Path.home() / ".local/opentallas-pdk")
) / "ihp-open-pdk-v0.3.0/ihp-sg13g2"
YOSYS = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
) / "yosys-0.68/bin/yosys"

RTL_SOURCES = (
    "rtl/rom/ot_rom_pkg.sv",
    "rtl/rom/ot_rom_read_service.sv",
)
PDK_COLLATERAL = (
    "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
    "libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef",
    "libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib",
    "libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib",
)

RESULT_BEGIN = "=== RESULT BEGIN ==="
RESULT_END = "=== RESULT END ==="

SYNTH_TEMPLATE = """\
{reads}
hierarchy -top {top} {chparam}
synth -top {top} -flatten
dfflibmap -liberty {liberty}
abc -liberty {liberty}
hilomap -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO
splitnets
opt_clean -purge
tee -o {stat_json} stat -json -liberty {liberty}
write_verilog -noattr {netlist}
"""

PNR_TEMPLATE = r"""
read_lef {tech_lef}
read_lef {cell_lef}
read_liberty {liberty}
read_verilog {netlist}
link_design {top}

create_clock -name clk -period {period} [get_ports clk]
set data_inputs [get_ports {{{data_inputs}}}]
set_input_delay  [expr {period} * 0.30] -clock clk $data_inputs
set_output_delay [expr {period} * 0.30] -clock clk [all_outputs]
set_clock_uncertainty 0.25 clk
set_max_fanout 10 [current_design]
set_driving_cell -lib_cell sg13g2_buf_4 -pin X $data_inputs
set_load 0.006 [all_outputs]

initialize_floorplan -utilization {util} -aspect_ratio 1.0 -core_space 5.0 -site CoreSite
foreach layer {{Metal1 Metal2 Metal3 Metal4 Metal5}} {{
    make_tracks $layer -x_offset 0.0 -x_pitch 0.48 -y_offset 0.0 -y_pitch 0.42
}}
place_pins -hor_layers Metal3 -ver_layers Metal2

add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
set_voltage_domain -name {{CORE}} -power {{VDD}} -ground {{VSS}}
define_pdn_grid -name {{grid}} -voltage_domains {{CORE}}
add_pdn_stripe -grid {{grid}} -layer {{Metal1}} -width {{0.44}} -followpins
add_pdn_stripe -grid {{grid}} -layer {{Metal4}} -width {{1.0}} -pitch {{40.0}} -offset {{20.0}}
add_pdn_stripe -grid {{grid}} -layer {{Metal5}} -width {{1.6}} -pitch {{40.0}} -offset {{20.0}}
add_pdn_connect -grid {{grid}} -layers {{Metal1 Metal4}}
add_pdn_connect -grid {{grid}} -layers {{Metal4 Metal5}}
pdngen

global_placement -density {density}
estimate_parasitics -placement
repair_design
detailed_placement

clock_tree_synthesis -buf_list {{sg13g2_buf_8 sg13g2_buf_4 sg13g2_buf_2}} \
                     -root_buf sg13g2_buf_16 -sink_clustering_enable
set_propagated_clock [all_clocks]
estimate_parasitics -placement
repair_clock_nets
detailed_placement

set_thread_count {threads}
global_route -congestion_iterations 40
detailed_route -output_drc {drc} -droute_end_iter 12 -verbose 0

filler_placement {{sg13g2_fill_1 sg13g2_fill_2}}
check_placement
estimate_parasitics -global_routing

puts "{begin}"
report_design_area
puts "--- worst setup ---"
report_worst_slack -max
puts "--- worst hold ---"
report_worst_slack -min
puts "--- tns ---"
report_tns
puts "period_ns {period}"
set db [ord::get_db]
set block [[$db getChain] getBlock]
set die [$block getDieArea]
set core [$block getCoreArea]
set dbu [$block getDefUnits]
puts "die_um [expr [$die dx]*1.0/$dbu] [expr [$die dy]*1.0/$dbu]"
puts "core_um [expr [$core dx]*1.0/$dbu] [expr [$core dy]*1.0/$dbu]"
puts "instances [llength [$block getInsts]]"
puts "nets [llength [$block getNets]]"
puts "{end}"

write_def {routed_def}
exit
"""

DATA_INPUTS = (
    "rst_n cfg_valid cfg_sel* cfg_index* cfg_data* "
    "req_valid req_object_id* req_byte_offset* req_byte_length* req_tag* "
    "sense_req_ready sense_rsp_valid sense_rsp_data* out_ready"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(text: str) -> str:
    return text.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def parse_results(log: str) -> dict[str, Any]:
    if RESULT_BEGIN not in log:
        return {}
    body = log.split(RESULT_BEGIN, 1)[1].split(RESULT_END, 1)[0]
    out: dict[str, Any] = {"raw": body.strip()}
    area = re.search(r"Design area (\S+) u\^2 (\S+)% utilization", body)
    if area:
        out["design_area_um2"] = float(area.group(1))
        out["utilization_percent"] = float(area.group(2))
    slacks = re.findall(r"^(-?\d+\.\d+)\s*$", body, re.MULTILINE)
    if len(slacks) >= 2:
        out["worst_setup_slack_ns"] = float(slacks[0])
        out["worst_hold_slack_ns"] = float(slacks[1])
    if len(slacks) >= 3:
        out["total_negative_slack_ns"] = float(slacks[2])
    for key, pattern in (
        ("period_ns", r"period_ns (\S+)"),
        ("instances", r"instances (\d+)"),
        ("nets", r"nets (\d+)"),
    ):
        match = re.search(pattern, body)
        if match:
            out[key] = (
                float(match.group(1)) if "." in match.group(1) else int(match.group(1))
            )
    for key, pattern in (
        ("die_um", r"die_um (\S+) (\S+)"),
        ("core_um", r"core_um (\S+) (\S+)"),
    ):
        match = re.search(pattern, body)
        if match:
            out[key] = [float(match.group(1)), float(match.group(2))]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--top", default="ot_rom_read_service")
    parser.add_argument("--period-ns", type=float, default=10.0)
    parser.add_argument("--utilization", type=float, default=30.0)
    parser.add_argument("--density", type=float, default=0.55)
    parser.add_argument("--threads", type=int, default=8)
    # The instance that is routed.  The shipped Qwen plan needs 16 objects, 14
    # shards, 14 regions and 14 resources; the DeepSeek wafer plan needs 312,
    # 9,527, 228 and 9,300.  This flow routes an instance sized for the Qwen
    # chip and says so, because an instance sized for the wafer would be a
    # ten-megabit register file that this open flow cannot build and that a
    # product would not build either.
    parser.add_argument("--objects", type=int, default=16)
    parser.add_argument("--shards", type=int, default=16)
    parser.add_argument("--regions", type=int, default=16)
    parser.add_argument("--resources", type=int, default=16)
    parser.add_argument("--repair-entries", type=int, default=8)
    parser.add_argument("--keep", default="")
    args = parser.parse_args()

    if not PDK_ROOT.exists():
        raise SystemExit(f"IHP PDK not found at {PDK_ROOT}")
    if not YOSYS.exists():
        raise SystemExit(f"pinned yosys not found at {YOSYS}")
    openroad = Path(shutil.which("openroad") or "/usr/bin/openroad")
    if not openroad.exists():
        raise SystemExit("openroad is not installed")

    liberty = PDK_ROOT / "libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
    tech_lef = PDK_ROOT / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"
    cell_lef = PDK_ROOT / "libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef"

    keep = Path(args.keep) if args.keep else None
    context = tempfile.TemporaryDirectory(prefix="romsvc-phys-")
    work = Path(keep) if keep else Path(context.name)
    work.mkdir(parents=True, exist_ok=True)

    instance = {
        "OBJECTS": args.objects,
        "SHARDS": args.shards,
        "REGIONS": args.regions,
        "RESOURCES": args.resources,
        "REPAIR_ENTRIES": args.repair_entries,
    }
    chparam = " ".join(f"-chparam {name} {value}" for name, value in instance.items())

    netlist = work / f"{args.top}_netlist.v"
    stat_json = work / "yosys_stat.json"
    reads = "\n".join(
        f"read_verilog -sv -DSYNTHESIS {ROOT / rel}" for rel in RTL_SOURCES
    )
    synth_script = work / "synth.ys"
    synth_script.write_text(
        SYNTH_TEMPLATE.format(
            reads=reads,
            top=args.top,
            chparam=chparam,
            liberty=liberty,
            stat_json=stat_json,
            netlist=netlist,
        )
    )
    synth = subprocess.run(
        [str(YOSYS), "-q", str(synth_script)],
        capture_output=True,
        text=True,
        check=False,
    )

    drc = work / f"{args.top}.drc"
    routed_def = work / f"{args.top}_routed.def"
    pnr_script = work / "pnr.tcl"
    pnr_script.write_text(
        PNR_TEMPLATE.format(
            tech_lef=tech_lef,
            cell_lef=cell_lef,
            liberty=liberty,
            netlist=netlist,
            top=args.top,
            period=args.period_ns,
            data_inputs=DATA_INPUTS,
            util=args.utilization,
            density=args.density,
            threads=args.threads,
            drc=drc,
            routed_def=routed_def,
            begin=RESULT_BEGIN,
            end=RESULT_END,
        )
    )
    pnr = subprocess.run(
        [str(openroad), "-exit", str(pnr_script)],
        capture_output=True,
        text=True,
        check=False,
    )
    log = pnr.stdout + pnr.stderr

    drc_violations = None
    if drc.exists():
        text = drc.read_text()
        drc_violations = text.count("violation type:")

    yosys_stat: dict[str, Any] = {}
    if stat_json.exists():
        try:
            raw = json.loads(stat_json.read_text())
            modules = raw.get("modules", {})
            top = modules.get(f"\\{args.top}") or next(iter(modules.values()), {})
            yosys_stat = {
                "cells": top.get("num_cells"),
                "cell_area_um2": top.get("area"),
                "sequential_cells": top.get("num_cells_by_type", {}).get(
                    "sg13g2_dfrbpq_1"
                ),
            }
        except (json.JSONDecodeError, StopIteration):
            yosys_stat = {}

    results = parse_results(log)
    converged = (
        pnr.returncode == 0
        and bool(results)
        and routed_def.exists()
        and drc_violations == 0
    )

    artifact = {
        "schema": "opentallas.rtl.rom_service_physical.v1",
        "campaign": "rom_read_service_physical",
        "status": "pass" if converged else "fail",
        "evidence_class": "open_foundry_pdk_digital_implementation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "top": args.top,
            "sources": list(RTL_SOURCES),
            "routed_instance": instance,
            "instance_note": (
                "sized for the shipped Qwen single-chip ROM plan (16 ROM "
                "objects, 14 shards, 14 regions, 14 banks). The DeepSeek wafer "
                "plan needs 312 objects, 9,527 shards, 228 regions and 9,300 "
                "resources; an instance that held those tables in flip-flops is "
                "not what a product would build and is not routed here"
            ),
            "yosys_statistics": yosys_stat,
        },
        "flow": {
            "platform": "ihp-sg13g2",
            "node_nm": 130,
            "corner": "typ_1p20V_25C",
            "target_clock_period_ns": args.period_ns,
            "floorplan_utilization_percent": args.utilization,
            "global_placement_density": args.density,
            "maximum_routing_layer": "Metal5",
            "steps": [
                "yosys synth + dfflibmap + abc + hilomap",
                "openroad initialize_floorplan + make_tracks + place_pins",
                "openroad pdngen (Metal1 followpins, Metal4/Metal5 straps)",
                "openroad global_placement + repair_design + detailed_placement",
                "openroad clock_tree_synthesis + repair_clock_nets",
                "openroad global_route + detailed_route (TritonRoute)",
                "openroad filler_placement + check_placement",
            ],
        },
        "toolchain": {
            "yosys": {
                "executable": scrub(str(YOSYS)),
                "executable_sha256": sha256(YOSYS),
                "version": subprocess.run(
                    [str(YOSYS), "-V"], capture_output=True, text=True, check=False
                ).stdout.strip(),
            },
            "openroad": {
                "executable": scrub(str(openroad)),
                "executable_sha256": sha256(openroad),
                "version": subprocess.run(
                    [str(openroad), "-version"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip(),
            },
        },
        "pdk_collateral_sha256": {rel: sha256(PDK_ROOT / rel) for rel in PDK_COLLATERAL},
        "synthesis": {
            "returncode": synth.returncode,
            "log": scrub((synth.stdout + synth.stderr).strip()[-4000:]),
            "command": scrub(shlex.join([str(YOSYS), "-q", str(synth_script)])),
        },
        "implementation": {
            "returncode": pnr.returncode,
            "command": scrub(shlex.join([str(openroad), "-exit", str(pnr_script)])),
            "log_tail": scrub(log.strip()[-8000:]),
            "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
            "detailed_route_drc_violations": drc_violations,
            "routed_def_written": routed_def.exists(),
        },
        "metrics": results,
        "source_sha256": {
            rel: sha256(ROOT / rel)
            for rel in RTL_SOURCES + ("tools/run_rom_service_physical.py",)
        },
        "claim_boundary": {
            "open_pdk_rtl_to_routed_feasibility": converged,
            "routed_not_only_synthesised": converged,
            "contains_rom_array_or_macro": False,
            "rom_cell_area_or_density": False,
            "rom_read_energy_or_sense_margin": False,
            "target_node_area_or_delay": False,
            "tables_are_flip_flops_not_an_sram_macro": True,
            "signoff_drc_or_lvs": False,
            "foundry_drc": False,
            "gds_generated": False,
            "activity_derived_power": False,
            "feature_size_scaling_permitted": False,
            "enters_iso_node_or_roofline_comparison": False,
        },
        "limitations": [
            "IHP SG13G2 is a 130-nm open foundry PDK. Neither the area nor the "
            "timing here may be scaled to N6, N5, N7 or N4 by any feature-size, "
            "gate-pitch or density ratio; docs/METHODOLOGY.md section 9 makes "
            "that a rule.",
            "The routed block is the ROM read service, which contains no ROM "
            "array. The array is behind the sense request/response interface "
            "and in a product is a foundry macro. This says nothing about ROM "
            "cell area, read energy or sense margin.",
            "The object, shard and repair tables are flip-flops here because "
            "that is the only storage this open flow can build. A product would "
            "hold them in a small SRAM loaded at admission, so this area "
            "over-counts them by an amount this run does not establish.",
            "The clock period is a constraint chosen for this run, not a "
            "characterised maximum frequency.",
            "No parasitic-extracted (SPEF) timing, no signoff DRC against a "
            "foundry deck, no LVS, no GDS, no activity-derived power.",
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n")
    print(f"{artifact['status']}: {output}")
    if results:
        print(json.dumps({k: v for k, v in results.items() if k != "raw"}, indent=1))
    if not converged:
        print(scrub(log.strip()[-2000:]))
    return 0 if converged else 1


if __name__ == "__main__":
    raise SystemExit(main())
