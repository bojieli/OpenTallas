"""Fail closed unless this exact kit still matches its already EQUIVALENT native proof."""
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);r=json.load(open(k/'lec/native_cache.json'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT','native proof is not EQUIVALENT'
for group,names in r['inventories'].items():
 actual=sorted(str(p.relative_to(k)) for p in (k/group).rglob('*') if p.is_file())
 assert actual==names,('changed complete inventory',group)
for name,digest in r['files'].items():
 assert (k/name).is_file() and h(k/name)==digest,('changed native proof input',name)
print('NATIVE_CACHE_EQ complete RTL/macros/reset/config/freeze/formal/netlist identity verified; physical gates rerun')
