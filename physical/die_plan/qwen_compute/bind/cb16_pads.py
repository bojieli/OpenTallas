"""QC-TOK 10-24: CB16 reduction-tree alignment pads for a bound QC top (cause B of STEWARD-TOKj, re-derived).

Each CB16 node tile adds n_a + n_b on one cycle (qfd_tile_nk_rp2_45: sticky mis_q when the two leg valids differ).  The
arrival shift of a leg = (landed - as-built) accumulated along its path: the fabric x/go delivery to the producing tile
(u_fab.u_x_c_r -> tile.tap) gives the tile's t_out shift; a node's n_y carries the later of its legs.  The earlier side
of every skewed node gets the MINIMUM pad (its r8 member pad + skew), nothing else.  Output = r8-member-schema table for
asbuilt.land_r8_extra (authoritative for the ids it lists).

    cb16_pads.py BIND_DIR R8_TABLE OUT.json
"""
import json, re, sys
from collections import defaultdict
bdir, table, outp = sys.argv[1:4]
sinks = json.load(open(bdir + "/bind_sinks.json"))
bg = json.load(open(bdir + "/bus_groups.json"))
r8 = {m["id"]: m for m in json.load(open(table))["members"]}
asb, gid = {}, {}
for g in bg["landing"]:
    if not g["sink"].startswith("c16_"):
        continue
    for m in g["members"]:
        sb = ",".join(f"{a}:{b}" for a, b in m["sink_bits"])
        mid = f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m['asbuilt_stages']}"
        for i in [i for a, b in m["sink_bits"] for i in range(a, b + 1)]:
            asb[(g["sink"], m["sink_port"], i)] = m["asbuilt_stages"]
            gid.setdefault((g["sink"], m["sink_port"]), set()).add(mid)
inp = defaultdict(dict)
for k, v in sinks.items():
    if not k.startswith("c16_") or v[0] != "pin":
        continue
    lp, bit = k.rsplit("[", 1)
    leaf, port = lp.rsplit(".", 1)
    if port in ("tile_id", "rst_n", "sidx") or "tie" in v[1]:
        continue
    b = int(bit[:-1])
    sl, sp = v[1].rsplit("[", 1)[0].rsplit(".", 1)
    a = asb.get((leaf, port, b))
    off = 0 if a is None else v[2] - a
    cur = inp[leaf].get(port)
    if cur is None or off > cur[2]:
        inp[leaf][port] = (sl, sp, off)
memo = {}
def sig(leaf, po, d=0):
    if (leaf, po) in memo:
        return memo[(leaf, po)]
    if d > 80 or leaf not in inp:
        return 0
    memo[(leaf, po)] = 0
    ins = inp[leaf]
    if re.search(r"\.u_t_\d_\d$", leaf):
        if po == "t_out":
            s = ins.get("tap")
            r = sig(s[0], s[1], d + 1) + s[2] if s else 0
        else:
            xs = [sig(s[0], s[1], d + 1) + s[2] for p, s in ins.items() if p in ("n_a", "n_b")]
            r = max(xs) if xs else 0
    else:
        xs = [sig(s[0], s[1], d + 1) + s[2] for s in ins.values()]
        r = max(xs) if xs else 0
    memo[(leaf, po)] = r
    return r
mem, sites, bad = [], defaultdict(set), []
for leaf in sorted(inp):
    if not re.search(r"\.u_t_\d_\d$", leaf) or "n_a" not in inp[leaf] or "n_b" not in inp[leaf]:
        continue
    arr = {s: sig(inp[leaf][s][0], inp[leaf][s][1]) + inp[leaf][s][2] for s in ("n_a", "n_b")}
    hi = max(arr.values())
    for side, x in arr.items():
        if x == hi:
            continue
        ids = gid.get((leaf, side), set())
        if not ids:
            bad.append(f"{leaf}.{side}: early side is not a crossing member (intra-partition leg)")
            continue
        for mid in sorted(ids):
            t = r8.get(mid)
            if t is None:
                bad.append(f"{mid}: not in the r8 table")
                continue
            mem.append(dict(t, pad=t["pad"] + hi - x, landed=t["landed"] + hi - x, tree_align=hi - x,
                            why=f"CB16 node {leaf.split('.')[-1]}: {side} lands {hi - x} cycle(s) before the other leg"))
        sites[f"{leaf.split('.')[-1]}.{side}"].add(hi - x)
if bad:
    sys.exit("\n".join(bad[:20]))
bits = lambda m: sum(b - a + 1 for a, b in m["sink_bits"])
summ = dict(members=len(mem), clusters=len({m["sink"].split(".")[0] for m in mem}),
            pad_flops=sum(m["tree_align"] * bits(m) for m in mem), sites={k: sorted(v) for k, v in sorted(sites.items())})
json.dump(dict(schema="opentallas.die_plan.r8_landing.v1", die=bg["die"], kind="cb16_tree_align_pads", note=__doc__,
               r8_table=str(table), summary=summ, members=mem), open(outp, "w"), indent=1)
print(json.dumps(summ))
