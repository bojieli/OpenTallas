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
    try:
        import tkinter
        interp = tkinter.Tcl()
        records = [list(interp.splitlist(line)) for line in open(path)]
    except ModuleNotFoundError:
        # Fleet Python can omit Tk while tclsh is installed. Parse list data
        # with Tcl itself, never eval snapshot strings or shell interpolation.
        import base64
        import subprocess
        script = """set f [open [lindex $argv 0] r]
while {[gets $f row] >= 0} {
 set fields {}
 foreach item $row {lappend fields [binary encode base64 -maxlen 0 [encoding convertto utf-8 $item]]}
 puts [join $fields "\t"]
}
close $f
"""
        result = subprocess.run(['tclsh', '/dev/stdin', str(path)], input=script, text=True, capture_output=True, check=True)
        records = [[base64.b64decode(x).decode('utf-8') for x in line.split('\t')] if line else [] for line in result.stdout.splitlines()]
    out = dict(rows=[], masters={}, obstacles=[])
    for f in records:
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


def sink_cap(value, corner):
    """Actual per-corner pin capacitance, or explicitly shared scalar input."""
    result = value[corner] if isinstance(value, dict) else value
    result = float(result)
    if not math.isfinite(result) or result < 0:
        raise CI.InfraError(f"invalid sink capacitance at {corner}")
    return result


# ---------------------------------------------------------------------------------------------------------------
# PLAN-ICG-MODEL (10-26): gated domains and CTS-open subtrees.
# A planned ICG is timed by its liberty CLK->GCLK arc (NLDM at the plan load); the CTS-open subtree below an ICG
# (or below a cts_open planned buffer) is not a list of planned cells, so it is modelled from its census N, the
# planned CTS stage count k = ceil(log_F N) (core_infra._cts_levels) and its region geometry:
#   load on the driver  = one CTS root buffer (CTS_ROOT_MASTER) next to the driver (TritonCTS places the subtree
#                         root at the driver: measured bf_col 16/16 gated domains, root buffer within ~2 um of the ICG)
#   subtree mean        = stage_ps * k + region_ps_per_um * D,  D = Manhattan driver -> farthest region corner
#                         (= (w + h) / 2 for a gate at its region centre, the 12.8b plan position)
#   subtree min / max   = mean - lo_ps_per_um * D / mean + hi_ps_per_um * D
# measured from the root-buffer input pin. Coefficients are per corner and were fitted ONCE on routed, signed-off
# gated cores (results/plan_icg_model_1026); they are plan constants, never per-build values (12.8 d1).
CTS_ROOT_MASTER = "BUFx24_ASAP7_75t_R"
OPEN_SUBTREE_CAL = {
    "basis": ("PLAN-ICG-MODEL 10-26 fit on 1,043 single-level gated domains of 2 routed signed-off S81 cores "
              "(qxpq_w10 cpr ffacf68cd 1,025 ICG domains / 37,431 sinks; bf_col compact199 05a8d46ee 18 ICG domains / "
              "52,679 sinks), 6_final ODB+SPEF OpenSTA, each core equal weight; results/plan_icg_model_1026"),
    "TT": dict(stage_ps=24.93, region_ps_per_um=0.636, lo_ps_per_um=0.092, hi_ps_per_um=0.270),
    "FF": dict(stage_ps=19.06, region_ps_per_um=0.518, lo_ps_per_um=0.086, hi_ps_per_um=0.239),
}

# Calibrated shape (COORD 10-26 condition): the fit only covers ONE-LEVEL REGIONAL gated domains. Measured envelope
# of the regional domains (whole-core gates excluded): N <= 1,472 sinks (k <= 3), driver->farthest-corner reach
# <= 224.4 um, region <= 0.346 of the core outline area (limits rounded up to 224.5 um / 0.35), no gate inside
# the domain. bf_col's whole-core gates
# (16,213 / 13,994 sinks, reach 307.5 / 313.7 um, 0.905 / 0.937 of the outline) sit outside it and are
# under-predicted by ~50 ps TT (CTS grew 9-11 levels to balance). Outside the envelope the number is reported
# but the prediction is INVALID for build gating.
CAL_ENVELOPE = dict(max_sinks=1472, max_levels=3, max_reach_um=224.5, max_outline_fraction=0.35, max_nested_gates=0)


def calibration_check(n_sinks, levels, reach_um, region_rect_um, outline_um, nested_gates=0, env=None):
    """[] when the CTS-open domain is inside the calibrated one-level regional shape, else the list of reasons."""
    env = env or CAL_ENVELOPE
    x0, y0, x1, y1 = (float(v) for v in region_rect_um)
    frac = (x1 - x0) * (y1 - y0) / (float(outline_um[0]) * float(outline_um[1]))
    bad = []
    if nested_gates > env["max_nested_gates"]:
        bad.append(f"multi-level gated domain ({nested_gates} gate(s) inside)")
    if n_sinks > env["max_sinks"]:
        bad.append(f"{n_sinks} sinks > calibrated {env['max_sinks']}")
    if levels > env["max_levels"]:
        bad.append(f"{levels} CTS levels > calibrated {env['max_levels']}")
    if reach_um > env["max_reach_um"]:
        bad.append(f"reach {reach_um:.1f} um > calibrated {env['max_reach_um']}")
    if frac > env["max_outline_fraction"]:
        bad.append(f"region {frac:.3f} of the outline > {env['max_outline_fraction']} (whole-core gate)")
    return bad


def icg_lib_cells(corner, libdir, names=("ICGx1_ASAP7_75t_R",)):
    """{ICG master: dict(delay, trans, cap)} for the CLK->GCLK positive-unate rise arc of the ASAP7 RVT SEQ liberty.

    Same table form as die_clock_128.lib_cells, so predict_tree treats a gate like a buffer stage (input CLK)."""
    import gzip
    import re
    from pathlib import Path
    import die_clock_128 as C128
    path = sorted(Path(libdir).glob(f"asap7sc7p5t_SEQ_RVT_{corner}_nldm_*.lib*"))
    if not path:
        raise CI.InfraError(f"no ASAP7 SEQ RVT {corner} liberty in {libdir}")
    txt = (gzip.open if path[0].suffix == ".gz" else open)(path[0], "rt").read()
    out = {}
    for n in names:
        i = txt.index(f"cell ({n})")
        j = txt.find("\n  cell (", i + 10)
        blk = txt[i:j if j > 0 else len(txt)]
        g = blk[blk.index("pin (GCLK)"):]
        k = g.index("cell_rise")                                  # the non-unate-fall CLK->GCLK rise group
        arc = g[g.rfind("timing ()", 0, k):]
        clk = blk[blk.index("pin (CLK)"):]
        out[n] = dict(delay=C128._table(arc, "cell_rise"), trans=C128._table(arc, "rise_transition"),
                      cap=float(re.search(r"rise_capacitance : ([\d.]+)", clk).group(1)))
    return out


def region_reach(rect, driver_xy=None):
    """Manhattan distance from the driver (default: region centre) to the farthest corner of the region rect."""
    x0, y0, x1, y1 = (float(v) for v in rect)
    if not (x1 >= x0 and y1 >= y0):
        raise CI.InfraError(f"invalid region rect {rect}")
    x, y = driver_xy if driver_xy is not None else ((x0 + x1) / 2, (y0 + y1) / 2)
    return max(abs(x - a) + abs(y - b) for a in (x0, x1) for b in (y0, y1))


def open_subtree(n_sinks, region_rect_um, corner, driver_xy=None, fanout=CI.CTS_FANOUT, cal=None):
    """Latency of a CTS-open subtree from its root-buffer input pin (ps): planned stages + region geometry only."""
    cal = (cal or OPEN_SUBTREE_CAL)[corner]
    k = CI._cts_levels(dict(domain_sinks=n_sinks, cts_fanout=fanout), "open subtree")
    d = region_reach(region_rect_um, driver_xy)
    mean = cal["stage_ps"] * k + cal["region_ps_per_um"] * d
    return dict(levels=k, region_d_um=d, mean_ps=mean,
                min_ps=mean - cal["lo_ps_per_um"] * d, max_ps=mean + cal["hi_ps_per_um"] * d)


def gated_leaf_region(leaf, gate=None, sink_points=None):
    """Plan region of a CTS-open leaf: declared region_rect_um, else the gate's island rect, else the listed sinks'
    bounding box (ungated cts_open leaves). A gate without either refuses (no whole-outline default)."""
    if leaf.get("region_rect_um"):
        return list(leaf["region_rect_um"])
    if gate is not None and gate.get("island_rect_um"):
        return list(gate["island_rect_um"])
    pts = [sink_points[s] for s in leaf.get("sinks", []) if sink_points and s in sink_points]
    if pts:
        return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
    raise CI.InfraError(f"CTS-open leaf {leaf['node']}: needs region_rect_um (or a gate island_rect_um) to be timed")


def predict_tree(sl, libraries, sink_points, sink_caps_ff, wire_r_kohm_um, wire_c_ff_um, input_slew_ps=40., routing_model=None, subtree_cal=None):
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
    cells={c["name"]:dict(xy_um=c["xy_um"],master=c["master"]) for c in plan["cells"]}
    gates={g["inst"]:g for g in tree.get("gates",[])}
    for g in gates.values():cells[g["inst"]]=dict(xy_um=g["xy_um"],master=g["master"])
    children=defaultdict(list);leaves=defaultdict(list);opened={}
    for n in tree["nodes"]:children[n["parent"]].append(n["name"])
    for g in gates.values():children[g["parent"]].append(g["inst"])
    for l in tree["leaves"]:
        if l.get("load_class")=="gated_domain" or l.get("cts_open"):
            # CTS-open leaf: its sinks hang below a CTS-grown subtree, not on the planned driver's net (PLAN-ICG-MODEL)
            rect=gated_leaf_region(l,gates.get(l["node"]),sink_points)
            opened[l["node"]]=dict(leaf=l,rect=rect,n=l.get("domain_sinks",len(l.get("sinks",[]))))
        else:leaves[l["node"]]+=l["sinks"]
    for sinks in leaves.values():
        for sink in sinks:
            if sink not in sink_points or sink not in sink_caps_ff:raise CI.InfraError(f"predictor missing physical point/cap for {sink}")
    order=[n["name"] for n in tree["nodes"]]+list(gates)
    answer={}
    for corner,libs in libraries.items():
        arrivals={};slews={};sink_arr={};nets=[];open_arr={}
        for name in order:
            if cells[name]["master"] not in libs:raise CI.InfraError(f"no {corner} liberty table for {cells[name]['master']} ({name})")
        for name in order:
            point=cells[name]["xy_um"];lib=libs[cells[name]["master"]]
            if name not in arrivals:arrivals[name]=0.;slews[name]=input_slew_ps
            targets=[(q,cells[q]["xy_um"],libs[cells[q]["master"]]["cap"]) for q in children[name]]
            targets += [(q,sink_points[q],sink_cap(sink_caps_ff[q],corner)) for q in leaves[name]]
            if name in opened:
                if CTS_ROOT_MASTER not in libs:raise CI.InfraError(f"CTS-open leaf {name} needs the {CTS_ROOT_MASTER} {corner} table")
                sub=open_subtree(opened[name]["n"],opened[name]["rect"],corner,point,opened[name]["leaf"].get("cts_fanout",CI.CTS_FANOUT),subtree_cal)
                opened[name]["sub_"+corner]=sub
                targets.append(("open:"+name,point,libs[CTS_ROOT_MASTER]["cap"]))
            if not targets:continue
            wire=_mst_length([point]+[q[1] for q in targets]);load=sum(q[2] for q in targets)
            rc=None
            if routing_model is not None:
                from core_infra_wire import rooted_rc
                branch=routing_model.get('nodes',{}).get(name)
                if branch is None:branch=routing_model['nonleaf' if children[name] else 'leaf']
                rc=rooted_rc([point]+[q[1] for q in targets],[q[2] for q in targets],**branch)
                wire=rc['wire_um'];wire_load=rc['wire_cap_ff']
            else:wire_load=wire*wire_c_ff_um
            delay=C128._bilin(lib["delay"],slews[name],wire_load+load)
            slew=C128._bilin(lib["trans"],slews[name],wire_load+load)
            for k,(target,q,cap) in enumerate(targets):
                length=abs(point[0]-q[0])+abs(point[1]-q[1])
                elmore=rc['target_elmore_ps'][k] if rc else length*wire_r_kohm_um*(length*wire_c_ff_um/2+cap)
                arrival=arrivals[name]+delay+elmore
                if target in cells:
                    arrivals[target]=arrival;slews[target]=math.hypot(slew,2.2*elmore)
                elif target.startswith("open:"):open_arr[target[5:]]=arrival
                else:sink_arr[target]=arrival
            nets.append(dict(driver=name,kind="icg" if name in gates else "buffer",fanout=len(targets),wire_um=round(wire,3),load_ff=round(load,3),
                             cell_delay_ps=round(delay,3),input_arrival_ps=round(arrivals[name],3),
                             wire_geometry={k:rc[k] for k in ('original_tree_wire_um','overlap_removed_um','overlap_removed_fraction','network_cycles') if k in rc} if rc else {}))
        leaf_means=[];groups=[]
        for leaf in tree["leaves"]:
            node=leaf["node"]
            if node in opened:
                sub=opened[node]["sub_"+corner];base=open_arr[node];n=opened[node]["n"]
                row=dict(node=node,kind=leaf.get("load_class","register") if not leaf.get("cts_open") or leaf.get("load_class")=="gated_domain" else "cts_open",
                         sinks=n,min_ps=base+sub["min_ps"],mean_ps=base+sub["mean_ps"],max_ps=base+sub["max_ps"],
                         driver_out_ps=round(base,3),cts_levels=sub["levels"],region_d_um=round(sub["region_d_um"],3),modelled_subtree=True)
                why=calibration_check(n,sub["levels"],sub["region_d_um"],opened[node]["rect"],sl["outline_um"],leaf.get("nested_gates",0))
                row["calibration"]="OUT" if why else "IN";row["out_of_calibration"]=why
                if leaf.get("load_class")=="gated_domain":row["kind"]="gated_domain"
            else:
                v=[sink_arr[q] for q in leaf["sinks"]]
                row=dict(node=node,kind=leaf.get("load_class","register"),sinks=len(v),min_ps=min(v),mean_ps=sum(v)/len(v),max_ps=max(v))
            leaf_means.append(row);groups.append(row)
        n=sum(g["sinks"] for g in groups)
        lo=min(g["min_ps"] for g in groups);hi=max(g["max_ps"] for g in groups)
        out=[g["node"] for g in groups if g.get("calibration")=="OUT"]
        answer[corner]=dict(sinks=n,min_ps=lo,mean_ps=sum(g["mean_ps"]*g["sinks"] for g in groups)/n,max_ps=hi,
                            window_ps=hi-lo,leaf_means=leaf_means,nets=nets,
                            prediction="INVALID" if out else "VALID",valid_for_build_gating=not out,out_of_calibration_leaves=out)
    basis=("Geometry/ASAP7 NLDM + directional rooted shared-subtree RC prototype; no clock measurements/pad selection" if routing_model is not None else "Geometry/ASAP7 NLDM + historical Manhattan-MST branch C/direct branch R; no clock measurements/pad selection")
    if opened:basis+="; ICG = liberty CLK->GCLK arc, CTS-open subtrees = plan stage count + region model ("+(subtree_cal or OPEN_SUBTREE_CAL)["basis"]+")"
    return dict(basis=basis,
                wire_r_kohm_um=wire_r_kohm_um,wire_c_ff_um=wire_c_ff_um,input_slew_ps=input_slew_ps,routing_model=routing_model,corners=answer)
