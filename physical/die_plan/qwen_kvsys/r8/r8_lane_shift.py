#!/usr/bin/env python3
"""KV-KITS-5 10-27: carry a plan lane-latency delta into the KV R8 landing table (no full regen).

The kvbind1025 R8 table (position-bank pipeline, 10-25) is not reproducible by `r8.py pads` on a raw bind's bus groups,
so a plan delta that changes lane cycles (hm_r12 io_cor +1 station on L356/L749/L750/L2047/L2048, COORD 04:26) is
carried member by member: bound += the lane's cycle change (gen.latency_table old plan -> new plan).  R8 then needs
every class (landing group = sink leaf + source partition + source leaf, joined by type replica sets: r8.classes on the
NEW bind's bus groups, --bus leaf --replica type as the table records) to keep its relative landing: the class shifts
by shift = max(0, max(bound' - landed)) and each member's pad = landed + shift - bound' (>= 0).  A member whose pad
absorbs the extra cycle keeps its landed depth; a pad-0 member on a +1 lane lands +1 and drags its class with it.
    r8_lane_shift.py OLD_PLAN NEW_PLAN TABLE BUS_GROUPS(new bind) OUT [--extra TABLE ...]
The same shift is applied to the land_r8_extra tables (authoritative for their ids); a changed extra is written next
to OUT as <name>.  Stats on stdout + OUT['lane_shift']."""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools/die_plan"))
import gen, r8, schema as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("old_plan"); ap.add_argument("new_plan"); ap.add_argument("table"); ap.add_argument("bus_groups")
ap.add_argument("out"); ap.add_argument("--extra", action="append", default=[])
a = ap.parse_args()
old = gen.latency_table(S.Plan(S.load(a.old_plan)))
newraw = S.load(a.new_plan)
new = gen.latency_table(S.Plan(newraw))
delta = {ln: new[ln]["cycles"] - old[ln]["cycles"] for ln in new if ln in old and new[ln]["cycles"] != old[ln]["cycles"]}
gone = sorted(set(old) ^ set(new))
assert not gone, f"lane sets differ: {gone[:10]}"
bg = json.loads(Path(a.bus_groups).read_text())
r8.configure()
N, uf, _ = r8.classes(bg, newraw, "type", "leaf")
cls = {r8.mkey(g, m): uf.find(i) for i, (_, g, m) in enumerate(N)}
tabs = [(Path(a.table), json.loads(Path(a.table).read_text()))] + [(Path(x), json.loads(Path(x).read_text())) for x in a.extra]
# effective members (extras authoritative for their ids, as bind.align_r8)
eff = {m["id"]: (0, m) for m in tabs[0][1]["members"]}
for k, (_, js) in enumerate(tabs[1:], 1):
    for m in js["members"]:
        if not m["id"].startswith("INNER:"):
            eff[m["id"]] = (k, m)
moved = {i: delta[m["lane"]] for i, (_, m) in eff.items() if m.get("lane") in delta}
key = {i: cls.get(i, ("solo", i)) for i in eff}
touched = {key[i] for i in moved}
shift = defaultdict(int)
for i, (_, m) in eff.items():
    if key[i] in touched:
        shift[key[i]] = max(shift[key[i]], m["bound"] + moved.get(i, 0) - m["landed"])
st = dict(lane_delta=delta, moved_members=len(moved), class_members=0, changed=[])
for i, (k, m) in eff.items():
    if key[i] not in touched:
        continue
    st["class_members"] += 1
    b2 = m["bound"] + moved.get(i, 0)
    l2 = m["landed"] + max(0, shift[key[i]])
    p2 = l2 - b2
    assert p2 >= 0, (i, m, b2, l2)
    if (b2, p2, l2) != (m["bound"], m["pad"], m["landed"]):
        st["changed"].append(dict(id=i, table=tabs[k][0].name, lane=m.get("lane"), bound=[m["bound"], b2],
                                  pad=[m["pad"], p2], landed=[m["landed"], l2]))
        m.update(bound=b2, pad=p2, landed=l2)
outp = Path(a.out)
for k, (p, js) in enumerate(tabs):
    if k and not any(c["table"] == p.name for c in st["changed"]):
        continue
    js["lane_shift"] = dict(tool="physical/die_plan/qwen_kvsys/r8/r8_lane_shift.py", **{kk: v for kk, v in st.items() if kk != "changed"},
                            changed=[c for c in st["changed"] if c["table"] == p.name])
    dst = outp if k == 0 else outp.parent / p.name
    dst.write_text(json.dumps(js, indent=0) + "\n")
print(json.dumps(st, indent=1))
