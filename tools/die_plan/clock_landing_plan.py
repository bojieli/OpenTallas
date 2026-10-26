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


def _bus_geom(t, bus):
    for b in t.get("buses",[]):
        if b["name"] == bus:
            return b
    for s in t.get("ft_slots",[]):
        for suffix,face,window in (("_i","in_face","in_window_um"),("_o","out_face","out_window_um")):
            if s["name"]+suffix == bus:
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
        next(s for s in raw["partition_types"][tn]["ft_slots"] if s["name"]==name)[wk]=vals[0]


def _storage_band(t,bus,width,used):
    b=_bus_geom(t,bus);w,h=t["outline_um"];lo,hi=b["window_um"]
    length=max(hi-lo,8.64);rw=64*((width+64)//64)
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
    candidates=[]
    for inset in [margin+2.16*k for k in range(88)]:
        f=b["face"]
        box=([inset,lo,inset+depth,hi] if f=="W" else
             [w-inset-depth,lo,w-inset,hi] if f=="E" else
             [lo,inset,hi,inset+depth] if f=="S" else [lo,h-inset-depth,hi,h-inset])
        if box[0]<margin or box[1]<margin or box[2]>w-margin or box[3]>h-margin:continue
        if any(min(box[2],o[2])>max(box[0],o[0])+1e-6 and min(box[3],o[3])>max(box[1],o[1])+1e-6 for o in obstacles):continue
        candidates.append(box)
    # A dense face may have no full-height strip beside a macro. A compact
    # bank in the adjoining macro-free row is valid when EVERY storage point
    # stays within405um of the original bus pin. Consider both bank aspects;
    # do not move the pin or add an unpriced relay stage.
    px,py=_bus_xy(t,bus)
    for bw,bh in ((depth,length),(length,depth)):
        xs={margin,w-bw-margin,max(margin,min(w-bw-margin,px-bw/2))}
        ys={margin,h-bh-margin,max(margin,min(h-bh-margin,py-bh/2))}
        for o in obstacles:
            xs.update((o[0]-bw-2.16,o[2]+2.16));ys.update((o[1]-bh-2.16,o[3]+2.16))
        for x0 in xs:
            for y0 in ys:
                box=[x0,y0,x0+bw,y0+bh]
                if x0<margin or y0<margin or box[2]>w-margin or box[3]>h-margin:continue
                if max(abs(x-px)+abs(y-py) for x in(box[0],box[2]) for y in(box[1],box[3]))>405-2.16:continue
                if any(min(box[2],o[2])>max(box[0],o[0])+1e-6 and min(box[3],o[3])>max(box[1],o[1])+1e-6 for o in obstacles):continue
                candidates.append(box)
    if candidates:
        box=min(candidates,key=lambda b:max(abs(x-px)+abs(y-py) for x in(b[0],b[2]) for y in(b[1],b[3])))
        return dict(rect_um=[round(x,6) for x in box],width=width,ring_width=rw,
                    live_data_storage_flops=5*(width+1),padded_data_storage_flops=5*rw,
                    clock_roles=dict(forwarded_write_flops=4*rw,local_read_flops=rw),
                    max_pin_to_band_hop_um=round(max(abs(x-px)+abs(y-py) for x in(box[0],box[2]) for y in(box[1],box[3])),3),
                    area_reserve_um2=round(area,3),placement="PROPOSED legal macro-free band; mapped anchoring pending")
    raise ValueError(f"no macro-free clock landing storage band for{bus}, required depth{depth:.2f}um")


def compose(plan,table,plan_path=None):
    original=copy.deepcopy(plan);raw=copy.deepcopy(plan)
    _fill_ft_windows(raw,plan_path)
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
    # Pin the existing reset-entry choices before splitting replicated types.
    # Parent/child graph can refine after OUT-site cohorts shrink, so repeat the
    # exact active-child hardware partition until no further type splits occur.
    P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
    raw.setdefault("reset",{}).setdefault("in_sites",{}).update({tn:t["in_um"] for tn,t in W["types"].items()})
    for _ in range(len(raw["partitions"])+1):
        P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
        active={pn for pn, bs in ins.items() if bs}
        for pn in list(active):
            q=pn
            while W["parts"][q]["parent"] is not None:
                q=W["parts"][q]["parent"];active.add(q)
        children=defaultdict(list)
        for pn in sorted(active):
            row=W["parts"][pn];par=row["parent"]
            if par is not None:
                k=int(row["source"].rsplit("_",1)[1]);xy=W["types"][P.parts[par]["type"]]["outs"][k][1:]
                children[par].append(dict(part=pn,reset_out=k,xy_um=xy,seam=region[pn]!=region[par]))
        signatures={}
        for pn,p in P.parts.items():
            ch=sorted(children[pn],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
            signatures[pn]=dict(inputs=sorted(ins[pn]),outputs=sorted(outs[pn]),active=pn in active,
                up_seam=pn in active and W["parts"][pn]["parent"] is not None and region[pn]!=region[W["parts"][pn]["parent"]],
                children=[dict(xy_um=c["xy_um"],seam=c["seam"]) for c in ch])
        groups=defaultdict(lambda:defaultdict(list))
        for pn,p in P.parts.items():groups[p["type"]][json.dumps(signatures[pn],sort_keys=True)].append(pn)
        split=False
        for tn,cohorts in groups.items():
            if len(cohorts)==1:continue
            split=True;old=raw["partition_types"].pop(tn)
            for sig,names in cohorts.items():
                base=base_type[names[0]];name=base+"__cl"+hashlib.sha256((tn+sig).encode()).hexdigest()[:8]
                clone=copy.deepcopy(old);clone["module"]=name
                clone["note"]=clone.get("note","")+f";clock landing cohort from{base} (exact local monitor children)"
                raw["partition_types"][name]=clone
                raw["reset"]["in_sites"][name]=W["types"][tn]["in_um"]
                for p in raw["partitions"]:
                    if p["name"] in names:p["type"]=name
        if not split:break
    else:raise ValueError("clock landing cohort refinement did not terminate")
    # Final topology is the topology the new wrappers and ports actually use.
    P=S.Plan(raw,plan_path);W=RT.wf_plan(P)
    bytype={};placement_failures=[];monitor_edges=[]
    for tn,t in raw["partition_types"].items():
        pn=next(pn for pn,p in P.parts.items() if p["type"]==tn)
        sig=signatures[pn];tree=RT.for_type(P,tn) if pn in active else None
        info=dict(base_type=base_type[pn],mask=sig,tree=tree,local_sources=[],children=[],up_parent=W["parts"][pn]["parent"] if pn in active else None,
                  reset_entry_um=W["types"].get(tn,{}).get("in_um"),bands={})
        used=[]
        for bus,r in sorted(ins[pn].items()):
            point=_bus_xy(t,bus)
            tapxy={int(r["q"].split("rst_n_t")[1]):r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
            tap=min(range(tree["n_clock_taps"]),key=lambda i:abs(tapxy[i][0]-point[0])+abs(tapxy[i][1]-point[1]))
            try:band=_storage_band(t,bus,int(r["width"]),used);used.append(band["rect_um"])
            except ValueError as e:
                placement_failures.append(dict(type=tn,bus=bus,error=str(e)));band=dict(placement="FAIL",rect_um=None)
            info["bands"][bus]=band
            info["local_sources"].append(dict(name=bus,ready="landing_ready_"+bus,fault="landing_fault_"+bus,tap=tap,
                xy_um=point,band=band))
            b=_scalar(t,"fclk_in_"+bus,"in",point,"clock");t["buses"].append(b)
            t.setdefault("clock",{}).setdefault("edge_clocks",[]).append(dict(port=b["name"],tap_um=point,period_mult=1,
                note="source-forwarded ring write clock; actual source-export/window STA required"))
        for bus in sorted(outs[pn]):t["buses"].append(_scalar(t,"fclk_out_"+bus,"out",_bus_xy(t,bus),"clock"))
        if pn in active:
            point=W["types"][tn]["in_um"]
            for j,kind in enumerate(("ready","fault")):
                t["buses"].append(_scalar(t,"cland_up_"+kind,"out",point,"ctl",shift=2.16*(j+2)))
            if sig["up_seam"]:t["buses"].append(_scalar(t,"fclk_out_cland_up","out",point,"clock",shift=2.16))
            ch=sorted(children[pn],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
            for i,c in enumerate(ch):
                row=dict(c,index=i,tap=tree["n_clock_taps"]+c["reset_out"],ready=f"cland_dn_ready_{i}",fault=f"cland_dn_fault_{i}")
                for j,kind in enumerate(("ready","fault")):
                    t["buses"].append(_scalar(t,f"cland_dn_{kind}_{i}","in",c["xy_um"],"ctl",shift=2.16*(j+2)))
                if c["seam"]:
                    b=_scalar(t,f"fclk_in_cland_dn_{i}","in",c["xy_um"],"clock",shift=2.16)
                    t["buses"].append(b);t["clock"].setdefault("edge_clocks",[]).append(dict(port=b["name"],tap_um=c["xy_um"],period_mult=1,
                        note="reverse monitor forwarded clock; 2bit landed ring, boot-only cost"))
                info["children"].append(row)
        bytype[tn]=info
    # Separate physical transport: clock and monitor ports never carry epochs.
    for r in table["ports"]:
        pr=pports[r["port"]]
        raw["ports"].append(dict(id="cland_clk__"+r["port"],src=dict(part=r["src"],bus="fclk_out_"+pr["src"]["bus"]),
            dst=dict(part=r["dst"],bus="fclk_in_"+pr["dst"]["bus"]),width=1,kind="clock",epoch=False))
    for pn in sorted(active):
        par=W["parts"][pn]["parent"]
        if par is None:continue
        ch=sorted(children[par],key=lambda c:(c["xy_um"],c["seam"],c["part"]))
        i=next(i for i,c in enumerate(ch) if c["part"]==pn)
        for kind in ("ready","fault"):
            raw["ports"].append(dict(id=f"cland_mon_{kind}__{pn}",src=dict(part=pn,bus="cland_up_"+kind),
                dst=dict(part=par,bus=f"cland_dn_{kind}_{i}"),width=1,kind="ctl",epoch=False))
        seam=region[pn]!=region[par]
        if seam:raw["ports"].append(dict(id="cland_mon_clk__"+pn,src=dict(part=pn,bus="fclk_out_cland_up"),
            dst=dict(part=par,bus=f"fclk_in_cland_dn_{i}"),width=1,kind="clock",epoch=False))
        monitor_edges.append(dict(src=pn,dst=par,dst_index=i,seam=seam,hop_um=W["parts"][pn]["hop_um"],
            data_cycles_added=0,boot_transport_extra_cycles=3 if seam else 0))
    root=W["root"]
    for kind in ("ready","fault"):
        raw["ports"].append(dict(id="cland_root_"+kind,src=dict(part=root,bus="cland_up_"+kind),
            dst=dict(part=S.DIE_PART,bus="clock_landing_"+kind),width=1,kind="ctl",epoch=False))
    side=copy.deepcopy(table);side["added_cycles_per_crossing"]=3
    side["collector"]=dict(root=root,parts={pn:dict(type=P.parts[pn]["type"],parent=W["parts"][pn]["parent"],active=pn in active)
        for pn in P.parts},types=bytype,edges=monitor_edges,base_type_by_part=base_type,
        reset_max_release=W["max_release"],max_die_hop_um=max([e["hop_um"] for e in monitor_edges]or[0]),
        placement_failures=placement_failures,physical_qualified=False,
        start_contract="START waits for registered root ready; root fault is observed; raw-reset ring training beforeSTART")
    return raw,side
