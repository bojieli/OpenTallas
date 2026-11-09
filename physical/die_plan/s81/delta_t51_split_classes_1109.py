#!/usr/bin/env python3
"""S81 plan event T51-SPLIT-CLASSES-1109 (DIE-S81-85, on top of T51-SPLIT-1109): slice_station__t51 takes the class
forms its native split needs (tools/die_plan class fixes of the same commit):

  1 clock.child_root_taps {parent_ffs: 0}: the parent holds no register (native_conservation_controls: parent 0 FF), so
    each of the 73 explicit type taps clk, clk_t1 .. clk_t72 is re-sited ONTO the child clock root pin(s) of the same
    port (tap.lands_on, xy = the first landing = the die M9/M8 drop; clk_t2 / clk_t19 / clk_t62 feed both children and
    reach the second landing by a parent wire).  The 89 early core taps of T51-SPLIT-1109 go: 76 of them are these
    landings, the other 13 are forwarded-clock child roots (fclk_in_*: source-synchronous clocks that enter with their
    data through the type's fclk_in ports, never die-clock taps), listed in child_root_taps.forwarded_roots.
    Insertion on a landed tap = its child's: E signed core_latency mean, W the plan bound (view pending); a tap landing
    on both children takes the larger.
  2 ft_slots[].stations_in: every slot names the children that hold its station registers (the children whose box
    holds any of its plan station cells: the exact full-stage packet where the slot has one, else regs_um / bit sites;
    a slot with no station inside a child names both children: the parent has no register).
The plan text is edited in place, asserted json-equal to the object edit.
    python3 delta_t51_split_classes_1109.py PLAN REPORT        (cwd = repo root)
"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
from delta_romq_split_1106 import render_like, spans  # noqa: E402

TN = "slice_station__t51"
EV = "T51-SPLIT-CLASSES-1109 DIE-S81-85"
RULE = ("DIE-S81-85 11-09 native split class 1: parent 0 FF (station_split_1106/native_conservation_controls.json "
        "parent_FFs none); the die clock drops onto the child clock roots")


def main():
    plan_p, rep_p = map(Path, sys.argv[1:3])
    text = plan_p.read_text()
    P = json.loads(text)
    t = P["partition_types"][TN]
    ck = t["clock"]
    assert ck["tap_mode"] == "explicit" and "child_root_taps" not in ck
    hcs = {h["inst"]: h for h in t["hard_cores"]}
    assert len(hcs) == 2
    explicit = [x for x in ck["taps"] if x.get("kind") != "core"]
    core = [x for x in ck["taps"] if x.get("kind") == "core"]
    assert len(explicit) == 73 and len(core) == 89 and ck["taps"] == explicit + core
    roots = {}
    for x in core:
        inst, _, port = x["name"].rpartition(".")
        roots.setdefault(port, []).append((inst, x))
    fwd = sorted(p for p in roots if not re.fullmatch(r"clk(_t\d+)?", p))
    assert len(fwd) == 13 and all(p.startswith("fclk_in_") for p in fwd)
    radius = float(ck.get("tap_radius_um", 200.0))
    new_taps, rep_taps = [], []
    for x in explicit:
        rows = roots[x["name"]]
        # the die drop lands on the child root nearest the old tap site (its source position); others by parent wire
        rows = sorted(rows, key=lambda r: abs(r[1]["xy"][0] - x["xy"][0]) + abs(r[1]["xy"][1] - x["xy"][1]))
        lands = [dict(pin=r[1]["name"], xy=list(r[1]["xy"])) for r in rows]
        far = max(abs(a["xy"][0] - lands[0]["xy"][0]) + abs(a["xy"][1] - lands[0]["xy"][1]) for a in lands)
        assert far <= radius, (x["name"], far)
        tt = max(r[1]["insertion_ps"] for r in rows)
        ff = max(r[1]["insertion_ff_ps"] for r in rows)
        e = dict(name=x["name"], xy=list(lands[0]["xy"]), lands_on=lands, insertion_ps=tt, insertion_ff_ps=ff,
                 budget_owner=f"{EV}: landed child insertion ({'; '.join(sorted({r[1]['budget_owner'] for r in rows}))})",
                 note=f"{EV}: child-root tap, was explicit site {x['xy']}; lands on {', '.join(a['pin'] for a in lands)}")
        new_taps.append(e)
        rep_taps.append(dict(tap=x["name"], old_xy=x["xy"], new_xy=e["xy"], landings=len(lands), far_um=round(far, 3)))
    # stations_in per slot
    boxes = {}
    for inst, h in hcs.items():
        (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
        dx, dy = h["track_offset_um"]
        boxes[inst] = (ox + dx, oy + dy, ox + dx + w, oy + dy + hh)
    slot_in, rep_slots = {}, []
    import schema as S
    from ft_full_stage import load as full_load
    full = full_load(S.Plan(P, str(plan_p)), TN)     # exact full-stage station cells (check.py geometry reads these)
    for s in t["ft_slots"]:
        if s["name"] in full:
            pts = [(r["xy"][0] + r["size"][0] / 2, r["xy"][1] + r["size"][1] / 2) for r in full[s["name"]].values()]
        else:
            pts = [tuple(r) for r in s.get("regs_um") or []] + [tuple(q) for st in s.get("bit_sites_um") or [] for q in st]
        inside = sorted(i for i, (a, b, c, d) in boxes.items() if any(a < px < c and b < py < d for px, py in pts))
        own = inside or sorted(boxes)
        slot_in[s["name"]] = own
        rep_slots.append(dict(slot=s["name"], stations_in=[i.rsplit("_", 1)[1] for i in own], sites=len(pts),
                              basis="sites inside" if inside else "no site inside a child: both (parent 0 FF)"))
    sp = spans(text)
    edits = []
    # taps: replace the whole list
    a, b = sp[("partition_types", TN, "clock", "taps")]
    a0, b0 = sp[("partition_types", TN, "clock", "taps", 0)]
    line0 = text.rfind("\n", 0, a0) + 1
    ind = text[line0:a0]
    edits.append((a, b, "[\n" + ind + render_like(text[a0:b0], new_taps, ind) + "\n" + ind[:-1] + "]"))
    # child_root_taps after taps
    edits.append((b, b, ",\n" + ind[:-1] + '"child_root_taps": ' + json.dumps(
        dict(parent_ffs=0, rule=RULE, forwarded_roots=fwd), indent=1).replace("\n", "\n" + ind[:-1])))
    for j, s in enumerate(t["ft_slots"]):
        a, b = sp[("partition_types", TN, "ft_slots", j, "name")]
        line0 = text.rfind("\n", 0, a) + 1
        pre = text[line0:a]
        # "name": "ft0" -> insert after the name value
        edits.append((b, b, ",\n" + re.match(r" *", pre).group(0) + '"stations_in": ' + json.dumps(slot_in[s["name"]])))
    out = text
    for a, b, s_ in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        out = out[:a] + s_ + out[b:]
    Q = json.loads(out)
    want = copy.deepcopy(P)
    wt = want["partition_types"][TN]
    wt["clock"]["taps"] = new_taps
    wt["clock"]["child_root_taps"] = dict(parent_ffs=0, rule=RULE, forwarded_roots=fwd)
    for s in wt["ft_slots"]:
        s["stations_in"] = slot_in[s["name"]]
    assert Q == want, "text edit != object edit"
    plan_p.write_text(out)
    rep = dict(event=EV, type=TN, taps=rep_taps, forwarded_roots=fwd, dropped_core_taps=len(core), slots=rep_slots,
               plan_sha256_before=hashlib.sha256(text.encode()).hexdigest(),
               plan_sha256_after=hashlib.sha256(out.encode()).hexdigest())
    rep_p.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(taps=len(new_taps), shared=sum(1 for r in rep_taps if r["landings"] > 1),
                          before=rep["plan_sha256_before"][:16], after=rep["plan_sha256_after"][:16])))


if __name__ == "__main__":
    main()
