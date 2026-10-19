#!/usr/bin/env python3
"""Inventory exact KV fault sources and conservatively unused forwarded payload lanes.

Read-only planning stage. This emits no waivers, netlist edits, or physical-closure claim.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import die_port_bind as P


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inventory(run,source_tree=None,die_relative='port_bind_v2/die_bound.v'):
    bound=run/die_relative
    nets,_,_,insts=P.parse_die(str(bound))
    cells={i:(m,p,c) for m,i,p,c in insts}
    if len(cells)!=len(insts):
        raise ValueError('duplicate instance identity')
    places={m.group(1):dict(x=float(m.group(2)),y=float(m.group(3)),orient=m.group(4))
            for m in re.finditer(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)',(run/'case_kv/place.tcl').read_text())}
    fwd=json.loads((run/'fwd_lanes.json').read_text())
    _,_,_,raw_instances=P.parse_die(str(run/'case_kv/die.v'))
    physical_masters={i:m for m,i,p,c in raw_instances}
    lef=(run/'case_kv/elements.lef').read_text()
    macros={}
    for match in re.finditer(r'^MACRO (\S+)\s*$(.*?)^END \1\s*$',lef,re.M|re.S):
        name,body=match.groups();size=re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',body)
        if not size: raise ValueError('macro without size '+name)
        pins={}
        for pin in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$',body,re.M|re.S):
            rect=re.search(r'RECT\s+([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin.group(2))
            if rect:
                x0,y0,x1,y1=map(float,rect.groups());pins[pin.group(1)]=[(x0+x1)/2,(y0+y1)/2]
        macros[name]=dict(size=list(map(float,size.groups())),pins=pins)
    def point(i,port):
        macro=macros[physical_masters[i]]
        pin=port if port in macro['pins'] else port+'[0]'
        if pin not in macro['pins']: return None
        x,y=macro['pins'][pin];w,h=macro['size'];pl=places[i]
        if pl['orient']=='MX': y=h-y
        elif pl['orient']=='MY': x=w-x
        elif pl['orient']=='R180': x,y=w-x,h-y
        elif pl['orient']!='R0': raise ValueError('unsupported orientation '+pl['orient'])
        return [pl['x']+x,pl['y']+y]
    obstacles=[]
    for i,pl in places.items():
        w,h=macros[physical_masters[i]]['size']
        obstacles.append([pl['x'],pl['y'],pl['x']+w,pl['y']+h])
    def ref(expr):
        bits=P.expr_bits(expr,nets)
        if bits is None or len(bits)!=1 or bits[0][0]=='CONST':
            raise ValueError('expected exact scalar signal: '+str(expr))
        return list(bits[0])
    def scalar(expr):
        name,bit=ref(expr)
        return f'{name}[{bit}]'
    def role(i,port,clock,reset,sticky):
        m,p,c=cells[i]
        if p: raise ValueError('unexpected parametrized source '+i)
        return dict(id=i+'.'+port,instance=i,master=m,port=port,
                    signal=ref(c[port]) if port in c else None,
                    clock=scalar(c[clock]),reset=scalar(c[reset]),sticky=sticky,
                    requires_sticky_latch=not sticky,placement=places[i],pin_xy=point(i,port))
    sources=[]
    for i,(m,p,c) in sorted(cells.items()):
        if m.startswith(('qkd_landsh_','qkd_landsh0_')) and not re.fullmatch(r'qkd_landsh0?_(1|36|296|528)',m):
            raise ValueError('new landing family requires exact fault admission '+m)
        if re.fullmatch(r'qkd_landsh0?_(1|36|296|528)',m):
            sources.append(role(i,'fault','ck','rs',True))
    for region in ('WS','WN','ES','EN'):
        i='kc_'+region
        if cells[i][0]!='qkd_ctrl_kc': raise ValueError('unqualified control source '+i)
        sources.append(role(i,'kf','ck','rsi',False))
    native_evidence={}
    if source_tree is not None:
        view=source_tree/'physical/ref_tile/qkd_ctrl_kc/views/qkd_ctrl_kc'
        path=view/'qkd_ctrl_kc.lef';text=path.read_text()
        size=re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',text)
        pin=re.search(r'\bPIN kf\s+(.*?)END kf',text,re.S)
        if not size or not pin or not re.search(r'DIRECTION OUTPUT',pin.group(1)):
            raise ValueError('canonical KC view does not expose output kf')
        rect=re.search(r'RECT\s+([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin.group(1))
        if not rect: raise ValueError('canonical KC kf has no physical rectangle')
        x0,y0,x1,y1=map(float,rect.groups());px,py=(x0+x1)/2,(y0+y1)/2
        for src in sources:
            if src['master']!='qkd_ctrl_kc': continue
            pl=src['placement']
            if pl['orient']!='R0': raise ValueError('native KC orientation requires explicit transform')
            src['successor_native_pin_xy']=[pl['x']+px,pl['y']+py]
            src['native_pin_basis']='Existing closed KC view, not the old generated case; regenerate case before binding'
        native_evidence=dict(view=str(view),pin='kf',size=list(map(float,size.groups())),
                             files={name:digest(view/name) for name in ('qkd_ctrl_kc.lef','abstract.json','insertion.json')})
    sinkm,sinkp,sinkc=cells['kvs_attn']
    if sinkm!='qkd_kvs_attn' or sinkp: raise ValueError('unexpected final consumer')
    # Preserve all old hub-fault fanout. The existing final ufh net becomes one real tree leaf.
    sources.append(dict(id='existing_ufh',instance='kvs_attn',port='ufh',signal=ref(sinkc['ufh']),
                        clock=scalar(sinkc['ck']),reset=scalar(sinkc['rst_n']),sticky=False,
                        requires_sticky_latch=False,placement=places['kvs_attn'],
                        pin_xy=point('kvs_attn','ufh'),
                        note='Existing hub path remains on core c; final sticky collector must retain any pulse. No new crossing allowed'))
    # Count every occurrence except the exact b output of a qualified forwarded payload cell.
    # This overcounts unfamiliar outputs as consumers and therefore rejects uncertain spare capacity.
    consumers=defaultdict(list)
    uncertain_nets=set()
    payload_drivers=Counter()
    family=re.compile(r'qkd_(rlysh0?|landsh0?)_(1|36|296|528)$')
    for m,i,p,c in insts:
        for port,expr in c.items():
            if family.fullmatch(m) and port=='b':
                out=P.expr_bits(expr,nets)
                if out is None: raise ValueError('unknown payload output expression '+i)
                payload_drivers.update(out)
                continue
            bits=P.expr_bits(expr,nets)
            if bits is None:
                uncertain_nets.update(re.findall(r'[A-Za-z_][A-Za-z_0-9$]*',expr))
                continue
            for k,bit in enumerate(reversed(bits)):
                if bit[0]!='CONST': consumers[bit].append((i,port,k))
    lanes=[]
    for number,lane in enumerate(fwd['lanes']):
        chain=lane['stations'];width=lane['S']
        if lane['src_tree']=='c' or lane['dst_tree']!='c': continue
        pairs=[]
        for i in chain:
            m,p,c=cells[i];match=family.fullmatch(m)
            if not match or p or int(match.group(2))!=width:
                raise ValueError('unexpected forwarded station '+i)
            a=P.expr_bits(c['a'],nets);b=P.expr_bits(c['b'],nets)
            if a is None or b is None or len(a)!=width or len(b)!=width:
                raise ValueError('station width '+i)
            pairs.append((list(reversed(a)),list(reversed(b))))
        free=[]
        for bit in range(width):
            if pairs[0][0][bit]!=('CONST',0): continue
            good=True
            for k,(aa,bb) in enumerate(pairs):
                out=bb[bit]
                if out[0]=='CONST' or out[0] in uncertain_nets or payload_drivers[out]!=1: good=False;break
                expected=[]
                if k+1<len(chain):
                    nxt=pairs[k+1][0][bit]
                    # Original padding may be retied at each hop or transparently propagated.
                    if nxt==out: expected=[(chain[k+1],'a',bit)]
                    elif nxt!=('CONST',0): good=False;break
                if sorted(consumers[out])!=expected: good=False;break
            if good: free.append(bit)
        if free:
            lanes.append(dict(id='lane_'+str(number),src_tree=lane['src_tree'],dst_tree=lane['dst_tree'],
                              stations=chain,free_bits=free,first=places[chain[0]],last=places[chain[-1]],
                              source_clock=scalar(cells[chain[0]][2]['ck_s' if cells[chain[0]][0].startswith('qkd_landsh0_') else 'ck']),
                              destination_clock=scalar(cells[chain[-1]][2]['ck']),
                              source_enable=lane['en'],destination_reset=lane['rs'],K=lane['K'],
                              input_pin_xy={str(b):point(chain[0],f'a[{b}]') for b in free},
                              output_pin_xy={str(b):point(chain[-1],f'b[{b}]') for b in free},
                              physical_price_cycles=lane['landed']+lane.get('post_stages',0),
                              conservative_model_cycles=math.ceil(lane['landed']+lane.get('post_stages',0))+2,
                              timing_basis='Existing lane metadata only; actual phase/reset/age signoff remains required'))
    paths=[die_relative,'case_kv/place.tcl','case_kv/elements.lef','fwd_lanes.json']
    return dict(schema='opentallas.kv_fault_plane_inventory.v1',status='INVENTORY_ONLY_NOT_PHYSICALLY_CLOSED',
                input_die=die_relative,source_basis='CANONICAL_BOUND_NETLIST' if die_relative=='port_bind_v2/die_bound.v' else 'EXPLICIT_RAW_PHYSICAL_UNBOUND_NETLIST',
                pinned_files={p:digest(run/p) for p in paths},native_kc_evidence=native_evidence,sources=sources,
                source_counts_by_clock=dict(Counter(s['clock'] for s in sources)),
                physical_obstacles=obstacles,
                physical_blockers=[dict(source=s['id'],reason='Generated case omits physical output pin; regenerate real consumer bus and native binding, canonical closed view must expose pin') for s in sources if s['pin_xy'] is None],
                consumer=dict(pin_xy=point('kvs_attn','ufh'),instance='kvs_attn',port='ufh',clock=scalar(sinkc['ck']),reset=scalar(sinkc['rst_n']),placement=places['kvs_attn']),
                spare_transport_candidates=lanes,
                spare_capacity_by_region=dict(Counter({r:sum(len(l['free_bits']) for l in lanes if l['src_tree']==r) for r in ('WS','WN','ES','EN')})),
                requirements=['No prior padding declaration may survive on a newly functional a/b bit',
                              'Rename and wire selected payload bit through EVERY station, including retied original pads',
                              'Sticky source qualification must precede crossing; final consumer requires sticky latch',
                              'All new cells require collision-free placement, native clock geometry, bounded same-root wires and priced closure',
                              'Reset/epoch flushing and retirement quiet must be proven from actual source calendars'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--source-tree',type=Path);ap.add_argument('--die-relative',default='port_bind_v2/die_bound.v');ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=inventory(a.run,a.source_tree,a.die_relative);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(doc,indent=1)+'\n')
    print(json.dumps(dict(sources=len(doc['sources']),by_clock=doc['source_counts_by_clock'],free_bits=doc['spare_capacity_by_region'])))
if __name__=='__main__':main()
