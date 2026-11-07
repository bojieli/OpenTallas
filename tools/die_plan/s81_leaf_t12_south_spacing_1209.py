#!/usr/bin/env python3
"""Private t12 SOUTH spacing/rehome model. West reform is explicitly unresolved.
Defaults preserve bytes. Never apply to the original placed/live kit.
"""
import argparse, hashlib, json, re
from pathlib import Path
SOUTH={
 'u_cland_ft5_i':([39.582,49.005,184.698,72.765],[39.582,17.325,184.698,41.085]),
 'u_cland_ft6_i':([979.392,30.24,1008.156,64.8],[979.392,17.28,1008.156,51.84]),
}
def transform(text, enabled=False):
 if not enabled:return text
 for prefix,(old,new) in SOUTH.items():
  a=prefix+' {'+' '.join(f'{x:.5f}' for x in old)+'}'
  b=prefix+' {'+' '.join(f'{x:.5f}' for x in new)+'}'
  assert text.count(a)==1, 'exact t12 band changed: '+prefix
  text=text.replace(a,b)
 anchor='  set pinx [cland_place_pinslot_col $ordered $rect $xt $ppins $rev $psp 1]'
 assert text.count(anchor)==1,'deployed +ff N/S call changed'
 repl='  set codex_s_rows [expr {$prefix in {u_cland_ft5_i u_cland_ft6_i} ? 2 : 1}]\n  set pinx [cland_place_pinslot_col $ordered $rect $xt $ppins $rev $psp $codex_s_rows]'
 return text.replace(anchor,repl)
def main():
 p=argparse.ArgumentParser();p.add_argument('kit',type=Path);p.add_argument('--south-rehome-rows2',action='store_true');p.add_argument('--apply',action='store_true');a=p.parse_args()
 cfg=(a.kit/'config.mk').read_text();f=a.kit/'landing_placement.tcl';s=f.read_text()
 assert 'export DESIGN_NAME = s81p_ot_s81sl_leaf__t12' in cfg,'exact type only'
 assert re.search(r'^export OT_TAP_MAX_SINKS = 3000$',cfg,re.M)
 assert re.search(r'^export OT_TAP_WINDOW = 180.0000$',cfg,re.M)
 assert re.search(r'^export OT_CLAND_PINSLOT = 1$',cfg,re.M)
 out=transform(s,a.south_rehome_rows2)
 d={'profile':'s81_leaf_t12_south_spacing_1209','enabled':a.south_rehome_rows2,'scope':['S ft5_i','S ft6_i'],'west_changed':False,'west_reform_unresolved':True,'config_changed':False,'pins_changed':False,'clock_hooks_changed':False,'native_poses_changed':False,'rtl_changed':False,'pin_cycles_added':0,'root_assignment_claim':'tap ports/config unchanged; final cap-pass mapping NOT proven','source_landing_sha256':hashlib.sha256(s.encode()).hexdigest(),'result_landing_sha256':hashlib.sha256(out.encode()).hexdigest(),'new_bands':{k:v[1] for k,v in SOUTH.items()} if a.south_rehome_rows2 else {},'pilot_ready':False,'reason':'requires coordinator review and cap-map/fixed-site budget; S/W cohort remains held'}
 print(json.dumps(d,indent=2))
 if a.apply:
  assert not list(a.kit.glob('run/results/**/3_place.odb')),'do not mutate original placed/live kit; fresh owned snapshot only'
  f.write_text(out);(a.kit/'SOURCE_PROFILE_T12_SOUTH.json').write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
