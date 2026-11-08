#!/usr/bin/env python3
import ast,copy,hashlib,json,os,re,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from signed_child_evidence import stage_signed_child_evidence
M='ot_hbm_svc_sm_xcal_rel_t'; V=R/'sealed_xcal'; O=R/'macros'
O.mkdir(exist_ok=True)
for n in [f'{M}_tt.lib',f'{M}_ff.lib',f'{M}.lef']:
 d=(V/n).read_bytes();p=O/n
 if p.exists() and p.read_bytes()!=d:raise ValueError('refusing overwrite '+str(p))
 p.write_bytes(d)
a=stage_signed_child_evidence(V,M,O)
ns=dict(Path=Path,hashlib=hashlib,json=json,os=os,FLOW_TAG_ENV='OT_FLOW_TAG')
s=R/'signoff_source.py';tree=ast.parse(s.read_text());keep={'_sha_file','_child_view_provenance','signed_child_etm'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in keep],type_ignores=[]),str(s),'exec'),ns)
qs=[]
for c in ['tt','ff']:
 p=O/f'{M}_{c}.lib';qs.append(ns['signed_child_etm'](dict(master=M,liberty=str(p),liberty_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),'flow-20261107-ed-hbm'))
ps=dict(PIN_TOL_NM=200,GRID_NM=1)
s=R/'release_tree_source.py';tree=ast.parse(s.read_text());keep={'_nm','canon_pin_rows','_inside','pin_compare'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in keep],type_ignores=[]),str(s),'exec'),ps)
cp=ps['pin_compare'](ps['canon_pin_rows'](json.loads((V/'pins.json').read_text())),ps['canon_pin_rows'](json.loads((R/'expected_pins.json').read_text())))
if any(cp[k] for k in ['moved','extra','missing']):raise ValueError('planned pin identity failed '+str(cp))
lef=(V/f'{M}.lef').read_text();size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef)
actual=list(map(float,size.groups()));expected=json.loads((R/'selection.json').read_text())['hard_cores'][0]['outline_um']
assert actual==expected,(actual,expected)
print(json.dumps(dict(scope='METADATA_AND_INPUT_IDENTITY_ONLY_NOT_STA_NOT_TYPE_READY',portable=a,qualification=qs,pins={k:len(v)for k,v in cp.items()},outline=actual,tool_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'signed_child_evidence.py',R/'signoff_source.py',R/'release_tree_source.py']}),indent=2))
