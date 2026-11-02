#!/usr/bin/env python3
"""Finite planning obstacle/contact check for a disabled r10 location.

Uses the established canonical body/probe union and existing4.32 STD clearance.
The8.64 contact guard is applied to existing clock contacts only.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
from ft_sites_unblock import placement_boxes
CELL=(1.404,.27)


def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-9 and min(a[3],b[3])>max(a[1],b[1])+1e-9

def expand(box,halo):return [box[0]-halo,box[1]-halo,box[2]+halo,box[3]+halo]

def pointbox(p):return [p[0]-CELL[0]/2,p[1]-CELL[1]/2,p[0]+CELL[0]/2,p[1]+CELL[1]/2]

def contact_distance(p,b):return max(b[0]-p[0],0,p[0]-b[2])+max(b[1]-p[1],0,p[1]-b[3])

def check(t,xy):
    x,y=xy;b=[x,y,x+574.56,y+738.72];grown=expand(b,4.32);obstacles=placement_boxes(t)
    body=[dict(name=n,box=list(q))for n,q in obstacles.items()if overlap(grown,list(q))]
    fts=[];nominal=[]
    for s in t.get('ft_slots',[]):
        for stage,bank in enumerate(s.get('bit_sites_um',[]),1):
            for bit,p in enumerate(bank):
                if overlap(grown,pointbox(p)):fts.append(dict(slot=s['name'],stage=stage,bit=bit,xy=p))
        for stage,p in enumerate(s.get('regs_um',[])):
            if overlap(grown,pointbox(p)):nominal.append(dict(kind='FT_nominal_not_actual_cell',slot=s['name'],stage=stage,xy=p))
    for s in t.get('internal_stations',[]):
        for stage,p in enumerate(s.get('regs_um',[])):
            if overlap(grown,pointbox(p)):nominal.append(dict(kind='internal_nominal_not_actual_cell',conn=s['conn'],stage=stage,xy=p))
    contacts=[]
    for q in t.get('clock',{}).get('taps',[]):
        p=q.get('xy',q.get('xy_um'));d=contact_distance(p,b)
        if d<8.64-1e-8:contacts.append(dict(name=q['name'],kind=q.get('kind'),xy=p,distance_to_new_body_um=round(d,6),minimum_clock_contact_clearance_um=8.64))
    inside=(x>=0 and y>=0 and b[2]<=t['outline_um'][0]and b[3]<=t['outline_um'][1])
    return dict(status='PASS_PLANNING_CONTACTS_ONLY'if inside and not(body or fts or nominal or contacts)else'FAIL',new_body_um=b,canonical_obstacle_count=len(obstacles),canonical_body_probe_overlaps=body,actual_FT_body_overlaps=fts,nominal_home_overlaps=nominal,existing_clock_contact_count=len(t.get('clock',{}).get('taps',[])),clock_contact_failures=contacts,inside_parent=inside,standard_cell_clearance_um=4.32,clock_contact_guard_um=8.64,physical_native_rows_source_clock_reset_PG='UNQUALIFIED; nominal homes are not placed cells, no physical provider compatibility assumed')


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--x',type=float,default=17.28);p.add_argument('--y',type=float,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());r=dict(plan=str(a.plan),plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),candidate_origin_um=[a.x,a.y],types={name:check(plan['partition_types'][name],[a.x,a.y])for name in ['q_b113','q_b113__physical_v1']},scope='Disabled programme placement planning; no P&R or current-plan mutation')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({name:{k:v for k,v in q.items()if k in ['status','canonical_obstacle_count','existing_clock_contact_count','clock_contact_failures']}for name,q in r['types'].items()}))
    return 0 if all(q['status']=='PASS_PLANNING_CONTACTS_ONLY'for q in r['types'].values())else 1

if __name__=='__main__':raise SystemExit(main())
