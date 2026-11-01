import lec,json,pickle
from pathlib import Path
b=Path(__file__).parent
L=lec.Lec(lec.read_aig(b/'gold.aig'),lec.read_map(b/'gold.map'),lec.read_aig(b/'gate.aig'),lec.read_map(b/'gate.map'))
log=[]
print('initial',len(L.matched),flush=True)
lec.normalize_gold_elements(L,lec.slang_elements(b/'gold.aliases.json'),log)
print('elements',len(L.matched),flush=True)
lec.json_alias_keys(L,log,work=b)
print('jsonalias',len(L.matched),flush=True)
lec.slang_element_keys(L,log,work=b)
print('slangelement',len(L.matched),flush=True)
# Array alias pass rekeys the 32 one-bit source-memory aliases in this real kit.
lec.alias_arrays(L,log,work=b)
print('arrays',len(L.matched),flush=True)
(b/'normalization.log').write_text('\n'.join(log)+'\n')
L.hyp={(s,k):tuple(h) for s,k,h in json.load(open(b/'hyp.json'))}
m,kind=L.build();print('baseline',m.ni,len(m.outs),len(m.ands)//2,flush=True)
with open(b/'state_normalized.pkl','wb') as f:pickle.dump((L,m,kind),f)
