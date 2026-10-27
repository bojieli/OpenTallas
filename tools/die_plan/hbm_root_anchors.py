#!/usr/bin/env python3
"""Resolve native N4 root ports to real mapped DFF pins, through buffers/inverters only.
Accepts hierarchical Yosys JSON. Does not create flops, pins or timing exceptions.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

PORTS=('up_nw','up_ne','down_nw','down_ne')


def collect(graph, top='ot_hnx_fused_hub_n4ext', cell_directions=None):
    modules=graph['modules']; fanin=collections.defaultdict(list);fanout=collections.defaultdict(list)
    leaves={}; parent={}
    def canonical(bit):
        trail=[]
        while bit in parent and parent[bit]!=bit:
            trail.append(bit);bit=parent[bit]
        for old in trail:parent[old]=bit
        return bit
    def alias(a,b):
        a,b=canonical(a),canonical(b)
        if a==b:return
        if isinstance(a,str) and isinstance(b,str):raise ValueError('contradictory constants')
        if isinstance(b,str):a,b=b,a
        parent[b]=a
    def descend(mod,path,bindings):
        body=modules[mod]
        def net(bit):
            if isinstance(bit,str):return bit
            return bindings.get(bit,(path,bit))
        for name,cell in body.get('cells',{}).items():
            cp=path+'/'+name if path else name;kind=cell['type'];cm=modules.get(kind)
            if cm and not cm.get('attributes',{}).get('blackbox'):
                binds={}
                for pn,p in cm['ports'].items():
                    for cb,pb in zip(p['bits'],cell['connections'].get(pn,[])):
                        if isinstance(cb,int):
                            value=net(pb)
                            if cb in binds:alias(binds[cb],value)
                            else:binds[cb]=value
                        elif p['direction']=='output':alias(cb,net(pb))
                descend(kind,cp,binds)
                continue
            dirs=cell.get('port_directions') or (cell_directions or {}).get(kind) or {n:p['direction'] for n,p in (cm or {}).get('ports',{}).items()}
            con={pn:[net(b) for b in bits] for pn,bits in cell['connections'].items()}
            leaves[cp]=(kind,con,dirs)
            for pn,bits in con.items():
                for bit in bits:
                    if isinstance(bit,str):continue
                    if dirs.get(pn)=='output':fanin[bit].append((cp,pn))
                    elif dirs.get(pn)=='input':fanout[bit].append((cp,pn))
    descend(top,'',{})
    for original in (fanin,fanout):
        merged=collections.defaultdict(list)
        for bit,edges in original.items():merged[canonical(bit)].extend(edges)
        original.clear();original.update(merged)
    rows=[]
    for pn in PORTS:
        port=modules[top]['ports'][pn];is_input=port['direction']=='input'
        for bi,bit in enumerate(port['bits']):
            token=bit if isinstance(bit,str) else ('',bit)
            frontier=[];blocked=[];todo=[token];visited=set()
            while todo:
                cur=canonical(todo.pop())
                if cur in visited:continue
                visited.add(cur)
                if isinstance(cur,str):
                    blocked.append(dict(reason='constant',value=cur));continue
                edges=fanout.get(cur,[]) if is_input else fanin.get(cur,[])
                if not edges:blocked.append(dict(reason='no mapped cell'))
                for cp,term in edges:
                    kind,con,dirs=leaves[cp]
                    if 'DFF' in kind.upper():
                        if (is_input and term=='D') or (not is_input and term in ('Q','QN')):
                            frontier.append(dict(cell=cp,type=kind,pin=term))
                        else:blocked.append(dict(reason='non-data sequential pin',cell=cp,pin=term))
                    elif kind.startswith(('INV','BUF','HB')):
                        wanted='output' if is_input else 'input'
                        nxt=[b for p,bs in con.items() if dirs.get(p)==wanted for b in bs]
                        if len(nxt)!=1:blocked.append(dict(reason='non-unary buffer',cell=cp,type=kind))
                        else:todo.extend(nxt)
                    else:blocked.append(dict(reason='combinational frontier',cell=cp,type=kind,pin=term))
            anchors=[dict(cell=c,type=t,pin=p) for c,t,p in sorted({(x['cell'],x['type'],x['pin']) for x in frontier})]
            rows.append(dict(port=pn,bit=bi,direction=port['direction'],anchors=anchors,blocked=blocked,
                             verdict='PASS' if len(anchors)==1 and not blocked else 'OPEN'))
    return dict(schema='opentallas.hbm-root-native-anchors.v1',scope='actual mapped sequential frontier; no physical pin placement or route PASS',
                mapped_leaf_cells=len(leaves), standard_cells=sum('ASAP7' in k for k,_,_ in leaves.values()),
                ff_cells=sum('DFF' in k for k,_,_ in leaves.values()),port_bits=len(rows),resolved_bits=sum(r['verdict']=='PASS' for r in rows),
                open_bits=sum(r['verdict']!='PASS' for r in rows),rows=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapped_json',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--cell-directions',type=Path)
    a=p.parse_args();data=a.mapped_json.read_bytes();out=collect(json.loads(data),cell_directions=json.loads(a.cell_directions.read_text()) if a.cell_directions else None);out['mapped_json_sha256']=hashlib.sha256(data).hexdigest()
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
if __name__=='__main__':main()
