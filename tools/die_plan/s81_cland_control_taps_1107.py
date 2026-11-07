#!/usr/bin/env python3
"""Opt-in t36 control/selector clock groups; payload storage stays nearest-tap."""
import argparse, hashlib, json, re
from pathlib import Path
GROUP_RE = r'^u_bound[.](u_cland_[A-Za-z0-9_]+)[./](?!u_ring[.]s_d)'
p = argparse.ArgumentParser(); p.add_argument('kit', type=Path); p.add_argument('--apply', action='store_true'); p.add_argument('--north-face-rows', type=int, choices=(1,2), default=1); p.add_argument('--east-spacing', type=float, choices=(1.0,1.25), default=1.0); a=p.parse_args()
f=a.kit/'config.mk'; s=f.read_text(); before=hashlib.sha256(s.encode()).hexdigest()
assert 'OT_TAP_GROUP_RE' in (a.kit/'clock_taps.tcl').read_text(), 'kit lacks the existing group hook'
for key,val in [('OT_TAP_MAX_SINKS','1500'),('OT_TAP_TARGET_PS','250'),('OT_TAP_WINDOW','140.0000')]:
 m=re.search(r'^export '+key+r' = (\S+)',s,re.M); assert m and m[1]==val,(key,m[1] if m else None)
assert not re.search(r'^export OT_TAP_FOLLOW_RE\s*=',s,re.M), 'source follower override requires review'
assert not re.search(r'^export OT_TAP_GROUP_RE\s*=',s,re.M), 'profile already present or source changed'
s += '\n# CODEX S81 control-only CLAND grouping: preserve payload clocks and all contracts.\nexport OT_TAP_GROUP_RE = '+GROUP_RE+'\nexport OT_TAP_FOLLOW_RE =\n'
# Row depth is opt-in, physical spacing only; all ports/RTL/windows remain unchanged.
lf=a.kit/'landing_placement.tcl'; old_landing=lf.read_text()
anchor='set pinx [cland_place_pinslot_col $ordered $rect $xt $ppins $rev $psp 1]'
new_landing=old_landing
if a.east_spacing == 1.25:
 # Exact two E-facing ring bands only: retain E edge, y extents, pins, order and all occupancy checks.
 for old,new in [('u_cland_ft0_i {1401.84000 17.28000 1425.60000 246.10800}', 'u_cland_ft0_i {1395.90000 17.28000 1425.60000 246.10800}'),
                 ('u_cland_ft1_i {1404.00000 247.29600 1425.60000 487.26000}', 'u_cland_ft1_i {1398.60000 247.29600 1425.60000 487.26000}')]:
  assert new_landing.count(old)==1, 'E band source geometry changed'
  new_landing=new_landing.replace(old,new)
 yanchor='  lassign [cland_place_pinslot $ordered $rect $tag $sp $ppins $rev $ypsp] na nr how'
 assert new_landing.count(yanchor)==1, 'E pinslot source changed'
 new_landing=new_landing.replace(yanchor,'  if {$prefix in {u_cland_ft0_i u_cland_ft1_i}} {set ypsp [expr {$ypsp*1.25}]}\n'+yanchor)
if a.north_face_rows == 2:
 assert old_landing.count(anchor)==1, 'expected exactly one legacy face-strip rows=1 call'
 assert re.search(r'^export OT_CLAND_PINSLOT = 1$',s,re.M), 'profile needs existing pinslot form'
 new_landing=new_landing.replace(anchor,anchor[:-2]+'2]')
j={'schema':'opentallas.kit_profile.v1','profile':'s81_cland_control_taps_1107','group_re':GROUP_RE,'follow_re':'','north_face_rows':a.north_face_rows,'east_spacing':a.east_spacing,'east_rect_widen_w_um':[5.94,5.40] if a.east_spacing==1.25 else [0,0],'east_farthest_pin_reach_est_um':[46.98,44.28] if a.east_spacing==1.25 else [41.04,38.88],'landing_source_sha256':hashlib.sha256(old_landing.encode()).hexdigest(),'landing_result_sha256':hashlib.sha256(new_landing.encode()).hexdigest(),'north_spacing_budget':{'strip_depth_um':[18.36,18.90] if a.north_face_rows==2 else [9.18,9.45],'reserved_depth_um':[23.76,25.92],'farthest_vertical_pin_reach_est_um':36.18 if a.north_face_rows==2 else 26.73,'pin_reg_p90_target_um':30,'east_hotspot_fixed':False,'east_density_goal_est':0.59 if a.east_spacing==1.25 else None,'estimates_are_not_place_results':True},'reset_follower_policy':'preserve baseline inactive follower pass; no reset phase reassignment','source_config_sha256':before,'result_config_sha256':hashlib.sha256(s.encode()).hexdigest(),'rtl_changed':False,'plan_changed':False,'pin_cycles_added':0,'source_window_ps':140.0,'tap_cap_unchanged':1500,'exclude':'u_ring.s_d payload registers','estimate_basis':'existing t36 routed DEF origins; eligible main-clock subset verified by clock_taps at CTS','max_all_sequential_upper_bound':1245,'goal':'source-only corrected scope; CTS held for edge-density redesign; no route or batch release'}
print(json.dumps(j,indent=2))
if a.apply: lf.write_text(new_landing); f.write_text(s); (a.kit/'SOURCE_PROFILE_CLAND_TAPS.json').write_text(json.dumps(j,indent=2)+'\n')
