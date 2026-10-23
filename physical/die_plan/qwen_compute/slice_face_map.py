#!/usr/bin/env python3
"""Die-level slice bus -> slice core port map, from the generated face wrappers (rtl/qwen_dv/qfd_dv_slice2_faces.sv,
tools/qwen_dv/gen_slice_faces.py).  The as-built die (census) names the slice buses by die face (st_wo, ard_eo, ...);
the slice kit floorplans (inputs/fp_*.json) and the landed-parent regions name the core ports (st_dn_o, ch_dn_o, ...).

    python3 slice_face_map.py qfd_dv_slice2_faces.sv > inputs/slice2_face_map.json
Output: {"w": {die_bus: core_port}, "e": {...}} for qfd_dv_slice2_w / qfd_dv_slice2_e.
"""
import json
import re
import sys


def parse(text):
    out = {}
    for m in re.finditer(r"module\s+qfd_dv_slice2_([we])\b(.*?)endmodule", text, re.S):
        side, body = m.group(1), m.group(2)
        wire_of = {}                                              # die bus -> wrapper wire
        for a in re.finditer(r"assign\s+(\w+)\s*=\s*(w_\w+)\s*\[", body):
            wire_of[a.group(1)] = a.group(2)
        for a in re.finditer(r"assign\s+(w_\w+)\s*=\s*\{([^}]*)\}", body):
            for b in a.group(2).split(","):
                wire_of[b.strip()] = a.group(1)
        core = {}
        for c in re.finditer(r"\.(\w+)\((\w+)\)", body.split("u_core", 1)[1]):
            core[c.group(2)] = c.group(1)
        mp = {}
        for p in re.finditer(r"(?:input|output)\s+wire\s+(?:\[[^\]]*\]\s*)?(\w+)", body):
            n = p.group(1)
            if n in core:
                mp[n] = core[n]
            elif n in wire_of and wire_of[n] in core:
                mp[n] = core[wire_of[n]]
        out[side] = mp
    return out


if __name__ == "__main__":
    print(json.dumps(parse(open(sys.argv[1]).read()), indent=1, sort_keys=True))
