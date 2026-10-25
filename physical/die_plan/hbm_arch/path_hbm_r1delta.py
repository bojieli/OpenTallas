#!/usr/bin/env python3
"""PATH-HBM/R1DELTA (COORD rulings 2026-10-25 15:56, Q1 + Q2): lane right-sizing + the NW_hub->root idx return lanes.

    python3 path_hbm_r1delta.py --src <plan dir after ROOTEP> --out <new plan dir>

Q2 (right-size every lane to its traced real bits, no dead width): the nine root<->hub lanes typed by ROOTEP
(root_ep_report.json 'used' = bits with a real as-built driver/consumer) shrink to their real bits; a lane through a
REPLICATED type (one slot / bus width for every instance) takes the max of the lanes sharing it (L12 / L12m share
q_su31.L12x2).  L13m has 0 real bits and is removed (ports, both end buses, its stations, latency row).
Windows shrink about their centre (bus targets unchanged, so every ft slot station and internal chain stays valid),
except where the freed face is needed for the new lanes (ANCHOR below); every chain / slot touching a moved window is
re-stationed (hops <= 360, 405 fallback, never in a hard core).

Q1 (2,740 real NW_hub->root idx bits had no lane since L74 went TKM-only): two dedicated, registered, landed lanes,
L74 untouched.  One lane cannot fit: at 5.6 pins/um the NW_hub E / root W face has 269 um free after the shrinks and
the NW_b101 E / root W face 244 um.  vm_rr is 8 independent per-bank response buses (vmb_SWk.rr4 -> ctl.vm_rr[257k+:257],
as-built trace), so the split is by bank:
  * LA (L156)  NW_hub -> root direct (E face, M6/M4, 2 cycles): ctl.cr 274 + argmax.cr 274 + ctl.index_rq 136 + 3 banks
          (the banks whose root pins are nearest this window).
  * LB (L157)  NW_hub -> NW_b101 -> root (S face M7/M5 beside L74_0, NW_b101 ft slot N->E, root W face low): 5 banks.
Root ends are typed exactly like ROOTEP (core_conns + internal stations, capture = core end).  Hub ends: vmb_Qk.rr4 and
u_hb_idx__op_Q.vm_rq are typed; the 548 cr bits come from u_hb_vms_Q.cr in the as-built die (hb_vms_SW,
hfd_hgi_vms_glue_sw_t NC=2) but the folded q_hub_nw vms core is hfd_hgi_vms_glue_nw_t (NC=0: no cq/cr ports) -> OPEN
(hub core variant, reported).
"""
import argparse, collections, copy, json, os, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
import b2n as B  # noqa: E402
import b2o as BO  # noqa: E402
import cores_b2 as CB  # noqa: E402
import path_hbm_b2p as PB  # noqa: E402

TYPED = ["L12", "L12m", "L13", "L62", "L62m", "L74m", "L89", "L89m"]     # ROOTEP-typed lanes that shrink
REMOVE = ["L13m"]
# window anchoring for the faces the new lanes need ('hi' keeps the window's high end); default = centre
ANCHOR = {"L13_0": "hi", "L12_0": "hi", "L12m_0": "hi"}
BANK = 257
NEWL = {"L153": dict(path=["NW_hub", "root"]), "L154": dict(path=["NW_hub", "NW_b101", "root"])}
N_DIRECT_BANKS = 3
HUB, ROOT_T = "q_hub_nw", "root"


def need_len(npins):
    return max(npins / B.PIN_DENS + 0.5, B.MIN_WIN)


def boxes_of(t):
    return [(h["origin_um"][0], h["origin_um"][1], h["outline_um"][0], h["outline_um"][1]) for h in t["hard_cores"]]


def pins_of(out, t):
    pins = {}
    for h in t["hard_cores"]:
        o = h.get("orient", "R0")
        cw, ch = h["outline_um"]
        d = collections.defaultdict(dict)
        f = collections.defaultdict(list)
        for p in json.loads((out / h["pins_file"]).read_text()):
            m = re.match(r"^(.*?)(?:\[(\d+)\])?$", p["name"])
            rx, ry = BO.opt(o, p["x"], p["y"], cw, ch)
            d[m.group(1)][int(m.group(2) or 0)] = (h["origin_um"][0] + rx, h["origin_um"][1] + ry)
            f[m.group(1)].append(BO.oface(o, CK._core_face("R0", p["x"], p["y"], cw, ch)))
        pins[h["inst"]] = (d, f)
    return pins


def routers(t, extra=()):
    W, H = t["outline_um"]
    bx = boxes_of(t) + list(extra)
    r0 = CB.RelayRouter(bx, W, H, B.HOP)
    r1 = CB.RelayRouter(bx, W, H, B.REACH - 1.0)

    def route(a, b):
        try:
            return r0(a, b)
        except ValueError:
            return r1(a, b)
    return route, bx


def hopmax(e):
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    return max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def chain_entry(t, route, bx, core, port, bits, d, f, bus, bt, dirn, tag):
    """ROOTEP-style typed chain core.port[bits] <-> face bus (capture = core end for inputs, face for outputs)."""
    W, H = t["outline_um"]
    pp = [d[port][b] for b in bits]
    A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
    Bp = tuple(bt[bus][1])
    dist = abs(A[0] - Bp[0]) + abs(A[1] - Bp[1])
    if dist <= B.HOP:
        return None, dist
    f_ = collections.Counter(f[port]).most_common(1)[0][0]
    nc = CB.free_point((A[0] + BO.NRM[f_][0] * 4 * BO.LAT, A[1] + BO.NRM[f_][1] * 4 * BO.LAT), bx, W, H)
    regs = route(Bp, nc) + [nc]
    r3 = lambda p: [round(p[0], 3), round(p[1], 3)]  # noqa: E731
    if dirn == "out":
        e = dict(conn=f"bus:{bus}", from_um=r3(A), to_um=r3(Bp), regs_um=[r3(p) for p in reversed(regs)],
                 bits=len(bits), launch=f"{core}.{port}", capture=f"face bus {bus}")
    else:
        e = dict(conn=f"bus:{bus}", from_um=r3(Bp), to_um=r3(A), regs_um=[r3(p) for p in regs], bits=len(bits),
                 launch=f"face bus {bus}", capture=f"{core}.{port}")
    e["note"] = (f"PATH-HBM/R1DELTA 10-25 {tag} typed endpoint ({dirn}), {dist:.0f} um, {len(regs)} station(s), "
                 f"hops <= {B.HOP:g} um")
    for p in e["regs_um"]:
        for (x, y, w, h) in bx:
            if x < p[0] < x + w and y < p[1] < y + h:
                raise ValueError(f"register inside a hard core: {tag} {core}.{port} {p}")
    return e, dist


def apply(plan, out, cc, rep_ep):
    T = plan["partition_types"]
    parts = {p["name"]: p for p in plan["partitions"]}
    ports = {p["id"]: p for p in plan["ports"]}
    lanes = {l["id"]: l for l in plan["lanes"]}
    rep = dict(resize={}, removed={}, new={}, restation={}, open=[])
    P0 = S.Plan(plan)
    bt0 = {tn: CK._bus_targets(P0, tn) for tn in T}

    # ---------------------------------------------------------------- Q2 widths (traced real bits)
    used = {b.split("_")[0]: v["used"] for b, v in rep_ep["buses"].items()}
    want = {l: used[l] for l in TYPED}

    def elems(lid):
        L = lanes[lid]
        p0, p1 = ports[L["ports"][0]], ports[L["ports"][-1]]
        e = [("bus", parts[p0["src"]["part"]]["type"], p0["src"]["bus"]),
             ("bus", parts[p1["dst"]["part"]]["type"], p1["dst"]["bus"])]
        e += [("slot", parts[pt]["type"], sn) for pt, sn in B._lane_slots(P0, lid)]
        return e
    users = collections.defaultdict(set)
    for lid in lanes:
        for e in elems(lid):
            users[e].add(lid)
    width = dict(want)
    for _ in range(4):
        for lid in TYPED:
            for e in elems(lid):
                sh = users[e]
                if any(o not in want for o in sh if o != lid):
                    raise ValueError(f"{lid}: {e} shared with untyped lanes {sh}")
                width[lid] = max(width[lid], max(width[o] for o in sh))

    def tbus(tn, nm):
        return next(b for b in T[tn]["buses"] if b["name"] == nm)

    def tslot(tn, nm):
        return next(s for s in T[tn]["ft_slots"] if s["name"] == nm)
    moved = {}                                   # port id -> (old window, new window)
    for lid in TYPED:
        w0, w = int(ports[lanes[lid]["ports"][0]]["width"]), width[lid]
        assert w <= w0, (lid, w0, w)
        for kind, tn, nm in elems(lid):
            (tbus if kind == "bus" else tslot)(tn, nm)["width"] = w
        for pid in lanes[lid]["ports"]:
            pr = ports[pid]
            lo, hi = pr["window_um"]
            pr["width"] = w
            L_ = need_len(S.port_pins_count(pr))
            a = ANCHOR.get(pid, "c")
            nw = ([B.snap(hi - L_), hi] if a == "hi" else [lo, B.snap(lo + L_)] if a == "lo"
                  else [B.snap(0.5 * (lo + hi) - L_ / 2), B.snap(0.5 * (lo + hi) + L_ / 2)])
            if nw[1] - nw[0] < hi - lo - 1e-6:
                pr["window_um"] = nw
                moved[pid] = ([lo, hi], nw)
        sh = sorted(set().union(*[users[e] for e in elems(lid)]) - {lid})
        rep["resize"][lid] = dict(width=[w0, w], traced_real=want[lid],
                                  replicated_type_max_with=(sh if w > want[lid] else None))
    # L89_0 sits directly below the shrunk L13_0 (contiguous free face below for L153)
    l13 = ports["L13_0"]["window_um"]
    p89 = ports["L89_0"]
    L89 = need_len(S.port_pins_count(p89))
    old = list(p89["window_um"])
    p89["window_um"] = [B.snap(l13[0] - B.GAP - L89), B.snap(l13[0] - B.GAP)]
    moved["L89_0"] = (moved.get("L89_0", (old,))[0], p89["window_um"])
    # L12 / L12m ft go straight through NW_b101 / NE_b101: the su31 side window (L12_1 / L12m_1, free W face below)
    # aligns with the root side one -> no Z jog, so the b101 horizontal cuts carry no L12 bits (L157 runs vertically
    # there); q_su31 is replicated, both instances move alike (vertical face: same y in both frames).
    for a_, b_ in (("L12_0", "L12_1"), ("L12m_0", "L12m_1")):
        old = list(ports[b_]["window_um"])
        ports[b_]["window_um"] = list(ports[a_]["window_um"])
        moved[b_] = (moved.get(b_, (old,))[0], ports[b_]["window_um"])
    # L124_0 / L80_0 pack up under the shrunk L12_0 (contiguous free face at the bottom for L154)
    top = ports["L12_0"]["window_um"][0]
    for pid in ("L80_0", "L124_0"):
        pr = ports[pid]
        old = list(pr["window_um"])
        Lw = old[1] - old[0]
        pr["window_um"] = [B.snap(top - B.GAP - Lw), B.snap(top - B.GAP)]
        top = pr["window_um"][0]
        moved[pid] = (old, pr["window_um"])

    # ---------------------------------------------------------------- Q2: L13m removed (0 real bits)
    for lid in REMOVE:
        L = lanes.pop(lid)
        assert used.get(lid, 0) == 0, lid
        pp = [ports.pop(pid) for pid in L["ports"]]
        plan["lanes"] = [l for l in plan["lanes"] if l["id"] != lid]
        plan["ports"] = [p for p in plan["ports"] if p["id"] not in L["ports"]]
        gone = []
        for kind, tn, nm in [("bus", parts[pp[0]["src"]["part"]]["type"], pp[0]["src"]["bus"]),
                             ("bus", parts[pp[-1]["dst"]["part"]]["type"], pp[-1]["dst"]["bus"])]:
            assert users[(kind, tn, nm)] == {lid}, (lid, tn, nm, users[(kind, tn, nm)])
            T[tn]["buses"] = [b for b in T[tn]["buses"] if b["name"] != nm]
            ist = T[tn].get("internal_stations", [])
            n0 = len(ist)
            T[tn]["internal_stations"] = [e for e in ist if e.get("conn") != f"bus:{nm}"]
            nc = 0
            for core, cp in cc.get(tn, {}).items():
                for port in list(cp):
                    k0 = len(cp[port])
                    cp[port] = [x for x in cp[port] if x != f"bus:{nm}"]
                    nc += k0 - len(cp[port])
                    if not cp[port]:
                        del cp[port]
            gone.append(dict(type=tn, bus=nm, stations_removed=n0 - len(T[tn]["internal_stations"]),
                             core_conn_refs_removed=nc))
        plan["latency"]["lanes"].pop(lid, None)
        rep["removed"][lid] = dict(ports=L["ports"], width=pp[0]["width"], ends=gone)

    # ---------------------------------------------------------------- Q1: new lanes
    nxt = 1 + max(int(re.sub(r"\D", "", l)) for l in lanes)

    root_t, hub_t = T[ROOT_T], T[HUB]
    rpins = pins_of(out, root_t)
    hpins = pins_of(out, hub_t)
    # face geometry
    P1 = S.Plan(plan)

    def free_seg(a, b, face, need):
        """lowest free stretch of the a/b shared face (die frame) of length >= need."""
        line, lo, hi = CK.face_line(P1.rect(a), face)
        _, lo2, hi2 = CK.face_line(P1.rect(b), S.OPP[face])
        lo, hi = max(lo, lo2), min(hi, hi2)
        ws = sorted(p["window_um"] for p in plan["ports"] if {p["src"]["part"], p["dst"]["part"]} == {a, b})
        prev, gaps = lo + 0.5, []
        for w in ws:
            gaps.append((prev, w[0] - B.GAP))
            prev = w[1] + B.GAP
        gaps.append((prev, hi - 0.5))
        return [g for g in gaps if g[1] - g[0] >= need - 1e-6], gaps
    # bank assignment: vm_rr bank k (bits 257k..257k+256) -> the lane whose root window is nearer its ctl pins
    rd = rpins["u_hb_idx__ctl"][0]
    rorg = parts["root"]["origin_um"]

    def bank_y(k):
        ys = [rd["vm_rr"][b][1] for b in range(k * BANK, (k + 1) * BANK)]
        return sum(ys) / len(ys) + rorg[1]
    by = {k: bank_y(k) for k in range(8)}
    direct_banks = sorted(sorted(range(8), key=lambda k: -by[k])[:N_DIRECT_BANKS])
    via_banks = [k for k in range(8) if k not in direct_banks]
    # rows: (root core, port, plo, phi, hub core, hub port, hlo, hhi)
    rows = {"L153": [("u_hb_idx__ctl", "cr", 0, 273, "u_hb_vms_Q", "cr", 274, 547),
                     ("u_hb_argmax", "cr", 0, 273, "u_hb_vms_Q", "cr", 0, 273),
                     ("u_hb_idx__ctl", "index_rq", 0, 135, "u_hb_idx__op_Q", "vm_rq", 0, 135)]
            + [("u_hb_idx__ctl", "vm_rr", k * BANK, (k + 1) * BANK - 1, f"u_vmb_Q{k}", "rr4", 0, BANK - 1)
               for k in direct_banks],
            "L154": [("u_hb_idx__ctl", "vm_rr", k * BANK, (k + 1) * BANK - 1, f"u_vmb_Q{k}", "rr4", 0, BANK - 1)
                     for k in via_banks]}
    nmap = {"L153": f"L{nxt}", "L154": f"L{nxt + 1}"}
    for key in ("L153", "L154"):
        lid = nmap[key]
        pth = NEWL[key]["path"]
        w = sum(r[3] - r[2] + 1 for r in rows[key])
        pids = []
        for h in range(len(pth) - 1):
            x, y = pth[h], pth[h + 1]
            face = {("NW_hub", "root"): "E", ("NW_hub", "NW_b101"): "S", ("NW_b101", "root"): "E"}[(x, y)]
            L_ = need_len(w)
            segs, gaps = free_seg(x, y, face, L_)
            if not segs:
                raise ValueError(f"{lid} {x}->{y} face {face}: no free {L_:.1f} um ({gaps})")
            if face == "S":        # NW_hub S face: the free stretch beside L74_0 (high end, next to the hub's E end)
                s0, s1 = segs[-1]
                win = [B.snap(s1 - L_), B.snap(s1)]
            else:                  # root W face: the lowest free stretch (nearest the idx cluster)
                s0, s1 = segs[0]
                win = [B.snap(s0), B.snap(s0 + L_)]
            sb = f"{lid}_o" if h == 0 else f"{lid}x{h}_o"
            db = f"{lid}_i" if h == len(pth) - 2 else f"{lid}x{h + 1}_i"
            pr = dict(id=f"{lid}_{h}", src=dict(part=x, bus=sb), dst=dict(part=y, bus=db), width=w, kind="data",
                      face=face, layers=list(B.FACE_LAYERS[face]), window_um=win,
                      note=f"PATH-HBM/R1DELTA 10-25 (COORD Q1 15:56): NW_hub->root idx return, registered + landed")
            plan["ports"].append(pr)
            ports[pr["id"]] = pr
            pids.append(pr["id"])
            P1 = S.Plan(plan)
        hub_t["buses"].append(dict(name=f"{lid}_o", dir="out", width=w, kind="data"))
        root_t["buses"].append(dict(name=f"{lid}_i", dir="in", width=w, kind="data"))
        for h in range(1, len(pth) - 1):
            tf = {P1.die_face(pth[h], g): g for g in "NSEW"}
            T[parts[pth[h]]["type"]]["ft_slots"].append(dict(name=f"{lid}x{h}", in_face=tf["N"], out_face=tf["E"],
                                                            width=w, stations=1))
        L = dict(id=lid, ports=pids, note=f"NW_hub->root idx return data (PATH-HBM/R1DELTA 10-25, COORD Q1: "
                                           f"{'cr/argmax.cr/index_rq + ' if key == 'L153' else ''}vm_rr banks "
                                           f"{direct_banks if key == 'L153' else via_banks})")
        plan["lanes"].append(L)
        lanes[lid] = L
        rep["new"][lid] = dict(path=pth, width=w, windows={p: ports[p]["window_um"] for p in pids},
                               map=[], hub_open=[])
    P2 = S.Plan(plan)
    # ft slot stations of the new slot + every slot whose port window moved (restation rule, slot only)
    routes = B._type_routes(P2)
    moved_lanes = {l for l in lanes for p in lanes[l]["ports"] if p in moved} | {nmap["L154"]}
    for lid in sorted(moved_lanes):
        for part, sn in B._lane_slots(P2, lid):
            tn = parts[part]["type"]
            t = T[tn]
            sl = tslot(tn, sn)
            seg = routes[(tn, sn)]
            W, H = t["outline_um"]
            bx = B._boxes(t)
            router = CB.RelayRouter(bx, W, H, B.HOP)
            regs = B._chain(router, lambda p: CB.free_point(p, bx, W, H), seg[0], seg[-1])
            Ls = CK.plen(seg)
            while Ls / len(regs) > B.REACH:
                regs.append(regs[-1])
            old = (sl.get("stations"), sl.get("regs_um"))
            sl["stations"] = len(regs)
            sl["regs_um"] = [[round(v, 3) for v in p] for p in regs]
            sl.pop("bit_sites_um", None)
            rep["restation"][f"{tn}.{sn}"] = dict(stations=[old[0], len(regs)], lane=lid)
    # internal chains whose window end moved: endpoint follows the bus target, re-chained if a hop breaks
    bt2 = {tn: CK._bus_targets(P2, tn) for tn in T}
    for tn, t in T.items():
        route = None
        for e in t.get("internal_stations", []):
            c = e.get("conn", "")
            if not c.startswith("bus:"):
                continue
            bn = c[4:]
            if bn not in bt0[tn] or bn not in bt2[tn]:
                continue
            o, n = bt0[tn][bn][1], bt2[tn][bn][1]
            if abs(o[0] - n[0]) + abs(o[1] - n[1]) < 1e-3:
                continue
            for k in ("from_um", "to_um"):
                if abs(e[k][0] - o[0]) + abs(e[k][1] - o[1]) < 1e-3:
                    e[k] = [round(n[0], 3), round(n[1], 3)]
            if hopmax(e) > B.REACH - 1.0:
                if route is None:
                    route, bx = routers(t)
                core_end = e["to_um"] if e["from_um"] == [round(n[0], 3), round(n[1], 3)] else e["from_um"]
                regs = route(tuple(n), tuple(core_end))
                e["regs_um"] = [[round(v, 3) for v in p] for p in (regs if e["from_um"][0] == round(n[0], 3)
                                                                    and e["from_um"][1] == round(n[1], 3)
                                                                    else list(reversed(regs)))]
                e["note"] = e.get("note", "") + " | R1DELTA re-stationed (window moved)"
            rep["restation"].setdefault(f"{tn}.internal", 0)
            rep["restation"][f"{tn}.internal"] += 1
    # typed endpoints of the new lanes: root (capture = core) and hub (launch = core)
    for key in ("L153", "L154"):
        lid = nmap[key]
        rr_route, rbx = routers(root_t)
        hr_route, hbx = routers(hub_t)
        at = 0
        groups_r = collections.defaultdict(list)
        groups_h = collections.defaultdict(list)
        for (rc, rp, plo, phi, hc, hp, hlo, hhi) in rows[key]:
            n = phi - plo + 1
            rep["new"][lid]["map"].append(dict(bits=f"[{at + n - 1}:{at}]", root=f"{rc}.{rp}[{phi}:{plo}]",
                                               hub=f"{hc}.{hp}[{hhi}:{hlo}]"))
            at += n
            d = rpins[rc][0].get(rp)
            if d is None or any(b not in d for b in range(plo, phi + 1)):
                raise ValueError(f"root {rc}.{rp}[{phi}:{plo}] has no pins")
            groups_r[(rc, rp)] += list(range(plo, phi + 1))
            hd = hpins.get(hc, ({}, {}))[0].get(hp)
            if hd is None or any(b not in hd for b in range(hlo, hhi + 1)):
                rep["new"][lid]["hub_open"].append(f"{hc}.{hp}[{hhi}:{hlo}]: no such port on the q_hub_nw core "
                                                   f"({[h['module'] for h in hub_t['hard_cores'] if h['inst'] == hc]})")
                continue
            groups_h[(hc, hp)] += list(range(hlo, hhi + 1))
        ist_r = root_t.setdefault("internal_stations", [])
        ist_h = hub_t.setdefault("internal_stations", [])
        for (rc, rp), bl in sorted(groups_r.items()):
            cc[ROOT_T].setdefault(rc, {}).setdefault(rp, []).append(f"bus:{lid}_i")
            d, f = rpins[rc]
            e, dist = chain_entry(root_t, rr_route, rbx, rc, rp, bl, d, f, f"{lid}_i", bt2[ROOT_T], "in", lid)
            if e:
                ist_r.append(e)
        for (hc, hp), bl in sorted(groups_h.items()):
            cc[HUB].setdefault(hc, {}).setdefault(hp, []).append(f"bus:{lid}_o")
            d, f = hpins[hc]
            e, dist = chain_entry(hub_t, hr_route, hbx, hc, hp, bl, d, f, f"{lid}_o", bt2[HUB], "out", lid)
            if e:
                ist_h.append(e)
        cr = [e for e in ist_r if e["conn"] == f"bus:{lid}_i"]
        ch = [e for e in ist_h if e["conn"] == f"bus:{lid}_o"]
        rep["new"][lid]["root_chains"] = [dict(capture=e["capture"], stations=len(e["regs_um"]),
                                               worst_hop=round(hopmax(e), 1)) for e in cr]
        rep["new"][lid]["hub_chains"] = [dict(launch=e["launch"], stations=len(e["regs_um"]),
                                              worst_hop=round(hopmax(e), 1)) for e in ch]
    rep["direct_banks"], rep["via_banks"], rep["bank_root_y"] = direct_banks, via_banks, by
    rep["moved_windows"] = moved
    return rep


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith("g0") or p.name.startswith("gates") or p.name.startswith("netcut") \
                or p.name in ("die_plan.json", "core_conns.json") or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    cc = json.loads((src / "core_conns.json").read_text())
    rep_ep = json.loads((src / "root_ep_report.json").read_text())
    rep = apply(plan, out, cc, rep_ep)
    plan["note"] = plan.get("note", "") + (" | PATH-HBM R1DELTA: lanes right-sized to traced real bits (L13m removed), "
                                           "NW_hub->root idx return lanes (COORD Q1/Q2 15:56)")
    S.Plan(plan, out / "die_plan.json")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    (out / "core_conns.json").write_text(json.dumps(cc, indent=1) + "\n")
    rep.update(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), out_plan_sha256=PB.sha(out / "die_plan.json"))
    (out / "r1delta_report.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    for k, v in rep["resize"].items():
        print("resize", k, v)
    print("removed", {k: (v["width"], v["ends"]) for k, v in rep["removed"].items()})
    for k, v in rep["new"].items():
        print("new", k, v["path"], v["width"], v["windows"], "hub_open", v["hub_open"])
        print("   root", v["root_chains"]); print("   hub", v["hub_chains"])
    print("banks direct", rep["direct_banks"], "via", rep["via_banks"])
    print("restation", rep["restation"])


if __name__ == "__main__":
    main()
