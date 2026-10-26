#!/usr/bin/env python3
"""PATH-HBM-R8 (COORD 14:59 DECISION "hbm r7 decision"): opt-in HBM plan-generator delta.  A plan that is not passed
through it is unchanged (new file; no existing tool output changes).

  --hubs T1,T2 --segments S
      HUB DISTRIBUTION (no star hub, owner 10-16 / 10-17 plan (b) per-quadrant services).  The hub outline, its face
      pins and every die-level port stay as they are.  The hub is cut into S equal x segments.  A hard core whose
      N/S face traffic comes from more than one segment ("star core", face bits >= --star-min-bits) is DISTRIBUTED:
      S copies, one per segment, each serving the die lanes whose face pin lies in its segment, so a die lane lands
      at its consumer core in its own segment.  Copy class:
        replicate  module matches --replicate-re (programme / store / calendar): full outline, same module
        slice      otherwise: a NEW core type <module>__sl<S> with the outline scaled by sqrt(1/S) (lane-proportional
                   slice, area 1/S; UNCHECKED assumption, the core owner sizes it) and edge pins remapped.
      Stations: face(N/S) -> star core: to the copy in the face pin's segment; face(E/W) -> star core: one station per
      copy (a broadcast tree, one net); star -> star: copy k -> copy k (segment-local), same bits; star -> other: each
      copy -> other with ceil(bits/S) (lane share); other -> star: other -> every copy, full bits (tree).  Collective
      star cores (module matches --tree-re) get a segment chain copy k -> copy k+1 of --tree-bits (the combine tree
      of the per-segment partials; UNCHECKED width, architecture owner states it).  Every other core goes to the
      segment of the bit-weighted median x of its connections.  Each segment is shelf-packed with hub_repack.pack_hub
      (regular 4.32 bay-street lattice); every station is regenerated with hub_repack.route_station (registers in
      streets, hops <= reach).
  --banks T1,.. --bank-k q=K,key=K
      BANK k-CYCLE EXCHANGE: the idx all-to-all data ports (q_b + hid + cs_in + cs_out = query class, key = key class)
      are statically scheduled over k beats: station bits ceil(bits/k), registered serialiser at the launch pin and
      k-deep registered deserialiser at the capture pin (partition logic; cores unchanged; no numerics change).
      Control/valid/clock-pair/reset ports keep their width.  --bank-k auto picks per type the cheapest (kq, kk)
      whose plan_cut bound is <= 0.6 (cost = kq-1+1 cycles per query pass + (kk-1) x beats per key pass).

Writes <out>/die_plan.json (+ entries.json, new pin files, r8_delta_report.json); everything else hard-linked.
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

G = 4.32
QCLASS = ("q_b", "hid", "cs_in", "cs_out")
KCLASS = ("key",)


def r3(v):
    return round(float(v), 3)


def _port(launch):
    p = launch.split(".")[-1] if "." in launch else launch
    return re.sub(r"\d+$", "", p)


# ------------------------------------------------------------------------------------------------ banks
def bank_class(st):
    p = _port(st.get("launch", ""))
    if p in QCLASS:
        return "q"
    if p in KCLASS:
        return "key"
    return None


def serialise_bank(t, kq, kk):
    n = collections.Counter()
    for st in t.get("internal_stations", []):
        c = bank_class(st)
        k = kq if c == "q" else kk if c == "key" else 1
        if k > 1:
            st["bits_parallel"] = st["bits"]
            st["bits"] = int(math.ceil(st["bits"] / k))
            st["serial_k"] = k
            st["note"] = (st.get("note", "") + f" | PATH-HBM-R8 k-cycle exchange: {k} registered beats of "
                          f"{st['bits']} b (was {st['bits_parallel']} b in 1)").strip(" |")
            n[c] += 1
    return dict(n)


def bank_cut(t):
    W, H = t["outline_um"]
    c = PC._cut_profile(W, H, PC._nets(t), PC._cores(t))
    return max(c["x"].get("max_use", 0), c["y"].get("max_use", 0)), c


def choose_k(t, beats=171, kmax=8):
    rows = []
    for kq in range(1, kmax + 1):
        for kk in range(1, kmax + 1):
            tt = copy.deepcopy(t)
            serialise_bank(tt, kq, kk)
            u, _ = bank_cut(tt)
            cost_q = (kq - 1) + (1 if kq > 1 else 0)
            cost_k = (kk - 1) * beats + (1 if kk > 1 else 0)
            rows.append(dict(kq=kq, kk=kk, cut_use=r3(u), ok=u <= 0.6 + 1e-9, cycles_query_pass=cost_q,
                             cycles_key_pass_if_1beat_per_cycle=cost_k))
    ok = [r for r in rows if r["ok"]]
    best = min(ok, key=lambda r: (r["cycles_query_pass"] + r["cycles_key_pass_if_1beat_per_cycle"], r["kq"]))
    best_eq = min((r for r in ok if r["kq"] == r["kk"]), key=lambda r: r["kq"])
    return best, best_eq, rows


# ------------------------------------------------------------------------------------------------ hubs
def _on(cores, p, tol=0.5):
    for i, (x0, y0, x1, y1) in cores.items():
        if x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol:
            return i
    return None


def distribute_hub(tn, t, S, plan_dir, entries, star_min_bits=1000, replicate_re="programme|store|calendar",
                   tree_re="coll", tree_bits=2470, reach=360.0, log=print, pack=True):
    W, H = t["outline_um"]
    seg_w = W / S
    seg = lambda x: min(S - 1, max(0, int(x // seg_w)))  # noqa: E731
    hc = {h["inst"]: h for h in t["hard_cores"]}
    rect = {i: HR._core_rect(h) for i, h in hc.items()}
    st0 = t["internal_stations"]
    ends = []
    for s in st0:
        ends.append((_on(rect, s["from_um"]), _on(rect, s["to_um"])))
    face = lambda s: str(s.get("launch", "")).startswith("face")  # noqa: E731
    ns = lambda p: p[1] <= 0.5 or p[1] >= H - 0.5  # noqa: E731
    # star cores
    fsrc = collections.defaultdict(set)
    fbits = collections.Counter()
    for s, (a, b) in zip(st0, ends):
        if face(s) and b and ns(s["from_um"]):
            fsrc[b].add(seg(s["from_um"][0]))
            fbits[b] += s["bits"]
    star = sorted(i for i in hc if len(fsrc[i]) > 1 and fbits[i] >= star_min_bits)
    rep_cls = {i: ("replicate" if re.search(replicate_re, hc[i]["module"]) else "slice") for i in star}
    # copies
    new_cores, copy_of = [], {}
    f = math.sqrt(1.0 / S)
    new_pin = {}
    pin_limited = []
    for i, h in hc.items():
        if i not in star:
            continue
        w, hh = h["outline_um"]
        if rep_cls[i] == "slice":
            nw, nh = HR.ce(max(w * f, 25.92)), HR.ce(max(hh * f, 25.92))
            mod = f"{h['module']}__sl{S}"
        else:
            nw, nh, mod = w, hh, h["module"]
        pf = h.get("pins_file")
        npf = pf
        if pf and rep_cls[i] == "slice":
            pins = json.loads((plan_dir / pf).read_text())
            try:
                npins = HR.remap_pins(pins, (w, hh), (nw, nh))
            except ValueError:   # the full pin list does not fit: a slice carries ~1/S of the lane pins
                cap = 2 * (nw + nh) / HR.PIN_PITCH * 2              # 2 pin layers per edge at 0.192 um
                need = len(pins) / S
                pin_limited.append(dict(core=i, pins_full=len(pins), pins_slice_est=round(need),
                                        perimeter_capacity=round(cap), fit=need <= cap))
                clk = [q for q in pins if "clk" in str(q.get("name", q.get("bus", "")))]
                npins = HR.remap_pins(clk, (w, hh), (nw, nh)) if clk else []
            npf = HR._pin_file_name(pf, mod, nw, nh)
            new_pin[npf] = npins
        for k in range(S):
            nh_ = dict(h, inst=f"{i}__s{k}", module=mod, outline_um=[nw, nh], pins_file=npf,
                       note=(f"PATH-HBM-R8 hub distribution: {rep_cls[i]} copy {k}/{S} of {i} "
                             f"({h['module']} {w}x{hh}); serves the die lanes landing in segment {k}"))
            new_cores.append(nh_)
            copy_of[(i, k)] = nh_
        if entries is not None and mod not in entries:
            entries[mod] = dict(source="PATH-HBM-R8 plan centre entry on the 4.32 lattice (12.8a, slice type)",
                                xy=[HR.sn(nw / 2), HR.sn(nh / 2)])
    # station rewrite (core-local offsets kept, mapped into the copy outline)
    def loc(i, p):
        h = hc[i]
        return (p[0] - h["origin_um"][0], p[1] - h["origin_um"][1])

    def to_copy(i, k, p):
        h, c = hc[i], copy_of[(i, k)]
        q = HR.map_local(loc(i, p), tuple(h["outline_um"]), tuple(c["outline_um"]))
        return ("C", c["inst"], q)

    def keep(i, p):
        return ("C", i, loc(i, p)) if i else ("F", None, tuple(p))
    stn = []                         # (station dict, end_a, end_b)
    for s, (a, b) in zip(st0, ends):
        A, B = s["from_um"], s["to_um"]
        if a in star and b in star:
            for k in range(S):
                stn.append((dict(s), to_copy(a, k, A), to_copy(b, k, B)))
        elif b in star:
            if face(s) and ns(A):
                stn.append((dict(s), keep(None, A), to_copy(b, seg(A[0]), B)))
            else:
                for k in range(S):
                    stn.append((dict(s), keep(a, A), to_copy(b, k, B)))
        elif a in star:
            for k in range(S):
                stn.append((dict(s, bits=int(math.ceil(s["bits"] / S))), to_copy(a, k, A), keep(b, B)))
        else:
            stn.append((dict(s), keep(a, A), keep(b, B)))
    nchain = 0
    for i in star:
        if re.search(tree_re, hc[i]["module"]):
            c0 = copy_of[(i, 0)]
            for k in range(S - 1):
                w_, h_ = c0["outline_um"]
                stn.append((dict(conn=f"r8tree:{i}:{k}->{k + 1}", launch=f"{i}__s{k}.r8_tree_out",
                                 capture=f"{i}__s{k + 1}.r8_tree_in", bits=tree_bits, regs_um=[],
                                 note="PATH-HBM-R8 segment combine-tree link (UNCHECKED width)"),
                            ("C", f"{i}__s{k}", (w_, h_ / 2)), ("C", f"{i}__s{k + 1}", (0.0, h_ / 2))))
                nchain += 1
    cores = [h for i, h in hc.items() if i not in star] + new_cores
    byname = {h["inst"]: h for h in cores}
    # segment of each non-star core: bit-weighted median x of its other endpoints (copies at their segment centre)
    def ex(e):
        if e[0] == "F":
            return e[2][0]
        n = e[1]
        m = re.match(r"(.+)__s(\d+)$", n)
        if m and (m.group(1), int(m.group(2))) in copy_of:
            return (int(m.group(2)) + 0.5) * seg_w
        h = hc[n]
        return h["origin_um"][0] + h["outline_um"][0] / 2
    segof = {}
    for i, h in hc.items():
        if i in star:
            continue
        xs = []
        for s, ea, eb in stn:
            for me, other in ((ea, eb), (eb, ea)):
                if me[0] == "C" and me[1] == i and not (other[0] == "C" and other[1] == i):
                    xs.append((ex(other), s["bits"]))
        if not xs:
            segof[i] = seg(h["origin_um"][0] + h["outline_um"][0] / 2)
            continue
        xs.sort()
        tot = sum(b for _, b in xs)
        acc = 0
        for x, b in xs:
            acc += b
            if acc >= tot / 2:
                segof[i] = seg(x)
                break
    for (i, k), c in copy_of.items():
        segof[c["inst"]] = k
    # pack each segment (regular street lattice), balance overflow to the neighbour segment
    place, infos = {}, {}
    order = list(range(S)) if pack else []
    if not pack:   # topology-only bound: every core inside its segment (overlaps allowed), no station regeneration
        for h in cores:
            k = segof[h["inst"]]
            x0, x1 = k * seg_w, (k + 1) * seg_w
            w_ = h["outline_um"][0]
            cx = h["origin_um"][0] + w_ / 2 if h["inst"] in hc else (x0 + x1) / 2
            cx = min(max(cx, x0 + w_ / 2), x1 - w_ / 2)
            place[h["inst"]] = (r3(cx - w_ / 2), h["origin_um"][1])
    for k in order:
        x0 = HR.sn(k * seg_w) if k else 0.0
        x1 = HR.sn((k + 1) * seg_w) if k < S - 1 else W
        mem = [byname[n] for n, sk in segof.items() if sk == k]
        cs = [dict(inst=h["inst"], w=h["outline_um"][0], h=h["outline_um"][1],
                   ocx=(h["origin_um"][0] + h["outline_um"][0] / 2 if h["inst"] in hc else (x0 + x1) / 2) - x0,
                   ocy=h["origin_um"][1] + h["outline_um"][1] / 2) for h in mem]
        while True:
            try:
                pl, info = HR.pack_hub(x1 - x0, H, cs, shelves=tuple(k for k in (2, 3, 4, 5, 1) if k <= len(cs)),
                                        reach=reach)
                break
            except ValueError:
                if k == S - 1 or not cs:
                    raise
                mv = max((c for c in cs if c["inst"] in hc), key=lambda c: c["ocx"])   # push E-most to k+1
                cs.remove(mv)
                segof[mv["inst"]] = k + 1
        for n, (x, y) in pl.items():
            place[n] = (r3(x + x0), y)
        info["x_um"] = [r3(x0), r3(x1)]
        info["cores"] = len(cs)
        infos[k] = info
    for h in cores:
        h["origin_um"] = list(place[h["inst"]])
    # endpoints in type frame + station regeneration
    R = HR.Raster(W, H, [HR._core_rect(h) for h in cores])
    sy = [] if not pack else sorted({HR.sn((a + b) / 2) for inf in infos.values() for a, b in inf["streets"]["horizontal_y_um"]})
    sx = [] if not pack else sorted({HR.sn((v[0] + v[2]) / 2) + HR.sn(inf["x_um"][0]) for inf in infos.values()
                 for v in inf["streets"]["vertical_rects_um"]})

    def pt(e):
        if e[0] == "F":
            return tuple(e[2])
        h = byname[e[1]]
        return (r3(h["origin_um"][0] + e[2][0]), r3(h["origin_um"][1] + e[2][1]))
    out, stats = [], dict(stations_in=len(st0), stations_out=len(stn), regs_old=0, regs_new=0, latency_up=0,
                          failed=0, chain_links=nchain)
    lat_up = []
    for s, ea, eb in stn:
        a, b = pt(ea), pt(eb)
        n_old = len(s.get("regs_um", []))
        res = HR.route_station(R, a, b, n_old, reach, sy, sx) if pack else None
        s = dict(s, from_um=list(a), to_um=list(b))
        stats["regs_old"] += n_old
        if res is None:
            stats["failed"] += int(pack)
            stats["regs_new"] += n_old
        else:
            s["regs_um"] = [list(r) for r in res["regs"]]
            stats["regs_new"] += len(res["regs"])
            if len(res["regs"]) > n_old:
                stats["latency_up"] += 1
                lat_up.append(dict(conn=s.get("conn"), launch=s.get("launch"), regs_old=n_old,
                                   regs_new=len(res["regs"])))
            s["note"] = (s.get("note", "").split(" | PATH-HBM-R8")[0] +
                         f" | PATH-HBM-R8 regenerated ({res['kind']}, {res['length_um']} um, {len(res['regs'])} st)")
        out.append(s)
    t["hard_cores"] = cores
    t["internal_stations"] = out
    # contents + clock taps follow
    t["contents"] = [c for c in t.get("contents", []) if c.get("inst") not in star] + [
        dict(inst=c["inst"], module=c["module"], status="new", cells=None, note=c["note"],
             origin_um=list(c["origin_um"]), outline_um=list(c["outline_um"])) for c in new_cores]
    for c in t["contents"]:
        if c.get("inst") in byname:
            c["origin_um"] = list(byname[c["inst"]]["origin_um"])
    taps = []
    for tp in (t.get("clock") or {}).get("taps", []):
        inst = tp.get("name", "").split(".")[0]
        tail = tp["name"][len(inst):]
        targets = [copy_of[(inst, k)] for k in range(S)] if inst in star else [byname.get(inst)]
        for h in targets:
            if h is None:
                taps.append(tp)
                continue
            e = (entries or {}).get(h["module"], {}).get("xy", [h["outline_um"][0] / 2, h["outline_um"][1] / 2])
            taps.append(dict(tp, name=h["inst"] + tail, budget_owner=h["module"],
                             xy=[r3(h["origin_um"][0] + e[0]), r3(h["origin_um"][1] + e[1])]))
    if t.get("clock"):
        t["clock"]["taps"] = taps
    area = sum(h["outline_um"][0] * h["outline_um"][1] for h in cores) / (W * H)
    t["note"] = (t.get("note", "") + f" | PATH-HBM-R8 hub distribution: {S} segments, {len(star)} star cores "
                 f"distributed ({sum(1 for v in rep_cls.values() if v == 'slice')} slice types), die lanes land at "
                 f"their segment's copy").strip(" |")
    log(f"{tn}: S={S} star={len(star)} cores {len(hc)}->{len(cores)} area {area:.3f} stations {len(st0)}->{len(out)} "
        f"regs {stats['regs_old']}->{stats['regs_new']} latency_up {stats['latency_up']} failed {stats['failed']}")
    return dict(segments=S, star_cores={i: dict(module=hc[i]["module"], cls=rep_cls[i], face_bits=fbits[i],
                                                 face_segments=sorted(fsrc[i]), slice_pins=next((q for q in pin_limited if q['core'] == i), None)) for i in star},
                core_area_frac=r3(area), segment_pack=infos, stations=stats, latency_up=lat_up[:4000],
                segment_of={n: k for n, k in sorted(segof.items())}), new_pin


# ------------------------------------------------------------------------------------------------ driver
def run(plan_dir, out_dir, hubs=(), segments=4, banks=(), bank_k="auto", tree_bits=2470, log=print, **kw):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    ep = plan_dir / "entries.json"
    entries = json.loads(ep.read_text()) if ep.exists() else None
    T = P["partition_types"]
    rep = dict(schema="opentallas.hbm_r8_delta.v1", source_plan_sha256=hashlib.sha256(
        (plan_dir / "die_plan.json").read_bytes()).hexdigest(), hubs={}, banks={},
        note="plan arithmetic, UNCHECKED until NUMBER-CHECK (12.9f)")
    pins = {}
    for tn in banks:
        t = T[tn]
        before = bank_cut(t)[0]
        best, best_eq, rows = choose_k(t)
        if bank_k == "auto":
            kq, kk = best_eq["kq"], best_eq["kk"]
        else:
            d = dict(x.split("=") for x in bank_k.split(","))
            kq, kk = int(d.get("q", 1)), int(d.get("key", 1))
        n = serialise_bank(t, kq, kk)
        u, c = bank_cut(t)
        rep["banks"][tn] = dict(cut_use_before=r3(before), kq=kq, kk=kk, cut_use_after=r3(u), cut=c,
                                stations_serialised=n, cheapest_ok=best, smallest_equal_k_ok=best_eq,
                                table=[r for r in rows if r["kq"] <= 6 and r["kk"] <= 6])
        log(f"{tn}: cut {before:.3f} -> {u:.3f} at kq={kq} kk={kk} (cheapest ok {best['kq']}/{best['kk']})")
    for tn in hubs:
        r, np_ = distribute_hub(tn, T[tn], segments, plan_dir, entries, tree_bits=tree_bits, log=log, **kw)
        rep["hubs"][tn] = r
        pins.update(np_)
    P["note"] = (P.get("note", "") + f" | PATH-HBM-R8 delta: hubs {list(hubs)} distributed S={segments}; banks "
                 f"{list(banks)} k-cycle idx exchange").strip(" |")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ("die_plan.json", "entries.json", "die_plan.sha256"):
        if (out_dir / name).exists():
            (out_dir / name).unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
    if entries is not None:
        (out_dir / "entries.json").write_text(json.dumps(entries, indent=1, sort_keys=True) + "\n")
    for npf, pp in pins.items():
        q = out_dir / npf
        if q.exists():
            q.unlink()
        q.write_text(json.dumps(pp) + "\n")
    sha = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "die_plan.sha256").write_text(f"{sha}  die_plan.json\n")
    rep["plan_sha256"] = sha
    rep["plan_cut"] = PC.analyse(P, [x for x in list(hubs) + list(banks)])
    for tn in list(hubs) + list(banks):
        t = T[tn]
        Wt, Ht = t["outline_um"]
        rep["plan_cut"]["types"][tn]["cut_per_sink"] = PC._cut_profile(Wt, Ht, PC._nets(t), PC._cores(t),
                                                                       per_sink=True)
        rep["plan_cut"]["types"][tn]["cut_per_sink_unblocked"] = PC._cut_profile(
            Wt, Ht, PC._nets(t), PC._cores(t), blocked=False, per_sink=True)
    if not kw.get("pack", True):
        for tn in hubs:
            t = T[tn]
            Wt, Ht = t["outline_um"]
            rep["plan_cut"]["types"][tn]["cut_unblocked"] = PC._cut_profile(Wt, Ht, PC._nets(t), PC._cores(t),
                                                                            blocked=False)
    (out_dir / "r8_delta_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="")
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--banks", default="")
    ap.add_argument("--bank-k", default="auto", help="auto | q=K,key=K")
    ap.add_argument("--tree-bits", type=int, default=2470)
    ap.add_argument("--star-min-bits", type=int, default=1000)
    ap.add_argument("--no-pack", action="store_true", help="topology-only cut bound (cores in their segment, "
                    "overlaps allowed, stations not regenerated): NOT a legal plan")
    a = ap.parse_args(argv)
    rep = run(a.plan_dir, a.out, [x for x in a.hubs.split(",") if x], a.segments, [x for x in a.banks.split(",") if x],
              a.bank_k, a.tree_bits, star_min_bits=a.star_min_bits, pack=not a.no_pack)
    pc = rep["plan_cut"]
    for tn, r in pc["types"].items():
        print(f"{tn:12s} {r['verdict']} cut x {r['cut']['x'].get('max_use')} y {r['cut']['y'].get('max_use')}")
    print("plan_sha256", rep["plan_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
