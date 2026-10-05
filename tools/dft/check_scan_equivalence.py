#!/usr/bin/env python3
"""Formal check that scan insertion leaves the function unchanged with scan off.

With ``scan_en`` = 0 and ``test_mode`` = 0 (and ``scan_in`` tied), the
scan-inserted netlist must compute exactly what the netlist before insertion
computed, cycle for cycle, from the same state.  Both netlists keep every
flop's instance name, so their states match by name, and Yosys proves it:

    equiv_make gold gate; equiv_simple -seq N; equiv_induct; equiv_status -assert

over cell models generated from Liberty (tools/dft/gate_sim.py), the same
models the gate-level pattern check simulates.  Every flop, every output and
every next-state function must be proven equivalent; nothing is left unproven.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dft import gate_sim  # noqa: E402
from dft import liberty as lib  # noqa: E402
from dft import netlist as nl  # noqa: E402

YOSYS_DEFAULT = Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"


def _rename_module(text: str, old: str, new: str) -> str:
    # both netlists carry (* top = 1 *); hierarchy would keep only one of them
    text = re.sub(r"\(\*\s*top\s*=\s*1\s*\*\)", "", text)
    pat = re.compile(r"(\bmodule\s+)" + re.escape(nl.verilog_name(old).rstrip()) + r"(\s*\()")
    out, n = pat.subn(r"\g<1>" + new + r"\g<2>", text, count=1)
    if n != 1:
        raise ValueError(f"module {old} not found")
    return out


def tie_scan_ports(text: str, scan: dict) -> str:
    """Turn the scan ports into internal wires held in functional mode."""
    ports = scan["ports"]
    tied = {ports["scan_enable"]: "1'b0"}
    if ports.get("test_mode"):
        tied[ports["test_mode"]] = "1'b0"
    n = scan["chain_count"]
    tied[ports["scan_in"]] = f"{n}'b0"
    removed = list(tied) + [ports["scan_out"]]
    # header: drop the ports from the port list (they were appended last)
    header_end = text.index(";", text.index("module"))
    header = text[:header_end]
    for p in removed:
        header = re.sub(r",\s*" + re.escape(p) + r"(?=\s*[,)])", "", header)
    text = header + text[header_end:]
    for p in removed:
        text = re.sub(r"\n\s*(input|output)\s+(\[[^\]]*\]\s*)?" + re.escape(p) + r"\s*;", "", text)
    assigns = "\n".join(f"  assign {p} = {v};" for p, v in tied.items())
    idx = text.rindex("endmodule")
    return text[:idx] + assigns + "\n" + text[idx:]


def check(prescan: Path, scan_netlist: Path, scan: dict, work: Path, cells, yosys: Path,
          seq: int = 1, timeout: int = 36000) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    top = scan["top"]
    gold = _rename_module(prescan.read_text(), top, "gold")
    gate = _rename_module(tie_scan_ports(scan_netlist.read_text(), scan), top, "gate")
    (work / "gold.v").write_text(gold)
    (work / "gate.v").write_text(gate)
    used = {i.cell for i in nl.parse_netlist(gate)[0].instances} | {i.cell for i in nl.parse_netlist(gold)[0].instances}
    # plain models: the per-pin fault-injection buffers would only add names to match
    gate_sim.write_cell_models(cells, used, work / "cells.v", pin_buffers=False)
    script = "\n".join([
        "read_verilog -sv cells.v",
        "read_verilog gold.v",
        "read_verilog gate.v",
        "hierarchy -check",
        "proc",
        "flatten",
        "opt_clean",
        # match on ports and flop states only: every other name is hidden, so
        # equiv_make pairs exactly the state elements and the outputs
        "select -set keep w:*.IQN w:*.IQ i:* o:*",
        "rename -hide w:* @keep %d",
        "async2sync",
        "equiv_make gold gate equiv",
        "hierarchy -top equiv",
        f"equiv_simple -seq {seq}",
        "equiv_induct",
        "equiv_status",
        "equiv_status -assert",
    ]) + "\n"
    (work / "equiv.ys").write_text(script)
    t0 = time.time()
    proc = subprocess.run([str(yosys), "-q", "-l", "equiv.log", "-s", "equiv.ys"], cwd=work,
                          capture_output=True, text=True, timeout=timeout)
    log = (work / "equiv.log").read_text() if (work / "equiv.log").is_file() else proc.stderr
    m = re.findall(r"Found (\d+) \$equiv cells in equiv:\s*\n\s*Of those cells (\d+) are proven and (\d+) are unproven", log)
    status = m[-1] if m else None
    return {
        "tool": str(yosys),
        "proven": proc.returncode == 0,
        "equiv_cells": int(status[0]) if status else None,
        "proven_cells": int(status[1]) if status else None,
        "unproven_cells": int(status[2]) if status else None,
        "method": f"equiv_make (state matched by instance name), equiv_simple -seq {seq}, equiv_induct",
        "scan_off": "scan_en=0, test_mode=0, scan_in=0; scan_out unobserved",
        "seconds": round(time.time() - t0, 1),
        "log_tail": log.strip().splitlines()[-6:],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prescan", required=True)
    ap.add_argument("--scan-netlist", required=True)
    ap.add_argument("--scan", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--yosys", default=str(YOSYS_DEFAULT))
    args = ap.parse_args(argv)
    cells = lib.load_cells(lib.default_asap7_liberty(), Path(args.work) / "cache")
    scan = json.loads(Path(args.scan).read_text())
    res = check(Path(args.prescan), Path(args.scan_netlist), scan, Path(args.work), cells, Path(args.yosys))
    Path(args.output).write_text(json.dumps(res, indent=1) + "\n")
    print(f"{scan['top']}: scan-off equivalence {'PROVEN' if res['proven'] else 'NOT PROVEN'} "
          f"({res['proven_cells']}/{res['equiv_cells']} $equiv cells, {res['seconds']} s)")
    return 0 if res["proven"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
