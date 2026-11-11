#!/usr/bin/env python3
"""DIE-KV-97 11-11 phyrev_1111: kv3_phy / kv3_phy_v1 PHY output-bus station order (blocker fix, COORD fail_watch 02:0x).

kv3_phy 481ef93659a1 a11 routed TT -238.78 / 904 endpoints: zero-logic hop u_ist_o_phy_Q__sN_piN_d3_2 (331, 963) ->
u_bout_o_phy_Q__sN_piN_d3 face flop (857, 619), ~870 um Manhattan.  Cause: the KV-TYPES-5 11-08 PHY RE-FORM wrote the six
o_phy_Q__sN_* internal_stations face -> core (from_um = east face, regs_um[0] next to the face), while data flows core ->
face (launch u_core.pi*, capture face flop) and kit_istations puts station k (k-th register after the launch) at
regs_um[k].  So station 0 landed next to the face and station 2 next to the core: the chain zig-zags core -> face ->
mid -> core -> face, first and last hops ~600-870 um instead of the planned <= 317 um.
Fix: for every bus station entry whose capture is the face and whose from_um is on the outline edge (launch is a core
pin), swap from_um / to_um and reverse regs_um.  Same stations, same sites, same cycles: EQ by construction; the
realised hops become core -> 24 um -> ... -> face as the re-form note intended.

usage (repo root): event.py PLAN_IN PLAN_OUT
"""
import copy, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))
TYPES = ("kv3_phy", "kv3_phy_v1")


def onedge(xy, o):
    return min(xy[0], xy[1], o[0] - xy[0], o[1] - xy[1]) < 1.0


def reversed_entries(t):
    o = t["outline_um"]
    for e in t.get("internal_stations") or []:
        if not e.get("regs_um") or not str(e.get("conn", "")).startswith("bus:"):
            continue
        L, C = str(e.get("launch", "")), str(e.get("capture", ""))
        if "face" in C and "face" not in L and onedge(e["from_um"], o) and not onedge(e["to_um"], o):
            yield e


def apply(text, types=TYPES):
    plan = json.loads(text); orig = copy.deepcopy(plan); done = []
    for tn in types:
        t = plan["partition_types"][tn]
        for e in list(reversed_entries(t)):
            e["from_um"], e["to_um"] = e["to_um"], e["from_um"]
            e["regs_um"] = list(reversed(e["regs_um"]))
            done.append((tn, e["conn"]))
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k]
    for tn, t in plan["partition_types"].items():
        if tn not in types:
            assert t == orig["partition_types"][tn]
        else:
            a = {k: v for k, v in t.items() if k != "internal_stations"}
            assert a == {k: v for k, v in orig["partition_types"][tn].items() if k != "internal_stations"}
            assert len(t["internal_stations"]) == len(orig["partition_types"][tn]["internal_stations"])
            for e, f in zip(t["internal_stations"], orig["partition_types"][tn]["internal_stations"]):
                assert sorted(map(tuple, e.get("regs_um") or [])) == sorted(map(tuple, f.get("regs_um") or []))
    out = text
    for tn in types:
        if not any(d[0] == tn for d in done):
            continue
        m = re.search(r'^(\s*)"' + re.escape(tn) + r'": ', out, re.M)
        _, j = json.JSONDecoder().raw_decode(out, m.end())
        out = out[:m.end()] + json.dumps(plan["partition_types"][tn], indent=1).replace("\n", "\n" + m.group(1)) + out[j:]
    assert json.loads(out) == plan
    return out, done


def main(a):
    out, done = apply(open(a[0]).read())
    import schema as S
    S.Plan(json.loads(out), Path(a[0]).resolve())
    open(a[1], "w").write(out)
    print("phyrev_1111:", len(done), "entries", done)


if __name__ == "__main__":
    main(sys.argv[1:])
