from pathlib import Path
import json,math,re,hashlib,collections
w=Path('/home/ubuntu/wt/codex-qw-ctlm-safe-recut-1019');p=Path(__file__).parent
record=w/'results/arch/landed_parent_1018/qfd_tt_ctlm_dv_lpf/qfd_tt_ctlm_dv_lpf_lp_record.json';a=json.loads(record.read_text());rows=[];s=collections.defaultdict(lambda:dict(payload_bits=0,chunks24=0,bank4_bits=0,valid4_bits=0,epoch_bits=0,total_cut_pins=0,landings=0))
for l in a['landings']:
 c=math.ceil(l['width']/24);row=dict(name=l['name'],net=l['net'],src=l['src_region'],dst=l['dst_region'],payload_bits=l['width'],chunks24=c,bank4_bits=4*l['width'],valid4_bits=4*c,epoch_bits=12,total_cut_pins=4*l['width']+4*c+12,added_edges=l['added_edges']);rows.append(row)
 q=s[l['src_region']+'->'+l['dst_region']]
 for k in ('payload_bits','chunks24','bank4_bits','valid4_bits','epoch_bits','total_cut_pins'):q[k]+=row[k]
 q['landings']+=1
# R0 hard native_cmd geometry; no unadvertised mirror/rotation: LEF has no SYMMETRY.
lef=w/'physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr/ot_qfd_tt_ctlm_static_hr.lef';text=lef.read_text();shapes={}
for m in re.finditer(r'  PIN ([^\n]+)\n(.*?)  END \1\n',text,re.S):
 rect=re.search(r'RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2]);
 if rect:shapes[m[1]]=list(map(float,rect.groups()))
pins=w/'physical/ref_tile/qfd_tt_ctlm_dv_safe1/assigned_pins.tcl';grants=[]
for line in pins.read_text().splitlines():
 m=re.match(r'ot_assigned_pin_exact \{(native_cmd\[\d+\])\} M3 N ([\d.]+)',line)
 if m:grants.append((float(m[2]),m[1]))
assert len(grants)==380;grants.sort();dist=[];new=[]
for j,(old,name) in enumerate(grants):
 box=shapes[name];x=475.2+(box[0]+box[2])/2;y=43.2+(box[1]+box[3])/2
 ey=78.732+.192*j
 dist.append(dict(port=name,hard_pin_center=[x,y],old_pin=['N',old],proposed_pin=['E',round(ey,6)],old_manhattan_um=abs(x-old)+abs(y-432),proposed_manhattan_um=abs(x-777.6)+abs(y-ey)))
 new.append(f'ot_assigned_pin_exact {{{name}}} M4 E {ey:.6f}')
oldmax=max(v['old_manhattan_um'] for v in dist);newmax=max(v['proposed_manhattan_um'] for v in dist)
r=dict(adoption=False,no_gate=True,source_record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),landings=rows,directional_summary=dict(s),total_payload_bits=sum(v['payload_bits'] for v in rows),single_clock_split_leaves=dict(bank4_bits=sum(v['bank4_bits'] for v in rows),valid4_bits=sum(v['valid4_bits'] for v in rows),epoch_bits=sum(v['epoch_bits'] for v in rows),raw_seam_pins=sum(v['total_cut_pins'] for v in rows),common_face_um=432.0,raw_pins_per_um=sum(v['total_cut_pins'] for v in rows)/432,at_legal_M4_pitch192_face_needed_um=sum(v['total_cut_pins'] for v in rows)*.192,lattice_face_needed_um=864,outline_area_ratio_if_same_width=2.0,alternatives_require='Multiple faces/channels need allocated reach/escape/slot proof; cannot assume this lower bound applies to all layouts'),whole_landing_pairs_in_destination_leaves=dict(internal_data_seam_bits=514,external_input_bits_enter_core_leaf_directly=438,leaf_clock_ports_each=['ck_core','ck_hr'],needs='Actual native related-root phase/cold-epoch contract inside both two-clock leaves'),existing_ages=a['compiler'],existing_landing_ff=a['flops'],hard_core_macro_home_blocker=dict(SRAMs=6,OPROMs=3,ROM_width=38.016,ROM_height=62.910,core_north_and_row_gaps_height=51.84,middle_column_gap=44.712,ROM_width_plus_two_halos=48.816,current_OPROMs_are_in_HR_physical_footprint=True,alternatives=['Re-home or grow complete core leaf','Separate explicit memory leaves with real clock/data boundary contracts']),typed_phase_contract_route=dict(source_phase_guarantee_present=False,default_phi_fraction=.75,setup_base_plus_res_ps=210,hold_base_plus_res_ps=175,budget_formula='T - 210ps - guaranteed_absolute_phi_bound_ps',cannot_use='Standalone ideal input clocks or measured extrema alone as a parent guarantee',required=['Real CKgen/root source and counter epoch/reset/context contract','Source/netlist/Liberty/RC hashes','All real child clock entries and register/macro endpoint populations TT/FF min/max rise/fall','Full original data/select/reset/native timing and reserve checks','Fail closed if source/coverage/initialization/phase guarantee changes']),native_cmd_reach_geometry_only=dict(hard_leaf_orientation='R0',LEF_symmetry_declared=bool(re.search(r'\bSYMMETRY\b',text)),no_mirror_or_leaf_reclose=True,ports_recut=380,old_N_to_proposed_E=True,old_fixed_pin_reach_max_um=oldmax,proposed_fixed_pin_reach_max_um=newmax,E_first_y=78.732,E_pitch=.192,E_last_y=78.732+.192*379,all_380_on_real_uniform_M4_grid=True,new_face_counts=dict(N=818,S=1775,W=0,E=399),logical_ports_and_edges_unchanged=True,needs='GEN actual seam/hop repricing; PG/pin access/reach proof on copied real DB before adoption'))
(p/'ctlm_structural_crossing_model.json').write_text(json.dumps(r,indent=2)+'\n');(p/'ctlm_nativecmd_E_recut_proposal.tcl').write_text('# Geometry-only proposal; no gate/adoption. Preserve all clocks/FF edges.\n'+'\n'.join(new)+'\n');(p/'ctlm_nativecmd_reach_model.json').write_text(json.dumps(dist,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('landings','existing_ages')},indent=2))
