import copy, hashlib, json, sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-head-tstart')
sys.path.insert(0,str(R/'code/die_plan'))
import gen_rtl as G
O=Path('/srv/opentallas-scratch2/claude/codex-head-land3/land')
W=Path('/srv/opentallas-scratch2/claude/wt/codex-head-land3')
a=json.loads((R/'input/landed_lat_ft.json').read_text()); b=json.loads((R/'landed_lat_ft_tstart.json').read_text());side=json.loads((R/'input/landed_sidecar.json').read_text())
G.write_rtl(a,R/'gen_before',rtl_root=W,plan_path=str(O/'landed_lat_ft.json'),landing=side)
G.write_rtl(b,R/'gen_after',rtl_root=W,plan_path=str(O/'landed_lat_ft.json'),landing=side)
files=sorted((R/'gen_before').glob('*.sv'))
hashes={};bad=[];vs_parent=[]
for f in files:
 x=f.read_bytes();y=(R/'gen_after'/f.name).read_bytes()
 if x!=y:bad.append(f.name)
 hashes[f.name]=hashlib.sha256(y).hexdigest()
 p=O/'gen'/f.name
 if not p.is_file() or p.read_bytes()!=y:vs_parent.append(f.name)
receipt=dict(schema='opentallas.head_tstart_rtl.v1',files=len(files),changed_before_after=bad,diff_vs_parent_live_generated=vs_parent,sha256=hashes)
(R/'rtl_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='sha256'}))
if bad or vs_parent:sys.exit(1)
