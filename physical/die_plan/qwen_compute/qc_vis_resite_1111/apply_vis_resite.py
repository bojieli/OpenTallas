#!/usr/bin/env python3
"""QC-VIS-RESITE 11-12: apply the stm ROM VIS placement (positions/orients only) onto a QC plan (s25 or s26).

    python3 -I apply_vis_resite.py PLAN_IN DELTA.json PLAN_OUT --repo REPO [--sidecar SIDECAR_IN SIDECAR_OUT]

DELTA = delta_stm_vis.json (this dir): changes[type].cores[inst] = {origin_um, orient}; before[type][inst] = the
s25 origin/orient each core must still have (a plan that moved these cores since s25 is refused, not merged).
hard_cores[].origin_um / orient change.  Tap-name follow-up (structural, found by the strict bind): these types use
clock.tap_mode "density", whose taps (schema.tap_grid -> taps.density_taps) are re-derived from the sinks and the
macro boxes and numbered in order, so moving the ROMs renumbers/relocates the clk_t<i> taps.  The forwarded-clock
exports name their source tap (landing_contract.pins[].source_clock_port/_tap); each such name
is re-pointed to the tap of the NEW grid nearest the OLD tap's position (same physical source; displacement
reported).  For any other tap_mode the grid does not depend on core positions and the map is the identity.
Nothing else changes (EQ by construction: buses, stations, register counts, outline, pins, tap count rules)."""
import json, math, sys
from pathlib import Path

args = sys.argv[1:4]
src, dl, out = args[:3]
repo = Path(sys.argv[sys.argv.index("--repo") + 1]).resolve()
sys.path.insert(0, str(repo / "tools" / "die_plan"))
import schema  # noqa: E402

text = open(src).read(); P = json.loads(text); D = json.load(open(dl))


def grid(raw, tn):
    return {n: (x, y) for n, x, y in schema.tap_grid(schema.Plan(raw, src), tn)}


before = {tn: grid(P, tn) for tn in D["changes"]}
n = 0
for tn, ch in D["changes"].items():
    t = P["partition_types"][tn]
    by = {h["inst"]: h for h in t["hard_cores"]}
    for inst, v in ch["cores"].items():
        h = by[inst]; b = D["before"][tn][inst]
        if h["origin_um"] != b["origin_um"] or h.get("orient", "R0") != b["orient"]:
            raise SystemExit(f"{tn} {inst}: plan has {h['origin_um']} {h.get('orient')} not the s25 {b}: refuse")
        h["origin_um"] = list(v["origin_um"]); h["orient"] = v["orient"]; n += 1
rep = {}
for tn in D["changes"]:
    t = P["partition_types"][tn]; lc = t.get("clock", {}).get("landing_contract", {})
    g0, g1 = before[tn], grid(P, tn)
    used = {q.get(k) for q in lc.get("pins", []) for k in ("source_clock_port", "source_clock_tap") if q.get(k)}
    used.discard("clk")
    m = {}
    for u in sorted(used):
        if u not in g0:
            raise SystemExit(f"{tn}: referenced tap {u} not in the input plan's tap grid")
        x0, y0 = g0[u]
        new = min(g1, key=lambda k: (math.hypot(g1[k][0] - x0, g1[k][1] - y0), k))
        m[u] = (new, round(math.hypot(g1[new][0] - x0, g1[new][1] - y0), 3))
    for q in lc.get("pins", []):
        for k in ("source_clock_port", "source_clock_tap"):
            if q.get(k) in m:
                q[k] = m[q[k]][0]
    rep[tn] = {"taps_before": len(g0), "taps_after": len(g1), "remap": {u: v for u, v in m.items() if v[0] != u},
               "max_tap_move_um": max([v[1] for v in m.values()] or [0])}
# Reset contract follow-up: the published landing collector_tree (reset relays per tap, n_clock_taps, tap_depth) was
# solved on the old tap set; re-solve it with the current tools on the moved plan (added_tap_recentre.republish, plan
# and, with --sidecar IN OUT, the landed sidecar's collector.types[t].tree, which must equal the plan's tree first).
import added_tap_recentre as AT  # noqa: E402
PP = schema.Plan(P, src)
side = None
if "--sidecar" in sys.argv:
    si, so = sys.argv[sys.argv.index("--sidecar") + 1: sys.argv.index("--sidecar") + 3]
    stext = open(si).read(); side = json.loads(stext)
for tn in D["changes"]:
    if AT.published_tree(P, tn) is not None:
        old = AT._norm(AT.published_tree(P, tn))
        rb, ra, rc = AT.republish(PP, P, tn, side)
        new = AT.published_tree(P, tn)
        rep[tn].update(tree_changed_keys=[k for k in AT.GUARD_KEYS if old.get(k) != AT._norm(new).get(k)],
                       reset_depth=[old.get("depth"), new.get("depth")], relays=[rb, ra], relays_changed=rc)
open(out, "w").write(json.dumps(P, indent=1 if text.startswith("{\n") else None) + "\n")
if side is not None:
    open(so, "w").write(json.dumps(side, indent=1 if stext.startswith("{\n") else None) + "\n")
open(out + ".taps.json", "w").write(json.dumps(rep, indent=1) + "\n")
print(f"applied {n} core moves in {len(D['changes'])} types")
for tn, r in rep.items():
    print(tn, f"taps {r['taps_before']}->{r['taps_after']} renamed {len(r['remap'])} max_tap_move {r['max_tap_move_um']} um")
