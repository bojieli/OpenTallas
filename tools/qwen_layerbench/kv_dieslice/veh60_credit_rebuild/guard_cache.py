#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
D=Path(__file__).resolve().parent;d=json.loads((D/'cache_receipt.json').read_text());phase=sys.argv[1]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(8<<20),b''):h.update(x)
 return h.hexdigest()
assert sha(D/'b/tb_kvslice.sv')==d['candidate_tb_sha256']
for row in d['private_child_files']:
 assert sha(row['snapshot'])==row['sha256'],row['snapshot']
for row in d['child_precision']:
 assert sha(row['path'])==row['sha256'],row['path']
for row in d['unchanged_hdl_inputs']:
 assert sha(row['path'])==row['sha256'],row['path']
if phase=='make-plan':
 p=(D/'top_make_plan.log').read_text()
 assert '--hierarchical-child' not in p and 'hier_launch_verilator' not in p
 assert not re.search(r'(?:make|gmake).*\s-C\s+(?:\S*/)?Vkv3_',p),'child make was planned'
 # Any write output into a private child is forbidden, including accidental make recipes.
 for lib in json.loads((D/'child_libs.json').read_text()):
  directory=str(Path(lib).parent)
  assert not re.search(r'(?:-o|touch|rm|cp)\s+(?:\S*/)?'+re.escape(directory)+r'/',p),directory
if phase=='post':
 ct=[]
 for f in (D/'b/obj').glob('**/*Syms*.cpp'):
  q=re.findall(r'timeprecision\(([^)]*)\)',f.read_text())
  if q:assert q==['-15'],(f,q);ct.append(str(f))
 # Private child snapshot intentionally excludes CPPs. Child precision is inherited
 # from the pinned original 51 sources; new top constructor must be exactly1fs.
 assert len(ct)==1,ct
print('CACHE_GUARD_PASS',phase)
