import odb,json,hashlib,gzip,re
from pathlib import Path
root=next(Path('/route').glob('work/orfs/results/asap7/*/base'))
def read(path):
 d=odb.dbDatabase.create();odb.read_db(d,str(path));return d,d.getChip().getBlock()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(b):
 return {'instances':[(i.getName(),i.getMaster().getName(),i.getOrigin(),str(i.getOrient()),str(i.getPlacementStatus()),i.isDoNotTouch()) for i in b.getInsts()], 'signal':[(i.getName(),t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for i in b.getInsts() for t in i.getITerms() if str(t.getMTerm().getSigType()) not in ('POWER','GROUND')], 'pg':{(i.getName(),t.getMTerm().getName()):(t.getNet().getName() if t.getNet() else None) for i in b.getInsts() for t in i.getITerms() if str(t.getMTerm().getSigType()) in ('POWER','GROUND')},'bterms':[(t.getName(),t.getNet().getName() if t.getNet() else None) for t in b.getBTerms()]}
orig=root/'6_final.odb'; spef=root/'6_final.spef'
d,b=read(orig);a=snapshot(b);odb.write_def(b,'/proof/source_before.def');del b,d
d,b=read(Path('/proof/source_order_clone.odb'));z=snapshot(b);odb.write_def(b,'/proof/source_after.def')
for key in ('instances','signal','bterms'):assert a[key]==z[key],key
changes=[(k,v,z['pg'][k]) for k,v in a['pg'].items() if v!=z['pg'][k]]
assert len(changes)==644 and len({k[0] for k,_,_ in changes})==322
assert all(old is None and new in ('VDD','VSS') for _,old,new in changes)
# Full native serialization matches the independently reviewed clone, so all
# route geometry and signal DEF token invariants from 39021a45e carry exactly.
ref=Path('/reference/after.def.gz')
assert Path('/proof/source_after.def').read_bytes()==gzip.open(ref,'rb').read()
assert sha(orig)=='851903b3ea016e159ac50862a1c80c5b3f4c6276e13df27789182736ce4e72c6'
assert sha(spef)=='a86653e98ff953e441f905ec66347cec4a7dd5cfb453b33f3903b59a8e2c29a2'
r={'status':'PASS','only_pg_metadata_changed':len(changes),'instances':322,'full_def_equals_reviewed_clone':True,'original_odb_sha256':sha(orig),'source_order_clone_odb_sha256':sha(Path('/proof/source_order_clone.odb')),'original_spef_sha256':sha(spef),'source_order_clone_def_sha256':sha(Path('/proof/source_after.def')),'native_pg_terms':len(z['pg'])}
Path('/proof/invariants.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
