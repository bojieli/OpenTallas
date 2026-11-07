#!/usr/bin/env python3
"""Opt-in t36 control/selector clock groups; payload storage stays nearest-tap."""
import argparse, hashlib, json, re
from pathlib import Path
GROUP_RE = r'^u_bound[.](u_cland_[A-Za-z0-9_]+)[./](?!u_ring[.]s_d)'
p = argparse.ArgumentParser(); p.add_argument('kit', type=Path); p.add_argument('--apply', action='store_true'); a=p.parse_args()
f=a.kit/'config.mk'; s=f.read_text(); before=hashlib.sha256(s.encode()).hexdigest()
assert 'OT_TAP_GROUP_RE' in (a.kit/'clock_taps.tcl').read_text(), 'kit lacks the existing group hook'
for key,val in [('OT_TAP_MAX_SINKS','1500'),('OT_TAP_TARGET_PS','250'),('OT_TAP_WINDOW','140.0000')]:
 m=re.search(r'^export '+key+r' = (\S+)',s,re.M); assert m and m[1]==val,(key,m[1] if m else None)
assert not re.search(r'^export OT_TAP_FOLLOW_RE\s*=',s,re.M), 'source follower override requires review'
assert not re.search(r'^export OT_TAP_GROUP_RE\s*=',s,re.M), 'profile already present or source changed'
s += '\n# CODEX S81 control-only CLAND grouping: preserve payload clocks and all contracts.\nexport OT_TAP_GROUP_RE = '+GROUP_RE+'\nexport OT_TAP_FOLLOW_RE =\n'
j={'schema':'opentallas.kit_profile.v1','profile':'s81_cland_control_taps_1107','group_re':GROUP_RE,'follow_re':'','reset_follower_policy':'preserve baseline inactive follower pass; no reset phase reassignment','source_config_sha256':before,'result_config_sha256':hashlib.sha256(s.encode()).hexdigest(),'rtl_changed':False,'plan_changed':False,'pin_cycles_added':0,'source_window_ps':140.0,'tap_cap_unchanged':1500,'exclude':'u_ring.s_d payload registers','estimate_basis':'existing t36 routed DEF origins; eligible main-clock subset verified by clock_taps at CTS','max_all_sequential_upper_bound':1245,'goal':'source-only corrected scope; CTS held for edge-density redesign; no route or batch release'}
print(json.dumps(j,indent=2))
if a.apply: f.write_text(s); (a.kit/'SOURCE_PROFILE_CLAND_TAPS.json').write_text(json.dumps(j,indent=2)+'\n')
