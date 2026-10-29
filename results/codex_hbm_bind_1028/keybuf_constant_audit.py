"""Audit actual NP4 source straps with the shared conservative constant evaluator.
This is a diagnostic; shared Graph hook and physical frontdoor must be adopted separately.
"""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import bind as B,bind_elab as E
abpath,manifest,out=map(Path,sys.argv[1:]);ab=json.loads(manifest.read_text())
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():ab['map_file']=str(manifest.parent/ab['map_file'])
F=E.flatten(json.loads(abpath.read_text()),ab['top']);errors=[]
g=B.Graph(F,B.Rules(ab),errors)
expected={x['source_path']:x for x in json.loads(Path(__file__).with_name('keybuf_active_map.json').read_text())['active']}
rows=[]
for c in F.cells:
    if c.module!='ot_hnx_idxn_keybuf_slice':continue
    e=expected[c.path];up=[g.source(n) for n in c.ports['strap_lane_id']]
    value=sum((v[1]=='1') << i for i,v in enumerate(up)) if all(v[0]=='const' and v[1] in ('0','1') for v in up) else None
    rows.append(dict(path=c.path,expected=e['pbase']+e['lane'],value=value,source_bits=up,pass_value=value==e['pbase']+e['lane']))
record=dict(schema='opentallas.hbm.keybuf_actual_constant_audit.v1',rows=rows,pass_all=len(rows)==16 and all(x['pass_value'] for x in rows),errors=errors,note='Proposed constant evaluator diagnostic only; no runtime inputs converted, physical frontdoor adoption remains separate.')
out.write_text(json.dumps(record,indent=2)+'\n');print('actual16sliceconstant audit',record['pass_all']);sys.exit(0 if record['pass_all'] else 1)
