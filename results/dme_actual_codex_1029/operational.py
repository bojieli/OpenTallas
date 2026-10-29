#!/usr/bin/env python3
"""Populate a coupon's operational files from the unchanged die-frame scaffold.

This is a placement-RC scaffold. The die owner supplies the reviewed actual
NDR/PG/GRT recipe before measuring routed arrivals.
"""
import json,re,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'die_plan'))
import die_trial as D

frame,out=map(Path,sys.argv[1:]);tree=json.loads((out/'tree.json').read_text())
old=json.loads((frame/'tree_frozen.json').read_text())
assert {t['port']:t['xy'] for t in old['taps']}=={t['port']:t['xy'] for t in tree['taps']}
place='\n'.join(f'place_inst -name {n} -location {{{x} {y}}} -status FIRM'
                for n,(x,y) in tree['sites'].items())+'\n'
(out/'placement_frozen.tcl').write_text(place)
text=(frame/'ctree.tcl').read_text();lines=text.splitlines();result=[];placed=False
for line in lines:
    if line.startswith('set ot_odd '):break
    if line.startswith('place_inst '):
        if not placed:result.append(place.rstrip());placed=True
        continue
    if line.startswith('place_pin -pin_name root '):
        x,y=tree['sites']['b0']
        line=f'place_pin -pin_name root -layer M9 -location {{{x} {y}}} -pin_size {{0.04 0.32}}'
    result.append(line)
result+=D.clock_edge_readout((out/'ctree.v').read_text(),'/work/clock/arr_$::env(CORNER).txt',
                            cells='{b* r* p*}',tap_slew=True)
result.append('puts OT_DONE')
(out/'ctree.tcl').write_text('\n'.join(result)+'\n')
for name in ('make_tracks.tcl','targets.json'):shutil.copyfile(frame/name,out/name)
shutil.copyfile(out/'tree.json',out/'tree_frozen.json')
print('operational frozen files',out,len(tree['sites']))
