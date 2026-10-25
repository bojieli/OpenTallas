# Recreate the exact, already ABC-proved-hypothesis miter plus XOR provenance.
exec(open('parity_diag.py').read().split('# Exact finite check')[0])
s=open('engine_hyp.py').read().split('for rnd in range')[0]
exec(s)
import json,pathlib,hashlib
p=pathlib.Path('eng_crypto');p.mkdir(exist_ok=True)
m,_=L.build(with_compare=True,with_hyp=True);m.write(p/'r0.aig')
json.dump(m.onames,open(p/'names.json','w'));json.dump([[lit,list(ts),c] for lit,(ts,c) in m.expr.items()],open(p/'xor.json','w'))
print('aig_sha',hashlib.sha256((p/'r0.aig').read_bytes()).hexdigest(),'matches_prior', (p/'r0.aig').read_bytes()==pathlib.Path('eng_parity/r0.aig').read_bytes(),flush=True)
assert (p/'r0.aig').read_bytes()==pathlib.Path('eng_parity/r0.aig').read_bytes()
