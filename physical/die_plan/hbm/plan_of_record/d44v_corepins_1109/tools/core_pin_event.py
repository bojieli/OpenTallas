"""DIE-HBM-97 11-09: type-local core pin-table event on the final HBM plan.

usage: python3 -I core_pin_event.py PLAN_DIR OUT_DIR EVENT_JSON_OUT spec.json
spec: [{"module": m, "kit_pins": path, "old_table": "cores/...", "new_table": "cores/...", "outline_um": [w, h], "form": s}]
Kit pins (bus/bit/face/layer/x/y[/w/h/entry]) -> plan core table (name/layer/x/y[/w/h]): face pins inset 0.096 um
toward the interior (W x+, E x-, S y+, N y-), entry pins unchanged; checked against every unchanged pin of the old table.
Only hard_cores with exactly that module are re-pointed; other modules sharing the old table keep it.
"""
import hashlib, json, os, shutil, sys

INSET = 0.096
SHIFT = {"W": (INSET, 0.0), "E": (-INSET, 0.0), "S": (0.0, INSET), "N": (0.0, -INSET)}


def kname(x):
    return x["bus"] if x.get("bit") is None else f"{x['bus']}[{x['bit']}]"


def to_plan(k):
    dx, dy = (0.0, 0.0) if k.get("entry") or k.get("face") not in SHIFT else SHIFT[k["face"]]
    out = dict(name=kname(k), layer=k["layer"], x=round(k["x"] + dx, 3), y=round(k["y"] + dy, 3))
    for a in ("w", "h"):
        if a in k:
            out[a] = k[a]
    return out


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(plan_dir, out_dir, ev_out, spec_path):
    spec = json.load(open(spec_path))
    if os.path.exists(out_dir):
        sys.exit(f"{out_dir} exists")
    shutil.copytree(plan_dir, out_dir, symlinks=True)
    pf = os.path.join(out_dir, "die_plan.json")
    base_sha = sha(pf)
    plan = json.load(open(pf))
    ev = dict(schema="opentallas.plan_core_pin_table_event.v1", event="corepins_1109", by="DIE-HBM-97",
              ruling="COORD 11-09 04:4x to DIE-HBM-97: adopt HBM-CORES-B pin tables for rootg1c_vC5 and own_vRF4T as "
                     "type-local events on the final HBM plan (replaces the WAIT default)",
              base_plan=plan_dir, base_plan_sha256=base_sha, changes=[])
    for s in spec:
        old = json.load(open(os.path.join(plan_dir, s["old_table"])))
        kit = json.load(open(s["kit_pins"]))
        new = {p["name"]: p for p in map(to_plan, kit)}
        if set(new) != {p["name"] for p in old} or len(new) != len(kit):
            sys.exit(f"{s['module']}: pin names differ from {s['old_table']}")
        tab = [new[p["name"]] for p in old]                               # plan table order kept
        same = [p for p in old if new[p["name"]] == p]
        moved = [p["name"] for p in old if new[p["name"]] != p]
        layer_change = [p["name"] for p in old if new[p["name"]]["layer"] != p["layer"]]
        W, H = s["outline_um"]
        out = [p["name"] for p in tab if not (-1e-6 <= p["x"] <= W + 1e-6 and -1e-6 <= p["y"] <= H + 1e-6)]
        if out or layer_change:
            sys.exit(f"{s['module']}: outside outline {out[:3]} / layer change {layer_change[:3]}")
        sites = {(p["layer"], p["x"], p["y"]) for p in tab}
        if len(sites) != len(tab):
            sys.exit(f"{s['module']}: duplicate pin sites")
        nt = os.path.join(out_dir, s["new_table"])
        if os.path.exists(nt):
            sys.exit(f"{nt} exists")
        with open(nt, "w") as f:
            json.dump(tab, f, indent=1)
        hosts, n = {}, 0
        for tname, t in plan["partition_types"].items():
            for hc in t.get("hard_cores", []):
                if hc.get("module") == s["module"]:
                    if hc.get("pins_file") != s["old_table"]:
                        sys.exit(f"{tname}/{hc['inst']}: pins_file {hc.get('pins_file')} != {s['old_table']}")
                    if [round(v, 3) for v in hc["outline_um"]] != [W, H]:
                        sys.exit(f"{tname}/{hc['inst']}: outline {hc['outline_um']}")
                    hc["pins_file"] = s["new_table"]
                    hosts.setdefault(tname, []).append(hc["inst"])
                    n += 1
        if not n:
            sys.exit(f"{s['module']}: no hard_cores")
        ev["changes"].append(dict(module=s["module"], form=s["form"], kit_pins=s["kit_pins"],
                                  kit_pins_sha256=sha(s["kit_pins"]), old_table=s["old_table"],
                                  new_table=s["new_table"], new_table_sha256=sha(nt), pins=len(tab),
                                  pins_moved=len(moved), pins_unchanged=len(same), moved_first=moved[:5],
                                  layer_changes=0, outline_um=[W, H], instances=n, host_types=hosts,
                                  pin_cycles=0, macros_outline_clock="unchanged"))
    plan["note"] = ("DIE-HBM-97 corepins_1109 (" + ", ".join(f"{c['module']} -> {c['new_table']}" for c in ev["changes"])
                    + ") <- " + plan.get("note", ""))
    os.remove(pf)                                    # new inode: never write through to the copied source
    with open(pf, "w") as f:
        f.write(json.dumps(plan, indent=1) + "\n")
    ev["die_plan_sha256"] = sha(pf)
    ev["host_types"] = sorted({h for c in ev["changes"] for h in c["host_types"]})
    with open(ev_out, "w") as f:
        json.dump(ev, f, indent=1)
    with open(os.path.join(out_dir, "corepins_1109_event.json"), "w") as f:
        json.dump(ev, f, indent=1)
    print(json.dumps({k: v for k, v in ev.items() if k != "changes"}))
    for c in ev["changes"]:
        print(c["module"], c["pins"], "moved", c["pins_moved"], "inst", c["instances"], c["host_types"].keys())


if __name__ == "__main__":
    main(*sys.argv[1:5])
