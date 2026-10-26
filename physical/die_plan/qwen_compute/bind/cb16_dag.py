"""Align CB16 phases through legal upstream/crossing pads, without changing a hard tile.

The as-built reduction order is fixed. Intra-partition relations are equalities; existing R8 crossings permit
only additional nonnegative, whole-port delay. A longest-path difference-constraint solve gives the earliest
feasible phase at every actual fabric/leaf/node output. Positive cycles are rejected rather than inventing relays.
"""
import argparse,json,re
from pathlib import Path
from collections import defaultdict
ROOT='$epoch'

def load(bound,table):
    sinks=json.loads((bound/'bind_sinks.json').read_text());groups=json.loads((bound/'bus_groups.json').read_text())
    r8={m['id']:m for m in json.loads(table.read_text())['members']};asb={};gid=defaultdict(set)
    for g in groups['landing']:
        if not g['sink'].startswith('c16_'):continue
        for m in g['members']:
            sb=','.join(f'{a}:{b}' for a,b in m['sink_bits']);mid=f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m['asbuilt_stages']}"
            for a,b in m['sink_bits']:
                for bit in range(a,b+1):asb[g['sink'],m['sink_port'],bit]=m['asbuilt_stages']
            gid[g['sink'],m['sink_port']].add(mid)
    ports=defaultdict(lambda:defaultdict(set))
    for k,v in sinks.items():
        if not k.startswith('c16_') or v[0]!='pin':continue
        lp,bit=k.rsplit('[',1);leaf,p=lp.rsplit('.',1)
        if p in ('tile_id','rst_n','sidx') or 'tie' in v[1]:continue
        sl,sp=v[1].rsplit('[',1)[0].rsplit('.',1);a=asb.get((leaf,p,int(bit[:-1])))
        ports[leaf][p].add((sl,sp,0 if a is None else v[2]-a))
    inp={}
    for leaf,ps in ports.items():
        inp[leaf]={}
        for p,values in ps.items():
            if len(values)!=1:raise ValueError(f'incoherent driver/added phase {leaf}.{p}: {sorted(values)}')
            inp[leaf][p]=next(iter(values))
    return inp,gid,r8,groups

def build(inp,gid):
    nodes={ROOT};relations=[];seen=set()
    def signal(leaf,po):
        if not leaf.startswith('c16_') or leaf not in inp:return ROOT
        tile=bool(re.search(r'\.u_t_\d_\d$',leaf));key=leaf+'.'+(po if tile else '*')
        if key in seen:return key
        seen.add(key);nodes.add(key)
        if tile:ports=['tap'] if po=='t_out' else ['n_a','n_b']
        else:
            ports=list(inp[leaf])
            if len(ports)!=1:raise ValueError(f'unsupported multi-input fabric cone {leaf}: {ports}')
        for p in ports:
            if p not in inp[leaf]:raise ValueError(f'missing dependency {leaf}.{p} for {po}')
            sl,sp,off=inp[leaf][p];src=signal(sl,sp)
            relations.append(dict(src=src,dst=key,off=off,ids=sorted(gid.get((leaf,p),())),leaf=leaf,port=p))
        return key
    roots={}
    for leaf in sorted(inp):
        if not re.search(r'\.u_t_\d_\d$',leaf):continue
        signal(leaf,'t_out')
        if 'n_a' in inp[leaf] and 'n_b' in inp[leaf]:
            out=signal(leaf,'n_y')
            if leaf.endswith('.u_t_0_0'):roots[leaf.split('.')[0]]=out
    return nodes,relations,roots

def solve(nodes,relations):
    edges=[]
    for i,e in enumerate(relations):
        edges.append((e['src'],e['dst'],e['off'],i))
        if not e['ids']:edges.append((e['dst'],e['src'],-e['off'],i))
    d={n:-10**9 for n in nodes};d[ROOT]=0;pred={}
    for iteration in range(len(nodes)):
        changed=None
        for a,b,w,i in edges:
            if d[a]>-10**8 and d[b]<d[a]+w:d[b]=d[a]+w;pred[b]=(a,i,w);changed=b
        if changed is None:break
    if changed is not None:
        v=changed
        for _ in nodes:v=pred[v][0]
        start=v;cycle=[]
        while True:
            a,i,w=pred[v];cycle.append(dict(source=a,destination=v,weight=w,relation=relations[i]));v=a
            if v==start:break
        raise ValueError('infeasible fixed-edge phase cycle: '+json.dumps(cycle))
    if d[ROOT]!=0 or any(v<=-10**8 for v in d.values()):raise ValueError('epoch moved or unreachable phase')
    return d,iteration+1

def baseline(inp):
    cache={};busy=set()
    def sig(leaf,po):
        if leaf not in inp:return 0
        k=leaf,po
        if k in cache:return cache[k]
        if k in busy:raise ValueError('cycle in baseline dependency graph')
        busy.add(k);ps=inp[leaf]
        if re.search(r'\.u_t_\d_\d$',leaf):ports=['tap'] if po=='t_out' else [p for p in ('n_a','n_b') if p in ps]
        else:ports=list(ps)
        v=max((sig(ps[p][0],ps[p][1])+ps[p][2] for p in ports),default=0)
        busy.remove(k);cache[k]=v;return v
    return sig

def align(bound,table,out):
    if out.exists():raise ValueError(f'refuse to overwrite {out}')
    inp,gid,r8,groups=load(bound,table);nodes,rels,roots=build(inp,gid);phase,iterations=solve(nodes,rels);old=baseline(inp)
    members=[];requests={};pads=[]
    for e in rels:
        extra=phase[e['dst']]-phase[e['src']]-e['off']
        if extra<0 or (extra and not e['ids']):raise ValueError('illegal phase solution')
        if not extra:continue
        pads.append(dict(e,extra=extra))
        for mid in e['ids']:
            if mid not in r8:raise ValueError(f'crossing absent from original R8 table: {mid}')
            if mid in requests and requests[mid]!=extra:raise ValueError('one R8 member has conflicting extra delays')
            requests[mid]=extra
    for mid,extra in sorted(requests.items()):
        m=r8[mid];members.append(dict(m,pad=m['pad']+extra,landed=m['landed']+extra,tree_align=extra,
            why='CB16 DAG: preserve every intra-partition phase relation; delay only existing whole-port crossings'))
    delta={}
    for cluster,n in sorted(roots.items()):
        before=old(cluster+'.u_t_0_0','n_y');after=phase[n]
        if after<before:raise ValueError('alignment advanced a cluster output')
        delta[cluster]=dict(before=before,after=after,added=after-before)
    bits=lambda m:sum(b-a+1 for a,b in m['sink_bits'])
    summary=dict(nodes=len(nodes),relations=len(rels),iterations=iterations,members=len(members),clusters=len(delta),
        logical_pad_flops=sum(m['tree_align']*bits(m) for m in members),
        launch_inputs=sum(p['port']=='b_d' for p in pads),root_added_max=max(v['added'] for v in delta.values()),
        root_added_min=min(v['added'] for v in delta.values()))
    result=dict(schema='opentallas.die_plan.r8_landing.v1',die=groups['die'],kind='cb16_upstream_dag_align_pads',
        note=__doc__,r8_table=str(table),summary=summary,members=members,cluster_output_delta=delta,
        phase_relations=rels,signal_phase=phase,pad_inputs=pads,
        qualification='CANDIDATE: independently check phase/packet exactness, model/type budgets and current-source bind before adoption')
    out.write_text(json.dumps(result,indent=1)+'\n');return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bound',type=Path);p.add_argument('table',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args(argv);r=align(a.bound,a.table,a.out);print(json.dumps(r['summary']))
if __name__=='__main__':main()
