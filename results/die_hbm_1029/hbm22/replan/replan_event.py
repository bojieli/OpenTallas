#!/usr/bin/env python3
"""DIE-HBM-22 re-plan event (die-local, opt-in; no shared tool changed).

    python3 replan_event.py TOOLS_DIR PLANDIR VARIANT_JSON OUTDIR [--rows92 rows92.json] [--near-um 1200]

VARIANT_JSON = {"name", "A": [NW names west->east], "C": [...], "size": {NW_name: width_um}, "rowh": {"A":1555.2,"C":1572.48}}
NE partitions = MY mirror of the NW order (x_ne = W - x_nw - w), same type outline as the NW partner's type.

Steps: (1) move origins (rows A y 4510.08, C y 10385.28) and set outlines (size override + row height) on the types of
moved partitions; (2) drop every lane with a port on a moved partition: its ports, endpoint buses, ft slots, latency
entries, latency_groups members kept by name (reported); (3) re-add the dropped lanes with the SAME lane id / end bus
names (L<id>_o / L<id>_i) via lane_add.Builder.build_one (ADJ = one port; else the shortest abutment path <= max_hops,
stations = ceil(route / ft_station_max)); (4) add the 92 far rows via lane_add.Builder (near 1200) on the result;
(5) write die_plan.json + replan_report.json (per lane old/new cycles, FAR/failed lists).
NOT UPDATED (reported): die clock h-tree/mesh sidecars (clock_taps_die.json, clock_htree.json, entries.json),
pg_bumps.json, type internal_stations (face-bus endpoints kept by name; windows may have moved), die_ft_bands.
All numbers are plan arithmetic: UNCHECKED until G0/G0C/bind.
"""
import sys, json, copy, os, time, argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tools"); ap.add_argument("plan"); ap.add_argument("variant"); ap.add_argument("out")
ap.add_argument("--rows92"); ap.add_argument("--near-um", type=float, default=1200.0)
ap.add_argument("--max-hops", type=int, default=6)
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S
import lane_add as LA

t0 = time.time()
plan_dir, out = Path(a.plan), Path(a.out)
raw = json.loads((plan_dir / "die_plan.json").read_text())
V = json.loads(Path(a.variant).read_text())
W = raw["die"]["outline_um"][0]
ROWY = {"A": 4510.08, "C": 10385.28}
ROWH = V.get("rowh", {"A": 1555.2, "C": 1572.48})
parts = {p["name"]: p for p in raw["partitions"]}
T = raw["partition_types"]

def mirror(n):
    return "NE" + n[2:]

moved, outline_changes = set(), []
for row in ("A", "C"):
    x = 0.0
    for n in V[row]:
        for nm in (n, mirror(n)):
            p = parts[nm]
            t = T[p["type"]]
            w = float(V.get("size", {}).get(n, t["outline_um"][0]))
            h = float(ROWH[row])
            if [round(w, 4), round(h, 4)] != [round(v, 4) for v in t["outline_um"]]:
                outline_changes.append(dict(type=p["type"], old=list(t["outline_um"]), new=[w, h]))
                t["outline_um"] = [w, h]
            o = [round(x, 4), ROWY[row]] if nm == n else [round(W - x - w, 4), ROWY[row]]
            if [round(v, 3) for v in p["origin_um"]] != [round(v, 3) for v in o]:
                moved.add(nm)
            p["origin_um"] = o
        x += float(V.get("size", {}).get(n, T[parts[n]["type"]]["outline_um"][0]))
    assert x <= 13357.44 + 0.01, (row, x)
moved |= {r["type"] for r in []}
# outline-changed types count as moved (their faces change)
for oc in outline_changes:
    moved |= {p["name"] for p in raw["partitions"] if p["type"] == oc["type"]}

P0 = S.Plan(raw)
ports = {p["id"]: p for p in raw["ports"]}
drop = []
for ln in raw["lanes"]:
    pp = [ports[q] for q in ln["ports"]]
    if any(x["src"]["part"] in moved or x["dst"]["part"] in moved for x in pp):
        drop.append(ln)
old_lat = raw["latency"]["lanes"]
dropped = []
for ln in drop:
    pp = [ports[q] for q in ln["ports"]]
    src, dst = pp[0]["src"]["part"], pp[-1]["dst"]["part"]
    chain = [src] + [x["dst"]["part"] for x in pp]
    cr = P0.lane_crossings(ln["id"])
    dropped.append(dict(id=ln["id"], src=src, dst=dst, bits=int(pp[0]["width"]), kind=pp[0].get("kind", "data"),
                        old_chain=chain, old_cycles=old_lat.get(ln["id"], {}).get("cycles"),
                        ob=pp[0]["src"]["bus"], ib=pp[-1]["dst"]["bus"], note=ln.get("note", ""),
                        slots=[(c[0], c[1]) for c in cr if c[1]]))
dids = {d["id"] for d in dropped}
dports = {q for ln in drop for q in ln["ports"]}
# remove buses / slots
rm_bus = {}
for d in dropped:
    rm_bus.setdefault(parts[d["src"]]["type"], set()).add(d["ob"]) if d["src"] in parts else None
    rm_bus.setdefault(parts[d["dst"]]["type"], set()).add(d["ib"]) if d["dst"] in parts else None
rm_slot = {}
for d in dropped:
    for part, sl in d["slots"]:
        rm_slot.setdefault(parts[part]["type"], set()).add(sl)
nb = ns = 0
for tn, names in rm_bus.items():
    L0 = len(T[tn].get("buses", []))
    T[tn]["buses"] = [b for b in T[tn].get("buses", []) if b["name"] not in names]
    nb += L0 - len(T[tn]["buses"])
for tn, names in rm_slot.items():
    L0 = len(T[tn].get("ft_slots", []))
    T[tn]["ft_slots"] = [s for s in T[tn].get("ft_slots", []) if s["name"] not in names]
    ns += L0 - len(T[tn]["ft_slots"])
raw["ports"] = [p for p in raw["ports"] if p["id"] not in dports]
raw["lanes"] = [l for l in raw["lanes"] if l["id"] not in dids]
for i in dids:
    old_lat.pop(i, None)
print(f"moved {len(moved)} partitions, outline changes {len(outline_changes)}, dropped lanes {len(dropped)} "
      f"(buses {nb}, slots {ns}) {time.time()-t0:.0f}s", flush=True)

# phase 1: re-add dropped lanes with their ids (no cycle-match: the pair's lanes are all being rebuilt)
_dc = copy.deepcopy
LA.copy = type("C", (), {"deepcopy": staticmethod(lambda x: x)})   # build_one's pre-write copy is unused w/o cycle match
B = LA.Builder(raw, near_um=1e9, max_hops=a.max_hops, require_cycle_match=False)
B.shared = set()                                                   # rebuilt lanes keep their shared-type crossings
rep1 = dict(rebuilt=[], failed=[])
dropped.sort(key=lambda d: (d["src"].startswith("NE_") or d["dst"].startswith("NE_"), -d["bits"]))

import heapq


def path_ex(B, a, b, ban=(), max_hops=8):
    """shortest abutment path a..b by centre distance; PHY/root/io only as an endpoint; `ban` = forbidden edges."""
    dist, prev, hq = {a: 0.0}, {}, [(0.0, a, 0)]
    while hq:
        d_, u, n = heapq.heappop(hq)
        if u == b:
            break
        if d_ > dist.get(u, 1e18) + 1e-6 or n >= max_hops:
            continue
        for v in B.neighbours(u):
            if v != b and (v.startswith("PHY") or v == "root" or v.endswith("_io")):
                continue
            if (u, v) in ban:
                continue
            cu, cv = LA.centre(B.P, u), LA.centre(B.P, v)
            nd = d_ + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1])
            if nd < dist.get(v, 1e18) - 1e-6:
                dist[v], prev[v] = nd, u
                heapq.heappush(hq, (nd, v, n + 1))
    if b not in prev:
        return None
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


def candidates(B, a, b, bits, old_chain=None):
    out, seen = [], set()

    def add(kind, ch):
        if ch and tuple(ch) not in seen:
            seen.add(tuple(ch)); out.append((kind, None, ch))
    e = LA.shared_edge(B.P, a, b)
    need = bits / 6.0 + 4.0
    if e and e[2] - e[1] >= need:
        add("adj", [a, b])
    if old_chain and all(LA.shared_edge(B.P, u, v) for u, v in zip(old_chain, old_chain[1:])):
        add("path", list(old_chain))
    add("path", path_ex(B, a, b, ban={(a, b)}))
    p1 = path_ex(B, a, b, ban={(a, b)})
    if p1 and len(p1) > 2:   # an alternative avoiding the first crossed partition
        add("path", path_ex(B, a, b, ban={(a, b), (a, p1[1])}))
        add("path", path_ex(B, a, b, ban={(a, b), (p1[-2], b)}))
    if e and (a, b) not in [(c[2][0], c[2][-1]) for c in out if len(c[2]) == 2]:
        add("adj", [a, b])
    return out


def add_lane(B, d, cands, rep, ids):
    for k in (1, 2, 3, 4):
        widths = [d["bits"] // k + (1 if i < d["bits"] % k else 0) for i in range(k)]
        got = []
        for j, wbits in enumerate(widths):
            lid = ids[0] if j == 0 else f"{ids[0]}s{j}"
            B.new_id = (lambda lid_: (lambda a_, b_, part=0: lid_))(lid)
            r1 = None
            for kind, tl, chain in cands:
                if got and chain != got[0]["chain"]:
                    continue
                r1 = B.build_one(d["src"], d["dst"], wbits, chain, kind, tl, record=False)
                if r1:
                    break
            if r1 is None:
                break
            got.append(r1)
        if len(got) == k:
            return got
        if got:
            rep["failed"].append(dict(id=ids[0], src=d["src"], dst=d["dst"], why=f"partial split {len(got)}/{k}: {B._why}"))
            return got
    rep["failed"].append(dict(id=ids[0], src=d["src"], dst=d["dst"], bits=d["bits"], why=B._why,
                              chains=[c[2] for c in cands]))
    return None


for i_, d in enumerate(dropped):
    if i_ % 20 == 0:
        print(f"  p1 {i_}/{len(dropped)} {time.time()-t0:.0f}s", flush=True)
    cands = candidates(B, d["src"], d["dst"], d["bits"], d["old_chain"])
    ok = add_lane(B, d, cands, rep1, [d["id"]])
    if not ok:
        continue
    for r1 in ok:
        rep1["rebuilt"].append(dict(id=r1["lane"], src=d["src"], dst=d["dst"], bits=r1["bits"], kind=r1["kind"],
                                    chain=r1["chain"], cycles=r1["cycles"], old_cycles=d["old_cycles"],
                                    old_chain=d["old_chain"], split=len(ok)))
    raw = B.raw
# mirror naming (plan convention): the NE mirror lane L<n>m uses the NW lane's bus / slot names (types shared by
# NW/NE then carry ONE bus per name).  Rename L<n>m* -> L<n>* on the NE lane's ports/types; on a shared type the two
# declarations must coincide (mirror-symmetric allocation) -> dedupe, else report a conflict.
def mirror_names(raw, rebuilt_ids, report):
    pl = {p["name"]: p for p in raw["partitions"]}
    T_ = raw["partition_types"]
    lanes = {l["id"]: l for l in raw["lanes"]}
    ports_ = {p["id"]: p for p in raw["ports"]}
    nren = 0
    for lid in sorted(rebuilt_ids):
        base = None
        for cand in (lid[:-1] if lid.endswith("m") else None,
                     (lid.split("ms")[0] + "s" + lid.split("ms")[1]) if "ms" in lid else None):
            if cand and cand in rebuilt_ids:
                base = cand
        if not base or lid not in lanes:
            continue
        pre_old = lid.split("s")[0] if "ms" in lid else lid
        pre_new = base.split("s")[0] if "ms" in lid else base
        def rn(nm):
            return pre_new + nm[len(pre_old):] if nm.startswith(pre_old) else nm
        touched = set()
        for q in lanes[lid]["ports"]:
            pr = ports_[q]
            for side in ("src", "dst"):
                touched.add(pl[pr[side]["part"]]["type"]) if pr[side]["part"] in pl else None
                pr[side]["bus"] = rn(pr[side]["bus"])
        for tn in touched:
            t = T_[tn]
            for key in ("buses", "ft_slots"):
                seen = {}
                keep = []
                for b in t.get(key, []):
                    if b["name"].startswith(pre_old) and b["name"][len(pre_old):len(pre_old) + 1] in ("_", "x", "s"):
                        b["name"] = rn(b["name"]); nren += 1
                    if b["name"] in seen:
                        a_ = {k: v for k, v in seen[b["name"]].items() if k not in ("regs_um",)}
                        c_ = {k: v for k, v in b.items() if k not in ("regs_um",)}
                        if a_ != c_:
                            report.append(dict(type=tn, name=b["name"], why="mirror declaration differs"))
                        continue
                    seen[b["name"]] = b
                    keep.append(b)
                t[key] = keep
    return nren

mirror_conf = []
nren = mirror_names(B.raw, {r["id"] for r in rep1["rebuilt"]}, mirror_conf)
print(f"mirror names renamed {nren}, conflicts {len(mirror_conf)}", flush=True)
rep1["mirror_conflicts"] = mirror_conf
print(f"phase1 rebuilt {len(rep1['rebuilt'])} failed {len(rep1['failed'])} {time.time()-t0:.0f}s", flush=True)
# restore original lane notes/kinds for rebuilt ids
notes = {d["id"]: d for d in dropped}
for l in B.raw["lanes"]:
    if l["id"] in notes:
        l["note"] = notes[l["id"]]["note"] + " | DIE-HBM-22 replan " + V["name"] + " rebuilt"
pk = {d["id"]: d["kind"] for d in dropped}
for p in B.raw["ports"]:
    lid = p["id"].rsplit("_", 1)[0]
    if lid in pk:
        p["kind"] = pk[lid]

# phase 2: the 92 rows
rep2 = None
if a.rows92:
    rows = json.loads(Path(a.rows92).read_text())["rows"]
    B2 = LA.Builder(B.raw, near_um=a.near_um, max_hops=a.max_hops, require_cycle_match=False)
    rep2 = dict(built=[], far=[], failed=[])
    rows = sorted(rows, key=lambda r: (r["src"].startswith("NE_") or r["dst"].startswith("NE_"), -int(r["unplanned_bits"])))
    nid, idmap = 400, {}
    for r in rows:
        x, y, bits = r["src"], r["dst"], int(r["unplanned_bits"])
        e = LA.shared_edge(B2.P, x, y)
        g = LA.gap_um(B2.P, x, y)
        if e is None and g > a.near_um:
            rep2["far"].append(dict(src=x, dst=y, bits=bits, gap_um=round(g, 1)))
            continue
        cands = candidates(B2, x, y, bits)
        cands = [c for c in cands if not (set(c[2]) & B2.shared)]
        if not cands:
            rep2["failed"].append(dict(src=x, dst=y, bits=bits, why="no abutment path"))
            continue
        key = (x.replace("NE_", "NW_"), y.replace("NE_", "NW_"))
        if (x.startswith("NE_") or y.startswith("NE_")) and key in idmap:
            lid = idmap.pop(key) + "m"
        else:
            lid = f"L{nid}"; nid += 1; idmap[key] = lid
        got = add_lane(B2, dict(src=x, dst=y, bits=bits), cands, rep2, [lid])
        if got:
            for r1 in got:
                r1["split"] = len(got)
            rep2["built"].extend(got)
    raw = B2.raw
    print(f"phase2 built {len(rep2['built'])} far {len(rep2['far'])} failed {len(rep2['failed'])} {time.time()-t0:.0f}s",
          flush=True)
else:
    raw = B.raw
LA.copy = copy

out.mkdir(parents=True, exist_ok=True)
for f in plan_dir.iterdir():
    dst = out / f.name
    if f.name in ("die_plan.json",) or dst.exists():
        continue
    try:
        os.link(f, dst) if f.is_file() else os.symlink(f.resolve(), dst)
    except OSError:
        pass
raw["die"]["label"] = f"DIE-HBM-22 replan {V['name']} | " + raw["die"].get("label", "")
raw["note"] = raw.get("note", "") + f" | DIE-HBM-22 replan {V['name']}: rows A/C re-ordered by locality"
(out / "die_plan.json").write_text(json.dumps(raw, indent=1))
cyc = [r for r in rep1["rebuilt"] if r["old_cycles"] is not None and r["cycles"] != r["old_cycles"]]
rep = dict(schema="die_hbm_22.replan_event.v1", variant=V, base=str(plan_dir), base_sha=LA.sha12(plan_dir / "die_plan.json"),
           out_sha=LA.sha12(out / "die_plan.json"), moved=sorted(moved), outline_changes=outline_changes,
           dropped=len(dropped), phase1=rep1,
           cycle_changes=dict(n=len(cyc), up=sum(1 for r in cyc if r["cycles"] > r["old_cycles"]),
                              max_up=max([r["cycles"] - r["old_cycles"] for r in cyc] or [0]),
                              max_down=min([r["cycles"] - r["old_cycles"] for r in cyc] or [0])),
           phase2=None if rep2 is None else dict(
               built=len(rep2["built"]), built_bits=sum(x["bits"] for x in rep2["built"]),
               by_kind={k: sum(1 for x in rep2["built"] if x["kind"] == k) for k in ("adj", "same", "reverse", "path")},
               far=rep2["far"], far_bits=sum(x["bits"] for x in rep2["far"]), failed=rep2["failed"],
               cycle_mismatch=[dict(lane=x["lane"], src=x["src"], dst=x["dst"], cycles=x["cycles"],
                                    pair=x["existing_pair_cycles"]) for x in rep2["built"] if not x["cycles_match_pair"]],
               built_list=[dict(lane=x["lane"], src=x["src"], dst=x["dst"], bits=x["bits"], kind=x["kind"],
                                cycles=x["cycles"]) for x in rep2["built"]]),
           not_updated=["clock sidecars (clock_taps_die.json, clock_htree.json, entries.json, clock_entries.json)",
                        "pg_bumps.json", "type internal_stations / die_ft_bands of moved types"])
(out / "replan_report.json").write_text(json.dumps(rep, indent=1, default=str))
print("OUT", rep["out_sha"], f"{time.time()-t0:.0f}s")
