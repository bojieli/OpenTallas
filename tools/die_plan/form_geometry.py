#!/usr/bin/env python3
"""Parent-aware physical form preparation, using the existing plan geometry.

This is an advisory construction helper, not a release gate. It never changes a
plan, pin, stage count, clock policy or routing-layer permission implicitly.
Coordinates are micrometres in the parent type frame unless stated otherwise.
"""
import argparse
import heapq
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))

EPS = 1e-7


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) + EPS and min(a[3], b[3]) > max(a[1], b[1]) + EPS


def grow(r, margin):
    return [r[0] - margin, r[1] - margin, r[2] + margin, r[3] + margin]


def transform_point(point, origin, outline, orient="R0"):
    """Same lower-left bbox convention as schema.Plan.to_die, including MX."""
    x, y = point
    w, h = outline
    x, y = {"R0": (x, y), "MX": (x, h-y), "MY": (w-x, y), "R180": (w-x, h-y)}[orient]
    return [origin[0] + x, origin[1] + y]


def transform_rect(rect, origin, outline, orient="R0"):
    pts = [transform_point([x, y], origin, outline, orient) for x in (rect[0], rect[2]) for y in (rect[1], rect[3])]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]


def layer_number(layer):
    return int(str(layer).removeprefix("M"))


def parent_obstacles(parent, exclude=()):
    """Reuse G0/G2's physical union; a split container does not become a wall."""
    from placement_obstacles import placement_boxes
    return {name: list(rect) for name, rect in placement_boxes(parent).items() if name not in exclude}


def placement_reservations(parent, exclude=(), macro_halo=5.0, clock_halo=8.64):
    """Existing physical placements, using the canonical landing group builders.

    These reserve *cell sites*, not all signal routing. A route can pass over a
    logic band while a new FIRM register cannot occupy its cells.
    """
    import landing_place as LP
    excluded=set(exclude)
    out={"macro:"+n:grow(r,macro_halo) for n,r in parent_obstacles(parent).items()}
    for n,r,_ in LP._reader_start_groups(parent)+LP._writer_start_groups(parent)+LP._status_reset_groups(parent):
        if n not in excluded:
            out["group:"+n]=list(r)
    ck=parent.get("clock",{})
    for n,b in ck.get("landing_contract",{}).get("bands",{}).items():
        for j,r in enumerate(b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else [])):
            out[f"band:{n}:{j}"]=list(r)
        if b.get("freg_rect_um"):
            out[f"freg:{n}"]=list(b["freg_rect_um"])
    for j,r in enumerate(ck.get("die_islands_um",[])):
        out[f"island:{j}"]=list(r)
    taps=[("clk",ck["tap_um"])] if ck.get("tap_um") else []
    taps += [(q["name"],q["xy"]) for q in ck.get("added_taps",[])]
    for n,p in taps:
        out["clock:"+n]=grow([*p,*p],clock_halo)
    for n,p in parent.get("relay_sites",{}).items():
        if n not in excluded:
            out["relay:"+n]=grow([*p,*p],.702)
    return out


def parent_cell_space(parent, *, inset=4.32, halo=0.0, glue_area_um2=None, utilization=.45):
    """Exact rectangle-union row area after opaque macro footprints are cut.

    Bbox containment alone does not make a composable parent: two abutted
    opaque halves can leave zero rows for even one OR gate. Caller supplies
    measured glue area; unknown area is never reported as a capacity pass.
    """
    W,H=parent["outline_um"];core=[inset,inset,W-inset,H-inset]
    if core[2] <= core[0] or core[3] <= core[1]:
        raise ValueError("parent outline smaller than core inset")
    boxes=[]
    for r in parent_obstacles(parent).values():
        r=grow(r,halo);q=[max(core[0],r[0]),max(core[1],r[1]),min(core[2],r[2]),min(core[3],r[3])]
        if q[0]<q[2] and q[1]<q[3]:boxes.append(q)
    xs=sorted({core[0],core[2]}|{q[k] for q in boxes for k in (0,2)})
    occupied=0.0
    for a,b in zip(xs,xs[1:]):
        intervals=sorted((q[1],q[3]) for q in boxes if q[0] < b-EPS and q[2] > a+EPS)
        end=-float("inf");height=0.0
        for lo,hi in intervals:
            height+=max(0.0,hi-max(lo,end));end=max(end,hi)
        occupied+=(b-a)*height
    area=(core[2]-core[0])*(core[3]-core[1]);free=max(0.0,area-occupied)
    return {"core_area_um2":area,"macro_union_um2":occupied,"free_row_area_um2":free,
            "utilization":utilization,"glue_area_um2":glue_area_um2,
            "capacity_fits":None if glue_area_um2 is None else glue_area_um2 <= free*utilization+EPS,
            "note":"cell-row capacity only; routing, clock, PG and parent pin contracts remain separate"}


def fit_core(parent, instance, outline=None, origin=None, obs_max=None, halo=0.0, route_reservations=()):
    """Check a candidate at a real parent's instance, not just its standalone box.

    Outline growth does not move the lower-left anchor of MX/MY instances. A new
    OBS layer is an explicit reservation obligation even if the bbox still fits.
    Reservations are caller-supplied actual route rectangles/layers; absent
    route geometry is not inferred to be clear.
    """
    records = {c["inst"]: c for c in parent.get("contents", []) if "outline_um" in c}
    records.update({c["inst"]: c for c in parent.get("hard_cores", [])})
    old = records[instance]
    wh = list(outline or old["outline_um"])
    xy = list(origin or old["origin_um"])
    if len(wh) != 2 or min(wh) <= 0 or not all(math.isfinite(float(x)) for x in wh + xy):
        raise ValueError("finite positive outline and finite origin required")
    dx, dy = old.get("track_offset_um", [0, 0]) if instance in {c["inst"] for c in parent.get("hard_cores", [])} else (0, 0)
    r = [xy[0] + dx, xy[1] + dy, xy[0] + dx + wh[0], xy[1] + dy + wh[1]]
    w, h = parent["outline_um"]
    overflow = [max(0.0, -r[0]), max(0.0, -r[1]), max(0.0, r[2]-w), max(0.0, r[3]-h)]
    obstacles = parent_obstacles(parent, [instance])
    collisions = [{"name": n, "rect_um": q} for n, q in obstacles.items() if overlap(grow(r, halo), q)]
    old_layer = old.get("obs_max", "M5")
    new_layer = obs_max or old_layer
    added = [f"M{k}" for k in range(layer_number(old_layer)+1, layer_number(new_layer)+1)]
    conflicts = [q for q in route_reservations if set(q.get("layers", [])) & set(added) and overlap(r, q["rect_um"])]
    return {"instance": instance, "orient": old.get("orient", "R0"), "origin_um": xy,
            "outline_um": wh, "bbox_um": r, "track_offset_um": [dx, dy],
            "fits": not any(x > EPS for x in overflow) and not collisions,
            "outside_um": dict(zip(("W", "S", "E", "N"), overflow)), "collisions": collisions,
            "halo_um": halo, "obs_max": new_layer, "new_obstruction_layers": added,
            "route_reservation_conflicts": conflicts,
            "parent_route_review_needed": bool(added),
            "pin_review_needed": wh != old["outline_um"] or xy != old["origin_um"]}


def resite_core(parent, instance, outline, *, obs_max=None, halo=0.0, grid_um=8.64):
    """Least-shift candidate from real obstacle edges; no plan or pins changed.

    This is a geometric proposal only. A moved macro still needs its parent
    connections/reach reviewed. A larger form with no free rectangle returns
    None rather than silently growing the parent or relocating other macros.
    """
    old = next(c for c in parent.get("hard_cores", []) if c["inst"] == instance)
    ox, oy = old["origin_um"]
    dx, dy = old.get("track_offset_um", [0,0])
    w, h = outline
    W, H = parent["outline_um"]
    boxes = parent_obstacles(parent,[instance])
    xs, ys = {ox, -dx, W-w-dx}, {oy, -dy, H-h-dy}
    for q in boxes.values():
        xs.update((q[2]+halo-dx,q[0]-halo-w-dx))
        ys.update((q[3]+halo-dy,q[1]-halo-h-dy))
    snap = lambda v: round(math.ceil((v-EPS)/grid_um)*grid_um,6)
    candidates = sorted({(snap(x),snap(y)) for x in xs for y in ys},
                        key=lambda p:(abs(p[0]-ox)+abs(p[1]-oy),p))
    for p in candidates:
        r=[p[0]+dx,p[1]+dy,p[0]+dx+w,p[1]+dy+h]
        if r[0] < -EPS or r[1] < -EPS or r[2] > W+EPS or r[3] > H+EPS:
            continue
        if any(overlap(grow(r,halo),q) for q in boxes.values()):
            continue
        return fit_core(parent,instance,outline,p,obs_max,halo)
    return None


def _inside(p, box):
    return box[0] + EPS < p[0] < box[2] - EPS and box[1] + EPS < p[1] < box[3] - EPS


def segment_clear(a, b, boxes):
    if abs(a[0]-b[0]) > EPS and abs(a[1]-b[1]) > EPS:
        return False
    if abs(a[1]-b[1]) < EPS:
        return not any(q[1]+EPS < a[1] < q[3]-EPS and min(max(a[0], b[0]), q[2])-max(min(a[0], b[0]), q[0]) > EPS for q in boxes)
    return not any(q[0]+EPS < a[0] < q[2]-EPS and min(max(a[1], b[1]), q[3])-max(min(a[1], b[1]), q[1]) > EPS for q in boxes)


def corridor_path(start, end, outline, boxes, margin=4.32, grid=(0.054, 0.27)):
    """Shortest rectilinear path on obstacle-edge visibility axes, no knob sweep.

    Physical route obstacles and placement reservations are distinct inputs to
    prepare_chain. Boundary contact is allowed because the caller already grows
    obstacles by its required halo/track clearance.
    """
    w, h = outline
    if any(_inside(p, b) for p in (start, end) for b in boxes):
        return None
    if any(not (margin-EPS <= p[0] <= w-margin+EPS and margin-EPS <= p[1] <= h-margin+EPS) for p in (start, end)):
        return None
    snap_lo = lambda v, step: margin + math.floor((v-margin)/step + EPS)*step
    snap_hi = lambda v, step: margin + math.ceil((v-margin)/step - EPS)*step
    xs = {float(start[0]), float(end[0]), margin, w-margin}
    ys = {float(start[1]), float(end[1]), margin, h-margin}
    for q in boxes:
        xs.update((snap_lo(q[0], grid[0]), snap_hi(q[2], grid[0])))
        ys.update((snap_lo(q[1], grid[1]), snap_hi(q[3], grid[1])))
    xs = sorted(x for x in xs if margin-EPS <= x <= w-margin+EPS)
    ys = sorted(y for y in ys if margin-EPS <= y <= h-margin+EPS)
    src, dst = (xs.index(float(start[0])), ys.index(float(start[1]))), (xs.index(float(end[0])), ys.index(float(end[1])))
    dist, back, queue = {src: 0.0}, {}, [(0.0, 0.0, src)]
    while queue:
        _, d, u = heapq.heappop(queue)
        if d > dist[u] + EPS:
            continue
        if u == dst:
            path = []
            while True:
                path.append([xs[u[0]], ys[u[1]]])
                if u == src:
                    break
                u = back[u]
            path.reverse()
            compact = []
            for p in path:
                if len(compact) >= 2 and (abs(compact[-2][0]-compact[-1][0]) < EPS and abs(p[0]-compact[-1][0]) < EPS or
                                         abs(compact[-2][1]-compact[-1][1]) < EPS and abs(p[1]-compact[-1][1]) < EPS):
                    compact[-1] = p
                else:
                    compact.append(p)
            return compact
        for v in ((u[0]-1,u[1]),(u[0]+1,u[1]),(u[0],u[1]-1),(u[0],u[1]+1)):
            if not (0 <= v[0] < len(xs) and 0 <= v[1] < len(ys)):
                continue
            a, b = (xs[u[0]], ys[u[1]]), (xs[v[0]], ys[v[1]])
            if any(_inside(b, q) for q in boxes) or not segment_clear(a, b, boxes):
                continue
            nd = d + abs(a[0]-b[0]) + abs(a[1]-b[1])
            if nd + EPS < dist.get(v, float("inf")):
                dist[v], back[v] = nd, u
                heuristic = abs(b[0]-end[0]) + abs(b[1]-end[1])
                heapq.heappush(queue, (nd+heuristic, nd, v))
    return None


def length(path):
    return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a, b in zip(path, path[1:]))


def _sample(path, distance):
    for a, b in zip(path, path[1:]):
        n = length([a, b])
        if distance <= n + EPS:
            return [a[k] + (b[k]-a[k])*distance/n for k in (0, 1)] if n else list(a)
        distance -= n
    return list(path[-1])


def prepare_chain(start, end, outline, route_boxes, stages, *, site_boxes=(), reach=405.0,
                  cell_clearance=2.16, grid=(0.054,0.27), margin=4.32, route_margin=0.0):
    """Prepare exactly `stages` grid-aligned internal relays in a clear corridor.

    A count shortage is reported, never fixed by silently changing reset phase
    or data latency. Returned per-hop polylines expose bends in the reach price.
    """
    if stages < 0:
        raise ValueError("nonnegative stage count required")
    route_boxes = [list(b) for b in route_boxes]
    path = corridor_path(start, end, outline, route_boxes, route_margin, grid)
    if path is None:
        return {"fits": False, "reason": "no clear rectilinear corridor", "stages": stages}
    n = length(path)
    need = max(0, math.ceil((n-EPS)/reach)-1)
    if need > stages:
        return {"fits": False, "reason": "stage count insufficient; latency/phase decision required",
                "stages": stages, "minimum_stages": need, "path_um": path, "length_um": n}
    occupied = [grow(b, cell_clearance) for b in list(route_boxes)+list(site_boxes)]
    points = []
    for j in range(stages):
        p = _sample(path, n*(j+1)/(stages+1))
        x0 = math.floor((p[0]-margin)/grid[0]); y0 = math.floor((p[1]-margin)/grid[1])
        xs = {margin+(x0+dx)*grid[0] for dx in (0,1)}
        ys = {margin+(y0+dy)*grid[1] for dy in (0,1)}
        # A wire corridor can abut a macro while a relay cell needs clearance.
        # Add nearest obstacle-edge projections, not a placement knob sweep.
        for q in occupied:
            if q[0]-grid[0] <= p[0] <= q[2]+grid[0] and q[1]-grid[1] <= p[1] <= q[3]+grid[1]:
                xs.update((margin+math.floor((q[0]-margin)/grid[0])*grid[0],
                           margin+math.ceil((q[2]-margin)/grid[0])*grid[0]))
                ys.update((margin+math.floor((q[1]-margin)/grid[1])*grid[1],
                           margin+math.ceil((q[3]-margin)/grid[1])*grid[1]))
        choices = [[round(x,6),round(y,6)] for x in xs for y in ys]
        choices.sort(key=lambda q: (abs(q[0]-p[0])+abs(q[1]-p[1]),q))
        good = next((q for q in choices if margin <= q[0] <= outline[0]-margin and margin <= q[1] <= outline[1]-margin
                     and not any(_inside(q,b) for b in occupied)), None)
        if good is None:
            return {"fits": False, "reason": "relay sample has no clear row/site location", "stage": j,
                    "stages": stages, "path_um": path, "sample_um": p}
        points.append(good)
        occupied.append(grow([*good,*good],2*cell_clearance))
    legs = [corridor_path(a,b,outline,route_boxes,route_margin,grid) for a,b in zip([start]+points,points+[end])]
    hops = [length(p) if p is not None else float("inf") for p in legs]
    return {"fits": all(h <= reach+EPS for h in hops), "reason": "prepared" if max(hops) <= reach+EPS else "snapped routed hop exceeds reach",
            "stages": stages, "minimum_stages": need, "points_um": points, "hop_paths_um": legs,
            "hop_lengths_um": hops, "max_hop_um": max(hops), "path_um": path, "length_um": n,
            "added_cycles": 0, "note": "existing stage count preserved; caller retains source/consumer phase contract"}


def unowned_guides(groups, placement):
    """Do not guide a cell already FIRM/FIXED, or claim it in two groups."""
    out, skipped, claimed = [], [], set()
    for group in groups:
        cells = []
        for name in group.get("instances", []):
            state = placement.get(name, {}).get("status", "UNPLACED").upper()
            reason = "fixed placement" if state in ("FIRM", "FIXED", "LOCKED", "COVER") else "already grouped" if name in claimed else None
            if reason:
                skipped.append({"instance": name, "group": group["name"], "reason": reason, "status": state})
            else:
                cells.append(name); claimed.add(name)
        if cells:
            out.append(dict(group, instances=cells))
    return {"groups": out, "excluded": skipped}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("core", help="check all selected core occurrences in actual parents")
    c.add_argument("plan"); c.add_argument("report"); c.add_argument("--module", required=True)
    c.add_argument("--outline", type=float,nargs=2); c.add_argument("--obs-max"); c.add_argument("--halo",type=float,default=0)
    c.add_argument("--resite",action="store_true",help="also propose least-shift legal lattice position, without editing plan/pins")
    c = sub.add_parser("chain", help="prepare a fixed-stage corridor from explicit geometry inputs")
    c.add_argument("input"); c.add_argument("report")
    c = sub.add_parser("guides", help="exclude fixed or already-owned cells from placement groups")
    c.add_argument("input"); c.add_argument("report")
    c = sub.add_parser("capacity",help="report exact parent row space after macro cutouts")
    c.add_argument("input");c.add_argument("report");c.add_argument("--type",required=True)
    c.add_argument("--glue-area",type=float);c.add_argument("--utilization",type=float,default=.45)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan if a.command=="core" else a.input).read_text())
    if a.command == "core":
        rows = []
        for tn,t in raw["partition_types"].items():
            for c in t.get("hard_cores",[]):
                if c["module"] != a.module:
                    continue
                row = dict(type=tn, **fit_core(t,c["inst"],a.outline,obs_max=a.obs_max,halo=a.halo))
                if a.outline and a.outline != c["outline_um"]:
                    row["original_outline_alternative"] = fit_core(t,c["inst"],obs_max=a.obs_max,halo=a.halo)
                if a.resite and not row["fits"]:
                    row["placement_candidate"] = resite_core(t,c["inst"],a.outline or c["outline_um"],obs_max=a.obs_max,halo=a.halo)
                rows.append(row)
        result = {"module":a.module,"occurrences":rows,"fit_count":sum(r["fits"] for r in rows),"total":len(rows)}
    elif a.command == "chain":
        result = prepare_chain(**raw)
    elif a.command == "capacity":
        result = parent_cell_space(raw["partition_types"][a.type],glue_area_um2=a.glue_area,utilization=a.utilization)
    else:
        result = unowned_guides(**raw)
    Path(a.report).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("occurrences","groups","excluded","hop_paths_um")},default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
