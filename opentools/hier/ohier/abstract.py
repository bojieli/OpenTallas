"""Partition abstracts: collect + check the LEF and ETM of each routed partition.

The abstract itself is made by ORFS `generate_abstract` on the routed partition
(OpenROAD `write_abstract_lef` + OpenSTA `write_timing_model`), see
scripts/orfs_flow.sh.  This module reads both views back and checks them against
the plan:
  * LEF SIZE == the partition rectangle (the top floorplan slot);
  * LEF pins == ETM pins == the partition's ports in the plan;
  * every ETM input has a setup/hold check or a combinational arc, every output a
    clock->out or combinational arc (unconstrained ports are listed, not failed:
    tie-offs and feed-through-free ports are legal);
  * the partition's own clock insertion (ETM min/max_clock_tree_path) is written into
    the shared plan as macros[u_<module>].clock_pins[clk].insertion_ps, which is what
    the clock tools (clkplan / MSCTS) balance against.
"""
from __future__ import annotations

import re


POWER = {"VDD", "VSS", "VPWR", "VGND", "VDDPE", "VDDCE"}   # supply pins (LEF PIN / macro ETM pg pins)


def parse_etm(text):
    """-> dict(cell, pins{name: dir}, clock_tree{min, max} (ps, max of rise/fall), arcs{pin: [types]})"""
    cell = re.search(r'cell\s*\(\s*"?([^")\s]+)"?\s*\)', text)
    out = {"cell": cell.group(1) if cell else None, "pins": {}, "arcs": {}, "clock_tree": {}}
    # split per pin( ... ) block at depth 2 inside the cell
    for m in re.finditer(r'\bpin\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text):
        name = m.group(1)
        i, depth = m.end(), 1
        while depth and i < len(text):
            c = text[i]
            depth += (c == "{") - (c == "}")
            i += 1
        body = text[m.end():i]
        d = re.search(r"direction\s*:\s*(\w+)", body)
        out["pins"][name] = d.group(1) if d else None
        types = re.findall(r"timing_type\s*:\s*(\w+)", body)
        out["arcs"][name] = types
        for kind in ("min", "max"):
            vals = []
            for blk in re.finditer(r"timing_type\s*:\s*%s_clock_tree_path\s*;(.*?)(?=timing\s*\(|\Z)" % kind, body, re.S):
                vals += [float(v) for v in re.findall(r'values\s*\(\s*"([-\d.eE]+)"', blk.group(1))]
            if vals:
                out["clock_tree"].setdefault(name, {})[kind] = max(vals) if kind == "max" else min(vals)
    return out


def parse_lef(text):
    """-> dict(name, size(w, h), pins[])"""
    m = re.search(r"^\s*MACRO\s+(\S+)", text, re.M)
    s = re.search(r"^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text, re.M)
    pins = re.findall(r"^\s*PIN\s+(\S+)", text, re.M)
    return {"name": m.group(1) if m else None, "size": (float(s.group(1)), float(s.group(2))) if s else None,
            "pins": pins}


def _port_bits(ports):
    """plan port names (bus[i] or scalar) -> LEF/ETM pin names (ORFS escapes '[i]' -> '_i_')."""
    return {re.sub(r"\[(\d+)\]", r"_\1_", p) for p in ports}


def check(region, lef_text, etm_text, ports, tol_um=0.01, clock="clk"):
    """region: hier-view region; ports: list of the partition's port bit names.
    -> dict(ok, problems[], insertion_ps{min,max}, unconstrained[])"""
    L, T = parse_lef(lef_text), parse_etm(etm_text)
    probs = []
    x0, y0, x1, y1 = region["bbox_um"]
    if L["size"] is None or abs(L["size"][0] - (x1 - x0)) > tol_um or abs(L["size"][1] - (y1 - y0)) > tol_um:
        probs.append(f"LEF SIZE {L['size']} != slot {(round(x1 - x0, 3), round(y1 - y0, 3))}")
    if L["name"] != region["module"] or T["cell"] != region["module"]:
        probs.append(f"names LEF {L['name']} / ETM {T['cell']} != {region['module']}")
    want = _port_bits(ports)
    lp, ep = set(L["pins"]) - POWER, set(T["pins"]) - POWER
    if lp != want:
        probs.append(f"LEF pins differ from plan ports: missing {sorted(want - lp)[:5]} extra {sorted(lp - want)[:5]}")
    if ep != want:
        probs.append(f"ETM pins differ from plan ports: missing {sorted(want - ep)[:5]} extra {sorted(ep - want)[:5]}")
    unconstrained = sorted(p for p in ep if p != clock and not T["arcs"].get(p)
                           and T["pins"][p] == "input")
    ins = T["clock_tree"].get(clock, {})
    if not ins:
        probs.append(f"ETM has no clock tree path on {clock}")
    return {"ok": not probs, "problems": probs, "insertion_ps": ins, "unconstrained_inputs": unconstrained,
            "n_pins": len(ep)}
