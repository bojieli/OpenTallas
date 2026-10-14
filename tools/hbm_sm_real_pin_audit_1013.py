#!/usr/bin/env python3
"""Diagnostic all-bit pin/cut audit of retained real SMH children.

Only exact source nets with two real hard-child endpoints are routed in this
lower-demand model. Parent and boundary endpoints are counted as missing physical
views and prevent admission. M6/M7 unobstructed capacity is an optimistic ceiling;
no PG credit, route proof or timing closure follows from passing this model.
"""
import argparse
import collections
import fnmatch
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as A


def pinmap(text):
    result={}
    for m in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n[ \t]*END \1[ \t]*(?=\n)',text,re.S):
        if re.search(r'USE (POWER|GROUND)',m[2]):continue
        r=re.search(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',m[2])
        if r:
            x,y,z,w=map(float,r.groups());result[m[1]]=[(x+z)/2,(y+w)/2]
    return result


def transform(row,xy):
    x,y=xy;w,h=row['size_um'];o=row['orient']
    if o in ('MY','R180'):x=w-x
    if o in ('MX','R180'):y=h-y
    return [x+row['at_um'][0],y+row['at_um'][1]]


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',required=True);p.add_argument('--geometry',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    work=Path(a.work); geom=json.load(open(a.geometry));result={}
    for variant in ('eg','wg'):
        module=json.load(open(work/(variant+'.json')))['modules']['ot_hbm_accel_smh_tile_'+variant]
        nodes=collections.defaultdict(list);rows=geom['variants'][variant]['children'];inputs={};refs={};metrics={};clock_rows={}
        for row in rows:
            path=ROOT/row['view'];lef=next(path.glob('*.lef'));raw=lef.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['lef_sha256'],str(lef)
            inputs[str(lef.relative_to(ROOT))]=row['lef_sha256']; key=row['instance']; refs[key]=pinmap(raw.decode()); metrics[key]={}
            ins=json.load(open(path/'insertion.json')) if (path/'insertion.json').exists() else None
            tt=next(path.glob('*_tt.lib'),None)
            if tt:
                lib=A.parse_lib(tt); ck=A.clock_refs(lib,ins,'tt'); metrics[key]=A.pin_metrics(lib,ck)
                clock_rows[key]=ck
        absent=[];parent_connections=0
        for name,c in module['cells'].items():
            matches=[r for r in rows if fnmatch.fnmatchcase(name,r['instance'])]
            row=matches[0] if matches else None
            for port,bits in c['connections'].items():
                for i,bit in enumerate(bits):
                    if not isinstance(bit,int):continue
                    if row is None:
                        if c['type']!='$scopeinfo':parent_connections+=1
                        continue
                    pin=port+'['+str(i)+']' if len(bits)>1 else port
                    xy=refs[row['instance']].get(pin)
                    if xy is None:absent.append([name,pin]);continue
                    nodes[bit].append({'instance':name,'key':row['instance'],'port':pin,'direction':c['port_directions'][port],'xy':transform(row,xy),'metrics':metrics[row['instance']].get(pin,{})})
        # Every retained hard-child bit is checked, including nets with no other
        # hard endpoint. Clock/reset are inventoried and deliberately not timed
        # as synchronous data here.
        pairs=collections.defaultdict(lambda:dict(bits=0,max_length_um=0,over_500_bits=0,pair_budget_fail_bits=0,unmeasured_timing_bits=0,worst_pins=None))
        segments=[];excluded=0;hard_to_parent_or_boundary=0
        for bit,ends in nodes.items():
            signal=[e for e in ends if not re.match(r'^(clk|ck|rst_a|rst_n)$',e['port'])]
            if len(signal)<2:
                if signal:hard_to_parent_or_boundary+=1
                excluded+=1;continue
            drivers=[e for e in signal if e['direction']=='output']
            sinks=[e for e in signal if e['direction']=='input']
            for src in drivers:
                for dst in sinks:
                    if src['instance']==dst['instance']:continue
                    key=src['instance']+' -> '+dst['instance']; r=pairs[key];r['bits']+=1
                    x,y=src['xy'];z,w=dst['xy'];L=abs(z-x)+abs(w-y)
                    if L>r['max_length_um']:r['max_length_um']=L;r['worst_pins']=[src['port'],dst['port']]
                    r['over_500_bits']+=L>500
                    out=src['metrics'].get('out');inp=dst['metrics'].get('inp')
                    if out is None or inp is None:r['unmeasured_timing_bits']+=1
                    else:
                        r['pair_budget_fail_bits']+=out+inp+0.76*L>623.3 # earlier trunk tap: skew150+uncertainty60
                    segments.extend([(x,y,z,y,'H'),(z,y,z,w,'V')])
        W,H=geom['outline_um'];cuts=[]
        for axis,limit,pitch in (('H',H,0.064),('V',W,0.064)):
            # H wires cross x cuts, V wires cross y cuts.
            span=W if axis=='H' else H
            for at in range(25,int(span),25):
                demand=sum(min(s[0],s[2])<at<max(s[0],s[2]) if axis=='H' else min(s[1],s[3])<at<max(s[1],s[3]) for s in segments if s[4]==axis)
                capacity=limit/pitch
                cuts.append({'wire_direction':axis,'cut_at_um':at,'bits':demand,'optimistic_capacity_tracks':capacity,'utilization':demand/capacity})
        windows=[]
        for size in (100,200,400):
            for x0 in range(0,int(W),50):
                for y0 in range(0,int(H),50):
                    x1=min(W,x0+size);y1=min(H,y0+size);hd=vd=0
                    for x,y,z,w,axis in segments:
                        if axis=='H' and y0<=y<y1:hd+=max(0,min(x1,max(x,z))-max(x0,min(x,z)))
                        if axis=='V' and x0<=x<x1:vd+=max(0,min(y1,max(y,w))-max(y0,min(y,w)))
                    area=(x1-x0)*(y1-y0);util=max(hd,vd)/(area/0.064)
                    windows.append({'rect_um':[x0,y0,x1,y1],'size_um':size,'H_wire_um':hd,'V_wire_um':vd,'optimistic_capacity_track_um':area/0.064,'utilization':util})
        result[variant]={'geometry_sha256':hashlib.sha256(Path(a.geometry).read_bytes()).hexdigest(),'boundary_netlist_sha256':hashlib.sha256((work/(variant+'.json')).read_bytes()).hexdigest(),'input_lef_sha256':inputs,'pins_missing':absent,'real_endpoint_bits_checked':sum(len(x) for x in nodes.values()),'hard_to_parent_or_boundary_unique_bits':hard_to_parent_or_boundary,'parent_connection_endpoints_without_physical_view':parent_connections,'parent_sequential_Q_bits':json.load(open(work/'boundary_census.json'))[variant]['parent_sequential_Q_bits'],'pair_rows':dict(pairs),'clock_references':clock_rows,'worst_cuts':sorted(cuts,key=lambda x:x['utilization'],reverse=True)[:20],'worst_windows':sorted(windows,key=lambda x:x['utilization'],reverse=True)[:20],'route_model':'first actual LEF access rectangle, horizontal then vertical; optimistic M6/M7 capacity, obstacles/PG/parent nets excluded','admission':'REFUSED_INCOMPLETE_PARENT_AND_BOUNDARY_VIEWS','geometry_only':True}
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:{x:v[x] for x in ('real_endpoint_bits_checked','parent_sequential_Q_bits','hard_to_parent_or_boundary_unique_bits','admission')}for k,v in result.items()}))


if __name__=='__main__':main()
