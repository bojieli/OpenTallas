import re,json,hashlib,gzip
from pathlib import Path
A=Path('before.def').read_text();B=Path('after.def').read_text()
def without_sections(s):
 for n in ['NETS','SPECIALNETS']:
  s=re.sub(r'^'+n+r'\b.*?^END '+n+r'\s*$','<'+n+'>',s,flags=re.M|re.S)
 return s
assert without_sections(A)==without_sections(B)
x=json.load(open('metal_proof.json'));assert x['signal_net_records_identical'] and x['specialnet_geometry_unchanged'];x['entire_def_outside_nets_and_specialnets_identical']=True
Path('metal_proof.json').write_text(json.dumps(x,indent=2)+'\n')
for src in ['before.def','after.def','clone_native/raw.json']:
 p=Path(src)
 with p.open('rb') as fi,gzip.open(str(p)+'.gz','wb',compresslevel=6) as fo:
  while z:=fi.read(1024*1024):fo.write(z)
print('DEF_FULL_INVARIANTS_PASS')
