#!/usr/bin/env python3
"""Actual recovered clock-only BPin cut for the approved geometry prototype; no connectivity/timing credit."""
import json,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-kv-hhp-parent-1131');K=R/'geometry_adapted3';C=Path('/srv/opentallas-scratch2/claude/codex-kv-pc-cores-1101/parent_abi_census1131')
D=json.loads((K/'diagnostic_network_cut.json').read_text());G=json.loads((C/'ft_cut_geometry.json').read_text());P=next(x for x in G['parts'] if x['part']=='pc_EN_0');netmap=D['per_instance_network_cut']['pc_EN_0']['input_aliases'];shapes={}
for alias,rec in netmap.items():
 actual=next(x for x in P['clock_only_inputs'] if x['net']==rec['actual_net']);shapes[alias]=actual['parent_shapes'];assert len(shapes[alias])==3 and all(x['layer']=='M1' for x in shapes[alias])
outs=P['clock_only_output']['native_FT_sources'];assert len(outs)==8
shapes['diag_mesh_post']=[{'layer':'M9','rect_um':x['declared_canonical_M9_strap_subset_parent_rect_um']} for x in outs]
for x in outs:assert x['actual_native_FT_layer']=='M5' and x['connection_credit'].startswith('NONE')
L=['# Actual native Y-pin M1 rectangles and recovered M9 strap subsets; no invented child M9 pins.', '# Clock-only geometry cut; no new wire, via, timing, equivalence or SIGNED credit.', 'set dc_b [ord::get_db_block]', 'set dc_u [$dc_b getDbUnitsPerMicron]', 'set dc_tech [ord::get_db_tech]']
for alias,ss in shapes.items():
 L += [f'set dc_t [$dc_b findBTerm {{{alias}}}]', f'if {{$dc_t eq "NULL" || $dc_t eq ""}} {{error "DIAGNOSTIC_CUT missing declared port {alias}"}}', 'set dc_n [$dc_t getNet]', f'if {{$dc_n eq "NULL" || $dc_n eq ""}} {{error "DIAGNOSTIC_CUT disconnected port {alias}"}}', '$dc_n setSigType CLOCK', '$dc_t setSigType CLOCK', 'foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}', 'set dc_p [odb::dbBPin_create $dc_t]', '$dc_p setPlacementStatus FIXED']
 for sh in ss:
  layer=sh['layer'];r=sh['rect_um'];assert len(r)==4 and r[2]>r[0] and r[3]>r[1]
  vals=' '.join(f'[expr {{round({v:.9f}*$dc_u)}}]' for v in r)
  L += [f'set dc_l [$dc_tech findLayer {{{layer}}}]',f'if {{$dc_l eq "NULL"}} {{error "DIAGNOSTIC_CUT missing layer {layer}"}}',f'odb::dbBox_create $dc_p $dc_l {vals}']
L += ['puts "DIAGNOSTIC_CUT placed exact5clock-only ports (12native M1 rectangles,8canonical M9 subsets); no route/via/STA credit"']
(K/'diagnostic_cut_geometry.tcl').write_text('\n'.join(L)+'\n');io=K/'io.tcl';s=io.read_text();assert 'diagnostic_cut_geometry.tcl' not in s;io.write_text(s+'\nsource /work/diagnostic_cut_geometry.tcl\n')
conf=K/'config.mk';s=conf.read_text();assert 'GPL_ROUTABILITY_DRIVEN = 0' not in s;s+='\n# Geometry-only cut: M9 die mesh is external; place soft glue by wirelength, do not infer a parent mesh route.\nexport GPL_ROUTABILITY_DRIVEN = 0\n';conf.write_text(s)
shutil.copy2(C/'ft_cut_geometry.json',K/'ft_cut_geometry.json');D['geometry_status']='Actual5port cut applied; EN/WN rendered and LOOKED; current prototype representative EN. NativeFT M5 versus canonicalM9strap distinction retained; no route/via/STA credit.';D['clock_only_port_shapes']=shapes;(K/'diagnostic_network_cut.json').write_text(json.dumps(D,indent=1)+'\n');print('Exact clock-only port geometry applied; representativeEN; no timing/connection credit')
