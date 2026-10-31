"""DIE-QC-51 step (5) of the last QC event (COORD 20:43, QC-KITS-AC 20:26 ASK): crowded landing collector boxes.
landing_place.tcl homes, for every collector-tree node n, the collector group u_cland_collect_<n>, the reset copy
u_cland_reset_<n> and every source raw copy u_cland_rst_<src> whose tap relay is n in ONE 4.32 x 4.32-um near() box at
the relay.  With >= 3 groups the earlier ones fill the box and the collector gets 0 capacity (sle_ctl plan_qc49
NO_3_PLACE 'u_cland_collect_rst_n_t13 ... band upper bound 0.0').  Fix (plan data, landing_contract.group_rects_um, the
plan_qc48 stm cle34a73c3 precedent): every collector of a slice type whose box holds >= 5 groups (the failing sle_ctl box holds 7-9; 3-4-group boxes place) gets its OWN adjacent 4.32-um box
(collectors always exist after synthesis; raw copies are optional, so they are never overridden).  The box is the
first of the 8 neighbours (then ring 2) of the relay box inside the outline, clear of hard cores (+halo), landing
bands and every other group box.  Existing overrides are kept.
usage: collector_spread.py PLAN --out PLAN2 --report REP [--min-groups 3]"""
import argparse, hashlib, json, re
from collections import defaultdict

safe = lambda s: re.sub(r"\W", "_", s)
H = 2.16


def near(xy):
    return [xy[0] - H, xy[1] - H, xy[0] + H, xy[1] + H]


def ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def groups_of(t):
    c = t.get("clock", {}).get("landing_contract", {})
    tree, root = c.get("collector_tree"), c.get("collector_root_node")
    if not tree or not root:
        return {}, {}
    xy = {"rst_root_n": tree["root"]}
    adj = defaultdict(list)
    for r in tree["relays"]:
        adj[r["q"]].append(r["d"]); adj[r["d"]].append(r["q"]); xy[r["q"]] = r["xy"]
    box = defaultdict(list)                       # node -> group prefixes in its near box
    for s in c.get("collector_local_sources", []):
        box[f"rst_n_t{s['tap']}"].append("u_cland_rst_" + s["name"])
    parent = {root: None}; todo = [root]
    while todo:
        n = todo.pop()
        for q in adj[n]:
            if q not in parent:
                parent[q] = n; todo.append(q)
    srcs = [f"rst_n_t{s['tap']}" for s in c.get("collector_local_sources", [])] + [s["node"] for s in c.get("collector_children", [])]
    active = set()
    for n in srcs:
        while n is not None:
            active.add(n); n = parent[n]
    for n in active:
        box[n].append("u_cland_collect_" + safe(n))
        if n != "rst_root_n":
            box[n].append("u_cland_reset_" + safe(n))
    return {n: v for n, v in box.items() if n in active}, xy


ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
ap.add_argument("--min-groups", type=int, default=5)
ap.add_argument("--types", default=r"sl[ew]_", help="type-name regex (default: slice types = the event scope)")
a = ap.parse_args()
P = json.load(open(a.plan))
rep = {}
for tn, t in P["partition_types"].items():
    if not re.match(a.types, tn):
        continue
    box, xy = groups_of(t)
    if not box:
        continue
    lc = t["clock"]["landing_contract"]
    W, Hh = t["outline_um"]
    blocked = [[h["origin_um"][0] - h.get("halo_um", 0), h["origin_um"][1] - h.get("halo_um", 0),
                h["origin_um"][0] + h["outline_um"][0] + h.get("halo_um", 0), h["origin_um"][1] + h["outline_um"][1] + h.get("halo_um", 0)]
               for h in t.get("hard_cores", []) if h.get("outline_um") and h.get("origin_um")]
    blocked += [b["rect_um"] for b in lc.get("bands", {}).values() if b.get("rect_um")]
    taken = [near(xy[n]) for n in box]
    over = dict(lc.get("group_rects_um", {}))
    taken += list(over.values())
    for n in sorted(box):
        g = box[n]
        pre = "u_cland_collect_" + safe(n)
        if len(g) < a.min_groups or pre in over:
            continue
        x, y = xy[n]
        cand = [(dx, dy) for r in (1, 2, 3) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if max(abs(dx), abs(dy)) == r]
        cand.sort(key=lambda d: (max(abs(d[0]), abs(d[1])), abs(d[0]) + abs(d[1])))
        for dx, dy in cand:
            r = [round(x - H + dx * 2 * H, 5), round(y - H + dy * 2 * H, 5), round(x + H + dx * 2 * H, 5), round(y + H + dy * 2 * H, 5)]
            if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > Hh:
                continue
            if any(ov(r, b) for b in blocked) or any(ov(r, b) for b in taken):
                continue
            over[pre] = r; taken.append(r)
            rep.setdefault(tn, []).append(dict(node=n, groups=g, relay_xy=[x, y], rect=r))
            break
        else:
            rep.setdefault(tn, []).append(dict(node=n, groups=g, relay_xy=[x, y], rect=None, fail="no free neighbour box"))
    if over != lc.get("group_rects_um", {}):
        lc["group_rects_um"] = over
open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
fails = [(tn, r["node"]) for tn, v in rep.items() for r in v if not r.get("rect")]
summary = dict(types=len(rep), collectors=sum(len(v) for v in rep.values()), fails=fails,
               max_groups=max((len(r["groups"]) for v in rep.values() for r in v), default=0),
               src_sha256=hashlib.sha256(open(a.plan, "rb").read()).hexdigest(),
               dst_sha256=hashlib.sha256(open(a.out, "rb").read()).hexdigest())
json.dump(dict(summary=summary, types=rep), open(a.report, "w"), indent=1)
print(json.dumps(summary))
