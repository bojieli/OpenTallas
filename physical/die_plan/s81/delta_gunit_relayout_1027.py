#!/usr/bin/env python3
"""S81 plan event CANDIDATE 2026-10-27 (S81-CORES-R25, COORD ruling S81-CORES-R24 (b)): gunit re-layout of all 10 hard
cores as ONE plan event.  Target: every core<->core bundle <= 405 um PIN-TO-PIN; stations only where the layout cannot
get there, cycles ledgered.

Why: the 10-25 CCONN2 re-place folded the RTL rung L3 / L1 / L2 / L0 / L4 / L5 (both ends, L3 and L5, talk to S-face
bus windows) into a U whose bundle faces point AWAY from their partners: L1-L2 928 um, L0-L0r 736, L4-L5 676, L0-L4
674, L1-L1c 580, L4-L4r 497 (pin-to-pin per bit, gunit_links_1027.py census at 5fc1caa5ca); the G0 check measured box
to box and passed them.

Layout (gunit type frame; every origin on the 8.64 lattice, outlines unchanged incl. the approved L2 34.56 outline):
  column A (W)  x 768.96: L3 (y 17.28) and L1 (y 380.16), orient MY -> L1's select-leaf face (sa/sb/bw/we/gs/i) faces
                W, where L1c (R0, x 665.28) and the soft L1f fronts sit; L1.S <-> L3.N stays face to face.
  column B (E)  x 1270.08: L5 (y 17.28), L4 (y 336.96), L0 (y 423.36), orient MX -> L5's vi_n/vo_n move to its S face
                over the xtier_i1/o1 windows, and every rung face of L5/L4/L0 faces its partner.
  bridge        L2 (R0) at (1019.52, 613.44) spans the 155.52-um channel above both column tops (596.16): its S face
                serves L1.N (W half), its N-face bundle drops onto L0.N (E half).  A U-turn at the thin L2 costs no
                side-face pins (its 34.56-um E/W faces cannot carry 1.4k bits).
  side leaves   L5f / L4r / L0r (MX) E of column B (x 1632.96), y-aligned with their partners.
  MX / MY / R0 only (no rotation): signed or soon-signed views (L5, side leaves) are re-used as mirrored instances.
Pins (only the two cores that must re-pin; both are unsigned and get new kits):
  L2: the 265 cw_d/cw_a/cw_v pins leave the E face for the S face E end (x 303.9-329.3, same M5 0.096 lattice as
      the S face); the S-face L1 bundle and the N-face L0 bundle are re-ordered on their existing slots so bit k sits
      in the x order of its partner pin (placed frame).
  L3: vi_s packed at the core-frame E end (placed W end, MY), vo_s at the core-frame W end (placed E), M5 0.096 as
      today's 154-208 pack (10.4/um, the existing core-face density).
Stations (internal_stations, FIRM; per-bit hops from the census below):
  xtier_i0  window 6.1-66.0 -> station (401, 8.64) -> L3.vi_s: 1 station (as today, moved from 432.8): hops <= 403.5.
  xtier_o0  L3.vo_s -> station (1268.56, 8.64, channel) -> window 1508-1568: NEW, +1 cycle (rung S out).
  unit_i0   window 1449-1507 -> station (1440.08, 328.32, the 17.28 strip between L5 and L4) -> L2 cw: NEW, +1 cycle.
  The two windows of L3 are 1,472 um apart; three hops (one station) reach that only with <= 27 um pin packs at both L3
  ends (>10 pins/um) -> one more station is geometric, not a layout choice.  unit_i0 -> L2 at the U top is >= 613 um.
Clock: the L5 tap follows its clk pin under MX (same -6.33 um x offset).
  python3 physical/die_plan/s81/delta_gunit_relayout_1027.py [--check]
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PLAN = HERE / "die_plan.json"
CONNS = HERE / "core_conns.json"
PINDIR = HERE / "inputs" / "core_pins"
RTL = REPO / "rtl" / "dsrom_sys" / "s81_dv" / "unit" / "dsdv_gunit.sv"
TYPE = "gunit__t1"
W = 345.6
OLD = {"u_l5": ([1537.92, 17.28], "R0"), "u_l1": ([812.16, 207.36], "R0"), "u_l1c": ([708.48, 207.36], "R0"),
       "u_l0": ([1175.04, 207.36], "R0"), "u_l2": ([1175.04, 155.52], "R0"), "u_l3": ([812.16, 17.28], "R0"),
       "u_l0r": ([1175.04, 397.44], "R0"), "u_l5f": ([1900.8, 17.28], "R0"), "u_l4r": ([1537.92, 423.36], "R0"),
       "u_l4": ([1537.92, 336.96], "R0")}
A, C = 768.96, 155.52
B = A + W + C                      # 1270.08
E = B + W + 17.28                  # 1632.96
NEW = {"u_l3": ([A, 17.28], "MY"), "u_l1": ([A, 380.16], "MY"), "u_l1c": ([A - 17.28 - 86.4, 380.16], "R0"),
       "u_l5": ([B, 17.28], "MX"), "u_l4": ([B, 336.96], "MX"), "u_l0": ([B, 423.36], "MX"),
       "u_l2": ([A + (W + C) / 2, 613.44], "R0"),
       "u_l5f": ([E, 17.28], "MX"), "u_l4r": ([E, 285.12], "MX"), "u_l0r": ([E, 423.36], "MX")}
# track offset per orient, as every mirrored S81 core in this plan (R0 [0.108,0.012], MX [0.108,0.036],
# MY [0.132,0.012]): keeps the core's on-track pins on the type-frame track lattice after the mirror
TOFF = {"R0": [0.108, 0.012], "MX": [0.108, 0.036], "MY": [0.132, 0.012]}
BASE_PINHASH = {"dsdv_gunit_l2": "ee6a4aebf832", "dsdv_gunit_l3": "b2855d2e6c6a"}
STATIONS = [
    dict(conn="bus:xtier_i0", from_um=[36.078, 0.0], to_um=[A + 13.3, 17.292], regs_um=[[401.0, 8.64]],
         launch="face bus xtier_i0", capture="u_gunit.u_l3.vi_s",
         note="S81-CORES-R25 gunit re-layout 10-27: 1 FIRM station (was 432.819, same cycle count); per-bit hops "
              "<= 403.5 um (delta_gunit_relayout_1027.py)"),
    dict(conn="bus:xtier_o0", from_um=[A + 332.3, 17.292], to_um=[1538.194, 0.0],
         regs_um=[[1268.56, 8.64]], launch="u_gunit.u_l3.vo_s", capture="face bus xtier_o0",
         note="S81-CORES-R25 gunit re-layout 10-27: NEW FIRM station, +1 cycle on xtier_o0 (L3 -> s_3N_x06 ft1_i); "
              "L3's two windows are 1472 um apart -> geometric; ledger TOK"),
    dict(conn="bus:unit_i0", from_um=[1477.998, 0.0], to_um=[1342.3, 613.44], regs_um=[[1440.08, 328.32]],
         launch="face bus unit_i0", capture="u_gunit.u_l2.cw_d",
         note="S81-CORES-R25 gunit re-layout 10-27: NEW FIRM station in the 17.28 strip between L5 and L4, +1 cycle "
              "on unit_i0 (seqhost -> gunit cw); L2 is the U top (>= 613 um from the S face); ledger TOK"),
]


def orient(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def nb(n):
    m = re.match(r"^(\w+)(?:\[(\d+)\])?$", n)
    return m.group(1), m.group(2)


def rtl_conn(cores):
    src = re.sub(r"//[^\n]*", "", RTL.read_text())
    conn = collections.defaultdict(list)
    for inst in cores:
        m = re.search(r"\b" + inst + r"\s*\((.*?)\);", src, re.S)
        if not m:
            raise SystemExit(f"RTL instance {inst} not found")
        for pm in re.finditer(r"\.(\w+)\s*\(\s*([A-Za-z_]\w*)\s*\)", m.group(1)):
            port, net = pm.groups()
            if net not in ("clk", "rst_n"):
                conn[net].append((inst, port))
    return {n: e for n, e in conn.items() if len(e) == 2}


def placed(cores, pins, place):
    out = {}
    for inst, c in cores.items():
        (ox, oy), o = place[inst]
        w, h = c["outline_um"]
        for p in pins[inst]:
            port, bit = nb(p["name"])
            x, y = orient(o, w, h, p["x"], p["y"])
            out[(inst, port, bit)] = (ox + x, oy + y)
    return out


def repin_l3(pins):
    keep = [p for p in pins if nb(p["name"])[0] not in ("vi_s", "vo_s")]
    vi = sorted([p for p in pins if nb(p["name"])[0] == "vi_s"], key=lambda p: int(nb(p["name"])[1]))
    vo = sorted([p for p in pins if nb(p["name"])[0] == "vo_s"], key=lambda p: int(nb(p["name"])[1]))

    def snap(x):                                  # today's vi_s / vo_s lattice: 157.404 + k * 0.096
        return round(157.404 + round((x - 157.404) / 0.096) * 0.096, 3)
    out = [dict(p, x=snap(345.4 - 0.096 * (len(vi) - 1 - i)), layer="M5") for i, p in enumerate(vi)]
    # S81-CORES-R26: 0.204 sits half-way between lattice points (0.156 / 0.252), so snap() rounded consecutive vo_s
    # bits onto the same site (core_pin_sites_gate dup_site 87).  Start the W-end pack on the first lattice point >= 0.204.
    v0 = snap(0.204 + 0.048 + 1e-6)
    out += [dict(p, x=round(v0 + 0.096 * i, 3), layer="M5") for i, p in enumerate(vo)]
    xs = [(q["layer"], q["x"], q["y"]) for q in keep + out]
    assert len(xs) == len(set(xs)), "L3 re-pin stacks pins on one site"
    return keep + out


def repin_l2(cores, pins, conn):
    cwn = ("cw_d", "cw_a", "cw_v")
    cw = sorted([p for p in pins["u_l2"] if nb(p["name"])[0] in cwn],
                key=lambda p: (nb(p["name"])[0] != "cw_v", nb(p["name"])[0], int(nb(p["name"])[1] or 0)))
    rest = [dict(p) for p in pins["u_l2"] if nb(p["name"])[0] not in cwn]
    k0 = int((310.0 - 29.724) / 0.096) - 64
    cw = [dict(p, x=round(29.724 + 0.096 * (k0 + i), 3), y=0.042, layer="M5") for i, p in enumerate(cw)]
    l2 = rest + cw
    pp = placed(cores, dict(pins, u_l2=l2), NEW)
    part = {}
    for ends in conn.values():
        d = dict(ends)
        if "u_l2" in d:
            part[d["u_l2"]] = next(e for e in ends if e[0] != "u_l2")
    H = cores["u_l2"]["outline_um"][1]
    for face in ("S", "N"):
        idx = []
        for i, p in enumerate(l2):
            f = "S" if p["y"] < 1 else "N" if p["y"] > H - 1 else None
            port, bit = nb(p["name"])
            if f != face or port not in part or port in cwn:
                continue
            q = pp.get((part[port][0], part[port][1], bit))
            if q is not None:
                idx.append((q[0], i))
        slots = sorted((l2[i]["x"], l2[i]["y"], l2[i]["layer"]) for _, i in idx)
        order = [i for _, i in sorted(idx)]
        moved = {i: dict(l2[i], x=x, y=y, layer=ly) for (x, y, ly), i in zip(slots, order)}
        l2 = [moved.get(i, p) for i, p in enumerate(l2)]
    return l2


def census(cores, pins, conn, place):
    pp = placed(cores, pins, place)
    res = collections.defaultdict(list)
    for ends in conn.values():
        (ia, pa), (ib, pb) = ends
        ka = {k[2]: v for k, v in pp.items() if k[0] == ia and k[1] == pa}
        kb = {k[2]: v for k, v in pp.items() if k[0] == ib and k[1] == pb}
        for bit in set(ka) & set(kb):
            res["%s-%s" % tuple(sorted((ia, ib)))].append(abs(ka[bit][0] - kb[bit][0]) + abs(ka[bit][1] - kb[bit][1]))
    return {k: dict(bits=len(v), max=round(max(v), 2), gt405=sum(1 for x in v if x > 405)) for k, v in sorted(res.items())}, pp


def station_hops(pp):
    def win(lo, hi, n, lsb_high=False):
        xs = [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]
        return xs[::-1] if lsb_high else xs
    out = {}
    vi = [pp[("u_l3", "vi_s", str(i))] for i in range(276)]
    w = win(6.144, 66.012, 276, True)
    s = STATIONS[0]["regs_um"][0]
    out["xtier_i0"] = (max(abs(x - s[0]) + s[1] for x in w), max(abs(v[0] - s[0]) + abs(v[1] - s[1]) for v in vi))
    vo = [pp[("u_l3", "vo_s", str(i))] for i in range(276)]
    w = win(1508.16, 1568.228, 276)
    s = STATIONS[1]["regs_um"][0]
    out["xtier_o0"] = (max(abs(v[0] - s[0]) + abs(v[1] - s[1]) for v in vo), max(abs(x - s[0]) + s[1] for x in w))
    cw = [v for k, v in pp.items() if k[0] == "u_l2" and k[1] in ("cw_d", "cw_a", "cw_v")]
    s = STATIONS[2]["regs_um"][0]
    out["unit_i0"] = (max(abs(x - s[0]) + s[1] for x in (1449.024, 1506.972)),
                      max(abs(v[0] - s[0]) + abs(v[1] - s[1]) for v in cw))
    return {k: [round(a, 1), round(b, 1)] for k, (a, b) in out.items()}


def conns_entry(conn):
    ent = collections.defaultdict(dict)
    for ends in conn.values():
        (ia, pa), (ib, pb) = ends
        ent["u_gunit." + ia].setdefault(pa, []).append(f"core:u_gunit.{ib}.{pb}")
        ent["u_gunit." + ib].setdefault(pb, []).append(f"core:u_gunit.{ia}.{pa}")
    for i, p, b in (("u_l3", "vi_s", "xtier_i0"), ("u_l3", "vo_s", "xtier_o0"), ("u_l5", "vi_n", "xtier_i1"),
                    ("u_l5", "vo_n", "xtier_o1"), ("u_l2", "cw_d", "unit_i0")):
        ent["u_gunit." + i].setdefault(p, []).append(f"bus:{b}")
    return {k: {p: sorted(v) for p, v in sorted(d.items())} for k, d in sorted(ent.items())}


def splice(text, key_from, opener, new_obj, indent):
    """replace the JSON value that starts at the first `opener` after `key_from` (bracket matched)"""
    i = text.index(opener, text.index(key_from))
    j = i + len(opener) - 1
    depth = 0
    for k in range(j, len(text)):
        ch = text[k]
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                break
    body = json.dumps(new_obj, indent=1).replace("\n", "\n" + " " * indent)
    return text[:j] + body + text[k + 1:]


def apply(check_only):
    d = json.loads(PLAN.read_text())
    pt = d["partition_types"][TYPE]
    cores = {c["inst"].split(".")[-1]: c for c in pt["hard_cores"]}
    cur = {k: (c["origin_um"], c.get("orient", "R0")) for k, c in cores.items()}
    if all(cur[k] == ([round(v[0][0], 4), round(v[0][1], 4)], v[1]) for k, v in NEW.items()):
        print("already applied")
        return 0
    if any(cur[k] != (v[0], v[1]) for k, v in OLD.items()):
        raise SystemExit(f"base mismatch: {cur}")
    raws, pds = {}, {}
    for inst, c in cores.items():
        raws[inst] = (PINDIR / Path(c["pins_file"]).name).read_bytes()
        pds[inst] = json.loads(raws[inst])
    for m, h in BASE_PINHASH.items():
        inst = "u_" + m.split("_")[-1]
        if pds[inst]["pinhash"] != h:
            raise SystemExit(f"{m} pinhash {pds[inst]['pinhash']} != base {h}")
    conn = rtl_conn(cores)
    pins = {k: v["pins"] for k, v in pds.items()}
    before, _ = census(cores, pins, conn, OLD)
    pins["u_l3"] = repin_l3(pins["u_l3"])
    pins["u_l2"] = repin_l2(cores, pins, conn)
    after, pp = census(cores, pins, conn, NEW)
    hops = station_hops(pp)
    # slot fit: inside the partition, no two cores overlap
    PW, PH = pt["outline_um"]
    boxes = {k: (NEW[k][0][0], NEW[k][0][1], NEW[k][0][0] + c["outline_um"][0], NEW[k][0][1] + c["outline_um"][1])
             for k, c in cores.items()}
    for k, b in boxes.items():
        assert 0 <= b[0] and b[2] <= PW and 0 <= b[1] and b[3] <= PH, f"{k} outside partition"
        for k2, b2 in boxes.items():
            if k < k2 and b[0] < b2[2] and b2[0] < b[2] and b[1] < b2[3] and b2[1] < b[3]:
                raise SystemExit(f"overlap {k} {k2}")
    rep = dict(before=before, after=after, station_hops=hops, place=NEW,
               worst_bundle=max(v["max"] for v in after.values()))
    print(json.dumps(rep, indent=1))
    if rep["worst_bundle"] > 405 or any(max(v) > 405 for v in hops.values()):
        raise SystemExit("reach target missed")
    sys.path.insert(0, str(REPO / "tools" / "die_plan"))
    import core_pin_sites_gate
    for inst in ("u_l2", "u_l3"):
        pg = core_pin_sites_gate.check_pins(pins[inst], *cores[inst]["outline_um"])
        if pg.get("stacked_pins"):
            raise SystemExit(f"{inst}: core_pin_sites_gate {pg[counts]}")
    if check_only:
        return rep
    for inst in ("u_l2", "u_l3"):
        pd = pds[inst]
        pd["pins"] = pins[inst]
        pd["pinhash"] = hashlib.sha256(json.dumps(pd["pins"], sort_keys=True).encode()).hexdigest()[:12]
        pd["source"] += (" | S81-CORES-R25 10-27 gunit re-layout (delta_gunit_relayout_1027.py): " +
                         ("cw_* E face -> S face E end; S/N bundles re-ordered to partner x order" if inst == "u_l2"
                          else "vi_s packed core-frame E end, vo_s packed W end (0.096 M5)"))
        (PINDIR / Path(cores[inst]["pins_file"]).name).write_text(json.dumps(pd, indent=0))
    t = PLAN.read_text()
    for inst, (org, o) in NEW.items():
        row = f'"inst":"u_gunit.{inst}","module":"dsdv_gunit_{inst[2:]}"'
        i = t.index(row)
        old = f'"origin_um":[{OLD[inst][0][0]},{OLD[inst][0][1]}]'
        a = t.index(old, i)
        t = t[:a] + f'"origin_um":[{round(org[0], 4)},{round(org[1], 4)}]' + t[a + len(old):]
        old_o = '"orient":"R0","track_offset_um":[0.108,0.012]'
        a = t.index(old_o, i)
        t = t[:a] + f'"orient":"{o}","track_offset_um":{json.dumps(TOFF[o]).replace(" ", "")}' + t[a + len(old_o):]
    for c in pt["hard_cores"]:
        k = c["inst"].split(".")[-1]
        c["origin_um"] = [round(NEW[k][0][0], 4), round(NEW[k][0][1], 4)]
        c["orient"] = NEW[k][1]
        c["track_offset_um"] = TOFF[NEW[k][1]]
    # L5 clock tap follows its clk pin (MX), same x offset
    tap = next(x for x in pt["clock"]["taps"] if x["name"] == "u_gunit.u_l5")
    clk = next(p for p in pds["u_l5"]["pins"] if p["name"] == "clk")
    oldxy = list(tap["xy"])
    dx_ = round(oldxy[0] - (OLD["u_l5"][0][0] + clk["x"]), 4)
    dy_ = round(oldxy[1] - (OLD["u_l5"][0][1] + clk["y"]), 4)
    tap["xy"] = [round(B + clk["x"] + dx_, 4), round(17.28 + cores["u_l5"]["outline_um"][1] - clk["y"] + dy_, 4)]
    old_s = json.dumps(oldxy).replace(" ", "")
    s_ = t.index('"name": "u_gunit.u_l5"', t.index(f'"{TYPE}"'))
    a = t.index('"xy": [', s_)
    t = splice(t, '"name": "u_gunit.u_l5"', '"xy": [', tap["xy"], 6)
    pt["internal_stations"] = STATIONS
    t = splice(t, f'"{TYPE}"', '"internal_stations": [', STATIONS, 3)
    if json.loads(t) != d:
        raise SystemExit("text edit != intended plan")
    PLAN.write_text(t)
    cc = json.loads(CONNS.read_text())
    cc[TYPE] = conns_entry(conn)
    CONNS.write_text(json.dumps(cc, indent=0) + ("\n" if CONNS.read_text().endswith("\n") else ""))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = apply(a.check)
    if a.json and isinstance(r, dict):
        Path(a.json).write_text(json.dumps(r, indent=1))
