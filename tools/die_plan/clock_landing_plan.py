"""Compose real clock-landing pins, storage bands and active monitor cohorts.

Returns a new plan and an emission sidecar. No canonical file is edited. The
reverse monitor follows the current reset wavefront and uses only actual child
inputs; split types have exact uniform hardware. Actual mapped placement,
clock export, ring-window STA and the source-bound token gate still qualify it.
"""
import copy
import hashlib
import json
import math
from collections import defaultdict

import clock_landings as CL
import reset_tree as RT
import schema as S


def _face(t, xy):
    w, h = t["outline_um"]; x, y = xy
    return min(((x,"W"),(w-x,"E"),(y,"S"),(h-y,"N")))[1]


def _scalar(t, name, direction, xy, kind, *, shift=0):
    face = _face(t, xy)
    ext = t["outline_um"][1 if face in "EW" else 0]
    at = xy[1 if face in "EW" else 0] + shift
    at = max(.432, min(ext-.432, round((at-.216)/.432)*.432+.216))
    layer = ("M8" if face in "EW" else "M9") if kind=="clock" else ("M4" if face in "EW" else "M3")
    return dict(name=name, dir=direction, width=1, kind=kind, face=face,
                window_um=[round(at-.216,6),round(at+.216,6)], layers=[layer], order="lsb_low")


# QC default observer (unchanged): the sys-face controller's two real inputs.
QC_OBSERVER=dict(module="qfd_sys_face_lctx3_wrapped",instance_suffix="u_sys_face",
                 fault_port="obs_fault",ready_port="seq_cfg_image_ready")


def _bus_geom(t, bus):
    if bus in t.get("_cland_geom",{}):return t["_cland_geom"][bus]
    for b in t.get("buses",[]):
        if b["name"] == bus and "window_um" in b and "face" in b:
            return b
    for s in t.get("ft_slots",[]):
        for suffix,face,window in (("_i","in_face","in_window_um"),("_o","out_face","out_window_um")):
            if s["name"]+suffix == bus and window in s:
                return dict(name=bus,face=s[face],window_um=s[window],width=s["width"])
    raise ValueError(f"landing bus geometry missing: {bus}")


def _bus_xy(t,bus):
    b=_bus_geom(t,bus);at=sum(b["window_um"])/2;w,h=t["outline_um"]
    return [0 if b["face"]=="W" else w,at] if b["face"] in "EW" else [at,0 if b["face"]=="S" else h]


def _fill_ft_windows(raw,path):
    """Materialize omitted slot-side windows from the real abutting port.

    Existing plans omit some input windows when the source side owns the
    shared seam geometry. The ring still needs that exact local face window.
    """
    P=S.Plan(raw,path);inferred=defaultdict(list)
    for pr in P.ports.values():
        for side in ("src","dst"):
            pn=pr[side]["part"]
            if pn not in P.parts:continue
            bus=pr[side]["bus"];tn=P.parts[pn]["type"]
            for slot in P.types[tn].get("ft_slots",[]):
                for suffix,fk,wk in (("_i","in_face","in_window_um"),("_o","out_face","out_window_um")):
                    if slot["name"]+suffix!=bus or wk in slot:continue
                    f=slot[fk];df=P.die_face(pn,f);x0,y0,x1,y1=P.rect(pn);lo,hi=pr["window_um"]
                    pts=([(x0 if df=="W" else x1,v) for v in (lo,hi)] if df in "EW" else
                         [(v,y0 if df=="S" else y1) for v in (lo,hi)])
                    axis=1 if f in "EW" else 0
                    vals=sorted(round(P.to_type(pn,xy)[axis],6) for xy in pts)
                    inferred[(tn,slot["name"],wk)].append(vals)
    for (tn,name,wk),vals in inferred.items():
        if any(max(abs(a-b) for a,b in zip(vals[0],v))>1e-4 for v in vals[1:]):
            raise ValueError(f"nonuniform inferred seam geometry {tn}.{name}.{wk}: {vals}")
        slot=next(s for s in raw["partition_types"][tn]["ft_slots"] if s["name"]==name)
        suffix="_i" if wk=="in_window_um" else "_o";face=slot["in_face" if suffix=="_i" else "out_face"]
        # Keep inferred information in the helper only. Adding an input window
        # to the canonical slot would also assert its internal output layer /
        # order at the seam, changing448 existing valid port contracts.
        raw["partition_types"][tn].setdefault("_cland_geom",{})[name+suffix]=dict(
            name=name+suffix,face=face,window_um=vals[0],width=slot["width"])


def _fill_port_windows(raw,path,table):
    """Type-local face/window for landing buses whose geometry lives on the PORT.

    Plans such as KV declare bus geometry only on the die-frame port (face =
    source face, destination uses the opposite face). Placed replicas may be
    mirrored/rotated (MX/MY/R180), so each endpoint is mapped back to the TYPE
    frame from the port's die window and the replica's orient. One window set
    per type: every replica carrying the bus must map to the same type-local
    window, else the compose fails (no per-instance pins on a shared type).
    Buses that already declare type geometry are left untouched.
    """
    P=S.Plan(raw,path);need=set();ports={p["id"]:p for p in raw["ports"]}
    for r in table["ports"]:
        pr=ports[r["port"]]
        for side in ("src","dst"):
            pn=pr[side]["part"]
            if pn in P.parts:need.add((P.parts[pn]["type"],pr[side]["bus"]))
    inferred=defaultdict(list)
    for pr in raw["ports"]:
        if not all(k in pr for k in ("face","window_um")):continue
        for side in ("src","dst"):
            pn=pr[side]["part"]
            if pn not in P.parts:continue
            tn=P.parts[pn]["type"];bus=pr[side]["bus"]
            if (tn,bus) not in need:continue
            t=raw["partition_types"][tn]
            if bus in t.get("_cland_geom",{}) or _has_type_geom(t,bus):continue
            df=pr["face"] if side=="src" or pr["src"]["part"]==S.DIE_PART else S.OPP[pr["face"]]
            tf=P.type_face(pn,df);x0,y0,x1,y1=P.rect(pn);lo,hi=pr["window_um"]
            pts=([(x0 if df=="W" else x1,v) for v in (lo,hi)] if df in "EW" else
                 [(v,y0 if df=="S" else y1) for v in (lo,hi)])
            axis=1 if tf in "EW" else 0
            vals=sorted(round(P.to_type(pn,xy)[axis],6) for xy in pts)
            inferred[(tn,bus)].append((tf,vals,pn))
    for (tn,bus),rows in inferred.items():
        tf,vals,_=rows[0]
        bad=[(f,v,pn) for f,v,pn in rows[1:] if f!=tf or max(abs(a-b) for a,b in zip(vals,v))>1e-4]
        if bad:raise ValueError(f"nonuniform type-local landing window {tn}.{bus}: {rows[0]} vs {bad[:3]}")
        width=next((b.get("width") for b in raw["partition_types"][tn].get("buses",[]) if b["name"]==bus),None)
        raw["partition_types"][tn].setdefault("_cland_geom",{})[bus]=dict(
            name=bus,face=tf,window_um=vals,width=width,source="port window -> type frame (orient-aware)",
            replicas=len(rows))


def _has_type_geom(t,bus):
    try:_bus_geom(t,bus);return True
    except ValueError:return False


def _hard(raw,tn):
    return bool(raw["partition_types"][tn].get("hard"))


def _reset_entry_xy(W,raw,tn):
    """Reset entry of a type: generated wavefront entry, or a hard partition's delivered-reset tap."""
    if tn in W["types"] and "in_um" in W["types"][tn]:return W["types"][tn]["in_um"]
    t=raw["partition_types"][tn]
    return list(t.get("reset",{}).get("tap_um",[t["outline_um"][0]/2,t["outline_um"][1]/2]))


def _hard_tree(entry,point,reach=405-2.16):
    """Registered monitor chain inside a hard partition's SOFT wrapper.

    The hard IP has no generated reset tree. Its landing ring sits at the
    received window (digital edge); ready/fault return to the delivered-reset
    entry (the reset-neighbour edge) through registered collector stages <=
    reach apart along the L path. Boot-time only: zero data cycles.
    """
    (ex,ey),(px,py)=entry,point;total=abs(px-ex)+abs(py-ey)
    n=max(0,math.ceil(total/reach)-1);nodes=[]
    for i in range(1,n+1):
        d=total*i/(n+1);dx=min(d,abs(px-ex));dy=d-dx
        nodes.append([round(ex+math.copysign(dx,px-ex),3),round(ey+math.copysign(dy,py-ey),3)])
    relays=[];prev="rst_root_n"
    for i,xy in enumerate(nodes):
        q=f"cland_h{i}";relays.append(dict(q=q,d=prev,xy=xy,name="u_cland_collect_"+q));prev=q
    return dict(hard=True,root=list(entry),relays=relays,n_clock_taps=0,leaf_node=prev,
                max_hop_um=round(total/(n+1),3))


def _grid_scan(w,h,obstacles,margin,px,py,area,depth,length,g=2.16,reach=405-2.16):
    """FALLBACK-S81-2 10-26: exhaustive macro-free bank search, used ONLY when the face-strip and compact-bank
    searches above find nothing.  Same legality (outline margin, no obstacle overlap, every corner within reach of the
    bus pin), same reserved area; any aspect from the face strip (depth x length) to near-square, both orientations,
    on a 2.16-um grid (prefix-sum occupancy).  Returns legal boxes (may be empty)."""
    import numpy as np
    nx,ny=int(w//g),int(h//g)
    if nx<=0 or ny<=0:return []
    occ=np.zeros((nx,ny),np.int32)
    for o in obstacles:
        i0,i1=max(0,int(math.floor(o[0]/g))),min(nx,int(math.ceil(o[2]/g)))
        j0,j1=max(0,int(math.floor(o[1]/g))),min(ny,int(math.ceil(o[3]/g)))
        if i1>i0 and j1>j0:occ[i0:i1,j0:j1]=1
    m=int(math.ceil(margin/g));occ[:m,:]=1;occ[nx-m:,:]=1;occ[:,:m]=1;occ[:,ny-m:]=1
    S=np.zeros((nx+1,ny+1),np.int64);S[1:,1:]=occ.cumsum(0).cumsum(1)
    shapes=set();a_cells=area/(g*g)
    for d in sorted({max(4,int(math.ceil(depth/g)))*k for k in (1,2,3,4,6,8)}):
        L=int(math.ceil(a_cells/d))
        if L>=4:shapes.update({(d,L),(L,d)})
    s0=int(math.ceil(math.sqrt(a_cells)));shapes.add((s0,s0))
    # PATH-S81-PD 10-26: thin long banks (4..8 rows/cols deep, any length) along a face edge or a free channel,
    # still every corner within reach and the same reserved area. Only reached when every search above failed.
    for d in range(4,9):
        L=int(math.ceil(a_cells/d))
        if L>=4:shapes.update({(d,L),(L,d)})
    out=[]
    for bw,bh in sorted(shapes):
        if bw>nx or bh>ny:continue
        blk=S[bw:,bh:]-S[:-bw,bh:]-S[bw:,:-bh]+S[:-bw,:-bh]
        ii,jj=np.nonzero(blk==0)
        if not len(ii):continue
        x0=ii*g;y0=jj*g;x1=x0+bw*g;y1=y0+bh*g
        far=np.maximum(np.maximum(abs(x0-px),abs(x1-px))+np.maximum(abs(y0-py),abs(y1-py)),0)
        ok=np.nonzero(far<=reach)[0]
        if not len(ok):continue
        k=ok[np.argmin(far[ok])]
        out.append([float(x0[k]),float(y0[k]),float(x1[k]),float(y1[k])])
    return out


def _storage_band(t,bus,width,used,*,has_epoch=True):
    b=_bus_geom(t,bus);w,h=t["outline_um"];lo,hi=b["window_um"]
    length=max(hi-lo,8.64);rw=64*math.ceil((width+int(has_epoch))/64)
    spanlo=(lo+hi-length)/2;spanhi=spanlo+length
    # Conservative physical reserve includes padded ring slots/readout, control,
    # selectors and local clock buffering, at40% fill and actualASAP7 FF area.
    area=(5*rw*.2916 + 4*rw*.0729 + 160*.2916)/.40
    depth=math.ceil(max(8.64,area/length)/2.16)*2.16
    obstacles=RT.blockages(t)+used
    # Existing face registers and fixed FT banks remain in place. The new ring
    # may use nearby open rows, never their occupied site bands.
    margin=17.28
    for slot in t.get("ft_slots",[]):
        cell=slot.get("bit_site_cell_um",[1.404,.27])
        for stage in slot.get("bit_sites_um",[]):
            if stage:
                obstacles.append([min(p[0] for p in stage)-cell[0]/2,min(p[1] for p in stage)-cell[1]/2,
                                  max(p[0] for p in stage)+cell[0]/2,max(p[1] for p in stage)+cell[1]/2])
        if not slot.get("bit_sites_um"):
            obstacles += [[x-2.16,y-2.16,x+2.16,y+2.16] for x,y in slot.get("regs_um",[])]
    candidates=[];px,py=_bus_xy(t,bus)
    for inset in [margin+2.16*k for k in range(88)]:
        f=b["face"]
        box=([inset,spanlo,inset+depth,spanhi] if f=="W" else
             [w-inset-depth,spanlo,w-inset,spanhi] if f=="E" else
             [spanlo,inset,spanhi,inset+depth] if f=="S" else [spanlo,h-inset-depth,spanhi,h-inset])
        if box[0]<margin or box[1]<margin or box[2]>w-margin or box[3]>h-margin:continue
        if max(abs(x-px)+abs(y-py) for x in(box[0],box[2]) for y in(box[1],box[3]))>405-2.16:continue
        if any(min(box[2],o[2])>max(box[0],o[0])+1e-6 and min(box[3],o[3])>max(box[1],o[1])+1e-6 for o in obstacles):continue
        candidates.append(box)
    # A dense face may have no full-height strip beside a macro. A compact
    # bank in the adjoining macro-free row is valid when EVERY storage point
    # stays within405um of the original bus pin. Consider both bank aspects;
    # do not move the pin or add an unpriced relay stage.
    px,py=_bus_xy(t,bus)
    aspects=[(depth,length),(length,depth)]
    # FALLBACK-HEAD 10-26: a face whose rows are all macro (s81_head hd_tile W/E: elemA columns from y8.64) may still
    # have a macro-free CHANNEL within reach (hd_tile: the45-um horizontal core channel). Only when both legacy
    # aspects fail, also try equal-area banks whose short side fits such a channel. Same area, same405-um rule.
    extra=[]
    for k in range(5,41):
        hh=2.16*k;ww=math.ceil(area/hh/2.16)*2.16
        extra += [(ww,hh),(hh,ww)]
    for bw,bh in (() if candidates else aspects+extra):
        if candidates and (bw,bh) not in aspects:break
        xs={margin,w-bw-margin,max(margin,min(w-bw-margin,px-bw/2))}
        ys={margin,h-bh-margin,max(margin,min(h-bh-margin,py-bh/2))}
        for o in obstacles:
            xs.update((o[0]-bw-2.16,o[2]+2.16));ys.update((o[1]-bh-2.16,o[3]+2.16))
        # Necessary components of the exact corner/reach predicate below.
        # Keep iteration order and the same candidate set, but do not form the
        # Cartesian product of obstacle edges on the far side of a large tile.
        # S81 svc has hundreds of such edges; the unfiltered product dominates
        # the compose although every far-away box is immediately rejected.
        reach=405-2.16
        xs=[x for x in xs if margin<=x<=w-margin-bw and
            max(abs(x-px),abs(x+bw-px))<=reach]
        ys=[y for y in ys if margin<=y<=h-margin-bh and
            max(abs(y-py),abs(y+bh-py))<=reach]
        for x0 in xs:
            for y0 in ys:
                box=[x0,y0,x0+bw,y0+bh]
                if x0<margin or y0<margin or box[2]>w-margin or box[3]>h-margin:continue
                if max(abs(x-px)+abs(y-py) for x in(box[0],box[2]) for y in(box[1],box[3]))>405-2.16:continue
                if any(min(box[2],o[2])>max(box[0],o[0])+1e-6 and min(box[3],o[3])>max(box[1],o[1])+1e-6 for o in obstacles):continue
                candidates.append(box)
    if not candidates:
        candidates=_grid_scan(w,h,obstacles,margin,px,py,area,depth,length)
    if candidates:
        box=min(candidates,key=lambda b:max(abs(x-px)+abs(y-py) for x in(b[0],b[2]) for y in(b[1],b[3])))
        if (box[2]-box[0])*(box[3]-box[1])+1e-6<area:
            raise ValueError(f"clock landing band area undersized for {bus}")
        return dict(rect_um=[round(x,6) for x in box],width=width,ring_width=rw,
                    live_data_storage_flops=5*(width+int(has_epoch)),padded_data_storage_flops=5*rw,
                    clock_roles=dict(forwarded_write_flops=4*rw,local_read_flops=rw),
                    max_pin_to_band_hop_um=round(max(abs(x-px)+abs(y-py) for x in(box[0],box[2]) for y in(box[1],box[3])),3),
                    area_reserve_um2=round(area,3),placement="PROPOSED legal macro-free band; mapped anchoring pending")
    raise ValueError(f"no macro-free clock landing storage band for{bus}, required depth{depth:.2f}um")


def _collector_graph(P,W,root):
    """Orient only the MONITOR on the undirected reset edges. Reset is unchanged."""
    if root not in P.parts:raise ValueError(f"monitor observer partition {root} missing")
    graph=defaultdict(list)
    for pn,r in W["parts"].items():
        if r["parent"] is not None:graph[pn].append(r["parent"]);graph[r["parent"]].append(pn)
    parent={root:None};todo=[root]
    while todo:
        pn=todo.pop()
        for other in graph[pn]:
            if other not in parent:parent[other]=pn;todo.append(other)
    if set(parent)!=set(P.parts):raise ValueError("monitor reset-neighbor graph disconnected")
    return parent


def _monitor_endpoints(P,W,src,dst,hard_xy=None):
    """Local terminal nodes on an unchanged physical reset-neighbor edge.

    A hard partition (no generated reset tree, e.g. a hard PHY) is only ever a
    reset LEAF: its monitor root is the one registered collector in its soft
    wrapper (digital edge), at hard_xy(part); it can never be a monitor parent.
    """
    if W["parts"][src]["parent"]==dst:
        k=int(W["parts"][src]["source"].rsplit("_",1)[1])
        if P.types[P.parts[dst]["type"]].get("hard"):
            raise ValueError(f"monitor edge {src}->{dst}: a hard partition cannot collect monitor children")
        dt=RT.for_type(P,P.parts[dst]["type"])
        if P.types[P.parts[src]["type"]].get("hard"):
            if hard_xy is None:raise ValueError(f"monitor edge {src}->{dst}: hard source needs its wrapper collector site")
            sxy=hard_xy(src)
        else:sxy=W["types"][P.parts[src]["type"]]["in_um"]
        return dict(src_node="rst_root_n",src_xy=sxy,
                    dst_node=f"rst_n_t{dt['n_clock_taps']+k}",dst_xy=W["types"][P.parts[dst]["type"]]["outs"][k][1:])
    if W["parts"][dst]["parent"]==src:
        if P.types[P.parts[src]["type"]].get("hard"):
            raise ValueError(f"monitor edge {src}->{dst}: a hard partition cannot collect monitor children")
        k=int(W["parts"][dst]["source"].rsplit("_",1)[1])
        st=RT.for_type(P,P.parts[src]["type"])
        return dict(src_node=f"rst_n_t{st['n_clock_taps']+k}",src_xy=W["types"][P.parts[src]["type"]]["outs"][k][1:],
                    dst_node="rst_root_n",dst_xy=W["types"][P.parts[dst]["type"]]["in_um"])
    raise ValueError(f"monitor edge {src}->{dst} is not an existing reset-neighbor edge")


def _dataflow_tree(P,table,pports,observer):
    """Monitor DAG on the landed DATA ports (opt-in monitor="dataflow").  Potential = reverse-BFS distance to the
    observer over the data ports; each type gets ONE uniform tree bus (an out bus that strictly lowers the potential
    for every instance), so the monitor needs no per-position cohort types.  Other outputs carry local-only status,
    so the AND network has no cycle.  -> (tree_bus {type: bus|None}, parent {part: part|None}, dist)."""
    rin=defaultdict(set);outp=defaultdict(list)
    for r in table["ports"]:
        pr=pports[r["port"]];outp[r["src"]].append((pr["src"]["bus"],r["dst"]));rin[r["dst"]].add(r["src"])
    dist={observer:0};todo=[observer]
    while todo:
        u=todo.pop(0)
        for v in sorted(rin[u]):
            if v not in dist:dist[v]=dist[u]+1;todo.append(v)
    if set(dist)!=set(P.parts):raise ValueError(f"dataflow monitor: {len(set(P.parts)-set(dist))} parts cannot reach observer {observer}")
    by=defaultdict(list)
    for pn,p in P.parts.items():by[p["type"]].append(pn)
    tree_bus={};parent={}
    for tn,ns in sorted(by.items()):
        if observer in ns:
            if len(ns)!=1:raise ValueError(f"dataflow monitor: observer type {tn} is replicated")
            tree_bus[tn]=None;parent[observer]=None;continue
        buses=sorted({b for n in ns for b,_ in outp[n]})
        ok=[b for b in buses if all(any(bb==b and dist[d]<dist[n] for bb,d in outp[n]) for n in ns)]
        if not ok:raise ValueError(f"dataflow monitor: {tn} has no uniform out bus toward the observer")
        tree_bus[tn]=min(ok,key=lambda b:(max(dist[d] for n in ns for bb,d in outp[n] if bb==b),b))
        for n in ns:parent[n]=min(d for bb,d in outp[n] if bb==tree_bus[tn] and dist[d]<dist[n])
    return tree_bus,parent,dist


def _compose_dataflow(raw,plan_path,table,pports,ins,outs,region,base_type,observer_part,observer=None):
    """Monitor rides each landed data crossing: 2 status bits (ready, fault) in the receiving data ring (spare padded
    ring bits, same forwarded write clock), scalar ctl pins named by the DATA bus, so every instance of a type has
    identical ports and every pin has exactly one real driver/receiver (no absent-child ties, no cohort types)."""
    P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
    tree_bus,parent,dist=_dataflow_tree(P,table,pports,observer_part)
    bytype={};placement_failures=[];monitor_edges=[]
    for tn,t in raw["partition_types"].items():
        names=sorted(pn for pn,p in P.parts.items() if p["type"]==tn);pn=names[0]
        for n in names:
            if sorted(ins[n])!=sorted(ins[pn]) or sorted(outs[n])!=sorted(outs[pn]):
                raise ValueError(f"dataflow monitor: {tn} instances differ in landed buses ({n} vs {pn})")
        sig=dict(inputs=sorted(ins[pn]),outputs=sorted(outs[pn]),active=True,observer=pn==observer_part,
                 monitor="dataflow",tree_bus=tree_bus[tn])
        info=dict(base_type=base_type[pn],mask=sig,tree=None,local_sources=[],children=[],up_buses=[],
                  up_parent=None,reset_entry_um=W["types"].get(tn,{}).get("in_um"),bands={},
                  bus_geometry=copy.deepcopy(t.get("_cland_geom",{})))
        used=[]
        for bus,r in sorted(ins[pn].items()):
            point=_bus_xy(t,bus)
            try:band=_storage_band(t,bus,int(r["width"])+2,used);used.append(band["rect_um"])
            except ValueError as e:
                placement_failures.append(dict(type=tn,bus=bus,error=str(e)));band=dict(placement="FAIL",rect_um=None)
            band.update(instance="u_cland_"+bus,monitor_bits=dict(ready=int(r["width"])+1,fault=int(r["width"])+2,
                        note="status rides the data ring under the same forwarded write clock"))
            info["bands"][bus]=band
            info["local_sources"].append(dict(name=bus,ready="landing_ready_"+bus,fault="landing_fault_"+bus,xy_um=point,band=band))
            b=_scalar(t,"fclk_in_"+bus,"in",point,"clock");t.setdefault("buses",[]).append(b)
            t.setdefault("clock",{}).setdefault("edge_clocks",[]).append(dict(port=b["name"],tap_um=point,period_mult=1,
                note="source-forwarded ring write clock (data + 2 monitor bits); actual source-export/window STA required"))
            for j,kind in enumerate(("ready","fault")):
                t["buses"].append(_scalar(t,f"cland_dn_{kind}_{bus}","in",point,"ctl",shift=2.16*(j+2)))
            info["children"].append(dict(bus=bus,ready=f"cland_dn_ready_{bus}",fault=f"cland_dn_fault_{bus}",xy_um=point,seam=True))
        for bus in sorted(outs[pn]):
            point=_bus_xy(t,bus)
            t.setdefault("buses",[]).append(_scalar(t,"fclk_out_"+bus,"out",point,"clock"))
            for j,kind in enumerate(("ready","fault")):
                t["buses"].append(_scalar(t,f"cland_up_{kind}_{bus}","out",point,"ctl",shift=2.16*(j+2)))
            info["up_buses"].append(dict(bus=bus,carries="aggregate" if bus==tree_bus[tn] else "local"))
        tgt=_bus_xy(t,tree_bus[tn]) if tree_bus[tn] else [v/2 for v in t["outline_um"]]
        srcs=[c["xy_um"] for c in info["children"]] or [tgt]
        info["local_registered_depth"]=1+max(math.ceil((abs(x-tgt[0])+abs(y-tgt[1]))/405) for x,y in srcs)
        info.update(collector_root_node=("observer" if tree_bus[tn] is None else "cland_up_ready_"+tree_bus[tn]),collector_root_xy=tgt)
        bytype[tn]=info
    for r in table["ports"]:
        pr=pports[r["port"]]
        raw["ports"].append(dict(id="cland_clk__"+r["port"],src=dict(part=r["src"],bus="fclk_out_"+pr["src"]["bus"]),
            dst=dict(part=r["dst"],bus="fclk_in_"+pr["dst"]["bus"]),width=1,kind="clock",epoch=False))
        for kind in ("ready","fault"):
            raw["ports"].append(dict(id=f"cland_mon_{kind}__{r['port']}",src=dict(part=r["src"],bus=f"cland_up_{kind}_{pr['src']['bus']}"),
                dst=dict(part=r["dst"],bus=f"cland_dn_{kind}_{pr['dst']['bus']}"),width=1,kind="ctl",epoch=False))
        tn=P.parts[r["src"]]["type"]
        monitor_edges.append(dict(port=r["port"],src=r["src"],dst=r["dst"],seam=True,
            carries="aggregate" if pr["src"]["bus"]==tree_bus[tn] and parent[r["src"]]==r["dst"] else "local",
            data_cycles_added=0,boot_transport_extra_cycles=3))
    # boot budget: rings train in parallel (21); an aggregate input arrives after its source's aggregate + ring (3);
    # a local-only input after the source's local ready; then the receiver's registered depth.
    loc={pn:W["max_release"]+21+bytype[P.parts[pn]["type"]]["local_registered_depth"] for pn in P.parts};agg={}
    for pn in sorted(P.parts,key=lambda n:-dist[n]):
        d=bytype[P.parts[pn]["type"]]["local_registered_depth"]
        arr=[W["max_release"]+21]
        for e in monitor_edges:
            if e["dst"]==pn:arr.append((agg[e["src"]] if e["carries"]=="aggregate" else loc[e["src"]])+3)
        agg[pn]=max(arr)+d
    side=copy.deepcopy(table);side["added_cycles_per_crossing"]=3
    side["collector"]=dict(root=observer_part,monitor="dataflow",observer=dict(part=observer_part,**({k:observer[k] for k in ("module","instance_suffix","fault_port","ready_port")}
            if observer else dict(module="OPEN",instance_suffix="OPEN",fault_port="OPEN",ready_port="OPEN"))),
        parts={pn:dict(type=P.parts[pn]["type"],parent=parent[pn],active=True,potential=dist[pn]) for pn in P.parts},
        types=bytype,edges=monitor_edges,base_type_by_part=base_type,tree_bus=tree_bus,
        reset_max_release=W["max_release"],max_die_hop_um=0,placement_failures=placement_failures,physical_qualified=False,
        start_contract="START waits for registered root ready; root fault is observed; raw-reset ring training beforeSTART",
        boot_budget=dict(raw_reset_release_max_cycles=W["max_release"],ring_train_max_cycles=21,
            ready_at_glue_max_cycles=agg[observer_part],observer_input_capture_cycles=1,
            contract="Cycles after external reset release, clocks running continuously; START is also gated by actual registered ready, never this budget alone.",
            physical_clock_phase_qualified=False,data_cycles_added=0))
    return _finish(raw,P,bytype,pports,side)


def compose(plan,table,plan_path=None,observer_part="glue",observer=None,monitor="reset"):
    """observer: {module, instance_suffix, fault_port, ready_port} of the real
    one-bit fault/ready inputs gated in observer_part (reset mode default QC_OBSERVER).
    monitor="dataflow" (opt-in, FALLBACK-HEAD): observer None stays OPEN (fails closed at bind)."""
    if monitor not in ("reset","dataflow"):raise ValueError(f"unknown monitor mode {monitor}")
    if observer is not None or monitor=="reset":
        observer=dict(QC_OBSERVER if observer is None else observer)
        missing=[k for k in ("module","instance_suffix","fault_port","ready_port") if not observer.get(k)]
        if missing:raise ValueError(f"clock landing observer spec missing {missing}")
    original=copy.deepcopy(plan);raw=copy.deepcopy(plan)
    _fill_ft_windows(raw,plan_path)
    _fill_port_windows(raw,plan_path,table)
    base_type={p["name"]:p["type"] for p in raw["partitions"]}
    req=CL.requirements(raw,table)
    pports={p["id"]:p for p in raw["ports"]}
    ins=defaultdict(dict);outs=defaultdict(set)
    for r in table["ports"]:
        pr=pports[r["port"]]
        ins[r["dst"]][pr["dst"]["bus"]]=dict(r,src_bus=pr["src"]["bus"],dst_bus=pr["dst"]["bus"])
        outs[r["src"]].add(pr["src"]["bus"])
    region={}
    for p in raw["partitions"]:
        t=raw["partition_types"][p["type"]];x,y=p["origin_um"];w,h=t["outline_um"]
        rs=[r["tag"] for r in table["regions"] if r["box_um"][0]<=x+w/2<r["box_um"][2] and r["box_um"][1]<=y+h/2<r["box_um"][3]]
        if len(rs)!=1:raise ValueError(f"part{p['name']} has no unique whole clock region")
        region[p["name"]]=rs[0]
    if monitor=="dataflow":     # opt-in (FALLBACK-HEAD): uniform per-type monitor on the data crossings, no cohort split
        return _compose_dataflow(raw,plan_path,table,pports,ins,outs,region,base_type,observer_part,observer)
    # Pin the existing reset-entry choices before splitting replicated types.
    # Parent/child graph can refine after OUT-site cohorts shrink, so repeat the
    # exact active-child hardware partition until no further type splits occur.
    P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
    raw.setdefault("reset",{}).setdefault("in_sites",{}).update({tn:t["in_um"] for tn,t in W["types"].items() if "in_um" in t})
    def hard_xy(pn):
        # Hard partition: the ring lands at the digital edge (soft wrapper,
        # received window); the monitor leaves at the delivered-reset entry.
        if not ins[pn]:raise ValueError(f"hard partition {pn} is active without a local landing")
        return _reset_entry_xy(W,raw,P.parts[pn]["type"])
    for _ in range(len(raw["partitions"])+1):
        P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
        monitor_parent=_collector_graph(P,W,observer_part)
        active={pn for pn, bs in ins.items() if bs}
        for pn in list(active):
            q=pn
            while monitor_parent[q] is not None:
                q=monitor_parent[q];active.add(q)
        children=defaultdict(list)
        for pn in sorted(active):
            par=monitor_parent[pn]
            if par is not None:
                end=_monitor_endpoints(P,W,pn,par,hard_xy)
                children[par].append(dict(part=pn,node=end["dst_node"],xy_um=end["dst_xy"],seam=region[pn]!=region[par]))
        signatures={}
        for pn,p in P.parts.items():
            ch=sorted(children[pn],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
            up=_monitor_endpoints(P,W,pn,monitor_parent[pn],hard_xy) if pn in active and monitor_parent[pn] is not None else None
            signatures[pn]=dict(inputs=sorted(ins[pn]),outputs=sorted(outs[pn]),active=pn in active,observer=pn==observer_part,
                up_xy=up["src_xy"] if up else None,
                up_seam=pn in active and monitor_parent[pn] is not None and region[pn]!=region[monitor_parent[pn]],
                children=[dict(xy_um=c["xy_um"],seam=c["seam"]) for c in ch])
        groups=defaultdict(lambda:defaultdict(list))
        for pn,p in P.parts.items():groups[p["type"]][json.dumps(signatures[pn],sort_keys=True)].append(pn)
        split=False
        for tn,cohorts in groups.items():
            if len(cohorts)==1:continue
            split=True;old=raw["partition_types"].pop(tn)
            for sig,names in cohorts.items():
                base=base_type[names[0]];name=base+"__cl"+hashlib.sha256((tn+sig).encode()).hexdigest()[:8]
                clone=copy.deepcopy(old);clone["module"]=name;clone["landing_base_type"]=base
                clone["note"]=clone.get("note","")+f";clock landing cohort from{base} (exact local monitor children)"
                raw["partition_types"][name]=clone
                if "in_um" in W["types"].get(tn,{}):raw["reset"]["in_sites"][name]=W["types"][tn]["in_um"]
                for p in raw["partitions"]:
                    if p["name"] in names:p["type"]=name
        if not split:break
    else:raise ValueError("clock landing cohort refinement did not terminate")
    # Final topology is the topology the new wrappers and ports actually use.
    P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
    bytype={};placement_failures=[];monitor_edges=[]
    for tn,t in raw["partition_types"].items():
        pn=next(pn for pn,p in P.parts.items() if p["type"]==tn)
        sig=signatures[pn];hard=bool(t.get("hard"))
        if hard and children[pn]:raise ValueError(f"hard partition type {tn} would collect monitor children")
        # Hard partitions carry no generated reset tree: the landing ring and
        # its one collector live in the soft wrapper on the delivered reset
        # (the same reset the wrapper's own ft stations use).
        if pn in active and hard:
            if len(ins[pn])!=1:raise ValueError(f"hard partition {pn}: exactly one landing per hard wrapper supported, got {sorted(ins[pn])}")
            tree=_hard_tree(hard_xy(pn),_bus_xy(t,next(iter(ins[pn]))))
        else:tree=RT.for_type(P,tn) if pn in active else None
        info=dict(base_type=base_type[pn],mask=sig,tree=tree,local_sources=[],children=[],up_parent=monitor_parent[pn] if pn in active else None,
                  reset_entry_um=W["types"].get(tn,{}).get("in_um"),bands={},bus_geometry=copy.deepcopy(t.get("_cland_geom",{})))
        used=[]
        for bus,r in sorted(ins[pn].items()):
            point=_bus_xy(t,bus)
            if hard:tap=None
            else:
                tapxy={int(r["q"].split("rst_n_t")[1]):r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
                tap=min(range(tree["n_clock_taps"]),key=lambda i:abs(tapxy[i][0]-point[0])+abs(tapxy[i][1]-point[1]))
            try:band=_storage_band(t,bus,int(r["width"]),used);used.append(band["rect_um"])
            except ValueError as e:
                placement_failures.append(dict(type=tn,bus=bus,error=str(e)));band=dict(placement="FAIL",rect_um=None)
            band["instance"]="u_cland_"+bus
            info["bands"][bus]=band
            status=None
            if not hard and band.get("rect_um") and abs(tapxy[tap][0]-point[0])+abs(tapxy[tap][1]-point[1])>405:
                # The ring's ready/fault flops sit in its band, not at the pin.
                # Only when the pin is beyond reach of every tap (QC never is)
                # the collector tap is chosen from the band centre instead.
                x0,y0,x1,y1=band["rect_um"];status=[round((x0+x1)/2,3),round((y0+y1)/2,3)]
                tap=min(range(tree["n_clock_taps"]),key=lambda i:abs(tapxy[i][0]-status[0])+abs(tapxy[i][1]-status[1]))
            info["local_sources"].append(dict(name=bus,ready="landing_ready_"+bus,fault="landing_fault_"+bus,tap=tap,
                xy_um=status or point,pin_xy_um=point,band=band,**(dict(node=tree["leaf_node"],reset="delivered") if hard else {})))
            b=_scalar(t,"fclk_in_"+bus,"in",point,"clock");t.setdefault("buses",[]).append(b)
            t.setdefault("clock",{}).setdefault("edge_clocks",[]).append(dict(port=b["name"],tap_um=point,period_mult=1,
                note="source-forwarded ring write clock; actual source-export/window STA required"))
        for bus in sorted(outs[pn]):t.setdefault("buses",[]).append(_scalar(t,"fclk_out_"+bus,"out",_bus_xy(t,bus),"clock"))
        if pn in active:
            if monitor_parent[pn] is None and hard:raise ValueError(f"hard partition {pn} cannot be the monitor root")
            if monitor_parent[pn] is None:
                tap=RT.leaf_tap(P,tn);node=f"rst_n_t{tap}"
                point=next(r["xy"] for r in tree["relays"] if r["q"]==node)
            else:
                end=_monitor_endpoints(P,W,pn,monitor_parent[pn],hard_xy);node=end["src_node"];point=end["src_xy"]
                for j,kind in enumerate(("ready","fault")):
                    t.setdefault("buses",[]).append(_scalar(t,"cland_up_"+kind,"out",point,"ctl",shift=2.16*(j+2)))
                if sig["up_seam"]:t.setdefault("buses",[]).append(_scalar(t,"fclk_out_cland_up","out",point,"clock",shift=2.16))
            info.update(collector_root_node=node,collector_root_xy=point)
            ch=sorted(children[pn],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
            for i,c in enumerate(ch):
                row=dict(c,index=i,ready=f"cland_dn_ready_{i}",fault=f"cland_dn_fault_{i}")
                for j,kind in enumerate(("ready","fault")):
                    t.setdefault("buses",[]).append(_scalar(t,f"cland_dn_{kind}_{i}","in",c["xy_um"],"ctl",shift=2.16*(j+2)))
                if c["seam"]:
                    b=_scalar(t,f"fclk_in_cland_dn_{i}","in",c["xy_um"],"clock",shift=2.16)
                    t.setdefault("buses",[]).append(b);t["clock"].setdefault("edge_clocks",[]).append(dict(port=b["name"],tap_um=c["xy_um"],period_mult=1,
                        note="reverse monitor forwarded clock; 2bit landed ring, boot-only cost"))
                if c["seam"]:
                    monbus=f"cland_dn_ready_{i}"
                    try:band=_storage_band(t,monbus,2,used,has_epoch=False);used.append(band["rect_um"])
                    except ValueError as e:
                        placement_failures.append(dict(type=tn,bus=monbus,error=str(e)));band=dict(placement="FAIL",rect_um=None)
                    band["instance"]=f"u_cland_monitor_{i}"
                    info["bands"][f"monitor_{i}"]=band
                info["children"].append(row)
        bytype[tn]=info
    # Separate physical transport: clock and monitor ports never carry epochs.
    for r in table["ports"]:
        pr=pports[r["port"]]
        raw["ports"].append(dict(id="cland_clk__"+r["port"],src=dict(part=r["src"],bus="fclk_out_"+pr["src"]["bus"]),
            dst=dict(part=r["dst"],bus="fclk_in_"+pr["dst"]["bus"]),width=1,kind="clock",epoch=False))
    for pn in sorted(active):
        par=monitor_parent[pn]
        if par is None:continue
        ch=sorted(children[par],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
        i=next(i for i,c in enumerate(ch) if c["part"]==pn)
        for kind in ("ready","fault"):
            raw["ports"].append(dict(id=f"cland_mon_{kind}__{pn}",src=dict(part=pn,bus="cland_up_"+kind),
                dst=dict(part=par,bus=f"cland_dn_{kind}_{i}"),width=1,kind="ctl",epoch=False))
        seam=region[pn]!=region[par]
        if seam:raw["ports"].append(dict(id="cland_mon_clk__"+pn,src=dict(part=pn,bus="fclk_out_cland_up"),
            dst=dict(part=par,bus=f"fclk_in_cland_dn_{i}"),width=1,kind="clock",epoch=False))
        end=_monitor_endpoints(P,W,pn,par,hard_xy);a=P.to_die(pn,end["src_xy"]);b=P.to_die(par,end["dst_xy"])
        monitor_edges.append(dict(src=pn,dst=par,dst_index=i,seam=seam,hop_um=abs(a[0]-b[0])+abs(a[1]-b[1]),
            data_cycles_added=0,boot_transport_extra_cycles=3 if seam else 0))
    root=observer_part
    side=copy.deepcopy(table);side["added_cycles_per_crossing"]=3
    side["collector"]=dict(root=root,observer=dict(part=root,**{k:observer[k] for k in ("module","instance_suffix","fault_port","ready_port")}),
        parts={pn:dict(type=P.parts[pn]["type"],parent=monitor_parent[pn],active=pn in active)
        for pn in P.parts},types=bytype,edges=monitor_edges,base_type_by_part=base_type,
        reset_max_release=W["max_release"],max_die_hop_um=max([e["hop_um"] for e in monitor_edges]or[0]),
        placement_failures=placement_failures,physical_qualified=False,
        start_contract="START waits for registered root ready; root fault is observed; raw-reset ring training beforeSTART")
    # Conservative deterministic boot budget from the actual rerooted graph.
    # All local rings train in parallel; charging another full training budget
    # at each region seam also covers a late upstream ready transition.
    deadlines={};local_depths={}
    for pn in sorted(active):
        inf=bytype[P.parts[pn]["type"]];tree=inf["tree"];rootnode=inf["collector_root_node"]
        if tree.get("hard"):local_depths[pn]=len(tree["relays"])+1;continue
        adj=defaultdict(list)
        for r in tree["relays"]:adj[r["q"]].append(r["d"]);adj[r["d"]].append(r["q"])
        distances={rootnode:0};todo=[rootnode]
        while todo:
            n=todo.pop()
            for q in adj[n]:
                if q not in distances:distances[q]=distances[n]+1;todo.append(q)
        nodes=[f"rst_n_t{s['tap']}" for s in inf["local_sources"]]+[c["node"] for c in inf["children"]]
        local_depths[pn]=max([distances[n]+1 for n in nodes]or[0])
    def deadline(pn):
        if pn in deadlines:return deadlines[pn]
        child=[deadline(c["part"])+(21 if c["seam"] else 0) for c in children[pn]]
        deadlines[pn]=max([W["max_release"]+21]+child)+local_depths[pn]
        return deadlines[pn]
    side["collector"]["boot_budget"]=dict(raw_reset_release_max_cycles=W["max_release"],
        ring_train_max_cycles=21,local_registered_depths=local_depths,
        ready_at_glue_max_cycles=deadline(root),observer_input_capture_cycles=1,
        contract="Cycles after external reset release, clocks running continuously; START is also gated by actual registered ready, never this budget alone.",
        physical_clock_phase_qualified=False,data_cycles_added=0)
    return _finish(raw,P,bytype,pports,side)



def _finish(raw,P,bytype,pports,side):
    # These are clock/reset-adjacent infrastructure pins, like existing tap
    # and wavefront pins. They are NOT ordinary aligned functional bus ports
    # and do not create fictitious R8 lanes. Keep exact physical endpoint and
    # registered-hop contracts in the infrastructure model instead.
    import gen_phys as GP
    for tn,t in raw["partition_types"].items():
        special=[b for b in t.get("buses",[]) if b["name"].startswith(("fclk_","cland_"))]
        pins=[];w,h=t["outline_um"]
        for b in special:
            at=sum(b["window_um"])/2;f=b["face"]
            point=([2.16 if f=="W" else w-2.16,at] if f in "EW" else [at,2.16 if f=="S" else h-2.16])
            point=list(GP._snap_tap(P,*point))
            pin=dict(name=b["name"],dir=b["dir"],kind=b["kind"],layer=P.layer_budget["partition_signal_max"],
                     xy_um=point,epoch=False)
            if pin["kind"]=="clock" and pin["dir"]=="in":
                ec=next(e for e in t["clock"]["edge_clocks"] if e["port"]==b["name"])
                ec["tap_um"]=point
            if pin["kind"]=="clock" and pin["dir"]=="out":
                roots=GP.clock_pins(P,tn)
                if not roots:raise ValueError(f"{tn}: no normal clock tap to forward")
                pin["source_clock_port"]=min(roots,key=lambda r:abs(r[1]-point[0])+abs(r[2]-point[1]))[0]
            pins.append(pin)
        if pins:
            t["clock"]["landing_contract"]=dict(pins=pins,bands=bytype[tn]["bands"],
                base_type=bytype[tn]["base_type"],registered_monitor=bytype[tn]["mask"]["active"],
                physical_qualified=False,collector_tree=bytype[tn]["tree"],
                collector_root_node=bytype[tn].get("collector_root_node"),
                collector_local_sources=bytype[tn]["local_sources"],
                collector_children=bytype[tn]["children"],
                **({"monitor":"dataflow"} if bytype[tn]["mask"].get("monitor")=="dataflow" else {}))
        t["buses"]=[b for b in t.get("buses",[]) if b not in special]
    infra_edges=[]
    for pr in raw["ports"]:
        if pr["id"] in pports:continue
        if S.DIE_PART in (pr["src"]["part"],pr["dst"]["part"]):continue
        infra_edges.append(dict(id=pr["id"],src=pr["src"],dst=pr["dst"],kind=pr["kind"],width=1,
            epoch=False,max_hop_um=405,source_registered=pr["kind"]=="ctl",capture_registered=pr["kind"]=="ctl"))
    raw["ports"]=[pr for pr in raw["ports"] if pr["id"] in pports]
    raw["clock"]["landing_network"]=dict(edges=infra_edges,root_observer=side["collector"]["observer"],
        data_cycles_per_crossing=3,physical_qualified=False)
    for t in raw["partition_types"].values():t.pop("_cland_geom",None)
    return raw,side
