"""Master-plan static gates for the COORD rulings of 2026-10-26 (METHODOLOGY 12.2a1 / 12.7b / 12.8; master-plan mode).

  clock_rep_sites        COORD 06:53 (option B): H-tree leg repeaters sit at PLAN-FIXED sites in partition repeater
                         bays, built by pushdown (partition netlist, fixed/dont_touch).  The plan site of repeater k of
                         a leg with n_seg segments is a + (b - a) k / n_seg (equal legs).  PASS = every site lies in a
                         partition outside every hard core (displacement 0) AND the mesh build slid none (slide_um 0).
                         Returns the type-frame sites per partition type for the slices.
  tap_region_containment COORD 06:53 (INFRA-FIRST-R2 single-region proof): clock regions are unions of partitions;
                         every tap's partition belongs to the tap's region and its stub foot (strap point) lies inside
                         that region's partition union.
  footless_stubs         COORD 06:41 (HEAD islands): a tap stub without a legal foot (no foot, foot off its strap line,
                         foot outside its region's strap box) is a plan defect: 0 allowed.
  island_ft_inputs       COORD 06:41: every pushdown island's clock ft input is fed (a die tree node / mesh driver at the
                         island, or the local strap of its region passes over it, or a clock-entry island fed by its
                         core's tap stub); unused inputs are fed from the local strap, never left open: 0 open.

All read the die clock build (die_clock_mesh.py mesh.json: htree, drivers, taps, xs/ys, part_region, meta.regions)
and the plan; no measurement feeds a site.  Without --mesh every gate is NOT RUN (blocks the freeze).
"""
from collections import defaultdict

STEP_UM = 4.32
TOL_UM = 0.5


def _inside(r, xy, strict=True, eps=1e-6):
    if strict:
        return r[0] + eps < xy[0] < r[2] - eps and r[1] + eps < xy[1] < r[3] - eps
    return r[0] - eps <= xy[0] <= r[2] + eps and r[1] - eps <= xy[1] <= r[3] + eps


class _Grid:
    """bucketed rect lookup (die frame)."""

    def __init__(self, rects, B=400.0):
        self.B = B
        self.b = defaultdict(list)
        for r in rects:
            for i in range(int(r[0] // B), int(r[2] // B) + 1):
                for j in range(int(r[1] // B), int(r[3] // B) + 1):
                    self.b[(i, j)].append(r)

    def hit(self, xy, strict=True):
        for r in self.b.get((int(xy[0] // self.B), int(xy[1] // self.B)), []):
            if _inside(r[:4], xy, strict):
                return r
        return None


def die_geometry(P, core_to_type, rect_pts):
    """(partition rects [x0, y0, x1, y1, part], hard-core rects [x0, y0, x1, y1, part, inst, module]) die frame."""
    parts, cores = [], []
    for part in P.parts:
        r = P.rect(part)
        parts.append(tuple(r) + (part,))
        for h in P.ptype(part).get("hard_cores", []):
            cr = rect_pts(P, part, core_to_type(h, (0.0, 0.0) + tuple(h["outline_um"])))
            cores.append(tuple(cr) + (part, h["inst"], h["module"]))
    return parts, cores


def rep_sites(e):
    """plan sites of the leg repeaters (equal segments, a -> b)."""
    n = int(e.get("n_seg") or 1)
    (ax, ay), (bx, by) = e["a"], e["b"]
    reps = e.get("reps") or []
    out = []
    for k in range(1, n):
        if k - 1 >= len(reps):
            break
        out.append((reps[k - 1].get("cell", f"{e.get('tag')}_{k}"), (ax + (bx - ax) * k / n, ay + (by - ay) * k / n),
                    float(reps[k - 1].get("slide_um") or 0.0)))
    return out


def clock_rep_sites(M, P, parts, cores, reach=450.0):
    if not M:
        return dict(verdict="NOT RUN", note="no --mesh (die H-tree)"), {}
    pg, cg = _Grid(parts), _Grid(cores)
    n = bad = slid = 0
    worst, by_type, inst_sets = [], defaultdict(set), defaultdict(set)
    kinds = defaultdict(int)
    for e in M.get("htree", []):
        (ax, ay), (bx, by) = e["a"], e["b"]
        L = abs(bx - ax) + abs(by - ay)
        for cell, xy, slide in rep_sites(e):
            n += 1
            if slide > 1e-6:
                slid += 1
            p = pg.hit(xy, strict=False)
            c = cg.hit(xy)
            if p is not None and c is None:
                tx, ty = P.to_type(p[4], xy)
                site = (round(tx, 3), round(ty, 3))
                by_type[P.parts[p[4]]["type"]].add(site)
                inst_sets[p[4]].add(site)
                continue
            bad += 1
            kinds["in_hard_core" if c is not None else "outside_partitions"] += 1
            # displacement to the nearest legal point along the leg (the build would have to slide it)
            d_best = None
            if L > 1e-9:
                ux, uy = (bx - ax) / L, (by - ay) / L
                s = STEP_UM
                while s <= reach / 2 and d_best is None:
                    for sg in (1, -1):
                        q = (xy[0] + sg * s * ux, xy[1] + sg * s * uy)
                        if pg.hit(q, strict=False) is not None and cg.hit(q) is None:
                            d_best = s
                            break
                    s += STEP_UM
            worst.append(dict(cell=cell, leg=e.get("tag"), level=e.get("level"), xy_um=[round(xy[0], 3),
                                                                                     round(xy[1], 3)],
                              blocker=(c[5] + ":" + c[6]) if c is not None else None,
                              displacement_um=round(d_best, 3) if d_best is not None else None))
    worst.sort(key=lambda r: -(r["displacement_um"] if r["displacement_um"] is not None else 1e9))
    # 12.2a1 'identical per type': instances of one type host different type-frame sites when the tree is not
    # commensurate with the partition lattice -> the slice carries the UNION; unused sites are fed from the local
    # strap (COORD 06:41).  INFO (the tree_commensurate gate owns the lattice).
    per_type_inst = defaultdict(list)
    for p, s in inst_sets.items():
        per_type_inst[P.parts[p]["type"]].append(len(s))
    nonuni = {t: dict(union=len(by_type[t]), min_per_inst=min(v), max_per_inst=max(v))
              for t, v in per_type_inst.items() if len(by_type[t]) > max(v)}
    g = dict(verdict="NOT RUN" if not n else ("PASS" if not bad and not slid else "FAIL"),
             repeaters=n, illegal_sites=bad, illegal_by_kind=dict(kinds), build_slid=slid,
             max_displacement_um=max([r["displacement_um"] or 0 for r in worst] or [0]),
             unresolved=sum(1 for r in worst if r["displacement_um"] is None), examples=worst[:30],
             types_with_sites=len(by_type), types_non_identical=len(nonuni),
             non_identical_examples=dict(sorted(nonuni.items(), key=lambda kv: -kv[1]["union"])[:10]),
             rule="COORD 06:53 (B): leg repeaters at plan-fixed sites in partition repeater bays (pushdown), "
                  "equal legs kept; displacement must be 0 (site inside a partition, outside every hard core)")
    return g, {t: sorted(v) for t, v in by_type.items()}


def _region_parts(M):
    pr = M.get("part_region") or {}
    out = defaultdict(list)
    for p, r in pr.items():
        out[r].append(p)
    return pr, out


def tap_region_containment(M, P):
    if not M:
        return dict(verdict="NOT RUN", note="no --mesh")
    pr, rp = _region_parts(M)
    taps = M.get("taps") or []
    if not pr or not taps:
        return dict(verdict="NOT RUN", note="mesh has no part_region / taps (single-region build)")
    grids = {r: _Grid([tuple(P.rect(p)) + (p,) for p in ps if p in P.parts]) for r, ps in rp.items()}
    wrong_region = foot_out = 0
    ex = []
    by_part = defaultdict(int)
    for t in taps:
        r = t.get("region", pr.get(t.get("part")))
        mism = pr.get(t.get("part")) is not None and pr.get(t.get("part")) != r
        f = t.get("foot")
        fo = f is None or grids.get(r) is None or grids[r].hit(tuple(f), strict=False) is None
        if mism:
            wrong_region += 1
        if fo:
            foot_out += 1
        if mism or fo:
            by_part[t.get("part")] += 1
            if len(ex) < 30:
                ex.append(dict(part=t.get("part"), tap=t.get("tap"), region=r, part_region=pr.get(t.get("part")),
                               foot=f, stub_um=t.get("stub_um")))
    # rectangular region boxes cutting through partitions (INFO: the cause the ruling removes)
    boxes = {(rg.get("k")): rg.get("box_um") for rg in (M.get("meta", {}).get("regions") or []) if rg.get("box_um")}
    cut = 0
    if boxes:
        for p in P.parts:
            x0, y0, x1, y1 = P.rect(p)
            hit = sum(1 for b in boxes.values()
                      if min(x1, b[2]) - max(x0, b[0]) > 1e-6 and min(y1, b[3]) - max(y0, b[1]) > 1e-6)
            cut += hit > 1
    bad = wrong_region + foot_out
    return dict(verdict="PASS" if not bad else "FAIL", taps=len(taps), regions=len(rp),
                tap_part_in_other_region=wrong_region, foot_outside_region_union=foot_out,
                partitions_cut_by_region_boxes=cut,
                worst_parts=dict(sorted(by_part.items(), key=lambda kv: -kv[1])[:15]), examples=ex,
                rule="COORD 06:53: clock regions = unions of partitions; each tap fed by the region containing its "
                     "partition (foot inside that region's partition union)")


def footless_stubs(M):
    if not M:
        return dict(verdict="NOT RUN", note="no --mesh")
    taps = M.get("taps") or []
    if not taps:
        return dict(verdict="NOT RUN", note="mesh has no taps")
    xs, ys = M.get("xs") or [], M.get("ys") or []
    sbox = {rg.get("k"): rg.get("strap_box_um") for rg in (M.get("meta", {}).get("regions") or [])
            if rg.get("strap_box_um")}
    kinds = defaultdict(int)
    ex = []
    for t in taps:
        f, st, sp = t.get("foot"), t.get("stub"), t.get("strap")
        why = None
        if f is None or st is None:
            why = "no_foot" if f is None else "no_stub"
        elif sp and isinstance(sp, (list, tuple)) and len(sp) == 2 and isinstance(sp[1], int):
            L, i = sp
            line = (ys if L == "M8" else xs)
            if not (0 <= i < len(line)):
                why = "strap_index_out_of_range"
            elif abs((f[1] if L == "M8" else f[0]) - line[i]) > TOL_UM:
                why = "foot_off_strap_line"
        if why is None and sbox and t.get("region") in sbox and f is not None:
            if not _inside(sbox[t["region"]], f, strict=False, eps=TOL_UM):
                why = "foot_outside_region_strap_box"
        if why:
            kinds[why] += 1
            if len(ex) < 30:
                ex.append(dict(part=t.get("part"), tap=t.get("tap"), why=why, foot=f, strap=sp))
    n = sum(kinds.values())
    return dict(verdict="PASS" if not n else "FAIL", taps=len(taps), footless=n, by_kind=dict(kinds), examples=ex,
                rule="COORD 06:41: a stub without a legal foot (on its strap line, inside its region's strap box) is "
                     "a plan defect; fix the strap/foot lattice before GRT")


def island_ft_inputs(M, islands):
    """islands: [dict(kind, part, inst, role, rect_um die frame)] for every pushdown island instance."""
    if not M:
        return dict(verdict="NOT RUN", note="no --mesh")
    if not islands:
        return dict(verdict="NOT RUN", note="no pushdown islands in the plan")
    pts = [tuple(e["b"]) for e in M.get("htree", [])]
    pts += [tuple(d.get("site") or d.get("ideal")) for d in (M.get("drivers") or {}).values()]
    B = 400.0
    pb = defaultdict(list)
    for q in pts:
        pb[(int(q[0] // B), int(q[1] // B))].append(q)
    xs, ys = sorted(M.get("xs") or []), sorted(M.get("ys") or [])
    sbox = [rg.get("strap_box_um") for rg in (M.get("meta", {}).get("regions") or []) if rg.get("strap_box_um")]
    tap_feet = defaultdict(list)
    for t in M.get("taps") or []:
        if t.get("foot") is not None:
            tap_feet[t.get("part")].append(tuple(t["xy"]))
    import bisect

    def node_in(r):
        for i in range(int(r[0] // B), int(r[2] // B) + 1):
            for j in range(int(r[1] // B), int(r[3] // B) + 1):
                if any(_inside(r, q, strict=False) for q in pb.get((i, j), [])):
                    return True
        return False

    def strap_over(r):
        def any_in(line, lo, hi):
            k = bisect.bisect_left(line, lo)
            return k < len(line) and line[k] <= hi
        ok = any_in(xs, r[0], r[2]) or any_in(ys, r[1], r[3])
        if ok and sbox:
            c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            ok = any(_inside(b, c, strict=False) for b in sbox)
        return ok
    feed = defaultdict(int)
    open_ = []
    for isl in islands:
        r = isl["rect_um"]
        if node_in(r):
            feed["tree_node_or_mesh_driver"] += 1
        elif isl.get("role") == "clock_entry" and any(_inside(r, q, strict=False, eps=4.32)
                                                       for q in tap_feet.get(isl.get("part"), [])):
            feed["core_tap_stub"] += 1
        elif strap_over(r):
            feed["local_strap"] += 1
        else:
            open_.append(dict(isl, rect_um=[round(v, 3) for v in r]))
    return dict(verdict="PASS" if not open_ else "FAIL", islands=len(islands), fed=dict(feed), open=len(open_),
                examples=open_[:30],
                reset="rst_i = die regional reset stack (declared per island; reset plan owner checks the stack)",
                rule="COORD 06:41: unused island inputs are fed from the island's local strap (identical cells + "
                     "load per instance); no open ft inputs")
