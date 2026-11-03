"""Structural equivalence proof (DIE-KV-64): tie-in-type bind == parent-tied bind with every removed strap port replaced
by its constant. Per changed type module: body identical after (drop removed strap port decls, rename strap_X -> S_X,
drop the new parameter block); per die instance: old top tie value == new top parameter override == module default."""
import json,re,sys,glob,os,difflib
B,N=sys.argv[1],sys.argv[2]
def blocks(txt):
    out={}
    for m in re.finditer(r'\n    (\w+) (?:#\((.*?)\) )?(\w+) \((.*?)\n    \);', txt, re.S):
        mod,par,inst,body=m.groups()
        out[inst]=(mod,dict(re.findall(r'\.(S_\w+)\((\d+\'b[01]+)\)',par or '')),dict(re.findall(r'\.(strap_\w+)\((\d+\'b[01]+)\)',body)))
    return out
ot=blocks(open(B+'/rtl/qwen_kvsys_bound_top.sv').read()); nt=blocks(open(N+'/rtl/qwen_kvsys_bound_top.sv').read())
changed=[os.path.basename(f) for f in glob.glob(N+'/rtl/*.sv') if not f.endswith('_bound_top.sv') and open(f).read()!=open(B+'/rtl/'+os.path.basename(f)).read()]
res={}; ok=True
for f in sorted(changed):
    o=open(B+'/rtl/'+f).read(); n=open(N+'/rtl/'+f).read()
    mod=re.search(r'^module (\w+)',o,re.M).group(1)
    oports=dict((b,int(w)+1) for w,b in re.findall(r'\n\s*input wire \[(\d+):0\] (strap_\w+),',o))
    nports=set(re.findall(r'\n\s*input wire \[\d+:0\] (strap_\w+),',n))
    rem={s:w for s,w in oports.items() if s not in nports}
    params={nm:v for w,nm,v in re.findall(r"\n\s*parameter \[(\d+):0\] (S_\w+) = (\d+'b[01]+),?",n)}
    o2='\n'.join(l for l in o.split('\n') if not any(re.match(r'\s*input wire \[\d+:0\] '+s+',',l) for s in rem))
    for s in rem: o2=re.sub(r'\b'+s+r'\b','S_'+s[6:],o2)
    n2='\n'.join(l for l in n.split('\n') if not re.match(r"\s*parameter \[\d+:0\] S_\w+ = ",l))
    n2=n2.replace(f'module {mod} #(\n) (',f'module {mod} (')
    body=o2==n2
    pset=set(params)=={'S_'+s[6:] for s in rem}
    insts=[i for i,(m,_,_) in nt.items() if m==mod]
    vok=bool(insts)
    for i in insts:
        _,ov,_=nt[i]; _,_,oldties=ot[i]
        for s in rem:
            p='S_'+s[6:]
            vok &= oldties.get(s)==ov.get(p)==params.get(p)
    res[f]=dict(removed_strap_ports=len(rem),instances=len(insts),body_identical=body,params_exact=pset,values_equal_every_instance=vok)
    ok &= body and pset and vok
    if not body: print(f,'\n'.join(list(difflib.unified_diff(o2.split('\n'),n2.split('\n'),lineterm=''))[:10]))
# top: nothing else changed
for i in ot:
    if ot[i][0]!=nt.get(i,(None,))[0]: ok=False; print('instance module changed',i)
print('VERDICT','EQUIVALENT' if ok else 'FAIL',len(res),'types', sum(r['removed_strap_ports'] for r in res.values()),'ports', sum(r['instances'] for r in res.values()),'instances')
for f,r in sorted(res.items())[:3]: print(f,r)
json.dump(dict(verdict='EQUIVALENT' if ok else 'FAIL',types=res),open(os.path.dirname(os.path.abspath(N))+'/strap_tie_eq.json','w'),indent=1)
