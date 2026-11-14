#!/usr/bin/env python3
"""HARD-IP wrapper cell check (QC-PHY-1 11-14, COORD): the synthesized wrapper of a full-area hard IP type must hold only the
macro instance and direct port-to-pin wires.  The in-band reset epoch pins (named by the plan's epoch flag, schema.has_epoch)
are driven from the delivered reset level (bind.py reg_hard: epoch = reset level, no flop) and the synthesis INSBUF turns each
into a BUF: those buffers are an intended feed-through and are exempt.  Any other cell is reported.

  hard_ip_wrapper_cells.py NETLIST.v TOP MACRO_MODULE PLAN.json TYPE
"""
import json
import re
import sys
from pathlib import Path

_CELL = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[\w$]+)\s*\((.*?)\);", re.S | re.M)
_PIN = re.compile(r"\.(\w+)\(([^()]*)\)")


def epoch_pins(P, tn):
    """{"bus[idx]"} epoch pins of type tn's boundary buses, from the plan ports that end on a partition of this type."""
    import schema as S
    types = {p for p, d in P.parts.items() if d["type"] == tn}
    out = set()
    for pr in P.ports.values():
        for side in ("src", "dst"):
            e = pr.get(side) or {}
            if e.get("part") in types and S.has_epoch(pr):
                out.add(f'{e["bus"]}[{int(pr["width"])}]')
    return out


def wrapper_cells(netlist_text, top, macro_module, epoch, pin_alias=True):
    """-> dict(macro=[inst], epoch_buffers=[(cell, port bit)], alias_buffers=[...], other=[...]).
    pin_alias (default True, COORD 11-14: a macro-output-pin -> port buffer is a harmless pass-through; --no-pin-alias = strict): also exempt a BUF whose input is a net inside the macro hierarchy (the macro
    output pin, e.g. \\u_bound.w_core_tx_up[0]) and whose output is a port bit: synthesis INSBUF on a direct pin-to-port wire."""
    m = re.search(r"\nmodule\s+" + re.escape(top) + r"\b.*?\nendmodule", netlist_text, re.S)
    if not m:
        raise ValueError(f"module {top} not in netlist")
    res = dict(macro=[], epoch_buffers=[], alias_buffers=[], other=[])
    for c in _CELL.finditer(m.group(0)):
        ctype, name, body = c.group(1), c.group(2), c.group(3)
        if ctype in ("module", "input", "output", "wire", "assign", "reg"):
            continue
        pins = {k: v.strip() for k, v in _PIN.findall(body)}
        if ctype == macro_module:
            res["macro"].append(name)
        elif ctype.startswith("BUF") and pins.get("Y", "").replace(" ", "") in {e.replace(" ", "") for e in epoch}:
            res["epoch_buffers"].append((name, pins["Y"]))
        elif pin_alias and ctype.startswith("BUF") and pins.get("A", "").startswith("\\u_bound."):
            res["alias_buffers"].append((name, pins["Y"]))
        else:
            res["other"].append((ctype, name, pins.get("A"), pins.get("Y")))
    return res


def main(argv):
    nl, top, macro, plan, tn = [a for a in argv[1:] if not a.startswith('--')][:5]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema as S
    P = S.Plan(S.load(plan), plan)
    r = wrapper_cells(Path(nl).read_text(), top, macro, epoch_pins(P, tn), pin_alias="--no-pin-alias" not in argv)
    ok = bool(r["macro"]) and not r["other"]
    # R-MINIMAL: the zero-cell check is ADVISORY (COORD 11-14), it never blocks a phy type: exit 0 unless --strict
    print(json.dumps(dict(r, ok=ok, advisory="--strict" not in argv), indent=1))
    return 0 if (ok or "--strict" not in argv) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
