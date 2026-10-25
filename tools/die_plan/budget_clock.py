#!/usr/bin/env python3
"""Explicit local-clock contracts for pure die-prototype budget stand-ins.

The die clock drives the partition's first clock-buffer input, rather than all
boundary DFFs directly. This is a budget model, never a hardened clock tree.
Actual partition views are rejected. Existing inputs are never changed.
"""
import argparse
import json
import math
from pathlib import Path
import re
import shutil

import die_sta

CELL = "OT_BUDGET_LOCAL_CLOCK"
FLOP = "DFFHQNx1_ASAP7_75t_R"
FF = re.compile(r"^\s*" + FLOP + r" f\d+ \(\.CLK\((\w+)\), \.D\(([^)]+)\), \.QN\(([^)]+)\)\);\s*$")
HOLD = re.compile(r"^\s*OT_BHOLD_\d+p\d h\d+ \(\.A\(([^)]+)\), \.Y\(d\d+\)\);\s*$")


def convert(text):
    """Only the deliberately minimal standin_netlist grammar is accepted."""
    if CELL in text:
        raise ValueError("local-clock contract already present")
    clocks, lines, count = set(), text.splitlines(), 0
    for line in lines:
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        m = FF.fullmatch(line)
        if m:
            clock, data, output = m.groups()
            if not re.fullmatch(r"clk(?:_t\d+|_c\d+)?", clock):
                raise ValueError("stand-in flop does not use a declared tap")
            if not (data == "1'b0" or re.fullmatch(r"(?:d\d+|\w+\[\d+\])", data)):
                raise ValueError("non-budget data expression")
            clocks.add(clock)
            count += 1
        elif HOLD.fullmatch(line):
            continue
        elif not re.match(r"(?:module\s|input\s|output\s|wire\s|endmodule\b)", s):
            raise ValueError("not a pure budget stand-in: " + s[:100])
    if not count:
        raise ValueError("no budget face flops")
    declared = set(re.findall(r"^\s*input (clk(?:_t\d+|_c\d+)?);\s*$", text, re.M))
    if not clocks <= declared:
        raise ValueError("undeclared clock tap")
    # Keep the original 3-fF load even at an unused tap, matching die_clock.py.
    inserted = []
    for i, clock in enumerate(sorted(declared)):
        inserted += [f"  wire budget_ck_{i};", f"  {CELL} budget_clock_{i} (.A({clock}), .Y(budget_ck_{i}));"]
        text = text.replace(f".CLK({clock})", f".CLK(budget_ck_{i})")
    end = text.rfind("endmodule")
    text = text[:end] + "\n".join(inserted) + "\n" + text[end:]
    return "// BUDGET ONLY: explicit local clock insertion/load, no physical clock closure.\n" + text, dict(
        flops=count, clock_ports=len(declared), used_clock_ports=len(clocks))


def liberty(insertion_ps, load_ff=3.0, transition_ps=10.0):
    for value in (insertion_ps, load_ff, transition_ps):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("positive finite clock contract required")
    # Reuse the scalar Liberty boilerplate and exact time/capacitance units of
    # the already explicit boundary-hold contract. No ASAP7 cell is modified.
    old = die_sta.bhold_cell(insertion_ps)
    result = die_sta.bhold_lib([old]).replace(old, CELL)
    result = result.replace("library (ot_boundary_hold)", "library (ot_budget_local_clock)")
    result = result.replace("capacitance : 0.5;", f"capacitance : {load_ff:g};")
    result = result.replace("max_capacitance : 1000;", "max_capacitance : 1000000;")
    for kind in ("rise_transition", "fall_transition"):
        result = result.replace(f'{kind} (scalar) {{ values ("{die_sta.BHOLD_SLEW_PS:g}"); }}',
                                f'{kind} (scalar) {{ values ("{transition_ps:g}"); }}')
    return result


def prepare(parts, out, tt_ps, ff_ps, load_ff=3.0):
    parts, out = Path(parts), Path(out)
    if out.exists():
        raise ValueError("refuse to overwrite output")
    prepared = []
    for netlist in sorted(parts.glob("*/6_final.v")):
        if (netlist.parent / "6_final.spef").exists():
            raise ValueError("routed views cannot use a budget local-clock contract")
        text, census = convert(netlist.read_text())
        prepared.append((netlist, text, census))
    if not prepared:
        raise ValueError("no stand-in parts")
    libs = {corner: liberty(delay, load_ff) for corner, delay in (("TT", tt_ps), ("FF", ff_ps))}
    out.mkdir(parents=True)
    for netlist, text, census in prepared:
        dest = out / "parts" / netlist.parent.name
        dest.mkdir(parents=True)
        (dest / "6_final.v").write_text(text)
        if (netlist.parent / "6_final.sdc").exists():
            shutil.copyfile(netlist.parent / "6_final.sdc", dest / "6_final.sdc")
    for corner, lib in libs.items():
        (out / f"local_clock_{corner}.lib").write_text(lib)
    record = dict(scope="budget stand-ins only; not G3/G4 physical closure", source=str(parts.resolve()),
                  load_ff=load_ff, insertion_ps=dict(TT=tt_ps, FF=ff_ps),
                  parts={v.parent.name: c for v, _, c in prepared})
    (out / "contract.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts")
    parser.add_argument("--out", required=True)
    parser.add_argument("--tt-ps", type=float, required=True)
    parser.add_argument("--ff-ps", type=float, required=True)
    parser.add_argument("--load-ff", type=float, default=3.0)
    args = parser.parse_args()
    print(json.dumps(prepare(args.parts, args.out, args.tt_ps, args.ff_ps, args.load_ff), indent=2))
