"""Compositional unchanged-macro miter: all inputs compared, outputs shared.

This assumes common corresponding memory state (or complete prior reinstall),
then checks every request/clock/config pin and all RTL state/output relations.
It does not model SRAM initialization, physical timing, or a standard-cell FF.
"""
from pathlib import Path
import json,copy,hashlib,sys
p=Path(sys.argv[1] if len(sys.argv)>1 else 'miter.json');j=json.loads(p.read_text());m=j['modules']['equiv'];cs=m['cells'];typ='ot_sram_1r1w_64x512_m1_r2c2';golds={n[:-5].removesuffix('_proof_unique'):n for n,c in cs.items()if c['type']==typ and n.endswith('_gold')};gates={n[:-5].removesuffix('_proof_unique'):n for n,c in cs.items()if c['type']==typ and n.endswith('_gate')};assert golds.keys()==gates.keys()and len(golds)==2,(golds,gates)
bits=[b for c in cs.values()for bs in c['connections'].values()for b in bs if isinstance(b,int)];nbit=max(bits)+1
replace={};checks=[];pairs=[]
for idx,k in enumerate(sorted(golds)):
 ga,gb=golds[k],gates[k];a,b=cs[ga],cs[gb];rec=dict(gold=ga,gate=gb,type=typ,inputs={},shared_output_bits=0)
 assert a['port_directions']==b['port_directions']
 for pin,direction in a['port_directions'].items():
  av,bv=a['connections'][pin],b['connections'][pin];assert len(av)==len(bv)
  if direction=='input':
   rec['inputs'][pin]=len(av)
   for i,(x,y)in enumerate(zip(av,bv)):
    checks.append((f'macro{idx}_{pin}_{i}',x,y))
  elif direction=='output':
   out=list(range(nbit,nbit+len(av)));nbit+=len(av)
   m['ports'][f'macro_shared_{idx}_{pin}']=dict(direction='input',bits=out)
   for x,y,z in zip(av,bv,out):
    for old in [x,y]:
     assert isinstance(old,int)
     assert old not in replace or replace[old]==z
     replace[old]=z
   rec['shared_output_bits']+=len(out)
  else:raise RuntimeError('unexpected inout')
 del cs[ga];del cs[gb];pairs.append(rec)
for c in cs.values():
 for pn,v in c['connections'].items():c['connections'][pn]=[replace.get(x,x)for x in v]
for d in [m['ports'],m['netnames']]:
 for v in d.values():v['bits']=[replace.get(x,x)for x in v['bits']]
asserted=0;trivial=0
for label,x,y in checks:
 x,y=replace.get(x,x),replace.get(y,y)
 if x==y:trivial+=1;continue
 out=nbit;nbit+=1
 cs[label+'_cell']=dict(hide_name=0,type='$equiv',parameters={},attributes={'keep':'1'},port_directions={'A':'input','B':'input','Y':'output'},connections={'A':[x],'B':[y],'Y':[out]})
 m['netnames'][label]=dict(hide_name=0,bits=[out],attributes={'keep':'1'});asserted+=1
Path(sys.argv[2] if len(sys.argv)>2 else 'miter_macro_cut.json').write_text(json.dumps(j)+'\n')
Path(sys.argv[3] if len(sys.argv)>3 else 'macro_cut_certificate.json').write_text(json.dumps(dict(miter_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),paired_macro_count=2,pairs=pairs,macro_input_bits_compared=len(checks),statically_identical_input_bits=trivial,explicit_equivalence_cells=asserted,shared_arbitrary_read_bits=sum(p['shared_output_bits']for p in pairs),assumption='same unchanged corresponding macro state, or full prior reinstall; not arbitrary independent SRAM power-up',claim='all macro inputs incl clocks/config plus full head RTL relation; no physical timing/reset-glitch claim from async2sync'),indent=2)+'\n')
