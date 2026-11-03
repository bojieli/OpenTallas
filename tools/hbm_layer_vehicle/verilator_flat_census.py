#!/usr/bin/env python3
"""Flattened Verilator census from --json-only output: instances and AST nodes per child and per module.

Usage: verilator_flat_census.py root.json  (diagnoses frontend memory explosions before V3Scope)."""
import json,sys,collections
d=json.load(open(sys.argv[1]))
mods={}; byaddr={}
def walk(n,acc):
    if isinstance(n,dict):
        acc['nodes']+=1
        t=n.get('type')
        if t=='CELL': acc['cells'].append((n.get('name'),n.get('modp')))
        if t=='VAR':
            # rough bit width unknown; count vars
            acc['vars']+=1
        for k,v in n.items():
            if isinstance(v,(list,dict)) and k not in ('modulesp',): walk(v,acc)
    elif isinstance(n,list):
        for x in n: walk(x,acc)
for m in d['modulesp']:
    acc={'nodes':0,'cells':[],'vars':0}
    walk(m.get('stmtsp',[]),acc)
    mods[m['addr']]=dict(name=m['name'],orig=m.get('origName'),**acc)
print('modules',len(mods))
top=d['modulesp'][0]['addr']
# flattened instance multiplicity
mult=collections.Counter(); 
memo={}
def flat(a):
    if a in memo: return memo[a]
    m=mods.get(a)
    if m is None: memo[a]=(1,0); return memo[a]
    inst=1; nodes=m['nodes']
    for _,c in m['cells']:
        i,n=flat(c); inst+=i; nodes+=n
    memo[a]=(inst,nodes); return memo[a]
ti,tn=flat(top)
print('flattened instances',ti,'flattened nodes',tn,'unflattened nodes',sum(m['nodes'] for m in mods.values()))
# per direct child of top
rows=[]
for nm,c in mods[top]['cells']:
    i,n=flat(c); rows.append((n,i,nm,mods.get(c,{}).get('name')))
rows.sort(reverse=True)
print('top own nodes',mods[top]['nodes'])
for n,i,nm,mn in rows[:25]: print(f'{n:>12} {i:>8} {nm} -> {mn}')
# multiplicity per module across flattened tree
cnt=collections.Counter()
def mul(a,k):
    cnt[a]+=k
    for _,c in mods.get(a,{'cells':[]})['cells']: mul(c,k)
sys.setrecursionlimit(100000)
mul(top,1)
agg=collections.Counter()
for a,k in cnt.items():
    m=mods.get(a)
    if m: agg[m['orig']]+=k*m['nodes']
print('--- flattened nodes by origName')
tot=sum(agg.values())
for o,v in agg.most_common(25): print(f'{v:>12} {100*v/tot:5.1f}% {o}  inst={sum(cnt[a] for a in cnt if mods.get(a,{}).get("orig")==o)}')
