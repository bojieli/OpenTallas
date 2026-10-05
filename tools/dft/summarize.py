#!/usr/bin/env python3
"""Collect the DFT evidence into results/dft/summary.json.

Per block it reads, when present:
  results/dft/<block>/atpg.json                      (tools/dft/run_atpg.py)
  results/dft/<block>/equivalence.json               (tools/dft/check_scan_equivalence.py)
  results/physical_abi3/asap7/dft/<block>/noscan/physical.json
  results/physical_abi3/asap7/dft/<block>/scan/physical.json
and reports coverage, pattern counts and the scan overheads the paired routes
measure (same RTL, same 0.9 ns target, --false-path-io, --slew-margin-percent 20;
the only difference is --dft scan).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATPG = ROOT / "results/dft"
PHYS = ROOT / "results/physical_abi3/asap7/dft"

ARCH = {
    # block -> architectures it serves
    "stream": ["hbm_comparator", "qwen3_8b_rom"],
    "matvec": ["hbm_comparator", "qwen3_8b_rom"],
    "kv_stream": ["hbm_comparator"],
    "sinkhorn": ["v41_rom_array"],
    "pkg_ctrl": ["v41_rom_array"],
    "fabric_router": ["v41_rom_array"],
    "pkg_link": ["v41_rom_array"],
    "argmax_reduce": ["v41_rom_array"],
    "mcast_node": ["v41_rom_array"],
    "moe_dispatch": ["v41_rom_array"],
    "expert_port": ["v41_rom_array"],
    "tap": ["hbm_comparator", "qwen3_8b_rom", "v41_rom_array"],
}


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def _phys(rec):
    if not rec or "place_and_route" not in rec:
        return None
    m = rec["place_and_route"]["metrics"]
    out = {
        "status": rec["status"],
        "fmax_mhz": round(float(m["fmax_hz"]) / 1e6, 2) if m.get("fmax_hz") else None,
        "standard_cell_area_um2": m.get("standard_cell_area_um2"),
        "sequential_area_um2": m.get("sequential_area_um2"),
        "core_area_um2": m.get("core_area_um2"),
        "instance_count": m.get("instance_count") or m.get("cell_count"),
        "routed_wirelength_um": m.get("routed_wirelength_um"),
        "setup_wns_ns": m.get("setup_wns_ns"),
        "drc_errors": m.get("drc_errors"),
    }
    dft = rec["place_and_route"].get("dft")
    if dft:
        out["scan"] = {k: dft[k] for k in ("flops", "chain_count", "chain_length_max", "scan_cells",
                                           "scan_mux_cells", "lockup_latches", "cell_area_added_fraction")}
    return out


def _ratio(a, b):
    try:
        return round(float(a) / float(b) - 1.0, 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def main() -> int:
    blocks = sorted({p.name for p in ATPG.iterdir() if p.is_dir()} | ({p.name for p in PHYS.iterdir() if p.is_dir()} if PHYS.is_dir() else set()))
    rows = {}
    for b in blocks:
        atpg = _load(ATPG / b / "atpg.json")
        eq = _load(ATPG / b / "equivalence.json")
        ns = _phys(_load(PHYS / b / "noscan/physical.json"))
        sc = _phys(_load(PHYS / b / "scan/physical.json"))
        row = {"architectures": ARCH.get(b, [])}
        if atpg:
            row["atpg"] = {
                "top": atpg["top"],
                "scan_cells": atpg["scan"]["scan_cells"],
                "chains": atpg["scan"]["chains"],
                "max_chain_length": atpg["scan"]["max_chain_length"],
                "faults": atpg["faults_total"],
                "classes": atpg["classes"],
                "fault_coverage": atpg["fault_coverage"],
                "test_coverage": atpg["test_coverage"],
                "capture_patterns": atpg["patterns"]["capture"],
                "tester_cycles": atpg["patterns"]["tester_cycles"],
                "gate_level": {k: atpg["gate_level"][k] for k in (
                    "good_machine_patterns", "good_machine_mismatches", "capture_faults_injected",
                    "capture_faults_confirmed", "chain_faults_injected", "chain_faults_confirmed")}
                if atpg.get("gate_level") else None,
            }
        if eq:
            row["scan_off_equivalence"] = {k: eq[k] for k in ("proven", "equiv_cells", "unproven_cells")}
        if ns or sc:
            row["route"] = {"noscan": ns, "scan": sc}
            if ns and sc:
                row["route"]["overhead"] = {
                    "standard_cell_area": _ratio(sc["standard_cell_area_um2"], ns["standard_cell_area_um2"]),
                    "core_area": _ratio(sc["core_area_um2"], ns["core_area_um2"]),
                    "routed_wirelength": _ratio(sc["routed_wirelength_um"], ns["routed_wirelength_um"]),
                    "fmax": _ratio(sc["fmax_mhz"], ns["fmax_mhz"]),
                    "instances": _ratio(sc["instance_count"], ns["instance_count"]),
                }
        rows[b] = row
    out = {
        "schema": "opentallas.dft.summary.v1",
        "route_settings": "asap7, 0.9 ns target, --false-path-io, --slew-margin-percent 20, --stages pnr; "
                          "scan adds --dft scan --scan-max-length 1024",
        "blocks": rows,
    }
    (ATPG / "summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for b, r in rows.items():
        a = r.get("atpg") or {}
        o = (r.get("route") or {}).get("overhead") or {}
        print(f"{b:14s} FC={a.get('fault_coverage')} TC={a.get('test_coverage')} pat={a.get('capture_patterns')} "
              f"area={o.get('standard_cell_area')} wl={o.get('routed_wirelength')} fmax={o.get('fmax')}")
    return 0


# --------------------------------------------------------------------------
# Markdown tables for docs/DFT.md, every number annotated with its source
# --------------------------------------------------------------------------

SRC = "results/dft/summary.json"
LABEL = {
    "stream": "stream unit `ot_hdc_stream`",
    "matvec": "matrix engine `ot_hdc_matvec`",
    "kv_stream": "KV streamer `ot_hdc_kv_stream`",
    "sinkhorn": "Sinkhorn unit `ot_hdc_sinkhorn`",
    "pkg_ctrl": "package controller `ot_rom_pkg_ctrl`",
    "fabric_router": "fabric router `ot_rom_fabric_router`",
    "pkg_link": "package link `ot_rom_pkg_link`",
    "argmax_reduce": "argmax collective `ot_rom_argmax_reduce`",
    "mcast_node": "multicast node `ot_rom_mcast_node`",
    "moe_dispatch": "MoE dispatch `ot_rom_moe_dispatch`",
    "expert_port": "MoE expert port `ot_rom_moe_expert_port`",
    "tap": "JTAG TAP `ot_tap`",
}
ARCH_SHORT = {"hbm_comparator": "HBM", "qwen3_8b_rom": "Qwen3 ROM", "v41_rom_array": "V4.1 array"}


def _fig(value, path, name, scale=None, fmt="{:,}"):
    shown = fmt.format(value)
    sc = f' scale="{scale}"' if scale else ""
    plain = shown.replace(",", "").lstrip("+")
    return f'{shown} <!-- figure: {plain} src="{SRC}#{path}"{sc} name="{name}" -->'


def markdown() -> str:
    data = json.loads((ATPG / "summary.json").read_text())
    out = ["| Block | Architectures | Scan cells | Chains (longest) | Pin faults | Fault coverage | Test coverage | Patterns | Gate-level check | Scan off equivalent |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for b, r in data["blocks"].items():
        a = r.get("atpg")
        if not a:
            continue
        p = f"blocks.{b}.atpg"
        g = a.get("gate_level")
        if g:
            gl = (f"{g['good_machine_patterns']} patterns, {g['good_machine_mismatches']} mismatches; "
                  f"{g['capture_faults_confirmed'] + g['chain_faults_confirmed']}/"
                  f"{g['capture_faults_injected'] + g['chain_faults_injected']} injected faults seen")
        else:
            gl = "not run"
        eq = r.get("scan_off_equivalence")
        eqs = (f"proven ({eq['equiv_cells']:,} points)" if eq and eq["proven"] else ("not proven" if eq else "not run"))
        out.append(
            f"| {LABEL.get(b, b)} | {', '.join(ARCH_SHORT[x] for x in r['architectures'])} | "
            f"{_fig(a['scan_cells'], p + '.scan_cells', b + ' scan cells')} | "
            f"{a['chains']} ({a['max_chain_length']}) | "
            f"{_fig(a['faults'], p + '.faults', b + ' pin faults')} | "
            f"{_fig(round(100 * a['fault_coverage'], 2), p + '.fault_coverage', b + ' fault coverage %', 100, '{:.2f}')}% | "
            f"{_fig(round(100 * a['test_coverage'], 2), p + '.test_coverage', b + ' test coverage %', 100, '{:.2f}')}% | "
            f"{_fig(a['capture_patterns'], p + '.capture_patterns', b + ' patterns')} | {gl} | {eqs} |"
        )
    out.append("")
    out.append("| Block | Std-cell area, no scan → scan (µm²) | Area | Routed Fmax, no scan → scan (MHz) | Fmax | Routed wirelength | Status, no scan / scan |")
    out.append("|---|---|---|---|---|---|---|")
    for b, r in data["blocks"].items():
        rt = r.get("route") or {}
        o = rt.get("overhead")
        if not o:
            continue
        ns, sc = rt["noscan"], rt["scan"]
        p = f"blocks.{b}.route"
        out.append(
            f"| {LABEL.get(b, b)} | {ns['standard_cell_area_um2']:,} → {sc['standard_cell_area_um2']:,} | "
            f"{_fig(round(100 * o['standard_cell_area'], 1), p + '.overhead.standard_cell_area', b + ' scan area overhead %', 100, '{:+.1f}')}% | "
            f"{_fig(ns['fmax_mhz'], p + '.noscan.fmax_mhz', b + ' Fmax no scan', None, '{:,.1f}')} → "
            f"{_fig(sc['fmax_mhz'], p + '.scan.fmax_mhz', b + ' Fmax scan', None, '{:,.1f}')} | "
            f"{_fig(round(100 * o['fmax'], 1), p + '.overhead.fmax', b + ' scan Fmax change %', 100, '{:+.1f}')}% | "
            f"{_fig(round(100 * o['routed_wirelength'], 1), p + '.overhead.routed_wirelength', b + ' scan wirelength overhead %', 100, '{:+.1f}')}% | "
            f"{ns['status']} / {sc['status']} |"
        )
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--markdown":
        print(markdown())
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--write-doc":
        # regenerate the tables between the markers in docs/DFT.md
        main()
        doc = ROOT / "docs/DFT.md"
        text = doc.read_text()
        begin, end = "<!-- dft-tables:begin -->", "<!-- dft-tables:end -->"
        a, b = text.index(begin) + len(begin), text.index(end)
        doc.write_text(text[:a] + "\n" + markdown() + text[b:])
        raise SystemExit(0)
    raise SystemExit(main())
