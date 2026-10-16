#!/usr/bin/env python3
"""Count actual SYS state and macro ports in a Yosys proc/opt/memory_map JSON.

Report source clock connectivity separately from proposed hard-child boundaries.
This does not infer new clock roots, die placement, mapped area or CTS evidence.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path


def census(path, top="ot_s81_hcx_projection_sys"):
    modules = json.loads(Path(path).read_text())["modules"]
    roots, owners, macro_counts, macro_roots = (Counter() for _ in range(4))
    comb_owners = {}
    macro_ports, owner_macros, owner_roles, owner_ports = {}, {}, {}, {}
    subtree_bits = Counter()
    latches, memories = [], []
    port_names = {}

    @lru_cache(None)
    def direct_pin_flops(name):
        """Wire-only connectivity to existing FF D/Q, through module boundaries.

        A valid mask or arithmetic before D is deliberately not a direct pin
        capture. This does not claim placement or classify every first FF cone.
        """
        captured, driven = set(), set()
        for cell in modules[name].get("cells", {}).values():
            kind = cell["type"]
            if kind.startswith("$") and "ff" in kind.lower():
                captured.update(cell["connections"].get("D", []))
                driven.update(cell["connections"].get("Q", []))
            elif kind in modules and not modules[kind].get("attributes", {}).get("blackbox"):
                child_d, child_q = direct_pin_flops(kind)
                for pin, port in modules[kind]["ports"].items():
                    for local, parent in zip(port["bits"], cell["connections"].get(pin, [])):
                        if local in child_d:
                            captured.add(parent)
                        if local in child_q:
                            driven.add(parent)
        return captured, driven
    for name, port in modules[top]["ports"].items():
        for i, bit in enumerate(port["bits"]):
            port_names[bit] = name if len(port["bits"]) == 1 else f"{name}[{i}]"

    def walk(name, path, bindings, owner):
        for cell_name, cell in modules[name].get("cells", {}).items():
            kind = cell["type"]
            child_path = path + "/" + cell_name
            if kind in modules:
                child = modules[kind]
                if child.get("attributes", {}).get("blackbox"):
                    macro_counts[kind] += 1
                    owner_macros.setdefault(owner, Counter())[kind] += 1
                    macro_ports[kind] = {p: dict(direction=v["direction"], bits=len(v["bits"]))
                                         for p, v in child["ports"].items()}
                    for pin, bits in cell["connections"].items():
                        if pin.lower() in ("clk", "clock", "ck"):
                            for bit in bits:
                                macro_roots[str(bindings.get(bit, (path, bit)))] += 1
                    continue
                child_bindings = {}
                for pin_name, port in child["ports"].items():
                    for pin, net in zip(port["bits"], cell["connections"].get(pin_name, [])):
                        child_bindings[pin] = bindings.get(net, (path, net))
                child_owner = owner
                if path == "top" or (path.startswith("top/ctl/") and cell_name in ("tree", "scalar")):
                    child_owner = child_path
                    role = ("controller_core" if cell_name == "ctl" and top.endswith("_clocked") else
                            "controller" if cell_name == "ctl" else
                            cell_name if cell_name in ("tree", "scalar") else
                            "half_bank" if cell_name.endswith(".bank") else
                            "lane8" if cell_name.endswith(".lanes") else "unknown")
                    owner_roles[child_owner] = role
                    owner_ports[child_owner] = {p: dict(direction=v["direction"], bits=len(v["bits"]))
                                                for p, v in child["ports"].items()}
                    cap, drv = direct_pin_flops(kind)
                    for pin, port in child["ports"].items():
                        rec = owner_ports[child_owner][pin]
                        rec["direct_FF_D_bits"] = sum(b in cap for b in port["bits"])
                        rec["direct_FF_Q_bits"] = sum(b in drv for b in port["bits"])
                    comb_owners[child_owner] = Counter()
                    owners[child_owner] += 0
                walk(kind, child_path, child_bindings, child_owner)
            elif kind.startswith("$") and "ff" in kind.lower():
                width = len(cell["connections"].get("Q", []))
                clocks = cell["connections"].get("CLK", cell["connections"].get("C", []))
                if not clocks:
                    raise ValueError("state without a clock: " + child_path)
                clock_name = ",".join(str(bindings.get(b, (path, b))) for b in clocks)
                roots[clock_name] += width
                owners[owner] += width
                subtree_bits[path] += width
            elif "latch" in kind.lower():
                latches.append(child_path)
            elif kind.startswith("$mem"):
                memories.append(child_path)
            else:
                comb_owners.setdefault(owner, Counter())[kind] += 1

    walk(top, "top", {bit: port_names[bit] for p in modules[top]["ports"].values()
                      for bit in p["bits"]}, "top_wires")
    if latches or memories:
        raise ValueError(f"unaccounted storage: latches={latches}, memories={memories}")
    roles = {}
    for role in sorted(set(owner_roles.values())):
        counts = [v for k, v in owners.items() if owner_roles.get(k) == role]
        roles[role] = dict(instances=len(counts), FF_bits_total=sum(counts),
                           FF_bits_min=min(counts), FF_bits_max=max(counts))
    return dict(schema="opentallas.s81-hcx-sys-source-census.v1",
                scope="Hierarchical Yosys proc/opt/memory_map source-state census; no technology mapping or physical qualification",
                netlist_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                actual_source_clock_FF_bits=dict(roots), actual_source_clock_macro_pins=dict(macro_roots),
                source_clock_roots=len(roots), total_FF_bits=sum(roots.values()),
                actual_source_largest_clock_FF_bits=max(roots.values()),
                actual_source_root_le_15000=max(roots.values()) <= 15000,
                proposed_hard_boundary_count=len(owner_roles), role_summary=roles,
                boundary_FF_bits=dict(owners), boundary_roles=owner_roles,
                boundary_exact_port_shapes=owner_ports,
                boundary_generic_comb_cells={k: dict(v) for k, v in comb_owners.items()},
                comb_scope="Counts of Yosys generic vector operators, not mapped cell area or timing",
                controller_state_by_module_instance={k: v for k, v in subtree_bits.items()
                                                     if k.startswith("top/ctl")},
                boundary_macros={k: dict(v) for k, v in owner_macros.items()},
                actual_macros=dict(macro_counts), exact_macro_port_shapes=macro_ports,
                boundaries_over_15000={k: v for k, v in owners.items() if v > 15000},
                clock_warning="Source clock ports and hard-child boundaries do not establish physical clock delivery, CTS or pin timing.",
                physical_submit_allowed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("netlist", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--top", default="ot_s81_hcx_projection_sys")
    args = parser.parse_args()
    result = census(args.netlist, args.top)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("total_FF_bits", "source_clock_roots", "role_summary", "actual_macros", "boundaries_over_15000")}, indent=2))
