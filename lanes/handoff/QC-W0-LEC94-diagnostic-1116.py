import collections
exec(open('/out/actual_keys.py').read().split('L=m.Lec')[0])
L=m.Lec(g,gm,t,tm);log=[]
m.normalize_gold_elements(L,m.slang_elements(p/'gold.aliases.json'),log)
m.json_alias_keys(L,log,work=p)
m.slang_element_keys(L,log,work=p)
m.alias_arrays(L,log,work=p)
# Reproduce original saved renaming decisions exactly (name-only; every pair below still checked).
import re
bases=re.findall(r"^renamed: (\S+) ", (p/'lec.log').read_text(), re.M)
for base in bases:
 for key in list(L.tp):
  mm=m.IDX.match(key)
  if mm and mm.group(1)==base:
   new=base+'#t'+mm.group(2);L.tp[new]=L.tp.pop(key);L.tc[new]=L.tc.pop(key)
L.matched=sorted(set(L.gp)&set(L.tp));L.gonly=sorted(set(L.gp)-set(L.tp));L.tonly=sorted(set(L.tp)-set(L.gp))
profile=json.load((p/'hyp.json').open());rec=m.transfer_profile(L,profile,log)
k='ff:u_dut.u_u_exp0.u_exp.d_lo.g_line.line[126]'
e='ff:u_dut.u_u_exp0.u_exp.a_r.g_l.u.s1_err'
L.hyp['gold',k]=('const',0)
assert e+'#t[0]' in L.tp
L.hyp['gate',e+'#t[0]']=('eq','gold',e+'[0]',0)
b,kind=L.build()
f=json.load((p/'lec.json').open()); print(type(f['failing'][0]),str(f['failing'][0])[:400],flush=True)
# Target every formerly failed compare point plus two proposed invariants. All other hypotheses are saved original proved ones.
names=set()
for entry in f['failing']+f['unproven_points']:
 if isinstance(entry,str):names.add(entry)
 elif isinstance(entry,dict): names.add(entry.get('point',entry.get('name',entry.get('key',''))))
print('targetNames',list(names)[:2],flush=True)
names|={'hyp:gold:'+k,'hyp:gate:'+e+'#t[0]'}
selected=[(o,n) for o,n in zip(b.outs,b.onames) if n in names]
print('selected',len(selected),flush=True)
print('missing',sorted(names-set(b.onames)),flush=True)
assert len(selected)==96
b.outs=[o for o,n in selected];b.onames=[n for o,n in selected]
status=m.prove(b,Path('/out'),10000,log,tag='conditional_failed94_withcarry')
result=dict(scope='Diagnostic conditional induction on only original94 failures and two added hypotheses; not release LEC and no reset contract altered',status=status,counts=dict(collections.Counter(status.values())))
Path('/out/conditional94.json').write_text(json.dumps(result,indent=2)+'\n');Path('/out/conditional94.log').write_text('\n'.join(log));print(json.dumps(result['counts']))
