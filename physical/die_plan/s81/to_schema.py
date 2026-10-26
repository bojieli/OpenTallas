#!/usr/bin/env python3
"""PLAN-S81: turn gen_plan.py's plan_internal.json into die_plan.json (schema opentallas.die_plan.v1).

* Port windows are allocated per shared face in a deterministic order (width, direction, class) and sized for
  width + 1 pins (the in-band epoch bit) at PINS_PER_UM.  The allocation runs in the TYPE frame of the lower-named
  partition, so replicas of one type get the same pin table.
* Types are exact: base master + ft slots + functional buses + every window in the type frame.  Bus and slot names
  are canonical inside a type (class_dir_k, s_k), so all replicas bind identically.
Usage: to_schema.py PLAN_DIR [--pins-per-um 5.5]
"""
import argparse
import collections
import json
from pathlib import Path

G = 8.64
OPP = dict(N="S", S="N", E="W", W="E")
FLIP = {"R0": {}, "MY": dict(E="W", W="E"), "MX": dict(N="S", S="N"), "R180": dict(E="W", W="E", N="S", S="N")}
H_LAYERS, V_LAYERS = ["M6", "M4"], ["M7", "M5"]
EDGE = 6.0


def tf(o, f):
    return FLIP[o].get(f, f)


def rel(p, face, lo, hi):
    """die window -> type-frame window along the face."""
    if face in "EW":
        a, b, flip = lo - p["y0"], hi - p["y0"], p["orient"] in ("MX", "R180")
        L = p["h"]
    else:
        a, b, flip = lo - p["x0"], hi - p["x0"], p["orient"] in ("MY", "R180")
        L = p["w"]
    if flip:
        a, b = L - b, L - a
    return (round(a, 3), round(b, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir")
    ap.add_argument("--pins-per-um", type=float, default=5.0)
    ap.add_argument("--reach", type=float, default=1500.0)
    a = ap.parse_args()
    d = Path(a.plan_dir)
    pl = json.load(open(d / "plan_internal.json"))
    P = {p["name"]: p for p in pl["parts"]}
    lane_of = {}
    lane_cls = {l["id"]: l["cls"] for l in pl["lanes"]}
    ports = pl["ports"]
    for pt in ports:
        lane_of[pt["id"]] = pt["lane"]
    # adjacency face of a toward b
    def face(a_, b_):
        A, B = P[a_], P[b_]
        if abs(A["x0"] + A["w"] - B["x0"]) < 1e-3:
            return "E", max(A["y0"], B["y0"]), min(A["y0"] + A["h"], B["y0"] + B["h"])
        if abs(B["x0"] + B["w"] - A["x0"]) < 1e-3:
            return "W", max(A["y0"], B["y0"]), min(A["y0"] + A["h"], B["y0"] + B["h"])
        if abs(A["y0"] + A["h"] - B["y0"]) < 1e-3:
            return "N", max(A["x0"], B["x0"]), min(A["x0"] + A["w"], B["x0"] + B["w"])
        return "S", max(A["x0"], B["x0"]), min(A["x0"] + A["w"], B["x0"] + B["w"])

    # ---- windows
    byface = collections.defaultdict(list)
    for pt in ports:
        byface[tuple(sorted((pt["a"], pt["b"])))].append(pt)
    win, over = {}, []
    for (k0, k1), lst in byface.items():
        f, lo, hi = face(k0, k1)
        A = P[k0]
        flip = (A["orient"] in ("MX", "R180")) if f in "EW" else (A["orient"] in ("MY", "R180"))
        lst.sort(key=lambda pt: (-pt["width"], pt["a"] != k0, lane_cls[pt["lane"]], pt["id"]))
        need = sum((pt["width"] + 1) / a.pins_per_um + 2.0 for pt in lst)
        avail = hi - lo - 2 * EDGE
        scale = min(1.0, avail / need) if need > 0 else 1.0
        if scale < 1.0:
            over.append(dict(a=k0, b=k1, face=f, bits=sum(pt["width"] + 1 for pt in lst), len=round(hi - lo, 2),
                             pins_per_um=round(sum(pt["width"] + 1 for pt in lst) / avail, 2)))
        pos = (hi - EDGE) if flip else (lo + EDGE)
        for pt in lst:
            L = (pt["width"] + 1) / a.pins_per_um * scale
            gap = 2.0 * scale
            if flip:
                w0, w1, pos = pos - L, pos, pos - L - gap
            else:
                w0, w1, pos = pos, pos + L, pos + L + gap
            win[pt["id"]] = (round(w0, 4), round(w1, 4), f if pt["a"] == k0 else OPP[f], k0, k1)
    # ---- stations per crossing from the real in/out port points (tools/die_plan/check.py lane_geometry)
    def pt_xy(pid):
        w0, w1, fsrc, k0, k1 = win[pid]
        pt = next(x for x in ports if x["id"] == pid) if False else None
        A = P[port_src[pid]]
        m = (w0 + w1) / 2
        if fsrc == "E":
            return (A["x0"] + A["w"], m)
        if fsrc == "W":
            return (A["x0"], m)
        if fsrc == "N":
            return (m, A["y0"] + A["h"])
        return (m, A["y0"])
    port_src = {pt["id"]: pt["a"] for pt in ports}
    st_of = {}
    for l in pl["lanes"]:
        pids = l["ports"]
        for i in range(len(pids) - 1):
            a_, b_ = pt_xy(pids[i]), pt_xy(pids[i + 1])
            L = abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
            st_of[(l["id"], i)] = max(1, -(-int(L * 1.0001) // int(a.reach)))
    # ---- per-instance interface signature (type frame)
    inst_buses = collections.defaultdict(list)   # part -> list of (sigtuple, kind, portid, role)
    for pt in ports:
        w0, w1, fsrc, _, _ = win[pt["id"]]
        for role, part, fc in (("src", pt["a"], fsrc), ("dst", pt["b"], OPP[fsrc])):
            p = P[part]
            r = rel(p, fc, w0, w1)
            inst_buses[part].append(dict(role=role, face=tf(p["orient"], fc), win=r, width=pt["width"],
                                         kind=pt["kind"], port=pt["id"], lane=pt["lane"],
                                         cls=lane_cls[pt["lane"]]))
    # pair in/out of the same lane inside an intermediate partition -> ft slot
    lane_ports = {l["id"]: l["ports"] for l in pl["lanes"]}
    port_idx = {}
    for lid, pids in lane_ports.items():
        for i, pid in enumerate(pids):
            port_idx[pid] = (lid, i, len(pids))
    sigs, members = {}, {}
    for p in pl["parts"]:
        ent = inst_buses.get(p["name"], [])
        func, slots = [], []
        byl = collections.defaultdict(list)
        for e in ent:
            byl[e["lane"]].append(e)
        for lid, es in byl.items():
            ins = [e for e in es if e["role"] == "dst"]
            outs = [e for e in es if e["role"] == "src"]
            # an intermediate crossing: dst of port i and src of port i+1
            used = set()
            for ei in ins:
                li, i, n = port_idx[ei["port"]]
                nxt = lane_ports[lid][i + 1] if i + 1 < n else None
                eo = next((x for x in outs if x["port"] == nxt), None)
                if eo is not None:
                    st = st_of[(lid, i)]
                    slots.append((ei, eo, st))
                    used |= {ei["port"], eo["port"]}
            for e in es:
                if e["port"] not in used:
                    func.append(e)
        fsig = tuple(sorted((e["role"], e["face"], e["win"], e["width"], e["kind"], e["cls"]) for e in func))
        ssig = tuple(sorted((ei["face"], ei["win"], eo["face"], eo["win"], ei["width"], st) for ei, eo, st in slots))
        key = (p["base"], tuple(round(v, 3) for v in (p["w"], p["h"])), fsig, ssig)
        sigs[p["name"]] = (key, func, slots)
    types = collections.OrderedDict()
    for p in pl["parts"]:
        types.setdefault(sigs[p["name"]][0], []).append(p["name"])
    # ---- emit
    tnames = {}
    cnt = collections.Counter()
    for key, names in types.items():
        base = key[0]
        cnt[base] += 1
        tnames[key] = "%s__t%d" % (base, cnt[base]) if True else base
    ptype, busname = {}, {}
    out_types = {}
    for key, names in types.items():
        tn = tnames[key]
        rep = P[names[0]]
        _, func, slots = sigs[names[0]]
        buses, ftsl = [], []
        # canonical order -> names
        fs = sorted(func, key=lambda e: (e["role"], e["face"], e["win"], e["width"], e["kind"], e["cls"]))
        canon_f = []
        cc = collections.Counter()
        for e in fs:
            nm = "%s_%s%d" % (e["cls"].replace("-", "_"), "o" if e["role"] == "src" else "i", cc[(e["cls"], e["role"])])
            cc[(e["cls"], e["role"])] += 1
            canon_f.append(nm)
            buses.append(dict(name=nm, dir="out" if e["role"] == "src" else "in", width=e["width"], kind=e["kind"],
                              note="face %s window %s (type frame)" % (e["face"], list(e["win"]))))
        ss = sorted(slots, key=lambda t: (t[0]["face"], t[0]["win"], t[1]["face"], t[1]["win"], t[0]["width"], t[2]))
        for i, (ei, eo, st) in enumerate(ss):
            ftsl.append(dict(name="ft%d" % i, in_face=ei["face"], out_face=eo["face"], width=ei["width"], stations=st))
        kind = rep["kind"]
        hard = kind in ("phy", "link")
        cont = [dict(inst=c["inst"], module=c["module"], status=c.get("status", "rework" if kind in
                     ("frame", "slice", "svc", "unit", "cte") else "reuse"))
                for c in rep["contents"]] if rep["contents"] else []
        ty = dict(module="s81p_" + tn, outline_um=[rep["w"], rep["h"]], hard=hard, buses=buses, ft_slots=ftsl,
                  clock=dict(tap_um=[round(rep["w"] / 2 / G) * G, round(rep["h"] / 2 / G) * G], layer="M9"),
                  reset=dict(sync_stages=2), contents=cont,
                  note="%s partition; %d replicas" % (kind, len(names)))
        if not cont:
            ty.pop("contents")
        out_types[tn] = ty
        # per-instance bus name maps
        for n in names:
            _, f2, s2 = sigs[n]
            f2s = sorted(f2, key=lambda e: (e["role"], e["face"], e["win"], e["width"], e["kind"], e["cls"]))
            for e, nm in zip(f2s, canon_f):
                busname[(n, e["port"], e["role"])] = nm
            s2s = sorted(s2, key=lambda t: (t[0]["face"], t[0]["win"], t[1]["face"], t[1]["win"], t[0]["width"], t[2]))
            for i, (ei, eo, st) in enumerate(s2s):
                busname[(n, ei["port"], "dst")] = "ft%d_i" % i
                busname[(n, eo["port"], "src")] = "ft%d_o" % i
            ptype[n] = tn
    parts = [dict(name=p["name"], type=ptype[p["name"]], origin_um=[p["x0"], p["y0"]], orient=p["orient"])
             for p in pl["parts"]]
    oports = []
    for pt in ports:
        w0, w1, fsrc, _, _ = win[pt["id"]]
        oports.append(dict(id=pt["id"], src=dict(part=pt["a"], bus=busname[(pt["a"], pt["id"], "src")]),
                           dst=dict(part=pt["b"], bus=busname[(pt["b"], pt["id"], "dst")]), width=pt["width"],
                           kind=pt["kind"], face=fsrc, layers=H_LAYERS if fsrc in "EW" else V_LAYERS,
                           window_um=[w0, w1]))
    olanes = [dict(id=l["id"], ports=l["ports"]) for l in pl["lanes"]]
    plan = {
        "schema": "opentallas.die_plan.v1",
        "note": "S81 72-frame MU release die, plan v1 (PLAN-S81 10-23): frame bands, 6x6 arrays of 3-frame E-W chains, "
                "lane columns, S halves lower / N halves upper. Generated by physical/die_plan/s81/gen_plan.py + to_schema.py.",
        "die": {"name": "s81", "label": "DeepSeek ROM S81 72-frame MU release die", "tech": "asap7",
                "outline_um": [33000.0, 26000.0], "period_ps": 833, "reach_um": 1500.0, "rep_um": 450.0,
                "grid_um": G,
                "layer_budget": {"partition_signal_max": "M7", "die_layers": ["M8", "M9"],
                                 "die_use": ["clock_spine", "pg", "ft_reserved"], "cut_avail": {"M8": 0.6, "M9": 0.6}},
                "pg": {"partition_pg_max": "M7", "grid": [
                    {"layer": "M8", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]},
                    {"layer": "M9", "width_um": 0.48, "pitch_um": 8.64, "offset_um": 4.32, "nets": ["VDD", "VSS"]}]},
                "channels": pl["chans"] + [
                    {"rect_um": [0, 0, 33000.0, 103.68], "reason": "seal ring"},
                    {"rect_um": [0, 25894.08, 33000.0, 26000.0], "reason": "seal ring"}]},
        "partition_types": out_types,
        "partitions": parts,
        "ports": oports,
        "lanes": olanes,
        "clock": {"source": {"part": "@die", "bus": "clk"}, "insertion_ps": 250, "insertion_tol_ps": 40,
                  "neighbour_skew_ps": 80, "face_xing": "budgeted",
                  "spine": {"layers": ["M8", "M9"], "root_um": [16502.4, 12994.56], "topology": "htree"}},
        "reset": {"source": {"part": "@die", "bus": "rst_n"}, "sync_stages": 2, "data_reset": False,
                  "epoch_bit": True, "release": "counted"},
        "budgets": {"face_pins_per_um": 6, "face_pin_layers": 2, "face_window_um": 10, "pin_track_max": 0.6,
                    "cut_ratio_max": 0.6, "cut_step_um": 250},
    }
    # side channels left/right of the outline (seal ring)
    plan["die"]["channels"] += [{"rect_um": [0, 103.68, 103.68, 25894.08], "reason": "seal ring"},
                                {"rect_um": [32892.48, 103.68, 33000.0, 25894.08], "reason": "seal ring"}]
    json.dump(plan, open(d / "die_plan.json", "w"), indent=0)
    kinds = collections.Counter(P[n[0]]["kind"] for n in types.values())
    print(json.dumps(dict(types=len(types), types_by_kind=kinds, faces_over=len(over), worst_over=sorted(
        over, key=lambda o: -o["pins_per_um"])[:8]), indent=1))


if __name__ == "__main__":
    main()
