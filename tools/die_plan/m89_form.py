#!/usr/bin/env python3
"""X-TIER-OTC 11-11 (COORD queue ruling, METHODOLOGY 12.1c/e, 12.2b, 12.7a): FORM (d) plan transform, die-agnostic.

    python3 tools/die_plan/m89_form.py PLAN.json SPEC.json --out NEW.json [--report R.json]

A wide lane that crosses partitions only to reach the far side stops using in-partition lane wire: its long wire is a
DECLARED DIE-TOP NET on the leftover M8 (H) / M9 (V) (port route "m89"), and its stations are partition-owned register
BAYS (12.2b) entered through M7 entry pins (12.7a).  The plan keeps every register: an ft slot of n stations is split
into k BAY SLOTS <slot>b0..b<k-1> (stations stacked inside a bay share it; the hop between two bays is a die-top net
port, possibly between two buses of ONE partition), so gen_rtl emits the same n ot_dp_st stages in the same order,
lane_natural() counts the same stations (latency rows unchanged) and every inter-partition port keeps its id (clock
landing edges cland_clk__<port> keep theirs; their fclk bus names follow the renamed buses).

SPEC (opentallas.m89_form.v1):
  {"schema": "opentallas.m89_form.v1",
   "die_m89": {...die.m89 budget, optional},
   "slots": [{"type": T, "slot": S, "in_route": "m89"|"face", "out_route": "m89"|"face",
              "bays": [{"rect_um": [x0, y0, x1, y1], "stations": [0, 1], "landing": false}, ...]}]}
  bays in data order; their stations partition 0..n-1 in order.  One bay keeps the slot name.  A bay with
  landing true holds the in bus's clock landing ring (it must be bay 0): the band moves to the bay rect.
  keep_regs true keeps the station sites (only the m89 end moves to the bay entry field).
  in_route "face" keeps the slot's in face pins (an abutted in port, e.g. a turn leaf fed from its neighbour); then
  station 0 stays on its face site and bay 0 is its out-pin field.
Ports: route m89 when both ends are m89 ends after the split; one m89 end against a face end is an error (put the
other partition's slot in the spec too).  m89 ports carry no face/window/layers.
"""
import argparse
import copy
import json
import re
import sys

SCHEMA = "opentallas.m89_form.v1"


class FormError(Exception):
    pass


def centre(r):
    return [round((r[0] + r[2]) / 2.0, 4), round((r[1] + r[3]) / 2.0, 4)]


def split_slot(slot, spec):
    n = int(slot.get("stations", 1))
    bays = spec["bays"]
    seq = [k for b in bays for k in b["stations"]]
    if seq != list(range(n)):
        raise FormError(f"slot {slot['name']}: bay stations {seq} do not cover 0..{n - 1} in order")
    if any(b.get("landing") for b in bays[1:]):
        raise FormError(f"slot {slot['name']}: only bay 0 may hold the landing ring")
    k = len(bays)
    names = [slot["name"]] if k == 1 else [f"{slot['name']}b{j}" for j in range(k)]
    regs = slot.get("regs_um") or []
    out = []
    for j, (nm, b) in enumerate(zip(names, bays)):
        s = copy.deepcopy(slot)
        s["name"] = nm
        s["stations"] = len(b["stations"])
        if not spec.get("keep_regs"):
            s.pop("bit_sites_um", None)      # sites follow the bay (the kit fills bay_um)
            s.pop("bit_site_cell_um", None)
        ir = spec.get("in_route", "m89") if j == 0 else "m89"
        orr = spec.get("out_route", "m89") if j == k - 1 else "m89"
        s["in_route"], s["out_route"], s["bay_um"] = ir, orr, [round(v, 4) for v in b["rect_um"]]
        if spec.get("keep_regs") and regs:
            s["regs_um"] = [list(regs[st]) for st in b["stations"]]     # stations keep their sites (e.g. a
            # station cell whose own lane wire stays; only its in end becomes an m89 entry field)
        else:
            s["regs_um"] = [list(regs[st]) if (ir == "face" and st == 0 and regs) else centre(b["rect_um"])
                            for st in b["stations"]]
        if ir == "m89":
            for f in ("in_window_um", "in_layers", "in_order"):
                s.pop(f, None)
        if orr == "m89":
            for f in ("out_window_um", "out_layers", "out_order"):
                s.pop(f, None)
        if ir == "m89" and orr == "m89":
            s.pop("layers", None)
            s.pop("order", None)
        s["note"] = (f"X-TIER-OTC form (d): bay {j}/{k} of {slot['name']} "
                     f"(stations {b['stations']}{', landing ring' if b.get('landing') else ''})")
        out.append(s)
    return out


def transform(raw, spec):
    if spec.get("schema") != SCHEMA:
        raise FormError(f"spec schema {spec.get('schema')!r} != {SCHEMA}")
    P = copy.deepcopy(raw)
    T = P["partition_types"]
    inst = {}
    for p in P["partitions"]:
        inst.setdefault(p["type"], []).append(p["name"])
    busmap = {}          # (type, old bus) -> new bus
    spec_by = {}         # (type, new end bus) -> spec entry
    chains = {}          # (type, slot) -> [bay slot names]
    landing = {}
    for e in spec["slots"]:
        tn, sn = e["type"], e["slot"]
        t = T.get(tn)
        if t is None:
            raise FormError(f"unknown type {tn}")
        slots = t.get("ft_slots", [])
        i = next((i for i, s in enumerate(slots) if s["name"] == sn), None)
        if i is None:
            raise FormError(f"type {tn}: no ft slot {sn}")
        new = split_slot(slots[i], e)
        clash = {s["name"] for s in slots} & {s["name"] for s in new[1:]}
        if clash:
            raise FormError(f"type {tn}: bay slot names {sorted(clash)} exist")
        slots[i:i + 1] = new
        names = [s["name"] for s in new]
        chains[(tn, sn)] = names
        busmap[(tn, sn + "_i")] = names[0] + "_i"
        busmap[(tn, sn + "_o")] = names[-1] + "_o"
        spec_by[(tn, names[0] + "_i")] = spec_by[(tn, names[-1] + "_o")] = e
        if e["bays"][0].get("landing"):
            landing[(tn, sn)] = e["bays"][0]["rect_um"]
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        if sn + "_i" in bands:
            bd = bands.pop(sn + "_i")
            if (tn, sn) in landing:
                bd["rect_um"] = [round(v, 4) for v in landing[(tn, sn)]]
                bd.pop("rects_um", None)
                bd["placement"] = "X-TIER-OTC form (d): landing ring in the m89 bay 0 of " + sn
            bands[names[0] + "_i"] = bd
        elif (tn, sn) in landing:
            raise FormError(f"type {tn} slot {sn}: bay 0 marked landing but the type has no band {sn}_i")
    # every other reference to a renamed bus inside its type (clock landing pins / edge clocks / landing entries /
    # ring instance names / reset) follows the new name; their point coordinates move to the bay entry field
    bayc = {}
    for e in spec["slots"]:
        bayc[(e["type"], busmap[(e["type"], e["slot"] + "_i")])] = centre(e["bays"][0]["rect_um"])
        bayc[(e["type"], busmap[(e["type"], e["slot"] + "_o")])] = centre(e["bays"][-1]["rect_um"])
    moved = 0
    for tn in {k[0] for k in busmap}:
        pairs = [(ob, nb) for (t_, ob), nb in busmap.items() if t_ == tn and ob != nb]
        if not pairs:
            continue
        t = T[tn]
        for key in [k for k in t if k != "ft_slots"]:
            txt = json.dumps(t[key])
            for ob, nb in pairs:
                txt = re.sub(r"(?<![A-Za-z0-9])" + re.escape(ob) + r"(?![A-Za-z0-9])", nb, txt)
            t[key] = json.loads(txt)
        ends = {nb: bayc[(tn, nb)] for _, nb in pairs if (tn, nb) in bayc}
        tok = {nb: re.compile(r"(?<![A-Za-z0-9])" + re.escape(nb) + r"(?![A-Za-z0-9])") for nb in ends}

        def walk(o):
            nonlocal moved
            if isinstance(o, dict):
                hit = [nb for nb, rx in tok.items()
                       if any(isinstance(v, str) and rx.search(v) for v in o.values())]
                if len(hit) == 1 and (tn, hit[0]) in bayc and \
                        (spec_by[(tn, hit[0])].get("in_route", "m89") == "m89" if hit[0].endswith("_i")
                         else spec_by[(tn, hit[0])].get("out_route", "m89") == "m89"):
                    for k in ("xy_um", "pin_xy_um", "tap_um"):
                        if k in o and isinstance(o[k], list) and len(o[k]) == 2:
                            o[k] = list(bayc[(tn, hit[0])])
                            moved += 1
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(t.get("clock") or {})
    tof = {p["name"]: p["type"] for p in P["partitions"]}

    def mapped(end):
        if end["part"] not in tof:
            return end
        nb = busmap.get((tof[end["part"]], end["bus"]))
        return dict(end, bus=nb) if nb else end

    def is_m89_end(end):
        if end["part"] not in tof:
            return False
        t = T[tof[end["part"]]]
        b = end["bus"]
        for s in t.get("ft_slots", []):
            if b == s["name"] + "_i":
                return s.get("in_route") == "m89"
            if b == s["name"] + "_o":
                return s.get("out_route") == "m89"
        return any(x["name"] == b and x.get("route") == "m89" for x in t.get("buses", []))

    bad = []
    rename = {}
    for pr in P["ports"]:
        a, b = mapped(pr["src"]), mapped(pr["dst"])
        for side, ne in (("src", a), ("dst", b)):
            if ne["bus"] != pr[side]["bus"]:
                rename[(pr[side]["part"], pr[side]["bus"])] = ne["bus"]
        pr["src"], pr["dst"] = a, b
        ma, mb = is_m89_end(a), is_m89_end(b)
        if ma and mb:
            pr["route"] = "m89"
            for f in ("face", "window_um", "layers", "segments", "order"):
                pr.pop(f, None)
        elif ma or mb:
            bad.append(f"port {pr['id']}: {'src' if ma else 'dst'} end is m89, the other end is a face end")
    if bad:
        raise FormError("; ".join(bad))
    # intra-partition bay -> bay die-top nets, inserted into their lanes
    ports = {p["id"]: p for p in P["ports"]}
    added = 0
    for ln in P["lanes"]:
        out = []
        for pid in ln["ports"]:
            out.append(pid)
            d = ports[pid]["dst"]
            if d["part"] not in tof:
                continue
            tn = tof[d["part"]]
            for (ct, sn), names in chains.items():
                if ct == tn and len(names) > 1 and d["bus"] == names[0] + "_i":
                    for j in range(len(names) - 1):
                        nid = f"{ln['id']}__{d['part']}_{sn}_b{j}"
                        if nid in ports:
                            raise FormError(f"port id {nid} exists")
                        np_ = dict(id=nid, src=dict(part=d["part"], bus=names[j] + "_o"),
                                   dst=dict(part=d["part"], bus=names[j + 1] + "_i"),
                                   width=ports[pid]["width"], kind=ports[pid].get("kind", "data"), route="m89")
                        if "epoch" in ports[pid]:
                            np_["epoch"] = ports[pid]["epoch"]
                        P["ports"].append(np_)
                        ports[nid] = np_
                        out.append(nid)
                        added += 1
        ln["ports"] = out
    # clock landing edges follow the renamed buses (edge ids = port ids, unchanged)
    edges = ((P.get("clock") or {}).get("landing_network") or {}).get("edges") or []
    fclk = 0
    for e in edges:
        for side, pre in (("src", "fclk_out_"), ("dst", "fclk_in_")):
            en = e.get(side) or {}
            if str(en.get("bus", "")).startswith(pre):
                nb = rename.get((en.get("part"), en["bus"][len(pre):]))
                if nb:
                    en["bus"] = pre + nb
                    fclk += 1
    if spec.get("die_m89"):
        P["die"]["m89"] = spec["die_m89"]
    lb = P["die"].setdefault("layer_budget", {})
    du = lb.setdefault("die_use", [])
    if "die_top_signal" not in du:
        du.append("die_top_signal")
    # leftover references to the old bus names inside the touched types (reported, never guessed)
    stale = []
    for (tn, ob), nb in busmap.items():
        if ob == nb:
            continue
        t = dict(T[tn])
        t.pop("ft_slots", None)
        if json.dumps(t).find(f'"{ob}"') >= 0:
            stale.append(f"type {tn}: still names {ob}")
    rep = dict(schema=SCHEMA + ".report", slots=len(chains), bay_slots=sum(len(v) for v in chains.values()),
               ports_m89=sum(1 for p in P["ports"] if p.get("route") == "m89"), ports_added=added,
               fclk_endpoints_renamed=fclk, landing_resited=len(landing), stale_refs=stale, points_moved=moved,
               chains={f"{k[0]}:{k[1]}": v for k, v in chains.items()})
    return P, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    spec = json.load(open(a.spec))
    try:
        P, rep = transform(raw, spec)
    except FormError as e:
        print(f"m89_form: {e}", file=sys.stderr)
        return 2
    json.dump(P, open(a.out, "w"))
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "chains"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
