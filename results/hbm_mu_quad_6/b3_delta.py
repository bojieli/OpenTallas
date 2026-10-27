#!/usr/bin/env python3
"""HBM-MU-QUAD-6 B3 (COORD GEOM HBM planU4f, 2026-10-27): soft regions = free area left after the macros.

Every soft content box (contents[] with origin_um/outline_um, no lef, not itself a hard core) of a USED partition
type is re-shaped so that it overlaps NO hard core (own or foreign; a hard core is OBS M1-M5 and holds no std cells)
and no other soft box:
  1. keep the box if it is already clear;
  2. else the free lattice rectangle of area >= need whose centre is nearest the old centre (shapes: the old box
     scaled, full-width and full-height strips of it; the largest area within 2 lattice steps of the best distance).
     The centre matters: kit_istations.py pins the content's flops FIRM there and the G0C face rule aims core pins
     at it.  'sub-rectangle' = inside the old box, 'moved' = partly or wholly outside.
Need of a region = cells * A_CELL / UMAX for pure-soft contents (no hard core of their own);  contents realised by
their own hard cores (inst == core, inst_*, inst.*) keep a glue region of at least MIN_SIDE^2 and their glue
capacity is proven at partition level (all partition cells, an upper bound, in outline minus hard area).
A_CELL = 0.20 um2/cell: measured pure-logic synth averages 0.122-0.161 (collar_idx256r, aq_tree13_fmt,
vms_glue_nw_t, pgslice pretree; kits 10-27) + 25 %.  UMAX = 0.65 (COORD).
usage: b3_delta.py PLAN_IN.json PLAN_OUT.json REPORT.json"""
import json, sys, math, re
import numpy as np

A_CELL, UMAX, G, MIN_SIDE = 0.20, 0.65, 8.64, 25.92


def hrect(c):
    x, y = c["origin_um"]; w, h = c["outline_um"]; dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return (x + dx, y + dy, x + dx + w, y + dy + h)


def srect(c):
    x, y = c["origin_um"]; w, h = c["outline_um"]
    return (x, y, x + w, y + h)


def ov(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6


def own(s, h):
    return h == s or h.startswith(s + "_") or h.startswith(s + ".")


def core_cells(c):
    """std cells inside a hard core: hard_cores[].cells, else the '<N> cells' figure of its note (None if unknown)."""
    if c.get("cells") is not None:
        return int(c["cells"])
    m = re.search(r"(\d+) cells", c.get("note", "") or "")
    return int(m.group(1)) if m else None


def glue_cells(c, hcs):
    """soft glue of a content = its cells minus the cells of its own hard cores; None when a core count is unknown."""
    mine = [h for h in hcs if own(c["inst"], h["inst"])]
    if not mine:
        return int(c.get("cells", 0) or 0), False
    cc = [core_cells(h) for h in mine]
    if any(v is None for v in cc):
        return None, True
    return max(0, int(c.get("cells", 0) or 0) - sum(cc)), True


def max_rect(free):
    """largest all-True rectangle of a 2D bool grid [ny, nx] -> (area, j0, i0, j1, i1) cell indices, half-open."""
    ny, nx = free.shape
    hgt = np.zeros(nx, int); best = (0, 0, 0, 0, 0)
    for j in range(ny):
        hgt = np.where(free[j], hgt + 1, 0)
        st = []
        for i in range(nx + 1):
            hh = hgt[i] if i < nx else 0
            s = i
            while st and st[-1][1] >= hh:
                s, sh = st.pop()
                a = sh * (i - s)
                if a > best[0]:
                    best = (a, j - sh + 1, s, j + 1, i)
            st.append((s, hh))
    return best


def run(d):
    T = d["partition_types"]
    used = sorted({p["type"] for p in d["partitions"]})
    rep = dict(a_cell_um2=A_CELL, umax=UMAX, grid_um=G, types={}, moved=[], kept_sub=[], unchanged=0, failed=[])
    rep["synced_hard_content_boxes"] = 0
    for tn in used:
        t = T[tn]; W, H = t["outline_um"]
        # 0. a content that IS a hard core (same inst) carries the core's rectangle (113 stale as-built boxes in U5e_r:
        #    G0 ignores them, but renders and kit_istations read them)
        HC = {c["inst"]: c for c in t.get("hard_cores", []) if "origin_um" in c and "outline_um" in c}
        for c in t.get("contents", []):
            h = HC.get(c["inst"])
            if h is None or "origin_um" not in c:
                continue
            hb = hrect(h); nb = [round(hb[0], 4), round(hb[1], 4)], [round(hb[2] - hb[0], 4), round(hb[3] - hb[1], 4)]
            if [c["origin_um"], c.get("outline_um")] != list(nb):
                c["origin_um"], c["outline_um"] = nb
                rep["synced_hard_content_boxes"] += 1
        nx, ny = int(math.floor(W / G)), int(math.floor(H / G))
        hard = [(c["inst"], hrect(c)) for c in t.get("hard_cores", []) if "origin_um" in c and "outline_um" in c]
        hn = {n for n, _ in hard}
        occ = np.zeros((ny, nx), bool)          # cell (j,i) = [i*G,(i+1)*G) x [j*G,(j+1)*G) touched by an obstacle

        def mark(r):
            i0 = max(0, int(math.floor(r[0] / G + 1e-9))); i1 = min(nx, int(math.ceil(r[2] / G - 1e-9)))
            j0 = max(0, int(math.floor(r[1] / G + 1e-9))); j1 = min(ny, int(math.ceil(r[3] / G - 1e-9)))
            if i1 > i0 and j1 > j0:
                occ[j0:j1, i0:i1] = True
        for _, r in hard:
            mark(r)
        hard_area = sum((r[2] - r[0]) * (r[3] - r[1]) for _, r in hard)
        soft = [c for c in t.get("contents", []) if "origin_um" in c and "outline_um" in c and not c.get("lef")
                and c["inst"] not in hn]
        cells_all = int(t.get("cells") or sum(int(c.get("cells", 0) or 0) for c in t.get("contents", [])))
        trep = dict(outline=[W, H], hard_area_um2=round(hard_area), free_area_um2=round(W * H - hard_area),
                    cells_all=cells_all, u_partition_all_cells=round(cells_all * A_CELL / max(1.0, W * H - hard_area), 4),
                    core_cells_known=sum(core_cells(c) or 0 for c in t.get("hard_cores", [])),
                    cores_unknown=[c["inst"] for c in t.get("hard_cores", []) if core_cells(c) is None][:8],
                    regions=[])
        # placement order: largest need first (they get the nearest spots)
        hcs = [c for c in t.get("hard_cores", []) if "origin_um" in c]

        def need_of(c):
            g, subs = glue_cells(c, hcs)
            if g is None:      # unknown own-core counts: glue proven at partition level only
                return MIN_SIDE * MIN_SIDE, subs
            return max(MIN_SIDE * MIN_SIDE, g * A_CELL / UMAX), subs
        order = sorted(soft, key=lambda c: -need_of(c)[0])
        for c in order:
            need, subs = need_of(c)
            r0 = srect(c)
            # snap the old box outward to the lattice for the grid test
            i0 = max(0, int(math.floor(r0[0] / G + 1e-9))); i1 = min(nx, int(math.ceil(r0[2] / G - 1e-9)))
            j0 = max(0, int(math.floor(r0[1] / G + 1e-9))); j1 = min(ny, int(math.ceil(r0[3] / G - 1e-9)))
            clear = not any(ov(r0, r) for _, r in hard) and not occ[j0:j1, i0:i1].any() if (i1 > i0 and j1 > j0) else False
            clear = clear and (r0[2] - r0[0]) * (r0[3] - r0[1]) >= need - 1e-6
            if clear:
                mark(r0); rep["unchanged"] += 1
                trep["regions"].append(dict(inst=c["inst"], how="unchanged", box=[round(v, 3) for v in r0], need_um2=round(need),
                                            u=round(need * UMAX / ((r0[2] - r0[0]) * (r0[3] - r0[1])), 4)))
                continue
            # 2. centre-preserving free rectangle: shapes from the old box (scaled, full-width / full-height strips),
            #    area >= need, at the free placement nearest the old centre (face rule + reach read the centre);
            #    among placements within 2 lattice steps of the best distance the largest area wins.
            bwc = max(1, int(round((r0[2] - r0[0]) / G))); bhc = max(1, int(round((r0[3] - r0[1]) / G)))
            msc = int(math.ceil(MIN_SIDE / G - 1e-9))
            shapes = set()
            for sc in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.42, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1):
                shapes.add((max(msc, int(bwc * sc)), max(msc, int(bhc * sc))))
                shapes.add((bwc, max(msc, int(bhc * sc)))); shapes.add((max(msc, int(bwc * sc)), bhc))
            shapes = [(w_, h_) for (w_, h_) in shapes if w_ * h_ * G * G >= need - 1e-6 and w_ <= nx and h_ <= ny]
            # need-sized shapes at several aspects (always: the old-box shapes may have no free placement)
            asp0 = max(0.25, min(4.0, (r0[2] - r0[0]) / max(G, r0[3] - r0[1])))
            for asp in (asp0, 1.0 / asp0, 1.0, 2.0, 0.5, 4.0, 0.25):
                for grow in (1.0, 1.3):
                    wc = max(msc, int(math.ceil(math.sqrt(need * grow * asp) / G)))
                    hc = max(msc, int(math.ceil(need * grow / (wc * G) / G)))
                    if wc <= nx and hc <= ny:
                        shapes.append((wc, hc))
            shapes = sorted(set(shapes))
            S = np.zeros((ny + 1, nx + 1), int); S[1:, 1:] = np.cumsum(np.cumsum(occ, 0), 1)
            cx, cy = (r0[0] + r0[2]) / 2, (r0[1] + r0[3]) / 2
            cands = []
            for (ww, hh) in shapes:
                tot = S[hh:, ww:] - S[:-hh, ww:] - S[hh:, :-ww] + S[:-hh, :-ww]
                J, I = np.nonzero(tot == 0)
                if not len(J):
                    continue
                dist = np.abs((I + ww / 2) * G - cx) + np.abs((J + hh / 2) * G - cy)
                k = int(np.argmin(dist))
                cands.append((float(dist[k]), ww * hh, (I[k] * G, J[k] * G, (I[k] + ww) * G, (J[k] + hh) * G)))
            if not cands:
                rep["failed"].append([tn, c["inst"], round(need)]); continue
            dmin = min(x[0] for x in cands)
            pick = max((x for x in cands if x[0] <= dmin + 2 * G), key=lambda x: x[1])
            nb = pick[2]
            inside = nb[0] >= r0[0] - 1e-6 and nb[1] >= r0[1] - 1e-6 and nb[2] <= r0[2] + 1e-6 and nb[3] <= r0[3] + 1e-6
            how = "sub-rectangle" if inside else "moved"
            nb = tuple(round(v, 4) for v in nb)
            assert not any(ov(nb, r) for _, r in hard), (tn, c["inst"], nb)
            c["origin_um"] = [nb[0], nb[1]]; c["outline_um"] = [round(nb[2] - nb[0], 4), round(nb[3] - nb[1], 4)]
            mark(nb)
            ar = (nb[2] - nb[0]) * (nb[3] - nb[1])
            dc = abs((nb[0] + nb[2]) / 2 - (r0[0] + r0[2]) / 2) + abs((nb[1] + nb[3]) / 2 - (r0[1] + r0[3]) / 2)
            ent = dict(type=tn, inst=c["inst"], how=how, old=[round(v, 3) for v in r0], new=list(nb), need_um2=round(need),
                       u=round(need * UMAX / ar, 4), centre_move_um=round(dc, 1), own_cores=subs)
            trep["regions"].append(ent)
            (rep["moved"] if how == "moved" else rep["kept_sub"]).append(ent)
        rep["types"][tn] = trep
    return rep


def verify(d):
    """independent re-count (gchk/gchk2 definitions): soft-on-hard (any, own or foreign, >1 um2), soft-soft (>1 um2),
    soft box centre inside a hard core, pure-soft region utilisation, partition all-cells utilisation."""
    T = d["partition_types"]; used = sorted({p["type"] for p in d["partitions"]})
    out = dict(soft_on_hard=0, soft_on_foreign_hard=0, soft_soft=0, centre_in_hard=0, region_u_max=0.0, part_u_max=0.0,
               outside=0)
    def a(a_, b_): return max(0, min(a_[2], b_[2]) - max(a_[0], b_[0])) * max(0, min(a_[3], b_[3]) - max(a_[1], b_[1]))
    for tn in used:
        t = T[tn]; W, H = t["outline_um"]
        hard = [(c["inst"], hrect(c)) for c in t.get("hard_cores", []) if "origin_um" in c]
        hn = {n for n, _ in hard}
        soft = [(c, srect(c)) for c in t.get("contents", []) if "origin_um" in c and "outline_um" in c and not c.get("lef")
                and c["inst"] not in hn]
        for c, r in soft:
            for h, b in hard:
                if a(r, b) > 1:
                    out["soft_on_hard"] += 1
                    if not own(c["inst"], h):
                        out["soft_on_foreign_hard"] += 1
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            if any(b[0] < cx < b[2] and b[1] < cy < b[3] for _, b in hard):
                out["centre_in_hard"] += 1
            if r[0] < -0.01 or r[1] < -0.01 or r[2] > W + 0.01 or r[3] > H + 0.01:
                out["outside"] += 1
            g, _ = glue_cells(c, [x for x in t.get("hard_cores", []) if "origin_um" in x])
            if g is not None:
                u = g * A_CELL / ((r[2] - r[0]) * (r[3] - r[1]))
                if u > out["region_u_max"]:
                    out["region_u_max"], out["region_u_arg"] = u, [tn, c["inst"]]
            else:
                out["regions_glue_unknown"] = out.get("regions_glue_unknown", 0) + 1
        for i, (c1, r1) in enumerate(soft):
            for c2, r2 in soft[i + 1:]:
                if a(r1, r2) > 1:
                    out["soft_soft"] += 1
        ha = sum((b[2] - b[0]) * (b[3] - b[1]) for _, b in hard)
        cells = int(t.get("cells") or sum(int(c.get("cells", 0) or 0) for c in t.get("contents", [])))
        glue = cells - sum(core_cells(c) or 0 for c in t.get("hard_cores", []))   # unknown core counts -> counted as glue
        u = glue * A_CELL / (W * H - ha)
        if u > out["part_u_max"]:
            out["part_u_max"], out["part_u_arg"] = u, tn
    out["region_u_max"] = round(out["region_u_max"], 4); out["part_u_max"] = round(out["part_u_max"], 4)
    return out


if __name__ == "__main__":
    src, dst, rp = sys.argv[1:4]
    d = json.load(open(src))
    before = verify(d)
    rep = run(d)
    after = verify(d)
    rep["verify_before"], rep["verify_after"] = before, after
    rep["counts"] = dict(synced_hard_content_boxes=rep["synced_hard_content_boxes"], unchanged=rep["unchanged"], sub_rectangle=len(rep["kept_sub"]), moved=len(rep["moved"]), failed=len(rep["failed"]))
    json.dump(d, open(dst, "w"), separators=(",", ":"))
    json.dump(rep, open(rp, "w"), indent=1)
    print(json.dumps(dict(counts=rep["counts"], before=before, after=after,
                          worst_moves=sorted(((m["centre_move_um"], m["type"], m["inst"]) for m in rep["moved"]), reverse=True)[:10])))
