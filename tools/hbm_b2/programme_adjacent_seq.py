"""Finite adjacent sequential hop model from saved native ODB connectivity.

Stops at every FF or native macro; never traverses a sequential boundary.
Uses proposed FF rows/native SRAM rectangles only, not synthetic ODB placement.
"""
import argparse
import csv
import heapq
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def canonical(name):
    return name.replace('\\[','[').replace('\\]',']')


def rect_distance(a,b):
    return max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--ff-rows',type=Path,required=True);p.add_argument('--row-model',type=Path,required=True)
    p.add_argument('--ingress',type=Path,required=True);p.add_argument('--macro-lef',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    cells={};loads=defaultdict(list)
    for x in csv.DictReader(a.graph.open(),delimiter='\t'):
        if x['kind']!='ITERM':continue
        c=cells.setdefault(x['owner'],dict(master=x['master'],mastertype=x['mastertype'],pins=[]))
        c['pins'].append((x['pin'],x['io'],x['signal'],x['net']))
    for name,c in cells.items():
        c['kind']='macro' if c['mastertype']=='BLOCK' else 'ff' if any(s=='CLOCK' and io=='INPUT' for p,io,s,n in c['pins']) else 'comb'
        for pin,io,sig,net in c['pins']:
            if io=='INPUT' and net:loads[net].append((name,pin,sig))
    ffrows={r['cell']:r for r in csv.DictReader(a.ff_rows.open())}
    ff_names={n:canonical(n) for n,c in cells.items() if c['kind']=='ff'}
    assert len(ff_names)==len(set(ff_names.values()))==20842
    assert set(ff_names.values())<=set(ffrows)
    model=json.loads(a.row_model.read_text());macros={m['name']:m for m in model['macros']}
    actual_macro_names={canonical(n) for n,c in cells.items() if c['kind']=='macro'}
    assert actual_macro_names==set(macros) and len(macros)==44
    masters=json.loads(a.ingress.read_text())['FF_native_pin_masters']
    lef=a.macro_lef.read_text();macro_pins={}
    for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',lef,re.S):
        rects=[list(map(float,x)) for x in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',m[2])]
        if rects:macro_pins[m[1]]=rects
    pin_cache={}
    def pin_boxes(owner,pin):
        key=(owner,pin)
        if key in pin_cache:return pin_cache[key]
        c=cells[owner];plain=canonical(owner);pin=canonical(pin)
        if c['kind']=='ff':
            r=ffrows[plain];m=masters[c['master']]
            assert r['master']==c['master']
            x,y=float(r['x_um'])-m['w']/2,float(r['y_um'])-m['h']/2
            rects=m['pins'][pin]
            boxes=[[x+u,y+v,x+U,y+V] for u,v,U,V in rects]
            boxes += [[x+u,y+m['h']-V,x+U,y+m['h']-v] for u,v,U,V in rects]
        else:
            assert c['kind']=='macro' and c['master']=='ot_sram_1r1w_512x256_m1_r2c2'
            x,y,_,_=macros[plain]['rect_um']
            boxes=[[x+u,y+v,x+U,y+V] for u,v,U,V in macro_pins[pin]]
        pin_cache[key]=boxes
        return boxes
    frontier_cache={}
    def frontier(net):
        if net in frontier_cache:return frontier_cache[net]
        todo=[net];seen=set();comb=set();ends=set()
        while todo:
            n=todo.pop()
            if n in seen:continue
            seen.add(n)
            for owner,pin,sig in loads.get(n,[]):
                c=cells[owner]
                if c['kind']=='comb':
                    if owner in comb:continue
                    comb.add(owner)
                    todo.extend(z for pp,io,s,z in c['pins'] if z and io=='OUTPUT' and s!='CLOCK')
                elif sig!='CLOCK':ends.add((owner,pin))
        value=sorted(ends);frontier_cache[net]=value
        return value
    def family(name):
        name=canonical(name).split('$_')[0]
        return re.sub(r'\[\d+\]$','',name)
    stats=defaultdict(lambda:dict(edges=0,bad=0,max_optimistic_pin_distance_um=0.))
    pairs=Counter();worst=[];serial=0
    with (a.out/'adjacent_sequential_edges.csv').open('w') as file:
        writer=csv.writer(file);writer.writerow(['launch_kind','launch_owner','launch_pin','capture_kind','capture_owner','capture_pin','optimistic_native_pin_distance_um'])
        for owner,c in sorted(cells.items()):
            if c['kind'] not in ('ff','macro'):continue
            for pin,io,sig,net in c['pins']:
                if io!='OUTPUT' or sig=='CLOCK' or not net:continue
                source=pin_boxes(owner,pin)
                for target,tp in frontier(net):
                    tc=cells[target];kind=c['kind']+'→'+tc['kind']
                    assert kind in ['ff→ff','ff→macro','macro→ff','macro→macro'],kind
                    distance=min(rect_distance(s,t) for s in source for t in pin_boxes(target,tp))
                    writer.writerow([c['kind'],owner,pin,tc['kind'],target,tp,round(distance,6)])
                    q=stats[kind];q['edges']+=1;q['max_optimistic_pin_distance_um']=max(q['max_optimistic_pin_distance_um'],distance)
                    if distance>405+1e-8:
                        q['bad']+=1;pairs[(kind,family(owner),family(target))]+=1
                        row=dict(launch_kind=c['kind'],launch_owner=owner,launch_pin=pin,
                                 capture_kind=tc['kind'],capture_owner=target,capture_pin=tp,
                                 optimistic_native_pin_distance_um=distance)
                        serial+=1
                        if len(worst)<1000:heapq.heappush(worst,(distance,serial,row))
                        elif distance>worst[0][0]:heapq.heapreplace(worst,(distance,serial,row))
    result=dict(status='FAIL_PROPOSED_ADJACENT_SEQUENTIAL_GEOMETRY' if any(q['bad'] for q in stats.values()) else 'NECESSARY_ADJACENT_SEQUENTIAL_GEOMETRY_ONLY',
        actual_FF=20842,actual_SRAM=44,proposed_outline_um=model['outline_um'],macro_halo_um=4.32,
        edge_classes=dict(stats),bad_bank_pairs=[dict(kind=k[0],launch_family=k[1],capture_family=k[2],edges=v) for k,v in pairs.most_common()],
        worst_bad_edges=[r for _,_,r in sorted(worst,reverse=True)],
        traversal='Actual MTerm INPUT/OUTPUT graph; combinational arcs conservatively all-input/all-output, stop at every sequential/native boundary, CLOCK targets excluded',
        geometry='Actual native LEF signal rectangles; proposed R0 SRAM locations and either R0/MX FF orientation. Minimum rectangle distance is optimistic; >405 is a necessary failure, <=405 is not timing/routing closure.',
        extra_preopt_rows=1088,extra_rows_placed_or_used_as_endpoints=False,
        holds=['No CAD/PLACE/CTS/route/STA/source/default activation','Native macro pin-grid snap and actual physical IO/clock/reset/START integration remain separate','Combinational structural reach may include unsensitized arcs; source-specific exclusion would need proof'])
    (a.out/'adjacent_model.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],dict(stats),flush=True)
    for q in result['bad_bank_pairs'][:24]:print(q,flush=True)


if __name__=='__main__':main()
