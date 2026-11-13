#!/usr/bin/env python3
"""QC-S28-F F4 (TAP-CAP): clock.tap_target_sinks lowered on density-tap types whose kit tap split (taps.assign on the
s28 sink bins) leaves a tap over clock.tap_max_sinks.  The density taps re-derive; forwarded-clock exports
(landing_contract.pins[].source_clock_port/_tap) re-point to the NEW tap nearest the OLD one and the published collector
tree is re-solved with added_tap_recentre.republish -- the make_s28.py compose rule, unchanged.  collector_reattach.py
runs after this.  0 cycles (no RTL, core, bus, station, pin cycle).
usage (cwd SRC): taptarget_s28f.py PLAN_IN PLAN_OUT REPORT SIDE_IN SIDE_OUT TYPE:TARGET [...]"""
import copy, hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path("tools/die_plan").resolve()))
import schema, taps as TP, added_tap_recentre as AT, reset_tree as RT  # noqa: E402
PIN, POUT, REPF, SIN, SOUT = sys.argv[1:6]
ITEMS = [(a.split(":")[0], int(a.split(":")[1])) for a in sys.argv[6:]]
text = open(PIN).read(); P = json.loads(text)


def grid(raw, tn):
    return {n: (x, y) for n, x, y in schema.tap_grid(schema.Plan(copy.deepcopy(raw), PIN), tn)}


def split(raw, tn):
    Pl = schema.Plan(copy.deepcopy(raw), PIN); ck = Pl.types[tn]["clock"]
    cap, rad = int(ck.get("tap_max_sinks", 1200)), float(ck.get("tap_radius_um", 200))
    g = schema.tap_grid(Pl, tn)
    load, far, _ = TP.assign([(n, x, y) for n, x, y in g], TP.sink_sites(Pl, tn), cap, rad, max_distance_um=rad)
    return dict(taps=len(g), max_load=round(max(load)), over_cap=sum(1 for v in load if v > cap), max_dist=round(max(far), 1))


rep = {}
before = {tn: grid(P, tn) for tn, _ in ITEMS}
for tn, tg in ITEMS:
    ck = P["partition_types"][tn]["clock"]
    if ck.get("tap_mode") != "density" or not ck.get("sink_bins_file"):
        raise SystemExit(f"{tn}: not a density type with sink bins")
    b = split(P, tn)
    old = ck.get("tap_target_sinks")
    ck["tap_target_sinks"] = tg
    rep[tn] = dict(changed=[f"clock.tap_target_sinks {old} -> {tg}"], split_before=b, split_after=split(P, tn))
for tn, _ in ITEMS:
    lc = P["partition_types"][tn]["clock"].get("landing_contract", {})
    g0, g1 = before[tn], grid(P, tn)
    used = {q.get(k) for q in lc.get("pins", []) for k in ("source_clock_port", "source_clock_tap") if q.get(k)}
    used.discard("clk")
    m = {}
    for u in sorted(used):
        x0, y0 = g0[u]
        new = min(g1, key=lambda k: (math.hypot(g1[k][0] - x0, g1[k][1] - y0), k))
        m[u] = (new, round(math.hypot(g1[new][0] - x0, g1[new][1] - y0), 3))
    for q in lc.get("pins", []):
        for k in ("source_clock_port", "source_clock_tap"):
            if q.get(k) in m:
                q[k] = m[q[k]][0]
    rep[tn].update(remap={u: v for u, v in m.items() if v[0] != u}, max_tap_move_um=max([v[1] for v in m.values()] or [0]))
stext = open(SIN).read(); side = json.loads(stext)
PP = schema.Plan(P, PIN)
for tn, _ in ITEMS:
    pub = AT.published_tree(P, tn)
    if pub is None:
        continue
    d_new = RT.for_type(PP, tn)["depth"]
    if d_new < pub["depth"]:
        rs = P["partition_types"][tn].setdefault("reset", {})
        if rs.get("wavefront_min_depth") is None:
            rs["wavefront_min_depth"] = pub["depth"]
            rep[tn]["changed"].append(f"reset.wavefront_min_depth = {pub['depth']}")
PP = schema.Plan(P, PIN)
for tn, _ in ITEMS:
    if AT.published_tree(P, tn) is None:
        continue
    old = AT._norm(AT.published_tree(P, tn))
    st = ((side.get("collector") or {}).get("types") or {}).get(tn)
    in_sync = st is None or AT._norm(st.get("tree")) == old
    rb, ra, rc = AT.republish(PP, P, tn, side if in_sync else None)
    new = AT.published_tree(P, tn)
    rep[tn].update(sidecar_tree="absent" if st is None else "republished" if in_sync else "kept",
                   tree_changed_keys=[k for k in AT.GUARD_KEYS if old.get(k) != AT._norm(new).get(k)],
                   reset_depth=[old.get("depth"), new.get("depth")], relays_changed=rc)
new = json.dumps(P, indent=1 if text.startswith("{\n") else None) + "\n"
if json.dumps(json.loads(text), indent=1 if text.startswith("{\n") else None) + "\n" != text:
    raise SystemExit("base style not reproduced")
Path(POUT).write_text(new)
Path(SOUT).write_text(json.dumps(side, indent=1 if stext.startswith("{\n") else None) + "\n")
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
Path(REPF).write_text(json.dumps(dict(base_sha256=sha(text.encode()), out_sha256=sha(new.encode()), types=rep), indent=1) + "\n")
for tn, r in rep.items():
    print(tn, r["changed"], r["split_before"], "->", r["split_after"], "remap", r["remap"], "tree", r.get("tree_changed_keys"), r.get("reset_depth"))
