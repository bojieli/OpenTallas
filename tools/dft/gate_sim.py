"""Gate-level confirmation of scan patterns.

The ATPG engine works on its own primitive model.  This module checks its
answers on the *netlist itself*, in an event-driven Verilog simulator (Icarus),
with cell models generated from the Liberty functions:

* every cell input pin is buffered inside its model (``<pin>__i``), so a
  stuck-at on one pin of one cell is a ``force`` on that buffer and leaves the
  net's other branches alone; an output-pin fault is a ``force`` on the port;
* the bench applies each pattern the way a tester does -- shift the load
  through ``scan_in`` with ``scan_en`` = 1 (one clock per bit, all chains in
  parallel, the previous pattern's response coming out of ``scan_out`` at the
  same time), set the primary inputs, compare the primary outputs, pulse one
  capture clock with ``scan_en`` = 0, and compare the unload;
* the load and unload bit streams are derived from the scan description --
  chain order and the inversion each link and cell applies -- not from the
  ATPG model, so a wrong chain would show up as a mismatch.

Three checks are run: the good machine over a sample of the patterns (zero
mismatches expected), every sampled detected fault injected with its
detecting pattern (a mismatch expected for each), and a sample of the faults
credited to the chain test injected during a flush (a mismatch expected).
"""

from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dft import liberty as lib  # type: ignore
    from dft import netlist as nl  # type: ignore
    from dft.scan_insert import sequential_role  # type: ignore
else:
    from . import liberty as lib
    from . import netlist as nl
    from .scan_insert import sequential_role


# --------------------------------------------------------------------------
# cell models
# --------------------------------------------------------------------------


def cell_model(name: str, cell: dict[str, Any]) -> str:
    ins = [p for p, i in cell["pins"].items() if i["direction"] == "input"]
    outs = [p for p, i in cell["pins"].items() if i["direction"] == "output"]
    ports = ", ".join(ins + outs)
    lines = [f"module {name} ({ports});"]
    for p in ins:
        lines.append(f"  input {p};")
        lines.append(f"  wire {p}__i;")
        lines.append(f"  assign {p}__i = {p};")
    for p in outs:
        lines.append(f"  output {p};")
    rename = {p: f"{p}__i" for p in ins}
    ff, latch = cell.get("ff"), cell.get("latch")
    if ff:
        role = sequential_role(cell)
        v0 = ff["vars"][0]
        lines.append(f"  reg {v0};")
        if len(ff["vars"]) > 1:
            lines.append(f"  wire {ff['vars'][1]} = ~{v0};")
            rename[ff["vars"][1]] = ff["vars"][1]
        edge = "posedge" if role["edge"] == "pos" else "negedge"
        clk = f"{role['clock_pin']}__i"
        ns = lib.to_verilog(role["next_state"], rename)
        sens = [f"{edge} {clk}"]
        body = []
        clr = pre = None
        if "clear" in ff:
            lines.append(f"  wire clr__w = {lib.to_verilog(lib.parse_function(ff['clear']), rename)};")
            sens.append("posedge clr__w")
            clr = True
        if "preset" in ff:
            lines.append(f"  wire pre__w = {lib.to_verilog(lib.parse_function(ff['preset']), rename)};")
            sens.append("posedge pre__w")
            pre = True
        if clr:
            body.append(f"if (clr__w) {v0} <= 1'b0;")
        if pre:
            body.append(("else " if body else "") + f"if (pre__w) {v0} <= 1'b1;")
        body.append(("else " if body else "") + f"{v0} <= {ns};")
        lines.append(f"  always @({' or '.join(sens)}) begin " + " ".join(body) + " end")
    elif latch:
        v0 = latch["vars"][0]
        lines.append(f"  reg {v0};")
        if len(latch["vars"]) > 1:
            lines.append(f"  wire {latch['vars'][1]} = ~{v0};")
        en = lib.to_verilog(lib.parse_function(latch["enable"]), rename)
        d = lib.to_verilog(lib.parse_function(latch["data_in"]), rename)
        lines.append(f"  always @* if ({en}) {v0} = {d};")
    for p in outs:
        func = cell["pins"][p]["function"]
        if func is None:
            lines.append(f"  assign {p} = 1'bx;")
        else:
            lines.append(f"  assign {p} = {lib.to_verilog(lib.parse_function(func), rename)};")
    lines.append("endmodule")
    return "\n".join(lines)


def write_cell_models(cells: dict[str, dict[str, Any]], used: set[str], path: Path) -> None:
    body = ["`timescale 1ns/1ps", "// generated from Liberty by tools/dft/gate_sim.py"]
    for name in sorted(used):
        body.append(cell_model(name, cells[name]))
    path.write_text("\n".join(body) + "\n")


# --------------------------------------------------------------------------
# scan stream derivation
# --------------------------------------------------------------------------


def chain_polarities(scan: dict[str, Any], cells: dict[str, dict[str, Any]]) -> list[list[int]]:
    """cum[c][k]: state of cell k after a load = (bit shifted in for it) ^ cum."""
    out = []
    for chain in scan["chains"]:
        cum = []
        acc = 0
        prev_outinv = 0
        for k, cellrec in enumerate(chain["cells"]):
            cell = cells[cellrec["cell"]]
            role = sequential_role(cell)
            env = {p: 0 for p in role["data_pins"]}
            if cellrec["kind"] == "scan_cell":
                env["SE"] = 1
                env["SI"] = 0
                v0 = lib.evaluate(role["next_state"], env)
                env["SI"] = 1
                v1 = lib.evaluate(role["next_state"], env)
            else:
                # the multiplexer passes SI unchanged onto the data pin
                dpins = [p for p in role["data_pins"] if p not in role["async"]]
                for a, meta in role["async"].items():
                    env[a] = meta["inactive_value"]
                env[dpins[0]] = 0
                v0 = lib.evaluate(role["next_state"], env)
                env[dpins[0]] = 1
                v1 = lib.evaluate(role["next_state"], env)
            if v0 == v1:
                raise ValueError(f"{cellrec['instance']}: shift does not depend on SI")
            si_inv = v0  # next = SI ^ si_inv
            acc ^= (prev_outinv if k else 0) ^ si_inv
            cum.append(acc)
            prev_outinv = 1 if cellrec["output_inverted"] else 0
        out.append(cum)
    return out


def _bits_to_hex(bits: list[int]) -> str:
    """MSB-first bit list to a hex string of ceil(len/4) digits."""
    n = len(bits)
    pad = (-n) % 4
    b = [0] * pad + bits
    return "".join(f"{(b[i] << 3) | (b[i + 1] << 2) | (b[i + 2] << 1) | b[i + 3]:x}" for i in range(0, len(b), 4))


def read_patterns(path: Path) -> tuple[list[list[int]], list[list[int]]]:
    lines = path.read_text().splitlines()
    head = lines[0].split()
    n_src, n_obs = int(head[3]), int(head[5])

    def unhex(text: str, n: int) -> list[int]:
        bits = []
        for ch in text:
            v = int(ch, 16)
            bits.extend([(v >> b) & 1 for b in range(4)])
        return bits[:n]

    srcs, obs = [], []
    for line in lines[1:]:
        a, b = line.split()
        srcs.append(unhex(a, n_src))
        obs.append(unhex(b, n_obs))
    return srcs, obs


# --------------------------------------------------------------------------
# bench
# --------------------------------------------------------------------------


def _hier(inst: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", inst):
        return inst
    return "\\" + inst + " "


def build_bench(
    work: Path,
    netlist: Path,
    scan: dict[str, Any],
    names: dict[str, Any],
    cells: dict[str, dict[str, Any]],
    patterns: list[int],
    srcs: list[list[int]],
    obs: list[list[int]],
    faults: list[dict[str, Any]],
    top: str,
) -> Path:
    """Write tb.v and data files into work/; faults: [{inst, pin, value, pattern|None, output}]."""
    mod = nl.read_module(netlist, top)
    used = {i.cell for i in mod.instances}
    write_cell_models(cells, used, work / "cells.v")
    shutil.copy2(netlist, work / "dut.v")

    ports = scan["ports"]
    clocks = sorted({c["clock"] for ch in scan["chains"] for c in ch["cells"]})
    cum = chain_polarities(scan, cells)
    chains = scan["chains"]
    L = max(len(ch["cells"]) for ch in chains)
    C = len(chains)
    pi_names = names["pi"]
    ppi_index = {n: i for i, n in enumerate(names["ppi"])}
    n_pi, n_po = len(pi_names), len(names["po"])
    n_ppi = len(names["ppi"])
    ppo_index = {n: i for i, n in enumerate(names["ppo"])}

    drive = [b for b in pi_names if b not in clocks]
    # per-pattern streams
    load_lines, unload_lines, mask_lines, pi_lines, po_lines = [], [], [], [], []
    for p in patterns:
        src, ob = srcs[p], obs[p]
        pivals = {b: src[i] for i, b in enumerate(pi_names)}
        pi_lines.append(_bits_to_hex([pivals[b] for b in drive]))
        po_lines.append(_bits_to_hex(ob[:n_po]))
        for c, ch in enumerate(chains):
            n = len(ch["cells"])
            load = [0] * L         # index = shift cycle
            unload = [0] * L
            mask = [0] * L
            for k, cellrec in enumerate(ch["cells"]):
                want = src[n_pi + ppi_index[cellrec["instance"]]]
                load[L - 1 - k] = want ^ cum[c][k]
                captured = ob[n_po + ppo_index[cellrec["instance"]]]
                t = n - 1 - k
                outinv = 1 if ch["cells"][-1]["output_inverted"] else 0
                unload[t] = captured ^ cum[c][n - 1] ^ cum[c][k] ^ outinv
                mask[t] = 1
            # bit t of the vector is shift cycle t: write MSB-first as reversed list
            load_lines.append(_bits_to_hex(load[::-1]))
            unload_lines.append(_bits_to_hex(unload[::-1]))
            mask_lines.append(_bits_to_hex(mask[::-1]))
    for name, data in (("load", load_lines), ("unload", unload_lines), ("mask", mask_lines),
                       ("pi", pi_lines), ("po", po_lines)):
        (work / f"{name}.hex").write_text("\n".join(data) + "\n")

    # fault list for injection (pattern numbers are local to this bench)
    local = {g: i for i, g in enumerate(patterns)}
    inject = []
    for f in faults:
        target = f"dut.{_hier(f['inst'])}.{f['pin']}" + ("" if f["output"] else "__i")
        inject.append((target, f["value"], None if f["pattern"] is None else local[f["pattern"]]))
    flush_len = [len(ch["cells"]) for ch in chains]
    flush_inv = [cum[c][-1] ^ (1 if ch["cells"][-1]["output_inverted"] else 0) for c, ch in enumerate(chains)]

    in_ports = [p for p in mod.ports if mod.port_dirs.get(p) == "input"]
    out_ports = [p for p in mod.ports if mod.port_dirs.get(p) == "output"]

    def decl(p: str, kind: str) -> str:
        rng = mod.ranges.get(p)
        width = f"[{rng[0]}:{rng[1]}] " if rng else ""
        return f"  {kind} {width}{nl.verilog_name('tbs_' + p)};"

    def spell(bit: str) -> str:
        m = re.fullmatch(r"(.*)\[(\d+)\]", bit)
        if m and mod.ranges.get(m.group(1)) is not None:
            return nl.verilog_name('tbs_' + m.group(1)).rstrip() + f"[{m.group(2)}]"
        return nl.verilog_name('tbs_' + bit)

    se = ports["scan_enable"]
    lines = ["`timescale 1ns/1ps", "module tb;"]
    for p in in_ports:
        lines.append(decl(p, "reg"))
    for p in out_ports:
        lines.append(decl(p, "wire"))
    conns = ", ".join(f".{nl.verilog_name(p).rstrip()}({nl.verilog_name('tbs_' + p).rstrip()} )" for p in mod.ports)
    lines.append(f"  {nl.verilog_name(top)} dut ({conns});")
    P = len(patterns)
    npi = len(drive)
    lines += [
        f"  localparam integer P = {P}, C = {C}, L = {L}, NPI = {max(npi,1)}, NPO = {max(n_po,1)};",
        f"  reg [L-1:0] load_m [0:{max(P * C - 1, 0)}];",
        f"  reg [L-1:0] unload_m [0:{max(P * C - 1, 0)}];",
        f"  reg [L-1:0] mask_m [0:{max(P * C - 1, 0)}];",
        f"  reg [NPI-1:0] pi_m [0:{max(P - 1, 0)}];",
        f"  reg [NPO-1:0] po_m [0:{max(P - 1, 0)}];",
        "  wire [NPO-1:0] po_now = {" + ", ".join(spell(b) for b in names["po"]) + "};" if n_po else "  wire [0:0] po_now = 1'b0;",
        "  integer p, t, c, mism, total_mism, f;",
        "  task pulse; begin",
    ]
    for clk in clocks:
        lines.append(f"    {spell(clk)} = 1'b1;")
    lines.append("    #5;")
    for clk in clocks:
        lines.append(f"    {spell(clk)} = 1'b0;")
    lines += ["    #5;", "  end endtask"]
    # apply pi vector (excluding clocks)
    lines.append("  task apply_pi(input integer pp); begin")
    if npi:
        lines.append("    {" + ", ".join(spell(b) for b in drive) + "} = pi_m[pp];")
    for b, v in scan["capture_constraints"].items():
        lines.append(f"    {spell(b)} = 1'b{v};")
    lines.append("  end endtask")
    # one scan shift phase: load pattern `ld` (or none), compare unload of `ul` (or none)
    lines.append("  task shift_phase(input integer ld, input integer ul); begin")
    for b, v in scan["shift_constraints"].items():
        lines.append(f"    {spell(b)} = 1'b{v};")
    lines.append("    for (t = 0; t < L; t = t + 1) begin")
    for c in range(C):
        sin = spell(f"{ports['scan_in']}[{c}]")
        sout = spell(f"{ports['scan_out']}[{c}]")
        lines.append(f"      {sin} = (ld >= 0) ? load_m[ld*C+{c}][t] : 1'b0;")
        lines.append("      #1;")
        lines.append(
            f"      if (ul >= 0 && mask_m[ul*C+{c}][t] && {sout} !== unload_m[ul*C+{c}][t]) mism = mism + 1;"
        )
    lines.append("      pulse;")
    lines.append("    end")
    lines.append("  end endtask")
    # chain flush: 0011... through every chain for 2L+2 cycles, no capture
    lines.append("  task flush; begin")
    for b, v in scan["shift_constraints"].items():
        lines.append(f"    {spell(b)} = 1'b{v};")
    lines.append("    for (t = 0; t < 2 * L + 2; t = t + 1) begin")   # same length as otatpg --flush
    for c in range(C):
        sin = spell(f"{ports['scan_in']}[{c}]")
        sout = spell(f"{ports['scan_out']}[{c}]")
        lines.append(f"      {sin} = (t >> 1) & 1;")
        lines.append("      #1;")
        lines.append(
            f"      if (t >= {flush_len[c]} && {sout} !== ((((t - {flush_len[c]}) >> 1) & 1) ^ {flush_inv[c]})) mism = mism + 1;"
        )
    lines.append("      pulse;")
    lines.append("    end")
    lines.append("  end endtask")
    lines.append("  task capture(input integer pp); begin")
    lines.append("    apply_pi(pp);")
    lines.append("    #2;")
    lines.append("    if (po_now !== po_m[pp]) mism = mism + 1;")
    lines.append("    pulse;")
    lines.append("  end endtask")
    lines.append("  initial begin")
    for p_ in in_ports:
        lines.append(f"    {nl.verilog_name('tbs_' + p_).rstrip()} = 0;")
    lines += [
        '    $readmemh("load.hex", load_m);',
        '    $readmemh("unload.hex", unload_m);',
        '    $readmemh("mask.hex", mask_m);',
        '    $readmemh("pi.hex", pi_m);',
        '    $readmemh("po.hex", po_m);',
        "    total_mism = 0;",
        "    // good machine: every pattern, loads overlapped with the previous unload",
        "    mism = 0;",
        "    flush;",
        '    $display("FLUSH good mismatches %0d", mism);',
        "    total_mism = mism;",
        "    mism = 0;",
        "    shift_phase(0, -1);",
        "    for (p = 0; p < P; p = p + 1) begin",
        "      capture(p);",
        "      shift_phase((p + 1 < P) ? p + 1 : -1, p);",
        "      if (mism) begin $display(\"GOOD_MISMATCH pattern %0d count %0d\", p, mism); total_mism = total_mism + mism; mism = 0; end",
        "    end",
        '    $display("GOOD patterns %0d mismatches %0d", P, total_mism);',
    ]
    for k, (target, value, pat) in enumerate(inject):
        if pat is None:
            # chain-test fault: a flush of alternating values
            lines += [
                f"    force {target} = 1'b{value};",
                "    mism = 0;",
                "    flush;",
                f"    release {target};",
                f'    $display("FAULT {k} chain mismatches %0d", mism);',
            ]
        else:
            lines += [
                f"    force {target} = 1'b{value};",
                "    mism = 0;",
                f"    shift_phase({pat}, -1);",
                f"    capture({pat});",
                f"    shift_phase(-1, {pat});",
                f"    release {target};",
                f'    $display("FAULT {k} capture mismatches %0d", mism);',
            ]
    lines += ["    $finish;", "  end", "endmodule"]
    (work / "tb.v").write_text("\n".join(lines) + "\n")
    return work / "tb.v"


def run_bench(work: Path, timeout: int = 36000) -> dict[str, Any]:
    comp = subprocess.run(
        ["iverilog", "-g2012", "-o", "sim.vvp", "cells.v", "dut.v", "tb.v"],
        cwd=work, capture_output=True, text=True, timeout=timeout,
    )
    if comp.returncode != 0:
        raise RuntimeError("iverilog failed:\n" + comp.stderr[-4000:])
    sim = subprocess.run(["vvp", "-n", "sim.vvp"], cwd=work, capture_output=True, text=True, timeout=timeout)
    (work / "sim.log").write_text(sim.stdout + sim.stderr)
    good = re.search(r"GOOD patterns (\d+) mismatches (\d+)", sim.stdout)
    faults = {int(m.group(1)): (m.group(2), int(m.group(3)))
              for m in re.finditer(r"FAULT (\d+) (\w+) mismatches (\d+)", sim.stdout)}
    return {
        "good_patterns": int(good.group(1)) if good else None,
        "good_mismatches": int(good.group(2)) if good else None,
        "faults": faults,
        "log_tail": sim.stdout[-2000:],
    }
