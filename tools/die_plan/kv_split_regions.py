#!/usr/bin/env python3
"""Private KV split event: one ordinary CA origin per piece, neighbor clock/START tree.

Uses the released locality variation model, CA ring planner and CA binder.  This
is a prediction, never a substitute for the new both-edge measured clock gate.
No input file is changed.  The existing PLL/boot origin remains the root.
"""
import argparse
import collections
import contextlib
import copy
import hashlib
import heapq
import io
import json
import sys
from pathlib import Path


def dump(path, value):
    def clean(x):
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items() if not str(k).startswith("_")}
        if isinstance(x, (list, tuple)):
            return [clean(v) for v in x]
        return x
    Path(path).write_text(json.dumps(clean(value), indent=1) + "\n")


def _part_names(plan):
    """Partition names of a raw plan (partitions is a list of {name, type, ...}); None when the plan has none."""
    names = {q["name"] for q in plan.get("partitions") or []}
    return names or None


def feed_ref(feed_path, rel="feed.json", parts=None):
    """clock.spine.feed reference for a committed feed doc: path, sha256, and the root/form/frame READ FROM the doc.

    The schema requires feed.root (region_form.apply writes it the same way).  The root is never supplied by the
    caller: it is the doc's own root, which must be the one parentless node of the feed tree and, when parts are
    given, a partition of the plan."""
    b = Path(feed_path).read_bytes()
    doc = json.loads(b)
    root = doc.get("root")
    if not root:
        raise ValueError(f"{feed_path}: feed doc has no root")
    par = doc.get("parent") or {}
    if par and (root not in par or par[root] is not None):
        raise ValueError(f"{feed_path}: root {root} is not the parentless node of the feed tree")
    orphans = sorted(n for n, q in par.items() if q is None and n != root)
    if orphans:
        raise ValueError(f"{feed_path}: feed has more than one parentless node: {[root] + orphans}")
    if parts is not None and root not in parts:
        raise ValueError(f"{feed_path}: feed root {root} is not a partition of the plan")
    ref = dict(path=rel, sha256=hashlib.sha256(b).hexdigest(), root=root)
    for k in ("form", "frame"):
        if doc.get(k) is not None:
            ref[k] = doc[k]
    return ref


def restamp_feed(plan, feed_path):
    """Set plan clock.spine.feed from the committed feed doc; refuse when the plan names another feed (sha)."""
    sp = plan.setdefault("clock", {}).setdefault("spine", {})
    old = sp.get("feed") or {}
    ref = feed_ref(feed_path, old.get("path", Path(feed_path).name), parts=_part_names(plan))
    if old.get("sha256") and old["sha256"] != ref["sha256"]:
        raise ValueError(f"plan feed sha {old['sha256']} != {feed_path} sha {ref['sha256']}")
    sp["feed"] = ref
    return ref


def neighbor_feed(root, G, E, X, v, kind="fwd"):
    """Clock and START choose the same directed, abutting data-link tree.

    Edge cost is the existing locality forward-clock delay.  Root is the actual
    input plan's PLL/boot region, not an invented new source.  A one-way data
    edge can only carry START in its real direction.
    """
    import locality as LO
    adj = collections.defaultdict(list)
    for x in X:
        if x.get("far"):
            continue
        p, c = x["ra"], x["rb"]
        tap = tuple(x["xy"])
        delay = LO.hop_delay(G, p, c, tap, v, kind)
        adj[p].append((c, delay, -int(x["width"]), str(x["id"]), tap))
    dist, parent, port, taps = {root: 0.0}, {root: None}, {}, {}
    todo, order = [(0.0, root)], []
    while todo:
        cost, p = heapq.heappop(todo)
        if cost != dist[p]:
            continue
        order.append(p)
        for c, delay, negbits, pid, tap in sorted(adj[p]):
            nc = cost + delay
            old = dist.get(c, float("inf"))
            if nc < old - 1e-9 or (abs(nc-old) <= 1e-9 and (negbits, pid) < port.get(c, (0, "~"))):
                dist[c], parent[c], port[c] = nc, p, (negbits, pid)
                taps[(p, c)] = tap
                heapq.heappush(todo, (nc, c))
    miss = sorted(set(G) - set(parent))
    if miss:
        raise ValueError(f"no directed neighbor START path from {root} to {len(miss)} regions: {miss[:12]}")
    return dict(root=root, parent=parent, order=list(dict.fromkeys(order)),
                tap={(p, c): taps[(p, c)] for c, p in parent.items() if p is not None}, joined=[], kind=kind,
                data_tree_port={c: x[1] for c, x in port.items()})


def model(plan_path, side, out, velocity):
    import locality as LO
    import count_align_plan as CAP
    import count_align_bind as CAB
    raw = json.loads(Path(plan_path).read_text())
    parts = {p["name"]: p for p in raw["partitions"]}
    ca0 = side["count_aligned"]
    # Every unlanded stream must share one actual regional clock. A split cut
    # is eligible only within its former fixed-origin owner.
    owners = {p: (a.get("src") if a["role"] == "relay" else p)
              for p, a in ca0["parts"].items()}
    landed = {p["port"] for p in side["ports"]}
    parent = {p: p for p in parts}
    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    plain, cuts = [], []
    for q in raw["ports"]:
        a, z = q["src"]["part"], q["dst"]["part"]
        if a not in parts or z not in parts or a == z:
            continue
        cut = owners.get(a, a) == owners.get(z, z)
        if cut:
            cuts.append(q["id"])
        if q["id"] not in landed and not cut:
            pa, pz = find(a), find(z)
            parent[max(pa, pz)] = min(pa, pz)
            plain.append(q["id"])
    reg = {p: find(p) for p in parts}
    groups = collections.defaultdict(list)
    for p, r in reg.items(): groups[r].append(p)
    dump(out / "plain_components.json", dict(part_region=reg, groups=dict(groups),
         plain_ports=plain, supported_split_cut_ports=cuts,
         invariant="every retained plain production edge has identical actual regional clock root"))
    root_region = ca0["root"]
    root = ca0["regions"][root_region].get("origin_part")
    if root is None:
        found = [p for p, r in ca0["parts"].items() if r["region"] == root_region and r["role"] == "origin"]
        if len(found) != 1:
            raise ValueError(f"root origin ambiguous: {found}")
        root = found[0]
    if root not in parts:
        raise ValueError(f"actual root partition absent after split: {root}")
    root = reg[root]
    original_feed = LO.feed_tree
    def feed(G, E, X, v, kind="fwd"):
        return neighbor_feed(root, G, E, X, v, kind)
    LO.feed_tree = feed
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            scored = LO.score(LO.load_plan(plan_path), reg, velocity, "fwd")
    finally:
        LO.feed_tree = original_feed
    R, F, G = scored["crossings"], scored["F"], scored["G"]
    corners = LO.cap_corner_rows(R)
    dump(out / "ocv_model.json", dict(corners={c: dict(all=r) for c, r in corners.items()}))
    rows = CAP.load_rows(str(out / "ocv_model.json"), ",".join(corners), 1.0)
    rows_by_port = {r["port"]: r for r in rows}
    original_tree = CAP.directed_tree
    def data_tree(rows_, regions):
        rmap = {r["port"]: r for r in rows_}
        par = {root: None}
        for child, pid in F["data_tree_port"].items():
            r = rmap[pid]
            assert (r["src"], r["dst"]) == (F["parent"][child], child)
            par[child] = (r["src"], r)
        return root, par
    CAP.directed_tree = data_tree
    try:
        summ, crossings, regions = CAP.plan(rows, T=833.0, ap=833.0/8,
                                          wander_frac=0.05, max_depth=8)
    finally:
        CAP.directed_tree = original_tree
    summ.update(period_ps=833.0, aperture_ps=833.0/8, sync_aperture_ps=26.5,
                wander_frac=0.05, pad=0, source="locality forward-clock model; NOT MEASURED")
    # Use the released wall-aligned count frame for link-fed clocks.  This
    # changes schedule labels, never RTL K or physical origin steps.
    import count_frame as CF
    tr, _ = LO.arrivals(G, F, velocity)
    leaves = {r: tr[r] + LO.ins(G[r], velocity) for r in tr}
    offsets = {r: int(round(x / 833.0)) for r, x in leaves.items()}
    feed = dict(root=F["root"], parent=F["parent"], joined=F["joined"],
                tap={f"{p}->{c}": list(xy) for (p, c), xy in F["tap"].items()},
                kind=F["kind"], form="fwd", frame="wall_aligned", v_ps_mm=velocity,
                frame_offset=offsets, leaf_arrival_tt_ps=leaves,
                data_tree_port=F["data_tree_port"],
                note="clock and standard CA START share the directed neighbor tree; prediction only")
    dump(out / "regions.json", dict(part_region=reg))
    dump(out / "feed.json", feed)
    frame = CF.Frame("wall_aligned", offsets, reg, "feed.json",
                     hashlib.sha256((out / "feed.json").read_bytes()).hexdigest(),
                     hashlib.sha256((out / "regions.json").read_bytes()).hexdigest())
    CAP.apply_frame(summ, crossings, frame)
    cap = dict(summary=summ, regions=regions, crossings=crossings)
    dump(out / "ca_model.json", cap)
    # Stop before composition if the normal CA model itself does not qualify.
    if summ["fail"] or summ["below_100ps"]:
        dump(out / "status.json", dict(verdict="MODEL_FAIL", summary=summ,
                                        physical_qualified=False))
        return raw, None, scored
    ends = {p["id"]: (p["src"]["part"], p["dst"]["part"]) for p in raw["ports"]}
    b = CAB.bind(cap, parts=ends)
    verified = CAB.verify(b, samples=100)
    dump(out / "ca_bind_model.json", b)
    dump(out / "ca_bind_check.json", verified)
    if verified["identity_and_loop_errors"] or verified["sim_window_violations"]:
        raise ValueError(f"standard CA binder rejects model: {verified}")
    lane_of = {pid: ln["id"] for ln in raw["lanes"] for pid in ln["ports"]}
    table_rows = []
    for p in raw["ports"]:
        pid = p["id"]
        if pid not in b["ports"]:
            continue
        s, d = ends[pid]
        table_rows.append(dict(port=pid, lane=lane_of.get(pid), src=s, dst=d,
                               src_region=reg[s], dst_region=reg[d], width=int(p["width"]),
                               kind=p.get("kind"), added_cycles=b["ports"][pid]["sched_lat"]))
    boxes = [dict(k=i, tag=rn, parts=g["parts"], box_um=list(g["bbox"]))
             for i, (rn, g) in enumerate(sorted(G.items()))]
    table = dict(schema="opentallas.fallback_landed.v1", mode="partition",
                 block=0, regions_count=len(boxes), regions=boxes,
                 crossings=len(table_rows), ports=table_rows)
    table = CAB.annotate_table(table, b, root_settle_cycles=ca0.get("root_settle_cycles", 64),
                               strap_form=True)
    if ca0.get("start_reset_wave"):
        table["count_aligned"]["start_reset_wave"] = True
    dump(out / "pipeline_stage_cycles.json", price_existing_pipeline_stages(table, raw))
    dump(out / "sidecar_model.json", table)
    dump(out / "status.json", dict(verdict="MODEL_PASS", physical_qualified=False,
                                    summary=summ, bind_check=verified,
                                    root=root, regions_before=len(side["regions"]),
                                    regions_after=len(boxes),
                                    removed_fixed_relay_roles=sum(r["role"] == "relay" for r in ca0["parts"].values())))
    return raw, table, scored


def price_existing_pipeline_stages(table, raw):
    """Preserve declared FREG/QREG hardware cycles while replanning raw rings."""
    import clock_landings as CL
    types = {p["name"]: p["type"] for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    changes = []
    for row in table["ports"]:
        pid = row["port"]
        p = ports[pid]
        tn, bus = types[p["dst"]["part"]], p["dst"]["bus"]
        c = table["count_aligned"]["ports"][pid]
        wr = CL.ring_write_reg(raw, tn, bus)
        freg = bool(wr and wr.get("freg"))
        qreg = CL.output_qreg(raw, tn, bus)
        extra = int(freg) + int(qreg)
        if freg: c["freg"] = 1
        if qreg:
            c["output_qreg"] = 1
            c["K"] += 1
        if extra:
            c["sched_lat"] += extra
            row["added_cycles"] += extra
            changes.append(dict(port=pid, freg=int(freg), output_qreg=int(qreg), added_cycles=extra))
    return changes


def prepare_native_form(raw, side, scored, out):
    """Export independent count-frame intent without fabricating a START proof.

    Physical clock groups remain plain-seam components. Standard measured
    clock START planning supplies all K, stage and origin steps later.
    """
    import locality as LO
    mapping = json.loads((out / "regions.json").read_text())["part_region"]
    endpoints = {p["id"]: (p["src"]["part"], p["dst"]["part"])
                 for p in raw["ports"]}
    corners = LO.cap_corner_rows(scored["crossings"])
    for rows in corners.values():
        for row in rows:
            src, dst = endpoints[row["port"]]
            row.update(src=src, dst=dst, src_part=src, dst_part=dst)
    dump(out / "independent_ocv_prediction.json",
         dict(corners={c: dict(all=r) for c, r in corners.items()},
              source="locality prediction only; replace with measured both-edge OCV before planning"))
    dump(out / "independent_count_intent.json", dict(
         physical_qualified=False, verdict="NEEDS_MEASURED_CLOCK_START",
         count_regions=len(mapping), physical_clock_groups=len(set(mapping.values())),
         root="hub_C", frame_clock_regions=mapping,
         parts={p: dict(region=p, role="origin", src=None, stages=0) for p in mapping},
         new_origin_parts=[p for p, a in side["count_aligned"]["parts"].items()
                           if a["role"] == "relay"],
         start_form="released count_align_plan --start-tree clock --start-partition-origins --start-native-clocks",
         required_readout="TT and FF rise AND fall, native t_PART__clk for all196parts, actual tree geometry",
         note="All196countorigins independent;32PC+PHYpairs share actual clock roots; no extra plain-edge landing or fixed2stagePHYrelay"))
    # This file is solely a clock geometry input, never a bound production plan.
    geometry = copy.deepcopy(raw)
    geometry.setdefault("clock", {}).setdefault("spine", {}).update(
        topology="link_htree",
        region_map=dict(path="regions.json", sha256=hashlib.sha256((out / "regions.json").read_bytes()).hexdigest()),
        feed=feed_ref(out / "feed.json", parts=_part_names(raw)))
    dump(out / "clock_geometry_plan.json", geometry)


def bind_native_measurement(raw, clock_table, cap_path, out, provisional=False):
    """Bind released measured clock-START output with independent real origins."""
    import count_align_bind as CAB
    cap = json.loads(Path(cap_path).read_text())
    summary = cap["summary"]
    if (cap.get("prediction_only") or summary.get("prediction_only")) and not provisional:
        raise ValueError("prediction-only CA document cannot be accepted as measured")
    if summary.get("fail") or summary.get("below_100ps"):
        raise ValueError("measured CA fails crossing/margin gate")
    start = summary.get("start_tree", {})
    if not cap.get("start_edges") or not isinstance(start, dict) or start.get("form") != "clock":
        raise ValueError("measured independent origins require standard clock START edges")
    if start.get("start_fail") or summary.get("tree_edges_ambiguous"):
        raise ValueError("measured independent origins fail START cleanliness")
    ends = {q["id"]: (q["src"]["part"], q["dst"]["part"]) for q in raw["ports"]}
    expected = {r["port"] for r in clock_table["ports"]}
    received = {r["port"] for r in cap["crossings"]}
    if expected != received:
        raise ValueError(f"measured crossing set changed: missing={len(expected-received)} extra={len(received-expected)}")
    b = CAB.bind(cap, parts=ends)
    check = CAB.verify(b, samples=100)
    if check["identity_and_loop_errors"] or check["sim_window_violations"]:
        raise ValueError(f"measured native CA bind fails: {check}")
    table = copy.deepcopy(clock_table)
    table.pop("count_aligned", None)
    for row in table["ports"]:
        row["added_cycles"] = b["ports"][row["port"]]["sched_lat"]
    groups = json.loads((out / "regions.json").read_text())["part_region"]
    # CAB annotates in count-frame coordinates; Landings consumes physical
    # clock-region rows. Preserve both through the tested frame_clock_regions API.
    for row in table["ports"]:
        row["src_region"], row["dst_region"] = row["src"], row["dst"]
    table = CAB.annotate_table(table, b, root_settle_cycles=64, strap_form=True)
    for row in table["ports"]:
        row["src_region"], row["dst_region"] = groups[row["src"]], groups[row["dst"]]
    ca = table["count_aligned"]
    for part, role in ca["parts"].items():
        if role["role"] != "origin" or role["region"] != part:
            raise ValueError(f"measured independent origin lost for {part}: {role}")
    ca["frame_clock_regions"] = groups
    if clock_table["count_aligned"].get("start_reset_wave"):
        ca["start_reset_wave"] = True
    dump(out / "native_pipeline_stage_cycles.json", price_existing_pipeline_stages(table, raw))
    label = "prototype" if provisional else "measured"
    dump(out / ("native_" + label + "_bind.json"), b)
    dump(out / ("sidecar_native_" + label + ".json"), table)
    dump(out / ("native_" + label + "_bind_check.json"), check)
    return table


def compose(raw, table, source, out, oldside, band_cache=None):
    import clock_landing_plan as CLP
    # Generated reset/START references belong to the previous origin/mask.
    base = copy.deepcopy(raw)
    cleared = {}
    keys = ("landing_reader_start", "landing_writer_start", "landing_raw_branches",
            "landing_local_resets", "landing_origin_rect_um")
    native_origins = bool(table["count_aligned"].get("frame_clock_regions"))
    for tn, t in base["partition_types"].items():
        if native_origins:
            # This flag selects u_cland_rstart_rx physical groups and copies;
            # a new ordinary count origin emits u_cland_origin instead.
            t.pop("landing_relay_start_copy", None)
        ck = t.get("clock", {})
        cleared[tn] = [k for k in keys if k in ck]
        for k in keys:
            ck.pop(k, None)
    observer = oldside.get("collector", {}).get("observer")
    if not observer:
        raise ValueError("current actual monitor observer absent; refusing guessed observer")
    obs = {k: observer[k] for k in ("module", "instance_suffix", "fault_port", "ready_port")}
    original_band, original_multi = CLP._storage_band, CLP._storage_rects_staged
    cache_stats = collections.Counter()
    cache = json.loads(Path(band_cache).read_text())["partition_types"] if band_cache else {}
    def cached(t, bus, width, used, phy=(), resets=()):
        names = [t.get("module"), t.get("landing_base_type")]
        candidates = [cache[n] for n in names if n in cache]
        for ct in candidates:
            b = ct.get("clock", {}).get("landing_contract", {}).get("bands", {}).get(bus)
            if not b or int(b.get("width", -1)) != width or ct["outline_um"] != t["outline_um"]:
                continue
            rects = b.get("rects_um") or [b.get("rect_um")]
            if any(not r for r in rects): continue
            obs_ = CLP._band_obstacles(t, used, phy, resets)
            px, py = CLP._bus_xy(t, bus)
            if any(CLP._hop(r, px, py) > 405.-2.16+1e-6 or
                   any(CLP._rect_overlap(r, o) for o in obs_) for r in rects):
                continue
            cache_stats["hits"] += 1
            return copy.deepcopy(b)
        cache_stats["misses"] += 1
        return None
    def band(t, bus, width, used, **kw):
        b = cached(t, bus, width, used, kw.get("phy", ()), kw.get("resets", ()))
        if b:
            if b.get("rects_um"): raise ValueError("cached multi-rectangle band uses standard multi path")
            return b
        return original_band(t, bus, width, used, **kw)
    def multi(t, bus, width, used, **kw):
        return cached(t, bus, width, used, kw.get("phy", ()), kw.get("resets", ())) or original_multi(t, bus, width, used, **kw)
    if cache: CLP._storage_band, CLP._storage_rects_staged = band, multi
    try:
        result = CLP.compose(base, table, plan_path=source, observer_part=observer["part"],
                             observer=obs, monitor="reset", forward_source="clk",
                             band_multi_rect=True)
    finally:
        CLP._storage_band, CLP._storage_rects_staged = original_band, original_multi
    if cache:
        dump(out / "band_cache_reuse.json", dict(source=band_cache, counts=dict(cache_stats),
             guards="exact width/outline, all current macro/FT/PHY/reset/used-band obstacles and every402.84um pin-to-band corner", physical_qualified=False))
    if isinstance(result, tuple):
        plan, side = result[:2]
        extra = result[2:]
    else:
        raise TypeError(f"unexpected compose result: {type(result)}")
    mapb = (out / "regions.json").read_bytes()
    sp = plan.setdefault("clock", {}).setdefault("spine", {})
    sp.update(topology="link_htree",
              feed=feed_ref(out / "feed.json", parts=_part_names(plan)),
              region_map=dict(path="regions.json", sha256=hashlib.sha256(mapb).hexdigest()))
    import schema as S
    P = S.Plan(plan, out / "plan_c.json")
    before = {l: x["cycles"] for l, x in raw.get("latency", {}).get("lanes", {}).items()}
    delta = []
    for lane in plan["lanes"]:
        lid = lane["id"]
        entry = P.lane_latency(lid)
        entry["param"] = plan["latency"]["lanes"].get(lid, {}).get("param", "LAT_"+lid)
        plan["latency"]["lanes"][lid] = entry
        if lid in before and before[lid] != entry["cycles"]:
            delta.append(dict(lane=lid, old=before[lid], new=entry["cycles"],
                              added_cycles=entry["cycles"]-before[lid], kind="CA_REGION"))
    dump(out / "lane_cycle_delta.json", delta)
    dump(out / "plan_c.json", plan)
    dump(out / "eW_sidecar.json", side)
    if not table["count_aligned"].get("frame_clock_regions"):
        dump(out / "scope_disposition.json", dict(verdict="SUPERSEDED_164_COUNT_FRAME_VARIANT", physical_qualified=False, reason="32newPHYfixedrelays undesired; use196independent count origins on164physical clock groups after measured native-clock START"))
    dump(out / "compose_extra.json", extra)
    changed = {tn: [k for k in set(raw["partition_types"][tn]) | set(t)
                    if raw["partition_types"][tn].get(k) != t.get(k)]
               for tn, t in plan["partition_types"].items() if tn in raw["partition_types"]
               and t != raw["partition_types"][tn]}
    dump(out / "type_impact.json", dict(changed=changed,
                                       new_types=sorted(set(plan["partition_types"])-set(raw["partition_types"])),
                                       cleared_previous_origin_fields=cleared,
                                       physical_qualified=False))


def feed_ref_main(argv):
    """feed-ref PLAN FEED OUT: rewrite clock.spine.feed of PLAN from the committed FEED doc (root from the doc)."""
    ap = argparse.ArgumentParser(prog="kv_split_regions.py feed-ref")
    ap.add_argument("plan")
    ap.add_argument("feed")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    ref = restamp_feed(plan, a.feed)
    dump(Path(a.out), plan)
    print(json.dumps(ref, sort_keys=True))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "feed-ref":
        return feed_ref_main(sys.argv[2:])
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("sidecar")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--v-ps-mm", type=float, default=290.0)
    ap.add_argument("--compose", action="store_true")
    ap.add_argument("--measured-ca", help="released both-edge measured clock-START CA doc; independent partition origins")
    ap.add_argument("--band-cache", help="private exact previously generated band geometry; recheck all current obstacles/reach")
    ap.add_argument("--prototype-ca", help="explicit unmeasured standard-origin body prototype; never measured qualification")
    a = ap.parse_args()
    if a.measured_ca and a.prototype_ca:
        ap.error("choose measured-ca or prototype-ca")
    sys.path.insert(0, str(Path(a.repo) / "tools/die_plan"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    side = json.loads(Path(a.sidecar).read_text())
    raw, table, scored = model(a.plan, side, out, a.v_ps_mm)
    if table is None:
        return 3
    prepare_native_form(raw, side, scored, out)
    if a.measured_ca or a.prototype_ca:
        table = bind_native_measurement(raw, table, a.measured_ca or a.prototype_ca, out, provisional=bool(a.prototype_ca))
    if a.prototype_ca:
        dump(out / "prototype_scope.json", dict(prediction_only=True, physical_qualified=False, source="standard origin/START body prototype; timing/K must be replaced by measured clock START", source_ca=a.prototype_ca))
    if a.compose:
        compose(raw, table, a.plan, out, side, band_cache=a.band_cache)
    status = json.loads((out / "status.json").read_text())
    print(json.dumps({k: status[k] for k in ("verdict", "physical_qualified", "root", "regions_after")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
