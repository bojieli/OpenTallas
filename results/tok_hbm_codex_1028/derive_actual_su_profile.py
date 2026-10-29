import json,sys,importlib.util,re
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-bind-1028')
f=root/'tools/hbm_static/su_lane_build.py'
spec=importlib.util.spec_from_file_location('lane_build',f);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
a=json.load(open('/srv/opentallas-scratch2/claude/codex-hbm-bind-1028/elab_sourcefix/asbuilt.json'))
rows=[]
for n,m in a['modules'].items():
 if m.get('attributes',{}).get('hdlname')!='ot_hbm_su_static_pgslice_lg_s':continue
 p={k:int(v,2) for k,v in m['parameter_default_values'].items() if k in ('MLAT','ALAT','QID','G','LEAF','WCOPY')}
 ml,al=p['MLAT'],p['ALAT'];rows.append(dict(qid=p['QID'],group=p['G'],parameters=p,
  wcprop='WCOPY' in p,linear_emit_to_write=c.lin(ml,al,p['LEAF']),lane_depths=c.depths(ml,al),
  scalar_side_depths=c.depths(3,3),side_ii={str(fn):c.side_ii(fn,ml,al) for fn in c.SIDE_FN}))
rows.sort(key=lambda r:(r['qid'],r['group']))
expected=dict(mlat=5,alat=3,wcopy=1,leaf=1)
report=dict(status='CURRENT_BIND_KIT_PROFILE_MISMATCH',basis='actualYosys parameter_default_values on8parentparamods; compiler source su_lane_build; static derivation, notRTL/STA',
 actual_slices=rows,side_fixed=c.SIDE,side_reason='intentional mixed pipeline; compiler side_ii holds early scalar result until lane consumes',
 physical_target=expected,physical_linear_emit_to_write=c.lin(5,3,1),physical_lane_depths=c.depths(5,3),
 physical_side_ii={str(fn):c.side_ii(fn,5,3) for fn in c.SIDE_FN},
 mismatches=['8parents requestMLAT4/ALAT4 instead of kit5/3','actual_s aliases lackWCOPY; generated pinned-bank kitWCOPY1 cannot be selected fromparent'],
 remedy='ThreadWCOPY default0 through_s alias like currentunsplitparent, chooseper-slice5/3/1fromactualphysicalrecipe, regeneratebind+staticprogramme; keepSIDE3/3 unchanged')
print(json.dumps(report,indent=2))
