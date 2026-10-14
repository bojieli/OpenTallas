import sys,json
from pathlib import Path
sys.path.insert(0,'tools'); import check_macro_track_alignment as C
D=Path('physical/hbm_accel_die_views/candidate_audit_1013/attention_track_repair')
new=C.parse_lef((D/'hbm_half_repaired.lef').read_text())
for m in new:
 r=C.audit_macro(m,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)
 assert all(not v['no_legal_origin'] for v in r['summary'].values())
 assert all(v['same_layer_obs_overlap_or_within_spacing']==0 for v in r['pin_checks'].values())
 assert all(not v['below_min_width'] and not v['below_min_area'] for v in r['pin_checks'].values())
old=C.parse_lef((D/'original_half_lo.lef').read_text())[0]
newlo=next(m for m in new if m['name']==old['name'])
assert [(p['name'],p['use']) for p in newlo['pins']]==[(p['name'],p['use']) for p in old['pins']]
# Actual rejected mutant: original source-derived contact geometry.
r=C.audit_macro(old,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)
assert r['summary']['M5']['no_legal_origin']==['R0','MX','MY','R180']
print('PASS exact14043contacts identity; uniformtrack/accesspreflight PASS; actual originalsource mutant REJECTED all4orientations')
