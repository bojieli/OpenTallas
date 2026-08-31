#!/usr/bin/env python3
"""Synthesise, place and route the ABI 3.0 inter-chip endpoint in IHP SG13G2.

WHY THIS EXISTS.  A synthesised cell area is an estimate; a routed area carries
the wires.  The endpoint that `runtime/cycle/fabric.py` and
`src/opentallas/roofline.py` charge a traversal to had neither, so this runs the
whole open flow -- yosys to OpenROAD floorplan, PDN, placement, clock tree,
global route and TritonRoute detailed route -- against the exact installed IHP
Open PDK v0.3.0 collateral and records what came out, including whether it
converged.

WHAT THIS IS NOT.  IHP SG13G2 is a 130-nm open foundry PDK.  Nothing here may be
scaled to N6, N5, N7 or N4 by any feature-size, gate-pitch or density ratio;
`docs/OPEN_PDK_SELECTION.md` forbids it and `docs/METHODOLOGY.md` section 9
makes it a rule rather than a preference.  This run establishes that the
endpoint is implementable and what it costs in an open 130-nm library.  It says
nothing about a leading-node endpoint's area, delay, energy, or about the
seconds a hop takes on any node.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_link_physical.json"
PDK_ROOT = Path(
    os.environ.get(
        "OPENTALLAS_PDK_ROOT", Path.home() / ".local/opentallas-pdk"
    )
) / "ihp-open-pdk-v0.3.0/ihp-sg13g2"
YOSYS = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
) / "yosys-0.68/bin/yosys"

#: Sources per implementable top.  The endpoint is the block the routed flow
#: targets; the node is the whole thing a mesh position holds, and is offered
#: synthesis-only because its receive bank is flip-flop based and a routed run
#: of it would be an area claim this program is not entitled to make.
SOURCES_BY_TOP = {
    "ot_a3_link_endpoint": (
        "rtl/lib/ot_crc_pkg.sv",
        "rtl/abi3/ot_a3_link_pkg.sv",
        "rtl/abi3/ot_a3_link_channel.sv",
        "rtl/abi3/ot_a3_link_endpoint.sv",
    ),
    "ot_a3_mesh_router": (
        "rtl/lib/ot_crc_pkg.sv",
        "rtl/abi3/ot_a3_link_pkg.sv",
        "rtl/abi3/ot_a3_mesh_router.sv",
    ),
    "ot_a3_link_node": (
        "rtl/lib/ot_crc_pkg.sv",
        "rtl/ot_fp32_rne_pkg.sv",
        "rtl/abi3/ot_a3_link_pkg.sv",
        "rtl/abi3/ot_a3_link_channel.sv",
        "rtl/abi3/ot_a3_mesh_router.sv",
        "rtl/abi3/ot_a3_collective_engine.sv",
        "rtl/abi3/ot_a3_link_node.sv",
    ),
}
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
# `synth -top` runs hierarchy itself.  A separate `hierarchy -top` pass
# cannot be used here because `chparam` renames the top to a
# `$paramod$<hash>\\<name>` derivation and the explicit pass then fails to
# find the original name -- which is how the whole-node statistics came
# back empty, with the failure visible only because the parser now says so.
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
puts "--- worst setup path ---"
report_checks -path_delay max -group_count 4 -digits 3
set block [ord::get_db_block]
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
    "rst_n tx_in_valid tx_in_flit* tx_r_ack tx_r_ack_seq* tx_r_credit* "
    "tx_r_nak tx_r_nak_seq* rx_w_valid rx_w_flit* rx_w_seq* rx_w_crc* "
    "rx_out_ready inject_crc_error"
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
    # OpenROAD's report_worst_slack prints "worst slack <value>" with no max/min
    # word, so the section marker is what distinguishes setup from hold.  An
    # earlier revision matched "worst slack max" and silently found nothing,
    # which left `worst_setup_slack_ns` absent -- and absent read as "not
    # closed" for the wrong reason.  A missing measurement must be visible.
    sections = {}
    current = None
    for line in body.splitlines():
        marker = re.match(r"^---\s*(.+?)\s*---$", line.strip())
        if marker:
            current = marker.group(1)
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    def slack_of(name: str):
        for line in sections.get(name, []):
            match = re.search(r"worst slack\s+(-?[\d.]+)", line)
            if match:
                return float(match.group(1))
        return None

    out["worst_setup_slack_ns"] = slack_of("worst setup")
    out["worst_hold_slack_ns"] = slack_of("worst hold")
    tns = re.search(r"tns\s+(-?[\d.]+)", body)
    if tns:
        out["total_negative_slack_ns"] = float(tns.group(1))
    # Keep the whole report: the first path OpenROAD prints belongs to the
    # asynchronous group and is not the failing one, so a cap that cuts before
    # the clocked group would archive the wrong path under the right name.
    out["worst_setup_path"] = "\n".join(
        sections.get("worst setup path", [])
    ).strip()[:20000]
    if out["worst_setup_slack_ns"] is None or out["worst_hold_slack_ns"] is None:
        out["slack_parse_failed"] = True

    for key, pattern in (
        ("period_ns", r"period_ns (\S+)"),
        ("instances", r"instances (\d+)"),
        ("nets", r"nets (\d+)"),
    ):
        match = re.search(pattern, body)
        if match:
            out[key] = float(match.group(1)) if "." in match.group(1) else int(
                match.group(1)
            )
    for key, pattern in (("die_um", r"die_um (\S+) (\S+)"),
                         ("core_um", r"core_um (\S+) (\S+)")):
        match = re.search(pattern, body)
        if match:
            out[key] = [float(match.group(1)), float(match.group(2))]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--top", default="ot_a3_link_endpoint")
    parser.add_argument("--period-ns", type=float, default=10.0)
    parser.add_argument("--utilization", type=float, default=35.0)
    parser.add_argument("--density", type=float, default=0.60)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--keep", default="", help="directory to keep artifacts in")
    parser.add_argument(
        "--synth-only", action="store_true",
        help="record synthesis only; the artifact then claims no routed result",
    )
    parser.add_argument(
        "--chparam", action="append", default=[],
        help="NAME=VALUE parameter override applied to the top before synthesis",
    )
    args = parser.parse_args()
    sources = SOURCES_BY_TOP.get(args.top)
    if sources is None:
        raise SystemExit(f"no source list registered for top {args.top}")

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
    context = tempfile.TemporaryDirectory(prefix="a3link-phys-")
    work = Path(keep) if keep else Path(context.name)
    work.mkdir(parents=True, exist_ok=True)

    netlist = work / f"{args.top}_netlist.v"
    stat_json = work / "yosys_stat.json"
    reads = "\n".join(
        f"read_verilog -sv -DSYNTHESIS {ROOT / rel}" for rel in sources
    )
    if args.chparam:
        sets = " ".join(
            f"-set {item.split('=', 1)[0]} {item.split('=', 1)[1]}"
            for item in args.chparam
        )
        reads += f"\nchparam {sets} {args.top}"
    synth_script = work / "synth.ys"
    synth_script.write_text(
        SYNTH_TEMPLATE.format(
            reads=reads, top=args.top, liberty=liberty,
            stat_json=stat_json, netlist=netlist,
        )
    )
    synth = subprocess.run(
        [str(YOSYS), "-q", str(synth_script)],
        capture_output=True, text=True, check=False,
    )

    drc = work / f"{args.top}.drc"
    routed_def = work / f"{args.top}_routed.def"
    pnr_script = work / "pnr.tcl"
    pnr_script.write_text(
        PNR_TEMPLATE.format(
            tech_lef=tech_lef, cell_lef=cell_lef, liberty=liberty,
            netlist=netlist, top=args.top, period=args.period_ns,
            data_inputs=DATA_INPUTS, util=args.utilization,
            density=args.density, threads=args.threads, drc=drc,
            routed_def=routed_def, begin=RESULT_BEGIN, end=RESULT_END,
        )
    )
    if args.synth_only:
        pnr = subprocess.CompletedProcess([], 0, "", "")
        log = ""
    else:
        pnr = subprocess.run(
            [str(openroad), "-exit", str(pnr_script)],
            capture_output=True, text=True, check=False,
        )
        log = pnr.stdout + pnr.stderr

    drc_violations = None
    if drc.exists():
        text = drc.read_text()
        match = re.search(r"violation type:", text)
        drc_violations = text.count("violation type:") if match else 0

    # `tee -o` writes yosys' log text around the JSON, and `chparam` renames the
    # top to a `$paramod$<hash>\\<name>` derivation.  Both were enough to make an
    # earlier revision record an EMPTY statistics block with no error -- a
    # missing measurement that read as a present one.  Parse from the first
    # brace, pick the module with the most cells, and say so when it fails.
    yosys_stat: dict[str, Any] = {}
    if stat_json.exists():
        text = stat_json.read_text()
        brace = text.find("{")
        if brace >= 0:
            try:
                raw = json.loads(text[brace:])
            except json.JSONDecodeError as exc:
                yosys_stat = {"parse_error": str(exc)}
                raw = None
            if raw is not None:
                modules = raw.get("modules", {})
                chosen = None
                for name, module in modules.items():
                    if args.top not in name:
                        continue
                    if chosen is None or (module.get("num_cells") or 0) > (
                        chosen[1].get("num_cells") or 0
                    ):
                        chosen = (name, module)
                if chosen is None and modules:
                    chosen = max(
                        modules.items(),
                        key=lambda item: item[1].get("num_cells") or 0,
                    )
                if chosen is None:
                    yosys_stat = {"parse_error": "no module in yosys statistics"}
                else:
                    name, module = chosen
                    yosys_stat = {
                        "module": name,
                        "cells": module.get("num_cells"),
                        "cell_area_um2": module.get("area"),
                        "sequential_cells": module.get("num_cells_by_type", {}).get(
                            "sg13g2_dfrbpq_1"
                        ),
                    }
        else:
            yosys_stat = {"parse_error": "no JSON object in yosys statistics"}
    else:
        yosys_stat = {"parse_error": "yosys wrote no statistics file"}

    results = parse_results(log)
    routed = (
        (not args.synth_only) and pnr.returncode == 0 and bool(results)
        and routed_def.exists() and (drc_violations == 0)
    )
    setup = results.get("worst_setup_slack_ns")
    hold = results.get("worst_hold_slack_ns")
    timing_closed = (
        setup is not None and hold is not None and setup >= 0.0 and hold >= 0.0
    )
    converged = routed and timing_closed
    if args.synth_only:
        status = "synthesis_only"
    elif converged:
        status = "pass"
    elif routed:
        # A clean route that misses its constraint is a result, not a failure to
        # report as one. Naming it separately is the point: the block is
        # implementable and the constraint is not met, and those are different
        # facts.
        status = "routed_timing_not_closed"
    else:
        status = "fail"

    artifact = {
        "schema": "opentallas.rtl.a3_link_physical.v1",
        "campaign": "rtl3_a3_link_endpoint_physical",
        "status": status,
        "evidence_class": "open_foundry_pdk_digital_implementation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design": {
            "top": args.top,
            "sources": list(sources),
            "parameter_overrides": list(args.chparam),
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
                    [str(openroad), "-version"], capture_output=True, text=True,
                    check=False,
                ).stdout.strip(),
            },
        },
        "pdk_collateral_sha256": {
            rel: sha256(PDK_ROOT / rel) for rel in PDK_COLLATERAL
        },
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
            "routed": routed,
            "timing_closed_at_target_period": timing_closed,
        },
        "metrics": results,
        "source_sha256": {
            rel: sha256(ROOT / rel)
            for rel in sources + ("tools/run_a3_link_physical.py",)
        },
        "claim_boundary": {
            "open_pdk_rtl_to_routed_feasibility": routed,
            "routed_not_only_synthesised": routed,
            "timing_closed_at_target_period": timing_closed,
            "target_node_area_or_delay": False,
            "establishes_hop_latency_s": False,
            "measures_reticle_boundary_delay": False,
            "contains_rom_or_sram_macro": False,
            "signoff_drc_or_lvs": False,
            "foundry_drc": False,
            "gds_generated": False,
            "activity_derived_power": False,
            "feature_size_scaling_permitted": False,
        },
        "limitations": [
            "IHP SG13G2 is a 130-nm open foundry PDK. Neither the area nor the "
            "timing here may be scaled to N6, N5, N7 or N4 by any feature-size, "
            "gate-pitch, or density ratio. docs/METHODOLOGY.md section 9 makes "
            "that a rule.",
            "The block is the endpoint of ONE directed hop: sender with credit "
            "window, CRC32C and bounded replay, plus receiver. It contains no "
            "collective engine, no router, no ROM and no SRAM macro; its "
            "buffers are standard-cell flip-flops.",
            "The clock period is a constraint chosen for this run, not a "
            "characterised maximum frequency. A closed period says the tool met "
            "the constraint, not that the block cannot go faster or that it "
            "would at any other node.",
            "No parasitic-extracted (SPEF) timing, no signoff DRC against a "
            "foundry deck, no LVS, no GDS, and no activity-derived power.",
            "Nothing here measures the wire between two endpoints, which is "
            "where a hop's latency actually lives.",
        ],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n")
    print(f"{artifact['status']}: {output}")
    if args.synth_only:
        return 0
    if not routed:
        print(scrub(log.strip()[-1500:]))
    return 0 if routed else 1


if __name__ == "__main__":
    raise SystemExit(main())
