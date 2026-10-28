#!/usr/bin/env python3
"""DIE-S81-8 opaque-hop estimator (info only, NOT a gate).

Per die plan JSON: hard cores whose LEF OBS makes them opaque to the partition routing stack
(coverage >= OPAQ_FRAC on every routing layer M2..top), opaque area fraction per type, narrowest soft
channels between opaque cores, declared internal_stations segments (straight + both Manhattan L) crossing an
opaque core interior, and a face-bus straight-projection proxy for relay hops (relay connectivity is not in
the plan).  LEFs are read from the repo object store (git show <rev>:path).

usage: opaque_hops.py --repo <git dir/worktree> --rev origin/main --out <dir> die=plan.json [die=plan.json ...]
"""
import argparse, collections, hashlib, json, re, subprocess, sys
import numpy as np

OPAQ_FRAC = 0.30
MARGIN = 2.0   # um: shrink core boxes so pin-edge endpoints do not count as crossings
G = 0.25       # um raster for LEF OBS coverage
GC = 4.32      # um bins for the 'any OBS in bin' (GRT-like gcell) coverage


def lnum(L):
    return int(str(L)[1:])


class Repo:
    def __init__(self, repo, rev):
        self.repo, self.rev = repo, rev
        names = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", rev], capture_output=True,
                               text=True, check=True).stdout.split("\n")
        self.lefs = collections.defaultdict(list)
        for n in names:
            if n.endswith(".lef"):
                self.lefs[n.rsplit("/", 1)[-1][:-4]].append(n)
        self.cache = {}

    def show(self, path):
        if path not in self.cache:
            r = subprocess.run(["git", "-C", self.repo, "show", f"{self.rev}:{path}"], capture_output=True, text=True)
            self.cache[path] = r.stdout if r.returncode == 0 else None
        return self.cache[path]


def lef_cov(text, module):
    """per-layer OBS coverage (area fraction at G raster, and any-hit fraction at GC bins) of MACRO module."""
    m = re.search(r"\nMACRO\s+%s\b(.*?)\nEND\s+%s\b" % (re.escape(module), re.escape(module)), text, re.S)
    body = m.group(1) if m else text
    W, H = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body).groups())
    i = body.find("\n  OBS")
    if i < 0:
        i = body.find("OBS")
    obs = body[i:] if i >= 0 else ""
    nx, ny = int(np.ceil(W / G)), int(np.ceil(H / G))
    cov, lay = {}, None
    for line in obs.split("\n"):
        mm = re.match(r"\s*LAYER\s+(\S+)", line)
        if mm:
            lay = mm.group(1)
            cov.setdefault(lay, np.zeros((ny, nx), bool))
            continue
        for mm in re.finditer(r"RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", line):
            if lay:
                x0, y0, x1, y1 = map(float, mm.groups())
                cov[lay][max(0, int(y0 / G)):int(np.ceil(y1 / G)), max(0, int(x0 / G)):int(np.ceil(x1 / G))] = True
    out = {}
    k = max(1, int(round(GC / G)))
    for L, a in cov.items():
        if not re.fullmatch(r"M\d+", L):
            continue
        py, px = (-a.shape[0]) % k, (-a.shape[1]) % k
        b = np.pad(a, ((0, py), (0, px))).reshape((a.shape[0] + py) // k, k, (a.shape[1] + px) // k, k).any(axis=(1, 3))
        out[L] = (round(float(a.mean()), 3), round(float(b.mean()), 3))
    return (W, H), out


def seg_hits(p, q, boxes):
    """indices of boxes whose (MARGIN-shrunk) interior the segment p->q intersects (Liang-Barsky)."""
    hits = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        x0, y0, x1, y1 = x0 + MARGIN, y0 + MARGIN, x1 - MARGIN, y1 - MARGIN
        if x1 <= x0 or y1 <= y0:
            continue
        dx, dy = q[0] - p[0], q[1] - p[1]
        t0, t1, ok = 0.0, 1.0, True
        for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
            if pp == 0:
                if qq < 0:
                    ok = False
                    break
            else:
                t = qq / pp
                if pp < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
        if ok and t0 < t1:
            hits.append(i)
    return hits


def channels(W, H, boxes):
    """narrowest interior gap between two opaque boxes that face each other with nothing between (V = side by
    side, H = stacked), edge free sides, and min over rows/cols of the soft cut width."""
    best = {"V": None, "H": None}
    for ax, (lo, hi, olo, ohi) in (("V", (0, 2, 1, 3)), ("H", (1, 3, 0, 2))):
        for a in boxes:
            for b in boxes:
                if b[lo] < a[hi]:
                    continue
                ov0, ov1 = max(a[olo], b[olo]), min(a[ohi], b[ohi])
                if ov1 - ov0 < 10:
                    continue
                gap = b[lo] - a[hi]
                if gap <= 0.5:
                    continue
                blocked = any(c is not a and c is not b and c[lo] < b[lo] and c[hi] > a[hi] and
                              c[olo] < ov1 and c[ohi] > ov0 for c in boxes)
                if not blocked and (best[ax] is None or gap < best[ax][0]):
                    best[ax] = (round(gap, 2), round(a[hi], 2), round(b[lo], 2), round(ov0, 1), round(ov1, 1))
    # soft cut width: for N-S crossing at row y, free x length; min over y where any core sits
    g = 1.0
    nx, ny = int(np.ceil(W / g)), int(np.ceil(H / g))
    m = np.zeros((ny, nx), bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, int(y0 / g)):int(np.ceil(y1 / g)), max(0, int(x0 / g)):int(np.ceil(x1 / g))] = True
    rows, cols = m.any(1), m.any(0)
    ns = int((~m[rows]).sum(1).min()) if rows.any() else nx
    ew = int((~m[:, cols]).sum(0).min()) if cols.any() else ny
    edge = {}
    if boxes:
        edge = {"W": round(min(b[0] for b in boxes), 1), "E": round(W - max(b[2] for b in boxes), 1),
                "S": round(min(b[1] for b in boxes), 1), "N": round(H - max(b[3] for b in boxes), 1)}
    return best, edge, ns, ew, round(float(m.mean()), 4)


def kit_ceilings(R, mods, globs):
    """module -> (route ceiling, source) from hard-core kit configs (MAX_ROUTING_LAYER / RLAYERS) whose kit dir
    basename starts with the module name: repo tree at rev + optional scratch globs (newest wins for scratch)."""
    import glob as _g, os
    out = {}
    def parse(txt):
        m = re.search(r"MAX_ROUTING_LAYER\s*\??=\s*(M\d+)", txt) or re.search(r"RLAYERS='?M\d+\s+(M\d+)", txt)
        return m.group(1) if m else None
    tree = subprocess.run(["git", "-C", R.repo, "ls-tree", "-r", "--name-only", R.rev], capture_output=True,
                          text=True).stdout.split("\n")
    for n in tree:
        if not (n.endswith("/config.mk") or n.endswith("/kit.env")):
            continue
        d = n.rsplit("/", 2)[-2]
        for m in mods:
            if d.startswith(m) and m not in out:
                c = parse(R.show(n) or "")
                if c:
                    out[m] = (c, "repo:" + n)
    for gl in globs:
        for f in sorted(_g.glob(gl), key=lambda f: os.path.getmtime(f)):
            d = os.path.basename(os.path.dirname(f))
            for m in mods:
                if d.startswith(m + "_") or d == m:
                    c = parse(open(f).read())
                    if c:
                        out[m] = (c, "scratch:" + f)
    return out


def resolve_lef(R, h, t, die_key):
    if h.get("lef"):
        return h["lef"], "plan"
    for c in t.get("contents", []):
        if c.get("lef") and (c["inst"] == h["inst"] or h["inst"].startswith(c["inst"] + "_")):
            return c["lef"], "contents"
    cands = R.lefs.get(h["module"], [])
    if not cands:
        return None, "none"
    W, H = h["outline_um"]
    sized = []
    for pth in cands:
        txt = R.show(pth)
        if not txt:
            continue
        mm = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
        if mm:
            w, hh = map(float, mm.groups())
            if (abs(w - W) < 0.05 and abs(hh - H) < 0.05) or (abs(w - H) < 0.05 and abs(hh - W) < 0.05):
                sized.append(pth)
    pick = sized or cands
    pick.sort(key=lambda s: (die_key not in s, len(s)))
    return pick[0], "search:%d/%d" % (len(sized), len(cands))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--rev", default="origin/main")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-type", default=None)
    ap.add_argument("--kit-glob", action="append", default=[], help="scratch kit config.mk globs for cores w/o LEF")
    ap.add_argument("--nolef-default", default=None,
                    help="ceiling for cores with no LEF, no kit config and no plan obs_max (default: partition top, g2 rule)")
    ap.add_argument("plans", nargs="+")
    a = ap.parse_args()
    R = Repo(a.repo, a.rev)
    covcache = {}
    summary = []
    for spec in a.plans:
        die, path = spec.split("=", 1)
        raw = open(path, "rb").read()
        sha = hashlib.sha256(raw).hexdigest()[:12]
        P = json.loads(raw)
        lb = P["die"].get("layer_budget", {})
        top = lb.get("partition_signal_max", "M7")
        top_src = "layer_budget.partition_signal_max" if "partition_signal_max" in lb else "default M7"
        ninst = collections.Counter(p["type"] for p in P["partitions"])
        dkey = {"s81": "s81_die", "s81_head": "s81_head", "qwen_compute": "qwen_compute", "qwen_kvsys": "qwen_kvsys",
                "hbm": "hbm"}.get(die.split("_s5")[0], die)
        rows, unres, g2_only_opaque = [], set(), set()
        nolef = set()
        for t in P["partition_types"].values():
            for h in t.get("hard_cores", []):
                if resolve_lef(R, h, t, dkey)[0] is None:
                    nolef.add(h["module"])
        kc = kit_ceilings(R, nolef, a.kit_glob) if nolef else {}
        for tn, t in sorted(P["partition_types"].items()):
            if a.only_type and tn != a.only_type:
                continue
            W, H = t["outline_um"]
            cores = [h for h in t.get("hard_cores", []) if "origin_um" in h and "outline_um" in h]
            # content leaves with a LEF and position that no hard core covers are also blockages (g2.probe_blockages)
            hc_inst = {h["inst"] for h in cores}
            for c in t.get("contents", []):
                if c.get("lef") and "origin_um" in c and "outline_um" in c and not any(
                        i == c["inst"] or i.startswith(c["inst"] + "_") for i in hc_inst):
                    cores.append(c)
            opq, info = [], []
            for h in cores:
                lef, how = resolve_lef(R, h, t, dkey)
                key = (lef, h["module"])
                if lef and key not in covcache:
                    txt = R.show(lef)
                    try:
                        covcache[key] = lef_cov(txt, h["module"]) if txt else None
                    except Exception as e:  # noqa
                        covcache[key] = None
                cv = covcache.get(key) if lef else None
                if cv is None:
                    unres.add(h["module"])
                    # no LEF: core kit route ceiling if found, else plan obs_max (g2 rule: absent -> partition top)
                    om_plan = h.get("obs_max", a.nolef_default or top)
                    if h["module"] in kc:
                        om, src = kc[h["module"]]
                        how = "NO-LEF->kit %s (%s); plan/g2 %s" % (om, src, om_plan)
                    else:
                        om, how = om_plan, "NO-LEF->plan/g2 obs_max " + str(om_plan)
                    is_op, frac = lnum(om) >= lnum(top), {}
                    if lnum(om_plan) >= lnum(top):
                        g2_only_opaque.add(h["module"])
                else:
                    frac = cv[1]
                    layers = ["M%d" % i for i in range(2, lnum(top) + 1)]
                    is_op = all(frac.get(L, (0, 0))[0] >= OPAQ_FRAC for L in layers)
                x0, y0 = h["origin_um"]
                w, hh = h["outline_um"]
                box = (x0, y0, x0 + w, y0 + hh)
                info.append(dict(inst=h["inst"], module=h["module"], opaque=is_op, lef_how=how, box=box,
                                 obs_max_plan=h.get("obs_max"),
                                 cov={L: v for L, v in sorted(frac.items(), key=lambda kv: lnum(kv[0]))}))
                if is_op:
                    opq.append(box)
            # declared internal_stations segments
            nseg = nstr = nl = nconn = 0
            crossed_conn = collections.Counter()
            for s in t.get("internal_stations", []):
                pts = [s["from_um"]] + list(s.get("regs_um", [])) + [s["to_um"]]
                hit_any = False
                for p, q in zip(pts, pts[1:]):
                    nseg += 1
                    st = seg_hits(p, q, opq)
                    l1 = seg_hits(p, (q[0], p[1]), opq) + seg_hits((q[0], p[1]), q, opq)
                    l2 = seg_hits(p, (p[0], q[1]), opq) + seg_hits((p[0], q[1]), q, opq)
                    if st:
                        nstr += 1
                        hit_any = True
                    if l1 and l2:
                        nl += 1
                if hit_any:
                    nconn += 1
                    crossed_conn[s.get("conn", "?")] += 1
            # face-bus straight projection proxy: bus bits whose window, projected straight across the type
            # (N/S windows vertically, E/W horizontally), lands on an opaque core column/row
            bus_bits = bus_blk = 0.0
            for b in t.get("buses", []):
                w0, w1 = b.get("window_um", [0, 0])
                wid = b.get("width", 0) or 0
                if w1 <= w0 or not wid:
                    continue
                bus_bits += wid
                vert = b.get("face") in ("N", "S")
                ivs = [((bx[0], bx[2]) if vert else (bx[1], bx[3])) for bx in opq]
                xs = np.linspace(w0, w1, 200)
                blk = np.array([any(lo < x < hi for lo, hi in ivs) for x in xs]).mean()
                bus_blk += wid * blk
            ch, edge, ns, ew, afrac = channels(W, H, opq)
            rows.append(dict(type=tn, inst=ninst.get(tn, 0), n_cores=len(cores), n_opaque=len(opq),
                             opaque_modules=sorted({i["module"] for i in info if i["opaque"]}),
                             opaque_area_frac=afrac, min_v_channel=ch["V"], min_h_channel=ch["H"], edge_free=edge,
                             min_soft_ns_width_um=ns, min_soft_ew_width_um=ew,
                             ist_entries=len(t.get("internal_stations", [])), ist_segs=nseg,
                             ist_segs_straight_cross=nstr, ist_segs_both_L_cross=nl, ist_entries_cross=nconn,
                             bus_bits=int(bus_bits), bus_bits_straight_over_opaque=int(round(bus_blk)),
                             cores=info))
        op_rows = [r for r in rows if r["n_opaque"]]
        insts_all = sum(r["inst"] for r in rows)
        op_insts = sum(r["inst"] for r in op_rows)
        mods = collections.Counter(m for r in op_rows for m in r["opaque_modules"])
        aw = (sum(r["opaque_area_frac"] * r["inst"] for r in op_rows) / op_insts) if op_insts else 0
        vmins = [r["min_v_channel"][0] for r in op_rows if r["min_v_channel"]]
        hmins = [r["min_h_channel"][0] for r in op_rows if r["min_h_channel"]]
        sm = dict(die=die, plan=path, sha=sha, top=top, top_src=top_src, types=len(rows), insts=insts_all,
                  types_opaque=len(op_rows), insts_opaque=op_insts, opaque_modules=dict(mods),
                  opaque_area_pct_inst_weighted=round(100 * aw, 1),
                  opaque_area_pct_max=round(100 * max([r["opaque_area_frac"] for r in op_rows] or [0]), 1),
                  min_v_channel_um=min(vmins) if vmins else None, min_h_channel_um=min(hmins) if hmins else None,
                  ist_segs=sum(r["ist_segs"] for r in rows),
                  ist_segs_straight_cross=sum(r["ist_segs_straight_cross"] for r in rows),
                  ist_segs_both_L_cross=sum(r["ist_segs_both_L_cross"] for r in rows),
                  ist_segs_straight_cross_x_inst=sum(r["ist_segs_straight_cross"] * r["inst"] for r in rows),
                  bus_bits_over_opaque_x_inst=sum(r["bus_bits_straight_over_opaque"] * r["inst"] for r in rows),
                  no_lef_modules=len(unres),
                  no_lef_ceiling_from_kit=sorted(m for m in unres if m in kc),
                  no_lef_ceiling_kit_values=dict(collections.Counter(kc[m][0] for m in unres if m in kc)),
                  no_lef_no_kit_plan_default=sorted(m for m in unres if m not in kc),
                  lef_by_search_size_mismatch=sorted({c["module"] for r in rows for c in r["cores"]
                                                      if c["lef_how"].startswith("search:0/")}))
        summary.append(sm)
        json.dump(dict(summary=sm, types=rows), open(f"{a.out}/{die}.json", "w"), indent=1, default=str)
        with open(f"{a.out}/{die}_types.tsv", "w") as f:
            f.write("type\tinst\tn_cores\tn_opaque\topaque_area%\tmin_V_ch\tmin_H_ch\tedge_free\tns_soft\tew_soft"
                    "\tist_segs\tist_x_str\tist_x_bothL\tbus_bits\tbus_over_opq\topaque_modules\n")
            for r in rows:
                f.write("\t".join(map(str, [r["type"], r["inst"], r["n_cores"], r["n_opaque"],
                                            round(100 * r["opaque_area_frac"], 1), r["min_v_channel"],
                                            r["min_h_channel"], r["edge_free"], r["min_soft_ns_width_um"],
                                            r["min_soft_ew_width_um"], r["ist_segs"], r["ist_segs_straight_cross"],
                                            r["ist_segs_both_L_cross"], r["bus_bits"],
                                            r["bus_bits_straight_over_opaque"], ",".join(r["opaque_modules"])])) + "\n")
        print(json.dumps({k: (v if not isinstance(v, (list, dict)) or len(v) < 12 else "len%d" % len(v))
                          for k, v in sm.items()}))
        sys.stdout.flush()
    json.dump(summary, open(f"{a.out}/summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
