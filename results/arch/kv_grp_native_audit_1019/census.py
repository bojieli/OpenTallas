"""Read actual ODB logical-pin dump; BUF/INV-transparent endpoint census."""
import collections, hashlib, json, pathlib, re, sys
p=pathlib.Path(sys.argv[1]); nets=collections.defaultdict(list); cells=collections.defaultdict(list)
for line in p.read_text().splitlines():
    net,kind,inst,master,pin,direction=line.split('\t')
    row=(kind,inst,master,pin,direction,net)
    nets[net].append(row)
    if kind=='I': cells[inst].append(row)
def transparent(master): return bool(re.match(r'^(?:BUF|INV)x',master))
def drivers(rows): return [r for r in rows if (r[0]=='I' and r[4]=='OUTPUT') or (r[0]=='B' and r[4]=='INPUT')]
def sinks(rows): return [r for r in rows if (r[0]=='I' and r[4]=='INPUT') or (r[0]=='B' and r[4]=='OUTPUT')]
def endpoints(net):
    todo=[net]; seen=set(); ends=set()
    while todo:
        n=todo.pop()
        if n in seen: continue
        seen.add(n)
        for r in sinks(nets[n]):
            if r[0]=='I' and transparent(r[2]):
                todo.extend(x[5] for x in cells[r[1]] if x[4]=='OUTPUT')
            else: ends.add(r[:5])
    return ends
roots=[]; boundary=[]
for net,rows in nets.items():
    for r in drivers(rows):
        if r[0]=='I' and transparent(r[2]): continue
        role='input' if r[0]=='B' else ('ff' if 'DFF' in r[2] else 'macro' if r[2].startswith('ot_sram') else 'tie' if 'TIE' in r[2] else 'comb')
        if r[0]=='B' and r[1] in ('ck','hck'): role='clock'
        es=endpoints(net)
        roots.append(dict(driver=list(r[:5]),net=net,role=role,count=len(es),endpoints=[list(x) for x in sorted(es)]))
        if r[0]=='B':
            bad=[x for x in es if x[0]=='B' or ('DFF' not in x[2] and not (x[2].startswith('ot_sram') and x[3] in ('CLK','CK')))]
            boundary.append(dict(port=r[1],count=len(es),unregistered=len(bad),examples=[list(x) for x in sorted(bad)[:8]]))
summary={role:dict(roots=sum(x['role']==role for x in roots),max=max([x['count'] for x in roots if x['role']==role] or [0]),over32=sum(x['role']==role and x['count']>32 for x in roots)) for role in sorted(set(x['role'] for x in roots))}
out=dict(schema='kv_grp_actual_placed_transparent_census_v1',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),summary=summary,roots=sorted(roots,key=lambda x:-x['count']),boundary=boundary,qualified=False)
pathlib.Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(summary)); print('unregistered input ports',sum(x['unregistered']>0 for x in boundary))
