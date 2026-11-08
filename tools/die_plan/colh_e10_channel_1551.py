#!/usr/bin/env python3
"""Private COLH10vQ successor: balance top e10 channels, pins/RTL unchanged.
Bottom e5 stays fixed because n12 occupies its proposed eastward pose.
"""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('kit',type=Path);p.add_argument('--balanced-e10',action='store_true');p.add_argument('--apply',action='store_true');a=p.parse_args()
f=a.kit/'macro_place.tcl';s=f.read_text();cfg=(a.kit/'config.mk').read_text()
assert 'col_h10_r1__t1__cl95b37463' in cfg,'exact vQ type required'
anchor='place_macro -macro_name {u_bound.u_u_e10} -location {518.5080 1010.8920} -orientation R0 -exact'
assert s.count(anchor)==1,'exact original central e10 pose required'
out=s.replace(anchor,anchor.replace('518.5080','534.0600')) if a.balanced_e10 else s
r={'profile':'colh10_e10_balanced_channel_1551','enabled':a.balanced_e10,'move_um':[15.552,0] if a.balanced_e10 else [0,0],'new_channels_um':{'west':40.584,'east':40.608} if a.balanced_e10 else {'west':25.032,'east':56.160},'bottom_e5_changed':False,'bottom_reason':'n12 native collision prevents same move','pin_cycles_added':0,'rtl_changed':False,'pins_changed':False,'clock_hooks_changed':False,'root_grid_nearest':'clk_t13 remains; clock-pin L1 130.748->146.300um','fixed_functional_cells_in_new_pose':0,'physical_tapcell_in_new_pose':737,'floorplan_must_regenerate':True,'source_macro_sha256':hashlib.sha256(s.encode()).hexdigest(),'result_macro_sha256':hashlib.sha256(out.encode()).hexdigest(),'goal':'ONE PLACE pilot; view actual density/native/pin/clock geometry before any CTS/GRT/batch','baseline':'private vQ pin-window kit, not a canonical plan adoption'}
print(json.dumps(r,indent=2))
if a.apply:
 assert not list(a.kit.glob('run/results/**/2_*')),'fresh1synth-only snapshot required, regenerate macro rows/tapcells'
 assert not list(a.kit.glob('.kwrs_done*')),'execution-state marker must not be copied'
 f.write_text(out);(a.kit/'SOURCE_PROFILE_E10_CHANNEL.json').write_text(json.dumps(r,indent=2)+'\n')
