#!/usr/bin/env python3
"""KV-BIND-R3 10-26: R8 landing table + authoritative extras for the landed plan die_plan_cland_r3.json (+3 data cycles
per landed crossing, KV-LAND-R3).  The 2144 tables were made on die_plan.json; the landings move 524 lane depths
(+3/+6/+9/+12), so every member on those lanes is R8_STALE and equal-latency groups whose legs landed unevenly need
re-padding.  Method = KV-405 r8_rebase (r8.rebase + r8.pads --bus leaf --replica type), inputs repo-relative:
  r8/b33_bus_groups_r8.json.gz  the B33 bind of record (claude/kv-batch-r2-1026@2a130d7df6, strict/R8/verify PASS)
                                bus groups after r8_fault_exempt.py + r8_invariant_split.py, bound on die_plan.json
  old lane depths               die_plan.json latency.lanes (== B33 bind_latency.json buses plan_cycles, all 2404)
  new lane depths               gen.latency_table(die_plan_cland_r3.json)
Pass 2 (KV-BIND-R3 after B35): r8/b35_bus_groups_r8.json.gz (the B35 bind of this plan at 84104e5023, after
r8_fault_exempt.py + r8_invariant_split.py) replaces the rebased B33 groups: exact bound depths for every member.
Extras (asbuilt.land_r8_extra, authoritative per id): each member on a moved lane gets bound += d; its landed depth is
the schedule the extra exists for (PV calendar: landed == as-built; vport request: materialised RT), so pad -= d keeps
landed.  A member whose pad < d cannot keep landed: it is reported (INFEASIBLE) and keeps pad 0, landed = new bound
(the PV calendar check then fails on it: a schedule conflict, never hidden).
    python3 make_r8_cland_r3.py  -> r8/qwen_kvsys_r8_landing.json, r8/vport_request_extra_cland_r3.json,
                                    r8/pv_calendar_restore_cland_r3.json, r8/make_r8_cland_r3.report.json"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import gen      # noqa: E402
import r8       # noqa: E402
import schema as S  # noqa: E402

KV = ROOT / "physical/die_plan/qwen_kvsys"
OLD = KV / "die_plan.json"
NEW = KV / "die_plan_cland_r3.json"
EXTRAS = [KV / "bind/kvbind1025/r8_position_2144/vport_request_extra.json",
          KV / "bind/kvbind1025/pv_calendar_restore_b31.json"]
OUT = HERE / "r8"
BG35 = OUT / "b35_bus_groups_r8.json.gz"   # B35 bind (84104e5023) bus groups after r8_fault_exempt + r8_invariant_split


def main():
    old = {k: v["cycles"] for k, v in json.loads(OLD.read_text())["latency"]["lanes"].items()}
    raw = S.load(str(NEW))
    tab = gen.latency_table(S.Plan(raw))
    inplan = raw["latency"]["lanes"]
    sk = S.Plan(raw).landed_skew()
    if sk:
        raise SystemExit("landed bundle over the landing window margin: " + "; ".join(sk[:8]))
    # gen.py latency --inplace semantics (gen.py itself refuses this plan only for the islands key die_islands_um,
    # which the schema of this branch does not list): the landed plan priced +3 on the landed lanes but not the R8
    # GROUP pads of their equal-latency lane groups (lane_pads), so 3 group-mate lanes stayed 3 short in latency.lanes
    stale = {k: (inplan[k]["cycles"], tab[k]["cycles"]) for k in tab if tab[k]["cycles"] != inplan[k]["cycles"]}
    if stale:
        for k in stale:
            inplan[k] = json.loads(json.dumps(tab[k]))
        NEW.write_text(json.dumps(raw, indent=1) + "\n")
    if BG35.exists():
        # pass 2: the bus groups of the B35 bind of THIS plan (bound depths exact, incl. multi-lane members that
        # r8.rebase cannot move: 5894 of 12228 B33 members carry no single lane)
        bg = json.loads(gzip.open(BG35, "rt").read())
        rb = dict(source=BG35.name, rebase="none (bound on this plan)")
    else:
        bg = json.loads(gzip.open(OUT / "b33_bus_groups_r8.json.gz", "rt").read())
        bl = dict(buses=[dict(lane=k, plan_cycles=c) for k, c in old.items()])
        bg, rb = r8.rebase(bg, bl, tab)
    bound = {r8.mkey(g, m): m["bound_stages"] for g in bg["landing"] for m in g["members"]}
    lp, sm = r8.write_pads(raw, bg, OUT, "type", "leaf")
    js = json.loads(lp.read_text())
    js["rebase"] = dict(old_plan=OLD.name, new_plan=NEW.name, **rb)
    lp.write_text(json.dumps(js, indent=0) + "\n")
    rep = dict(inplan_latency_fixed=stale, rebase=rb, table=sm, extras={})
    delta = {k: tab[k]["cycles"] - c for k, c in old.items() if tab[k]["cycles"] != c}
    for f in EXTRAS:
        x = json.loads(f.read_text())
        st = dict(members=len(x["members"]), moved=0, pad_absorbed=0, infeasible=[])
        for m in x["members"]:
            d = (bound[m["id"]] - m["bound"]) if m["id"] in bound else delta.get(m.get("lane"), 0)
            if not d:
                continue
            st["moved"] += 1
            m["bound"] += d
            if m["pad"] >= d:
                m["pad"] -= d
                st["pad_absorbed"] += 1
            else:
                st["infeasible"].append(dict(id=m["id"], lane=m["lane"], d=d, pad=m["pad"], landed_was=m["landed"],
                                             landed_now=m["bound"] + m["pad"]))
                m["landed"] = m["bound"] + m["pad"]
        x["note"] = x.get("note", "") + f" | KV-BIND-R3 rebased onto {NEW.name}: {st["moved"]} moved, " \
                                        f"{st["pad_absorbed"]} pad-absorbed, {len(st["infeasible"])} infeasible"
        o = OUT / (f.stem.replace("_b31", "").replace("_2144", "") + "_cland_r3.json")
        o.write_text(json.dumps(x, indent=0) + "\n")
        rep["extras"][f.name] = dict(out=o.name, **{k: (v if k != "infeasible" else len(v)) for k, v in st.items()},
                                     infeasible_list=st["infeasible"])
    (OUT / "make_r8_cland_r3.report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "extras"}))
    for k, v in rep["extras"].items():
        print(k, {a: b for a, b in v.items() if a != "infeasible_list"})


if __name__ == "__main__":
    main()
