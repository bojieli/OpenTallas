#!/usr/bin/env python3
"""Muxed-D scan insertion on a flat mapped netlist.

Every edge-triggered flip-flop becomes a scan cell: a flop with a library scan
equivalent (ASAP7 ``DFFHQN*``/``DFFLQN*`` -> ``SDFH*``/``SDFL*``) is swapped for
it, and any other flop (the asynchronous set/reset ``DFFASRHQNx1``, the
Q-output ``DFF*Qx4``) keeps its cell and gains a scan multiplexer, an
``AO22`` computing ``D & !SE | SI & SE``, in front of its data pin.  The cells
are then stitched into balanced chains:

* ``scan_en``          one scalar input, 1 = shift;
* ``scan_in[N-1:0]``   chain inputs, bit c feeds chain c;
* ``scan_out[N-1:0]``  chain outputs, each driven by a buffer from the last
  cell of its chain.

Chains are formed per clock domain -- a domain is the root clock net traced
back through buffers and inverters, plus the active edge -- and, within a
domain, in natural instance-name order, which keeps the bits of one register
adjacent.  With ``clock_mixing="mix"`` a chain may cross domains; every
crossing gets a lock-up latch clocked by the launching domain (transparent
while that clock is inactive), and negative-edge cells are ordered before
positive-edge ones so that no same-clock crossing needs one.

Asynchronous set/reset pins must be held inactive by the tester during shift
and capture.  A pin whose net traces back to a primary input through buffers
and inverters is controllable; any other is forced inactive by an OR/AND gate
with a new ``test_mode`` input (added only when needed), and reported.

The rewrite is textual: changed instances are re-emitted, new ports, wires and
cells are added, and every other byte of the netlist is kept.  A JSON scan
description (chains, cell order, polarities, constraints) is returned beside
it; the ATPG model builder and the gate-level pattern checker read it.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dft import liberty as lib  # type: ignore
    from dft import netlist as nl  # type: ignore
else:
    from . import liberty as lib
    from . import netlist as nl

SCAN_SCHEMA = "opentallas.dft.scan.v1"

# Library-specific choices.  Only ASAP7 is registered; the rest of the code
# derives everything else (pin roles, polarities, equivalence) from Liberty.
TECH = {
    "asap7": {
        "scan_equivalent": {
            "DFFHQNx1_ASAP7_75t_R": "SDFHx1_ASAP7_75t_R",
            "DFFHQNx2_ASAP7_75t_R": "SDFHx2_ASAP7_75t_R",
            "DFFHQNx3_ASAP7_75t_R": "SDFHx3_ASAP7_75t_R",
            "DFFLQNx1_ASAP7_75t_R": "SDFLx1_ASAP7_75t_R",
            "DFFLQNx2_ASAP7_75t_R": "SDFLx2_ASAP7_75t_R",
            "DFFLQNx3_ASAP7_75t_R": "SDFLx3_ASAP7_75t_R",
        },
        "mux": ("AO22x1_ASAP7_75t_R", "A1", "A2", "B1", "B2", "Y"),   # Y = A1&A2 | B1&B2
        "inv": ("INVx2_ASAP7_75t_R", "A", "Y"),
        "buf": ("BUFx2_ASAP7_75t_R", "A", "Y"),
        "or2": ("OR2x2_ASAP7_75t_R", "A", "B", "Y"),
        "and2": ("AND2x2_ASAP7_75t_R", "A", "B", "Y"),
        # lock-up latches: transparent while CLK is low / high
        "latch_low": ("DLLx1_ASAP7_75t_R", "CLK", "D", "Q"),
        "latch_high": ("DHLx1_ASAP7_75t_R", "CLK", "D", "Q"),
    }
}


def natural_key(name: str) -> list[Any]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


class DftError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Netlist analysis shared with the ATPG model builder
# --------------------------------------------------------------------------


def single_input_function(cell: dict[str, Any]) -> tuple[str, str, bool] | None:
    """(input pin, output pin, inverting) when the cell is a buffer or inverter."""
    if cell.get("ff") or cell.get("latch"):
        return None
    outs = lib.cell_outputs(cell)
    ins = lib.cell_inputs(cell)
    if len(outs) != 1 or len(ins) != 1:
        return None
    func = cell["pins"][outs[0]]["function"]
    if not func:
        return None
    expr = lib.parse_function(func)
    if expr == ("var", ins[0]):
        return ins[0], outs[0], False
    if expr == ("not", ("var", ins[0])):
        return ins[0], outs[0], True
    return None


class Design:
    """Bit-level connectivity of one module against a cell library."""

    def __init__(self, mod: nl.Module, cells: dict[str, dict[str, Any]]):
        self.mod = mod
        self.cells = cells
        self.aliases = nl.build_aliases(mod)
        self.driver: dict[str, tuple[int, str]] = {}
        self.loads: dict[str, list[tuple[int, str]]] = defaultdict(list)
        missing = sorted({i.cell for i in mod.instances if i.cell not in cells})
        if missing:
            raise DftError(f"cells missing from the liberty: {missing[:10]}")
        for idx, inst in enumerate(mod.instances):
            cell = cells[inst.cell]
            for pin, bits in inst.pins.items():
                info = cell["pins"].get(pin)
                if info is None:
                    raise DftError(f"{inst.name}: cell {inst.cell} has no pin {pin}")
                if len(bits) > 1:
                    raise DftError(f"{inst.name}.{pin}: multi-bit connection to a cell pin")
                if not bits:
                    continue
                net = self.net(bits[0])
                if info["direction"] == "output":
                    if net in self.driver:
                        raise DftError(f"net {net} has two drivers")
                    self.driver[net] = (idx, pin)
                elif info["direction"] == "input":
                    self.loads[net].append((idx, pin))
        self.inputs = [self.net(b) for b in mod.port_bits("input")]
        self.outputs = [self.net(b) for b in mod.port_bits("output")]
        self.input_set = set(self.inputs)

    def net(self, bit: str) -> str:
        return self.aliases.find(bit)

    def pin_net(self, inst: nl.Instance, pin: str) -> str | None:
        bits = inst.pins.get(pin)
        if not bits:
            return None
        return self.net(bits[0])

    def constant_value(self, net: str) -> int | None:
        """0/1 when the net is a constant or a tie cell, through buffers/inverters."""
        root, inverted, _ = self.trace_root(net)
        if nl.is_const_bit(root):
            return None if root.endswith("x") else int(root[-1]) ^ int(inverted)
        if root in self.driver:
            idx, pin = self.driver[root]
            inst = self.mod.instances[idx]
            func = self.cells[inst.cell]["pins"][pin]["function"]
            if func in ("0", "1") and not lib.cell_inputs(self.cells[inst.cell]):
                return int(func) ^ int(inverted)
        return None

    def trace_root(self, net: str) -> tuple[str, bool, list[int]]:
        """Walk back through buffers/inverters: (root net, inverted, cells walked)."""
        inverted = False
        walked: list[int] = []
        seen = set()
        while net in self.driver and net not in seen:
            seen.add(net)
            idx, _pin = self.driver[net]
            inst = self.mod.instances[idx]
            fn = single_input_function(self.cells[inst.cell])
            if fn is None:
                break
            in_pin, _out, inv = fn
            src = self.pin_net(inst, in_pin)
            if src is None:
                break
            walked.append(idx)
            inverted ^= inv
            net = src
        return net, inverted, walked


def sequential_role(cell: dict[str, Any]) -> dict[str, Any] | None:
    """Pin roles of a flop: clock pin and edge, data pins, async pins, output."""
    ff = cell.get("ff")
    if not ff:
        return None
    clk_expr = lib.parse_function(ff["clocked_on"])
    if clk_expr[0] == "var":
        clk_pin, edge = clk_expr[1], "pos"
    elif clk_expr[0] == "not" and clk_expr[1][0] == "var":
        clk_pin, edge = clk_expr[1][1], "neg"
    else:
        raise DftError(f"{cell['name']}: unsupported clocked_on {ff['clocked_on']!r}")
    state = ff["vars"][0]
    nxt = lib.parse_function(ff["next_state"])
    asyncs: dict[str, dict[str, Any]] = {}
    for kind in ("clear", "preset"):
        if kind in ff:
            expr = lib.parse_function(ff[kind])
            names = sorted(lib.expr_vars(expr))
            if len(names) != 1:
                raise DftError(f"{cell['name']}: {kind} over several pins unsupported")
            pin = names[0]
            active = 1 if lib.evaluate(expr, {pin: 1}) else 0
            asyncs[pin] = {"kind": kind, "active_value": active, "inactive_value": 1 - active}
    outputs = {}
    for pin, info in cell["pins"].items():
        if info["direction"] == "output" and info["function"]:
            expr = lib.parse_function(info["function"])
            if expr == ("var", state):
                outputs[pin] = False
            elif expr == ("not", ("var", state)):
                outputs[pin] = True
            elif len(ff["vars"]) > 1 and expr == ("var", ff["vars"][1]):
                outputs[pin] = True
    data_pins = sorted(lib.expr_vars(nxt) - {clk_pin})
    return {
        "clock_pin": clk_pin,
        "edge": edge,
        "state": state,
        "next_state": nxt,
        "data_pins": data_pins,
        "async": asyncs,
        "outputs": outputs,   # pin -> output is inverted state
    }


def _check_scan_equivalent(cells, flop: str, scan: str) -> None:
    f, s = cells[flop], cells[scan]
    rf, rs = sequential_role(f), sequential_role(s)
    if rf["edge"] != rs["edge"] or rf["clock_pin"] != rs["clock_pin"]:
        raise DftError(f"{scan} does not clock like {flop}")
    if set(rf["outputs"]) != set(rs["outputs"]) or rf["async"] or rs["async"]:
        raise DftError(f"{scan} is not a pin-compatible scan version of {flop}")
    extra = set(rs["data_pins"]) - set(rf["data_pins"])
    if extra != {"SE", "SI"}:
        raise DftError(f"{scan}: unexpected scan pins {sorted(extra)}")
    names = sorted(set(rs["data_pins"]))
    for row in range(1 << len(names)):
        env = {n: (row >> i) & 1 for i, n in enumerate(names)}
        want = lib.evaluate(rf["next_state"], env) if env["SE"] == 0 else env["SI"]
        got = lib.evaluate(rs["next_state"], env)
        # a scan cell with an inverted state variable stores !SI in shift
        if env["SE"] == 1:
            got_si = got if rs["outputs"] == rf["outputs"] else 1 - got
            inv = lib.evaluate(rs["next_state"], {**env, "SI": 1 - env["SI"]}) != got
            if not inv:
                raise DftError(f"{scan}: shift path does not depend on SI")
            del got_si
            continue
        if want != got:
            raise DftError(f"{scan} with SE=0 differs from {flop}")


# --------------------------------------------------------------------------
# Insertion
# --------------------------------------------------------------------------


_VNAME_MODULE: list[nl.Module] = []


def _vname(bit: str) -> str:
    """Spell a canonical bit name for Verilog output."""
    m = re.fullmatch(r"(.*)\[(\d+)\]", bit)
    mod = _VNAME_MODULE[-1] if _VNAME_MODULE else None
    if m and (mod is None or mod.ranges.get(m.group(1)) is not None):
        return nl.verilog_name(m.group(1)).rstrip() + f"[{m.group(2)}]"
    return nl.verilog_name(bit)


def _chain_counts(total: int, chains: int | None, max_length: int | None) -> int:
    count = chains or 1
    if max_length:
        count = max(count, math.ceil(total / max_length))
    return max(1, min(count, total)) if total else 0


def _split(items: list[Any], parts: int) -> list[list[Any]]:
    base, extra = divmod(len(items), parts)
    out, pos = [], 0
    for k in range(parts):
        size = base + (1 if k < extra else 0)
        out.append(items[pos:pos + size])
        pos += size
    return out


def insert_scan(
    mod: nl.Module,
    cells: dict[str, dict[str, Any]],
    *,
    chains: int | None = None,
    max_length: int | None = None,
    clock_mixing: str = "no_mix",
    tech: str = "asap7",
    scan_enable: str = "scan_en",
    scan_in: str = "scan_in",
    scan_out: str = "scan_out",
    test_mode: str = "test_mode",
) -> tuple[str, dict[str, Any]]:
    if clock_mixing not in ("no_mix", "mix"):
        raise DftError(f"clock_mixing must be no_mix or mix, got {clock_mixing!r}")
    t = TECH[tech]
    for name in (scan_enable, scan_in, scan_out, test_mode):
        if name in mod.ranges:
            raise DftError(f"netlist already has a net named {name}")
    if any(inst.name.startswith("dft_") for inst in mod.instances):
        raise DftError("netlist already carries dft_ instances (scan inserted twice?)")
    for flop, scan in t["scan_equivalent"].items():
        if flop in cells and scan in cells:
            _check_scan_equivalent(cells, flop, scan)

    design = Design(mod, cells)
    _VNAME_MODULE[:] = [mod]
    roles: dict[str, dict[str, Any]] = {}
    flops: list[int] = []
    latches: list[str] = []
    for idx, inst in enumerate(mod.instances):
        cell = cells[inst.cell]
        if cell.get("ff"):
            if inst.cell not in roles:
                roles[inst.cell] = sequential_role(cell)
            flops.append(idx)
        elif cell.get("latch"):
            latches.append(inst.name)
        elif any(i["direction"] == "internal" for i in cell["pins"].values()) and "ICG" in inst.cell:
            raise DftError(f"{inst.name}: clock-gating cell {inst.cell} needs a test-enable hookup; not supported")

    # ---- clock domains ------------------------------------------------------
    domain_of: dict[int, tuple[str, str]] = {}
    clock_roots: dict[str, dict[str, Any]] = {}
    for idx in flops:
        inst = mod.instances[idx]
        role = roles[inst.cell]
        net = design.pin_net(inst, role["clock_pin"])
        if net is None or nl.is_const_bit(net):
            raise DftError(f"{inst.name}: clock pin unconnected or constant")
        root, inverted, _ = design.trace_root(net)
        edge = role["edge"]
        if inverted:
            edge = "neg" if edge == "pos" else "pos"
        domain_of[idx] = (root, edge)
        entry = clock_roots.setdefault(root, {"is_primary_input": root in design.input_set, "flops": 0})
        entry["flops"] += 1
    uncontrolled_clocks = sorted(r for r, e in clock_roots.items() if not e["is_primary_input"])

    # ---- asynchronous set/reset controllability ------------------------------
    async_ports: dict[str, int] = {}
    async_fixes: dict[str, dict[str, Any]] = {}   # net -> {inactive, users}
    for idx in flops:
        inst = mod.instances[idx]
        role = roles[inst.cell]
        for pin, meta in role["async"].items():
            net = design.pin_net(inst, pin)
            if net is None:
                continue
            const = design.constant_value(net)
            if const is not None:
                if const != meta["inactive_value"]:
                    raise DftError(f"{inst.name}.{pin} is tied active")
                continue
            root, inverted, _ = design.trace_root(net)
            if root in design.input_set:
                need = meta["inactive_value"] ^ int(inverted)
                prev = async_ports.get(root)
                if prev is not None and prev != need:
                    raise DftError(f"port {root} drives set/reset pins of both polarities")
                async_ports[root] = need
            else:
                fix = async_fixes.setdefault(net, {"inactive_value": meta["inactive_value"], "users": []})
                if fix["inactive_value"] != meta["inactive_value"]:
                    raise DftError(f"net {net} drives set/reset pins of both polarities")
                fix["users"].append((idx, pin))

    # ---- chain formation -------------------------------------------------------
    def order_key(idx: int) -> tuple:
        root, edge = domain_of[idx]
        # negative-edge first so a same-clock neg->pos hand-off needs no latch
        return (0 if edge == "neg" else 1, root, natural_key(mod.instances[idx].name))

    total = len(flops)
    n_chains = _chain_counts(total, chains, max_length)
    chain_members: list[list[int]] = []
    if clock_mixing == "mix" or len(set(domain_of.values())) <= 1:
        ordered = sorted(flops, key=order_key)
        chain_members = [c for c in _split(ordered, n_chains) if c]
    else:
        by_domain: dict[tuple[str, str], list[int]] = defaultdict(list)
        for idx in flops:
            by_domain[domain_of[idx]].append(idx)
        domains = sorted(by_domain, key=lambda d: (0 if d[1] == "neg" else 1, d[0]))
        # proportional allocation, at least one chain per domain
        alloc = {d: 1 for d in domains}
        remaining = max(0, n_chains - len(domains))
        target = max(n_chains, len(domains))
        while remaining > 0:
            best = max(domains, key=lambda d: len(by_domain[d]) / alloc[d])
            alloc[best] += 1
            remaining -= 1
        for d in domains:
            members = sorted(by_domain[d], key=order_key)
            chain_members.extend(c for c in _split(members, min(alloc[d], len(members))) if c)
        del target
    n_chains = len(chain_members)

    # ---- emit -----------------------------------------------------------------
    replaced: dict[int, str] = {}   # instance index -> new statement text
    new_wires: list[str] = []
    new_cells: list[str] = []
    counters = defaultdict(int)
    area_before = sum(cells[i.cell]["area"] for i in mod.instances)
    area_added = 0.0
    mux_cell, m_a1, m_a2, m_b1, m_b2, m_y = t["mux"]
    inv_cell, inv_a, inv_y = t["inv"]
    buf_cell, buf_a, buf_y = t["buf"]
    se_n = "dft_scan_en_n"
    need_se_n = False

    pin_texts: dict[int, dict[str, str]] = {idx: dict(mod.instances[idx].pin_text) for idx in flops}
    cell_of: dict[int, str] = {idx: mod.instances[idx].cell for idx in flops}
    chain_records: list[dict[str, Any]] = []

    def output_of(idx: int) -> tuple[str, str, bool]:
        """(pin, verilog text of its net, inverted) of a flop's state output."""
        inst = mod.instances[idx]
        role = roles[inst.cell]
        for pin, inverted in sorted(role["outputs"].items()):
            text = pin_texts[idx].get(pin, "")
            if text:
                return pin, text, inverted
        pin, inverted = sorted(role["outputs"].items())[0]
        wire = f"dft_q_{counters['q']}"
        counters["q"] += 1
        new_wires.append(wire)
        pin_texts[idx][pin] = wire
        return pin, wire, inverted

    for c, members in enumerate(chain_members):
        record: dict[str, Any] = {
            "index": c,
            "scan_in": f"{scan_in}[{c}]",
            "scan_out": f"{scan_out}[{c}]",
            "length": len(members),
            "cells": [],
            "lockup_latches": [],
        }
        prev_text = f"{scan_in}[{c}]"
        prev_domain: tuple[str, str] | None = None
        for pos, idx in enumerate(members):
            inst = mod.instances[idx]
            role = roles[inst.cell]
            dom = domain_of[idx]
            si_text = prev_text
            if prev_domain is not None and prev_domain[0] != dom[0]:
                # lock-up latch clocked by the launching domain, transparent
                # while that clock is in its inactive phase
                lat_cell, lat_clk, lat_d, lat_q = t["latch_low" if prev_domain[1] == "pos" else "latch_high"]
                wire = f"dft_lockup_{counters['lock']}"
                name = f"dft_lockup_latch_{counters['lock']}"
                counters["lock"] += 1
                new_wires.append(wire)
                new_cells.append(
                    f"  {lat_cell} {name} (.{lat_clk}({_vname(prev_domain[0])}), "
                    f".{lat_d}({si_text}), .{lat_q}({wire}));"
                )
                area_added += cells[lat_cell]["area"]
                record["lockup_latches"].append(
                    {"instance": name, "after_position": pos - 1, "clock": prev_domain[0], "cell": lat_cell}
                )
                si_text = wire
            scan_cell = t["scan_equivalent"].get(inst.cell)
            if scan_cell and scan_cell in cells:
                cell_of[idx] = scan_cell
                pin_texts[idx]["SE"] = scan_enable
                pin_texts[idx]["SI"] = si_text
                area_added += cells[scan_cell]["area"] - cells[inst.cell]["area"]
                kind = "scan_cell"
            else:
                data = [p for p in role["data_pins"] if p not in role["async"]]
                if len(data) != 1:
                    raise DftError(f"{inst.name}: {inst.cell} has no single data pin to multiplex")
                dpin = data[0]
                d_text = pin_texts[idx].get(dpin) or "1'b0"
                wire = f"dft_d_{counters['mux']}"
                name = f"dft_scan_mux_{counters['mux']}"
                counters["mux"] += 1
                new_wires.append(wire)
                new_cells.append(
                    f"  {mux_cell} {name} (.{m_a1}({d_text}), .{m_a2}({se_n}), "
                    f".{m_b1}({si_text}), .{m_b2}({scan_enable}), .{m_y}({wire}));"
                )
                need_se_n = True
                pin_texts[idx][dpin] = wire
                area_added += cells[mux_cell]["area"]
                kind = "scan_mux"
            out_pin, out_text, out_inv = output_of(idx)
            record["cells"].append({
                "instance": inst.name,
                "cell": cell_of[idx],
                "original_cell": inst.cell,
                "kind": kind,
                "clock": dom[0],
                "edge": dom[1],
                "output_pin": out_pin,
                "output_inverted": out_inv,
            })
            prev_text = out_text
            prev_domain = dom
        so_name = f"dft_scan_out_buf_{c}"
        new_cells.append(f"  {buf_cell} {so_name} (.{buf_a}({prev_text}), .{buf_y}({scan_out}[{c}]));")
        area_added += cells[buf_cell]["area"]
        chain_records.append(record)

    if need_se_n:
        new_wires.append(se_n)
        new_cells.insert(0, f"  {inv_cell} dft_scan_en_inv (.{inv_a}({scan_enable}), .{inv_y}({se_n}));")
        area_added += cells[inv_cell]["area"]

    # asynchronous set/reset nets not controllable from a port
    add_test_mode = bool(async_fixes)
    fixes_report = []
    for k, (net, fix) in enumerate(sorted(async_fixes.items())):
        gate = t["or2"] if fix["inactive_value"] == 1 else t["and2"]
        g_cell, g_a, g_b, g_y = gate
        wire = f"dft_async_{k}"
        new_wires.append(wire)
        tm = test_mode if fix["inactive_value"] == 1 else f"dft_{test_mode}_n"
        new_cells.append(f"  {g_cell} dft_async_gate_{k} (.{g_a}({_vname(net)}), .{g_b}({tm}), .{g_y}({wire}));")
        area_added += cells[g_cell]["area"]
        for idx, pin in fix["users"]:
            pin_texts[idx][pin] = wire
        fixes_report.append({"net": net, "inactive_value": fix["inactive_value"], "pins": len(fix["users"])})
    if add_test_mode and any(f["inactive_value"] == 0 for f in fixes_report):
        new_wires.append(f"dft_{test_mode}_n")
        new_cells.append(f"  {inv_cell} dft_test_mode_inv (.{inv_a}({test_mode}), .{inv_y}(dft_{test_mode}_n));")
        area_added += cells[inv_cell]["area"]

    for idx in flops:
        inst = mod.instances[idx]
        conns = ", ".join(f".{pin}({text})" for pin, text in pin_texts[idx].items())
        replaced[idx] = f"{cell_of[idx]} {nl.verilog_name(inst.name)} ({conns});"

    # ---- splice text ------------------------------------------------------------
    text = mod.text
    edits: list[tuple[int, int, str]] = []
    new_ports = [scan_enable, scan_in, scan_out] + ([test_mode] if add_test_mode else [])
    edits.append((mod.port_list_close, mod.port_list_close, ", " + ", ".join(new_ports)))
    decl = [
        f"  input {scan_enable};",
        f"  wire {scan_enable};",
        f"  input [{n_chains - 1}:0] {scan_in};",
        f"  wire [{n_chains - 1}:0] {scan_in};",
        f"  output [{n_chains - 1}:0] {scan_out};",
        f"  wire [{n_chains - 1}:0] {scan_out};",
    ]
    if add_test_mode:
        decl += [f"  input {test_mode};", f"  wire {test_mode};"]
    decl += [f"  wire {w};" for w in new_wires]
    edits.append((mod.decl_end, mod.decl_end, "\n" + "\n".join(decl)))
    for idx, stmt in replaced.items():
        start, end = mod.instances[idx].span
        edits.append((start, end, stmt))
    edits.append((mod.end_span[0], mod.end_span[0], "\n".join(new_cells) + "\n"))
    edits.sort(key=lambda e: (e[0], e[1]))
    out, pos = [], 0
    for start, end, repl in edits:
        if start < pos:
            raise DftError("overlapping netlist edits")
        out.append(text[pos:start])
        out.append(repl)
        pos = end
    out.append(text[pos:])
    new_text = "".join(out)

    kinds = defaultdict(int)
    for rec in chain_records:
        for cell in rec["cells"]:
            kinds[cell["kind"]] += 1
    lengths = [rec["length"] for rec in chain_records]
    report = {
        "schema": SCAN_SCHEMA,
        "top": mod.name,
        "style": "muxed-D full scan",
        "tech": tech,
        "clock_mixing": clock_mixing,
        "requested": {"chains": chains, "max_length": max_length},
        "ports": {
            "scan_enable": scan_enable,
            "scan_enable_active": 1,
            "scan_in": scan_in,
            "scan_out": scan_out,
            "test_mode": test_mode if add_test_mode else None,
        },
        "flops": total,
        "scan_cells": kinds.get("scan_cell", 0),
        "scan_mux_cells": kinds.get("scan_mux", 0),
        "non_scan_latches": latches,
        "chain_count": n_chains,
        "chain_length_max": max(lengths) if lengths else 0,
        "chain_length_min": min(lengths) if lengths else 0,
        "lockup_latches": sum(len(r["lockup_latches"]) for r in chain_records),
        "clock_domains": [
            {"clock": d[0], "edge": d[1], "flops": sum(1 for v in domain_of.values() if v == d)}
            for d in sorted(set(domain_of.values()))
        ],
        "clock_roots": clock_roots,
        "uncontrolled_clock_roots": uncontrolled_clocks,
        "capture_constraints": {scan_enable: 0, **({test_mode: 1} if add_test_mode else {}), **async_ports},
        "shift_constraints": {scan_enable: 1, **({test_mode: 1} if add_test_mode else {}), **async_ports},
        "async_set_reset_fixes": fixes_report,
        "cell_area_before_um2": round(area_before, 5),
        "cell_area_added_um2": round(area_added, 5),
        "cell_area_added_fraction": round(area_added / area_before, 6) if area_before else None,
        "chains": chain_records,
    }
    return new_text, report


def insert_scan_file(src: Path, dst: Path, cells, **kwargs) -> dict[str, Any]:
    mod = nl.read_module(src, kwargs.pop("top", None))
    text, report = insert_scan(mod, cells, **kwargs)
    Path(dst).write_text(text, encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist")
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--top")
    ap.add_argument("--chains", type=int)
    ap.add_argument("--max-length", type=int)
    ap.add_argument("--clock-mixing", default="no_mix", choices=["no_mix", "mix"])
    ap.add_argument("--port-prefix", default="",
                    help="prefix for the added ports (a block that already has scan_en, such as the TAP)")
    ap.add_argument("--liberty", action="append", default=None)
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args(argv)
    paths = [Path(p) for p in args.liberty] if args.liberty else lib.default_asap7_liberty()
    cells = lib.load_cells(paths, args.cache_dir)
    report = insert_scan_file(
        Path(args.netlist), Path(args.output), cells, top=args.top, chains=args.chains,
        max_length=args.max_length, clock_mixing=args.clock_mixing,
        scan_enable=args.port_prefix + "scan_en", scan_in=args.port_prefix + "scan_in",
        scan_out=args.port_prefix + "scan_out", test_mode=args.port_prefix + "test_mode",
    )
    Path(args.report).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(
        f"{report['top']}: {report['flops']} flops -> {report['chain_count']} chains "
        f"(max length {report['chain_length_max']}), {report['scan_cells']} scan cells, "
        f"{report['scan_mux_cells']} muxed, {report['lockup_latches']} lock-up latches, "
        f"+{report['cell_area_added_um2']:.2f} um2 ({100 * (report['cell_area_added_fraction'] or 0):.2f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
