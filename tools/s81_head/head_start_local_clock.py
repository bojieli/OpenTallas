#!/usr/bin/env python3
"""Plan one local START clock entry buffer per actual virtual-stage FF group.

A real group replaces an unloaded measurement tap with several FF clock caps.
The local buffer isolates that load from the neighbour-forwarded clock trunk;
its geometry/load are fixed before build and its insertion is measured, never
trimmed. No clock domain, FF or explicit pipeline cycle is added.
"""
import argparse,copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools/s81_head'))
import schema as S,die_trial as D,start_stage_emit as E
from head_start_pack import lef_sizes
from head_start_sites import Bodies,row_orientation
MASTER='BUFx8_ASAP7_75t_R'


def add(physical,stages,plan,ctree_v,ctree_tcl,sizes):
    ph=copy.deepcopy(physical)
    if ph.get('stage_clock_drivers'):raise ValueError('local clock drivers already present')
    rows=Bodies();site=D.SiteMap(plan);W,H=plan.die['outline_um'];w,h=sizes[MASTER]
    for c in ph['cells'].values():
        x,y=c['xy_um'];cw,ch=sizes[c['cell']];rows.add(x,x+cw,y)
    cells,xy=E.ctree_cells(ctree_v,ctree_tcl)
    for n,(master,_,_) in cells.items():x,y=xy[n];rows.add(x,x+sizes[master][0],y)
    drivers={}
    for s in stages['stages']:
        rejected=Bodies()
        class Candidate:
            def free(self,x0,x1,y):return rows.free(x0,x1,y) and rejected.free(x0,x1,y)
        for trial in range(4*E.MAX_ROW_TRIES):
            r=E.place_stage(xy[s['node_cell']],math.ceil(w/E.FLOP_W_UM),Candidate(),site,W,H)
            x,y=r[:2]
            if all(site.legal((xx,yy)) for xx in (x,x+w/2,x+w) for yy in (y,y+h)):break
            rejected.add(r[0],r[2],y)
        else:raise ValueError('no complete local clock-buffer body for '+s['id'])
        rows.add(x,x+w,y)
        drivers[s['clock_port']]=dict(cell=MASTER,inst='start_clock_'+s['id'],stage=s['id'],xy_um=[x,y],rect_um=[x,y,round(x+w,3),round(y+h,3)],orient=row_orientation(y),flop_loads=s['flops'],logical_cycles_added=0)
    ph['stage_clock_drivers']=drivers
    ph['clock_driver_scope']='universal prebuild FF clock-load isolation; measured phase/insertion required'
    return ph


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('physical','stages','plan','ctree','lef','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();o=Path(a.out)
    if o.exists():raise ValueError('preserve existing local clock-buffer plan')
    ph=add(json.load(open(a.physical)),json.load(open(a.stages)),S.Plan(json.load(open(a.plan)),Path(a.plan)),(Path(a.ctree)/'ctree.v').read_text(),(Path(a.ctree)/'ctree.tcl').read_text(),lef_sizes(Path(a.lef).read_text()))
    o.write_text(json.dumps(ph,indent=1));print(json.dumps(dict(local_clock_buffers=len(ph['stage_clock_drivers']),source=MASTER,flops_added=0,explicit_cycles_added=0)))
if __name__=='__main__':main()
