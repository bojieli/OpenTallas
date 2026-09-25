"""Build the full-scan combinational ATPG model of a scan-inserted netlist.

With every flop on a scan chain, a test is: load a state (the pseudo-primary
inputs, PPIs), apply the primary inputs, observe the primary outputs, pulse the
clock once (capture) and unload the next state (the pseudo-primary outputs,
PPOs).  Test generation is therefore combinational over the logic between the
scan cells, which is what this module extracts.

The model is a graph of primitive gates (BUF, NOT, AND, NAND, OR, NOR, XOR,
XNOR and constants).  Each library cell becomes:

* one BUF per input pin (the *pin node*: its stuck-at faults are the cell's
  input-pin faults, distinct from the net's other branches);
* the primitive network of the cell's Liberty function; and
* one BUF per output pin (the *output node*: the cell output-pin faults, which
  are the net's stem faults).

A flop contributes a PPI (its state variable) whose output-pin nodes are BUF
or NOT of it, and a PPO: the Liberty ``next_state`` over its pin nodes, with
the asynchronous clear/preset folded in as ``!clear & (preset | next)`` so a
stuck set/reset pin shows up in the captured value.

Faults are stuck-at-0 and stuck-at-1 on every pin of every cell -- the
uncollapsed pin-fault universe commercial tools report on.  Clock pins are
not modelled combinationally; they are graded by the chain test, where a
clock pin stuck at either value is a cell that never updates.

Two models are written from one netlist: *capture* (``scan_en`` = 0 and the
other test constraints held, observe POs and PPOs) and *shift* (``scan_en`` = 1,
with the state-to-next-state pairs, scan inputs and scan outputs the engine's
chain-test mode clocks through a whole flush).  A fault the capture patterns
miss but the flush exposes is detected by the chain test; a clock pin is
modelled there as its cell holding its state.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dft import liberty as lib  # type: ignore
    from dft import netlist as nl  # type: ignore
    from dft.scan_insert import Design, sequential_role, DftError  # type: ignore
else:
    from . import liberty as lib
    from . import netlist as nl
    from .scan_insert import Design, sequential_role, DftError

# node types shared with otatpg.cpp
T_CONST0, T_CONST1, T_INPUT, T_BUF, T_NOT, T_AND, T_NAND, T_OR, T_NOR, T_XOR, T_XNOR = range(11)
TYPE_NAMES = ["CONST0", "CONST1", "INPUT", "BUF", "NOT", "AND", "NAND", "OR", "NOR", "XOR", "XNOR"]


class Model:
    def __init__(self) -> None:
        self.types: list[int] = []
        self.fanins: list[list[int]] = []
        self.const = {}

    def add(self, typ: int, fanins: list[int] | None = None) -> int:
        self.types.append(typ)
        self.fanins.append(list(fanins or []))
        return len(self.types) - 1

    def constant(self, value: int) -> int:
        if value not in self.const:
            self.const[value] = self.add(T_CONST1 if value else T_CONST0)
        return self.const[value]

    def expr(self, e: tuple, env: dict[str, int]) -> int:
        kind = e[0]
        if kind == "var":
            return env[e[1]]
        if kind == "const":
            return self.constant(e[1])
        if kind == "not":
            inner = e[1]
            # fold NOT over AND/OR/XOR into NAND/NOR/XNOR
            if inner[0] == "and":
                return self.add(T_NAND, [self.expr(t, env) for t in inner[1]])
            if inner[0] == "or":
                return self.add(T_NOR, [self.expr(t, env) for t in inner[1]])
            if inner[0] == "xor":
                return self.add(T_XNOR, [self.expr(inner[1], env), self.expr(inner[2], env)])
            return self.add(T_NOT, [self.expr(inner, env)])
        if kind == "and":
            return self.add(T_AND, [self.expr(t, env) for t in e[1]])
        if kind == "or":
            return self.add(T_OR, [self.expr(t, env) for t in e[1]])
        if kind == "xor":
            return self.add(T_XOR, [self.expr(e[1], env), self.expr(e[2], env)])
        raise ValueError(kind)


def build_models(
    netlist: Path,
    scan: dict[str, Any],
    cells: dict[str, dict[str, Any]],
    out_dir: Path,
    top: str | None = None,
    clock_ports: list[str] | None = None,
) -> dict[str, Any]:
    """Write capture.model, shift.model, faults and a names map into out_dir."""
    mod = nl.read_module(netlist, top or scan.get("top"))
    design = Design(mod, cells)
    out_dir.mkdir(parents=True, exist_ok=True)

    roots = {c["clock"] for ch in scan["chains"] for c in ch["cells"]}
    clock_ports = sorted(set(clock_ports or []) | {r for r in roots if r in design.input_set})

    m = Model()
    net_node: dict[str, int] = {}
    pi_nodes: list[tuple[str, int]] = []
    for bit in design.inputs:
        if bit in net_node:
            continue
        node = m.add(T_INPUT)
        net_node[bit] = node
        pi_nodes.append((bit, node))

    # flops and output nodes first, so nets have driver nodes before any fanin is built
    flop_state: dict[int, int] = {}
    role_cache: dict[str, dict[str, Any] | None] = {}
    out_node: dict[tuple[int, str], int] = {}
    latches: list[int] = []
    for idx, inst in enumerate(mod.instances):
        cell = cells[inst.cell]
        if inst.cell not in role_cache:
            role_cache[inst.cell] = sequential_role(cell) if cell.get("ff") else None
        if cell.get("ff"):
            flop_state[idx] = m.add(T_INPUT)
        elif cell.get("latch"):
            latches.append(idx)
        for pin, info in cell["pins"].items():
            if info["direction"] != "output":
                continue
            bits = inst.pins.get(pin)
            node = m.add(T_BUF)   # fanin filled in below
            out_node[(idx, pin)] = node
            if bits:
                net = design.net(bits[0])
                if net in net_node and net not in design.input_set:
                    raise DftError(f"net {net} driven twice")
                if net not in design.input_set:
                    net_node[net] = node

    undriven: set[str] = set()

    def node_of(bits: list[str] | None) -> int:
        if not bits:
            undriven.add("<unconnected pin>")
            return m.constant(0)
        net = design.net(bits[0])
        if nl.is_const_bit(net):
            return m.constant(0 if net.endswith("0") or net.endswith("x") else 1)
        if net not in net_node:
            undriven.add(net)
            return m.constant(0)
        return net_node[net]

    faults: list[tuple[int, int, str, str]] = []   # (node, stuck, instance, pin)
    clock_pin_faults: list[tuple[str, str, int]] = []
    clock_pin_effect: list[str] = []
    latch_q: dict[str, int] = {}
    ppo_nodes: list[tuple[str, int]] = []
    ppi_nodes: list[tuple[str, int]] = []

    for idx, inst in enumerate(mod.instances):
        cell = cells[inst.cell]
        role = role_cache[inst.cell]
        env: dict[str, int] = {}
        clock_pins = set()
        if role:
            clock_pins.add(role["clock_pin"])
        if cell.get("latch"):
            en = lib.parse_function(cell["latch"]["enable"])
            clock_pins |= lib.expr_vars(en)
        for pin, info in cell["pins"].items():
            if info["direction"] != "input":
                continue
            if pin in clock_pins:
                for v in (0, 1):
                    clock_pin_faults.append((inst.name, pin, v))
                    if cell.get("latch"):
                        # a latch clock stuck in its transparent phase only
                        # removes the lock-up delay: invisible to a zero-delay
                        # test; stuck opaque, the latch holds
                        en = lib.parse_function(cell["latch"]["enable"])
                        transparent = lib.evaluate(en, {x: v for x in lib.expr_vars(en)})
                        clock_pin_effect.append("transparent" if transparent else "hold")
                    else:
                        clock_pin_effect.append("hold")
                continue
            node = m.add(T_BUF, [node_of(inst.pins.get(pin))])
            env[pin] = node
            for v in (0, 1):
                faults.append((node, v, inst.name, pin))
        if role:
            state = flop_state[idx]
            env[role["state"]] = state
            ff = cell["ff"]
            if len(ff["vars"]) > 1:
                env[ff["vars"][1]] = m.add(T_NOT, [state])
            ns = m.expr(role["next_state"], env)
            clear = preset = None
            for pin, meta in role["async"].items():
                active = m.expr(lib.parse_function(ff[meta["kind"]]), env)
                if meta["kind"] == "clear":
                    clear = active
                else:
                    preset = active
            if preset is not None:
                ns = m.add(T_OR, [preset, ns])
            if clear is not None:
                ns = m.add(T_AND, [m.add(T_NOT, [clear]), ns])
            ppo = m.add(T_BUF, [ns])
            ppo_nodes.append((inst.name, ppo))
            ppi_nodes.append((inst.name, state))
        if cell.get("latch"):
            # lock-up latch: transparent while the clock is at rest (off-state 0)
            lat = cell["latch"]
            en = lib.parse_function(lat["enable"])
            clk_vars = sorted(lib.expr_vars(en))
            transparent = lib.evaluate(en, {v: 0 for v in clk_vars})
            data = m.expr(lib.parse_function(lat["data_in"]), env)
            if not transparent:
                raise DftError(f"{inst.name}: latch opaque at clock rest; not supported")
            env[lat["vars"][0]] = data
            if len(lat["vars"]) > 1:
                env[lat["vars"][1]] = m.add(T_NOT, [data])
        for pin, info in cell["pins"].items():
            if info["direction"] != "output":
                continue
            node = out_node[(idx, pin)]
            if cell.get("latch"):
                latch_q[inst.name] = node
            func = info["function"]
            if not func:
                raise DftError(f"{inst.cell}.{pin} has no function")
            root = m.expr(lib.parse_function(func), env)
            m.fanins[node] = [root]
            for v in (0, 1):
                faults.append((node, v, inst.name, pin))

    po_nodes: list[tuple[str, int]] = []
    for bit in mod.port_bits("output"):
        po_nodes.append((bit, node_of([bit])))

    ports = scan["ports"]
    scan_out_bits = [b for b in mod.bits_of(ports["scan_out"])] if ports["scan_out"] in mod.ranges else []

    def write(name: str, constraints: dict[str, int], observe_po: bool) -> dict[str, Any]:
        pi_lines = []
        constrained = {}
        for bit, node in pi_nodes:
            value = -1
            base = bit.split("[")[0]
            if bit in constraints:
                value = constraints[bit]
            elif base in constraints and base == bit:
                value = constraints[base]
            if bit in clock_ports:
                value = 0
            if value >= 0:
                constrained[bit] = value
            pi_lines.append(f"PI {node} {value}")
        obs = []
        if observe_po:
            obs += [node for _, node in po_nodes]
        else:
            obs += [node_of([b]) for b in scan_out_bits]
        obs += [node for _, node in ppo_nodes]
        path = out_dir / f"{name}.model"
        with path.open("w") as fh:
            fh.write(f"OTATPG 1\nN {len(m.types)}\n")
            for typ, fins in zip(m.types, m.fanins):
                fh.write(f"G {typ} {len(fins)}" + "".join(f" {f}" for f in fins) + "\n")
            fh.write("\n".join(pi_lines) + "\n")
            for _, node in ppi_nodes:
                fh.write(f"PPI {node}\n")
            for node in obs:
                fh.write(f"OBS {node}\n")
            if not observe_po:
                # chain-test records: state -> next state, scan inputs, scan outputs
                for (_, ppi), (_, ppo) in zip(ppi_nodes, ppo_nodes):
                    fh.write(f"SEQ {ppi} {ppo}\n")
                for c, _chain in enumerate(scan["chains"]):
                    bit = f"{ports['scan_in']}[{c}]"
                    fh.write(f"FLUSHIN {node_of([bit])}\n")
                for c, chain in enumerate(scan["chains"]):
                    bit = f"{ports['scan_out']}[{c}]"
                    fh.write(f"FLUSHOBS {node_of([bit])} {len(chain['cells'])}\n")
        return {"path": str(path), "constrained_inputs": constrained, "observed": len(obs)}

    capture = write("capture", scan["capture_constraints"], observe_po=True)
    shift = write("shift", scan["shift_constraints"], observe_po=False)
    with (out_dir / "faults.txt").open("w") as fh:
        fh.write(f"{len(faults)}\n")
        for node, v, _inst, _pin in faults:
            fh.write(f"{node} {v}\n")
    # chain-test fault list: the pin faults, then a stopped clock on every
    # scan cell as its state held at 0 and at 1
    ppi_of = dict(ppi_nodes)
    ppi_of.update(latch_q)   # a held latch is its output stuck
    clock_insts = sorted({inst for (inst, _pin, _v), eff in zip(clock_pin_faults, clock_pin_effect)
                          if eff == "hold" and inst in ppi_of})
    with (out_dir / "flush_faults.txt").open("w") as fh:
        fh.write(f"{len(faults) + 2 * len(clock_insts)}\n")
        for node, v, _inst, _pin in faults:
            fh.write(f"{node} {v}\n")
        for inst in clock_insts:
            fh.write(f"{ppi_of[inst]} 0\n{ppi_of[inst]} 1\n")
    names = {
        "pi": [b for b, _ in pi_nodes],
        "ppi": [n for n, _ in ppi_nodes],
        "po": [b for b, _ in po_nodes],
        "ppo": [n for n, _ in ppo_nodes],
        "faults": [[inst, pin, v] for _node, v, inst, pin in faults],
        "clock_pin_faults": clock_pin_faults,
        "clock_pin_effect": clock_pin_effect,
        "hold_fault_instances": clock_insts,
    }
    (out_dir / "names.json").write_text(json.dumps(names))
    counts = defaultdict(int)
    for t in m.types:
        counts[TYPE_NAMES[t]] += 1
    return {
        "top": mod.name,
        "instances": len(mod.instances),
        "nodes": len(m.types),
        "node_types": dict(counts),
        "primary_inputs": len(pi_nodes),
        "primary_outputs": len(po_nodes),
        "scan_cells": len(ppi_nodes),
        "lockup_latches": len(latches),
        "pin_faults_modelled": len(faults),
        "clock_pin_faults": len(clock_pin_faults),
        "undriven_nets": sorted(undriven)[:20],
        "undriven_net_count": len(undriven),
        "clock_ports": clock_ports,
        "capture": capture,
        "shift": shift,
    }
