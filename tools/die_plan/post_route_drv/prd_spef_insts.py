#!/usr/bin/env python3
"""prd_spef_insts.py SPEF OUT -- list the logic instances a SPEF connects (DIE-S81-50 11-03, stale-staging class).

The ECO hook reads the routed SPEF onto the staged seed DB.  When the seed is not the DB the SPEF was extracted from
(S81 l4: kit 6_final.{odb,spef} = a post-route hold ECO with 1,300 hxeco_* buffers; the seed 5_2_route.odb predates
it), every ECO-only instance is "not found" (STA-1648) and the repair later dies in RSZ-0074 "found route to 23 pins,
expected 24" after ~30 min.  prd_mk.sh writes this list; prd_hook.tcl checks every logic instance exists in the seed
before it reads the SPEF and stops at once with OT_PRD STAGE_MISMATCH otherwise.

OUT: one "<instance> <master>" line per instance on a *CONN *I line (name map resolved, SPEF escapes kept; the hook
tries the name as written, then unescaped).
Physical-only masters (antenna diodes, fillers, taps, decaps) are skipped: a grt seed legitimately lacks the diodes
the detailed route inserts.
"""
import re
import sys

PHYS = re.compile(r"^(ANTENNA|FILLER|FILLCELL|TAPCELL|DECAP)", re.I)


def instances(lines):
    names, out, in_map = {}, {}, False
    for ln in lines:
        if ln.startswith("*NAME_MAP"):
            in_map = True
            continue
        if in_map:
            if ln.startswith("*") and not ln.startswith(("*PORTS", "*POWER_NETS", "*GROUND_NETS", "*D_NET")):
                parts = ln.split(None, 1)
                if len(parts) == 2 and parts[0][1:].isdigit():
                    names[parts[0]] = parts[1].strip()
                    continue
            if ln.strip() == "":
                continue
            in_map = False
        if not ln.startswith("*I "):
            continue
        f = ln.split()
        pin = f[1]
        master = f[f.index("*D") + 1] if "*D" in f[:-1] else ""
        inst = pin.rsplit(":", 1)[0]
        inst = names.get(inst, inst)
        if PHYS.match(master):
            continue
        out.setdefault(inst, master)
    return out


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    with open(argv[1], errors="replace") as f:
        ins = instances(f)
    with open(argv[2], "w") as f:
        for i in sorted(ins):
            f.write(f"{i} {ins[i]}\n")
    print(f"prd_spef_insts: {len(ins)} logic instances in {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
