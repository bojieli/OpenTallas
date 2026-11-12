#!/usr/bin/env python3
"""QC-EVENT-S28 (DIE-QC-99, 11-12): plan_qc99_s28 = plan_qc99_s27 + clock.sink_bins_file on all 31 QC density-tap types
that had none (class HOLD-TAP-SPLIT: without bins the density tap planner sees only the plan's face / ft / station
sinks, ~40 % of the netlist registers, so the kit's nearest-tap + cap split leaves taps over the 1200 cap and splits
station chains across taps; sle_su_c FF hold -410 ps, VISLAYOUT2-QC suc-hold 11-12).

Subcommands (run from the repo root, python3 -I):
  bins DUMP_DIR TYPE OUT.json --src NOTE     sink bins from a sinkdump28.tcl dump (sinks.tsv: x y master name net):
                                             every input ITerm on the die-clock nets clk / clk_t<i> of the row's own
                                             3_place.odb, 10.8-um bins, type frame (the DIE-QC-97 sinkdump.tcl /
                                             VISLAYOUT2-QC sle_su_c form: same keys, same binning).
  compose S27 S28 TYPES.json REPORT.json --sidecar SIDE_IN SIDE_OUT
                                             per listed type: clock.sink_bins_file = plan_of_record/sink_bins/<t>.json
                                             (+ tap_pair_affinity {} if absent: none are); the density taps are then
                                             re-derived from the full inventory, so the forwarded-clock exports'
                                             landing_contract.pins[].source_clock_port/_tap are re-pointed to the NEW
                                             tap nearest the OLD tap (apply_vis_resite.py rule), and the landing
                                             collector_tree is re-solved with added_tap_recentre.republish (plan and
                                             sidecar copy when it equals the s27 plan tree; a copy that already
                                             differed in s27 is kept).  collector_reattach.py runs after this.
  hist S27 S28 TYPES.json OUT.json [--dumps DIR]
                                             per type: the real register sinks (the bins file) split onto the s27
                                             taps and onto the s28 taps by the kit's rule (taps.assign: nearest tap,
                                             then cap moves within tap_radius_um), max sinks per tap vs the cap, taps
                                             over the cap; with --dumps, per-flop station chains (<inst>.r[k]) whose
                                             flops land on more than one tap.
Nothing else changes: no RTL, no core, no bus, no station, no pin cycle (EQ by construction; reset relays re-anchor by
site at bind, reset_anchor.resolve, same depth -> +0 cycles)."""
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

REL = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
BIN_UM = 10.8


def _tools():
    sys.path.insert(0, str(Path("tools/die_plan").resolve()))


def cmd_bins(dump, tn, out, src):
    d = Path(dump)
    die = [float(v) for v in (d / "die.txt").read_text().split()]
    c = collections.Counter()
    n = 0
    for ln in (d / "sinks.tsv").read_text().splitlines():
        x, y = (float(v) for v in ln.split("\t")[:2])
        cx, cy = x - die[0], y - die[1]
        c[(int(cx // BIN_UM), int(cy // BIN_UM))] += 1
        n += 1
    doc = dict(bin_um=BIN_UM, n=n,
               bins=[[round((i + 0.5) * BIN_UM, 3), round((j + 0.5) * BIN_UM, 3), k] for (i, j), k in sorted(c.items())],
               type=tn, placed_kit=tn, source=src)
    Path(out).write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"{tn}: {n} sinks in {len(doc['bins'])} bins -> {out}")


def _grid(schema, raw, path, tn):
    return {n: (x, y) for n, x, y in schema.tap_grid(schema.Plan(raw, path), tn)}


def cmd_compose(s27, s28, types_json, report, side_in, side_out):
    _tools()
    import schema
    import added_tap_recentre as AT
    text = open(s27).read()
    P = json.loads(text)
    types = json.loads(Path(types_json).read_text())
    before = {tn: _grid(schema, json.loads(text), s27, tn) for tn in types}
    rep = {}
    for tn in types:
        ck = P["partition_types"][tn]["clock"]
        if ck.get("tap_mode") != "density":
            raise SystemExit(f"{tn}: tap_mode {ck.get('tap_mode')} is not density")
        if ck.get("sink_bins_file"):
            raise SystemExit(f"{tn}: already has clock.sink_bins_file {ck['sink_bins_file']}")
        rel = f"{REL}/{tn}.json"
        doc = json.loads(Path(rel).read_text())
        if doc.get("type") != tn or not doc.get("bins") or doc.get("n", 0) <= 0:
            raise SystemExit(f"{tn}: bins file {rel} empty or for another type")
        ck["sink_bins_file"] = rel
        ch = ["clock.sink_bins_file"]
        if "tap_pair_affinity" not in ck:
            ck["tap_pair_affinity"] = {}
            ch.append("clock.tap_pair_affinity = {}")
        rep[tn] = {"changed": ch, "bins_sha256": hashlib.sha256(Path(rel).read_bytes()).hexdigest(), "bins_n": doc["n"]}
    for tn in types:
        t = P["partition_types"][tn]
        lc = t["clock"].get("landing_contract", {})
        g0, g1 = before[tn], _grid(schema, P, s27, tn)
        used = {q.get(k) for q in lc.get("pins", []) for k in ("source_clock_port", "source_clock_tap") if q.get(k)}
        used.discard("clk")
        m = {}
        for u in sorted(used):
            if u not in g0:
                raise SystemExit(f"{tn}: referenced tap {u} not in the s27 tap grid")
            x0, y0 = g0[u]
            new = min(g1, key=lambda k: (math.hypot(g1[k][0] - x0, g1[k][1] - y0), k))
            m[u] = (new, round(math.hypot(g1[new][0] - x0, g1[new][1] - y0), 3))
        for q in lc.get("pins", []):
            for k in ("source_clock_port", "source_clock_tap"):
                if q.get(k) in m:
                    q[k] = m[q[k]][0]
        rep[tn].update(taps_before=len(g0), taps_after=len(g1), remap={u: v for u, v in m.items() if v[0] != u},
                       max_tap_move_um=max([v[1] for v in m.values()] or [0]))
    stext = open(side_in).read()
    side = json.loads(stext)
    # a type whose bins make the legal reset tree SHALLOWER than its published collector tree keeps the published
    # release depth: reset.wavefront_min_depth = old depth (reset_tree pads, never shortens; precedent
    # sle_su_l1__clc6d66f5b 6).  Otherwise a collector child sitting at the root (depth 0) has no relay at depth -1
    # and the collector cycles would change.
    import reset_tree as RT
    PP = schema.Plan(P, s27)
    for tn in types:
        pub = AT.published_tree(P, tn)
        if pub is None:
            continue
        d_new = RT.for_type(PP, tn)["depth"]
        if d_new < pub["depth"]:
            rs = P["partition_types"][tn].setdefault("reset", {})
            if rs.get("wavefront_min_depth") is not None:
                raise SystemExit(f"{tn}: tree depth {pub['depth']} -> {d_new} with wavefront_min_depth already set")
            rs["wavefront_min_depth"] = pub["depth"]
            rep[tn]["changed"].append(f"reset.wavefront_min_depth = {pub['depth']} (bins tree depth {d_new})")
    PP = schema.Plan(P, s27)
    for tn in types:
        if AT.published_tree(P, tn) is not None:
            old = AT._norm(AT.published_tree(P, tn))
            st = ((side.get("collector") or {}).get("types") or {}).get(tn)
            # a sidecar copy that already differed from the plan's tree in s27 (9 su_l0/su_l1 types) is left as it was
            # (added_tap_recentre never refreshes a stale snapshot; the bind walks the plan tree: LC.effective_tree)
            in_sync = st is None or AT._norm(st.get("tree")) == old
            rb, ra, rc = AT.republish(PP, P, tn, side if in_sync else None)
            rep[tn]["sidecar_tree"] = ("absent" if st is None else "republished" if in_sync
                                       else "kept: differed from the s27 plan tree already")
            new = AT.published_tree(P, tn)
            rep[tn].update(tree_changed_keys=[k for k in AT.GUARD_KEYS if old.get(k) != AT._norm(new).get(k)],
                           reset_depth=[old.get("depth"), new.get("depth")], relays=[rb, ra], relays_changed=rc)
        else:
            rep[tn].update(tree_changed_keys=None)
    new = json.dumps(P, indent=1 if text.startswith("{\n") else None) + "\n"
    Path(s28).write_text(new)
    Path(side_out).write_text(json.dumps(side, indent=1 if stext.startswith("{\n") else None) + "\n")
    sha = lambda b: hashlib.sha256(b).hexdigest()
    doc = {"event": "QC-EVENT-S28 sink bins on the 31 density-tap types without clock.sink_bins_file",
           "base": s27, "base_sha256": sha(text.encode()), "out": s28, "out_sha256": sha(new.encode()),
           "sidecar_in_sha256": sha(stext.encode()), "sidecar_out_sha256": sha(Path(side_out).read_bytes()),
           "rtl_change": False, "data_cycles": 0, "pin_cycles": 0, "types": rep}
    Path(report).write_text(json.dumps(doc, indent=1) + "\n")
    for tn, r in rep.items():
        print(tn, f"taps {r['taps_before']}->{r['taps_after']} remap {len(r['remap'])} max_move {r['max_tap_move_um']}"
              f" tree {r.get('tree_changed_keys')} depth {r.get('reset_depth')}")


def _station_split(flops, asg):
    """chains <inst>.r[k]: count those whose flops sit on more than one tap"""
    g = collections.defaultdict(set)
    for (name, _, _), j in zip(flops, asg):
        m = re.match(r"^(.*)\.r\\?\[\d+\\?\]", name)
        if m:
            g[m.group(1)].add(j)
    return len(g), sum(1 for s in g.values() if len(s) > 1)


def cmd_hist(s27, s28, types_json, out, dumps=None):
    _tools()
    import schema
    import taps as TP
    P27 = schema.Plan(json.loads(open(s27).read()), s27)
    P28 = schema.Plan(json.loads(open(s28).read()), s28)
    types = json.loads(Path(types_json).read_text())
    res = {}
    for tn in types:
        ck = P28.types[tn]["clock"]
        cap = int(ck.get("tap_max_sinks", 1500))
        tgt = int(ck.get("tap_target_sinks", int(0.8 * cap)))
        rad = float(ck.get("tap_radius_um", 200.0))
        real = TP.sink_sites(P28, tn)      # bins inventory (+ control pins if clock.control_sinks)
        old_inv = TP.sink_sites(P27, tn)   # what the s27 planner saw
        r = dict(cap=cap, target=tgt, radius_um=rad, real_sinks=round(sum(p[2] for p in real)),
                 planner_s27_sinks=round(sum(p[2] for p in old_inv)))
        flops = None
        if dumps and (Path(dumps) / tn / "sinks.tsv").is_file():
            flops = []
            for ln in (Path(dumps) / tn / "sinks.tsv").read_text().splitlines():
                f = ln.split("\t")
                flops.append((f[3], float(f[0]), float(f[1])))
        for tag, P in (("s27", P27), ("s28", P28)):
            dt = TP.density_taps(P, tn)
            xy = [(n, x, y) for n, x, y, _, _ in dt]
            load, far, asg = TP.assign(xy, real, cap, rad, max_distance_um=rad)
            near = TP.tap_loads([(x, y) for _, x, y in xy], real)
            d = dict(taps=len(xy), planned_max=max(q[3] for q in dt),
                     nearest_max=round(max(q[0] for q in near)),
                     kit_max=round(max(load)), kit_over_cap=sum(1 for v in load if v > cap),
                     kit_over_target=sum(1 for v in load if v > tgt), kit_far_um=round(max(far), 1),
                     kit_hist=sorted((round(v) for v in load), reverse=True)[:6])
            if flops:
                pts = [(x, y, 1.0) for _, x, y in flops]
                _, _, fa = TP.assign(xy, pts, cap, rad, max_distance_um=rad)
                d["chains"], d["chains_split"] = _station_split(flops, fa)
            r[tag] = d
        res[tn] = r
        print(tn, json.dumps(r))
    Path(out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "bins":
        cmd_bins(a[1], a[2], a[3], a[a.index("--src") + 1])
    elif a[0] == "compose":
        i = a.index("--sidecar")
        cmd_compose(a[1], a[2], a[3], a[4], a[i + 1], a[i + 2])
    elif a[0] == "hist":
        cmd_hist(a[1], a[2], a[3], a[4], a[a.index("--dumps") + 1] if "--dumps" in a else None)
    else:
        raise SystemExit(__doc__)
