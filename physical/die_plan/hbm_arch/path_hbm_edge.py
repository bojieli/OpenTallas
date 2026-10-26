#!/usr/bin/env python3
"""PATH-HBM/EDGE 10-25: one coherent NW_hub->root structural answer (COORD Q1/Q2 + the failing NW_b101 G2).

    python3 path_hbm_edge.py --src <R1DELTA plan_cond dir> --out <new plan dir> [--grow 501.12]

Inputs: the R1DELTA plan (HUBNW3 q_hub_nw split, lanes right-sized to traced real bits, TKM leg repeaters).
Problem: R1DELTA laned the 2,740 real NW_hub->root idx bits as L156 (1455 b direct) + L157 (1285 b via NW_b101), and the
selected TKM L74 (1171 b x 2 beats) still crosses NW_b101, whose G2 probe FAILS (overflow 4.26 M, displaced FT).
Answer (no traffic through NW_b101 on either path):
  E1  remove R1DELTA L156 / L157 (ports, end buses, b101 slot L157x1, typed chains, core_conns, latency rows).
  E2  grow the die by GROW at y = 8484.48 (top of the NW hub row; path_hbm_idx_edge.py rules: 13 types end there and
      stretch at their N edge, every part above translates, root keeps its frame and grows at its top, so the TKM array,
      its clock corridor and every core stay fixed in their partition frames).
  E3  L156 = ONE dedicated registered, landed 2,740 b lane NW_hub E -> root W in the new band (all 8 vm_rr banks +
      ctl.cr + argmax.cr + index_rq, exact as-built map), typed root/hub endpoint chains.
  E4  L74 (TKM, selected path) direct NW_hub E -> root W in the LOW free stretch of the shared face that R1DELTA's L156
      vacated (bottom of the face, ~0.4-0.6 mm above u_tkx_rx_SW), NW_b101 slot L74x1 removed, typed L74_i -> RX chain.
      Rationale vs the 725.76 two-window band: a band window lands the TKM bus at root y >= 4153 (frame), 2.8 mm above
      the RX FIRM site (y 1010-1356) -> ~8 extra stations in the root W channel for nothing, plus +6.4 mm2.
  E5  every internal chain whose bus target moved is re-stationed (hops <= 360, 405 fallback, never in a hard core).
  E6  inline die.io + PG domains (rect and bump rect) of translated parts follow the growth (die_io.json sidecar too),
      clock spine root y re-centred is NOT done here (CLOCK owns the H-tree; reported stale).
"""
import argparse, collections, copy, json, os, re, shutil, sys, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
import b2n as B  # noqa: E402
import cores_b2 as CB  # noqa: E402
import path_hbm_r1delta as R  # noqa: E402

CUT = 8484.48
BANK = 257
HUB, ROOT_T = "q_hub_nw", "root"
B101 = "q_b101_nw"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def remove_lane(plan, cc, lid, rep):
    T = plan["partition_types"]
    parts = {p["name"]: p for p in plan["partitions"]}
    L = next(l for l in plan["lanes"] if l["id"] == lid)
    ports = [next(p for p in plan["ports"] if p["id"] == pid) for pid in L["ports"]]
    P0 = S.Plan(plan)
    slots = list(B._lane_slots(P0, lid))
    gone = dict(ports=L["ports"], width=ports[0]["width"], buses=[], slots=[], stations=0, cc=0)
    ends = [(parts[ports[0]["src"]["part"]]["type"], ports[0]["src"]["bus"]),
            (parts[ports[-1]["dst"]["part"]]["type"], ports[-1]["dst"]["bus"])]
    for tn, nm in ends:
        T[tn]["buses"] = [b for b in T[tn]["buses"] if b["name"] != nm]
        ist = T[tn].get("internal_stations", [])
        n0 = len(ist)
        T[tn]["internal_stations"] = [e for e in ist if e.get("conn") != f"bus:{nm}"]
        gone["stations"] += n0 - len(T[tn]["internal_stations"])
        for core, cp in cc.get(tn, {}).items():
            for port in list(cp):
                k0 = len(cp[port])
                cp[port] = [x for x in cp[port] if x != f"bus:{nm}"]
                gone["cc"] += k0 - len(cp[port])
                if not cp[port]:
                    del cp[port]
        gone["buses"].append(f"{tn}.{nm}")
    for part, sn in slots:
        tn = parts[part]["type"]
        T[tn]["ft_slots"] = [s for s in T[tn]["ft_slots"] if s["name"] != sn]
        gone["slots"].append(f"{tn}.{sn}")
    plan["lanes"] = [l for l in plan["lanes"] if l["id"] != lid]
    plan["ports"] = [p for p in plan["ports"] if p["id"] not in L["ports"]]
    plan["latency"]["lanes"].pop(lid, None)
    rep["removed"][lid] = gone


def grow(plan, G, rep):
    """path_hbm_idx_edge.py growth (no lane added). Returns (P_before, stretched types, shifted parts)."""
    raw = plan
    P0 = S.Plan(copy.deepcopy(raw))
    d = raw["die"]["outline_um"]
    area0 = d[0] * d[1]
    endtypes, shiftparts = set(), []
    for p in raw["partitions"]:
        h = raw["partition_types"][p["type"]]["outline_um"][1]
        if abs(p["origin_um"][1] + h - CUT) < 1e-6:
            endtypes.add(p["type"])
        elif p["origin_um"][1] >= CUT - 1e-6:
            shiftparts.append(p["name"])
        elif p["origin_um"][1] < CUT < p["origin_um"][1] + h and p["name"] != "root":
            raise ValueError("unexpected straddling partition " + p["name"])
    for p in raw["partitions"]:
        if p["type"] in endtypes and abs(p["origin_um"][1] + P0.types[p["type"]]["outline_um"][1] - CUT) > 1e-6:
            raise ValueError("type requires explicit split " + p["type"])
    oldt = {tn: copy.deepcopy(raw["partition_types"][tn]) for tn in endtypes | {"root"}}
    for p in raw["partitions"]:
        if p["name"] in shiftparts:
            p["origin_um"][1] = round(p["origin_um"][1] + G, 6)
    for tn in oldt:
        raw["partition_types"][tn]["outline_um"][1] = round(oldt[tn]["outline_um"][1] + G, 6)
    raw["die"]["outline_um"][1] = round(d[1] + G, 6)
    for p in raw["ports"]:
        if p["face"] in ["E", "W"] and p["window_um"][0] >= CUT - 1e-6:
            p["window_um"] = [round(v + G, 6) for v in p["window_um"]]
        elif p["face"] in ["E", "W"] and p["window_um"][0] < CUT < p["window_um"][1]:
            raise ValueError("straddling port window " + p["id"])
    slots = []
    P1 = S.Plan(raw)
    for tn, ty in oldt.items():
        bt0 = CK._bus_targets(P0, tn)
        bt1 = CK._bus_targets(P1, tn)
        for old in ty.get("ft_slots", []):
            s = next(s for s in raw["partition_types"][tn]["ft_slots"] if s["name"] == old["name"])
            a, b = tuple(bt0[s["name"] + "_i"][1]), tuple(bt0[s["name"] + "_o"][1])
            aa, bb = tuple(bt1[s["name"] + "_i"][1]), tuple(bt1[s["name"] + "_o"][1])
            da = [round(aa[i] - a[i], 6) for i in range(2)]
            db = [round(bb[i] - b[i], 6) for i in range(2)]
            if da == db == [0., 0.]:
                continue
            n = old["stations"]
            line = CK.zroute(a, b, old["in_face"], old["out_face"])
            Ln = CK.plen(line)
            regs = copy.deepcopy(old.get("regs_um") or [list(CK.point_at(line, Ln * k / n)) for k in range(n)])
            if da == db:
                regs = [[round(p[i] + da[i], 6) for i in range(2)] for p in regs]
                if s.get("bit_sites_um"):
                    s["bit_sites_um"] = [[[round(p[i] + da[i], 6) for i in range(2)] for p in st]
                                         for st in s["bit_sites_um"]]
                stale, mode = [], "rigid slot translation; depth unchanged"
            else:
                if da != [0., 0.]:
                    regs = [list(aa), [(aa[i] + a[i]) / 2 for i in range(2)]] + regs
                if db != [0., 0.]:
                    regs += [list(b), [(bb[i] + b[i]) / 2 for i in range(2)]]
                stale = [k for k in ["bit_sites_um", "bit_site_cell_um"] if k in s]
                for k in stale:
                    s.pop(k)
                mode = "extra registered top-band hops; exact new per-bit sites required"
            s["regs_um"] = regs
            s["stations"] = len(regs)
            slots.append(dict(type=tn, slot=s["name"], stations_before=n, stations_after=len(regs),
                              input_delta_um=da, output_delta_um=db, mode=mode, explicit_sites_need_refresh=stale))
    rep["growth"] = dict(cut_y_um=CUT, growth_um=G, area_before_mm2=area0 / 1e6,
                         area_after_mm2=raw["die"]["outline_um"][0] * raw["die"]["outline_um"][1] / 1e6,
                         area_added_mm2=raw["die"]["outline_um"][0] * G / 1e6, stretched_types=sorted(oldt),
                         shifted_partitions=shiftparts, slot_changes=slots)
    # E6 inline die.io + PG domains (rect + bumps) of translated parts
    io_moved, pg_moved = [], []
    sp = set(shiftparts)
    for row in raw["die"].get("io", []):
        r = row["rect_um"]
        if row.get("part") in sp:
            row["rect_um"] = [r[0], round(r[1] + G, 6), r[2], round(r[3] + G, 6)]
            io_moved.append(row["name"])
        elif r[1] < CUT < r[3]:
            raise ValueError("io rect straddles the cut " + row["name"])
    for dm in raw["die"].get("pg", {}).get("domains", []):
        ios = set(dm.get("io", []))
        mv = ios & set(io_moved)
        if mv and mv != ios:
            raise ValueError("pg domain mixes moved/unmoved io " + dm["name"])
        r = dm["rect_um"]
        if mv:
            dm["rect_um"] = [r[0], round(r[1] + G, 6), r[2], round(r[3] + G, 6)]
            if "bumps" in dm and "rect_um" in dm["bumps"]:
                b = dm["bumps"]["rect_um"]
                dm["bumps"]["rect_um"] = [b[0], round(b[1] + G, 6), b[2], round(b[3] + G, 6)]
            pg_moved.append(dm["name"])
        elif r[1] < CUT < r[3]:
            raise ValueError("pg domain straddles the cut " + dm["name"])
    rep["growth"]["inline_io_moved"] = io_moved
    rep["growth"]["inline_pg_domains_moved"] = pg_moved
    return P0, set(oldt), sp


def free_seg(plan, a, b, face):
    P1 = S.Plan(plan)
    line, lo, hi = CK.face_line(P1.rect(a), face)
    _, lo2, hi2 = CK.face_line(P1.rect(b), S.OPP[face])
    lo, hi = max(lo, lo2), min(hi, hi2)
    ws = sorted(p["window_um"] for p in plan["ports"] if {p["src"]["part"], p["dst"]["part"]} == {a, b})
    prev, gaps = lo + 0.5, []
    for w in ws:
        gaps.append((prev, w[0] - B.GAP))
        prev = w[1] + B.GAP
    gaps.append((prev, hi - 0.5))
    return gaps


def world_cores(plan):
    T = plan["partition_types"]
    out = {}
    for p in plan["partitions"]:
        t = T[p["type"]]
        w, h = t["outline_um"]
        for c in t.get("hard_cores", []):
            o = c["origin_um"]
            # orientation-independent anchor: R0 / MY only keep y; MY mirrors x about the partition
            x = p["origin_um"][0] + (o[0] if p.get("orient", "R0") in ("R0", "MX") else w - o[0] - c["outline_um"][0])
            y = p["origin_um"][1] + (o[1] if p.get("orient", "R0") in ("R0", "MY") else h - o[1] - c["outline_um"][1])
            out[(p["name"], c["inst"])] = (round(x, 4), round(y, 4), c["module"], tuple(c["outline_um"]),
                                           c.get("pins_file"), tuple(c.get("track_offset_um", [0, 0])))
    return out


def apply(plan, out, cc, G):
    T = plan["partition_types"]
    rep = dict(removed={}, new={}, moved={}, restation={}, open=[])
    lat0 = copy.deepcopy(plan["latency"]["lanes"])
    W0 = world_cores(plan)
    st0 = {tn: {(e.get("conn"), e.get("launch"), e.get("capture")): len(e.get("regs_um", []))
                for e in T[tn].get("internal_stations", [])} for tn in (ROOT_T, HUB)}
    # ------------------------------------------------ E1
    for lid in ("L156", "L157"):
        remove_lane(plan, cc, lid, rep)
    # ------------------------------------------------ E2 (+E6)
    Pg0, stretched, shifted = grow(plan, G, rep)
    bt_pre = {tn: CK._bus_targets(Pg0, tn) for tn in T}
    # ------------------------------------------------ E4: L74 direct, low on the NW_hub E / root W face
    ports = {p["id"]: p for p in plan["ports"]}
    L74 = next(l for l in plan["lanes"] if l["id"] == "L74")
    assert L74["ports"] == ["L74_0", "L74_1"], L74["ports"]
    p0, p1 = ports["L74_0"], ports["L74_1"]
    assert p0["dst"]["part"] == "NW_b101" and p1["src"]["part"] == "NW_b101"
    w74 = int(p0["width"])
    old74 = dict(L74_0=dict(face=p0["face"], window=p0["window_um"], dst="NW_b101"),
                 L74_1=dict(face=p1["face"], window=p1["window_um"], src="NW_b101"))
    plan["ports"] = [p for p in plan["ports"] if p["id"] != "L74_1"]
    T[B101]["ft_slots"] = [s for s in T[B101]["ft_slots"] if s["name"] != "L74x1"]
    gaps = free_seg({**plan, "ports": [p for p in plan["ports"] if p["id"] != "L74_0"]}, "NW_hub", "root", "E")
    need = R.need_len(w74)
    segs = [g for g in gaps if g[1] - g[0] >= need - 1e-6]
    s0, s1 = segs[0]
    p0["dst"] = dict(part="root", bus="L74_i")
    p0["face"] = "E"
    p0["layers"] = list(B.FACE_LAYERS["E"])
    p0["window_um"] = [B.snap(s0), B.snap(s0 + need)]
    p0["note"] = (p0.get("note", "") + " | PATH-HBM/EDGE 10-25: direct NW_hub E -> root W, lowest free stretch of the "
                  "shared face (vacated by R1DELTA L156), next to u_tkx_rx_SW; NW_b101 no longer on the TKM path")
    L74["ports"] = ["L74_0"]
    L74["note"] = L74.get("note", "") + " | PATH-HBM/EDGE 10-25: direct (NW_b101 L74x1 slot removed)"
    rep["moved"]["L74"] = dict(old=old74, new=dict(L74_0=dict(face="E", window=p0["window_um"], dst="root")),
                               free_gaps=gaps, need_um=need)
    # ------------------------------------------------ E3: L156 2740 direct in the band
    need156 = R.need_len(2740)
    lo = B.snap(CUT + (G - need156) / 2)
    win156 = [lo, B.snap(lo + need156)]
    if not (CUT + B.GAP <= win156[0] and win156[1] <= CUT + G - B.GAP):
        raise ValueError(f"L156 window {win156} does not fit the band")
    plan["ports"].append(dict(id="L156_0", src=dict(part="NW_hub", bus="L156_o"), dst=dict(part="root", bus="L156_i"),
                              width=2740, kind="data", face="E", layers=list(B.FACE_LAYERS["E"]), window_um=win156,
                              note="PATH-HBM/EDGE 10-25 (COORD Q1 15:56): dedicated registered, landed NW_hub->root "
                                   "idx lane, real as-built bits only, in the new edge band"))
    plan["lanes"].append(dict(id="L156", ports=["L156_0"],
                              note="NW_hub->root idx return data (PATH-HBM/EDGE 10-25, COORD Q1): ctl.cr 274 + "
                                   "argmax.cr 274 + ctl.index_rq 136 + vm_rr 8 banks x 257 = 2740"))
    T[HUB]["buses"].append(dict(name="L156_o", dir="out", width=2740, kind="data"))
    T[ROOT_T]["buses"].append(dict(name="L156_i", dir="in", width=2740, kind="data"))
    P2 = S.Plan(plan)
    bt2 = {tn: CK._bus_targets(P2, tn) for tn in T}
    # ------------------------------------------------ E5: internal chains whose bus target moved
    for tn, t in T.items():
        route = None
        for e in t.get("internal_stations", []):
            c = e.get("conn", "")
            if not c.startswith("bus:"):
                continue
            bn = c[4:]
            if bn not in bt_pre[tn] or bn not in bt2[tn]:
                continue
            o, n = bt_pre[tn][bn][1], bt2[tn][bn][1]
            if abs(o[0] - n[0]) + abs(o[1] - n[1]) < 1e-3:
                continue
            nn = [round(n[0], 3), round(n[1], 3)]
            face_is_from = abs(e["from_um"][0] - o[0]) + abs(e["from_um"][1] - o[1]) < 1e-3
            face_is_to = abs(e["to_um"][0] - o[0]) + abs(e["to_um"][1] - o[1]) < 1e-3
            if face_is_from:
                e["from_um"] = nn
            if face_is_to:
                e["to_um"] = nn
            n_old = len(e["regs_um"])
            dv = (round(n[0] - o[0], 3), round(n[1] - o[1], 3))
            if tn in stretched and dv[0] == 0 and abs(dv[1] - G) < 1e-3:
                # N-face target moved straight up through the new (empty) band: keep the chain, extend it along the
                # straight free segment old target -> new target with the fewest stations (hops <= 360)
                regs = [list(p) for p in e["regs_um"]]
                if face_is_from:
                    regs = list(reversed(regs))          # core -> face order
                last = regs[-1] if regs else (e["from_um"] if face_is_from else e["to_um"])
                if not regs:
                    last = e["from_um"] if not face_is_from else e["to_um"]
                h0 = abs(last[0] - o[0]) + abs(last[1] - o[1])
                tot = h0 + G
                k = max(0, -(-tot // B.HOP) - 1) if h0 <= B.HOP else max(1, -(-G // B.HOP))
                if h0 <= B.HOP:
                    ext = [[round(o[0], 3), round(o[1] + max(0.0, j * B.HOP - h0), 3)] for j in range(1, int(k) + 1)]
                else:                                  # 405 fallback hop: first new station on the old target
                    ext = [[round(o[0], 3), round(o[1] + j * G / k, 3)] for j in range(0, int(k))]
                regs = regs + ext
                if face_is_from:
                    regs = list(reversed(regs))
                e["regs_um"] = regs
                e["note"] = e.get("note", "") + f" | EDGE +{len(ext)} band station(s) (N face +{G:g} um)"
            elif R.hopmax(e) > B.REACH - 1.0:
                if route is None:
                    route, bx = R.routers(t)
                core_end = e["to_um"] if face_is_from else e["from_um"]
                regs = route(tuple(n), tuple(core_end))
                e["regs_um"] = [[round(v, 3) for v in p] for p in (regs if face_is_from else list(reversed(regs)))]
                e["note"] = e.get("note", "") + " | EDGE re-stationed (bus target moved)"
            rep["restation"].setdefault(tn, []).append(dict(conn=c, launch=e.get("launch"), capture=e.get("capture"),
                                                           stations=[n_old, len(e["regs_um"])],
                                                           worst_hop=round(R.hopmax(e), 1)))
    # ------------------------------------------------ E3 typed endpoints of L156 (exact as-built map)
    root_t, hub_t = T[ROOT_T], T[HUB]
    rpins, hpins = R.pins_of(out, root_t), R.pins_of(out, hub_t)
    rows = [("u_hb_idx__ctl", "cr", 0, 273, "u_hb_vms_Q", "cr", 274, 547),
            ("u_hb_argmax", "cr", 0, 273, "u_hb_vms_Q", "cr", 0, 273),
            ("u_hb_idx__ctl", "index_rq", 0, 135, "u_hb_idx__op_Q", "vm_rq", 0, 135)] + \
           [("u_hb_idx__ctl", "vm_rr", k * BANK, (k + 1) * BANK - 1, f"u_vmb_Q{k}", "rr4", 0, BANK - 1)
            for k in range(8)]
    assert sum(r[3] - r[2] + 1 for r in rows) == 2740
    rr_route, rbx = R.routers(root_t)
    hr_route, hbx = R.routers(hub_t)
    gr, gh = collections.defaultdict(list), collections.defaultdict(list)
    nm = rep["new"]["L156"] = dict(window=win156, width=2740, map=[], hub_open=[])
    at = 0
    for (rc, rp, plo, phi, hc, hp, hlo, hhi) in rows:
        n = phi - plo + 1
        nm["map"].append(dict(bits=f"[{at + n - 1}:{at}]", root=f"{rc}.{rp}[{phi}:{plo}]", hub=f"{hc}.{hp}[{hhi}:{hlo}]"))
        at += n
        d = rpins[rc][0].get(rp)
        if d is None or any(b not in d for b in range(plo, phi + 1)):
            raise ValueError(f"root {rc}.{rp}[{phi}:{plo}] has no pins")
        gr[(rc, rp)] += list(range(plo, phi + 1))
        hd = hpins.get(hc, ({}, {}))[0].get(hp)
        if hd is None or any(b not in hd for b in range(hlo, hhi + 1)):
            nm["hub_open"].append(f"{hc}.{hp}[{hhi}:{hlo}]: no such port on the q_hub_nw core "
                                  f"({[h['module'] for h in hub_t['hard_cores'] if h['inst'] == hc]})")
            continue
        gh[(hc, hp)] += list(range(hlo, hhi + 1))
    for (rc, rp), bl in sorted(gr.items()):
        cc[ROOT_T].setdefault(rc, {}).setdefault(rp, []).append("bus:L156_i")
        d, f = rpins[rc]
        e, _ = R.chain_entry(root_t, rr_route, rbx, rc, rp, bl, d, f, "L156_i", bt2[ROOT_T], "in", "EDGE L156")
        if e:
            e["note"] = e["note"].replace("R1DELTA", "EDGE")
            root_t["internal_stations"].append(e)
    for (hc, hp), bl in sorted(gh.items()):
        cc[HUB].setdefault(hc, {}).setdefault(hp, []).append("bus:L156_o")
        d, f = hpins[hc]
        e, _ = R.chain_entry(hub_t, hr_route, hbx, hc, hp, bl, d, f, "L156_o", bt2[HUB], "out", "EDGE L156")
        if e:
            e["note"] = e["note"].replace("R1DELTA", "EDGE")
            hub_t["internal_stations"].append(e)
    nm["root_chains"] = [dict(capture=e["capture"], bits=e["bits"], stations=len(e["regs_um"]),
                              worst_hop=round(R.hopmax(e), 1))
                         for e in root_t["internal_stations"] if e["conn"] == "bus:L156_i"]
    nm["hub_chains"] = [dict(launch=e["launch"], bits=e["bits"], stations=len(e["regs_um"]),
                             worst_hop=round(R.hopmax(e), 1))
                        for e in hub_t["internal_stations"] if e["conn"] == "bus:L156_o"]
    # ------------------------------------------------ E4 typed L74_i -> u_tkx_rx_SW (FIRM soft site, W face del_flit)
    rx = next(c for c in root_t["contents"] if c["inst"] == "u_tkx_rx_SW")
    ro, rs = rx["origin_um"], rx["outline_um"]
    Bp = tuple(bt2[ROOT_T]["L74_i"][1])
    tgt = (ro[0], min(max(Bp[1], ro[1]), ro[1] + rs[1]))          # nearest point of the RX W face
    dist = abs(tgt[0] - Bp[0]) + abs(tgt[1] - Bp[1])
    root_t["internal_stations"] = [e for e in root_t["internal_stations"] if e.get("conn") != "bus:L74_i"]
    if dist > B.HOP:
        regs = rr_route(Bp, tgt)
        e = dict(conn="bus:L74_i", from_um=[round(Bp[0], 3), round(Bp[1], 3)], to_um=[round(tgt[0], 3), round(tgt[1], 3)],
                 regs_um=[[round(v, 3) for v in p] for p in regs], bits=w74, launch="face bus L74_i",
                 capture="u_tkx_rx_SW.beat",
                 note=f"PATH-HBM/EDGE 10-25 typed endpoint (in): L74_i -> RX FIRM W face, {dist:.0f} um, "
                      f"{len(regs)} station(s), hops <= {B.HOP:g} um")
        root_t["internal_stations"].append(e)
        rep["new"]["L74_i_chain"] = dict(dist_um=round(dist, 1), stations=len(regs), worst_hop=round(R.hopmax(e), 1))
    else:
        rep["new"]["L74_i_chain"] = dict(dist_um=round(dist, 1), stations=0)
    # ------------------------------------------------ latency + invariants
    P = S.Plan(plan)
    key = lambda d: None if d is None else (d.get("cycles"), d.get("word_cycles"), d.get("stations"), d.get("faces"))  # noqa: E731
    plan["latency"]["lanes"] = {lid: P.lane_latency(lid) for lid in P.lanes}
    rep["lane_changes"] = {lid: dict(before=lat0.get(lid), after=plan["latency"]["lanes"].get(lid))
                           for lid in sorted(set(lat0) | set(plan["latency"]["lanes"]))
                           if key(lat0.get(lid)) != key(plan["latency"]["lanes"].get(lid))}
    st1 = {tn: {(e.get("conn"), e.get("launch"), e.get("capture")): len(e.get("regs_um", []))
                for e in T[tn].get("internal_stations", [])} for tn in (ROOT_T, HUB)}
    rep["chain_changes"] = {tn: [dict(chain=list(k), before=st0[tn].get(k), after=st1[tn].get(k))
                                 for k in sorted(set(st0[tn]) | set(st1[tn]), key=str)
                                 if st0[tn].get(k) != st1[tn].get(k)] for tn in st1}
    summ = {}
    for tn, rows_ in rep["chain_changes"].items():
        by = collections.defaultdict(lambda: [0, 0, 0, 0])
        for r in rows_:
            b_ = r["chain"][0]
            v = by[b_]
            v[0] += 1
            v[1] += (r["after"] or 0) - (r["before"] or 0)
            v[2] = max(v[2], (r["after"] or 0) - (r["before"] or 0))
            v[3] = min(v[3], (r["after"] or 0) - (r["before"] or 0))
        summ[tn] = {k: dict(chains=v[0], sum_station_delta=v[1], max_delta=v[2], min_delta=v[3]) for k, v in by.items()}
    rep["chain_change_summary"] = summ
    W1 = world_cores(plan)
    bad, n_up, n_same = [], 0, 0
    for k, v in W0.items():
        v1 = W1.get(k)
        if v1 is None or v1[2:] != v[2:] or abs(v1[0] - v[0]) > 1e-3:
            bad.append(str(k))
            continue
        dy = round(v1[1] - v[1], 3)
        if abs(dy) < 1e-3:
            n_same += 1
        elif abs(dy - G) < 1e-3:
            n_up += 1
        else:
            bad.append(f"{k} dy {dy}")
    rep["world_core_invariant"] = dict(cores=len(W0), unchanged=n_same, translated_up=n_up, errors=bad[:20],
                                       n_errors=len(bad) + abs(len(W1) - len(W0)))
    rep["open"] += [
        "clock: die H-tree / spine root_um y 8052.48 is the pre-growth centre (die centre now %.2f); CLOCK owns the "
        "re-publication; clock_htree.json sidecar stale" % (plan["die"]["outline_um"][1] / 2),
        "reset: root/parts reset pin repair must be re-applied after the final clock/geometry regeneration "
        "(codex reset_pin_sites.py), not copied",
        "u_hb_vms_Q cr[547:0]: folded NW vms core hfd_hgi_vms_glue_nw_t has no cq/cr (native SW-client master needed, "
        "+55,140 cells measured) -> hub chains for 548 cr bits OPEN (no invented pin)",
        "ft slots that got extra top-band hops lost bit_sites_um: exact RowAllocator per-bit refresh required",
        "q_b101_nw keeps L12x1 2996 / L48x11 634 / L53x1 612 + 2-11 b slots: its G2 structural failure is no longer "
        "on the selected path but still owned by PLAN"]
    return rep


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--grow", type=float, default=501.12)
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith(("g0", "gates", "netcut", "lat")) or p.name in ("die_plan.json", "core_conns.json") \
                or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    cc = json.loads((src / "core_conns.json").read_text())
    rep = apply(plan, out, cc, x.grow)
    plan["note"] = plan.get("note", "") + (" | PATH-HBM EDGE 10-25: +%.2f um edge band at y %.2f; L156 2740 b direct in "
                                           "the band; L74 TKM direct low on the NW_hub/root face; NW_b101 off both "
                                           "paths (R1DELTA L156/L157 replaced)" % (x.grow, CUT))
    dio = out / "die_io.json"
    if dio.exists():
        dio.write_text(json.dumps(plan["die"]["io"], indent=1) + "\n")
    S.Plan(plan)
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    (out / "core_conns.json").write_text(json.dumps(cc, indent=1) + "\n")
    rep.update(src=str(src), src_plan_sha256=sha(src / "die_plan.json"), out_plan_sha256=sha(out / "die_plan.json"))
    (out / "edge_report.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    g = rep["growth"]
    print("growth", {k: g[k] for k in ("growth_um", "area_before_mm2", "area_after_mm2", "area_added_mm2")},
          "stretched", len(g["stretched_types"]), "shifted", len(g["shifted_partitions"]), "slot changes",
          len(g["slot_changes"]), "io", g["inline_io_moved"], "pg", g["inline_pg_domains_moved"])
    print("removed", {k: (v["width"], v["slots"], v["stations"]) for k, v in rep["removed"].items()})
    print("L74", rep["moved"]["L74"]["new"], "L74_i chain", rep["new"]["L74_i_chain"])
    n = rep["new"]["L156"]
    print("L156", n["window"], "hub_open", n["hub_open"])
    print("  root", n["root_chains"])
    print("  hub", n["hub_chains"])
    print("lane changes", len(rep["lane_changes"]))
    for k, v in rep["lane_changes"].items():
        print("  ", k, (v["before"] or {}).get("cycles"), "->", (v["after"] or {}).get("cycles"),
              "word", (v["before"] or {}).get("word_cycles"), "->", (v["after"] or {}).get("word_cycles"))
    print("restation", {k: len(v) for k, v in rep["restation"].items()})
    for tn, sm in rep["chain_change_summary"].items():
        tot = sum(v["sum_station_delta"] for v in sm.values())
        hist = collections.Counter()
        for r in rep["chain_changes"][tn]:
            hist[(r["after"] or 0) - (r["before"] or 0)] += 1
        print("chain deltas", tn, "chains", len(rep["chain_changes"][tn]), "sum", tot, "hist", sorted(hist.items()))
        for k, v in sorted(sm.items(), key=lambda kv: -abs(kv[1]["sum_station_delta"]))[:12]:
            print("   ", k, v)
    print("world invariant", rep["world_core_invariant"])


if __name__ == "__main__":
    main()
