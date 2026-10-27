"""Apply the measured, visually reviewed E2 capture placement policy to an own copy.

Parent source kit: d39b145d46575c843e4ba2f175a2199a16708355, hash53c75b470162949e.
Only placement changes. RTL, port geometry, reset, clock target and cycles remain.
"""
from pathlib import Path
import hashlib,json,sys
k=Path(sys.argv[1]);commit=sys.argv[2];hook=Path(__file__).with_name('e2_reach.tcl').read_bytes()
(k/'e2_reach.tcl').write_bytes(hook)
p=k/'face_flops_release.tcl';s=p.read_text()
if 'source /work/e2_reach.tcl' not in s:p.write_text(s+'\nsource /work/e2_reach.tcl\n')
f=json.load(open(k/'freeze.json'));old=f['kit_hash']
f.update(source_commit=commit,kit_hash=hashlib.sha256((old+'\0').encode()+hook).hexdigest()[:16])
f['placement_successor']=dict(parent_source='d39b145d46575c843e4ba2f175a2199a16708355',parent_kit_hash=old,hook_sha256=hashlib.sha256(hook).hexdigest(),cause='c_in capture SW to g_ft3 NE r2r409.536um>405',cycles_added=0)
(k/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
