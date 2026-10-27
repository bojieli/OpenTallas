#!/usr/bin/env python3
"""Select existing constant-D capture FFs for early physical mapping.

Every target is an explicit bit of an existing wire. This never adds state or
changes an RTL connection. Missing, merged, reset-bearing or nonconstant FFs
fail before mapping. Verify again after mapping; final synthesis/route checks
remain the kit's responsibility.
"""
import argparse
import json
from pathlib import Path

CELL = "DFFHQNx2_ASAP7_75t_R"


def selected(design, spec):
    if set(spec) != {"captures"} or not spec["captures"]:
        raise ValueError("spec requires a nonempty captures list")
    rows, used = [], set()
    for entry in spec["captures"]:
        if set(entry) != {"module", "wire", "bits"} or not entry["bits"]:
            raise ValueError("each capture needs exact module, wire and bit offsets")
        mn, wn = entry["module"], entry["wire"]
        module = design["modules"][mn]
        wire = module["netnames"][wn]
        for bit in entry["bits"]:
            if type(bit) is not int or bit < 0 or bit >= len(wire["bits"]):
                raise ValueError(f"{mn}/{wn}: invalid bit offset {bit}")
            q = wire["bits"][bit]
            drivers = [(cn, c) for cn, c in module["cells"].items()
                       if c.get("port_directions", {}).get("Q") == "output"
                       and c.get("connections", {}).get("Q") == [q]]
            if len(drivers) != 1:
                raise ValueError(f"{mn}/{wn}[{bit}]: expected one existing FF driver, got {len(drivers)}")
            cn, cell = drivers[0]
            if (mn, cn) in used:
                raise ValueError(f"{mn}/{wn}[{bit}]: capture FF shared by target bits")
            used.add((mn, cn))
            cc = cell["connections"]
            keep = cell.get("attributes", {}).get("keep", "0")
            if cell["type"] != "$_DFF_P_" or set(cc) != {"C", "D", "Q"}:
                raise ValueError(f"{mn}/{cn}: only existing positive-edge plain DFFs are supported")
            if not str(keep).strip("0") or cc["D"] not in (["0"], ["1"]) or len(cc["C"]) != 1 or type(cc["C"][0]) is not int:
                raise ValueError(f"{mn}/{cn}: requires a kept constant-D FF with a real clock")
            if any(ch in mn + cn for ch in "{}\n\r"):
                raise ValueError("unsafe Yosys selection name")
            rows.append(dict(module=mn, cell=cn, wire=wn, bit=bit,
                             q=q, clock=cc["C"][0], d=cc["D"][0]))
    return rows


def selection(rows):
    def literal(s):
        for a, b in (("\\", "\\\\"), ("[", "\\["), ("]", "\\]"), ("*", "\\*"), ("?", "\\?")):
            s = s.replace(a, b)
        return "{" + s + "}"
    return "yosys select -set ot_const_dff_keep " + " ".join(literal(r["module"] + "/" + r["cell"]) for r in rows) + "\n"


def verify(design, rows):
    for row in rows:
        c = design["modules"][row["module"]]["cells"][row["cell"]]
        expected = {"QN": [row["q"]], "CLK": [row["clock"]], "D": ["1" if row["d"] == "0" else "0"]}
        if c["type"] != CELL or c["connections"] != expected:
            raise ValueError(f"{row['module']}/{row['cell']}: mapped state, clock or polarity changed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("prepare", "verify"))
    ap.add_argument("design")
    ap.add_argument("record")
    ap.add_argument("--tcl")
    ap.add_argument("--receipt")
    a = ap.parse_args()
    design = json.loads(Path(a.design).read_text())
    record = json.loads(Path(a.record).read_text())
    if a.mode == "prepare":
        rows = selected(design, record)
        Path(a.tcl).write_text(selection(rows))
        Path(a.receipt).write_text(json.dumps(dict(cells=rows, count=len(rows), original_state_only=True), indent=1) + "\n")
        print(f"OT_CONST_DFF selected {len(rows)} existing capture FFs")
    else:
        verify(design, record["cells"])
        print(f"OT_CONST_DFF mapped {len(record['cells'])} existing capture FFs: PASS")


if __name__ == "__main__":
    main()
