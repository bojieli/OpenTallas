#!/usr/bin/env python3
"""Per-die bound-transport table (TRANSPORT-3): every core-to-core crossing of a bind, its depth change against as-built,
and the structural exposure of that change.  Advisory only, never a gate.

Reads only a finished bind directory:  bind_latency.json  bus_groups.json  param_regen.json  and optionally
latency_consumers JSON (--lc).  Exposure classes (a bus can carry several):
  ZERO      landed == as-built on every member (the zero-transport view is still exact for this bus)
  TORN      one landing group (one sink leaf + one source partition, as-built equal) has unequal landed depths
  JOIN      the sink leaf receives buses from >=2 source partitions whose landed-minus-as-built deltas differ
  REPLICA   the source bit fans out to several sink partitions with unequal bound depth
  ABS       the whole bundle moved by one value and no other class applies: only the absolute age changes
Consumer rows (the standing table a die owner reads when a plan changes): every latency_consumers contract, every
param_regen entry (regenerated parameter) and any row from --known (hand-recorded fixed-age consumers with the required
depth from a bench or a read), with the hop depths they depend on and required vs landed.

    python3 -I transport_table.py BIND_DIR --die NAME [--lc LC.json] [--known KNOWN.json] --out OUTDIR
Writes OUTDIR/<die>_buses.tsv, _classes.tsv, _consumers.tsv, _summary.json.  Never exits nonzero on findings.
"""
import argparse, collections, json, re, sys
from pathlib import Path


def base_name(part):
    """partition instance -> replica class name (s_3S_C -> s_S_C, svc_5 -> svc, dvs_E0 -> dvs_E)"""
    return re.sub(r"\d+", "", part)


def load(p):
    return json.loads(Path(p).read_text())


def analyse(bind, die):
    lat = load(bind / "bind_latency.json")
    groups = load(bind / "bus_groups.json")
    regen = {}
    p = bind / "param_regen.json"
    if p.exists():
        regen = load(p)
    buses = {}
    for b in lat["buses"]:
        ab = b["asbuilt_stages"]
        lane = b["lane"] or f"unnamed:{b['src']}>{b['dst']}:{b.get('bus_out','')}:{len(buses)}"
        buses[lane] = dict(lane=lane, src=b["src"], dst=b["dst"], bus_out=b.get("bus_out", ""), bus_in=b.get("bus_in", ""),
                                width=b["width"], asbuilt_min=min(ab), asbuilt_max=max(ab), bound=b["bound_stages"],
                                delta=b["delta"], tags=set(), sinks=set(), forwarded=b.get("forwarded", 0))
    # member records: per lane landed-minus-asbuilt set, per sink leaf
    lane_mem = collections.defaultdict(list)
    sink_groups = collections.defaultdict(list)   # sink leaf -> [(src_part, delta set, lanes)]
    torn_groups = []
    for g in groups["landing"]:
        members = g["members"]
        lane_d = collections.defaultdict(set)
        by_ab = collections.defaultdict(set)
        for m in members:
            d = m["landed_stages"] - m["asbuilt_stages"]
            lane_d[m.get("lane")].add(d)
            by_ab[m["asbuilt_stages"]].add(m["landed_stages"])
            lane_mem[m.get("lane")].append(g["sink"])
            buses_row = buses.get(m.get("lane"))
            if buses_row:
                buses_row["sinks"].add(g["sink"])
        torn = (not g["aligned_landed"]) or any(len(v) > 1 for v in by_ab.values())
        ds = set().union(*lane_d.values()) if lane_d else set()
        sink_groups[g["sink"]].append((g["src_part"], ds, list(lane_d)))
        if torn:
            spread = max(max(v) - min(v) for v in by_ab.values()) if by_ab else 0
            torn_groups.append(dict(sink=g["sink"], sink_part=g["sink_part"], src_part=g["src_part"], lanes=sorted(k for k in lane_d if k),
                                    asbuilt=sorted(g["asbuilt_stage_set"]), spread=spread))
            for l in [x for x in lane_d if x]:
                if l in buses:
                    buses[l]["tags"].add("TORN")
    # JOIN: sink leaf fed from >=2 source partitions with different landed-asbuilt deltas (group delta when single-valued)
    join_sinks = []
    for sink, rows in sink_groups.items():
        per_src = {}
        for src, ds, lanes in rows:
            per_src.setdefault(src, set()).update(ds)
        if len(per_src) < 2:
            continue
        reps = {s: (min(v) if len(v) == 1 else None) for s, v in per_src.items()}
        vals = {v for v in reps.values()}
        if None in vals or len(vals) > 1:
            lane_set = set()
            for src, ds, lanes in rows:
                lane_set.update(l for l in lanes if l)
            join_sinks.append(dict(sink=sink, deltas_by_source={s: sorted(per_src[s]) for s in per_src}, lanes=sorted(lane_set)))
            for l in lane_set:
                if l in buses:
                    buses[l]["tags"].add("JOIN")
    # REPLICA: as-built one fan-out, unequal bound depth per sink partition
    replicas = []
    for r in groups.get("replica", []):
        if r.get("equal"):
            continue
        depths = {s: sorted(set(v)) for s, v in r.get("bound_depths", {}).items()}
        replicas.append(dict(source=r["source"], depths=depths, asbuilt=r.get("asbuilt_stages")))
    # map replica to lanes by source leaf prefix
    src_leaf_lanes = collections.defaultdict(set)
    for b in lat["buses"]:
        for leaf in b.get("leaves") or []:
            if b.get("lane"):
                src_leaf_lanes[leaf.split("[")[0]].add(b["lane"])
    for r in replicas:
        hit = set()
        for leaf, lanes in src_leaf_lanes.items():
            if leaf == r["source"] or leaf.startswith(r["source"] + "."):
                hit |= lanes
        r["lanes"] = sorted(hit)
        for l in hit:
            if l in buses:
                buses[l]["tags"].add("REPLICA")
    for b in buses.values():
        if b["delta"] == 0 and b["asbuilt_min"] == b["asbuilt_max"] and not (b["tags"]):
            b["tags"].add("ZERO")
        elif not b["tags"]:
            b["tags"].add("ABS")
    return lat, groups, regen, buses, torn_groups, join_sinks, replicas


def classes(buses):
    """roll up: (src class, dst class, bus_out class) -> count, bits, delta range, tags"""
    cl = {}
    for b in buses.values():
        k = (base_name(b["src"]), base_name(b["dst"]), re.sub(r"\d+", "", b["bus_out"]))
        c = cl.setdefault(k, dict(n=0, bits=0, dmin=10**9, dmax=-10**9, tags=collections.Counter(), ex=b["lane"]))
        c["n"] += 1
        c["bits"] += b["width"]
        c["dmin"] = min(c["dmin"], b["delta"])
        c["dmax"] = max(c["dmax"], b["delta"])
        for t in b["tags"]:
            c["tags"][t] += 1
    return cl


def consumers(lat, regen, buses, lc, known, die):
    rows = []
    # contracts from latency_consumers
    for c in (lc or {}).get("contracts", []):
        rows.append(dict(die=die, consumer=c["inst"], label=c.get("param", ""), source=c.get("src", "contract"), module=c.get("module", ""),
                         req_lanes=c.get("req"), resp_lanes=c.get("resp"), landed=c.get("landed_loop", c.get("added")),
                         required=c.get("required", c.get("added")), verdict=c.get("verdict", ""), note=""))
    # undeclared latency-named parameters on leaves with added crossing cycles (census): read these first when a plan moves
    for c in (lc or {}).get("advisory", []):
        rows.append(dict(die=die, consumer=c.get("eg", ""), label=";".join(sorted(c.get("params", {}))), source="census", module=c.get("module", ""),
                         req_lanes=None, resp_lanes=None, landed=c.get("max_added"), required=dict(c.get("params", {})),
                         verdict="CENSUS", note=f"n={c.get('n')}"))
    # regenerated params: consumer is compensated by parameter
    for c in regen.get("changed", []):
        rows.append(dict(die=die, consumer=c["inst"], label=c["param"], source="param_regen", module="",
                         req_lanes=None, resp_lanes=None, landed=c["bound"], required=c["asbuilt"], verdict="REGENERATED", note="as-built->bound"))
    for r in known or []:
        if r.get("die") == die:
            # landed depth sum from lane regex if given
            lm = None
            if r.get("lanes"):
                rx = re.compile(r["lanes"])
                ls = [b for b in buses.values() if rx.fullmatch(b["lane"])]
                lm = sorted(set(b["bound"] for b in ls))
            rows.append(dict(die=die, consumer=r["consumer"], label=r["label"], source=r.get("source", "known"), module=r.get("module", ""),
                             req_lanes=r.get("lanes"), resp_lanes=None, landed=lm if lm is not None else r.get("landed"),
                             required=r.get("required"), verdict=r.get("verdict", "KNOWN"), note=r.get("note", "")))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("bind_dir", type=Path)
    ap.add_argument("--die", required=True)
    ap.add_argument("--lc", type=Path)
    ap.add_argument("--known", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    lc = load(a.lc) if a.lc and a.lc.exists() else None
    known = load(a.known) if a.known and a.known.exists() else []
    lat, groups, regen, buses, torn, joins, reps = analyse(a.bind_dir, a.die)
    cls = classes(buses)
    cons = consumers(lat, regen, buses, lc, known, a.die)
    tag_count = collections.Counter(); tag_bits = collections.Counter()
    for b in buses.values():
        for t in b["tags"]:
            tag_count[t] += 1; tag_bits[t] += b["width"]
    with open(a.out / f"{a.die}_buses.tsv", "w") as f:
        f.write("lane\tsrc\tdst\tbus_out\tbus_in\twidth\tasbuilt_min\tasbuilt_max\tbound\tdelta\tforwarded\ttags\n")
        for b in sorted(buses.values(), key=lambda x: (-abs(x["delta"]), x["lane"])):
            f.write("\t".join(map(str, (b["lane"], b["src"], b["dst"], b["bus_out"], b["bus_in"], b["width"], b["asbuilt_min"], b["asbuilt_max"],
                                        b["bound"], b["delta"], b["forwarded"], "+".join(sorted(b["tags"]))))) + "\n")
    with open(a.out / f"{a.die}_classes.tsv", "w") as f:
        f.write("src_class\tdst_class\tbus\tn\tbits\tdelta_min\tdelta_max\ttags\texample\n")
        for k, c in sorted(cls.items(), key=lambda kv: -kv[1]["bits"]):
            f.write("\t".join(map(str, (*k, c["n"], c["bits"], c["dmin"], c["dmax"], dict(c["tags"]), c["ex"]))) + "\n")
    with open(a.out / f"{a.die}_consumers.tsv", "w") as f:
        f.write("die\tconsumer\tlabel\tsource\tmodule\tlanded\trequired\tverdict\treq_lanes\tresp_lanes\tnote\n")
        for r in cons:
            f.write("\t".join(str(r.get(k, "")) for k in ("die", "consumer", "label", "source", "module", "landed", "required", "verdict", "req_lanes", "resp_lanes", "note")) + "\n")
    with open(a.out / f"{a.die}_torn_join_replica.json", "w") as f:
        json.dump(dict(torn=torn, join=joins, replica=reps), f, indent=1)
    s = dict(die=a.die, bind_dir=str(a.bind_dir), buses=len(buses), bits=sum(b["width"] for b in buses.values()),
             classes=len(cls), tag_bus_count=dict(tag_count), tag_bits=dict(tag_bits),
             delta_nonzero=sum(1 for b in buses.values() if b["delta"]), torn_groups=len(torn), join_sinks=len(joins),
             replica_unequal=len(reps), consumers=len(cons), regen=len(regen.get("changed", [])),
             lc_contracts=len((lc or {}).get("contracts", [])),
             lc_census=len((lc or {}).get("advisory", [])), r8=(lc or {}).get("r8", {}).get("stats"), r8_errors=(lc or {}).get("r8", {}).get("errors"))
    (a.out / f"{a.die}_summary.json").write_text(json.dumps(s, indent=1, sort_keys=True))
    print(json.dumps(s))


if __name__ == "__main__":
    main()
