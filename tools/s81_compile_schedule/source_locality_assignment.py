#!/usr/bin/env python3
"""Propose native non-FIELD homes from literal dataflow and actual FIELD homes.

This design pass uses no fixture addresses, programme prices or provider2L rule.
Its objective counts source dependency boundaries across physical stages, with
worst-case conditional FIELD alternatives. Unknown bit widths, clock/cycles,
physical native children and implementation costs remain explicit obligations.
It emits candidate assignments, never actual elaboration or executable evidence.
"""
from collections import Counter, defaultdict, deque
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())


def field_rows(path):
    rows={}
    with gzip.open(path,'rt') as f:
        for line in f:
            row=json.loads(line)
            if row['node'] in rows:raise ValueError('duplicate source FIELD home')
            rows[row['node']]=row
    return rows


def literal_graph(demand):
    """Conservative symbolic dependencies, retaining independent write bursts.

    A sequence of independent producers of one named tensor (W1/W3, WO_A
    fragments) stays a set until consumed. Read-modify-write creates a new
    version. Predicated writes retain old potential writers. Native bit ranges
    and conditional execution must refine this candidate before qualification.
    """
    nodes={};state={};edges=[];external=[];last_scope=None
    for n in demand['nodes']:
        if n.get('kind')!='instruction':continue
        ident=n['id'];ins=n['instruction']
        if ident in nodes:raise ValueError('duplicate literal instruction')
        nodes[ident]=n
        reads=ins.get('_reads',[]);writes=ins.get('_writes',[])
        if not isinstance(reads,list) or not isinstance(writes,list):raise ValueError('literal tensor names required')
        scope=n['scope']
        # Only H/SSX explicitly carry between model scopes. Reused temporary
        # names must not inherit unrelated previous-layer operand producers.
        if scope!=last_scope:
            state={k:v for k,v in state.items() if k in ('H','SSX')}
            last_scope=scope
        for tensor in reads:
            current=state.get(tensor)
            if current:
                for producer in sorted(current['writers']):
                    edges.append(dict(producer=producer,consumer=ident,tensor=tensor,
                                      bits=None,bandwidth=None,source='literal _reads/_writes version'))
                current['consumed']=True
            else:
                external.append(dict(consumer=ident,tensor=tensor,scope=scope,
                                     status='UNBOUND_NATIVE_BOOT_OR_PREVIOUS_PRODUCER'))
        for tensor in writes:
            old=state.get(tensor)
            independent=old and not old['consumed'] and tensor not in reads
            predicated=ins.get('pred',0) not in (None,0)
            writers=(set(old['writers']) if old and (independent or predicated) else set())|{ident}
            state[tensor]=dict(writers=writers,consumed=False)
    return nodes,edges,external


class Flow:
    """Integer max-flow for submodular alpha expansion; no external packages."""
    def __init__(self,n):self.g=[[] for _ in range(n)]
    def edge(self,a,b,c):
        if c<0:raise ValueError('negative cut capacity')
        self.g[a].append([b,c,len(self.g[b])]);self.g[b].append([a,0,len(self.g[a])-1])
    def cut(self,source,sink):
        sys.setrecursionlimit(max(10000,4*len(self.g)))
        total=0
        while True:
            level=[-1]*len(self.g);level[source]=0;q=deque([source])
            while q:
                a=q.popleft()
                for b,c,_ in self.g[a]:
                    if c and level[b]<0:level[b]=level[a]+1;q.append(b)
            if level[sink]<0:break
            pos=[0]*len(self.g)
            def send(a,cap):
                if a==sink:return cap
                while pos[a]<len(self.g[a]):
                    e=self.g[a][pos[a]];b,c,rev=e
                    if c and level[b]==level[a]+1:
                        f=send(b,min(c,cap))
                        if f:e[1]-=f;self.g[b][rev][1]+=f;return f
                    pos[a]+=1
                return 0
            while True:
                f=send(source,10**18)
                if not f:break
                total+=f
        reached={source};q=deque([source])
        while q:
            for b,c,_ in self.g[q.popleft()]:
                if c and b not in reached:reached.add(b);q.append(b)
        return total,reached


def optimise(variables,edges,unary,candidates):
    ids=sorted(variables);index={n:i for i,n in enumerate(ids)}
    adjacency=defaultdict(set)
    for a,b in edges:adjacency[a].add(b);adjacency[b].add(a)
    # Initialise by nearest actual FIELD anchor, using graph distance only for
    # initialisation. Equal-distance ties use actual stage identity.
    labels={};queue=deque()
    for n in ids:
        if n in unary:
            labels[n]=min(candidates,key=lambda s:(unary[n][s],s));queue.append(n)
    while queue:
        n=queue.popleft()
        for other in sorted(adjacency[n]):
            if other not in labels:labels[other]=labels[n];queue.append(other)
    anchored=set(labels);unbound=sorted(set(ids)-anchored)
    ids=[n for n in ids if n in anchored];index={n:i for i,n in enumerate(ids)}
    active_edges=[(a,b) for a,b in edges if a in index and b in index]
    def cost(lab):
        return sum(unary.get(n,{}).get(lab[n],0) for n in ids)+sum(lab[a]!=lab[b] for a,b in active_edges)
    initial=cost(labels);history=[initial]
    changed=True
    while changed:
        changed=False
        for alpha in candidates:
            count=len(ids);flow=Flow(count+2);source=count;sink=count+1
            d0=[2*unary.get(n,{}).get(labels[n],0) for n in ids]
            d1=[2*unary.get(n,{}).get(alpha,0) for n in ids]
            for a,b in active_edges:
                i,j=index[a],index[b]
                A=int(labels[a]!=labels[b]);B=int(labels[a]!=alpha);C=int(alpha!=labels[b]);D=0
                w=B+C-A-D
                d1[i]+=2*(C-A)-w;d1[j]+=2*(B-A)-w
                flow.edge(i,j,w);flow.edge(j,i,w)
            for i in range(count):
                floor=min(d0[i],d1[i]);d0[i]-=floor;d1[i]-=floor
                flow.edge(source,i,d1[i]);flow.edge(i,sink,d0[i])
            _,keep=flow.cut(source,sink)
            proposed={n:labels[n] if index[n] in keep else alpha for n in ids}
            new=cost(proposed)
            if new<cost(labels):labels=proposed;history.append(new);changed=True
    return labels,dict(objective='equal-weight symbolic interstage dependency boundaries',
        initial=initial,final=cost(labels),strict_improvements=history,algorithm='integer alpha-expansion graph cuts',
        global_optimum_proven=False,unanchored_operations=unbound)


def assign(demand,homes):
    nodes,edges,external=literal_graph(demand)
    fixed={}
    for ident,h in homes.items():
        if ident not in nodes:raise ValueError('FIELD home absent from actual literal source '+ident)
        if h['template_sha256']!=nodes[ident]['template_word_sha256']:raise ValueError('stale FIELD template '+ident)
        choices=[set(f['stage'] for f in c['fragments']) for c in h['canonical_choices']]
        if not choices or any(not c or any(type(s)!=int or not 0<=s<81 for s in c) for c in choices):
            raise ValueError('missing actual FIELD choice/stage')
        fixed[ident]=choices
    variables=set(nodes)-set(fixed);candidates=sorted({s for choices in fixed.values() for c in choices for s in c})
    if not candidates:raise ValueError('no actual FIELD anchors')
    unary=defaultdict(lambda:Counter({s:0 for s in candidates}));free_edges=[]
    for e in edges:
        a,b=e['producer'],e['consumer']
        if a in variables and b in variables:free_edges.append((a,b))
        elif (a in variables)!=(b in variables):
            variable,field=(a,b) if a in variables else (b,a)
            for s in candidates:
                # A FIELD operation can span multiple real stages, and runtime
                # expert choices stay alternatives. Never assume one expert.
                unary[variable][s]+=max(sum(t!=s for t in choice) for choice in fixed[field])
    labels,objective=optimise(variables,free_edges,unary,candidates)
    records=[]
    for ident in sorted(variables):
        n=nodes[ident];stage=labels.get(ident)
        for rank in range(4):
            records.append(dict(node=ident,template_sha256=n['template_word_sha256'],scope=n['scope'],
                unit=n['instruction']['unit'],semantic_tag=n['instruction'].get('_tag'),rank=rank,
                stage=stage,die_id=None if stage is None else 4*stage+rank,physical_instance=None,
                programme_id=None,core_epoch=None,start_cycle=None,duration_cycles=None,
                status='CANDIDATE_COMPILER_ASSIGNMENT_NOT_INSTANTIATED' if stage is not None else 'UNBOUND_NO_FIELD_ANCHOR'))
    return dict(schema='opentallas.s81.source-locality-candidate.v1',qualified=False,dispatch_eligible=False,
        native_instance_inventory=False,native_kernel_boundary_constraints_bound=False,
        MTP_continuation_bound=False,source_operation_homes=records,
        source_instruction_count=len(nodes),source_SU_instruction_count=sum(n['instruction']['unit']==2 for n in nodes.values()),
        actual_FIELD_anchor_operations=len(fixed),literal_dependency_edges=edges,unbound_symbolic_inputs=external,
        objective=objective,source_order_preserved=True,
        limitations=['Candidate compiler stage assignments only; physical_instance/programmes/coreepochs are NOT supplied.',
                    'Symbolic dependencies conservatively coalesce independent write bursts; actual bit ranges/predicates need native lowering.',
                    'Equal edge weights are not actual bit widths/bandwidths/clock or cycle costs.',
                    'Native fusion and equipment replication/capacity constraints are unbound; raw assignments may split existing fused kernels.',
                    'No package distance or cross-die latency is inferred from stage numbers.',
                    'Native leaf instantiation, storage/ports/capacity, exact programmes/global calendars and MTP remain mandatory.'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--demand',type=Path,required=True);ap.add_argument('--field-homes',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    result=assign(read(args.demand),field_rows(args.field_homes))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.demand,args.field_homes)}
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    args.out.write_bytes(gzip.compress(raw,mtime=0) if args.out.suffix=='.gz' else raw)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_operation_homes','literal_dependency_edges','unbound_symbolic_inputs')}))
if __name__=='__main__':main()
