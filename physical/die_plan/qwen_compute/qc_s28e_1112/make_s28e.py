#!/usr/bin/env python3
"""QC-S28-E (DIE-QC-99, 11-12): glue clock -> the QC density-tap form (class HOLD-TAP-SPLIT / tap_density_class_1106
recipe), the one QC soft type still on the R4 grid (tap pitch 400 -> 8 taps on 778x1469) with no sink bins.
Measured (11-10 attempt_9 3_place, auto_geom): clk family 22,796 sinks, clk_t6 14,033 and clk_t7 4,118 (cap 3000, cap moves
within 200 um find no tap: the logic clumps in the N third).  clk_d2d (21,796 sinks) is NOT touched: it is the die-to-die
forwarded clock, one RTL port, split in the kit by clock_edge_split.tcl (OT_EDGE_SPLIT_PORTS) -> REACH-FIX-1 class item.

  compose BASE OUT BINS_REL REPORT --sidecar SIDE_IN SIDE_OUT
      glue.clock: tap_mode density, tap_max_sinks 1200, tap_target_sinks 900, tap_radius_um 200, sink_bins_file BINS_REL
      (+ tap_pair_affinity kept); landing_contract.pins[].source_clock_port/_tap re-pointed from the old grid tap to the
      NEW tap nearest it (apply_vis_resite rule, as make_s28 compose); collector tree re-published
      (added_tap_recentre.republish) and wavefront_min_depth kept if the tree gets shallower (make_s28 rule).
  Run from a repo root (tools/die_plan importable), python3 -I.  collector_reattach.py runs after this.
EQ: clock tap / landing source-tap / collector re-solve only; no RTL logic, bus, station or pipeline change."""
import hashlib, json, math, sys
from pathlib import Path
TN = "glue"
KEYS = dict(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=900, tap_radius_um=200.0)


def _grid(schema, raw, path, tn):
    return {n: (x, y) for n, x, y in schema.tap_grid(schema.Plan(raw, path), tn)}


def compose(base, out, bins_rel, report, side_in, side_out):
    sys.path.insert(0, str(Path("tools/die_plan").resolve()))
    import schema
    import added_tap_recentre as AT
    import reset_tree as RT
    text = open(base).read()
    P = json.loads(text)
    g0 = _grid(schema, json.loads(text), base, TN)
    ck = P["partition_types"][TN]["clock"]
    if ck.get("tap_mode", "grid") != "grid" or ck.get("sink_bins_file"):
        raise SystemExit(f"{TN}: base clock is not the grid form ({ck.get('tap_mode')}, {ck.get('sink_bins_file')})")
    doc = json.loads(Path(bins_rel).read_text())
    if doc.get("type") != TN or doc.get("n", 0) <= 0:
        raise SystemExit("bins file empty or for another type")
    ch = []
    for k, v in KEYS.items():
        ck[k] = v; ch.append(f"clock.{k} = {v}")
    ck["sink_bins_file"] = bins_rel; ch.append(f"clock.sink_bins_file = {bins_rel}")
    rep = {"changed": ch, "bins_sha256": hashlib.sha256(Path(bins_rel).read_bytes()).hexdigest(), "bins_n": doc["n"],
           "bins_proxy": bool(doc.get("proxy"))}
    g1 = _grid(schema, P, base, TN)
    lc = ck.get("landing_contract", {})
    used = {q.get(k) for q in lc.get("pins", []) for k in ("source_clock_port", "source_clock_tap") if q.get(k)}
    used.discard("clk")
    m = {}
    for u in sorted(used):
        if u not in g0:
            raise SystemExit(f"referenced tap {u} not in the base grid")
        x0, y0 = g0[u]
        new = min(g1, key=lambda k: (math.hypot(g1[k][0] - x0, g1[k][1] - y0), k))
        m[u] = (new, round(math.hypot(g1[new][0] - x0, g1[new][1] - y0), 3))
    for q in lc.get("pins", []):
        for k in ("source_clock_port", "source_clock_tap"):
            if q.get(k) in m:
                q[k] = m[q[k]][0]
    rep.update(taps_before=len(g0), taps_after=len(g1), taps_after_xy={k: list(v) for k, v in g1.items()},
               remap={u: v for u, v in m.items() if v[0] != u}, max_tap_move_um=max([v[1] for v in m.values()] or [0]))
    stext = open(side_in).read()
    side = json.loads(stext)
    PP = schema.Plan(P, base)
    pub = AT.published_tree(P, TN)
    if pub is not None:
        d_new = RT.for_type(PP, TN)["depth"]
        if d_new < pub["depth"]:
            rs = P["partition_types"][TN].setdefault("reset", {})
            rs["wavefront_min_depth"] = pub["depth"]
            rep["changed"].append(f"reset.wavefront_min_depth = {pub['depth']} (bins tree depth {d_new})")
        PP = schema.Plan(P, base)
        old = AT._norm(AT.published_tree(P, TN))
        st = ((side.get("collector") or {}).get("types") or {}).get(TN)
        in_sync = st is None or AT._norm(st.get("tree")) == old
        rb, ra, rc = AT.republish(PP, P, TN, side if in_sync else None)
        new = AT.published_tree(P, TN)
        rep.update(sidecar_tree=("absent" if st is None else "republished" if in_sync else "kept (differed)"),
                   tree_changed_keys=[k for k in AT.GUARD_KEYS if old.get(k) != AT._norm(new).get(k)],
                   reset_depth=[old.get("depth"), new.get("depth")], relays=[rb, ra], relays_changed=rc)
    else:
        rep["tree_changed_keys"] = None
    new = json.dumps(P, indent=1 if text.startswith("{\n") else None) + "\n"
    Path(out).write_text(new)
    Path(side_out).write_text(json.dumps(side, indent=1 if stext.startswith("{\n") else None) + "\n")
    sha = lambda b: hashlib.sha256(b).hexdigest()
    Path(report).write_text(json.dumps({"event": "QC-S28-E glue density taps", "base": base,
        "base_sha256": sha(text.encode()), "out_sha256": sha(new.encode()),
        "sidecar_in_sha256": sha(stext.encode()), "sidecar_out_sha256": sha(Path(side_out).read_bytes()),
        "rtl_change": False, "data_cycles": 0, "pin_cycles": 0, "types": {TN: rep}}, indent=1) + "\n")
    print(TN, f"taps {rep['taps_before']}->{rep['taps_after']} remap {len(rep['remap'])} max_move {rep['max_tap_move_um']}"
          f" tree {rep.get('tree_changed_keys')} depth {rep.get('reset_depth')}")


def hist(base, new, out):
    """bins inventory (the NEW plan's glue sink_bins_file) split onto the base grid taps (cap = base cap) and onto the
    new density taps (cap 1200) by the kit rule taps.assign (nearest tap, then cap moves within the radius)."""
    sys.path.insert(0, str(Path("tools/die_plan").resolve()))
    import schema, taps as TP
    PB = schema.Plan(json.loads(open(base).read()), base)
    PN = schema.Plan(json.loads(open(new).read()), new)
    real = TP.sink_sites(PN, TN)
    res = {"real_sinks": round(sum(p[2] for p in real))}
    for tag, P in (("base", PB), ("new", PN)):
        ck = P.types[TN]["clock"]
        cap = int(ck.get("tap_max_sinks", 1500 if ck.get("tap_mode") == "density" else 3000))
        rad = float(ck.get("tap_radius_um", 200.0))
        xy = [(n, x, y) for n, x, y in schema.tap_grid(P, TN)]
        load, far, asg = TP.assign(xy, real, cap, rad, max_distance_um=rad)
        near = TP.tap_loads([(x, y) for _, x, y in xy], real)
        res[tag] = dict(mode=ck.get("tap_mode", "grid"), cap=cap, radius_um=rad, taps=len(xy),
                        nearest_max=round(max(q[0] for q in near)), kit_max=round(max(load)),
                        kit_over_cap=sum(1 for v in load if v > cap), kit_far_um=round(max(far), 1),
                        kit_hist=sorted((round(v) for v in load), reverse=True)[:8])
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "compose":
        i = a.index("--sidecar")
        compose(a[1], a[2], a[3], a[4], a[i + 1], a[i + 2])
    elif a and a[0] == "hist":
        hist(a[1], a[2], a[3])
    else:
        raise SystemExit(__doc__)
