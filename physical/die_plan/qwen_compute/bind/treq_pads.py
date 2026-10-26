#!/usr/bin/env python3
"""BINDER3: R8 members for the QC-P5-TIE treq lanes (plan e3f313354; not in the QC-P5 r8 table @c0152774b) in the r8
member schema, for asbuilt.land_r8_extra: each treq hop lands with its cmd twin (pad = max cmd landed - treq bound on
the same source leaf -> sink leaf hop, 0 when the hop has no cmd twin), so treq and cmd keep their as-built relative
timing at every slice entry (COORD 18:4x: W5 0 .. E5 11 = the leaf-internal 1 edge/slice only).
    treq_pads.py BIND_DIR OUT.json"""
import json
import sys
bg = json.load(open(f"{sys.argv[1]}/bus_groups.json"))
cmd, treq = {}, []
for g in bg["landing"]:
    for m in g["members"]:
        src = m["source"].rpartition(".")[0]
        if m["sink_port"] == "cmd_i":
            cmd[(src, g["sink"])] = max(cmd.get((src, g["sink"]), 0), m["landed_stages"])
        if m["sink_port"] == "treq_i":
            treq.append((g, m, src))
out = []
for g, m, src in treq:
    c = cmd.get((src, g["sink"]))
    pad = max(0, c - m["bound_stages"]) if c is not None else 0
    for a, b in m["sink_bits"]:
        out.append(dict(id=f"{g['sink']}.treq_i[{a}:{b}]<-{m['source']}@{m['asbuilt_stages']}", sink=g["sink"],
                        sink_part=g["sink_part"], src_part=g["src_part"], sink_port="treq_i", sink_bits=[[a, b]],
                        source=m["source"], asbuilt=m["asbuilt_stages"], bound=m["bound_stages"], pad=pad,
                        landed=m["bound_stages"] + pad, lane=m["lane"], cmd_twin_landed=c))
json.dump(dict(schema="opentallas.die_plan.r8_landing.v1", die=bg["die"], kind="treq_twin_pads",
               note=__doc__, members=out), open(sys.argv[2], "w"), indent=1)
print(len(out), "members,", sum(x["pad"] * (x["sink_bits"][0][1] - x["sink_bits"][0][0] + 1) for x in out), "pad bits x stages")
