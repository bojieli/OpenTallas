#!/usr/bin/env python3
"""Correct six unrealized O slot bindings without changing intended geometry."""
import json,shutil,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];base=ROOT/'results/arch/hbm_release_r16_1021/planoM';out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));m=json.load(open(out/'corridor_model.json'));sm=dict(x.split('=') for x in (out/'slot_map.txt').read_text().strip().split(','));rows={r['instance']:r for r in m['placement_checks']};fix=[]
for n in ['refcfg_SW','refcfg_NW','cij_SW','cij_SE','cij_NW','cij_NE']:
 a=rows[n]['after'];sn='exact_o2_'+n;assert sn not in {s['name'] for s in g['slots']}
 g['slots'].append(dict(name=sn,cell=a['m'],kind='tile',parent='die',outline=dict(w=a['w'],h=a['h']),origin=dict(x=a['x'],y=a['y'],orient=a['o']),pins=[],pin_status='FACES_ONLY',notes='Exact current source/master/body, explicit instance slot-map. Old canonical slot has different contract ownership or stale footprint and is unused. No old source/view alias.'))
 sm[n]=sn;fix.append(dict(instance=n,new_slot=sn,actual_master=a['m'],actual_body=[a['w'],a['h']],intended_xy=[a['x'],a['y']]))
receipt=Path(sys.argv[2]);r=json.load(open(receipt));assert r['source']=='83d057be0' and r['realized']==67 and set(r['mismatch_instances'])=={x['instance'] for x in fix}
m['binding_correction']=dict(status='SIX_EXACT_SLOT_MAPS_REQUIRED_ACTUAL_POST_GEN_CHECK',base='83d057be0/O intended73; actual67',receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),fixes=fix,geometry_delta=0,source_delta=0,new_S2=0)
g['floorplan']['r16o_corridors']=m;g['floorplan']['selected_geometry_model']='r16o_corridors/corridor_model.json with O2 six exact slot bindings; historical model files are not selected'
for fn,d in [('grants_d4g.json',g),('corridor_model.json',m)]: (out/fn).write_text(json.dumps(d,indent=1)+'\n')
(out/'slot_map.txt').write_text(','.join(k+'='+v for k,v in sorted(sm.items()))+'\n');print('O2_EXACT_SIX_SLOT_BINDINGS geometry/source/S2delta0; actual73homecheck mandatory')
