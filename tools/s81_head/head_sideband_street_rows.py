#!/usr/bin/env python3
"""FABLE-DIE-HEAD NF14 = NF13b + landing sideband reach rows (FABLE-CLOSURE lever C) on hd_lep0N and hd_ctl.
Same plan keys and helpers as tools/s81_head/head_cland_stage_delta.py (local_resets, nearest, rrl_from_rtl, republish);
the only difference: stage sites follow a street path round the hard cores instead of the straight segment (hd_lep0N has
four 777.6 x 492.48 cores), every path hop <= HMAX.  0 data cycles; sidecar unchanged.
usage: head_sideband_street_rows.py TOOLS_ROOT SRC_PREP OUT_PREP [--types hd_lep0N,hd_ctl] [--no-republish]
Types on the region-reset form (hd_ctl) take the depth of their tap wavefront relay."""
import sys, json, re, math, heapq, shutil, hashlib
from pathlib import Path
_H = Path(__file__).resolve().parent
sys.path[:0] = [str(_H.parent / "die_plan"), str(_H)]
import head_cland_stage_delta as m
HMAX, G, KEEP = m.HMAX, 10.0, 6.0
md = m.md


class Streets:
    def __init__(s, T):
        s.W, s.H = T["outline_um"]
        s.cores = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
                   for h in T.get("hard_cores", [])]
        s.NX, s.NY = int(s.W // G) + 1, int(s.H // G) + 1
        s.free = [[s.ok(i * G, j * G) for j in range(s.NY)] for i in range(s.NX)]
        s.cache = {}

    def ok(s, x, y):
        if not (KEEP <= x <= s.W - KEEP and KEEP <= y <= s.H - KEEP): return False
        return not any(a - KEEP < x < c + KEEP and b - KEEP < y < d + KEEP for a, b, c, d in s.cores)

    def snap(s, p):
        return min(((abs(i * G - p[0]) + abs(j * G - p[1]), i, j) for i in range(s.NX) for j in range(s.NY) if s.free[i][j]))[1:]

    def legal(s, p):
        if s.ok(p[0], p[1]): return (round(p[0], 2), round(p[1], 2))
        i, j = s.snap(p); return (i * G, j * G)

    def path(s, a, b):
        k = (tuple(a), tuple(b))
        if k in s.cache: return s.cache[k]
        st, en = s.snap(a), s.snap(b); dist = {st: 0.0}; prev = {}; pq = [(0.0, st)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == en: break
            if d > dist[u]: continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (u[0] + di, u[1] + dj)
                if 0 <= v[0] < s.NX and 0 <= v[1] < s.NY and s.free[v[0]][v[1]]:
                    nd = d + G + (0.01 if u in prev and (u[0] - prev[u][0], u[1] - prev[u][1]) != (di, dj) else 0)
                    if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        pts = [en]
        while pts[-1] != st: pts.append(prev[pts[-1]])
        r = [tuple(a)] + [(q[0] * G, q[1] * G) for q in reversed(pts)] + [tuple(b)]
        s.cache[k] = r
        return r

    def chain(s, a, ea, b, eb, n=None):
        """(stage points, hop um): n points on the street path a -> b, equal hops, end extents charged to the end hops"""
        pp = s.path(a, b); L = sum(md(pp[i], pp[i + 1]) for i in range(len(pp) - 1)); tot = L + ea + eb
        need = max(0, math.ceil(tot / HMAX - 1e-9) - 1)
        n = need if n is None else max(n, need)
        h = tot / (n + 1); out = []; want = [min(max(h * (k + 1) - ea, 0.0), L) for k in range(n)]; acc = 0.0; k = 0
        for i in range(len(pp) - 1):
            seg = md(pp[i], pp[i + 1])
            while k < n and want[k] <= acc + seg + 1e-9:
                f = (want[k] - acc) / seg if seg else 0.0
                out.append(s.legal((pp[i][0] + (pp[i + 1][0] - pp[i][0]) * f, pp[i][1] + (pp[i + 1][1] - pp[i][1]) * f))); k += 1
            acc += seg
        while k < n: out.append(s.legal(pp[-1])); k += 1
        return out, h


def build(tn, T, coll, wrapper):
    c = T["clock"]; S = Streets(T); pins = m.pins_of(T); rep = dict(type=tn); worst = [0.0, ""]
    def note(name, h):
        if h > worst[0]: worst[:] = [h, name]
    rrl = m.rrl_from_rtl(wrapper); dep = {r[0]: r[1] for r in rrl}
    text = Path(wrapper).read_text()
    rd = {b: dep[n] + 1 for b, n in re.findall(r"ot_dp_rrelay u_cland_rst_(\w+) \(\.clk\(clk\), \.d\((\w+)\)", text) if n in dep}
    if not rd:
        # region-reset form (hd_ctl): the collects and the FSTART face flops take a timed tap wavefront relay rst_n_t<k>
        # directly, so the landing-control depth is that relay's own depth (no ring reset relay on top)
        nets = set(re.findall(r"ot_dp_landing_collect[^;]*?\.rst_n\((rst_n_t\d+)\)", text)) | set(re.findall(r"assign cland_start_raw = (rst_n_t\d+);", text))
        tdep = {n: int(d) for n, d in re.findall(r"\.q\((rst_n_t\d+)\)\);\s*//[^\n]*?depth (\d+)", text)}
        rd = {n: tdep[n] for n in sorted(nets)}
        rep["reset_form"] = "region"
    assert rd, (tn, "no landing-control reset found")
    depth = max(rd.values()); rep["ring_reset_depths"] = rd
    assert len(set(rd.values())) == 1, (tn, "ring reset depths differ", rd)
    origin = tuple(c["start_capture_um"])
    bands = {b: m.band_geom(v["rect_um"]) for b, v in c["landing_contract"]["bands"].items()}
    mask = coll["mask"]; rings = list(mask["inputs"]); tree = mask["tree_bus"]; ndep = int(coll["local_registered_depth"])
    add, consumers = {}, {}
    have_reader = "landing_reader_start" in c
    for k in ("landing_writer_start", "landing_status_input_stages", "landing_local_resets"): assert k not in c, (tn, k)
    if not have_reader:
        R = max(len(S.chain(origin, m.ORIGIN_EXT, *bands[b])[0]) for b in rings); br = {}
        for b in rings:
            pts, h = S.chain(origin, m.ORIGIN_EXT, bands[b][0], bands[b][1], R); note("reader:" + b, h)
            br[b] = {"stages": [dict(xy_um=m.rnd(p), raw_reset=m.nearest(rrl, p, allow_exported=False)[0]) for p in pts]}
        if R:
            add["landing_reader_start"] = dict(depth=R, origin_rect_um=[round(origin[0] - 8.64, 2), round(origin[1] - 8.64, 2),
                                                                        round(origin[0] + 8.64, 2), round(origin[1] + 8.64, 2)], branches=br)
        consumers["u_cland_origin"] = origin; rep["reader_start_depth"] = R
    outs = [b for b in mask["outputs"] if f"cland_fstart_out_{b}" in pins]
    need = {b: len(S.chain(origin, m.ORIGIN_EXT, tuple(pins[f"cland_fstart_out_{b}"]), 0.0)[0]) for b in outs}
    W = max(need.values()) if need else 0; far = sorted(b for b, n in need.items() if n)
    if W:
        wb = {}
        for b in far:
            pts, h = S.chain(origin, m.ORIGIN_EXT, tuple(pins[f"cland_fstart_out_{b}"]), 0.0, W); note("writer:" + b, h)
            wb[b] = {"stages": [dict(xy_um=m.rnd(p), raw_reset=m.nearest(rrl, p, allow_exported=False)[0]) for p in pts]}
        add["landing_writer_start"] = dict(depth=W, branches=wb)
    for b in outs: consumers[f"u_cland_fstart_{b}"] = tuple(pins[f"cland_fstart_out_{b}"])
    rep["writer_start_depth"] = W; rep["writer_far"] = far
    targets = {}
    if tree and "landing_status_anchors" not in c:
        root_xy = tuple(coll.get("collector_root_xy") or pins[f"cland_up_ready_{tree}"])
        a1 = S.legal(tuple(sum(bands[b][0][i] for b in rings) / len(rings) for i in (0, 1)))
        pts, h = S.chain(a1, 0.0, root_xy, 0.0, ndep - 2); note("agg", h)
        assert len(pts) == ndep - 2, (tn, "agg chain needs depth", len(pts) + 2, "has", ndep)
        anchors = {"u_cland_agg_1": a1}
        for k, p in enumerate(pts): anchors[f"u_cland_agg_{k + 2}"] = p
        add["landing_status_anchors"] = {k: m.rnd(v) for k, v in anchors.items()}
        consumers.update(anchors); consumers[f"u_cland_up_{tree}"] = root_xy; targets["agg"] = a1
    for b in mask["outputs"]:
        if b != tree and pins.get(f"cland_up_ready_{b}"):
            targets[b] = tuple(pins[f"cland_up_ready_{b}"]); consumers[f"u_cland_up_{b}"] = targets[b]
    sis, nsin = {}, 0
    for tgt, tp in targets.items():
        for r in rings:
            pts, h = S.chain(bands[r][0], bands[r][1], tp, 0.0); note(f"sin:{tgt}:{r}", h)
            if not pts: continue
            sis.setdefault(tgt, {})[r] = [dict(xy_um=m.rnd(p)) for p in pts]
            for k, p in enumerate(pts): consumers[f"u_cland_sin_{tgt}_{r}_{k}"] = p
            nsin += len(pts)
    if sis: add["landing_status_input_stages"] = sis
    add["landing_local_resets"] = m.local_resets(rrl, depth, consumers)
    rep.update(status_relays=nsin, status_input_stages={t: {r: len(v) for r, v in rr.items()} for t, rr in sis.items()},
               local_reset_copies=len(add["landing_local_resets"]), worst_path_hop_um=[worst[1], round(worst[0], 1)],
               boot_extra_cycles=rep.get("reader_start_depth", 0) + W, steady_data_cycles_added=0, ctrl_depth=depth)
    return add, rep


def main(argv):
    ROOT, SRC, OUT = Path(argv[1]), Path(argv[2]), Path(argv[3])
    TYPES = argv[argv.index("--types") + 1].split(",") if "--types" in argv else ["hd_lep0N", "hd_ctl"]
    plan = json.loads((SRC / "source_plan.json").read_text()); side = json.loads((SRC / "source_sidecar.json").read_text())
    report = {}
    for tn in TYPES:
        T = plan["partition_types"][tn]
        add, rep = build(tn, T, side["collector"]["types"][tn], SRC / "published" / (T["module"] + ".sv"))
        T["clock"].update(add); report[tn] = rep
        T["note"] += (" | FABLE-DIE-HEAD rp21z20NF14 (11-16, FABLE-CLOSURE lever C): landing sideband reach rows %s on street paths, "
                      "every hop <= 370 um, 0 data cycles" % "/".join(sorted(add)))
        print(tn, json.dumps({k: v for k, v in rep.items() if k != "status_input_stages"}))
    if OUT.exists(): raise SystemExit("OUT exists")
    shutil.copytree(SRC, OUT, symlinks=True); m.writable(OUT)
    (OUT / "source_plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    (OUT / "nf14_report.json").write_text(json.dumps(report, indent=1) + "\n")
    if "--no-republish" not in argv:
        m.republish(OUT, ROOT.resolve(), TYPES, OUT / "source_sidecar.json")
    print("plan sha256", hashlib.sha256((OUT / "source_plan.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    main(sys.argv)
