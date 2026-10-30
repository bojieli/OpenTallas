import json,re,subprocess
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030');out=Path(__file__).resolve().parent
m=json.loads(subprocess.check_output(['git','-C',str(root),'show','1f9fe3c3a:results/hbm_su_native_1030/native112_plan_map.json']))
rows=[x for x in m['rows']if'physical_source_PREP'in x];assert len(rows)==48
normal='ot_hnx_su_plain4__lid9_rst3';special='ot_hnx_su_plain4__7dd6a1bbbf47_rst3';common='ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__nocoll__native_bridge';specialbridge='ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44__nocoll__native_bridge'
fragment=dict(scope='PREP only, merge into EXACT current-native source plan after conflict checks; no current plan changed',asbuilt=dict(substitute={normal:dict(module=common,reason='Explicit full-native ABI TIE0 collision outputs, zero cycles'),special:dict(module=specialbridge,reason='Special id44 full-native ABI TIE0 collision outputs, zero cycles')},dissolve=[normal,special,common,specialbridge],substitute_inst=[],map=dict(parts={})),physical_updates=[],expected=dict(plain_cuts=48,const0_outputs=192,extra_cycles=0))
for r in rows:
 native=r['native_path'];physical=native+'.u_sub.u_phys';p=r['physical_source_PREP'];fragment['asbuilt']['substitute_inst'].append(dict(inst=re.escape(physical),module=p['module'],reason='Same68-port exact physical outline variant; no output removal here'))
 fragment['asbuilt']['map']['parts'][physical]=[r['part'],r['local']]
 fragment['physical_updates'].append(dict(part=r['part'],type=r['type'],local=r['local'],native_path=native,physical_path=physical,module=p['module'],pins_source=p['pins_source'],pins_sha256=p['pins_sha256'],TIE0_parent_outputs=p['explicit_native_TIE0']))
(out/'plan_fragment_PREP.json').write_text(json.dumps(fragment,indent=2)+'\n')
