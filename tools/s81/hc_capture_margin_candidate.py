#!/usr/bin/env python3
"""Prepare an unadopted structural capture-height candidate from assigned pins.
Run before generation; actual die parent slot and hop integration remain required.
"""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[2];out=R/'physical/s81_die_pins/v21_hc_capture_margin_candidate';out.mkdir(exist_ok=True)
receipt={'scope':'proposal pending actual die parent placement/slot integration; no qualification','old_height_um':25.92,'new_height_um':51.84,'reason':'Actual post-hold max bin632.41um2 / old24x21.6um capacity=122%;51.84um outline gives47.52um core,55.45% local density.','ports':{}}
for old,master,new in [('s81hc_ctfxcap_ref','ot_s81_hc_ctfx_cap','s81hc_ctfxcap_margin_ref'),('s81hc_ctfxnt_ref','ot_s81_hc_ctfx_nt','s81hc_ctfxnt_margin_ref')]:
 p=json.loads((R/f'physical/s81_die_pins/v20_hc_capture/{master}.json').read_text());assert p['outline_um']==[576.72,25.92];p['outline_um'][1]=51.84;p['case']='v21_hc_capture_margin_candidate';p['source']='proposed structural margin measured from native_closure_1014/cts_legalizer_1015';p['qualification']='pending actual die parent slot/hop integration, CTS, fullroute/native';(out/(master+'.json')).write_text(json.dumps(p,indent=1)+'\n');lines=[];n=0
 for port,plan in p['ports'].items():
  for i,(face,layer,coordinate,depth) in enumerate(plan['per_bit']):
   x,y={'S':(coordinate,.042),'N':(coordinate,51.798),'W':(.042,coordinate),'E':(576.678,coordinate)}[face];nm=port if plan['bits']==1 else f'{port}[{i}]';lines.append(f'place_pin -pin_name {{{nm}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary');n+=face=='N'
 (out/(master+'.tcl')).write_text('\n'.join(lines)+'\n');receipt['ports'][master]={'N_rectangles_shifted_um':25.92,'N_pin_count':n,'other_rectangles':'unchanged','all_pin_names_layers_and_face_coordinates':'unchanged'}
 spec=json.loads((R/f'physical/ref_tile/{old}/spec.json').read_text());spec['name']=new;spec['outline']['h']=51.84;spec['why_floorplan']='Actual full FF hold repair causes117-122%local density at original25.92um height; doubled51.84um outline/core47.52 restores measured55.45%local density margin without numeric/cycle/pin-x/SDC changes.';spec['io_tcl']=f'physical/s81_die_pins/v21_hc_capture_margin_candidate/{master}.tcl';spec['assigned_pins']={'file':f'physical/s81_die_pins/v21_hc_capture_margin_candidate/{master}.json','source':'proposed structural height margin, actual die parent integration pending'};spec['slot_change_request']='Proposed51.84um capture height +25.92um percth;S-DIE actual parent/source/hop integration pending. No publication/adoption before grant.';spec['job']['tag']='margin1';spec['job']['owner']='Codex:S-NORM';spec['job']['hold_merge']='Actual canonical die capture slot/pin/peer geometry and native TTFFDRC0 qualification pending';spec['job']['views_to']=f'physical/ref_tile/{new}/views';spec['job']['record_to']=f'results/rtl/ref_tile/{new}';spec['job']['structural_change']=spec['why_floorplan'];spec['job']['reroute_reason']={'kind':'slot_change','slot_change_request':spec['slot_change_request']};target=R/f'tools/ref_tile/specs_s81hc/{new}.json';target.write_text(json.dumps(spec,indent=1)+'\n')
(out/'proposal.json').write_text(json.dumps(receipt,indent=2)+'\n')

# Keep generation deterministic, including the measured original NT CTS wrapper.
import subprocess
for name in ('s81hc_ctfxcap_margin_ref', 's81hc_ctfxnt_margin_ref'):
 subprocess.run(['python3', str(R/'tools/ref_tile/ref_tile.py'), 'gen', str(R/f'tools/ref_tile/specs_s81hc/{name}.json')], cwd=R, check=True)
(R/'physical/ref_tile/s81hc_ctfxnt_margin_ref/pre_cts.tcl').write_text((R/'physical/ref_tile/s81hc_ctfxnt_ref/pre_cts.tcl').read_text())
