#!/usr/bin/env python3
"""Plan one local START clock entry buffer per actual virtual-stage FF group.

A real group replaces an unloaded measurement tap with several FF clock caps.
The local buffer isolates that load from the neighbour-forwarded clock trunk;
its geometry/load are fixed before build and its insertion is measured, never
trimmed. No clock domain, FF or explicit pipeline cycle is added.
"""
import argparse,copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S,die_trial as D,start_stage_emit as E
MASTER='BUFx8_ASAP7_75t_R'

import re
from collections import defaultdict
import math


class Bodies:
    def __init__(self, height=.27, bucket=2.0):
        self.height=height
        self.bucket=bucket
        self.bins=defaultdict(list)
        self.next_id=0

    def keys(self,x0,x1,y):
        for i in range(math.floor(x0/self.bucket),math.floor(x1/self.bucket)+1):
            for j in range(math.floor(y/self.bucket),math.floor((y+self.height)/self.bucket)+1):
                yield i,j

    def add(self,x0,x1,y):
        entry=(self.next_id,x0,x1,y,y+self.height)
        self.next_id+=1
        for key in self.keys(x0,x1,y):self.bins[key].append(entry)

    def free(self,x0,x1,y):
        seen=set()
        for key in self.keys(x0,x1,y):
            for ident,a,b,c,d in self.bins.get(key,()):
                if ident in seen:continue
                seen.add(ident)
                if min(x1,b)>max(x0,a)+1e-6 and min(y+self.height,d)>max(y,c)+1e-6:return False
        return True


def row_orientation(y, origin=0.0, height=.27):
    row=round((y-origin)/height)
    if abs(origin+row*height-y)>1e-6:
        raise ValueError(f'cell y={y} is not on native0.27um row phase')
    return 'MX' if row%2 else 'R0'

def lef_sizes(text):
    out = {}
    for m in re.finditer(r'\bMACRO\s+(\S+)(.*?)(?=\bEND\s+\1\b)', text, re.S):
        size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', m[2])
        if size:
            out[m[1]] = tuple(map(float, size.groups()))
    return out



def add(physical,stages,plan,ctree_v,ctree_tcl,sizes,master=MASTER):
    ph=copy.deepcopy(physical)
    if ph.get('stage_clock_drivers'):raise ValueError('local clock drivers already present')
    rows=Bodies();site=D.SiteMap(plan);W,H=plan.die['outline_um'];w,h=sizes[master]
    if h > E.ROW_UM + 1e-6:
        raise ValueError('local clock entry requires a single-row master')
    for c in ph['cells'].values():
        x,y=c['xy_um'];cw,ch=sizes[c['cell']];rows.add(x,x+cw,y)
    cells,xy=E.ctree_cells(ctree_v,ctree_tcl)
    for n,(clock_master,_,_) in cells.items():x,y=xy[n];rows.add(x,x+sizes[clock_master][0],y)
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
        # DIE-HEAD-29 (FLOW-CLOCK-R / COORD 10-29 10:01): two stages naming one clock_port silently replaced the
        # first driver (its flops lost their isolation buffer); fail closed instead.
        if s['clock_port'] in drivers:
            raise ValueError('duplicate local clock port '+s['clock_port']+': stages '+drivers[s['clock_port']]['stage']+' and '+s['id'])
        drivers[s['clock_port']]=dict(cell=master,inst='start_clock_'+s['id'],stage=s['id'],xy_um=[x,y],rect_um=[x,y,round(x+w,3),round(y+h,3)],orient=row_orientation(y),flop_loads=s['flops'],logical_cycles_added=0)
    ph['stage_clock_drivers']=drivers
    ph['clock_driver_scope']='universal prebuild FF clock-load isolation; measured phase/insertion required'
    return ph


def add_arguments(p):
    for n in ('physical','stages','plan','ctree','lef','out'):p.add_argument('--'+n,required=True)
    p.add_argument('--cell', default=MASTER, help='native single-row clock-entry buffer master')


def run(a):
    o=Path(a.out)
    if o.exists():raise ValueError('preserve existing local clock-buffer plan')
    ph=add(json.load(open(a.physical)),json.load(open(a.stages)),S.Plan(json.load(open(a.plan)),Path(a.plan)),(Path(a.ctree)/'ctree.v').read_text(),(Path(a.ctree)/'ctree.tcl').read_text(),lef_sizes(Path(a.lef).read_text()),a.cell)
    o.write_text(json.dumps(ph,indent=1));print(json.dumps(dict(local_clock_buffers=len(ph['stage_clock_drivers']),source=a.cell,flops_added=0,explicit_cycles_added=0)))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);add_arguments(p);run(p.parse_args())
