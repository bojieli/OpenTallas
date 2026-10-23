#!/usr/bin/env python3
"""FT-S81 10-23: structural audit of a pushdown.py frame ft wrapper against its ft spec.

PASS iff (1) the kit top is instantiated exactly once, every kit port connected to the wrapper port of the same name
(the frame is functionally unmodified), (2) every ft path of the spec is ftK_i -> stage 0 -> ... -> stage S-1 -> ftK_o
through exactly `stages` ft_pipe_reg / ot_dvrly_st instances of width `bits`, all on the declared clock, and (3) nothing
else reads or drives an ft net.  --mutate drop-stage removes the last stage of path 0 first (negative control: must FAIL).
Prints FT_WRAPPER_AUDIT PASS|FAIL <reason>.
"""
import argparse
import json
import re
import sys


def audit(text, spec, kit_top, clock):
    inst = re.findall(rf"^\s*{re.escape(kit_top)}\b[^;]*?\bu_kit\s*\((.*?)\);", text, re.S | re.M)
    if len(inst) != 1:
        return f"kit top {kit_top} instantiated {len(inst)} times"
    for port, net in re.findall(r"\.(\w+)\s*\(\s*([^)]*?)\s*\)", inst[0]):
        if port != net:
            return f"kit port {port} connected to {net!r}, not the same-name wrapper port"
    st = re.findall(r"^\s*(ft_pipe_reg|ot_dvrly_st)\s*#\(\.W\((\d+)\)[^)]*\)\s*(\w+)\s*\((.*?)\);", text, re.S | re.M)
    conn = {}
    for mod, w, name, body in st:
        pins = dict(re.findall(r"\.(\w+)\s*\(\s*([^)]*?)\s*\)", body))
        conn[name] = (int(w), pins)
    used = set()
    for p in spec["paths"]:
        k, bits, stages = p["path"], p["bits"], p["stages"]
        net = p["in"]
        for s in range(stages):
            name = f"ft{k}_s{s}"
            if name not in conn:
                return f"path {k}: stage {name} missing"
            w, pins = conn[name]
            if w != bits or pins.get("i") != net or pins.get("ck") != clock:
                return f"path {k}: stage {name} W={w} i={pins.get('i')} ck={pins.get('ck')} (want {bits}/{net}/{clock})"
            used.add(name)
            net = pins.get("o")
        if net != p["out"]:
            return f"path {k}: last stage drives {net}, not {p['out']} ({stages} stages expected)"
    extra = sorted(set(conn) - used)
    if extra:
        return f"stations outside the spec paths: {extra}"
    for p in spec["paths"]:
        for k_net in (p["in"], p["out"]):
            n = len(re.findall(rf"\b{re.escape(k_net)}\b", text))
            if n != 2:      # port declaration + its one station pin
                return f"ft net {k_net} referenced {n} times (declaration + one station pin expected)"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("wrapper"); ap.add_argument("spec")
    ap.add_argument("--kit-top", required=True); ap.add_argument("--clock", required=True)
    ap.add_argument("--mutate", choices=["drop-stage"])
    a = ap.parse_args()
    text = open(a.wrapper).read(); spec = json.load(open(a.spec))
    if a.mutate == "drop-stage":
        p = spec["paths"][0]; last = p["stages"] - 1
        text = re.sub(rf"^\s*\w+\s*#\([^;]*?\)\s*ft{p['path']}_s{last}\s*\(.*?\);\n", "", text, flags=re.S | re.M)
    why = audit(text, spec, a.kit_top, a.clock)
    print("FT_WRAPPER_AUDIT " + ("PASS" if why is None else "FAIL " + why)
          + f" paths={len(spec['paths'])} bits={sum(p['bits'] for p in spec['paths'])}")
    sys.exit(0 if why is None else 1)


if __name__ == "__main__":
    main()
