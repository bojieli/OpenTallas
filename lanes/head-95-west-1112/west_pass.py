#!/usr/bin/env python3
"""HEAD-95 west growth: ONE translation pass (COORD 11-12 rulings 1a-1d).

west_pass.py BASE MOVED OUT [--fork-nst1]
  BASE  = k1 plan (pre-move), MOVED = srx3 plan (+ reach_fix) with die moves and the street-rule hd_lep0N type.
  (a) every port of a MOVED partition to a FIXED partition on an abutting face keeps the DIE x of its windows:
      ft_slot in/out windows, bus windows, landing pins, bands, reader/writer start stages, edge-clock taps,
      collector sources/children of that bus are translated by -dx_die (local +198.72 for a west move).
      A SHARED type whose other instances did not move cannot do that: with --fork-nst1 the moved instance gets its
      own type <type>_nw (module <module>_nw) carrying the translated windows; the shared type is restored to BASE.
  (b) faces to moved neighbours keep local windows (untouched).
  (c) taps / resets: NOT done here; reach_fix.py fix runs on the output (REACH-FIX tool, role-matched reset_resel).
Prints every translated item; exits 2 on any face it cannot resolve.
"""
import copy, json, sys

COORD_KEYS = ("xy_um", "rect_um", "tap_um")


def load(p):
    return json.load(open(p))


def face_of(outline, xy, tol=6.0):
    w, h = outline
    x, y = xy
    if abs(y - h) <= tol: return "N"
    if abs(y) <= tol: return "S"
    if abs(x) <= tol: return "W"
    if abs(x - w) <= tol: return "E"
    return None


def shift_xy(v, dx):
    if isinstance(v, list) and len(v) == 2 and all(isinstance(a, (int, float)) for a in v):
        return [round(v[0] + dx, 4), v[1]]
    if isinstance(v, list) and len(v) == 4 and all(isinstance(a, (int, float)) for a in v):
        return [round(v[0] + dx, 4), v[1], round(v[2] + dx, 4), v[3]]
    return v


def owned(d, buses):
    for k in ("name", "bus", "port"):
        s = d.get(k)
        if isinstance(s, str) and (s in buses or any(s.endswith("_" + b) for b in buses)):
            return True
    return False


ALLBUS = set()


def walk(o, buses, dx, path, log, inside=False):
    if isinstance(o, dict):
        mine = inside or owned(o, buses)
        for k in list(o):
            v = o[k]
            if k in COORD_KEYS and mine:
                nv = shift_xy(v, dx)
                if nv != v:
                    o[k] = nv
                    log.append(f"{path}/{k} {v} -> {nv}")
            elif isinstance(v, (dict, list)):
                # the innermost bus key decides ownership (status stages d_o/d_i belong to d_i, not d_o)
                sub = True if k in buses else (False if k in ALLBUS else mine)
                walk(v, buses, dx, f"{path}/{k}", log, sub)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, buses, dx, f"{path}[{i}]", log, inside)


def translate_type(t, buses, face, dx, log, tn, skip_bus_windows=False):
    ALLBUS.clear()
    ALLBUS.update(b["name"] for b in t.get("buses") or [])
    for s in t.get("ft_slots") or []:
        ALLBUS.update((s["name"] + "_i", s["name"] + "_o"))
    for s in t.get("ft_slots") or []:
        for side in ("in", "out"):
            port = f"{s['name']}_{'i' if side == 'in' else 'o'}"
            if s.get(f"{side}_face") == face and port in buses:
                k = f"{side}_window_um"
                old = s[k]; s[k] = [round(old[0] + dx, 4), round(old[1] + dx, 4)]
                log.append(f"{tn}/ft_slots/{s['name']}/{k} {old} -> {s[k]}")
    if not skip_bus_windows:
        for b in t.get("buses") or []:
            if b["name"] in buses and b.get("face") == face:
                old = b["window_um"]; b["window_um"] = [round(old[0] + dx, 4), round(old[1] + dx, 4)]
                log.append(f"{tn}/buses/{b['name']}/window_um {old} -> {b['window_um']}")
    walk(t.get("clock", {}), buses, dx, f"{tn}/clock", log)


def main():
    base, moved, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    fork = "--fork-nst1" in sys.argv
    P = copy.deepcopy(moved)
    bparts = {p["name"]: p for p in base["partitions"]}
    parts = {p["name"]: p for p in P["partitions"]}
    movedp = {n for n, p in parts.items() if p["origin_um"] != bparts[n]["origin_um"]}
    insts = {}
    for p in P["partitions"]:
        insts.setdefault(p["type"], []).append(p["name"])
    log, errors = [], []
    # (a) ports between a moved and a fixed partition
    need = {}  # (part, bus) -> (face, dx)
    for po in P["ports"]:
        s, d = po["src"]["part"], po["dst"]["part"]
        for me, other, end in ((s, d, po["src"]), (d, s, po["dst"])):
            if me in movedp and other not in movedp:
                bus = end.get("bus")
                dx = -(parts[me]["origin_um"][0] - bparts[me]["origin_um"][0])
                if parts[me].get("orient", "R0") != "R0":
                    errors.append(f"{me}: orient {parts[me].get('orient')} not handled"); continue
                t = P["partition_types"][parts[me]["type"]]
                face = None
                for b in t.get("buses") or []:
                    if b["name"] == bus: face = b.get("face")
                for sl in t.get("ft_slots") or []:
                    if f"{sl['name']}_i" == bus: face = sl["in_face"]
                    if f"{sl['name']}_o" == bus: face = sl["out_face"]
                if face in ("E", "W"):
                    log.append(f"SKIP {me}.{bus} face {face}: y-window, die y unchanged"); continue
                need[(me, bus)] = (face, dx)
    bytype = {}
    for (me, bus), (face, dx) in need.items():
        bytype.setdefault(parts[me]["type"], {}).setdefault((face, dx), {"parts": set(), "buses": set()})
        bytype[parts[me]["type"]][(face, dx)]["parts"].add(me)
        bytype[parts[me]["type"]][(face, dx)]["buses"].add(bus)
    for tn, groups in sorted(bytype.items()):
        for (face, dx), g in groups.items():
            others = [n for n in insts[tn] if n not in g["parts"]]
            if others:
                if not fork:
                    errors.append(f"{tn}: SHARED with unmoved {others}; {sorted(g['parts'])} needs {face} windows +{dx} (use --fork-nst1)")
                    continue
                new = tn + "_nw"
                T = copy.deepcopy(base["partition_types"][tn])
                T["module"] = T["module"] + "_nw"
                P["partition_types"][tn] = copy.deepcopy(base["partition_types"][tn])
                P["partition_types"][new] = T
                for n in g["parts"]: parts[n]["type"] = new
                for sect, key in (("reset", "in_sites"),):
                    if tn in P[sect].get(key, {}): P[sect][key][new] = copy.deepcopy(P[sect][key][tn])
                tw = P["clock"].get("tap_window", {}).get("per_type_ps", {})
                if tn in tw: tw[new] = tw[tn]
                rh = P["clock"].get("ring_hold", {}).get("write_fall_types")
                if rh is not None and tn in rh: rh.append(new)
                log.append(f"FORK {tn} -> {new} for {sorted(g['parts'])} (shared with {others}); {tn} restored to base")
                tn2 = new
            else:
                tn2 = tn
            T = P["partition_types"][tn2]
            skip = tn2 == "hd_lep0N"  # srx3 already moved its N bus windows; pins/bands/collector not
            if skip:
                bb = {b["name"]: b["window_um"] for b in base["partition_types"][tn]["buses"]}
                for b in T["buses"]:
                    if b["name"] in g["buses"] and abs(b["window_um"][0] - bb[b["name"]][0] - dx) > 0.01:
                        errors.append(f"{tn2}.{b['name']} window {b['window_um']} is not base+{dx}")
            translate_type(T, g["buses"], face, dx, log, tn2, skip_bus_windows=skip)
    for l0 in log:
        if "->" in l0 and "_um" in l0:
            tn0 = l0.split("/")[0]
            w, h = P["partition_types"][tn0]["outline_um"] if tn0 in P["partition_types"] else (1e9, 1e9)
            nv = json.loads(l0.split("->")[1])
            if max(nv[0::2] if len(nv) == 4 else nv[:1]) > w + 0.01:
                errors.append(f"OUTSIDE outline {w}: {l0}")
    json.dump(P, open(out, "w"), indent=1)
    side_in = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--sidecar=")), None)
    if side_in:
        S = load(side_in)
        for l0 in list(log):
            if not l0.startswith("FORK "): continue
            tn, new = l0.split()[1], l0.split()[3]
            col = S["collector"]
            ct = copy.deepcopy(col["types"][tn]); ct["base_type"] = new
            g = [gg for gg in bytype[tn].values()][0]
            face, dx = [k for k in bytype[tn]][0]
            for src in ct.get("local_sources", []):
                if src["name"] in g["buses"]:
                    src["xy_um"] = shift_xy(src["xy_um"], dx)
                    if "band" in src: src["band"]["rect_um"] = shift_xy(src["band"]["rect_um"], dx)
                    log.append(f"sidecar/collector/types/{new}/local_sources/{src['name']} +{dx}")
            col["types"][new] = ct
            for n in g["parts"]:
                col["parts"][n]["type"] = new
                if n in col.get("base_type_by_part", {}): col["base_type_by_part"][n] = new
            tp = S.get("count_aligned", {}).get("start_pins", {}).get("type_pins", {})
            if tn in tp: tp[new] = copy.deepcopy(tp[tn])
            log.append(f"sidecar fork {tn} -> {new}")
        json.dump(S, open(out.replace(".json", "_sidecar.json"), "w"), indent=1)
    for l in log: print(l)
    for e in errors: print("ERROR", e)
    print(f"west_pass: moved {sorted(movedp)}; fixed-face ports {len(need)}; items {len(log)}; errors {len(errors)}")
    sys.exit(2 if errors else 0)


if __name__ == "__main__":
    main()
