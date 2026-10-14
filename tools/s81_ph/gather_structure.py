#!/usr/bin/env python3
"""Elaborate the physical clock-mode gather parent; refuse logic or shared leaf clocks.

This checks the hierarchy against derived blackbox leaf interfaces. It is not
routed timing, pin assignment, throughput or behavioural qualification.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--strip", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    leaf = (ROOT / "rtl/dsrom_sys/s81_ph/ot_s81ph_root_leaf.sv").read_text()
    ctl = (ROOT / "rtl/dsrom_sys/s81_ph/dsfd_gth_ctl.sv").read_text()
    stubs = []
    for name, source in [("dsfd_gth_rw", leaf), ("dsfd_gth_re", leaf), ("dsfd_gth_ctl", ctl)]:
        head = re.search(r"module " + name + r"\s*(?:#\(.*?\)\s*)?\((.*?)\);", source, re.S)
        if head is None:
            raise RuntimeError(f"missing interface: {name}")
        stubs.append(f"(* blackbox *) module {name} ({head[1]}); endmodule\n")
    if args.strip:
        manifest=json.loads((ROOT / "tools/s81_ph/gather_strip_instances.json").read_text())["instances"]
        for name in sorted({v["master"] for v in manifest}):
            width=int(name.split("_")[2]);bus="" if width==1 else f"[{width-1}:0] "
            stubs.append(f"(* blackbox *) module {name}(input wire ck,rs,input wire {bus}i,output wire {bus}o);endmodule\n")
    stub = args.out / "leaves.v"
    stub.write_text("\n".join(stubs))
    parent = ROOT / "rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv"
    netlist = args.out / "parent.json"
    # File paths are Yosys tokens; no shell interpretation is involved.
    strip_read=f"read_verilog -sv {ROOT / 'rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv'}; " if args.strip else ""
    defs="-DS81PH_GTH_CONTROL_STRIP " if args.strip else ""
    script = (f"read_verilog -sv {stub}; {strip_read}read_verilog -sv {defs}-DS81PH_GTH_HARD "
              f"-DS81PH_GTH_DIE_CLOCKS {parent}; "
              f"hierarchy -check -top dsfd_sp_gather_c; proc; flatten; opt; "
              f"write_json {netlist}")
    with (args.out / "yosys.log").open("w") as log:
        subprocess.run(["yosys", "-p", script], stdout=log, stderr=subprocess.STDOUT, check=True)
    top = json.loads(netlist.read_text())["modules"]["dsfd_sp_gather_c"]
    cells = list(top["cells"].values())
    counts = {name: sum(cell["type"] == name for cell in cells)
              for name in ("dsfd_gth_rw", "dsfd_gth_re", "dsfd_gth_ctl")}
    assert counts == {"dsfd_gth_rw": 16, "dsfd_gth_re": 16, "dsfd_gth_ctl": 1}, counts
    assert len(cells) == (166 if args.strip else 33), "parent contains logic rather than hard leaves and wires"
    ck_bits = top["ports"]["ck_l"]["bits"]
    assert len(ck_bits) == 32 and len(set(ck_bits)) == 32
    clocks = [cell["connections"]["ck"][0] for cell in cells if cell["type"] in ("dsfd_gth_rw","dsfd_gth_re")]
    assert sorted(clocks) == sorted(ck_bits), "leaf clocks shared, missing or buffered"
    ctl_cell = next(cell for cell in cells if cell["type"] == "dsfd_gth_ctl")
    assert ctl_cell["connections"]["ck"] == top["ports"]["ck"]["bits"]
    assert ctl_cell["connections"]["ckv"] == top["ports"]["ckv"]["bits"]
    if args.strip:
        relay_cells=[c for c in cells if c['type'].startswith('dsfd_rly_')]
        assert len(relay_cells)==133
        assert sorted(c['connections']['ck'][0] for c in relay_cells)==sorted(top['ports']['ck_r']['bits'])
        for c in relay_cells:
            serial=c['connections']['ck']==[top['ports']['ck_r']['bits'][132]]
            assert c['connections']['rs']==top['ports']['rsv' if serial else 'rst']['bits']
    result = {"gate": "GATHER_STRUCTURE PASS", "counts": counts, "parent_logic_cells": 0,
              "leaf_clock_pins": 32, "relay_clock_pins":133 if args.strip else 0, "total_clock_pins":167 if args.strip else 34, "control_clock_pins": 2,
              "limitations": "no routed view, clock insertion, pin, throughput or behavioural proof"}
    (args.out / "verdict.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
