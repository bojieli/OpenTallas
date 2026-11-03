#!/usr/bin/env python3
"""S81 plan event step 4 (DIE-S81-50/diegrt 11-03): refresh STALE landing collector_tree snapshots.

Census after steps 1-3 (census.py): 191/194 published landing collector_trees equal reset_tree.for_type on the
current plan; 3 do not, under every tools tree since source39 (pre-existing, not caused by this event):
  ot_s81sl_leaf__t29 / ot_s81sl_leaf__t73: core u_lf.u_ve.u_s (ot_s81sl_ve_s, R180) uses ot_s81sl_ve_s_tpl_w1728.lef;
    the snapshot was solved with the wider LEF, so its rst_n pin (and the relays that drive it) sit 8.64 um to the
    east -- INSIDE the core outline (origin x + 0 .. 172.8 um).  The re-solve puts the pin on the LEF and the relays
    outside the core.
  iqf__t1: one relay (u_rrl_109) re-sites 2.16 um.
Fix = republish the re-solved tree (plan + landed sidecar collector.types[<t>].tree) ONLY when the reset contract is
kept: every added_tap_recentre.GUARD_KEYS field equal except the geometric fields of core_resets (pin_um, xy), same
relay count and the same (q, d) relay graph; and every re-sited relay's 4.32-um site box
(clock_landing_plan.reset_site_rects) stays clear of the type's landing band rects / group rects and of the hard
core outlines.  Anything else is reported and left alone.

    refresh_stale_trees.py PLAN --types a,b --sidecar SIDE --out PLAN2 --sidecar-out SIDE2 --report R.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import added_tap_recentre as ATR  # noqa: E402
from clock_landing_plan import reset_site_rects  # noqa: E402

GEOM = ("pin_um", "xy")


def _strip(cr):
    return [{k: v for k, v in c.items() if k not in GEOM} for c in cr or []]


def contract_kept(pub, new):
    """None when new keeps pub's reset contract (geometry may move), else the first difference"""
    for k in ATR.GUARD_KEYS:
        a, b = pub.get(k), new.get(k)
        if k == "core_resets":
            a, b = _strip(a), _strip(b)
        if ATR._norm(a) != ATR._norm(b):
            return k
    g = lambda t: sorted((r.get("q"), r.get("d"), r.get("name")) for r in t.get("relays", []))
    return None if g(pub) == g(new) else "relay graph"


def _over(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def blockers(P, raw, tn, tree):
    """landing band / group rects and hard-core outlines of tn (um, type frame)"""
    lc = raw["partition_types"][tn]["clock"]["landing_contract"]
    out = []
    for k, b in (lc.get("bands") or {}).items():
        for r in b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else []):
            out.append(("band:" + k, r))
    out += [("group:" + k, r) for k, r in (lc.get("group_rects_um") or {}).items()]
    from placement_obstacles import placement_boxes
    out += [("obst:" + k, list(r)) for k, r in placement_boxes(P.types[tn], halo=0.0).items()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("--types", required=True); ap.add_argument("--sidecar", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--sidecar-out", required=True); ap.add_argument("--report")
    a = ap.parse_args()
    raw = S.load(a.plan); P = S.Plan(raw, a.plan)
    side = json.loads(Path(a.sidecar).read_text())
    recs = []
    for tn in a.types.split(","):
        pub = ATR.published_tree(raw, tn)
        rec = dict(type=tn)
        recs.append(rec)
        if pub is None:
            rec["skip"] = "no published collector_tree"; continue
        new = ATR._norm(RT.for_type(P, tn))
        if ATR._norm(pub) == new:
            rec["skip"] = "already current"; continue
        bad = contract_kept(ATR._norm(pub), new)
        if bad:
            rec["skip"] = f"reset contract changes ({bad}): not refreshed"; continue
        key = lambda r: (r.get("name"), round(float(r["xy"][0]), 4), round(float(r["xy"][1]), 4))
        moved = [r for r in new["relays"] if key(r) not in {key(o) for o in pub["relays"]}]
        old_rects = reset_site_rects(pub)
        blk = blockers(P, raw, tn, new)
        hits = [(r["name"], nm) for r in moved for box in reset_site_rects(dict(relays=[r]))
                for nm, rr in blk if _over(box, rr)]
        rec["old_hits"] = sorted({(r["name"], nm) for r in pub["relays"] if key(r) not in {key(o) for o in new["relays"]}
                                  for box in reset_site_rects(dict(relays=[r])) for nm, rr in blk if _over(box, rr)})
        rec["moved"] = [(r["name"], r["xy"]) for r in moved]
        if hits:
            rec["skip"] = f"re-sited relays overlap {sorted(set(hits))[:6]}: not refreshed"; continue
        rec["republished"] = dict(zip(("relays_before", "relays_after", "relays_changed"), ATR.republish(P, raw, tn, side)))
        rec["n_old_rects"] = len(old_rects)
    Path(a.sidecar_out).write_text(json.dumps(side, separators=(",", ":")))
    Path(a.out).write_text(ATR.dumps_like(raw, Path(a.plan).read_text()))
    rep = dict(plan=a.plan, types=recs)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(recs)[:3000])
    return 0 if all("republished" in r for r in recs) else 1


if __name__ == "__main__":
    sys.exit(main())
