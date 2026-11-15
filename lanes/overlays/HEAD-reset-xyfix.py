"""HEAD-99: reset_start_raw_exports row xy_um -> actual registered raw relay xy of the rebuilt reset tree (landing_contract.py:141 check).
Only rows whose instance exists in the tree with q == net and whose xy differs are changed (instance/net untouched).
usage: xyfix.py SOURCE_PLAN.json   (in place via tmp+rename; run after landing_remap, before republish)"""
import json, sys, os, pathlib
sys.path.insert(0, "/srv/opentallas-scratch2/claude/kw45/src_head_rp21z20/tools/die_plan")
import schema as S, reset_tree as RT
path = pathlib.Path(sys.argv[1]); raw = json.load(open(path))
P = S.Plan(S.load(str(path)), path); n = 0; bad = []
for tn, t in raw["partition_types"].items():
    rows = t.get("reset_start_raw_exports") or []
    if not rows: continue
    tree = RT.for_type(P, tn); relays = RT.start_relays(tree) if tree.get("start") else tree["relays"]
    src = {r["name"]: r for r in relays if not tree.get("start") or r.get("role") in ("raw", "boot", "bootstrap_transport")}
    for r in rows:
        if r.get("existing_port"): continue
        s = src.get(r["instance"])
        if s is None or s.get("q") != r["net"]: bad.append((tn, r["port"], r["instance"])); continue
        if any(abs(a - b) > 1e-6 for a, b in zip(s["xy"], r["xy_um"])):
            r["xy_um"] = [float(s["xy"][0]), float(s["xy"][1])]; n += 1   # exact: the check compares to 1e-6
# landing pins follow their export row (instance, net): the pin-source check (landing_contract.py:145-151) only runs after xy passes
npin = 0
for tn, t in raw["partition_types"].items():
    rows = {r["port"]: r for r in (t.get("reset_start_raw_exports") or []) if not r.get("existing_port")}
    for pin in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or []:
        r = rows.get(pin.get("name"))
        if r is None or not pin.get("source_registered"): continue
        want = dict(source_instance=r["instance"])
        if t.get("private_reset_start_exports"): want.update(source_net=pin["name"], source_copy_from_net=r["net"])
        else: want.update(source_net=r["net"])
        if any(pin.get(k) != v for k, v in want.items()): pin.update(want); npin += 1
print("pins re-pointed", npin)
json.dump(raw, open(str(path) + ".xyfix", "w"), indent=1); os.replace(str(path) + ".xyfix", path)
print("xyfix rows updated", n, "unresolvable", bad)
