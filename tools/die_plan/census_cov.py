"""G0 census coverage (mandatory, COORD 10-23 06:45): the plan carries every as-built inter-partition bit.

Background: QC v2 silently dropped 62.9k inter-partition bits. Its part_of() returned None, so the traffic vanished,
and G0 / G2 still passed.

A plan names its census sources in the top-level key `census`:

    "census": [{"rows": "<census rows: FT census JSON (groups[]) or lanes TSV>", "map": "<instance map JSON>",
                "note": "..."}]
    "census": {"none": "<reason>"}      only for synthetic / proof plans; G0 warns

Paths are relative to the plan file. The instance map JSON:

    {"parts":    {"<census inst>": "<partition>", ...},      exact names first
     "rules":    [["<regex>", "<partition or group>"], ...],  then the first matching regex
     "groups":   {"<group>": ["<partition>", ...]},           a census block re-derived as several partitions
     "collapse": ["<regex>", ...],                            pass-through endpoints (landing cells ld_*, relays):
                                                              merged onto their single upstream source
     "bus_widths": {"<inst>.<bus>": nbits} or "<path.json[.gz]>",  optional: cap as-built bits per (source bus,
                                                              destination partition) at the bus width (broadcast once)
     "exempt":   [{"match": "<regex on src_bus|dst_bus|kind>", "kind": "clock|reset",
                   "replaced_by": "spine / per-partition sync", "reason": "..."}],
     "forward_via": ["<partition / group name regex>", ...],  forwarding partitions (tap trees): a pair is carried
                                                              by a lane chain through them (bottleneck width)
     "collapse_broadcast": true}                              count one driver bus once per sink partition/group

How the check works:
- Every census row whose endpoints map to different partitions (or groups) is inter-partition traffic. For each
  directed pair (A, B), the plan must carry at least the as-built bits on lanes that start on A and end on B.
  Bits are counted without epoch bits, and a lane through ft slots counts once.
  dropped = sum over pairs of max(0, as-built - planned).
- A row with an unmapped endpoint is an ERROR.
- Reset rows not covered by an explicit `exempt` entry are counted as dropped.
- Exempted rows are listed with their totals.
- A group spanning several partitions hides the traffic inside it, which a finer census must cover.
  Groups with no finer census are WARNed.
"""
import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

from schema import DIE_PART


def load_rows(path):
    p = Path(path)
    if p.suffix == ".tsv" or p.name.endswith(".tsv.gz"):
        fh = gzip.open(p, "rt") if p.name.endswith(".gz") else open(p)
        return [dict(src=r["src"], src_bus=r.get("src_bus", ""), dst=r["dst"], dst_bus=r.get("dst_bus", ""),
                     kind=r.get("kind", "data"), bits=int(float(r["bits"])))
                for r in csv.DictReader(fh, delimiter="\t")]
    js = json.load(gzip.open(p, "rt")) if p.name.endswith(".gz") else json.loads(p.read_text())
    rows = js["groups"] if isinstance(js, dict) else js
    return [dict(src=r["src"], src_bus=r.get("src_bus", ""), dst=r["dst"], dst_bus=r.get("dst_bus", ""),
                 kind=r.get("kind", "data"), bits=int(r["bits"])) for r in rows]


def collapse(rows, pats, err):
    """drop pass-through instances (landing cells / relays): row X->ld + ld->Y  =>  X->Y."""
    if not pats:
        return rows
    rx = [re.compile(p) for p in pats]

    def thru(i):
        return any(r.search(i) for r in rx)
    up = defaultdict(list)
    for r in rows:
        if thru(r["dst"]):
            up[r["dst"]].append(r)
    out = []
    for r in rows:
        if thru(r["dst"]):
            continue
        src, seen = r, set()
        while thru(src["src"]):
            if src["src"] in seen:
                err(f"census: pass-through loop at {src['src']}")
                break
            seen.add(src["src"])
            u = up.get(src["src"], [])
            if len(u) != 1:
                err(f"census: pass-through {src['src']} has {len(u)} upstream rows (needs exactly 1)")
                break
            src = u[0]
        out.append(dict(r, src=src["src"], src_bus=src["src_bus"]))
    return out


def coverage(P, plan_dir, R):
    """run every census of the plan; returns the summary dict (and files ERROR / WARN into R)."""
    spec = P.raw.get("census")
    if spec is None:
        R.err("census", "no `census` declared: census coverage is mandatory (as-built rows + instance map, or "
              "{\"none\": reason} for a synthetic plan)")
        return dict(declared=False)
    if isinstance(spec, dict) and "none" in spec:
        R.warn("census", f"census coverage not run: {spec['none']}")
        return dict(declared="none", reason=spec["none"])
    # plan lane bits per directed partition pair (data width, an ft lane once)
    # Broadcast trees: a branch lane starts at a fork / re-launch leaf (contents module matching `fork_modules`,
    # default hbm_ft_fork_reg) named <fk|rl>_<S>, fed by the lane of group <S> that ends in or crosses that partition.
    # The branch then counts from the tree's ORIGIN partition (as-built rows are origin -> leaf, not fork -> leaf).
    forkrx = re.compile(P.raw.get("census_fork_modules", r"^hbm_ft_fork_reg$"))
    forkleaf = {}
    for tn, t in P.types.items():
        fl = {c["inst"] for c in t.get("contents", []) if forkrx.search(c.get("module", ""))}
        for b in t.get("buses", []):
            inst = b.get("leaf", "").split(".")[0]
            if inst in fl:
                forkleaf[(tn, b["name"])] = inst
    by_group = defaultdict(list)
    for lid, ln in P.lanes.items():
        by_group[lid.rsplit("_", 1)[0]].append(lid)
    parent = {}
    for lid, ln in P.lanes.items():
        a = P.ports[ln["ports"][0]]
        part = a["src"]["part"]
        if part == DIE_PART or part not in P.parts:
            continue
        inst = forkleaf.get((P.parts[part]["type"], a["src"]["bus"]))
        if inst is None:
            continue
        grp = inst.split("_", 1)[1]
        # a replicated type names the fork after one image of the lane group; mirrored instances carry the other
        # images (same group name up to its last letter)
        own = lid.rsplit("_", 1)[0]                     # the branch's own group (same image) first
        cands = by_group.get(own, []) + by_group.get(grp, []) + [
            o for x in "abcdefgh" for o in by_group.get(grp[:-1] + x, []) if grp[:-1] + x not in (grp, own)]
        for o in cands:
            if o != lid and any(P.ports[q]["dst"]["part"] == part for q in P.lanes[o]["ports"]):
                parent[lid] = o
                break

    def origin(lid, seen=()):
        if lid in parent and lid not in seen:
            return origin(parent[lid], seen + (lid,))
        return P.ports[P.lanes[lid]["ports"][0]]["src"]["part"]
    planned = defaultdict(int)
    for lid, ln in P.lanes.items():
        a = P.ports[ln["ports"][0]]
        b = P.ports[ln["ports"][-1]]
        planned[(origin(lid), b["dst"]["part"])] += int(a["width"])
        if lid in parent:                                # the fork partition also receives the word
            planned[(a["src"]["part"], b["dst"]["part"])] += int(a["width"])
    out = dict(declared=True, sources=[])
    for k, src in enumerate(spec):
        rows = load_rows(Path(plan_dir) / src["rows"])
        mp = json.loads((Path(plan_dir) / src["map"]).read_text())
        exact = mp.get("parts", {})
        rules = [(re.compile(rx), tgt) for rx, tgt in mp.get("rules", [])]
        groups = mp.get("groups", {})
        g_of = {}
        for g, plist in groups.items():
            for p in plist:
                if p not in P.parts:
                    R.err("census", f"census[{k}] group {g}: unknown partition {p}")
                g_of[p] = g
        for tgt in list(exact.values()) + [t for _, t in rules]:
            if tgt not in P.parts and tgt not in groups and tgt != DIE_PART:
                R.err("census", f"census[{k}] map target '{tgt}' is neither a partition, a group nor {DIE_PART}")
        errs = []
        rows = collapse(rows, mp.get("collapse", []), errs.append)
        for e in errs[:20]:
            R.err("census", f"census[{k}] {e}")
        ex = [(re.compile(e["match"]), e) for e in mp.get("exempt", [])]

        def where(inst):
            if inst in exact:
                return exact[inst]
            for rx, tgt in rules:
                if rx.search(inst):
                    return tgt
            return None
        # optional source bus widths {"<inst>.<bus>": nbits} (or a JSON path): a broadcast / tapped source bus is on
        # the wire once per destination partition, so as-built bits per (src bus, dst partition) are capped at the bus
        # width (the FT census bits_unique rule; rows are per (src bus, dst inst, dst bus) and repeat broadcast nets)
        bw = mp.get("bus_widths") or {}
        if isinstance(bw, str):
            bwp = Path(plan_dir) / bw
            bw = json.load(gzip.open(bwp, "rt")) if bwp.name.endswith(".gz") else json.loads(bwp.read_text())
        capped = defaultdict(int)
        unmapped = defaultdict(int)
        asb = defaultdict(int)
        exempt = defaultdict(int)
        intra = 0
        seen = {}
        collapsed = 0
        collapse_bc = bool(mp.get("collapse_broadcast", False))
        for r in rows:
            s, d = where(r["src"]), where(r["dst"])
            if s is None or d is None:
                for i, w in ((r["src"], s), (r["dst"], d)):
                    if w is None:
                        unmapped[i] += r["bits"]
                continue
            sg, dg = g_of.get(s, s), g_of.get(d, d)
            if sg == dg:
                intra += r["bits"]
                continue
            hit = next((e for rx, e in ex if rx.search(r["src_bus"]) or rx.search(r["dst_bus"])
                        or rx.search(r["kind"])), None)
            if hit is not None:
                exempt[(hit["kind"], hit.get("replaced_by", ""), hit["match"])] += r["bits"]
                continue
            w = bw.get(f"{r['src']}.{r['src_bus']}")
            if w is not None:
                key = (r["src"], r["src_bus"], sg, dg)
                add = min(r["bits"], max(0, int(w) - capped[key]))
                capped[key] += add
                asb[(sg, dg)] += add
            elif collapse_bc:
                # PLAN-S81v3 (989ee4d63): one driver bus reaching several sinks in the same partition/group (a
                # broadcast, or the tracer's src-bus x dst-bus cross product through one relay bundle) crosses the
                # boundary once: count it once (max).  Opt-in: rows carry no bit ranges, so a bus SPLIT over
                # several sinks of one group is under-counted; the collapsed bits are reported.
                key = (r["src"], r["src_bus"], dg)
                if r["bits"] > seen.get(key, 0):
                    asb[(sg, dg)] += r["bits"] - seen.get(key, 0)
                    collapsed += seen.get(key, 0)
                    seen[key] = r["bits"]
                else:
                    collapsed += r["bits"]
            else:
                asb[(sg, dg)] += r["bits"]
        for inst, b in sorted(unmapped.items(), key=lambda x: -x[1])[:30]:
            R.err("census", f"census[{k}]: as-built instance '{inst}' ({b} bits) maps to no partition")
        if len(unmapped) > 30:
            R.err("census", f"census[{k}]: {len(unmapped) - 30} more unmapped instances")
        # planned bits at group granularity
        pg = defaultdict(int)
        for (a, b), w in planned.items():
            ga, gb = g_of.get(a, a), g_of.get(b, b)
            if ga != gb:
                pg[(ga, gb)] += w
        # forwarded lanes (KV-P2 10-23): a pair with no (or too narrow) direct lane is carried by a chain of planned
        # lanes through partitions the map names as forwarders (`forward_via`: partition / group names or regexes,
        # e.g. tap-tree hosts).  Credit = the chain's bottleneck width (broadcast trees reuse the same lanes).
        fwd_rx = [re.compile(x) for x in mp.get("forward_via", [])]

        def is_fwd(n):
            return any(rx.fullmatch(n) for rx in fwd_rx)
        adj = defaultdict(dict)
        for (a, b), w in pg.items():
            adj[a][b] = w

        def bottleneck(a, b):
            """widest path a -> b through forwarders only (modified Dijkstra on min-capacity)."""
            import heapq
            best = {a: float("inf")}
            hq = [(-best[a], a)]
            while hq:
                cap, u = heapq.heappop(hq)
                cap = -cap
                if u == b:
                    return cap
                if cap < best.get(u, 0):
                    continue
                if u != a and not is_fwd(u):
                    continue
                for v, w in adj[u].items():
                    c = min(cap, w)
                    if c > best.get(v, 0):
                        best[v] = c
                        heapq.heappush(hq, (-c, v))
            return 0
        dropped, forwarded = {}, 0
        for pair, b in asb.items():
            have = pg.get(pair, 0)
            if have < b and fwd_rx:
                f = bottleneck(*pair)
                if f > have:
                    forwarded += min(b, f) - have
                    have = max(have, f)
            if have < b:
                dropped[pair] = b - have
        tot = sum(dropped.values())
        for (a, b), v in sorted(dropped.items(), key=lambda x: -x[1])[:30]:
            R.err("census", f"census[{k}]: {a} -> {b}: as-built {asb[(a, b)]} bits, planned {pg.get((a, b), 0)} "
                  f"(dropped {v})")
        if tot:
            R.err("census", f"census[{k}]: {tot} as-built inter-partition bits dropped over {len(dropped)} pairs")
        multi = {g: len(pl) for g, pl in groups.items() if len(pl) > 1}
        for g, n in sorted(multi.items()):
            R.warn("census", f"census[{k}] group {g} spans {n} partitions: traffic inside it is unchecked by this "
                   "census (cover it with a finer census)")
        out["sources"].append(dict(rows=src["rows"], map=src["map"], census_rows=len(rows),
                                   inter_bits=sum(asb.values()), intra_bits=intra, planned_pairs=len(pg),
                                   dropped_bits=tot, dropped_pairs=len(dropped), unmapped_instances=len(unmapped),
                                   forwarded_bits=forwarded, broadcast_collapsed_bits=collapsed,
                                   exempt={f"{k_[0]}:{k_[2]}": v for k_, v in exempt.items()},
                                   groups_spanning=multi))
    out["dropped_bits"] = sum(s["dropped_bits"] for s in out["sources"])
    return out
