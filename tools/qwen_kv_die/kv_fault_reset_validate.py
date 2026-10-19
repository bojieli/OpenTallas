#!/usr/bin/env python3
"""Independent actual-case native reset branch geometry/fanout checker."""
import argparse,collections,json,re
from pathlib import Path
import kv_fault_plane as I
from kv_fault_reset_plan import Space,dist,norm

def validate(run,inv,c,m,p):
    P=I.P;nets,_,_,insts=P.parse_die(str(run/'case_kv/die.v'))
    uses=collections.Counter()
    for _,_,_,ports in insts:
        for expr in ports.values():uses.update(b for b in (P.expr_bits(expr,nets) or []) if b[0]!='CONST')
    lef=(run/'case_kv/elements.lef').read_text();macro=re.search(r'^MACRO qkd_rlys_1\s*$(.*?)^END qkd_rlys_1$',lef,re.M|re.S)
    if not macro:raise ValueError('Native reset relay view absent')
    body=macro[1];sz=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body);w,h=map(float,sz.groups())
    pins={}
    for port in ('a[0]','b[0]'):
        pin=re.search(r'PIN '+re.escape(port)+r'\s+(.*?)END '+re.escape(port),body,re.S)
        rect=re.search(r'RECT\s+([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin[1]);x0,y0,x1,y1=map(float,rect.groups());pins[port]=[(x0+x1)/2,(y0+y1)/2]
    if (w,h)!=(12.96,12.96):raise ValueError('Unqualified relay native outline')
    rects=list(inv['physical_obstacles'])
    for n in c['nodes']:
        x,y=n['placement']['x'],n['placement']['y'];rects.append([x,y,x+21.6,y+21.6])
    space=Space(rects);nodes={};loads=collections.Counter();original={}
    for n in m['existing_reset_nodes']:
        k=(n['root_id'],n['instance']);nodes[k]=dict(xy=n['output_pin_xy'],depth=n['depth_from_root'],clock=norm(n['clock']))
        original[k]=max(0,uses[tuple(n['output_bit'])]-1)
    maximum=0
    for n in p['stations']:
        k=(n['root_id'],n['id']);s=(n['root_id'],n['source'])
        if k in nodes or s not in nodes:raise ValueError('Missing/duplicate branch source')
        parent=nodes[s];pl=n['placement'];x,y=pl['x'],pl['y'];g=[x/w,y/h]
        if pl['orient']!='R0' or not space.free(g):raise ValueError('Overlapping/unsupported branch placement')
        if n['clock']!=parent['clock'] or n['depth']!=parent['depth']+1:raise ValueError('Wrong reset root/clock/depth')
        pi=[x+pins['a[0]'][0],y+pins['a[0]'][1]];po=[x+pins['b[0]'][0],y+pins['b[0]'][1]];edge=dist(parent['xy'],pi)
        if edge>405+1e-6 or abs(edge-n['edge_um'])>1e-6:raise ValueError('Long/forged reset edge')
        if any(abs(a-b)>1e-6 for a,b in zip(pi,n['input_xy'])) or any(abs(a-b)>1e-6 for a,b in zip(po,n['output_xy'])):raise ValueError('Wrong native relay pin')
        loads[s]+=1;maximum=max(maximum,edge);space.add([x,y,x+w,y+h]);nodes[k]=dict(xy=po,depth=n['depth'],clock=n['clock'])
    target={l['instance']:l for l in m['loads']};seen=set()
    for n in p['targets']:
        if n['instance'] not in target or n['instance'] in seen:raise ValueError('Missing/duplicate target')
        seen.add(n['instance']);old=target[n['instance']];s=(n['root_id'],n['source'])
        if s not in nodes:raise ValueError('Missing target reset branch')
        parent=nodes[s]
        if n['root_id']!=old['root_details']['id'] or n['clock']!=norm(old['clock']) or n['clock']!=parent['clock'] or n['depth']!=parent['depth']:raise ValueError('Wrong target reset identity')
        if n['pin_xy']!=old['native_pin_xy']:raise ValueError('Target native pin drift')
        edge=dist(parent['xy'],old['native_pin_xy'])
        if edge>405+1e-6 or abs(edge-n['edge_um'])>1e-6:raise ValueError('Target reach violation')
        loads[s]+=1;maximum=max(maximum,edge)
    if seen!=set(target):raise ValueError('Missing reset target')
    total={k:loads[k]+original.get(k,0) for k in loads}
    if any(v>32 for v in total.values()):raise ValueError('Reset fanout exceeds32')
    return dict(status='INDEPENDENT_NATIVE_GEOMETRY_AND_FANOUT_PASS_NOT_CLOCK_ADMISSION',qualified_release=False,targets=len(seen),new_stations=len(p['stations']),max_edge_um=maximum,max_total_seed_or_branch_fanout=max(total.values()),new_clock_pins_unqualified=len(p['stations']),input_case_hashes={f:I.digest(run/f) for f in ('case_kv/die.v','case_kv/place.tcl','case_kv/elements.lef')})

def main():
    a=argparse.ArgumentParser();a.add_argument('--run',type=Path,required=True);a.add_argument('--dir',type=Path,required=True);v=a.parse_args();d=v.dir
    inv=json.loads((d/'inventory.json').read_text());c=json.loads((d/'candidate.json').read_text());m=json.loads((d/'reset_loads.json').read_text());p=json.loads((d/'reset_branch_candidate.json').read_text())
    out=validate(v.run,inv,c,m,p);(d/'reset_branch_validation.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
