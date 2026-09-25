#!/usr/bin/env python3
"""Harden one block into a macro with abstracts, against its timing budget.

Phases (each resumable; ORFS's make is incremental on a kept work dir):

  synth   ORFS synthesis, netlist normalisation, boundary characterisation
          (tools/chip_assembly/boundary.py) -> <work>/boundary.json
  pnr     the budgeted SDC (tools/chip_assembly/budgets.py) replaces the
          synthesis SDC, pins are placed on the edges the parent floorplan
          names, the die is fixed, the level-1 power grid is built, and the
          flow runs to ``finish`` then ``generate_abstract``: the LEF abstract
          (write_abstract_lef -bloat_occupied_layers) and the Liberty timing
          model (write_timing_model) of the routed, extracted block.

The block record (per-block timing against the budget, area, utilisation,
wirelength, abstract digests) goes to
``results/physical_abi3/asap7/chip/blocks/<block>.json``.

    python3 tools/chip_assembly/harden.py --block ot_hdc_matvec \
        --work /tmp/.../chipwork/ot_hdc_matvec --phase synth
    python3 tools/chip_assembly/harden.py --block ot_hdc_matvec \
        --work /tmp/.../chipwork/ot_hdc_matvec --phase pnr \
        --budget results/physical_abi3/asap7/chip/budgets/hdc_tile.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chip_assembly import boundary, case as cs, etm, floorplans as fp, orfs  # noqa: E402

RESULTS = orfs.ROOT / "results/physical_abi3/asap7/chip"
PERIOD_PS = fp.CLOCK_PERIOD_NS * 1000.0


def synth_sdc() -> str:
    """The synthesis-phase SDC: the clock, and the conventional 20% I/O."""
    return "\n".join([
        f"set clk_period {PERIOD_PS:g}",
        "create_clock -name clk -period $clk_period [get_ports clk]",
        "set non_clock_inputs [all_inputs -no_clocks]",
        "set_input_delay [expr $clk_period * 0.2] -clock clk $non_clock_inputs",
        "set_output_delay [expr $clk_period * 0.2] -clock clk [all_outputs]",
        "set_max_fanout 32 [current_design]",
        "",
    ])


def budget_sdc(block: str, budget: dict[str, Any]) -> str:
    """Per-port I/O delays from the budget table (no I/O false paths)."""
    entry = budget["blocks"][block]
    lines = [
        f"# Budgeted boundary constraints for {block} from {budget['name']}",
        f"# (tools/chip_assembly/budgets.py); period {PERIOD_PS:g} ps.",
        f"set clk_period {PERIOD_PS:g}",
        "create_clock -name clk -period $clk_period [get_ports clk]",
        f"set_clock_uncertainty {budget['uncertainty_ps']:g} [get_clocks clk]",
        "set_max_fanout 32 [current_design]",
        "set_max_transition 320 [current_design]",
        "set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y [all_inputs -no_clocks]",
        "set_false_path -from [get_ports rst_n]",
    ]
    for port, b in sorted(entry["ports"].items()):
        if port in ("clk", "rst_n"):
            continue
        if b["status"] == "static":
            sel = f"[get_ports {{{port}}}]" if b["width"] == 1 else f"[get_ports {{{port}[*]}}]"
            lines.append(f"set_false_path -from {sel}")
            continue
        sel = f"[get_ports {{{port}}}]" if b["width"] == 1 else f"[get_ports {{{port}[*]}}]"
        if b["direction"] == "input":
            lines.append(f"set_input_delay {b['external_ps']:.1f} -clock clk {sel}")
        else:
            lines.append(f"set_output_delay {b['external_ps']:.1f} -clock clk {sel}")
            lines.append(f"set_load {b.get('load_ff', 4.0):.1f} {sel}")
    lines += fp.BLOCKS[block].extra_sdc
    return "\n".join(lines) + "\n"


def pin_groups(block: fp.Block, ports: dict[str, Any]) -> list[dict[str, Any]]:
    by_edge: dict[str, list[str]] = {e: [] for e in ("W", "E", "N", "S")}
    for name in sorted(ports):
        p = ports[name]
        if p["width"] == 1:
            by_edge[fp.edge_of(block, name, None)].append(name)
        else:
            for bit in range(p["width"]):
                by_edge[fp.edge_of(block, name, bit)].append(f"{name}[{bit}]")
    return [{"edge": e, "names": n} for e, n in by_edge.items() if n]


def spec_for(block: fp.Block, sdc: str, ports: dict[str, Any] | None) -> cs.CaseSpec:
    return cs.CaseSpec(
        nickname=f"chip_{block.name}",
        top=block.name,
        sources=block.sources,
        die_um=(block.width_um, block.height_um),
        sdc=sdc,
        params=block.params,
        pin_groups=pin_groups(block, ports) if ports else [],
        pdn_tcl=cs.TCL_DIR / "pdn_block.tcl",
        max_layer="M6",
        place_density=block.place_density,
        extra={"SLEW_MARGIN": 20, "HOLD_SLACK_MARGIN": 5, "SETUP_SLACK_MARGIN": 0},
    )


def phase_synth(block: fp.Block, work: Path, timeout: int) -> dict[str, Any]:
    spec = spec_for(block, synth_sdc(), None)
    cs.write_case(work, spec)
    res = orfs.results_dir(work, spec.nickname)
    netlist = res / "1_2_yosys.v"
    if not netlist.is_file():
        with orfs.slot(f"synth {block.name}"):
            proc = orfs.docker_make(work, f"/work/results/asap7/{spec.nickname}/base/1_2_yosys.v",
                                    "synth.log", timeout)
        if proc.returncode != 0 or not netlist.is_file():
            raise orfs.FlowError(f"synthesis of {block.name} failed; see {work}/synth.log")
    stripped = orfs.normalise_netlist(netlist)
    char = boundary.characterise([netlist], block.name, work / "boundary", period_ps=PERIOD_PS)
    char["netlist_signed_stripped"] = stripped
    boundary.write(char, work / "boundary.json")
    out = RESULTS / "boundary" / f"{block.name}.json"
    boundary.write({**char, "netlists": [f"<work>/results/asap7/{spec.nickname}/base/1_2_yosys.v"],
                    "sources": orfs.source_digests(block.sources)}, out)
    return char


def flow_seconds(work: Path, nickname: str) -> float:
    """Wall time of the stages, from ORFS's per-stage logs."""
    total = 0.0
    for log in orfs.logs_dir(work, nickname).glob("*.log"):
        m = re.search(r"Elapsed time: (?:(\d+):)?(\d+):(\d+(?:\.\d+)?)", log.read_text(errors="replace"))
        if m:
            total += int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return total


def phase_pnr(block: fp.Block, work: Path, budget_path: Path, timeout: int,
              record_only: bool = False) -> dict[str, Any]:
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    char = json.loads((work / "boundary.json").read_text(encoding="utf-8"))
    spec = spec_for(block, budget_sdc(block.name, budget), char["ports"])
    if not record_only:
        cs.write_case(work, spec)
        cs.ensure_constraints(work, spec.nickname, spec.sdc)
    res = orfs.results_dir(work, spec.nickname)
    t0 = time.time()
    if not record_only:
        with orfs.slot(f"pnr {block.name}"):
            proc = orfs.docker_make(work, "finish metadata-generate", "flow.log", timeout)
            if proc.returncode != 0:
                raise orfs.FlowError(f"place-and-route of {block.name} failed; see {work}/flow.log")
            proc = orfs.docker_make(work, "generate_abstract", "abstract.log", 7200)
            if proc.returncode != 0:
                raise orfs.FlowError(f"abstract generation of {block.name} failed; see {work}/abstract.log")
    elapsed = flow_seconds(work, spec.nickname) if record_only else time.time() - t0
    lef, lib = res / f"{block.name}.lef", res / f"{block.name}_typ.lib"
    views = RESULTS / "abstracts" / block.name
    views.mkdir(parents=True, exist_ok=True)
    for f in (lef, lib):
        (views / f.name).write_bytes(f.read_bytes())
    m = cs.metrics(work, spec.nickname)
    record = block_record(block, spec, budget, budget_path, m, lef, lib, work, elapsed)
    out = RESULTS / "blocks" / f"{block.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def budget_check(block: str, budget: dict[str, Any], lib: Path) -> dict[str, Any]:
    """Each budgeted port's routed internal delay (the extracted timing model)
    against its budget."""
    model = etm.read(lib)
    rows, over = {}, []
    for port, b in sorted(budget["blocks"][block]["ports"].items()):
        if b["status"] in ("static", "untimed") or port == "rst_n":
            continue
        m = model.get(port, {})
        actual = m.get("setup_ps") if b["direction"] == "input" else m.get("clk_to_out_ps")
        through = max(m.get("through", {}).values(), default=None) if b["direction"] == "output" else None
        within = actual is None or actual <= b["internal_budget_ps"] + 0.05
        rows[port] = {"budget_ps": b["internal_budget_ps"], "routed_ps": None if actual is None else round(actual, 1),
                      "through_ps": None if through is None else round(through, 1), "within_budget": within}
        if not within:
            over.append(port)
    return {"ports": rows, "over_budget": over,
            "basis": ("routed delay from the block's write_timing_model liberty: an input's worst setup "
                      "constraint (pin to register, setup included), an output's worst clock-to-output")}


def block_record(block, spec, budget, budget_path, m, lef, lib, work, elapsed) -> dict[str, Any]:
    closed = (
        m.get("setup_wns_ps") is not None and m["setup_wns_ps"] >= 0
        and (m.get("hold_wns_ps") or 0) >= 0
        and not m.get("drc_errors") and not m.get("max_slew_violations")
        and not m.get("max_cap_violations") and not m.get("max_fanout_violations")
    )
    return {
        "schema": "opentallas-chip-block-v1",
        "block": block.name,
        "budget": {"table": str(budget_path.relative_to(orfs.ROOT)), "name": budget["name"]},
        "clock_period_ns": fp.CLOCK_PERIOD_NS,
        "die_um": [block.width_um, block.height_um],
        "constraints": ("budgeted per-port set_input_delay / set_output_delay (no I/O false "
                        "paths), clock uncertainty from the budget, max transition 320 ps"),
        "metrics": m,
        "closed_against_budget": closed,
        "budget_check": budget_check(block.name, budget, lib),
        "closed_basis": ("setup and hold met with the budgeted I/O constraints, zero DRC, zero "
                         "max-slew / max-cap / max-fanout violations"),
        "abstract": {
            "lef": {"path": f"results/physical_abi3/asap7/chip/abstracts/{block.name}/{lef.name}",
                    "sha256": orfs.sha256_file(lef)},
            "liberty": {"path": f"results/physical_abi3/asap7/chip/abstracts/{block.name}/{lib.name}",
                        "sha256": orfs.sha256_file(lib)},
            "basis": "ORFS generate_abstract: write_abstract_lef -bloat_occupied_layers and "
                     "write_timing_model on 6_final.odb with its extracted SPEF",
        },
        "flat_record": block.record,
        "sources": orfs.source_digests(block.sources),
        "git": orfs.git_identity(),
        "toolchain": orfs.orfs_identity(),
        "elapsed_seconds": round(elapsed, 1),
        "work_dir": str(work),
        "notes": block.notes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--block", required=True, choices=sorted(fp.BLOCKS))
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--phase", required=True, choices=["synth", "pnr", "record"])
    ap.add_argument("--budget", type=Path)
    args = ap.parse_args(argv)
    timeout = int(os.environ.get("OT_FLOW_TIMEOUT_SECONDS", "86400"))
    block = fp.BLOCKS[args.block]
    if args.phase == "synth":
        char = phase_synth(block, args.work.resolve(), timeout)
        print(json.dumps({"block": block.name, "ports": len(char["ports"])}))
    else:
        if not args.budget:
            ap.error("--phase pnr / record needs --budget")
        rec = phase_pnr(block, args.work.resolve(), args.budget.resolve(), timeout,
                        record_only=args.phase == "record")
        print(json.dumps({"block": block.name, "closed": rec["closed_against_budget"],
                          "setup_wns_ps": rec["metrics"].get("setup_wns_ps")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
