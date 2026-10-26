"""Plan-stage core-cell legalization and RC/load prediction; no build-time search.

Inputs are the slice, actual LEF master footprints/row lattice, macro/fixed
obstacles and named clock sinks. Outputs are frozen per-type cell origins and
geometry-only predictions. No clock measurement, trim, pad or ECO is read.
"""
import copy
import math
from collections import defaultdict

import core_infra as CI


def read_technology(path):
    """Read the small OpenDB technology.tsv snapshot produced before planning."""
    import tkinter
    interp = tkinter.Tcl()
    out = dict(rows=[], masters={}, obstacles=[])
    for line in open(path):
        f = list(interp.splitlist(line))
        if not f:
            continue
        if f[0] == "DBU": out["dbu"] = int(f[1])
        elif f[0] == "CORE": out["core"] = list(map(int, f[1:]))
        elif f[0] == "ROW": out["rows"].append(dict(rect=list(map(int, f[1:5])), site=int(f[5]), orient=f[6]))
        elif f[0] == "MASTER": out["masters"][f[1]] = list(map(int, f[2:]))
        elif f[0] == "OBSTACLE": out["obstacles"].append(dict(name=f[1], kind=f[2], rect=list(map(int, f[3:]))))
    return out


def _subtract(intervals, lo, hi):
    ans = []
    for a,b in intervals:
        if hi < a or lo > b: ans.append((a,b)); continue
        if a < lo: ans.append((a,min(b,lo-1)))
        if b > hi: ans.append((max(a,hi+1),b))
    return ans


def legalize_slice(sl, technology, macro_halo_um=4.32):
    """Deterministic nearest legal row/site in the PLAN, before CTS.

    Obstacle geometry is immutable. Each buffer remains inside its declared
    island/core rect; touching is allowed, overlap is not. No identity, stage,
    driver or sink assignment changes. Returned source slice records exact
    origins/orientations plus displacement report for the predictor/review.
    """
    out = copy.deepcopy(sl)
    out.pop("cell_placements", None)
    plan = CI.compile_slice(out)
    u = technology["dbu"]
    halo = int(round(macro_halo_um*u))
    obstacles=[]
    for o in technology["obstacles"]:
        x0,y0,x1,y1=o["rect"]
        h=halo if o["kind"]=="macro" else 0
        obstacles.append((x0-h,y0-h,x1+h,y1+h,o["name"]))
    rows=sorted(technology["rows"],key=lambda r:(r["rect"][1],r["rect"][0],r["orient"]))
    core=technology["core"]
    placed=[]; result={}; moves=[]; row_obstacles={}
    for c in plan["cells"]:
        w,h=technology["masters"][c["master"]]
        cx,cy=(v*u for v in c["xy_um"])
        rx0,ry0,rx1,ry1=(int(round(v*u)) for v in c["rect_um"])
        best=None
        for row in rows:
            x0,y0,x1,y1=row["rect"];sw=row["site"]
            if y0 < max(core[1],ry0) or y0+h > min(core[3],ry1,y1):continue
            low=max(core[0],rx0,x0);high=min(core[2],rx1,x1)-w
            lo=math.ceil((low-x0)/sw);hi=math.floor((high-x0)/sw)
            if hi < lo:continue
            free=[(lo,hi)]
            rk=(y0,h)
            if rk not in row_obstacles:
                row_obstacles[rk]=[o for o in obstacles if y0 < o[3] and y0+h > o[1]]
            for a,b,d,e,_ in row_obstacles[rk]+placed:
                if y0 >= e or y0+h <= b:continue
                # x origins in (a-w,d) overlap this obstacle; site indexes exact.
                free=_subtract(free,math.floor((a-w-x0)/sw)+1,math.ceil((d-x0)/sw)-1)
                if not free:break
            desired=(cx-w/2-x0)/sw
            for a,b in free:
                for ix in {max(a,min(b,math.floor(desired))),max(a,min(b,math.ceil(desired)))}:
                    xx=x0+ix*sw
                    dx=xx+w/2-cx;dy=y0+h/2-cy
                    key=(abs(dx)+abs(dy),abs(dy),y0,xx,row["orient"])
                    if best is None or key < best[0]:best=(key,xx,y0,row["orient"],dx,dy)
        if best is None:raise CI.InfraError(f"plan legalization: no legal site for {c['name']} inside {c['rect_um']}")
        _,x,y,orient,dx,dy=best
        placed.append((x,y,x+w,y+h,c["name"]))
        result[c["name"]]=dict(origin_um=[x/u,y/u],orient=orient,master=c["master"],size_um=[w/u,h/u],
                               centre_um=[(x+w/2)/u,(y+h/2)/u])
        moves.append(dict(name=c["name"],dx_um=round(dx/u,6),dy_um=round(dy/u,6),
                          displacement_um=round((abs(dx)+abs(dy))/u,6)))
    out["cell_placements"]=result
    out["placement_basis"]="PLAN-STAGE deterministic LEF/rows/macros/fixed cells; never a build-time or measured adjustment"
    return out,dict(cells=len(result),macro_halo_um=macro_halo_um,cell_or_macro_overlaps=0,
                    max_displacement_um=max((m["displacement_um"] for m in moves),default=0),
                    moved=sum(m["displacement_um"]>1e-9 for m in moves),moves=moves)


def _mst_length(points):
    """Manhattan MST estimate of total wire; each sink's path remains Manhattan."""
    if len(points)<2:return 0.
    used={0};best=[abs(p[0]-points[0][0])+abs(p[1]-points[0][1]) for p in points];total=0.
    while len(used)<len(points):
        k=min((i for i in range(len(points)) if i not in used),key=lambda i:(best[i],i))
        total+=best[k];used.add(k);q=points[k]
        for i,p in enumerate(points):
            if i not in used:best[i]=min(best[i],abs(p[0]-q[0])+abs(p[1]-q[1]))
    return total


def predict_tree(sl, libraries, sink_points, sink_caps_ff, wire_r_kohm_um, wire_c_ff_um, input_slew_ps=40.):
    """NLDM buffer delay at total branch load + Elmore branch wires.

    libraries: {corner: die_clock_128.lib_cells(...)}; sink points/caps identify
    every actual pin. Uses Manhattan MST net capacitance, Manhattan branch R.
    This predicts imbalance before build; it never chooses cells/pads from it.
    No routed clock result is consumed. Missing sink/cap refuses rather than a
    zero-load substitute. Macro and FF leaves are both propagated and reported.
    """
    import die_clock_128 as C128
    plan=CI.compile_slice(sl);tree=plan["core_tree"]
    if not tree:raise CI.InfraError("predict_tree needs a named core_tree")
    cells={c["name"]:c for c in plan["cells"]};children=defaultdict(list);leaves=defaultdict(list)
    for n in tree["nodes"]:children[n["parent"]].append(n["name"])
    for l in tree["leaves"]:leaves[l["node"]]+=l["sinks"]
    for sinks in leaves.values():
        for sink in sinks:
            if sink not in sink_points or sink not in sink_caps_ff:raise CI.InfraError(f"predictor missing physical point/cap for {sink}")
    answer={}
    for corner,libs in libraries.items():
        arrivals={};slews={};sink_arr={};nets=[]
        for n in tree["nodes"]:
            name=n["name"];point=cells[name]["xy_um"]
            if n["parent"].startswith("port:"):arrivals[name]=0.;slews[name]=input_slew_ps
            targets=[(q,cells[q]["xy_um"],libs[cells[q]["master"]]["cap"]) for q in children[name]]
            targets += [(q,sink_points[q],sink_caps_ff[q]) for q in leaves[name]]
            if not targets:continue
            wire=_mst_length([point]+[q[1] for q in targets]);load=sum(q[2] for q in targets)
            lib=libs[cells[name]["master"]]
            delay=C128._bilin(lib["delay"],slews[name],wire*wire_c_ff_um+load)
            slew=C128._bilin(lib["trans"],slews[name],wire*wire_c_ff_um+load)
            for target,q,cap in targets:
                length=abs(point[0]-q[0])+abs(point[1]-q[1])
                elmore=length*wire_r_kohm_um*(length*wire_c_ff_um/2+cap)
                arrival=arrivals[name]+delay+elmore
                if target in cells:
                    arrivals[target]=arrival;slews[target]=math.hypot(slew,2.2*elmore)
                else:sink_arr[target]=arrival
            nets.append(dict(driver=name,fanout=len(targets),wire_um=round(wire,3),load_ff=round(load,3),
                             cell_delay_ps=round(delay,3),input_arrival_ps=round(arrivals[name],3)))
        vals=list(sink_arr.values());leaf_means=[]
        for leaf in tree["leaves"]:
            v=[sink_arr[q] for q in leaf["sinks"]]
            leaf_means.append(dict(node=leaf["node"],kind=leaf.get("load_class","register"),sinks=len(v),
                                   min_ps=min(v),mean_ps=sum(v)/len(v),max_ps=max(v)))
        answer[corner]=dict(sinks=len(vals),min_ps=min(vals),mean_ps=sum(vals)/len(vals),max_ps=max(vals),
                            window_ps=max(vals)-min(vals),leaf_means=leaf_means,nets=nets)
    return dict(basis="Geometry/ASAP7 NLDM + Manhattan-MST branch C + Elmore path R; no clock measurements/pad selection",
                wire_r_kohm_um=wire_r_kohm_um,wire_c_ff_um=wire_c_ff_um,input_slew_ps=input_slew_ps,corners=answer)
