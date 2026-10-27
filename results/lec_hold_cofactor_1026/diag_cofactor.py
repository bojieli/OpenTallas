import sys,json,collections
from pathlib import Path
sys.path.insert(0,sys.argv[1]); import lec as LC
out,work=Path(sys.argv[2]),Path(sys.argv[3]);work.mkdir(parents=True,exist_ok=True)
L=LC.Lec(LC.read_aig(out/'gold.aig'),LC.read_map(out/'gold.map'),LC.read_aig(out/'gate.aig'),LC.read_map(out/'gate.map'))
log=[]
LC.normalize_gold_elements(L,LC.slang_elements(out/'gold.aliases.json'),log)
LC.json_alias_keys(L,log,work=out);LC.slang_element_keys(L,log,work=out);LC.alias_arrays(L,log,work=out);LC.relayout(L,log);LC.renamed(L,log)
L.hyp={(sd,k):tuple(h) for sd,k,h in json.load(open(out/'hyp.json'))}
L.hyp[('gold','ff:u_dut.u_e.w_cgt[1]')]=('eq','gold','ff:u_dut.u_e.w_coh[0]',0)
print('loaded',len(L.hyp),flush=True)
tried={}
for rnd in range(12):
 before=dict(L.hyp)
 n=LC.structural_constant_closure(L,log)+LC.structural_twin_closure(L,log)+LC.structural_cofactor_pairs(L,log,tried)
 print('closures',rnd,n,flush=True)
 m,kind=L.build(with_compare=True,with_hyp=True)
 st=LC.prove(m,work,1000,log,tag='relay'+str(rnd))
 bad=[n for n,s in st.items() if s!='proved']; print('statuses',dict(collections.Counter(st.values())),flush=True)
 for n in bad:print('BAD',n,flush=True)
 hypbad=[n for n in bad if n.startswith(('hyp:','cons:'))]
 if not hypbad:break
 LC.drop_failed(L,[n for n in hypbad if n.startswith('cons:')])
 for n in hypbad:
  if n.startswith('hyp:'):
   _,sd,k=n.split(':',2);sd='both' if sd=='bothg' else sd;h=L.hyp.pop((sd,k),None)
   if h and h[0]=='eq':tried[(sd,k,h[2],h[3])]=1
 if L.hyp==before:break
(work/'log').write_text('\n'.join(log));(work/'hyp.json').write_text(json.dumps([[sd,k,h]for(sd,k),h in L.hyp.items()]))
