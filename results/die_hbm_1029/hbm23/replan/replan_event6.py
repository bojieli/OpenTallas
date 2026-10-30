#!/usr/bin/env python3
"""DIE-HBM-22 re-plan event, DIE-HBM-23 rev (NE mirror windows on own faces; die-local, opt-in; no shared tool changed).

    python3 replan_event.py TOOLS_DIR PLANDIR VARIANT_JSON OUTDIR [--rows92 rows92.json] [--near-um 1200]

VARIANT_JSON = {"name", "A": [NW names west->east], "C": [...], "size": {NW_name: width_um}, "rowh": {"A":1555.2,"C":1572.48}}
NE partitions = MY mirror of the NW order (x_ne = W - x_nw - w), same type outline as the NW partner's type.

Steps: (1) move origins (rows A y 4510.08, C y 10385.28) and set outlines (size override + row height) on the types of
moved partitions; (2) drop every lane with a port on a moved partition: its ports, endpoint buses, ft slots, latency
entries, latency_groups members kept by name (reported); (3) re-add the dropped lanes with the SAME lane id / end bus
names (L<id>_o / L<id>_i) via lane_add.Builder.build_one (ADJ = one port; else the shortest abutment path <= max_hops,
stations = ceil(route / ft_station_max)); (4) add the 92 far rows via lane_add.Builder (near 1200) on the result;
(5) write die_plan.json + replan_report.json (per lane old/new cycles, FAR/failed lists).
NOT UPDATED (reported): die clock h-tree/mesh sidecars (clock_taps_die.json, clock_htree.json, entries.json),
pg_bumps.json, type internal_stations (face-bus endpoints kept by name; windows may have moved), die_ft_bands.
All numbers are plan arithmetic: UNCHECKED until G0/G0C/bind.
"""
import sys, json, copy, os, time, argparse
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("tools"); ap.add_argument("plan"); ap.add_argument("variant"); ap.add_argument("out")
ap.add_argument("--rows92"); ap.add_argument("--near-um", type=float, default=1200.0)
ap.add_argument("--max-hops", type=int, default=6)
a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S
import lane_add as LA

t0 = time.time()
plan_dir, out = Path(a.plan), Path(a.out)
raw = json.loads((plan_dir / "die_plan.json").read_text())
V = json.loads(Path(a.variant).read_text())
W = raw["die"]["outline_um"][0]
ROWY = {"A": 4510.08, "C": 10385.28}
ROWH = V.get("rowh", {"A": 1555.2, "C": 1572.48})
parts = {p["name"]: p for p in raw["partitions"]}
T = raw["partition_types"]

def mirror(n):
    return "NE" + n[2:]

moved, outline_changes = set(), []
for row in ("A", "C"):
    x = 0.0
    for n in V[row]:
        for nm in (n, mirror(n)):
            p = parts[nm]
            t = T[p["type"]]
            w = float(V.get("size", {}).get(n, t["outline_um"][0]))
            h = float(ROWH[row])
            if [round(w, 4), round(h, 4)] != [round(v, 4) for v in t["outline_um"]]:
                outline_changes.append(dict(type=p["type"], old=list(t["outline_um"]), new=[w, h]))
                t["outline_um"] = [w, h]
            o = [round(x, 4), ROWY[row]] if nm == n else [round(W - x - w, 4), ROWY[row]]
            if [round(v, 3) for v in p["origin_um"]] != [round(v, 3) for v in o]:
                moved.add(nm)
            p["origin_um"] = o
        x += float(V.get("size", {}).get(n, T[parts[n]["type"]]["outline_um"][0]))
    assert x <= 13357.44 + 0.01, (row, x)
moved |= {r["type"] for r in []}
# outline-changed types count as moved (their faces change)
for oc in outline_changes:
    moved |= {p["name"] for p in raw["partitions"] if p["type"] == oc["type"]}

P0 = S.Plan(raw)
ports = {p["id"]: p for p in raw["ports"]}
OPP = LA.OPP
SELF_MIRROR = {"root", "PHY_NC"}
old_lat = raw["latency"]["lanes"]
dropped = []
for ln in raw["lanes"]:
    pp = [ports[q] for q in ln["ports"]]
    if not any(x["src"]["part"] in moved or x["dst"]["part"] in moved for x in pp):
        continue
    chain = [pp[0]["src"]["part"]] + [x["dst"]["part"] for x in pp]
    n = len(pp)
    kept_hop = [chain[i] not in moved and chain[i + 1] not in moved for i in range(n)]
    slots = {}
    for part, sl, a_, b_ in P0.lane_crossings(ln["id"]):
        if sl:
            slots[chain.index(part, 1)] = (sl, copy.deepcopy(P0.slot(part, sl)))
    # runs of non-kept hops [s, e) in partition indices
    runs, i = [], 0
    while i < n:
        if kept_hop[i]:
            i += 1; continue
        s0 = i
        while i < n and not kept_hop[i]:
            i += 1
        runs.append((s0, i))
    dropped.append(dict(id=ln["id"], src=chain[0], dst=chain[-1], bits=int(pp[0]["width"]),
                        kind=pp[0].get("kind", "data"), old_chain=chain, old_cycles=old_lat.get(ln["id"], {}).get("cycles"),
                        ob=pp[0]["src"]["bus"], ib=pp[-1]["dst"]["bus"], note=ln.get("note", ""),
                        port_ids=list(ln["ports"]), kept_hop=kept_hop, runs=runs, slots=slots,
                        rports={q: dict(face=P0.ports[q].get("face"), window_um=P0.ports[q].get("window_um"),
                                        layers=P0.ports[q].get("layers")) for q in ln["ports"]}))
# remove: ports of non-kept hops; endpoint buses whose hop is not kept; slots not fully kept (boundary ones re-created)
rm_bus, rm_slot, rm_port = {}, {}, set()
for d in dropped:
    n = len(d["port_ids"])
    for i in range(n):
        if not d["kept_hop"][i]:
            rm_port.add(d["port_ids"][i])
    if not d["kept_hop"][0] and d["src"] in parts:
        rm_bus.setdefault(parts[d["src"]]["type"], set()).add(d["ob"])
    if not d["kept_hop"][-1] and d["dst"] in parts:
        rm_bus.setdefault(parts[d["dst"]]["type"], set()).add(d["ib"])
    for j, (sl, decl) in d["slots"].items():
        if not (d["kept_hop"][j - 1] and d["kept_hop"][j]):
            rm_slot.setdefault(parts[d["old_chain"][j]]["type"], set()).add(sl)
nb = ns = 0
for tn, names in rm_bus.items():
    L0 = len(T[tn].get("buses", [])); T[tn]["buses"] = [b for b in T[tn].get("buses", []) if b["name"] not in names]
    nb += L0 - len(T[tn]["buses"])
for tn, names in rm_slot.items():
    L0 = len(T[tn].get("ft_slots", [])); T[tn]["ft_slots"] = [x for x in T[tn].get("ft_slots", []) if x["name"] not in names]
    ns += L0 - len(T[tn]["ft_slots"])
raw["ports"] = [p for p in raw["ports"] if p["id"] not in rm_port]
dids = {d["id"] for d in dropped}
lane_obj = {l["id"]: l for l in raw["lanes"]}
for i_ in dids:
    old_lat.pop(i_, None)
print(f"moved {len(moved)} partitions, outline changes {len(outline_changes)}, lanes touched {len(dropped)} "
      f"(hops re-routed {len(rm_port)}, buses {nb}, slots {ns}) {time.time()-t0:.0f}s", flush=True)

import heapq
import check as C


def efaces(P, c, u, v):
    """die faces of c toward u and toward v."""
    return LA.shared_edge(P, c, u)[0], LA.shared_edge(P, c, v)[0]


def uturn(P, ch, in_face=None, out_face=None):
    for k in range(len(ch)):
        fi = (LA.shared_edge(P, ch[k], ch[k - 1])[0] if k > 0 else in_face)
        fo = (LA.shared_edge(P, ch[k], ch[k + 1])[0] if k < len(ch) - 1 else out_face)
        if fi is not None and fo is not None and fi == fo:
            return True
    return False


def path_ex(B, a, b, ban=(), max_hops=8, in_face=None, out_face=None, ban_nodes=()):
    dist, prev, hq = {a: 0.0}, {}, [(0.0, a, 0)]
    while hq:
        d_, u, n = heapq.heappop(hq)
        if u == b:
            break
        if d_ > dist.get(u, 1e18) + 1e-6 or n >= max_hops:
            continue
        for v in B.neighbours(u):
            if v != b and (v.startswith("PHY") or v == "root" or v.endswith("_io")):
                continue
            if (u, v) in ban or v in ban_nodes:
                continue
            fi = LA.shared_edge(B.P, u, prev[u])[0] if u in prev else (in_face if u == a else None)
            if fi is not None and fi == LA.shared_edge(B.P, u, v)[0]:
                continue                                        # no U-turn through u
            cu, cv = LA.centre(B.P, u), LA.centre(B.P, v)
            nd = d_ + abs(cu[0] - cv[0]) + abs(cu[1] - cv[1])
            if nd < dist.get(v, 1e18) - 1e-6:
                dist[v], prev[v] = nd, u
                heapq.heappush(hq, (nd, v, n + 1))
    if b not in prev:
        return None
    out = [b]
    while out[-1] != a:
        out.append(prev[out[-1]])
    return out[::-1]


def candidates(B, a, b, bits, old_chain=None, in_face=None, out_face=None):
    out, seen = [], set()

    def add(kind, ch):
        if ch and tuple(ch) not in seen and not uturn(B.P, ch, in_face, out_face):
            seen.add(tuple(ch)); out.append((kind, None, ch))
    e = LA.shared_edge(B.P, a, b)
    need = bits / 6.0 + 4.0
    if e and e[2] - e[1] >= need:
        add("adj", [a, b])
    if old_chain and all(LA.shared_edge(B.P, u, v) for u, v in zip(old_chain, old_chain[1:])):
        add("path", list(old_chain))
    p1 = path_ex(B, a, b, ban={(a, b)}, in_face=in_face, out_face=out_face)
    add("path", p1)
    if p1 and len(p1) > 2:
        add("path", path_ex(B, a, b, ban={(a, b), (a, p1[1])}, in_face=in_face, out_face=out_face))
        add("path", path_ex(B, a, b, ban={(a, b), (p1[-2], b)}, in_face=in_face, out_face=out_face))
    if e:
        add("adj", [a, b])
    # DIE-HBM-23: more diverse detours (tried only after the above fail): ban each interior partition of the shortest
    # path / old chain, then pairs of them (window-full or macro-blocked partitions are routed around)
    inter = []
    for ch in ([p1] if p1 else []) + ([old_chain] if old_chain else []):
        inter += [x for x in ch[1:-1] if x not in inter]
    for x in inter:
        add("path", path_ex(B, a, b, ban={(a, b)}, in_face=in_face, out_face=out_face, ban_nodes={x}, max_hops=10))
    for i, x in enumerate(inter):
        for y in inter[i + 1:]:
            add("path", path_ex(B, a, b, ban={(a, b)}, in_face=in_face, out_face=out_face, ban_nodes={x, y}, max_hops=10))
    return out


def mirror_part(n):
    if n.startswith("NW_"):
        return "NE_" + n[3:]
    if n.startswith("NE_"):
        return "NW_" + n[3:]
    return {"PHY_NW": "PHY_NE", "PHY_NE": "PHY_NW"}.get(n, n)


def mirror_win(win, face):
    # DIE-HBM-23: MY mirror flips x only -> N/S-face windows (x spans) mirror, E/W-face windows (y spans) keep
    if face in ("E", "W"):
        return [round(win[0], 4), round(win[1], 4)]
    return [round(W - win[1], 4), round(W - win[0], 4)]


NEWDECL = {}     # (type, name) -> decl created by this event (mirror dedupe on NW/NE-shared types)


def add_decl(tn, key, decl, rep):
    t = T[tn]
    for x in t.get(key, []):
        if x["name"] == decl["name"]:
            a_ = {k: v for k, v in x.items() if k != "regs_um"}
            b_ = {k: v for k, v in decl.items() if k != "regs_um"}
            if a_ != b_:
                rep.append(dict(type=tn, name=decl["name"], why="shared-type declaration differs"))
            return False
    t.setdefault(key, []).append(decl)
    NEWDECL[(tn, decl["name"])] = decl
    return True


def reroute_run(B, d, s, e, rep, base_name, nw_hint=None):
    """re-route hops s..e-1 of lane d.  Returns list of new port dicts (in order) or None."""
    P = B.P
    ch0 = d["old_chain"]
    a, b = ch0[s], ch0[e]
    lid = d["id"]
    in_face = out_face = None
    if s > 0:   # boundary slot in a (unmoved) keeps its in side
        q = d["port_ids"][s - 1]; in_face = OPP[d["rports"][q]["face"]]
    if e < len(ch0) - 1:
        q = d["port_ids"][e]; out_face = d["rports"][q]["face"]
    cands = candidates(B, a, b, d["bits"], ch0[s:e + 1], in_face, out_face)
    why = "no candidate"
    for kind, _, chain in cands:
        hops, ok = [], True
        for k, (u, v) in enumerate(zip(chain, chain[1:])):
            pref, got = None, None
            if nw_hint is not None and k < len(nw_hint) and LA.shared_edge(P, u, v):
                df_ = LA.shared_edge(P, u, v)[0]
                mw = mirror_win(nw_hint[k], df_)
                occ = LA.face_intervals(P, u, df_) + LA.face_intervals(P, v, OPP[df_]) + B.taken[(u, df_)]
                if all(mw[1] + B.guard <= x0 or mw[0] - B.guard >= x1 for x0, x1 in occ):
                    got = (df_, mw, LA.face_layers(P, u, df_))
                    B.taken[(u, df_)].append(tuple(mw)); B.taken[(v, OPP[df_])].append(tuple(mw))
                pref = (mw[0] + mw[1]) / 2
            if got is None:
                got = B.alloc(u, v, d["bits"], prefer=pref)
            if got is None:
                ok = False; why = f"no free window {u}|{v}"; break
            hops.append((u, v, got))
        if not ok:
            for (uu, vv, (df, win, _)) in hops:
                B.taken[(uu, df)].remove(tuple(win)); B.taken[(vv, OPP[df])].remove(tuple(win))
            continue
        # slots: boundary a (s>0), interior, boundary b (e<n)
        slots = []
        for k, part in enumerate(chain):
            if k == 0 and s == 0:
                continue
            if k == len(chain) - 1 and e == len(ch0) - 1:
                continue
            if k == 0:
                q = d["port_ids"][s - 1]; dfi, wi, li = in_face, d["rports"][q]["window_um"], d["rports"][q]["layers"]
            else:
                dfi, wi, li = OPP[hops[k - 1][2][0]], hops[k - 1][2][1], hops[k - 1][2][2]
            if k == len(chain) - 1:
                q = d["port_ids"][e]; dfo, wo, lo_ = out_face, d["rports"][q]["window_um"], d["rports"][q]["layers"]
            else:
                dfo, wo, lo_ = hops[k][2][0], hops[k][2][1], hops[k][2][2]
            if dfi == dfo:
                ok = False; why = f"U-turn in {part}"; break
            nst, seg, L = B.stations_for(part, dfi, wi, dfo, wo)
            even = [C.point_at(seg, L * j / nst) for j in range(nst)]
            if k == 0:
                name = d["slots"][s][0]
            elif k == len(chain) - 1:
                name = d["slots"][e][0]
            else:
                name = f"{base_name if part not in SELF_MIRROR else lid}r{s}_{k}"
            slots.append([part, k, dfi, wi, li, dfo, wo, lo_, nst, even, L, 0, even, name])
        if not ok:
            for (uu, vv, (df, win, _)) in hops:
                B.taken[(uu, df)].remove(tuple(win)); B.taken[(vv, OPP[df])].remove(tuple(win))
            continue
        start = B.face_pt(P, chain[0], in_face if s > 0 else hops[0][2][0],
                          d["rports"][d["port_ids"][s - 1]]["window_um"] if s > 0 else hops[0][2][1])
        end = B.face_pt(P, chain[-1], out_face if e < len(ch0) - 1 else OPP[hops[-1][2][0]],
                        d["rports"][d["port_ids"][e]]["window_um"] if e < len(ch0) - 1 else hops[-1][2][1])

        def worst():
            pts = [start] + [r for sl in slots for r in sl[9]] + [end]
            return max([abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])] or [0.0])
        if slots and (worst() > B.reach + 1e-6 or any(B.macro_hits(sl[0], sl[9]) for sl in slots)):
            got = B.resite(chain, slots, start, end)
            if got is None:
                ok = False; why = f"no macro-free station chain ({sum(sl[8] for sl in slots)} st)"
            else:
                for sl, regs in zip(slots, got):
                    sl[8], sl[9] = len(regs), regs
        if ok and worst() > B.reach + 1e-6:
            ok = False; why = f"hop {worst():.0f} > reach"
        if not ok:
            for (uu, vv, (df, win, _)) in hops:
                B.taken[(uu, df)].remove(tuple(win)); B.taken[(vv, OPP[df])].remove(tuple(win))
            continue
        # write declarations
        if s == 0:
            tf, tw, flip = LA.to_type_window(P, a, hops[0][2][0], hops[0][2][1])
            add_decl(P.parts[a]["type"], "buses", dict(name=d["ob"], dir="out", width=d["bits"], kind=d["kind"], face=tf,
                     window_um=tw, layers=list(hops[0][2][2]), order="lsb_high" if flip else "lsb_low"), rep)
        if e == len(ch0) - 1:
            tf, tw, flip = LA.to_type_window(P, b, OPP[hops[-1][2][0]], hops[-1][2][1])
            add_decl(P.parts[b]["type"], "buses", dict(name=d["ib"], dir="in", width=d["bits"], kind=d["kind"], face=tf,
                     window_um=tw, layers=list(hops[-1][2][2]), order="lsb_high" if flip else "lsb_low"), rep)
        sname = {}
        for part, k, dfi, wi, li, dfo, wo, lo_, nst, regs, L, h, _, name in slots:
            tfi, twi, fi = LA.to_type_window(P, part, dfi, wi)
            tfo, two, fo = LA.to_type_window(P, part, dfo, wo)
            decl = dict(name=name, in_face=tfi, out_face=tfo, width=d["bits"], stations=int(nst), in_window_um=twi,
                        in_layers=list(li), in_order="lsb_high" if fi else "lsb_low", out_window_um=two,
                        out_layers=list(lo_), out_order="lsb_high" if fo else "lsb_low",
                        regs_um=[[round(v, 4) for v in P.to_type(part, r)] for r in regs])
            add_decl(P.parts[part]["type"], "ft_slots", decl, rep)
            sname[k] = name
        newp = []
        for k, (u, v, (df, win, lay)) in enumerate(hops):
            sb = d["ob"] if (k == 0 and s == 0) else sname[k] + "_o"
            db = d["ib"] if (k == len(hops) - 1 and e == len(ch0) - 1) else sname[k + 1] + "_i"
            newp.append(dict(id=f"{lid}_r{s}_{k}", src=dict(part=u, bus=sb), dst=dict(part=v, bus=db),
                             width=d["bits"], kind=d["kind"]))
        B.P = S.Plan(B.raw)
        return dict(ports=newp, chain=chain, kind=kind, wins=[h[2][1] for h in hops])
    rep.append(dict(id=lid, src=a, dst=b, run=[s, e], why=why, chains=[c[2] for c in cands]))
    return None


_dc = copy.deepcopy
B = LA.Builder(raw, near_um=1e9, max_hops=a.max_hops, require_cycle_match=False)
B.shared = set()
rep1 = dict(rebuilt=[], failed=[], decl_conflicts=[])
dropped.sort(key=lambda d: (d["src"].startswith("NE_") or d["dst"].startswith("NE_") or d["id"].endswith("m"), -d["bits"]))
hint = {}
for i_, d in enumerate(dropped):
    if i_ % 20 == 0:
        print(f"  p1 {i_}/{len(dropped)} {time.time()-t0:.0f}s", flush=True)
    lid = d["id"]
    base = lid[:-1] if lid.endswith("m") and lid[:-1] in dids else lid
    pid_list = list(d["port_ids"])
    newports_by_run = {}
    okall = True
    for (s, e) in d["runs"]:
        r = reroute_run(B, d, s, e, rep1["failed"], base, nw_hint=hint.get((base, s)) if base != lid else None)
        if r is None:
            okall = False; break
        newports_by_run[s] = (e, r)
        if base == lid:
            hint[(lid, s)] = r["wins"]
    if not okall:
        continue
    # assemble port order
    order, i = [], 0
    n = len(pid_list)
    newp_all = []
    while i < n:
        if i in newports_by_run:
            e, r = newports_by_run[i]
            order += [p["id"] for p in r["ports"]]; newp_all += r["ports"]; i = e
        else:
            order.append(pid_list[i]); i += 1
    B.raw["ports"].extend(newp_all)
    lane_obj[lid]["ports"] = order
    lane_obj[lid]["note"] = d["note"] + f" | DIE-HBM-22 replan {V['name']}: {len(d['runs'])} run(s) re-routed"
    B.P = S.Plan(B.raw)
    nat = B.P.lane_natural(lid)
    B.raw["latency"]["lanes"][lid] = dict(nat, natural=nat["cycles"], pad=0, param="LAT_" + lid.upper())
    rep1["rebuilt"].append(dict(id=lid, src=d["src"], dst=d["dst"], bits=d["bits"], cycles=nat["cycles"],
                                old_cycles=d["old_cycles"], old_chain=d["old_chain"], runs=d["runs"],
                                new_chains=[newports_by_run[s][1]["chain"] for s in sorted(newports_by_run)]))
# lanes that failed: drop them entirely (and their kept pieces) so the plan stays consistent
failed_ids = dids - {r["id"] for r in rep1["rebuilt"]}
for lid in failed_ids:
    ln = lane_obj[lid]
    keep_ports = [q for q in ln["ports"] if q not in rm_port]
    B.P = S.Plan(B.raw)
    for q in keep_ports:
        pr = B.P.ports[q]
        for side in ("src", "dst"):
            part = pr[side]["part"]
            if part in parts:
                bus = pr[side]["bus"]
                tn = parts[part]["type"]
                stem = bus[:-2]
                T[tn]["buses"] = [x for x in T[tn].get("buses", []) if x["name"] != bus]
                T[tn]["ft_slots"] = [x for x in T[tn].get("ft_slots", []) if x["name"] != stem]
B.raw["ports"] = [p for p in B.raw["ports"] if not any(p["id"] in lane_obj[l]["ports"] for l in failed_ids)]
B.raw["lanes"] = [l for l in B.raw["lanes"] if l["id"] not in failed_ids]
for l in failed_ids:
    B.raw["latency"]["lanes"].pop(l, None)
B.P = S.Plan(B.raw)
rep1["decl_conflicts"] = [x for x in rep1["failed"] if x.get("why") == "shared-type declaration differs"]
rep1["failed"] = [x for x in rep1["failed"] if x.get("why") != "shared-type declaration differs"]
print(f"phase1 rebuilt {len(rep1['rebuilt'])} failed lanes {len(failed_ids)} decl conflicts {len(rep1['decl_conflicts'])} "
      f"{time.time()-t0:.0f}s", flush=True)
raw = B.raw

def add_lane(B, d, cands, rep, ids):
    for k in (1, 2, 3, 4):
        widths = [d["bits"] // k + (1 if i < d["bits"] % k else 0) for i in range(k)]
        got = []
        for j, wbits in enumerate(widths):
            lid = ids[0] if j == 0 else f"{ids[0]}s{j}"
            B.new_id = (lambda lid_: (lambda a_, b_, part=0: lid_))(lid)
            r1 = None
            for kind, tl, chain in cands:
                if got and chain != got[0]["chain"]:
                    continue
                r1 = B.build_one(d["src"], d["dst"], wbits, chain, kind, tl, record=False)
                if r1:
                    break
            if r1 is None:
                break
            got.append(r1)
        if len(got) == k:
            return got
        if got:
            rep["failed"].append(dict(id=ids[0], src=d["src"], dst=d["dst"], why=f"partial split {len(got)}/{k}: {B._why}"))
            return got
    rep["failed"].append(dict(id=ids[0], src=d["src"], dst=d["dst"], bits=d["bits"], why=B._why,
                              chains=[c[2] for c in cands]))
    return None

LA.copy = type('C', (), {'deepcopy': staticmethod(lambda x: x)})
# phase 2: the 92 rows
rep2 = None
if a.rows92:
    rows = json.loads(Path(a.rows92).read_text())["rows"]
    B2 = LA.Builder(B.raw, near_um=a.near_um, max_hops=a.max_hops, require_cycle_match=False)
    rep2 = dict(built=[], far=[], failed=[])
    rows = sorted(rows, key=lambda r: (r["src"].startswith("NE_") or r["dst"].startswith("NE_"), -int(r["unplanned_bits"])))
    nid, idmap = 400, {}
    for r in rows:
        x, y, bits = r["src"], r["dst"], int(r["unplanned_bits"])
        e = LA.shared_edge(B2.P, x, y)
        g = LA.gap_um(B2.P, x, y)
        if e is None and g > a.near_um:
            rep2["far"].append(dict(src=x, dst=y, bits=bits, gap_um=round(g, 1)))
            continue
        cands = candidates(B2, x, y, bits)
        cands = [c for c in cands if not (set(c[2]) & B2.shared)]
        if not cands:
            rep2["failed"].append(dict(src=x, dst=y, bits=bits, why="no abutment path"))
            continue
        key = (x.replace("NE_", "NW_"), y.replace("NE_", "NW_"))
        if (x.startswith("NE_") or y.startswith("NE_")) and key in idmap:
            lid = idmap.pop(key) + "m"
        else:
            lid = f"L{nid}"; nid += 1; idmap[key] = lid
        got = add_lane(B2, dict(src=x, dst=y, bits=bits), cands, rep2, [lid])
        if got:
            for r1 in got:
                r1["split"] = len(got)
            rep2["built"].extend(got)
    raw = B2.raw
    print(f"phase2 built {len(rep2['built'])} far {len(rep2['far'])} failed {len(rep2['failed'])} {time.time()-t0:.0f}s",
          flush=True)
else:
    raw = B.raw
LA.copy = copy

out.mkdir(parents=True, exist_ok=True)
for f in plan_dir.iterdir():
    dst = out / f.name
    if f.name in ("die_plan.json",) or dst.exists():
        continue
    try:
        os.link(f, dst) if f.is_file() else os.symlink(f.resolve(), dst)
    except OSError:
        pass
raw["die"]["label"] = f"DIE-HBM-22 replan {V['name']} | " + raw["die"].get("label", "")
raw["note"] = raw.get("note", "") + f" | DIE-HBM-22 replan {V['name']}: rows A/C re-ordered by locality"
(out / "die_plan.json").write_text(json.dumps(raw, indent=1))
cyc = [r for r in rep1["rebuilt"] if r["old_cycles"] is not None and r["cycles"] != r["old_cycles"]]
rep = dict(schema="die_hbm_22.replan_event.v1", variant=V, base=str(plan_dir), base_sha=LA.sha12(plan_dir / "die_plan.json"),
           out_sha=LA.sha12(out / "die_plan.json"), moved=sorted(moved), outline_changes=outline_changes,
           dropped=len(dropped), phase1=rep1,
           cycle_changes=dict(n=len(cyc), up=sum(1 for r in cyc if r["cycles"] > r["old_cycles"]),
                              max_up=max([r["cycles"] - r["old_cycles"] for r in cyc] or [0]),
                              max_down=min([r["cycles"] - r["old_cycles"] for r in cyc] or [0])),
           phase2=None if rep2 is None else dict(
               built=len(rep2["built"]), built_bits=sum(x["bits"] for x in rep2["built"]),
               by_kind={k: sum(1 for x in rep2["built"] if x["kind"] == k) for k in ("adj", "same", "reverse", "path")},
               far=rep2["far"], far_bits=sum(x["bits"] for x in rep2["far"]), failed=rep2["failed"],
               cycle_mismatch=[dict(lane=x["lane"], src=x["src"], dst=x["dst"], cycles=x["cycles"],
                                    pair=x["existing_pair_cycles"]) for x in rep2["built"] if not x["cycles_match_pair"]],
               built_list=[dict(lane=x["lane"], src=x["src"], dst=x["dst"], bits=x["bits"], kind=x["kind"],
                                cycles=x["cycles"]) for x in rep2["built"]]),
           not_updated=["clock sidecars (clock_taps_die.json, clock_htree.json, entries.json, clock_entries.json)",
                        "pg_bumps.json", "type internal_stations / die_ft_bands of moved types"])
(out / "replan_report.json").write_text(json.dumps(rep, indent=1, default=str))
print("OUT", rep["out_sha"], f"{time.time()-t0:.0f}s")
