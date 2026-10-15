#!/usr/bin/env python3
"""Census actual clock sinks recursively in Yosys proc/opt hierarchical JSON.

This is a conservative source-state gate, never a CTS or routed-view claim.
Clock ports must actually reach sequential cells; unused ports do not count.
"""
import argparse
import collections
import json
from pathlib import Path


def census(source):
    modules = json.loads(Path(source).read_text())["modules"]
    top = "ot_s81_hcx_projection_partition"
    roots, owners, macros = (collections.Counter() for _ in range(3))
    macro_clocks = collections.Counter()
    port_names = {}
    for name, port in modules[top]["ports"].items():
        for index, bit in enumerate(port["bits"]):
            port_names[bit] = name if len(port["bits"]) == 1 else f"{name}[{index}]"

    def walk(name, path, bindings, owner):
        for cell_name, cell in modules[name].get("cells", {}).items():
            kind = cell["type"]
            child_path = path + "/" + cell_name
            if kind in modules:
                if modules[kind].get("attributes", {}).get("blackbox"):
                    macros[kind] += 1
                    for pin, bits in cell["connections"].items():
                        if pin.lower() in ("clk", "clock", "ck"):
                            for bit in bits:
                                macro_clocks[str(bindings.get(bit, (path, bit)))] += 1
                    continue
                child_bindings = {}
                for pin_name, port in modules[kind]["ports"].items():
                    for pin, net in zip(port["bits"], cell["connections"].get(pin_name, [])):
                        child_bindings[pin] = bindings.get(net, (path, net))
                child_owner = owner
                if kind == "ot_s81_hcx_hcp_lane8" or "ot_s81_hcx_hcp_bank" in kind or cell_name == "u_tree":
                    child_owner = child_path
                walk(kind, child_path, child_bindings, child_owner)
            elif kind.startswith("$") and "ff" in kind.lower():
                width = len(cell["connections"].get("Q", []))
                clocks = cell["connections"].get("CLK", cell["connections"].get("C", []))
                clock_names = [str(bindings.get(bit, (path, bit))) for bit in clocks]
                roots[",".join(clock_names)] += width
                owners[owner] += width

    bindings = {bit: port_names[bit] for port in modules[top]["ports"].values() for bit in port["bits"]}
    walk(top, "top", bindings, "shell")
    return {"scope": "Yosys hierarchical proc/opt source-state census; no mapped area, CTS or pin reach qualification",
            "clock_roots": dict(roots), "hard_owners": dict(owners), "actual_macros": dict(macros),
            "macro_clock_pins": dict(macro_clocks),
            "total_FF_bits": sum(roots.values()), "largest_root_bits": max(roots.values()),
            "all_roots_le_15000": max(roots.values()) <= 15000}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = census(args.source)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("total_FF_bits", "largest_root_bits", "all_roots_le_15000")}, indent=2))
