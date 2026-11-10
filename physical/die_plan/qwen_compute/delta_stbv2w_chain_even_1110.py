#!/usr/bin/env python3
"""DIE-QC-97 STBV2W 11-10: chain_even placement groups for slw_st_b_v2__pvc2ec5bfb (sl_W5_st_b), u_u_r7 only.

The W5 station regions take qfd_dv_s8_station_tail1_nb0_orq_mrep (asbuilt substitute_inst).  Its neighbour-out gate reads
a replica cone (u_c3 / u_p3 copy stage -> u_m3 / u_m4 kept mode units) instead of u_m.  In the routed DB of bc65a3535579
the r7 g_nb[z].u_o registers sit by the bottom-face u_bout_x_fe_o, 846-954 um from u_mode_mid (r4..r6: <= 127 um), so a
wirelength GPL alone could leave one long hop.  This adds the existing chain_even form (S81-RCK-4, tools/die_plan/
chain_even.tcl, PRE_DETAIL_PLACE, placement only, no netlist change): per lane z one group
    from u_mode_mid -> stage {u_p3, u_c3} at 1/3 -> cone {u_m3, u_m4} at 2/3 -> to centroid of g_nb[z].u_o
so every hop of the replica path is ~1/3 of the line (~280-320 um, under the ~400 um knee).  Opt-in type key; plans
without it are unchanged.  Refuses a type that already carries chain_even (merge by hand then).
"""
import argparse
import json
from pathlib import Path

TYPE = "slw_st_b_v2__pvc2ec5bfb"
REGIONS = (7,)


def groups():
    out = []
    for r in REGIONS:
        p = r"^u_bound\.u_u_r%d\." % r
        for z in range(4):
            out.append(["stbv2w_r%d_z%d" % (r, z), p + r"u_mode_mid/",
                        [p + r"g_mode_payload\[%d\]\.u_[pc]3/" % z],
                        p + r"g_mode_payload\[%d\]\.u_m[34]/" % z,
                        p + r"g_nb\[%d\]\.u_o/" % z])
    return out


def apply(raw):
    t = raw["partition_types"][TYPE]
    assert {"u_r4", "u_r5", "u_r6", "u_r7"} <= {c["inst"] for c in t["contents"]}, TYPE
    want = {"chains": [], "groups": groups()}
    if "chain_even" in t:
        assert t["chain_even"] == want, "type already has a different chain_even: merge by hand"
        return raw
    t["chain_even"] = want
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    raw = apply(json.loads(Path(a.input).read_text()))
    Path(a.output).write_text(json.dumps(raw, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
