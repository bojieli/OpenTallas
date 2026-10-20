"""Emit a source-pinned mapped arithmetic graph with actual replicated drivers.

This is a technology-specific structural candidate, not a gate-rule change.
BUF/INV trees are canonicalised, then BOTH logic and state drivers are cloned
recursively. Each clone has the same input functions and clock/reset edge as
its original. A ledger proves that invariant before emitting any source.
No buffers are used to hide a logical driver's load count.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import heapq
import hashlib
import json
from pathlib import Path


class ReplicationFrontier(AssertionError):
    def __init__(self, report):
        self.report=report
        super().__init__(report['reason']+' '+json.dumps(report))


def cyclic_cells(inputs,drivers):
    """Conservative state/logic feedback frontier, linear iterative SCC walk.

    DFF copies on a feedback cycle need an initialization/state proof beyond
    the feed-forward capture induction. Never clone that graph speculatively.
    """
    adj={n:{drivers[b] for bs in ports.values() for b,_ in bs if b in drivers}
         for n,ports in inputs.items()}
    rev={n:[] for n in adj}
    for n,ps in adj.items():
        for p in ps:rev[p].append(n)
    visited=set();order=[]
    for start in adj:
        if start in visited:continue
        visited.add(start);stack=[(start,iter(adj[start]))]
        while stack:
            n,it=stack[-1]
            nxt=next(it,None)
            if nxt is None:order.append(n);stack.pop()
            elif nxt not in visited:
                visited.add(nxt);stack.append((nxt,iter(adj[nxt])))
    visited=set();cyclic=set()
    for start in reversed(order):
        if start in visited:continue
        component=[];stack=[start];visited.add(start)
        while stack:
            n=stack.pop();component.append(n)
            for p in rev[n]:
                if p not in visited:visited.add(p);stack.append(p)
        if len(component)>1 or start in adj[start]:cyclic.update(component)
    return cyclic


def bound(data, top, limit=24, clock_ports=('clk',), incremental=False):
    m=deepcopy(data['modules'][top])
    original=deepcopy(m['cells'])
    aliases={}
    removed=set()
    for name,c in m['cells'].items():
        typ=c['type']
        if typ.startswith(('BUF','INV','CKINV','HB')):
            ins=[b for p,bs in c['connections'].items()
                 if c['port_directions'][p]=='input' for b in bs]
            outs=[b for p,bs in c['connections'].items()
                  if c['port_directions'][p]=='output' for b in bs]
            assert len(ins)==len(outs)==1,(name,typ)
            aliases[outs[0]]=(ins[0],typ.startswith(('INV','CKINV')))
            removed.add(name)
    def norm(b):
        inv=False; seen=set()
        while b in aliases:
            assert b not in seen,'BUF/INV cycle'
            seen.add(b);b,v=aliases[b];inv^=v
        if isinstance(b,str):
            if inv and b in ('0','1'):b=str(1-int(b));inv=False
        return b,inv
    cells={n:c for n,c in m['cells'].items() if n not in removed and c['type']!='$scopeinfo'}
    origins={n:n for n in cells}
    families={}
    drivers={}
    inputs={}
    for n,c in cells.items():
        outs=[b for p,bs in c['connections'].items()
              if c['port_directions'][p]=='output' for b in bs]
        for b in outs:drivers[b]=n;families[b]=b
        inputs[n]={p:[norm(b) for b in bs] for p,bs in c['connections'].items()
                   if c['port_directions'][p]=='input'}
    outputs={p:[norm(b) for b in v['bits']] for p,v in m['ports'].items()
             if v['direction']=='output'}
    cyclic=cyclic_cells(inputs,drivers)
    nextbit=max([b for c in cells.values() for bs in c['connections'].values()
                 for b in bs if isinstance(b,int)]+[1])+1
    clock={b for p in clock_ports for b in m['ports'].get(p,{}).get('bits',[])}
    clones=0
    # The reference rebuild remains available for differential tests.  The
    # worklist updates only roots whose sink sets change after cloning.
    loads=defaultdict(dict)
    heap=[]
    versions=defaultdict(int)
    def add_load(bit, sink):
        if isinstance(bit,int) and (bit not in clock or sink[0]=='port'):
            loads[bit][sink]=None
    def touch(bit):
        if not isinstance(bit,int):return
        versions[bit]+=1
        if len(loads[bit])>limit:
            heapq.heappush(heap,(-len(loads[bit]),-bit,versions[bit]))
    if incremental:
        for n,ports in inputs.items():
            for p,bs in ports.items():
                for i,(bit,inv) in enumerate(bs):add_load(bit,('cell',n,p,i))
        for p,bs in outputs.items():
            for i,(bit,inv) in enumerate(bs):add_load(bit,('port',None,p,i))
        for bit in loads:touch(bit)
    while True:
        if incremental:
            while heap:
                count,negbit,version=heapq.heappop(heap);b=-negbit
                if versions[b]==version and -count==len(loads[b]):break
            else:break
            sinks=list(loads[b])
        else:
            scan=defaultdict(list)
            for n,ports in inputs.items():
                for p,bs in ports.items():
                    for i,(bit,inv) in enumerate(bs):
                        if isinstance(bit,int) and bit not in clock:
                            scan[bit].append(('cell',n,p,i))
            for p,bs in outputs.items():
                for i,(bit,inv) in enumerate(bs):
                    if isinstance(bit,int):scan[bit].append(('port',None,p,i))
            bad=[(len(sinks),bit,sinks) for bit,sinks in scan.items() if len(sinks)>limit]
            if not bad:break
            _,b,sinks=max(bad)
        if b not in drivers:
            ports=[p+'[%d]'%i for p,v in m['ports'].items() if v['direction']=='input'
                   for i,pb in enumerate(v['bits']) if norm(pb)[0]==b]
            raise ReplicationFrontier(dict(reason='unregistered port needs RTL distribution',
                net=b,ports=ports,loads=len(sinks),limit=limit,clones_so_far=clones,
                cells_so_far=len(cells),original_cells=len(original)))
        src=drivers[b];cell=cells[src]
        if origins[src] in cyclic:
            raise ReplicationFrontier(dict(reason='feedback state/logic needs explicit initialization proof',
                cell=src,type=cell['type'],net=b,loads=len(sinks),limit=limit,
                cyclic_cells=len(cyclic),clones_so_far=clones,cells_so_far=len(cells),
                original_cells=len(original)))
        outbits=[ob for p,bs in cell['connections'].items()
                 if cell['port_directions'][p]=='output' for ob in bs]
        if len(outbits)!=1:
            raise ReplicationFrontier(dict(reason='multi-output hard primitive needs explicit model/partition',
                cell=src,type=cell['type'],net=b,loads=len(sinks),limit=limit,
                clones_so_far=clones,cells_so_far=len(cells),original_cells=len(original)))
        outport=next(p for p in cell['connections'] if cell['port_directions'][p]=='output')
        for k in range(limit,len(sinks),limit):
            fresh=nextbit;nextbit+=1;clones+=1
            name='svc7_copy_%d'%clones
            cells[name]=deepcopy(cell)
            cells[name]['connections'][outport]=[fresh]
            origins[name]=origins[src]
            families[fresh]=families[b]
            drivers[fresh]=name
            inputs[name]=deepcopy(inputs[src])
            dirty=set()
            if incremental:
                for p,bs in inputs[name].items():
                    for i,(bit,inv) in enumerate(bs):
                        add_load(bit,('cell',name,p,i))
                        if isinstance(bit,int):dirty.add(bit)
            for kind,n,p,i in sinks[k:k+limit]:
                bs=inputs[n][p] if kind=='cell' else outputs[p]
                _,inv=bs[i];bs[i]=(fresh,inv)
                if incremental:
                    sink=(kind,n,p,i)
                    loads[b].pop(sink)
                    add_load(fresh,sink)
            if incremental:
                dirty.update((b,fresh))
                for bit in dirty:touch(bit)
    # Structural equivalence invariant: each primitive's type and every input
    # function, including clock/reset, agree with the original graph. Cloned
    # unreset registers require a separate legal reset/first-valid capture proof.
    for n,c in cells.items():
        old=original[origins[n]]
        assert c['type']==old['type']
        for p,bs in inputs[n].items():
            want=[norm(b) for b in old['connections'][p]]
            actual=[(families.get(b,b),v) for b,v in bs]
            assert actual==want,(n,p,actual,want)
    for p,bs in outputs.items():
        assert [(families.get(b,b),v) for b,v in bs]==[norm(b) for b in m['ports'][p]['bits']]
    return m,cells,inputs,outputs,origins,clones


def emit(m,cells,inputs,outputs,newtop):
    lines=['// Generated bounded native cell graph; see committed replication ledger.',
           'module '+newtop+'('+','.join(m['ports'])+');']
    for p,v in m['ports'].items():
        w=len(v['bits']);r='' if w==1 else '[%d:0] '%(w-1)
        lines.append(v['direction']+' wire '+r+p+';')
    wires=set();invs={}
    def bit(b):
        if isinstance(b,str):return "1'b"+b
        wires.add(b);return 'n%d'%b
    def edge(e):
        b,inv=e
        if not inv:return bit(b)
        if e not in invs:invs[e]='iv%d'%len(invs)
        bit(b);return invs[e]
    body=[]
    for p,v in m['ports'].items():
        if v['direction']=='input':
            for i,b in enumerate(v['bits']):
                pb=p if len(v['bits'])==1 else '%s[%d]'%(p,i)
                body.append('assign %s = %s;'%(bit(b),pb))
    for i,(n,c) in enumerate(cells.items()):
        pins=[]
        for p,bs in c['connections'].items():
            conn=[edge(e) for e in inputs[n][p]] if p in inputs[n] else [bit(b) for b in bs]
            val=conn[0] if len(conn)==1 else '{'+','.join(reversed(conn))+'}'
            pins.append('.%s(%s)'%(p,val))
        body.append('(* keep = 1, dont_touch = 1 *) %s c%d (%s);'%(c['type'],i,','.join(pins)))
    for p,bs in outputs.items():
        for i,e in enumerate(bs):
            pb=p if len(bs)==1 else '%s[%d]'%(p,i)
            body.append('assign %s = %s;'%(pb,edge(e)))
    lines.extend('wire n%d;'%b for b in sorted(wires))
    lines.extend('wire %s;'%v for v in invs.values())
    for i,((b,_),out) in enumerate(invs.items()):
        lines.append('(* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R inv%d (.A(%s),.Y(%s));'%(i,bit(b),out))
    lines+=body+['endmodule']
    return '\n'.join(lines)+'\n'


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('mapped_json');a.add_argument('--top',required=True)
    a.add_argument('--name',required=True);a.add_argument('--out',required=True)
    a.add_argument('--limit',type=int,default=24)
    a.add_argument('--clock-port',action='append',default=['clk'])
    a.add_argument('--incremental',action='store_true',help='update fanout worklist instead of rescanning every cell')
    a.add_argument('--budget-only',action='store_true',help='report resource/frontier only, emit no RTL')
    args=a.parse_args()
    raw=Path(args.mapped_json).read_bytes();d=json.loads(raw)
    try:
        m,c,i,o,origins,n=bound(d,args.top,args.limit,args.clock_port,incremental=args.incremental)
    except ReplicationFrontier as e:
        Path(args.out+'.blocked.json').write_text(json.dumps(e.report,indent=2)+'\n')
        print('SVC7_GRAPH BLOCKED '+json.dumps(e.report))
        raise SystemExit(2)
    if args.budget_only:
        report=dict(status='bounded graph exists; MODEL ONLY',clones=n,
                    original_cells=len(m['cells']),final_cells=len(c),limit=args.limit)
        Path(args.out+'.budget.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report));return
    text=emit(m,c,i,o,args.name)
    Path(args.out).write_text(text)
    ledger=dict(source_sha256=hashlib.sha256(raw).hexdigest(),
                output_sha256=hashlib.sha256(text.encode()).hexdigest(),
                source_top=args.top,output_top=args.name,limit=args.limit,
                original_cells=len(m['cells']),final_cells=len(c),clones=n,
                invariant='all clone primitive input functions/clock/reset identical to original; port functions identical',
                initialization='independent power-up requires separate reset/first-valid/capture proof; not established by this ledger',
                origins=origins)
    Path(args.out+'.ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print('SVC7_GRAPH clones=%d final_cells=%d structural_invariant=PASS'%(n,len(c)))


if __name__=='__main__':main()
