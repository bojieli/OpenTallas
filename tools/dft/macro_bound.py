"""Scan insertion around hard macros and integrated clock gates (default-off successor).

``scan_insert.insert_scan`` refuses a netlist that instantiates a hard macro (a
memory or ROM, which the standard-cell Liberty does not describe) or an
integrated clock gate (ICG).  Every replicated element of the current designs
has both: the DeepSeek-V4.1 ROM q element reads two ROM macros through one
element ICG.  This module wraps the unchanged inserter:

* **Hard macros are black boxes, X-bounded.**  The macro stays in the routed
  netlist byte-identical except for its output connections: every output bit
  now drives a new wire, and an ``AND2`` with ``!test_mode`` re-drives the
  original net.  In test mode (``test_mode`` = 1, held by the capture and
  shift constraints) a macro output is a known 0, so the unknown array
  contents never reach a scan cell; in functional mode the AND is transparent.
  The macro's own pins (array, decoder, sense path) belong to memory BIST.
  The logic that only feeds macro inputs is unobservable by scan; it is graded
  as untestable and reported.
* **ICGs are opened in test mode.**  The ICG's ``SE`` (test enable) pin, which
  synthesis ties to 0, is connected to ``test_mode`` (ORed with its functional
  value when that is not a constant), so every gated register clocks in shift
  and capture -- the single-frame capture model the ATPG uses.  ``ENA`` faults
  are then untestable by construction; the ICG's own pins are listed, not
  graded.

Three netlists come out of one scan insertion:

1. the routed netlist (macros and ICGs as above);
2. the ATPG netlist: the routed netlist in test mode, each macro replaced by
   ``TIELO`` cells on its output wires and each ICG by a buffer CLK -> GCLK
   (exactly the test-mode behaviour), so ``run_atpg.py`` runs unchanged;
3. cut netlists for the scan-off equivalence check: macro and ICG instances
   become cut points (outputs -> new module inputs, inputs -> new module
   outputs, the same names on both sides), applied to the pre-scan and the
   scanned netlist, so ``check_scan_equivalence.check`` runs unchanged.

Nothing here changes ``scan_insert.py`` or any earlier record.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dft import liberty as lib  # type: ignore
    from dft import netlist as nl  # type: ignore
    from dft import scan_insert as si  # type: ignore
else:
    from . import liberty as lib
    from . import netlist as nl
    from . import scan_insert as si

SCHEMA = "opentallas.dft.macro_bound.v1"
_PORT_RE = re.compile(r"\b(input|output)\s+(?:wire\s+|reg\s+|logic\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s*)?([A-Za-z_][A-Za-z0-9_$]*)")


def read_bb_ports(path: Path) -> dict[str, tuple[str, int]]:
    """Port directions and widths of a macro blackbox (``<name>_bb.v``)."""
    text = re.sub(r"//[^\n]*", "", Path(path).read_text())
    ports: dict[str, tuple[str, int]] = {}
    for m in _PORT_RE.finditer(text):
        width = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(2) else 1
        ports[m.group(4)] = (m.group(1), width)
    if not ports:
        raise si.DftError(f"{path}: no ports found")
    return ports


def is_icg(name: str, cell: dict[str, Any] | None) -> bool:
    return bool(cell) and "ICG" in name and any(i["direction"] == "internal" for i in cell["pins"].values())


def _bb_pin(pin: str, k: int) -> str:
    return f"{pin}__b{k}"


def prepare(mod: nl.Module, cells: dict[str, dict[str, Any]],
            bb_ports: dict[str, dict[str, tuple[str, int]]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """In-memory view the unchanged inserter accepts: bit-blasted macro pins, ICGs without internal pins."""
    cells2 = dict(cells)
    seen_bb: dict[str, int] = {}
    icgs: list[str] = []
    for inst in mod.instances:
        if inst.cell in bb_ports:
            ports = bb_ports[inst.cell]
            new_pins: dict[str, list[str]] = {}
            for pin, bits in inst.pins.items():
                if pin not in ports:
                    raise si.DftError(f"{inst.name}: macro {inst.cell} has no port {pin}")
                for k, bit in enumerate(bits):
                    new_pins[_bb_pin(pin, k)] = [bit]
            inst.pins = new_pins
            seen_bb[inst.cell] = seen_bb.get(inst.cell, 0) + 1
            if inst.cell not in cells2 or "__bb__" not in cells2[inst.cell]:
                pins = {}
                for pin, (d, w) in ports.items():
                    for k in range(w):
                        pins[_bb_pin(pin, k)] = {"direction": d, "function": None, "clock": pin in ("clk", "CLK", "CE")}
                cells2[inst.cell] = {"name": inst.cell, "area": 0.0, "pins": pins, "ff": None, "latch": None,
                                     "__bb__": True}
        elif is_icg(inst.cell, cells.get(inst.cell)):
            icgs.append(inst.name)
            if "__icg__" not in cells2[inst.cell]:
                c = copy.deepcopy(cells[inst.cell])
                c["pins"] = {p: i for p, i in c["pins"].items() if i["direction"] != "internal"}
                c["__icg__"] = True
                cells2[inst.cell] = c
    return cells2, {"macro_instances": seen_bb, "icg_instances": icgs}


def _stmt(cell: str, name: str, conns: list[tuple[str, str]]) -> str:
    return f"{cell} {nl.verilog_name(name).rstrip()} (" + ", ".join(f".{p}({t})" for p, t in conns) + ");"


def _splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    edits.sort(key=lambda e: (e[0], e[1]))
    out, pos = [], 0
    for start, end, repl in edits:
        if start < pos:
            raise si.DftError("overlapping netlist edits")
        out.append(text[pos:start])
        out.append(repl)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def insert_scan_bounded(mod: nl.Module, cells: dict[str, dict[str, Any]],
                        bb_ports: dict[str, dict[str, tuple[str, int]]], *, tech: str = "asap7",
                        test_mode: str = "test_mode", **kwargs) -> tuple[str, dict[str, Any]]:
    """``scan_insert.insert_scan`` plus macro X-bounding and ICG test enable."""
    cells2, found = prepare(mod, cells, bb_ports)
    text, report = si.insert_scan(mod, cells2, tech=tech, test_mode=test_mode, **kwargs)
    t = si.TECH[tech]
    and_cell, and_a, and_b, and_y = t["and2"]
    or_cell, or_a, or_b, or_y = t["or2"]
    inv_cell, inv_a, inv_y = t["inv"]

    smod = nl.parse_netlist(text)
    smod = [m for m in smod if m.name == mod.name][0]
    si._VNAME_MODULE[:] = [smod]
    tm_n = f"dft_{test_mode}_n"
    have_tm = report["ports"].get("test_mode") is not None
    have_tm_n = tm_n in smod.ranges
    edits: list[tuple[int, int, str]] = []
    new_wires: list[str] = []
    new_cells: list[str] = []
    area = 0.0
    bounded_bits = 0
    macro_rec = []
    icg_rec = []
    k_inst = 0
    for inst in smod.instances:
        if inst.cell in bb_ports:
            ports = bb_ports[inst.cell]
            conns = []
            outs = 0
            for pin, ptxt in inst.pin_text.items():
                d, w = ports[pin]
                bits = inst.pins[pin]
                if d == "output" and ptxt:
                    wire = f"dft_xb{k_inst}_{pin}"
                    new_wires.append(f"  wire [{len(bits) - 1}:0] {wire};")
                    conns.append((pin, wire))
                    for j, bit in enumerate(bits):
                        idx = len(bits) - 1 - j          # bits are MSB first
                        if nl.is_const_bit(bit):
                            continue
                        new_cells.append(f"  {and_cell} dft_xbound_{k_inst}_{pin}_{idx} (.{and_a}({wire}[{idx}]), "
                                         f".{and_b}({tm_n}), .{and_y}({si._vname(bit)}));")
                        area += cells[and_cell]["area"]
                        outs += 1
                else:
                    conns.append((pin, ptxt))
            edits.append((inst.span[0], inst.span[1], _stmt(inst.cell, inst.name, conns)))
            macro_rec.append({"instance": inst.name, "cell": inst.cell, "bounded_output_bits": outs,
                              "wire_prefix": f"dft_xb{k_inst}_"})
            bounded_bits += outs
            k_inst += 1
        elif is_icg(inst.cell, cells.get(inst.cell)):
            conns = []
            se_bits = inst.pins.get("SE", [])
            for pin, ptxt in inst.pin_text.items():
                if pin == "SE":
                    if not se_bits or all(b == "1'b0" for b in se_bits):
                        conns.append((pin, test_mode))
                        how = "tied 0 -> test_mode"
                    else:
                        wire = f"dft_icg_se_{len(icg_rec)}"
                        new_wires.append(f"  wire {wire};")
                        new_cells.append(f"  {or_cell} dft_icg_se_or_{len(icg_rec)} (.{or_a}({ptxt}), .{or_b}({test_mode}), .{or_y}({wire}));")
                        area += cells[or_cell]["area"]
                        conns.append((pin, wire))
                        how = "OR test_mode"
                else:
                    conns.append((pin, ptxt))
            if "SE" not in inst.pin_text:
                conns.append(("SE", test_mode))
                how = "unconnected -> test_mode"
            edits.append((inst.span[0], inst.span[1], _stmt(inst.cell, inst.name, conns)))
            icg_rec.append({"instance": inst.name, "cell": inst.cell, "SE": how})

    if (macro_rec or icg_rec) and not have_tm:
        edits.append((smod.port_list_close, smod.port_list_close, f", {test_mode}"))
        new_wires[:0] = [f"  input {test_mode};", f"  wire {test_mode};"]
    if bounded_bits and not have_tm_n:
        new_wires.append(f"  wire {tm_n};")
        new_cells.insert(0, f"  {inv_cell} dft_test_mode_inv (.{inv_a}({test_mode}), .{inv_y}({tm_n}));")
        area += cells[inv_cell]["area"]
    edits.append((smod.decl_end, smod.decl_end, "\n" + "\n".join(new_wires)))
    edits.append((smod.end_span[0], smod.end_span[0], "\n".join(new_cells) + "\n"))
    out = _splice(text, edits)

    if macro_rec or icg_rec:
        report["ports"]["test_mode"] = test_mode
        report["capture_constraints"][test_mode] = 1
        report["shift_constraints"][test_mode] = 1
    std_before = sum(cells[i.cell]["area"] for i in mod.instances if i.cell in cells and i.cell not in bb_ports)
    report["cell_area_before_um2"] = round(std_before, 5)
    report["cell_area_added_um2"] = round(report["cell_area_added_um2"] + area, 5)
    report["cell_area_added_fraction"] = round(report["cell_area_added_um2"] / std_before, 6) if std_before else None
    report["macro_bound"] = {
        "schema": SCHEMA,
        "macros": macro_rec,
        "bounded_output_bits": bounded_bits,
        "icgs": icg_rec,
        "bounding_area_um2": round(area, 5),
        "rule": "macro outputs AND !test_mode (X-bounded, 0 in test); ICG SE = test_mode (gated clocks run in test)",
    }
    return out, report


# ---------------------------------------------------------------------------
# derived netlists
# ---------------------------------------------------------------------------

def _module(text: str, top: str | None) -> nl.Module:
    mods = nl.parse_netlist(text)
    if top:
        mods = [m for m in mods if m.name == top]
    if len(mods) != 1:
        raise si.DftError("expected one module")
    return mods[0]


def atpg_netlist(text: str, top: str, bb_cells: set[str], icg_cells: set[str], tech: str = "asap7") -> tuple[str, dict]:
    """Test-mode netlist: macros -> TIELO on their output wires, ICG -> BUF CLK -> GCLK."""
    mod = _module(text, top)
    si._VNAME_MODULE[:] = [mod]
    buf_cell, buf_a, buf_y = si.TECH[tech]["buf"]
    edits = []
    ties = 0
    dropped_inputs = 0
    for n, inst in enumerate(mod.instances):
        if inst.cell in bb_cells:
            stm = []
            for pin, bits in inst.pins.items():
                # outputs connect to dft_xb wires after bounding; inputs are dropped (unobservable by scan)
                if inst.pin_text[pin].startswith("dft_xb"):
                    for j, bit in enumerate(bits):
                        stm.append(f"TIELOx1_ASAP7_75t_R dft_atpg_tie_{n}_{pin}_{j} (.L({si._vname(bit)}));")
                        ties += 1
                else:
                    dropped_inputs += len(bits)
            edits.append((inst.span[0], inst.span[1], "\n  ".join(stm)))
        elif inst.cell in icg_cells:
            edits.append((inst.span[0], inst.span[1],
                          f"{buf_cell} {nl.verilog_name(inst.name).rstrip()} (.{buf_a}({inst.pin_text['CLK']}), "
                          f".{buf_y}({inst.pin_text['GCLK']}));"))
    return _splice(text, edits), {"tied_macro_output_bits": ties, "dropped_macro_input_bits": dropped_inputs}


def cut_netlist(text: str, top: str, bb_cells: set[str], icg_cells: set[str]) -> tuple[str, dict]:
    """Macro and ICG instances -> cut points named by instance and pin (outputs -> inputs, inputs -> outputs)."""
    mod = _module(text, top)
    edits = []
    ports, decls, assigns = [], [], []
    for inst in mod.instances:
        if inst.cell not in bb_cells and inst.cell not in icg_cells:
            continue
        base = re.sub(r"[^A-Za-z0-9_]", "_", inst.name)
        for pin, bits in inst.pins.items():
            ptxt = inst.pin_text[pin]
            if not ptxt:
                continue
            name = f"dft_cut_{base}_{pin}"
            w = len(bits)
            rng = f"[{w - 1}:0] " if w > 1 else ""
            # direction from the instance's role: an output pin drives its net
            is_out = (inst.cell in icg_cells and pin == "GCLK") or (inst.cell in bb_cells and _out_pin(inst, pin))
            if is_out:
                ports.append(name)
                decls += [f"  input {rng}{name};", f"  wire {rng}{name};"]
                assigns.append(f"  assign {ptxt} = {name};")
            else:
                ports.append(name)
                decls += [f"  output {rng}{name};", f"  wire {rng}{name};"]
                assigns.append(f"  assign {name} = {ptxt};")
        edits.append((inst.span[0], inst.span[1], ""))
    edits.append((mod.port_list_close, mod.port_list_close, "".join(", " + p for p in ports)))
    edits.append((mod.decl_end, mod.decl_end, "\n" + "\n".join(decls)))
    edits.append((mod.end_span[0], mod.end_span[0], "\n".join(assigns) + "\n"))
    return _splice(text, edits), {"cut_ports": len(ports)}


_OUT_PINS: dict[str, set[str]] = {}


def _out_pin(inst: nl.Instance, pin: str) -> bool:
    return pin in _OUT_PINS.get(inst.cell, set())


def set_bb_ports(bb_ports: dict[str, dict[str, tuple[str, int]]]) -> None:
    _OUT_PINS.clear()
    for cell, ports in bb_ports.items():
        _OUT_PINS[cell] = {p for p, (d, _w) in ports.items() if d == "output"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("atpg-netlist")
    a.add_argument("--scan-netlist", required=True)
    a.add_argument("--scan", required=True, help="scan_chains.json with a macro_bound section")
    a.add_argument("--output", required=True)
    a.add_argument("--scan-output", required=True,
                   help="scan_chains.json for the ATPG netlist: chain clocks behind an ICG re-rooted at its CLK net")
    e = sub.add_parser("equivalence")
    e.add_argument("--prescan", required=True)
    e.add_argument("--scan-netlist", required=True)
    e.add_argument("--scan", required=True)
    e.add_argument("--bb", action="append", default=[], metavar="CELL=BB_V")
    e.add_argument("--work", required=True)
    e.add_argument("--output", required=True)
    e.add_argument("--yosys", default="yosys")
    e.add_argument("--seq", type=int, default=1)
    args = ap.parse_args(argv)
    scan = json.loads(Path(args.scan).read_text())
    mb = scan.get("macro_bound") or {}
    bb_cells = {m["cell"] for m in mb.get("macros", [])}
    icg_cells = {m["cell"] for m in mb.get("icgs", [])}
    if args.cmd == "atpg-netlist":
        src = Path(args.scan_netlist).read_text()
        text, info = atpg_netlist(src, scan["top"], bb_cells, icg_cells)
        Path(args.output).write_text(text)
        # in test mode an ICG is a buffer: a chain cell clocked from its GCLK is clocked from its CLK
        mod = _module(src, scan["top"])
        reroot = {}
        for inst in mod.instances:
            if inst.cell in icg_cells:
                reroot[nl.canonical_name(inst.pin_text["GCLK"].strip())] = nl.canonical_name(inst.pin_text["CLK"].strip())
        for ch in scan["chains"]:
            for c in ch["cells"]:
                c["clock"] = reroot.get(c["clock"], c["clock"])
        for d in scan.get("clock_domains", []):
            d["clock"] = reroot.get(d["clock"], d["clock"])
        roots = {}
        for r, e in scan.get("clock_roots", {}).items():
            nr = reroot.get(r, r)
            ent = roots.setdefault(nr, {"is_primary_input": nr in mod.port_dirs, "flops": 0})
            ent["flops"] += e["flops"]
        scan["clock_roots"] = roots
        scan["uncontrolled_clock_roots"] = sorted(r for r, e in roots.items() if not e["is_primary_input"])
        scan["atpg_reroot"] = reroot
        Path(args.scan_output).write_text(json.dumps(scan, indent=1, sort_keys=True) + "\n")
        info["rerooted_clocks"] = reroot
        print(json.dumps(info))
        return 0
    from dft import check_scan_equivalence as ce  # noqa: PLC0415
    bb_ports = {c: read_bb_ports(Path(p)) for c, p in (x.split("=", 1) for x in args.bb)}
    set_bb_ports(bb_ports)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    gold, gi = cut_netlist(Path(args.prescan).read_text(), scan["top"], bb_cells, icg_cells)
    gate, gt = cut_netlist(Path(args.scan_netlist).read_text(), scan["top"], bb_cells, icg_cells)
    (work / "prescan_cut.v").write_text(gold)
    (work / "scan_cut.v").write_text(gate)
    cells = lib.load_cells(lib.default_asap7_liberty(), work / "cache")
    res = ce.check(work / "prescan_cut.v", work / "scan_cut.v", scan, work / "equiv", cells, Path(args.yosys), seq=args.seq)
    res["cut_points"] = {"prescan": gi, "scan": gt, "macros": sorted(bb_cells), "icgs": sorted(icg_cells)}
    Path(args.output).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("proven", "equiv_cells", "unproven_cells")}))
    return 0 if res["proven"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
