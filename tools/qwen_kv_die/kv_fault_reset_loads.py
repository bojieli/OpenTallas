#!/usr/bin/env python3
"""Emit review-only reset loads; never retime existing resets or approve new loads."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import kv_fault_plane as I
P=I.P


def trace_reset(bit, edges):
    chain=[];seen=set()
    while bit in edges:
        if bit in seen:raise ValueError('reset relay cycle')
        seen.add(bit)
        entries=edges[bit]
        if len(entries)!=1:raise ValueError('multiple reset relay drivers')
        entry=entries[0];chain.append(dict(entry))
        bit=tuple(entry['input_bit'])
    return dict(root_bit=list(bit),registered_depth=len(chain),chain=chain)


def derive(run,plan,source):
    die=run/'case_kv/die.v';nets,_,_,insts=P.parse_die(str(die))
    def bits(e):
        result=P.expr_bits(e,nets)
        if result is None or any(b[0] in ('CONST','UNDECL','Z') for b in result):raise ValueError('unresolved reset expression '+str(e))
        return result
    cells={i:m for m,i,_,_ in insts}
    places={m[1]:(float(m[2]),float(m[3]),m[4]) for m in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)',(run/'case_kv/place.tcl').read_text())}
    macros={}
    for mm in re.finditer(r'^MACRO (\S+)\s*$(.*?)^END \1\s*$',(run/'case_kv/elements.lef').read_text(),re.M|re.S):
        size=re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',mm[2]);pins={}
        for pp in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$',mm[2],re.M|re.S):
            rect=re.search(r'RECT\s+([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pp[2])
            if rect:
                x0,y0,x1,y1=map(float,rect.groups());pins[pp[1]]=[(x0+x1)/2,(y0+y1)/2]
        macros[mm[1]]=(list(map(float,size.groups())),pins)
    def point(inst,port,index=0):
        (w,h),pins=macros[cells[inst]];pin=port if port in pins else f'{port}[{index}]'
        if pin not in pins:raise ValueError('native reset source pin missing '+inst+'.'+pin)
        x,y=pins[pin];px,py,orient=places[inst]
        if orient=='MX':y=h-y
        elif orient=='MY':x=w-x
        elif orient=='R180':x,y=w-x,h-y
        elif orient!='R0':raise ValueError('unqualified reset source orientation')
        return [px+x,py+y]
    edges={};host=[];regional={}
    for master,inst,params,ports in insts:
        if master=='qkd_host_rt' and inst=='host':host.append(ports)
        if master in ('qkd_rst_region','qkd_rst_region_pr'):
            b=bits(ports['b'])
            if len(b)!=1:raise ValueError('regional reset root width')
            regional.setdefault(b[0],[]).append(dict(instance=inst,master=master,port='b',clock=ports['ck'],parameters=params,input=ports['a'],delay_input=ports.get('dly')))
        if master!='qkd_rlys_1':continue
        if params:raise ValueError('reset standard has parameters')
        a,b=bits(ports['a']),bits(ports['b'])
        if len(a)!=1 or len(b)!=1:raise ValueError('reset standard width')
        edges.setdefault(b[0],[]).append(dict(instance=inst,input_bit=list(a[0]),output_bit=list(b[0]),output_pin_xy=point(inst,'b'),clock=ports['ck']))
    if len(host)!=1:raise ValueError('exact host root not present')
    view=source/'physical/ref_tile/qkd_astk_fault_join/views/qkd_astk_fault_join/qkd_astk_fault_join.lef'
    text=view.read_text();m=re.search(r'PIN rst_n\s+(.*?)END rst_n',text,re.S)
    if not m or 'DIRECTION INPUT' not in m[1]:raise ValueError('native reset input missing')
    rect=re.search(r'RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[1]);x0,y0,x1,y1=map(float,rect.groups());local=[(x0+x1)/2,(y0+y1)/2]
    loads=[]
    for node in plan['nodes']:
        if node['master']!='qkd_astk_fault_join' or node['placement']['orient']!='R0':raise ValueError('unqualified new load')
        reset=bits(node['reset'])
        if len(reset)!=1:raise ValueError('new reset not scalar')
        path=trace_reset(reset[0],edges);root=tuple(path['root_bit'])
        # This is a depth measured from the exact host output, not an inferred
        # global release epoch. Unknown roots stay blocked for planner review.
        root_ports=[p for p,e in host[0].items() if root in (P.expr_bits(e,nets) or [])]
        root_region=regional.get(root,[])
        if len(root_region)>1:raise ValueError('multiple regional reset roots')
        host_root=len(root_ports)==1 and bool(re.match(r'^n_(rst_|hboot)',root[0]))
        qualified=host_root or bool(root_region)
        root_info=(dict(instance='host',port=root_ports[0],kind='HOST_OUTPUT',clock=host[0].get('ck_rst'),native_clock_port='ck_rst') if host_root else
                   dict(root_region[0],kind='REGIONAL_REGISTERED_RELEASE') if root_region else None)
        if qualified:
            root_info['id']=root_info['instance']+'.'+root_info['port']+':'+str(root)
            root_info['output_bit']=list(root)
            expr=host[0][root_info['port']] if host_root else next(c[root_info['port']] for _,i,_,c in insts if i==root_info['instance'])
            index=list(reversed(P.expr_bits(expr,nets))).index(root)
            root_info['output_pin_xy']=point(root_info['instance'],root_info['port'],index)
            root_info['depth_from_root']=0
            for k,entry in enumerate(path['chain']):
                entry['depth_from_root']=path['registered_depth']-k
                entry['root_id']=root_info['id']
        pl=node['placement'];loads.append(dict(instance='kv_'+node['id'],master=node['master'],port='rst_n',
            reset_net=node['reset'],clock=node['clock'],native_pin_xy=[pl['x']+local[0],pl['y']+local[1]],
            inherited_release=path,root_instance=root_info['instance'] if qualified else None,root_port=root_info['port'] if qualified else None,root_details=root_info,
            status='EXISTING_DEPTH_MEASURED_ADDITIVE_BRANCH_PENDING' if qualified else 'BLOCKED_UNKNOWN_RESET_ROOT',
            required_target_depth=path['registered_depth'] if qualified else None))
    return dict(schema='opentallas.kv_fault_reset_loads.v1',status='REVIEW_ONLY_RESET_ADMISSION_OPEN',
        input_die_sha256=I.digest(die),native_lef_sha256=I.digest(view),
        input_place_sha256=I.digest(run/'case_kv/place.tcl'),input_lef_sha256=I.digest(run/'case_kv/elements.lef'),
        candidate_normalized_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest(),loads=loads,
        load_count=len(loads),unknown_root_loads=sum(x['root_instance'] is None for x in loads),
        constraints=['Preserve every existing reset load and release edge',
                     'Depth is relative to exact host or regional output; it does not imply an equal global release edge',
                     'Default regional HOLD128 does not alone prove clearing a 180-edge fault graph',
                     'Prove source clear arrival + full path flush + reset skew precedes final sticky release; no stale fault resurrection',
                     'Additive branches must match each target measured host-relative depth and actual clock calendar',
                     'Native pin reach/fanout, closed branch loads, flush bound and all-root reset simulation remain required',
                     'No direct inherited reset alias is physically admitted by this manifest'])


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--run',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--source-tree',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args()
    doc=derive(v.run,json.loads(v.plan.read_text()),v.source_tree);v.out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:doc[k] for k in ('status','load_count','unknown_root_loads')}))
if __name__=='__main__':main()
