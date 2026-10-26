#!/usr/bin/env python3
"""Candidate-only actual-bit graph screen for the S-DIE 4x2 capture grant.

Reused relays retain their measured LEF pins. New or rebuilt leaves carry an
explicit proposed pin table, never an inherited physical view. External die
seams, clock trees and routed congestion remain outside this local screen.
"""
import argparse
import json
import re
from pathlib import Path

from capture_split_census import census, ROOT
from gather_flatten_plan import lef_pins

WIDTH, HEIGHT = 1727.976, 561.576


def build(wide=False, assigned=None):
    graph = census()
    children = {}
    endpoint = {}
    for name, c in graph["children"].items():
        master = c["master"]
        group = re.search(r"g_t\[(\d+)\]", name)
        g = int(group[1]) if group else None
        measured = None
        if master.startswith("dsfd_rly_"):
            suffix = master.removeprefix("dsfd_rly_").lower()
            view = ROOT / f"physical/ref_tile/s81_rly_{suffix}/views/{master}/{master}.lef"
            size, measured = lef_pins(view)
        elif master.startswith("dsfd_capt_x8_data_"): size = (108,162) if wide else (123.12, 136.08)
        elif master == "dsfd_capt_g2_dualho": size = (118.8, 162)
        elif master == "dsfd_capt_ctl": size = (324, 86.4)
        elif master == "dsfd_capt_status_dual": size = (43.2, 86.4)
        elif master == "dsfd_capt_cd": size = (15.12, 15.12)
        elif master == "dsfd_capt_rly_31_EW": size = (15.12, 17.28)
        elif master == "dsfd_capt_rly_36_WE": size = (15.12, 17.28)
        elif master == "dsfd_capt_rly_64_EW": size = (17.28, 19.44)
        elif master == "dsfd_capt_rly_12_SN": size = (12.96, 12.96)
        else: raise ValueError(master)
        if g is not None:
            gx, gy = 15.108 + (439.92 if wide else 429.84) * (g // 2), 129.6 + 183.6 * (g % 2)
            if name.endswith("u_g"): at = (gx + (129.6 if wide else 144.72), gy)
            elif name.endswith("u_x0"): at = (gx, gy)
            elif name.endswith("u_x1"): at = (gx + (270 if wide else 285.12), gy)
            else:
                role = {"u_ka": 0, "u_kb": 1, "u_sb": 2}[name.rsplit(".", 1)[1]]
                index = role + (3 if g in (2, 3, 4, 5) else 0)
                x = 336.384 + 37.44 * index if g < 4 else WIDTH - 388.8 - 37.44 * index - size[0]
                if g == 7 and role == 2:
                    x = 1451.52  # far-NE fault relay: both actual legs stay below 500 um
                at = (round(x, 3), 21.6 + 39.96 * (g % 2))
                if wide and g in (1,7):
                    at=(414.72 if g==1 else 1294.272,207.36+37.44*role)
                elif wide and g in (3,5):
                    at=(at[0],90.0)
        else:
            at = {"u_ctl": (701.988, 21.6), "u_status": (598.308, 21.6), "u_sn": (663.108, 55.296),
                  "u_cd": (561.588, 21.6), "u_cr": (561.588, 501.12)}[name]
        pins = {}
        for port, bits in c["connections"].items():
            for i, bit in enumerate(bits):
                pin = f"{port}[{i}]" if len(bits) > 1 or port in graph["single_bit_bus_ports"][master] else port
                if measured is not None:
                    value = measured.get(pin) or measured.get(pin + "[0]")
                    if value is None: raise ValueError(f"missing actual {master}/{pin}")
                    layer, x, y = value
                else:
                    layer = "M5"
                    if master.startswith("dsfd_capt_x8_data_"):
                        if port == "f_w": layer, x, y = "M4", (size[0] if name.endswith("u_x0") else 0), 18 + (.288 if wide else .24)*i
                        elif port == "t_ho": layer, x, y = "M4", (size[0] if name.endswith("u_x0") else 0), (150 if wide else 120)
                        elif port == "t_vm": layer, x, y = ("M3" if i%2 else "M5"), 10 + (.192 if wide else .24)*(i//2), 0
                        else: x, y = (10 if port in ("ck", "ckv") else 14), (size[1] if port in ("ck", "rst") else 0)
                    elif master == "dsfd_capt_g2_dualho":
                        if port == "f_row": layer, x, y = ("M3" if i%2 else "M5"), 8+.24*(i//2), size[1]
                        elif port == "t_w": layer, x, y = "M4", (0 if i<416 else size[0]), 18+.288*(i%416)
                        elif port == "f_ho": layer, x, y = "M4", (0 if i==0 else size[0]), 150
                        elif port == "f_k": x,y=10+.96*i,0
                        elif port == "t_sb": x,y=110+2*i,0
                        else: x,y=(114 if port=="ck" else 116),size[1]
                    elif master == "dsfd_capt_ctl":
                        if port == "t_k":
                            index=(i//99)*99+(98-i%99) if wide and i//99==1 else i
                            x,y=10+.384*index,size[1]
                        elif port == "f_ctl": x,y=10+.96*i,0
                        elif port == "f_sb": layer,x,y="M4",(0 if i<8 else size[0]),76+1.152*(i%8)
                        elif port == "t_sn": layer,x,y="M4",0,10+.96*i
                        else: x,y=(300 if port=="ck" else 304),0
                    elif master == "dsfd_capt_status_dual":
                        if port in ("f_sn","t_st"): layer,x,y="M4",(size[0] if port=="f_sn" else 0),8+.96*i
                        else:x,y=(10 if port in ("ck","ckv") else 14),(size[1] if port in ("ck","rst") else 0)
                    elif master == "dsfd_capt_cd":
                        if port=="f_st":layer,x,y="M4",size[0],1.44+.864*i
                        elif port=="t_cd":x,y=1.44+.96*i,size[1]
                        else:x,y=(4 if port=="ckv" else 8),0
                    else:
                        if port in ("i","o"):
                            if master.endswith("SN"):x,y=1.44+.864*i,(0 if port=="i" else size[1])
                            else:
                                layer="M4"
                                x=size[0] if (master.endswith("EW")== (port=="i")) else 0
                                pitch=.24 if "_64_" in master else .384 if "_36_" in master else .432
                                y=1.44+pitch*i
                        elif master.endswith("SN"):layer,x,y="M4",0,(3 if port=="ck" else 6)
                        else:x,y=(3 if port=="ck" else 6),size[1]
                if assigned is not None and measured is None:
                    proposal=assigned["masters"][master]
                    if list(size)!=proposal["outline_um"] or proposal["orient"]!="R0":raise ValueError("assignment outline/orientation mismatch")
                    assigned_pin=proposal["pins"][pin]
                    layer=assigned_pin["layer"];x,y=assigned_pin["assigned_place_pin_location_um"]
                if not (-.001 <= x <= size[0]+.001 and -.001 <= y <= size[1]+.001):
                    raise ValueError(f"pin outside {name}/{pin}: {x},{y}")
                pins[pin] = dict(layer=layer, local_xy_um=[round(x,3),round(y,3)],
                                 xy_um=[round(at[0]+x,3),round(at[1]+y,3)],
                                 status="actual closed LEF" if measured else "assigned request, not exported contact" if assigned is not None else "proposed, not physical-qualified")
                endpoint[(name, pin)] = (bit,c["port_directions"][port],pins[pin]["xy_um"])
        children[name] = dict(master=master,at_um=at,outline_um=size,orient="R0",pins=pins,
                              reused_actual_pins=measured is not None)
    canonical = {}
    for name,c in children.items():
        table = {p:(d["layer"],round(c["outline_um"][0]-d["local_xy_um"][0],3) if c["orient"]=="MY" else d["local_xy_um"][0],d["local_xy_um"][1]) for p,d in c["pins"].items()}
        if c["master"] in canonical and canonical[c["master"]] != table:
            raise ValueError("same master has inconsistent transformed pins: "+name)
        canonical[c["master"]]=table
    entries=[]
    for parent_port,pv in graph["ports"].items():
        if not parent_port.startswith("ck"):continue
        for i,bit in enumerate(pv["bits"]):
            parent_pin=f"{parent_port}[{i}]" if len(pv["bits"])>1 else parent_port
            targets=[(n,p) for (n,p),(b,d,xy) in endpoint.items() if b==bit and d=="input"]
            if len(targets)!=1:raise ValueError("clock entry is not one actual leaf root")
            n,p=targets[0];entries.append(dict(parent_clock_pin=parent_pin,child=n,child_clock_pin=p,domain="serial" if parent_port.startswith("ckv") else "core",child_pin_request_xy_um=children[n]["pins"][p]["xy_um"],measured_R_ps=None,phi_minus_R_delivery="OPEN actual native view and routed tree required"))
    if len(entries)!=70:raise ValueError("capture clock count changed")
    drivers, sinks = {}, {}
    for (name,pin),(bit,direction,xy) in endpoint.items():
        (drivers if direction=="output" else sinks).setdefault(bit,[]).append(dict(pin=name+"/"+pin,xy_um=xy))
    paths=[]
    for bit, ds in drivers.items():
        if len(ds)!=1: raise ValueError("multiple drivers")
        for s in sinks.get(bit,[]):
            L=sum(abs(a-b) for a,b in zip(ds[0]["xy_um"],s["xy_um"]))
            paths.append(dict(driver=ds[0]["pin"],sink=s["pin"],manhattan_um=round(L,3)))
    paths.sort(key=lambda p:p["manhattan_um"],reverse=True)
    gap_fail=[]
    for n,a in children.items():
        ax,ay=a["at_um"];aw,ah=a["outline_um"]
        if ax<0 or ay<0 or ax+aw>WIDTH+.001 or ay+ah>HEIGHT+.001:raise ValueError("child outside "+n)
        for m,b in children.items():
            if n>=m:continue
            bx,by=b["at_um"];bw,bh=b["outline_um"]
            gap=max(bx-ax-aw,ax-bx-bw,by-ay-ah,ay-by-bh)
            if gap<20-1e-6:gap_fail.append(dict(a=n,b=m,gap_um=round(gap,3)))
    return dict(schema="opentallas.s81.capture_split_geometry_candidate.v1",adopted=False,physical_qualified=False,
                outline_um=[WIDTH,HEIGHT],wide_roads=wide,children=children,clock_entries=entries,
                assigned_pin_scope=assigned.get("scope") if assigned else None,
                summary=dict(children=len(children),hard_child_gaps_below20=len(gap_fail),
                             internal_bit_paths=len(paths),max_internal_manhattan_um=paths[0]["manhattan_um"],
                             internal_paths_over500=sum(p["manhattan_um"]>500 for p in paths)),
                gap_failures=gap_fail,internal_paths=paths,
                remaining="Actual die assigned tracks/PG/pin access, native child views, clock delivery, all incident die seams and measured congestion/cuts; planned pins are not LEF or timing evidence.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--wide",action="store_true")
    parser.add_argument("--assigned-pins",type=Path)
    args=parser.parse_args();out=build(args.wide,json.loads(args.assigned_pins.read_text()) if args.assigned_pins else None);args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out["summary"]))
