import lec as E,json,hashlib
from pathlib import Path
w=Path('.'); log=[]
L=E.Lec(E.read_aig(w/'gold.aig'),E.read_map(w/'gold.map'),E.read_aig(w/'gate.aig'),E.read_map(w/'gate.map'))
r=json.loads((w/'lec.json').read_text());L.kit_reset_ports=r.get('kit_reset_ports',[])
E.normalize_gold_elements(L,E.slang_elements(w/'gold.aliases.json'),log)
for f in (E.json_alias_keys,E.slang_element_keys,E.alias_arrays):f(L,log,work=w)
E.relayout(L,log);E.renamed(L,log)
L.hyp={(s,k):tuple(h) for s,k,h in json.loads((w/'hyp.json').read_text())}
# Frozen cube records retain the exact binary codes of this one-hot FSM.
# This is a reconstruction candidate, accepted only by original byte identity.
groups={}
for sd,k,hyp in json.loads((w/'hyp.json').read_text()):
 if hyp[0]=='cube':groups.setdefault((hyp[1],tuple(hyp[2])),[]).append(hyp[3])
L.cons=[(side,list(keys),sorted(vals,key=lambda v:sum(b<<i for i,b in enumerate(v)))) for (side,keys),vals in groups.items()]
print('recovered_constraint_candidates',len(L.cons),flush=True)
m,kind=L.build();m.write(w/'rebuilt.aig')
(w/'names_candidate.json').write_text(json.dumps({'inames':m.inames,'onames':m.onames,'kind':kind}))
import pickle
with (w/'state_candidate.pkl').open('wb') as f:pickle.dump(L,f)

h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rec={'original':h(w/'miter.aig'),'rebuilt':h(w/'rebuilt.aig'),'equal':(w/'miter.aig').read_bytes()==(w/'rebuilt.aig').read_bytes(),'log':log,'outputs':len(m.outs),'inputs':m.ni}
(w/'rebuild.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec),flush=True)
if not rec['equal']:raise SystemExit(2)
(w/'names.json').write_text(json.dumps({'inames':m.inames,'onames':m.onames,'kind':kind}))
