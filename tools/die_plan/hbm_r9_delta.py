#!/usr/bin/env python3
"""PATH-HBM-R9 (COORD 15:41 DECISION "hbm r8 decision"): opt-in HBM plan delta -- hub SERVICE QUADRANTS.
A plan that is not passed through it is unchanged (new file; no existing tool output changes).

  --hubs T1,T2 --segments S [--height-um H | auto]
      Every hub type is cut into S equal x segments; each segment becomes a SELF-CONTAINED SERVICE QUADRANT:
        replicated   every module with fewer than S instances in the hub (the whole singleton service set:
                     vmks/wbk/vms/pgp/xl_ctl/dbk and every other singleton) gets ONE copy per segment at its FULL
                     outline (same RTL module, segment lane parameter; area is the conservative full-core bound,
                     pins = the segment's own subset, so no slice is pin-limited);
        distributed  modules with >= S instances (kshare x4, pc_ctrl x16, vms_bank x8, ...) keep their instances,
                     count/S per segment, assigned by x order then improved by pairwise swaps that minimise the
                     inter-segment bits.
      Lane ownership: a station end at a N/S face pin belongs to the segment of the pin x; W face -> segment 0,
      E face -> segment S-1; a distributed instance -> its segment.  Station rewrite:
        fixed(j) - fixed(k)        one station, INTER-SEGMENT if j != k;
        replicated R - fixed(k)    R copy k <-> it (segment-local);  for an E/W face the bits are split over the
                                   copies by R's lane weight per segment (N/S face bits + bits to distributed
                                   instances there; uniform if none), each share an inter-segment link from the edge;
        replicated - replicated    copy k <-> copy k, full bits (conservative);
        collective bodies (--tree-re) get a segment combine chain copy k -> k+1 of --tree-bits (UNCHECKED width).
      Inter-segment links are registered neighbour links; they are serialised over k_x beats (ceil(bits/k_x),
      registered serialiser at launch + k_x-deep deserialiser at capture, partition logic) with the smallest k_x that
      brings the plan_cut per-sink bound <= 0.6 on every cut.  Every segment is shelf-packed with
      hub_repack.pack_hub on the 4.32 lattice; --height-um auto = smallest hub height (8.64 steps) at which every
      segment packs; every station is regenerated with hub_repack.route_station (registers in streets, hops <= reach).
Writes <out>/die_plan.json (+ r9_delta_report.json); everything else hard-linked.  The die outline is NOT changed by
this tool (hub type only); the die-level growth needed is reported (die_growth_um).
All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import collections
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR  # noqa: E402
import plan_cut as PC  # noqa: E402

r3 = HR.r3


def _on(rect, p, tol=0.5):
    for i, (x0, y0, x1, y1) in rect.items():
        if x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol:
            return i
    return None


def plan_quadrants(t, S, tree_re=r"coll_q\w*_body", tree_bits=2470):
    """topology only: replicate / distribute, segment assignment, rewritten station list with abstract ends."""
    W, H = t["outline_um"]
    seg_w = W / S
    seg = lambda x: min(S - 1, max(0, int(x // seg_w)))  # noqa: E731
    hc = {h["inst"]: h for h in t["hard_cores"]}
    rect = {i: HR._core_rect(h) for i, h in hc.items()}
    cnt = collections.Counter(h["module"] for h in hc.values())
    rep_mod = sorted(m for m, c in cnt.items() if c < S)
    dist = [i for i, h in hc.items() if cnt[h["module"]] >= S]
    st0 = t["internal_stations"]

    def end(p):
        i = _on(rect, p)
        if i:
            return ("C", i)
        if p[1] <= 0.5 or p[1] >= H - 0.5:
            return ("F", seg(p[0]))
        return ("F", 0 if p[0] <= W / 2 else S - 1)
    ends = [(end(s["from_um"]), end(s["to_um"])) for s in st0]
    isrep = lambda e: e[0] == "C" and cnt[hc[e[1]]["module"]] < S  # noqa: E731
    # distributed assignment: x order, count/S per segment, then pairwise swaps
    segof = {}
    bymod = collections.defaultdict(list)
    for i in dist:
        bymod[hc[i]["module"]].append(i)
    for m, L in bymod.items():
        L.sort(key=lambda i: hc[i]["origin_um"][0] + hc[i]["outline_um"][0] / 2)
        per = len(L) / S
        for n, i in enumerate(L):
            segof[i] = min(S - 1, int(n // per))
    adj = collections.defaultdict(collections.Counter)    # inst -> {('F',k)|inst: bits}
    for s, (a, b) in zip(st0, ends):
        for me, ot in ((a, b), (b, a)):
            if me[0] == "C" and me[1] in segof and not isrep(ot):
                key = ot if ot[0] == "F" else ot[1]
                if key != me[1]:
                    adj[me[1]][key] += s["bits"]

    def cost(i, k):
        c = 0
        for key, b in adj[i].items():
            kk = key[1] if isinstance(key, tuple) else segof[key]
            c += b * abs(kk - k)          # bits x boundaries crossed
        return c
    swaps = 0
    for _ in range(8):
        imp = False
        for m, L in bymod.items():
            for x in range(len(L)):
                for y in range(x + 1, len(L)):
                    i, j = L[x], L[y]
                    ki, kj = segof[i], segof[j]
                    if ki == kj:
                        continue
                    d0 = cost(i, ki) + cost(j, kj)
                    segof[i], segof[j] = kj, ki
                    d1 = cost(i, kj) + cost(j, ki)
                    if d1 < d0 - 1e-9:
                        swaps += 1
                        imp = True
                    else:
                        segof[i], segof[j] = ki, kj
        if not imp:
            break
    # lane weight of each replicated module per segment
    lw = collections.defaultdict(lambda: [0.0] * S)
    for s, (a, b) in zip(st0, ends):
        for me, ot in ((a, b), (b, a)):
            if isrep(me):
                m = hc[me[1]]["module"]
                if ot[0] == "F" and ot[1] in (0, S - 1) and not (min(s["from_um"][1], s["to_um"][1]) <= 0.5 or
                                                                 max(s["from_um"][1], s["to_um"][1]) >= H - 0.5):
                    continue        # E/W face: not a lane weight
                if ot[0] == "F":
                    lw[m][ot[1]] += s["bits"]
                elif ot[1] in segof:
                    lw[m][segof[ot[1]]] += s["bits"]
    share = {}
    for m in rep_mod:
        tot = sum(lw[m])
        share[m] = [v / tot for v in lw[m]] if tot > 0 else [1.0 / S] * S
    # copies: replicated module m -> one copy per segment (from original instance k % c)
    reps = collections.defaultdict(list)
    for i, h in sorted(hc.items()):
        if cnt[h["module"]] < S:
            reps[h["module"]].append(i)
    copy_name = {(m, k): f"{reps[m][k % len(reps[m])]}__q{k}" for m in rep_mod for k in range(S)}
    copies = {}
    for (m, k), n in copy_name.items():
        h = hc[reps[m][k % len(reps[m])]]
        copies[n] = dict(h, inst=n, note=(f"PATH-HBM-R9 service quadrant {k}/{S}: full-outline copy of "
                                          f"{h['module']} serving the die lanes of segment {k}"))
    # station rewrite: ends -> ('C', inst, local_xy) | ('F', None, xy) ; seg tag per end
    def loc(i, p):
        h = hc[i]
        return (p[0] - h["origin_um"][0], p[1] - h["origin_um"][1])
    stn = []
    for s, (a, b) in zip(st0, ends):
        A, B = s["from_um"], s["to_um"]

        def fx(e, P):
            if e[0] == "F":
                return ("F", None, tuple(P)), e[1]
            return ("C", e[1], loc(e[1], P)), segof[e[1]]
        ew = lambda e, P: e[0] == "F" and not (P[1] <= 0.5 or P[1] >= H - 0.5)  # noqa: E731
        ra, rb = isrep(a), isrep(b)
        if ra and rb:
            ma, mb = hc[a[1]]["module"], hc[b[1]]["module"]
            for k in range(S):
                stn.append((dict(s), ("C", copy_name[(ma, k)], loc(a[1], A)), ("C", copy_name[(mb, k)], loc(b[1], B)),
                            k, k))
        elif ra or rb:
            r, R_, o, O_ = (a, A, b, B) if ra else (b, B, a, A)
            m = hc[r[1]]["module"]
            oe, ok = fx(o, O_)
            if ew(o, O_):
                for k in range(S):
                    bits = int(math.ceil(s["bits"] * share[m][k]))
                    if bits <= 0:
                        continue
                    ce = ("C", copy_name[(m, k)], loc(r[1], R_))
                    ss = dict(s, bits=bits, r9_share=r3(share[m][k]))
                    stn.append((ss, ce, oe, k, ok) if ra else (ss, oe, ce, ok, k))
            else:
                ce = ("C", copy_name[(m, ok)], loc(r[1], R_))
                stn.append((dict(s), ce, oe, ok, ok) if ra else (dict(s), oe, ce, ok, ok))
        else:
            ea, ka = fx(a, A)
            eb, kb = fx(b, B)
            stn.append((dict(s), ea, eb, ka, kb))
    nchain = 0
    for m in rep_mod:
        if re.search(tree_re, m):
            h = hc[reps[m][0]]
            w_, h_ = h["outline_um"]
            for k in range(S - 1):
                stn.append((dict(conn=f"r9tree:{m}:{k}->{k + 1}", launch=f"{copy_name[(m, k)]}.r9_tree_out",
                                 capture=f"{copy_name[(m, k + 1)]}.r9_tree_in", bits=tree_bits, regs_um=[],
                                 note="PATH-HBM-R9 segment combine-chain link (UNCHECKED width)"),
                            ("C", copy_name[(m, k)], (w_, h_ / 2)), ("C", copy_name[(m, k + 1)], (0.0, h_ / 2)), k, k + 1))
                nchain += 1
    cores = [h for i, h in hc.items() if i in segof] + list(copies.values())
    sego = dict(segof)
    for (m, k), n in copy_name.items():
        sego[n] = k
    return dict(S=S, seg_w=seg_w, cores=cores, segof=sego, stations=stn, rep_mod=rep_mod, share=share,
                swaps=swaps, chain_links=nchain, cnt=cnt)


def boundary_bits(Q):
    S = Q["S"]
    bb = [0] * (S - 1)
    for s, ea, eb, ka, kb in Q["stations"]:
        for k in range(min(ka, kb), max(ka, kb)):
            bb[k] += s["bits"]
    return bb


def realise(t, Q, H_new, kx=1, reach=360.0, route=True, log=print):
    """pack segments in (W, H_new), map ends, serialise inter-segment links by kx, regenerate stations."""
    W, H = t["outline_um"]
    S, seg_w = Q["S"], Q["seg_w"]
    byname = {h["inst"]: h for h in Q["cores"]}
    place, infos = {}, {}
    for k in range(S):
        x0 = HR.sn(k * seg_w) if k else 0.0
        x1 = HR.sn((k + 1) * seg_w) if k < S - 1 else W
        mem = [byname[n] for n, sk in Q["segof"].items() if sk == k]
        cs = [dict(inst=h["inst"], w=h["outline_um"][0], h=h["outline_um"][1],
                   ocx=min(max(h["origin_um"][0] + h["outline_um"][0] / 2 - x0, 0), x1 - x0),
                   ocy=(h["origin_um"][1] + h["outline_um"][1] / 2) * H_new / H) for h in mem]
        pl, info = HR.pack_hub(x1 - x0, H_new, cs, shelves=tuple(q for q in (2, 3, 4, 5, 1) if q <= len(cs)),
                                reach=reach)
        for n, (x, y) in pl.items():
            place[n] = (r3(x + x0), y)
        info["x_um"] = [r3(x0), r3(x1)]
        info["cores"] = len(cs)
        info["core_area_um2"] = r3(sum(c["w"] * c["h"] for c in cs))
        info["fill"] = r3(info["core_area_um2"] / ((x1 - x0) * H_new))
        infos[k] = info
    cores = []
    for h in Q["cores"]:
        h = dict(h)
        h["origin_um"] = list(place[h["inst"]])
        cores.append(h)
    byname = {h["inst"]: h for h in cores}

    def pt(e):
        if e[0] == "F":
            x, y = e[2]
            return (x, H_new if y >= H - 0.5 else (y * H_new / H if y > 0.5 else y))
        h = byname[e[1]]
        return (r3(h["origin_um"][0] + e[2][0]), r3(h["origin_um"][1] + e[2][1]))
    R = HR.Raster(W, H_new, [HR._core_rect(h) for h in cores]) if route else None
    sy = sorted({HR.sn((a + b) / 2) for inf in infos.values() for a, b in inf["streets"]["horizontal_y_um"]})
    sx = sorted({HR.sn((v[0] + v[2]) / 2) + HR.sn(inf["x_um"][0]) for inf in infos.values()
                 for v in inf["streets"]["vertical_rects_um"]})
    out = []
    stats = dict(stations=len(Q["stations"]), inter_segment=0, serialised=0, regs_old=0, regs_new=0, latency_up=0,
                 failed=0, chain_links=Q["chain_links"])
    lat = collections.Counter()
    for s, ea, eb, ka, kb in Q["stations"]:
        s = dict(s)
        a, b = pt(ea), pt(eb)
        s["from_um"], s["to_um"] = list(a), list(b)
        s["r9_segments"] = [ka, kb]
        if ka != kb:
            stats["inter_segment"] += 1
            if kx > 1:
                s["bits_parallel"] = s["bits"]
                s["bits"] = int(math.ceil(s["bits"] / kx))
                s["serial_k"] = kx
                stats["serialised"] += 1
        n_old = len(s.get("regs_um", []))
        stats["regs_old"] += n_old
        if route:
            res = HR.route_station(R, a, b, n_old, reach, sy, sx)
            if res is None:
                stats["failed"] += 1
                stats["regs_new"] += n_old
            else:
                s["regs_um"] = [list(r) for r in res["regs"]]
                stats["regs_new"] += len(res["regs"])
                d = len(res["regs"]) - n_old
                if d > 0:
                    stats["latency_up"] += 1
                    lat[d] += 1
                s["note"] = (s.get("note", "").split(" | PATH-HBM-R9")[0] +
                             f" | PATH-HBM-R9 quadrant ({res['kind']}, {res['length_um']} um, {len(res['regs'])} st)")
        out.append(s)
    stats["latency_up_hist"] = dict(sorted(lat.items()))
    return cores, out, infos, stats


def _packs(t, Q, H):
    try:
        realise(t, Q, H, route=False)
        return True
    except ValueError:
        return False


def min_height(t, Q, H0, Hmax=14000.0, step=8.64, log=print):
    """smallest hub height (multiple of step) at which every segment packs: doubling then bisection (packing
    feasibility is monotone in the height for a fixed core set; the bracket is re-checked at the result)."""
    lo = HR.ce(H0, step)
    if _packs(t, Q, lo):
        return r3(lo)
    hi = lo
    while not _packs(t, Q, hi):
        lo = hi
        hi = HR.ce(hi * 1.25, step)
        log(f"  height {hi} probe")
        if hi > Hmax:
            raise ValueError("no hub height packs")
    while hi - lo > step + 1e-6:
        mid = HR.ce((lo + hi) / 2, step)
        if mid >= hi:
            break
        if _packs(t, Q, mid):
            hi = mid
        else:
            lo = mid
        log(f"  height bracket {lo} .. {hi}")
    return r3(hi)


def cut(t_like):
    W, H = t_like["outline_um"]
    return dict(blocked=PC._cut_profile(W, H, PC._nets(t_like), PC._cores(t_like), per_sink=True),
                unblocked=PC._cut_profile(W, H, PC._nets(t_like), PC._cores(t_like), blocked=False, per_sink=True))


def run(plan_dir, out_dir, hubs, S=4, height="auto", kx="auto", tree_bits=2470, log=print, route=True):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    T = P["partition_types"]
    rep = dict(schema="opentallas.hbm_r9_delta.v1", source_plan_sha256=hashlib.sha256(
        (plan_dir / "die_plan.json").read_bytes()).hexdigest(), segments=S, hubs={},
        note="plan arithmetic, UNCHECKED until NUMBER-CHECK (12.9f)")
    for tn in hubs:
        t = T[tn]
        W, H = t["outline_um"]
        Q = plan_quadrants(t, S, tree_bits=tree_bits)
        log(f"{tn}: S={S} cores {len(t['hard_cores'])} -> {len(Q['cores'])}, boundary bits {boundary_bits(Q)}")
        Hn = min_height(t, Q, H, log=log) if height == "auto" else float(height)
        rows = []
        ks = range(1, 9) if kx == "auto" else [int(kx)]
        chosen = None
        for k in ks:
            cores, st, infos, stats = realise(t, Q, Hn, kx=k, route=False)
            u = cut(dict(outline_um=[W, Hn], hard_cores=cores, internal_stations=st))
            mu = max(u["blocked"]["x"]["max_use"], u["blocked"]["y"]["max_use"])
            rows.append(dict(kx=k, cut_x=u["blocked"]["x"]["max_use"], cut_y=u["blocked"]["y"]["max_use"]))
            log(f"{tn}: H {Hn} kx {k} per-sink blocked x {u['blocked']['x']['max_use']} y {u['blocked']['y']['max_use']}"
                f" | unblocked x {u['unblocked']['x']['max_use']}")
            chosen = k
            if mu <= 0.6 + 1e-9:
                break
        cores, st, infos, stats = realise(t, Q, Hn, kx=chosen, route=route)
        u = cut(dict(outline_um=[W, Hn], hard_cores=cores, internal_stations=st))
        area0 = sum(h["outline_um"][0] * h["outline_um"][1] for h in t["hard_cores"])
        area1 = sum(h["outline_um"][0] * h["outline_um"][1] for h in cores)
        cnt = Q["cnt"]
        added = collections.Counter()
        for h in cores:
            if h["module"] in Q["rep_mod"]:
                added[h["module"]] += 1
        rep["hubs"][tn] = dict(
            outline_um_old=[W, H], outline_um_new=[W, Hn], hub_growth_y_um=r3(Hn - H),
            core_area_mm2_old=r3(area0 / 1e6), core_area_mm2_new=r3(area1 / 1e6),
            added_core_area_mm2=r3((area1 - area0) / 1e6), hub_area_mm2_new=r3(W * Hn / 1e6),
            replicated_modules={m: dict(instances_old=cnt[m], copies_new=added[m],
                                        lane_share=[r3(v) for v in Q["share"][m]]) for m in Q["rep_mod"]},
            distributed_swaps=Q["swaps"], boundary_bits_parallel=boundary_bits(Q),
            kx=chosen, kx_table=rows, boundary_bits_serialised=[int(math.ceil(b / chosen)) for b in boundary_bits(Q)],
            cut_per_sink=u, segment_pack={k: {kk: v for kk, v in inf.items() if kk != "streets"}
                                          for k, inf in infos.items()},
            stations=stats, segment_of={h["inst"]: Q["segof"][h["inst"]] for h in cores})
        t["outline_um"] = [W, Hn]
        t["hard_cores"] = cores
        t["internal_stations"] = st
        byname = {h["inst"]: h for h in cores}
        t["contents"] = [c for c in t.get("contents", []) if c.get("inst") in byname] + [
            dict(inst=h["inst"], module=h["module"], status="new", cells=None, note=h.get("note", ""),
                 origin_um=list(h["origin_um"]), outline_um=list(h["outline_um"])) for h in cores
            if "__q" in h["inst"]]
        for c in t["contents"]:
            if c.get("inst") in byname:
                c["origin_um"] = list(byname[c["inst"]]["origin_um"])
        t["note"] = (t.get("note", "") + f" | PATH-HBM-R9 service quadrants S={S}, height {Hn} um, "
                     f"inter-segment kx={chosen}").strip(" |")
    rep["die_growth_um"] = max([0.0] + [v["hub_growth_y_um"] for v in rep["hubs"].values()])
    P["note"] = (P.get("note", "") + f" | PATH-HBM-R9 delta: hubs {list(hubs)} service quadrants S={S} "
                 f"(type outlines only; die growth {rep['die_growth_um']} um NOT applied)").strip(" |")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ("die_plan.json", "die_plan.sha256"):
        if (out_dir / name).exists():
            (out_dir / name).unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
    sha = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "die_plan.sha256").write_text(f"{sha}  die_plan.json\n")
    rep["plan_sha256"] = sha
    (out_dir / "r9_delta_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="q_hub_nw,q_hub_ne")
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--height-um", default="auto")
    ap.add_argument("--kx", default="auto")
    ap.add_argument("--tree-bits", type=int, default=2470)
    ap.add_argument("--no-route", action="store_true")
    a = ap.parse_args(argv)
    rep = run(a.plan_dir, a.out, [x for x in a.hubs.split(",") if x], a.segments, a.height_um, a.kx, a.tree_bits,
              route=not a.no_route)
    for tn, r in rep["hubs"].items():
        c = r["cut_per_sink"]["blocked"]
        print(f"{tn}: H {r['outline_um_old'][1]} -> {r['outline_um_new'][1]} core {r['core_area_mm2_old']} -> "
              f"{r['core_area_mm2_new']} mm2 kx {r['kx']} boundary {r['boundary_bits_parallel']} cut x {c['x']['max_use']}"
              f" y {c['y']['max_use']} stations {r['stations']}")
    print("die_growth_um", rep["die_growth_um"], "plan_sha256", rep["plan_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
