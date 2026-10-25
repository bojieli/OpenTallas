#!/usr/bin/env python3
"""KV-PLAN3 10-25 (plan v3.9e = v3.9d + this pass): the batched KV plan items that are not channel geometry.

Runs on the geom_v39d.py output (die_plan_geom.json + its cores/ copy), before chan_windows.py re-windows the ports.

(1) ECTLK quarter pins (COORD KV RULING 10-25 05:07 (c) + KV-CORES RULING 05:28 (1)): qkd_ectlk_q0..q3 get their REAL
    pin tables from the four-column RTL (codex/kv-ectlk-1025 ectlk_columns.py, lockstep miter vs the legacy ectlk PASS,
    0 mismatches / 8580 edges): output bits = the quarter's own output cone, input bits = the inputs that stay live
    after synthesis of that quarter (ectlk_live.json), approved pin drop applied (so 413->271, req_v gone, req_t 14->13,
    si 633->537).  Placement per quarter and face: each pin keeps its legacy face and layer; pins of one face are
    spread in legacy order over the quarter face (track pitch kept); a face over capacity spills onto the side faces
    (W/E) toward the source.  One clock pin ck (N-face centre) + rst_n per quarter.
(2) am g drop (KV-CORES RULING 05:28 (2); KV-TOK 05:36: g == 0 for every scheduled op): the four ahub -> astk am
    buses lose bit 1 (36 -> 35 b): old bit 0 -> 0, old 2..35 -> 1..34.  Ports, type buses, ft slots, internal stations
    and the ahub / astk core pins.  RTL side (ahub drops the constant, ASTK G_CONST=0 parameter) = KV-CORES dependency.
(3) reset.start = "broadcast" (OWNER DECISION 13c, CLOCK-RESET per-die delta, main 577932a17).
usage: post_v39e.py PLAN_GEOM.json --cores DIR [--ectlk-sv SV --ectlk-live JSON] --report R.json  (in place)
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

AM_BUSES = ("ahub_am_EN", "ahub_am_ES", "ahub_am_WN", "ahub_am_WS")
G_BIT = 1


def am_map(b):
    """old am bit -> new bit (None = dropped g)"""
    return None if b == G_BIT else (b if b < G_BIT else b - 1)


def drop_am(raw, cores, rep):
    T = raw["partition_types"]
    nb = 0
    for tn, t in T.items():
        for b in t.get("buses", []):
            if any(b["name"].endswith(x) for x in AM_BUSES) and b["width"] == 36:
                b["width"] = 35
                nb += 1
    # ports carrying am (functional end or ft slot hop); the slot names they use
    slots = set()
    np_ = 0
    for p in raw["ports"]:
        ends = (p["src"].get("bus", ""), p["dst"].get("bus", ""))
        lane_am = any(any(e.endswith(x) for x in AM_BUSES) for e in ends)
        if not lane_am:
            continue
        p["width"] = 35
        np_ += 1
    # follow lanes: every port of a lane that has an am port
    am_ports = {p["id"] for p in raw["ports"] if p["width"] == 35 and
                any(any(p[k].get("bus", "").endswith(x) for x in AM_BUSES) for k in ("src", "dst"))}
    pid = {p["id"]: p for p in raw["ports"]}
    for L in raw["lanes"]:
        if am_ports & set(L["ports"]):
            for q in L["ports"]:
                p = pid[q]
                if p["width"] == 36:
                    p["width"] = 35
                    np_ += 1
                for k in ("src", "dst"):
                    m = re.match(r"^(ft\d+)_[io]$", p[k].get("bus", ""))
                    if m:
                        slots.add((p[k]["part"], m.group(1)))
    ptype = {p["name"]: p["type"] for p in raw["partitions"]} if isinstance(raw["partitions"], list) else \
        {k: v["type"] for k, v in raw["partitions"].items()}
    ns = 0
    for part, sn in sorted(slots):
        for s in T[ptype[part]].get("ft_slots", []):
            if s["name"] == sn and s["width"] == 36:
                s["width"] = 35
                ns += 1
                for k in ("bit_sites_um",):
                    if s.get(k):
                        s[k] = [[xy for i, xy in enumerate(st) if i != G_BIT] for st in s[k]]
    ni = 0
    for tn, t in T.items():
        for st in t.get("internal_stations", []) or []:
            if any(st.get("conn", "").endswith(x) for x in AM_BUSES) and st.get("bits") == 36:
                st["bits"] = 35
                ni += 1
    # core pins
    npin = 0
    for fn in sorted(Path(cores).glob("*_pins.json")):
        d = json.loads(fn.read_text())
        pat = re.compile(r"^(am[0-3]|u_strip_u_strip_u_ctl__am)\[(\d+)\]$") if fn.name in (
            "qkd_ahub_pins.json",) or fn.name.startswith("kv3_astk_") else None
        if pat is None:
            continue
        out, ch = [], 0
        for p in d["pins"]:
            m = pat.match(p["name"])
            if m:
                nbit = am_map(int(m.group(2)))
                ch += 1
                if nbit is None:
                    continue
                p = dict(p, name=f"{m.group(1)}[{nbit}]")
            out.append(p)
        if ch:
            d["pins"] = out
            if isinstance(d.get("faces"), dict):
                for f in d["faces"].values():
                    f["pins"] = None
                fc = defaultdict(int)
                for p in out:
                    fc[face_of(p, d)] += 1
                for f, v in d["faces"].items():
                    v["pins"] = fc.get(f, 0)
            d["source"] = (d.get("source", "") + " | KV-PLAN3 v3.9e: am g bit dropped (36 -> 35 b, old 0 -> 0, "
                           "old 2..35 -> 1..34; KV-CORES RULING 10-25 05:28 (2))")
            fn.write_text(json.dumps(d, indent=0) + "\n")
            npin += ch
    rep["am_g_drop"] = dict(type_buses=nb, ports=np_, ft_slots=ns, internal_stations=ni, core_pin_bits_touched=npin,
                            mapping="old0->0, old1 (g) dropped, old2..35->new1..34")


def outline_of(d):
    m = re.search(r"outline ([\d.]+) x ([\d.]+)", d.get("frame", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (None, None)


def face_of(p, d):
    w, h = outline_of(d)
    if p["y"] <= 0.2:
        return "S"
    if h is not None and p["y"] >= h - 0.2:
        return "N"
    if p["x"] <= 0.2:
        return "W"
    return "E"


OFFS = dict(M4=(0.024, 0.048), M5=(0.024, 0.048), M6=(0.032, 0.064), M7=(0.032, 0.064))


def snap(v, layer):
    off, pitch = OFFS[layer]
    return round(off + round((v - off) / pitch) * pitch, 6)


def die_tracks(pins, w, h):
    """snap every M4-M7 face pin onto the DIE symmetric track (offset pitch/2, gen_core_kit_kv.py) along its face;
    collisions move to the next free track.  Returns the max shift (um)."""
    seen, out, mx = set(), [], 0.0
    for p in pins:
        if p["layer"] not in OFFS:
            out.append(p)
            continue
        f = "S" if p["y"] <= 0.2 else "N" if p["y"] >= h - 0.2 else "W" if p["x"] <= 0.2 else "E"
        k = "x" if f in "SN" else "y"
        lim = w if k == "x" else h
        v = snap(p[k], p["layer"])
        pitch = OFFS[p["layer"]][1]
        key = (p["layer"], f, round(v, 4))
        while key in seen:
            v = round(v + pitch, 6)
            key = (p["layer"], f, round(v, 4))
        if v > lim - 0.024:
            raise SystemExit(f"die_tracks: {p['name']} off the {f} face")
        seen.add(key)
        mx = max(mx, abs(v - p[k]))
        out.append(dict(p, **{k: v}))
    return out, round(mx, 4)


def pv_join_snap(cores, rep):
    """pv_join_t (reused 10-19 LEF pins, platform offset 0.012) -> die symmetric tracks (<= 0.012 um per pin) so
    gen_core_kit_kv accepts the re-kit with the +513 FF port-copy fix (CODEX-LOG 06:06 KV PC boundary / PV join)."""
    fn = Path(cores) / "pv_join_pins.json"
    d = json.loads(fn.read_text())
    w, h = outline_of(d)
    d["pins"], mx = die_tracks(d["pins"], w, h)
    d["source"] += " | KV-PLAN3 v3.9e: M4-M7 pins snapped to the die symmetric tracks (offset pitch/2)"
    fn.write_text(json.dumps(d, indent=0) + "\n")
    rep["pv_join_snap"] = dict(pins=len(d["pins"]), max_shift_um=mx)


KVS_CTL_SIDE = 371.52   # 43 x 8.64: ~61 % of the 475.2^2 outline (GEOM-REVIEW-2 05:45: ~60 %, faces next to the fan tree)


def kvs_ctl_reoutline(raw, cores, rep):
    """qkd_kvs_ctl 475.2^2 -> 371.52^2, same centre in kv3_hub_C; pins keep face, layer and order (scaled along the
    face, die symmetric tracks).  GEOM-REVIEW-2 05:45 FAIL (S half ~70 % empty, fan tree 150-250 um to each face)."""
    fn = Path(cores) / "kvs_ctl_pins.json"
    d = json.loads(fn.read_text())
    W0, H0 = outline_of(d)
    S = KVS_CTL_SIDE
    pins = []
    for p in d["pins"]:
        f = "S" if p["y"] <= 0.2 else "N" if p["y"] >= H0 - 0.2 else "W" if p["x"] <= 0.2 else "E"
        if f in "SN":
            q = dict(p, x=p["x"] * S / W0, y=p["y"] if f == "S" else S - (H0 - p["y"]))
        else:
            q = dict(p, y=p["y"] * S / H0, x=p["x"] if f == "W" else S - (W0 - p["x"]))
        pins.append(q)
    pins.sort(key=lambda p: (p["layer"], p["x"], p["y"]))
    d["pins"], mx = die_tracks(pins, S, S)
    d["frame"] = d["frame"].replace(f"outline {W0:g} x {H0:g}", f"outline {S:g} x {S:g}")
    if f"outline {S:g} x {S:g}" not in d["frame"]:
        d["frame"] = f"core R0, origin (0,0), outline {S} x {S}"
    d["source"] = d.get("source", "") + (f" | KV-PLAN3 v3.9e: outline {W0:g}^2 -> {S:g}^2 (GEOM-REVIEW-2 05:45), pins "
                                         "scaled along their face, die symmetric tracks")
    fn.write_text(json.dumps(d, indent=0) + "\n")
    n = 0
    for tn, t in raw["partition_types"].items():
        for c in t.get("hard_cores", []) or []:
            if c.get("module") == "qkd_kvs_ctl":
                dx = (c["outline_um"][0] - S) / 2
                dy = (c["outline_um"][1] - S) / 2
                c["origin_um"] = [round(c["origin_um"][0] + dx, 4), round(c["origin_um"][1] + dy, 4)]
                c["outline_um"] = [S, S]
                c["note"] = (c.get("note", "") + " | KV-PLAN3 v3.9e: re-outlined 475.2^2 -> 371.52^2, same centre "
                             "(GEOM-REVIEW-2 05:45 FAIL: S half ~70 % empty)").strip(" |")
                n += 1
    rep["kvs_ctl_reoutline"] = dict(instances=n, outline=[S, S], pins=len(d["pins"]), area_frac=round(S * S / W0 / H0, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--cores", required=True)
    ap.add_argument("--ectlk-sv")
    ap.add_argument("--ectlk-live")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    rep = {}
    drop_am(raw, a.cores, rep)
    pv_join_snap(a.cores, rep)
    kvs_ctl_reoutline(raw, a.cores, rep)
    raw["reset"]["start"] = "broadcast"
    rep["reset_start"] = "broadcast"
    if a.ectlk_sv:
        import ectlk_quarters
        rep["ectlk_quarters"] = ectlk_quarters.build(raw, a.cores, a.ectlk_sv, a.ectlk_live)
    raw["note"] = ("KV plan v3.9e (KV-PLAN3 10-25) = v3.9d (pv column +259.2, channel-mouth pins, ectlk quarters) + "
                   "ECTLK quarter real pins (approved pin drop) + am g drop + reset.start broadcast + G2-proven "
                   "per-type face budgets. " + raw.get("note", ""))
    Path(a.plan).write_text(json.dumps(raw, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("post_v39e:", json.dumps(rep))


if __name__ == "__main__":
    main()
