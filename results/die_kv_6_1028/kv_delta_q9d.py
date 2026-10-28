"""DIE-KV-6 KV plan delta q9c -> q9d (COORD 03:23 RISK-SWEEP-2 ASK defaults (1)+(2); METHODOLOGY 12.3 v5.0 early taps).
(1) EARLY CORE TAPS from each core's own view: clock.core_taps = "early" on every type with core taps; each core tap's
    insertion_ps / insertion_ff_ps = the tap-table row of its budget_owner module (schema.core_tap_early_ps then gives
    early = insertion - common latency, 0 for cores at or below it).  Modules without a row (NO VIEW) keep 250 = 0 early.
    Named core taps are ADDED for every hard-core instance of kv3_head_eighth_e0/e2/e6 (no planned tap on q9c): tap name
    = the instance (every clock pin of the core), xy = core origin + its clock-pin centre (pins file, orient-mapped).
    TAP TABLE HOOK: --tap-table JSON {module: {L_tt, L_ff, basis}}; default = RISK-SWEEP-2 c1_rows (ETM estimates,
    UNCHECKED); CORELAT-SQ-1 writes the same form for KV and replaces it with no code change.
(2) RESET REACH: reset.local_taps_um on every type whose final reset hop exceeds 405 um (reset_tree.consumer_taps +
    blockages, the RISK-SWEEP-2 C3 model): greedy cover of the free outline sample points by local taps placed at free
    sample points (outside hard-core boxes), target 380 um (25 um margin), until worst <= 380.
usage: kv_delta_q9d.py TOOLS_ROOT PLAN_IN PLAN_OUT [--tap-table J] [--report R]"""
import argparse
import copy
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tools")
ap.add_argument("plan")
ap.add_argument("out")
ap.add_argument("--tap-table", default="/srv/opentallas-scratch2/claude/risk-sweep-2/c1_rows.json")
ap.add_argument("--report")
ap.add_argument("--reach", type=float, default=380.0)
ap.add_argument("--step", type=float, default=17.28)
ap.add_argument("--skip-reset", action="store_true")
a = ap.parse_args()
sys.path.insert(0, a.tools + "/tools/die_plan")
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402

pp = Path(a.plan).resolve()
raw = json.load(open(pp))
tt = json.load(open(a.tap_table))
rows = tt["rows"] if isinstance(tt, dict) and "rows" in tt else tt
table = {r["module"]: r for r in (rows if isinstance(rows, list) else [dict(v, module=k) for k, v in rows.items()])
         if r.get("L_tt") is not None}
NEW_TAP = {"kv3_head_eighth_e0", "kv3_head_eighth_e2", "kv3_head_eighth_e6"}
rep = dict(tap_table=a.tap_table, core=[], added=[], reset=[])


def pin_centre(pins_file, orient, w, h):
    pf = json.load(open(pp.parent / pins_file))
    ck = [p for p in pf["pins"] if "clk" in p["name"]]
    x = sum(p["x"] for p in ck) / len(ck)
    y = sum(p["y"] for p in ck) / len(ck)
    o = orient or "R0"
    if o == "MX":
        y = h - y
    elif o == "MY":
        x = w - x
    elif o == "R180":
        x, y = w - x, h - y
    elif o != "R0":
        raise SystemExit(f"orient {o} not handled")
    return x, y, len(ck)


for tn, t in sorted(raw["partition_types"].items()):
    ck = t.get("clock") or {}
    taps = ck.get("taps") or []
    named = {tp["name"].split(".")[0] for tp in taps if tp.get("kind") == "core"}
    for h in t.get("hard_cores", []):
        if h["module"] in NEW_TAP and h["inst"] not in named:
            w, hh = h["outline_um"]
            x, y, n = pin_centre(h["pins_file"], h.get("orient"), w, hh)
            xy = [round(h["origin_um"][0] + x, 3), round(h["origin_um"][1] + y, 3)]
            taps.append(dict(name=h["inst"], kind="core", xy=xy, insertion_ps=250.0, budget_owner=h["module"],
                             note=f"DIE-KV-6 q9d: named core tap (every clock pin, {n} pins at the core centre entry); "
                                  "RISK-SWEEP-2 C1 / COORD 03:23"))
            rep["added"].append(dict(type=tn, inst=h["inst"], module=h["module"], xy=xy))
    if not any(tp.get("kind") == "core" for tp in taps):
        continue
    ck["taps"] = taps
    for tp in taps:
        if tp.get("kind") != "core":
            continue
        r = table.get(tp.get("budget_owner"))
        if r and float(r["L_tt"]) > 250.0:
            tp["insertion_ps"] = round(float(r["L_tt"]), 1)
            tp["insertion_ff_ps"] = round(float(r["L_ff"]), 1)
            tp["note"] = (tp.get("note", "") + f" | DIE-KV-6 q9d early tap: insertion {r['L_tt']}/{r['L_ff']} TT/FF "
                          f"from {r.get('basis', '?')} (tap table {Path(a.tap_table).name}, UNCHECKED until CORELAT-SQ-1)")
            rep["core"].append(dict(type=tn, tap=tp["name"], module=tp["budget_owner"], tt=tp["insertion_ps"],
                                    ff=tp["insertion_ff_ps"]))
    ck["core_taps"] = "early"
    t["clock"] = ck

if not a.skip_reset:
    P = S.Plan(copy.deepcopy(raw), str(pp))
    for tn in sorted(P.types):
        t = P.types[tn]
        if t.get("hard") and not t.get("hard_cores"):
            continue
        try:
            terms = [(x, y) for _, x, y in RT.consumer_taps(P, tn)]
        except Exception as e:  # noqa: BLE001
            rep["reset"].append(dict(type=tn, err=str(e)[:200]))
            continue
        w, h = t["outline_um"]
        boxes = RT.blockages(t, clear=0.0)
        pts = []
        y = a.step / 2
        while y < h:
            x = a.step / 2
            while x < w:
                if not any(b0 <= x <= b2 and b1 <= y <= b3 for b0, b1, b2, b3 in boxes):
                    pts.append((x, y))
                x += a.step
            y += a.step

        def dist(p, ts):
            return min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in ts)
        worst0 = max(dist(p, terms) for p in pts) if pts else 0
        if worst0 <= 405.0:
            continue
        unc = [p for p in pts if dist(p, terms) > a.reach]
        add = []
        while unc:
            best = max(pts[::2], key=lambda c: sum(1 for p in unc if abs(p[0] - c[0]) + abs(p[1] - c[1]) <= a.reach))
            add.append([round(best[0], 3), round(best[1], 3)])
            unc = [p for p in unc if abs(p[0] - best[0]) + abs(p[1] - best[1]) > a.reach]
        rt = raw["partition_types"][tn].setdefault("reset", {})
        rt["local_taps_um"] = rt.get("local_taps_um", []) + add
        worst1 = max(dist(p, terms + [tuple(q) for q in add]) for p in pts)
        rep["reset"].append(dict(type=tn, worst_before_um=round(worst0, 1), worst_after_um=round(worst1, 1),
                                 local_taps_added=len(add)))
        print(tn, round(worst0, 1), "->", round(worst1, 1), "taps", len(add), flush=True)

raw["note"] = raw.get("note", "") + " | DIE-KV-6 q9d: early core taps (tap table hook) + reset.local_taps_um (reach 405)"
json.dump(raw, open(a.out, "w"), indent=1)
if a.report:
    json.dump(rep, open(a.report, "w"), indent=1)
print(json.dumps(dict(core_taps_early=len(rep["core"]), named_added=len(rep["added"]),
                      reset_types=sum(1 for r in rep["reset"] if "local_taps_added" in r),
                      reset_taps=sum(r.get("local_taps_added", 0) for r in rep["reset"]),
                      reset_err=[r for r in rep["reset"] if "err" in r][:3])))
