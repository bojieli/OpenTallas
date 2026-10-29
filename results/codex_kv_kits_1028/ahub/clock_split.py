#!/usr/bin/env python3
"""Materialize the canonical q5 AHUB three co-timed clock roots, without datapath edits.

ck[0] clocks the register/reciprocal logic, ck[1] the south zh pair, ck[2]
the north zh pair. The source clone substitutes only the four zh clock pins.
"""
import argparse
import json
import re
from pathlib import Path


def split(source):
    match = re.search(r"^module qkd_ahub_static_dw\b.*?^endmodule\b", source, re.M | re.S)
    if match is None:
        raise ValueError("exactly one qkd_ahub_static_dw module required")
    original = match.group()
    old_pin = "ot_nhb_zh u_zh (.clk(ck),"
    new_pin = "ot_nhb_zh u_zh (.clk(ck_zh[(a < 2) ? 0 : 1]),"
    if original.count(old_pin) != 1:
        raise ValueError("expected the four-way g_zh generate clock connection")
    clone = original.replace("module qkd_ahub_static_dw", "module qkd_ahub_static_dw_ck3", 1)
    decl = "    input  wire          ck,"
    if clone.count(decl) != 1:
        raise ValueError("expected one core clock declaration")
    extra = "\n    input  wire [1:0]    ck_zh,"
    clone = clone.replace(decl, decl + extra, 1).replace(old_pin, new_pin, 1)
    # With co-timed clock roots, the full cloned source must be literally identical
    # to the original after substitution. This checks every datapath/control token.
    collapsed = clone.replace("module qkd_ahub_static_dw_ck3", "module qkd_ahub_static_dw", 1)
    collapsed = collapsed.replace(extra, "", 1).replace(new_pin, old_pin, 1)
    if collapsed != original:
        raise ValueError("the transformation changed a non-clock token")
    return source + "\n// Canonical q5 dedicated macro clock drops; 0 added cycles.\n" + clone + "\n"


def wrapper(source):
    if source.count("input wire [0:0] ck,") != 1 or source.count(".ck(ck[0]),") != 1:
        raise ValueError("unexpected source wrapper clock declaration/connection")
    source = source.replace("input wire [0:0] ck,", "input wire [2:0] ck,", 1)
    source = source.replace("qkd_ahub_static_dw #(", "qkd_ahub_static_dw_ck3 #(", 1)
    return source.replace(".ck(ck[0]),", ".ck(ck[0]), .ck_zh(ck[2:1]),", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    src = a.repo / "results/codex_kv_kits_1028/ahub"
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "qkd_ahub.sv").write_text(wrapper((src / "qkd_ahub.sv").read_text()))
    (a.out / "qkd_ahub_static_dw.sv").write_text(split((a.repo / "rtl/hdc/nearhbm/qkd_ahub_static_dw.sv").read_text()))
    d = json.loads((src / "core_source.json").read_text())
    # The result directory lives inside the committed tree, so all core sources
    # remain repo-relative in the frozen kit record.
    rel = a.out.relative_to(a.repo)
    d["files"] = [str(rel / Path(f).name) if Path(f).name in ("qkd_ahub.sv", "qkd_ahub_static_dw.sv") else f for f in d["files"]]
    d["port_decl"]["ck"] = ["input", 2, 0]
    d["pin_bits"].extend(["ck[1]", "ck[2]"])
    d["classes"]["clk"] = 3
    d["pin_class"].update({"ck[1]": "clk", "ck[2]": "clk"})
    d["boundary_role"] = {"ck": "clk", "rst_n": "reset"}
    d["clock_split"] = {"roots": ["registers+recip", "south zh[0:1]", "north zh[2:3]"], "cycles_added": 0,
                        "proof": "co-timed substitution restores full original module byte-for-byte"}
    (a.out / "core.json").write_text(json.dumps(d, indent=2) + "\n")


if __name__ == "__main__":
    main()
