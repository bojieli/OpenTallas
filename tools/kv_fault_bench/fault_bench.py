#!/usr/bin/env python3
"""Functional fault-plane qualification; transport delays are NOT CDC qualification."""
import argparse, copy, hashlib, json, re, subprocess
from pathlib import Path


def normalize(plan):
    sources = plan['sources']
    ops = []
    ids = {s['id'] for s in sources}
    if len(ids) != len(sources):
        raise ValueError('duplicate source ID')
    pending = copy.deepcopy(plan.get('transports', []) + plan['nodes'])
    for n in pending:
        if 'source' in n:
            n.update(a=n.pop('source'), kind='pipe', latency=n.pop('latency_cycles'))
        n['latency'] = n.get('latency', 1)
    known = ids | {n['id'] for n in ops}
    while pending:
        ready = [n for n in pending if all(n[p] in known or (n['kind']=='sticky' and n[p]==n['id']) or n[p] in ('0', "1'b0") for p in ('a','b') if p in n)]
        if not ready:
            raise ValueError('unresolved/cyclic references: '+str([n['id'] for n in pending]))
        for n in ready:
            if n['id'] in known or n['kind'] not in ('join','sticky','pipe') or n['latency'] < 1:
                raise ValueError('invalid node '+str(n))
            if n['kind'] != 'pipe' and n['latency'] != 1:
                raise ValueError('join/sticky latency must be one')
            known.add(n['id']); ops.append(n); pending.remove(n)
    sink = plan.get('sink', plan.get('root'))
    if isinstance(sink, dict): sink = sink['id']
    if sink not in known:
        raise ValueError('unknown sink '+str(sink))
    # Sink stickiness must be explicit, preventing accidental latency changes.
    if not any(n['id']==sink and n['kind']=='sticky' for n in ops):
        raise ValueError('sink must name an explicit sticky node')
    return sources, ops, sink


def path_latencies(sources, ops, sink):
    """Independent graph propagation: every source must reach the final sink."""
    paths = {s['id']: {s['id']: 0} for s in sources}
    paths['0'] = {}; paths["1'b0"] = {}
    for n in ops:
        d = {}
        for p in ('a','b'):
            for s, latency in paths.get(n.get(p), {}).items():
                d[s] = max(d.get(s, 0), latency+n['latency'])
        paths[n['id']] = d
    missing = {s['id'] for s in sources} - paths[sink].keys()
    if missing: raise ValueError('missing source coverage: '+str(sorted(missing)))
    return paths[sink]


def generate(plan, output, mutant='none'):
    sources, ops, sink = normalize(plan)
    latencies = path_latencies(sources, ops, sink)
    bound = max(latencies.values())
    quiet = plan.get('retirement_quiet_cycles', bound+2)
    if quiet < bound:
        raise ValueError(f'retirement quiet window {quiet} below leaf bound {bound}')
    names = [s['id'] for s in sources]+[n['id'] for n in ops]
    idx = {x:i for i,x in enumerate(names)}
    width = len(names)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    # A cycle-exact software machine supplies node-level expected values. An
    # independent graph latency bound checks source coverage and retirement.
    state = {n['id']: [0]*n['latency'] for n in ops}
    rows = []; case = 0
    held = set()
    def tick(active=(), reset=False):
        if reset: held.clear()
        else: held.update(s['id'] for s in sources if s.get('sticky',False) and s['id'] in active)
        before = {s['id']: int(not reset and (s['id'] in active or s['id'] in held)) for s in sources}
        before.update({k:v[-1] for k,v in state.items()}); before['0']=0; before["1'b0"]=0
        for n in ops:
            v = before[n['a']] | before.get(n.get('b'), 0)
            if n['kind']=='sticky': v |= before[n['id']]
            state[n['id']] = [0]*n['latency'] if reset else [v]+state[n['id']][:-1]
        expected = {s['id']:before[s['id']] for s in sources}
        expected.update({k:v[-1] for k,v in state.items()})
        stimulus = sum(before[s['id']] << i for i,s in enumerate(sources))
        word = sum(expected[k] << i for k,i in idx.items())
        rows.append(f'{int(not reset):x} {stimulus:x} {word:x} {case:x}\n')
        return expected[sink]
    tick(reset=True)
    for s in sources:
        case += 1; tick(reset=True)
        # Single-edge pulse, then quiet long enough for the slowest path.
        tick([s['id']])
        seen = False
        for _ in range(quiet): seen |= bool(tick())
        if not seen: raise AssertionError('golden missed '+s['id'])
        for _ in range(3):
            if tick()!=1: raise AssertionError('sink lost sticky fault')
        tick(reset=True)
        for _ in range(quiet):
            if tick()!=0: raise AssertionError('retirement quiet window contaminated')
    case += 1
    for _ in range(quiet): tick([s['id'] for s in sources])
    for _ in range(quiet): tick()
    tick(reset=True)
    for _ in range(quiet): tick()
    # Reset in flight must erase both the pipeline and source feedback cells.
    case += 1; tick([s['id'] for s in sources]); tick(reset=True)
    for _ in range(quiet):
        if tick()!=0: raise AssertionError('in-flight reset failed')
    (output/'vectors.txt').write_text(''.join(rows))
    wires = [f'wire [{width-1}:0] q;']
    for i,s in enumerate(sources): wires.append(f'assign q[{i}] = src[{i}];')
    def ref(x):
        if x in ('0', "1'b0", None): return "1'b0"
        if x == sources[0]['id'] and mutant=='missingfold': return "1'b0"
        if x == sources[0]['id'] and mutant=='duplicate_wrongbranch': return f'q[{idx[sources[1]["id"]]}]'
        return f'q[{idx[x]}]'
    for ni,n in enumerate(ops):
        prev = ref(n['a'])
        for j in range(n['latency']):
            dest = f'q[{idx[n["id"]]}]' if j==n['latency']-1 else f'p_{ni}_{j}'
            if j<n['latency']-1: wires.append(f'wire {dest};')
            b = f'q[{idx[n["id"]]}]' if n['kind']=='sticky' else ref(n.get('b')) if n['kind']=='join' else "1'b0"
            wires.append(f'qkd_astk_fault_join u_{ni}_{j}(.ck(ck),.rst_n(rst_n),.a({prev}),.b({b}),.q({dest}));')
            prev = dest
    text = '''module tb;
reg ck=0,rst_n=1;
reg [NS-1:0] src=0;
WIRES
integer f,r,cycle=0,case_id; reg [W-1:0] expected; reg reset_value;
initial begin
 f=$fopen("vectors.txt","r"); if(!f) $fatal(1,"vectors missing");
 while (!$feof(f)) begin
  r=$fscanf(f,"%h %h %h %h\\n", reset_value,src,expected,case_id);
  if(r==4) begin
   rst_n=reset_value; #2;
   if (!rst_n && q !== expected) $fatal(1,"ASYNC_CLEAR_MISMATCH cycle=%0d",cycle);
   ck=1; #2;
   if(q !== expected) $fatal(1,"FAULT_MISMATCH cycle=%0d case=%0d got=%h expected=%h",cycle,case_id,q,expected);
   ck=0; #2; cycle=cycle+1;
  end
 end
 $display("FAULT_PLANE_PASS cycles=%0d sources=NS quiet=QUIET",cycle); $finish;
end
endmodule
'''.replace('NS',str(len(sources))).replace('WIRES','\n'.join(wires)).replace('W-1',str(width-1)).replace('QUIET',str(quiet))
    if mutant != 'none':
        text = text.replace('if(q !== expected)', f'if(q[{idx[sink]}] !== expected[{idx[sink]}])')
    (output/'tb.sv').write_text(text)
    meta = dict(source_count=len(sources),node_count=len(ops),cycles=len(rows),quiet_cycles=quiet,max_leaf_latency=max(latencies.values()),latencies=latencies,mutant=mutant,qualification='logical topology only; fixed-cycle transports do not qualify CDC or physical lanes',plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest())
    (output/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta


def fixture(n=340):
    sources=[dict(id=f's{i}',sticky=i>=4,requires_sticky_latch=i<4) for i in range(n)]
    transports=[dict(id=f't{i}',source=f'kc{i}' if i<4 else f's{i}',latency_cycles=1+i%5) for i in range(n)]
    nodes=[dict(id=f'kc{i}',a=f's{i}',b=f'kc{i}',kind='sticky',latency=1) for i in range(4)]; level=[f't{i}' for i in range(n)]; k=0
    while len(level)>1:
        nxt=[]
        for i in range(0,len(level),2):
            name=f'j{k}'; k+=1
            nodes.append(dict(id=name,a=level[i],b=level[i+1] if i+1<len(level) else '0',kind='join',latency=1)); nxt.append(name)
        level=nxt
    nodes.append(dict(id='sink',a=level[0],kind='sticky',latency=1))
    return dict(sources=sources,transports=transports,nodes=nodes,sink='sink')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--plan'); p.add_argument('--out',required=True); p.add_argument('--mutant',choices=['none','missingfold','duplicate_wrongbranch'],default='none'); p.add_argument('--fixture',action='store_true'); a=p.parse_args()
    plan=fixture() if a.fixture else json.loads(Path(a.plan).read_text())
    print(json.dumps(generate(plan,a.out,a.mutant),sort_keys=True))
