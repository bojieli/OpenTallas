#!/usr/bin/env python3
"""KV-PLAN3F 10-25 (owner option B, ID straps; KV-CORE-RTL 07:09): ASTK 4 -> 1 strap master in the plan.

The four corner cores kv3_astk_{EN,ES,WN,WS} (kv3_hub_Eo / kv3_hub_Wo) become instances of ONE master module kv3_astk
(kit kv3_astk__190.08x181.44, 1692 pins = corner pins + ck, rst_n, strap_corner[1:0]).  Each instance:
  module kv3_astk, pins_file cores/kv3_astk_pins.json (the master kit table in plan convention: a pin also in the
  kv3_astk_EN plan table keeps that plan coordinate, the master's own layout = EN; a pin new in the kit (ck, rst_n,
  straps) keeps its kit coordinate), orient = the whole-instance orient (R0/MX/MY/R180) that keeps the most pins on the face
  the old corner table chose (its partner side; ties: smaller mean displacement), straps [strap_corner, 2 b, value EN 2'b11 | ES 2'b10 | WN 2'b01 | WS 2'b00]
  (bit1 = E side, bit0 = N half; the hub ties TIEHI/TIELO next to the pin).
Hub internal_stations[] to/from a re-oriented core port that lands on another face (ES/WS am + ap: W/E -> N) are
re-routed to the oriented master pins round the core box (KV-PLAN3 07:2x: re-pin the slots and the ahub side).
Pins of the old corner tables missing from the master (am g drop qo[571]) are reported, not invented.
    astk_master_v39f.py PLAN_IN PLAN_OUT --kit-pins KIT/pins.json --cores DIR --report R.json
"""
import argparse
import json
import math
import re
from pathlib import Path

W, H = 190.08, 181.44
VAL = dict(EN="2'b11", ES="2'b10", WN="2'b01", WS="2'b00")
OR = {"R0": lambda x, y: (x, y), "MX": lambda x, y: (x, H - y), "MY": lambda x, y: (W - x, y),
      "R180": lambda x, y: (W - x, H - y)}


def load(f):
    j = json.loads(Path(f).read_text())
    return j, (j.get("pins", j) if isinstance(j, dict) else j)


def face(x, y):
    d = dict(W=x, E=W - x, S=y, N=H - y)
    return min(d, key=d.get)


def key(q):
    return q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]"


REACH = 405.0
CLR = 17.28                 # corridor offset off the core box (2 x 8.64 lattice)


def hops_on(path, reach=REACH):
    """Anchor each Manhattan bend, then subdivide straight segments at <= reach.

    A station on the final bend makes the last hop enter the core on its pin
    face. Equal distance placement across the whole polyline can skip this
    bend and put the last station behind the core.
    """
    clean = []
    for p in path:
        p = tuple(p)
        if not clean or p != clean[-1]:
            clean.append(p)
    out, length = [], 0.0
    for seg, (p, q) in enumerate(zip(clean, clean[1:])):
        if abs(p[0] - q[0]) > 1e-6 and abs(p[1] - q[1]) > 1e-6:
            raise ValueError(f"non-Manhattan station segment: {p} -> {q}")
        distance = abs(p[0] - q[0]) + abs(p[1] - q[1])
        length += distance
        pieces = max(1, math.ceil(distance / reach - 1e-9))
        for i in range(1, pieces + 1):
            # Every interior path corner is a station; the core/face endpoints
            # already contain their own boundary registers.
            if seg == len(clean) - 2 and i == pieces:
                continue
            f = i / pieces
            out.append([round(p[0] + f * (q[0] - p[0]), 3),
                        round(p[1] + f * (q[1] - p[1]), 3)])
    return out, length


def reroute(raw, mk, insts):
    """internal_stations[] between a hub face and a re-oriented astk core port: the core end moves to the oriented
    master pins (port centroid on its face), the path leaves the core face by CLR, runs round the core box on the side
    of the far end, and stations are re-spaced at <= REACH; lanes on that bus get the depth change."""
    rerouted, depth = [], {}
    for ins in insts:
        if ins["orient"] == "R0" or not ins["ports_off_face"]:
            continue
        t = raw["partition_types"][ins["type"]]
        hc = next(h for h in t["hard_cores"] if h["inst"] == ins["inst"])
        (ox, oy), f = hc["origin_um"], OR[ins["orient"]]
        x0, y0, x1, y1 = ox, oy, ox + W, oy + H
        for e in t.get("internal_stations") or []:
            ends = [(k, str(e.get(k, ""))) for k in ("launch", "capture")]
            hit = [(k, v.split(".", 1)[1]) for k, v in ends if v.startswith(ins["inst"] + ".")]
            if not hit:
                continue
            side, port = hit[0]
            pts = [f(*mk[n]) for n in mk if re.sub(r"\[\d+\]$", "", n) == port]
            if not pts or port not in ins["ports_off_face"]:
                continue
            cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            fc = face(cx, cy)
            pin = (round(cx + ox, 3), round(cy + oy, 3))
            far = tuple(e["to_um"] if side == "launch" else e["from_um"])
            out_pt = dict(N=(pin[0], y1 + CLR), S=(pin[0], y0 - CLR), E=(x1 + CLR, pin[1]), W=(x0 - CLR, pin[1]))[fc]
            if fc in "NS":       # round the core on the far end's x side, then straight to the far end
                wx = x0 - CLR if far[0] < (x0 + x1) / 2 else x1 + CLR
                core_side = [pin, out_pt, (wx, out_pt[1]), (wx, far[1])]
            else:
                wy = y0 - CLR if far[1] < (y0 + y1) / 2 else y1 + CLR
                core_side = [pin, out_pt, (out_pt[0], wy), (far[0], wy)]
            path = core_side + [far]
            if side == "launch":
                regs, L = hops_on(path)
                e["from_um"] = list(pin)
            else:
                regs, L = hops_on(path[::-1])
                e["to_um"] = list(pin)
            old = len(e["regs_um"])
            e["regs_um"] = regs
            e["note"] = (e.get("note", "") + f" | v3.9f ASTK master {ins['orient']}: core end on the {fc} face, path "
                         f"{L:.0f} um round the core box (+{CLR:g} um), {len(regs)} stations <= {REACH:g} um").lstrip(" |")
            rerouted.append(dict(type=ins["type"], conn=e.get("conn"), port=f"{ins['inst']}.{port}", face=fc,
                                 path_um=round(L, 1), stations=[old, len(regs)]))
            if e.get("conn", "").startswith("bus:") and len(regs) != old:
                depth[(ins["type"], e["conn"][4:])] = depth.get((ins["type"], e["conn"][4:]), 0) + len(regs) - old
    ptype = {p["name"]: p["type"] for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {}
    for ln in raw["lanes"]:
        d = 0
        for end in (ports[ln["ports"][0]]["src"], ports[ln["ports"][-1]]["dst"]):
            d += depth.get((ptype.get(end["part"]), end["bus"]), 0)
        if d:
            ln["fixed_cycles"] = int(ln.get("fixed_cycles", 0)) + d
            ln["note"] = ln.get("note", "") + f" | v3.9f ASTK master re-route {d:+d} internal stations"
            lanes[ln["id"]] = d
    return rerouted, lanes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--kit-pins", required=True)
    ap.add_argument("--cores", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    cores = Path(a.cores)
    _, kit = load(a.kit_pins)
    en_js, en = load(cores / "kv3_astk_EN_pins.json")
    enk = {key(q): q for q in en}
    master = []
    for q in kit:
        k = key(q)
        if k in enk:
            master.append(dict(enk[k]))
        else:
            r = dict(name=k, layer=q["layer"], x=q["x"], y=q["y"])
            if q.get("face"):
                r["face"] = q["face"]
            master.append(r)
    mk = {key(q): (q["x"], q["y"]) for q in master}
    out_js = dict(schema=en_js.get("schema", "opentallas.die_plan.core_pins.v1") if isinstance(en_js, dict) else
                  "opentallas.die_plan.core_pins.v1", core="kv3_astk",
                  frame="core R0, origin (0,0), outline 190.08 x 181.44",
                  source=f"KV-PLAN3F 10-25: ASTK strap master kit table ({a.kit_pins}); pins also in kv3_astk_EN keep "
                         "the EN plan coordinate", pins=master)
    (cores / "kv3_astk_pins.json").write_text(json.dumps(out_js, indent=1) + "\n")
    raw = json.loads(Path(a.plan).read_text())
    rep = dict(master_pins=len(master), instances=[])
    for tn, t in raw["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            m = hc.get("module", "")
            if not m.startswith("kv3_astk_"):
                continue
            c = m.rsplit("_", 1)[1]
            _, old = load(cores / f"kv3_astk_{c}_pins.json")
            ok = {key(q): (q["x"], q["y"]) for q in old}
            disp, fmatch = {}, {}
            for o, f in OR.items():
                d = [abs(f(*mk[k])[0] - x) + abs(f(*mk[k])[1] - y) for k, (x, y) in ok.items() if k in mk]
                disp[o] = sum(d) / max(1, len(d))
                fmatch[o] = sum(face(*f(*mk[k])) == face(x, y) for k, (x, y) in ok.items() if k in mk)
            # the orient that keeps the most pins on the face the corner table chose (partner side), then displacement
            o = max(OR, key=lambda z: (fmatch[z], -disp[z], z == "R0"))
            off_face = sorted({re.sub(r"\[\d+\]$", "", k) for k, (x, y) in ok.items()
                               if k in mk and face(*OR[o](*mk[k])) != face(x, y)})
            missing = sorted(k for k in ok if k not in mk)
            hc.update(module="kv3_astk", pins_file="cores/kv3_astk_pins.json", orient=o,
                      straps=[dict(port="strap_corner", width=2, value=VAL[c],
                                   note="{E/W, N/S}: bit1 = E side, bit0 = N half (KV-CORE-RTL 10-25 07:09)")])
            hc["note"] = (hc.get("note", "") + f" | v3.9f ASTK strap master kv3_astk ({c}, {o}, strap_corner={VAL[c]})"
                          ).lstrip(" |")
            rep["instances"].append(dict(type=tn, inst=hc["inst"], corner=c, orient=o,
                                         mean_disp_um={k: round(v, 1) for k, v in disp.items()},
                                         face_match=fmatch, ports_off_face=off_face,
                                         pins_missing_in_master=missing,
                                         pins_moved=sum(1 for k in ok if k in mk and
                                                        OR[o](*mk[k]) != ok[k])))
    rep["rerouted"], rep["lanes"] = reroute(raw, mk, rep["instances"])
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for r in rep["rerouted"]:
        print(f"astk_master: re-route {r['type']} {r['conn']} {r['port']} -> {r['face']} face, {r['path_um']} um, "
              f"stations {r['stations'][0]} -> {r['stations'][1]}")
    for i in rep["instances"]:
        print(f"astk_master: {i['type']}.{i['inst']} {i['corner']} -> kv3_astk {i['orient']} mean disp "
              f"{i['mean_disp_um'][i['orient']]} um, face match {i['face_match'][i['orient']]}, off-face ports "
              f"{i['ports_off_face']}, missing {i['pins_missing_in_master']}")


if __name__ == "__main__":
    main()
