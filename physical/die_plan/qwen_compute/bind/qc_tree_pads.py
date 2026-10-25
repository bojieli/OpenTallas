#!/usr/bin/env python3
"""QC-P6-XT1 10-23: CB16 reduction-tree alignment pads (STEWARD-TOKj 22:00 cause B; COORD 23:4x correctness-only pads).

Each CB16 node tile adds n_a + n_b on ONE cycle (qfd_tile_nk_rp2_45, sticky mis_q fault when the two valids differ).
As built the fabric legs were padded to equal arrival; the plan's 4-way cluster split shortens some legs (a00 31 -> 8,
b12 16 -> 4, a22 18 -> 4) and the node sides go out of step.  This adds the MINIMUM stages on the earlier side of each
skewed node (tools/die_plan/regen_constants.tree_pads on the R8-landed depths), nothing else: the column runs and the
rs exit keep the shorter bound depth (the per-cluster result shift is the calendar constant QC_CLUSTER_RESULT_SHIFT).
Output: an r8-member-schema table for asbuilt.land_r8_extra (authoritative for the ids it lists: the plan r8 member
with pad + alignment).

    qc_tree_pads.py BIND_DIR R8_TABLE OUT.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "die_plan"))
import regen_constants as RC  # noqa: E402

bind, table, out = sys.argv[1:4]
bg = json.load(open(Path(bind) / "bus_groups.json"))
r8 = {m["id"]: m for m in json.load(open(table))["members"]}
ms, byid = [], {}
for g in bg["landing"]:
    for m in g["members"]:
        sb = ",".join(f"{a}:{b}" for a, b in m["sink_bits"])
        mid = f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m['asbuilt_stages']}"
        t = r8.get(mid)
        d = dict(sink=g["sink"], port=m["sink_port"], source=m["source"], asb=m["asbuilt_stages"],
                 bound=m["bound_stages"], landed=t["landed"] if t else m["bound_stages"], id=mid)
        ms.append(d)
        byid[(g["sink"], m["sink_port"])] = (d, t)
mem, sites = [], {}
for cl, (c, r), side, pad in RC.tree_pads(ms):
    d, t = byid[(f"{cl}.u_t_{c}_{r}", f"n_{side}")]
    if t is None:
        sys.exit(f"{cl} node ({c},{r}) n_{side}: early side is not an r8 member (intra-partition leg): needs an INNER member")
    x = dict(t, pad=t["pad"] + pad, landed=t["landed"] + pad, tree_align=pad,
             why=f"CB16 node u_t_{c}_{r}: n_{side} lands {pad} cycle(s) before the other side on the R8-landed depths")
    mem.append(x)
    k = f"u_t_{c}_{r}.n_{side} ({t['lane'].split('__')[-1]}, as-built {t['asbuilt']}, bound {t['bound']})"
    sites.setdefault(k, set()).add(pad)
bits = lambda m: sum(b - a + 1 for a, b in m["sink_bits"])
flops = sum(m["tree_align"] * bits(m) for m in mem)
summ = dict(members=len(mem), clusters=len({m["sink"].split(".")[0] for m in mem}), pad_flops=flops,
            sites={k: sorted(v) for k, v in sorted(sites.items())})
json.dump(dict(schema="opentallas.die_plan.r8_landing.v1", die=bg["die"], kind="cb16_tree_align_pads", note=__doc__,
               r8_table=str(table), summary=summ, members=mem), open(out, "w"), indent=1)
print(json.dumps(summ))
