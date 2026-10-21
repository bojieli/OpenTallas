#!/usr/bin/env python3
import json,shutil,hashlib
from pathlib import Path
D=Path(__file__).parent;out=D/'planpM';out.mkdir(exist_ok=True)
for p in (D/'plano2M').iterdir():
 if p.is_file():shutil.copyfile(p,out/p.name)
p=D.parent/'hbm_no_window_decomposition_1021/root_aware_model.json';r=json.load(open(p));m=json.load(open(out/'corridor_model.json'));g=json.load(open(out/'grants_d4g.json'));sm=dict(x.split('=') for x in (out/'slot_map.txt').read_text().strip().split(','));rows={x['instance']:x for x in m['placement_checks']}
for c in r['changed_bodies']:
 n=c['instance'];a=c['after'];sn='exact_p_'+n
 g['slots'].append(dict(name=sn,cell=a['m'],kind='tile',parent='die',outline={'w':a['w'],'h':a['h']},origin={'x':a['x'],'y':a['y'],'orient':a['o']},pins=[],pin_status='FACES_ONLY',notes='ROOT-reviewed9a23 diagnostic placement correction; original clocks/rootkeepouts fixed.'))
 sm[n]=sn
 if n not in rows:rows[n]=dict(instance=n,before=c['before'],after=a,fixed_body_overlaps=[],old_generated_SFR_contacts_require_actual_GEN_replan=[])
 rows[n]['after']=a
m['placement_checks']=list(rows.values());assert len(rows)==74
m['selected_root_aware_model']=dict(reviewed_source='9a23b4f8b',sha256=hashlib.sha256(p.read_bytes()).hexdigest(),local_changed_bodies=11,all_targets=74,root_ownership_changes=0,global_fit_qualified=False,scope='DIAGNOSTIC GEN/PQ/S4 ONLY; all45 physical clock constraints OPEN; no S5/route/clock qualification')
g['floorplan']['r16o_corridors']=m;g['floorplan']['selected_geometry_model']='planpM/corridor_model.json ROOT-reviewed9a23 diagnostic only'
for fn,data in [('grants_d4g.json',g),('corridor_model.json',m)]: (out/fn).write_text(json.dumps(data,indent=1)+'\n')
(out/'slot_map.txt').write_text(','.join(k+'='+v for k,v in sorted(sm.items()))+'\n')
assert (out/'d4g_region_map.json').read_bytes()==(D/'plano2M/d4g_region_map.json').read_bytes()
print('MODEL_P 74targets/11localbodyrootclear; same source/S2/clockownership; diagnostic only')
