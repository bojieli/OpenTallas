#!/usr/bin/env python3
"""Necessary PG-aware pin capacity screen, never a pin assignment or route proof."""
import json,math,hashlib,pathlib,subprocess,gzip
out=pathlib.Path('results/arch/qwen_delivery_lifetime_1014/current_pin_capacity');out.mkdir(parents=True,exist_ok=True)
commit='6cc764460';paths=['results/arch/qwen_tp8_1012/vm_band_die_root_candidate_input_codex.json','results/arch/qwen_tp8_1012/vm_cluster_layer_grant_1013.json']
raw=[subprocess.check_output(['git','show',commit+':'+p]) for p in paths];die,grant=[json.loads(b) for b in raw];pg=grant['die_pg'];pitch=pg['pitch_um'];phases=pg['net_center_phases_um'];guard=.02+.04+pg['width_um']/2
fields={'selected_fill_payload_plus_event':375,'actual_tile_query_semantic':210,'actual_tile_query_with_toggle_credit_fault':213,'held_dispatch_common':428,'provider_full512_plus_event':759}
def centers(start,span):
 a=[];last=-math.inf
 for n in range(math.ceil((start+1.6)/.08),math.floor((start+span-1.6)/.08)+1):
  x=n*.08
  if x-last<.16-1e-8:continue
  if any(abs(x-(v+round((x-v)/pitch)*pitch))<guard-1e-9 for v in phases.values()):continue
  a.append(round(x,4));last=x
 return a
rows=[]
for s in die['slots']:
 n=centers(s['x'],s['w']);side=centers(s['y'],s['h'])
 rows.append({'slot':s['n'],'geometry':{k:s[k] for k in ['x','y','w','h']},'existing_bbox_conflicts':s.get('existing_conflicts',[]),'N_M9_available_guarded_centers':len(n),'WE_M8_available_guarded_centers':len(side),'scenarios':{'selected_fill375_plus_query210_with10center_gap_M9':{'required_positions':595,'raw_PG_capacity_pass':len(n)>=595},'selected_fill375_plus_query213_with10center_gap_M9':{'required_positions':598,'raw_PG_capacity_pass':len(n)>=598},'selected_fill375_plus_query210_plus_dispatch428_with20center_gaps_M9':{'required_positions':1033,'raw_PG_capacity_pass':len(n)>=1033},'provider759_alone_M9':{'required_positions':759,'raw_PG_capacity_pass':len(n)>=759},'selected_fill375_alone_side_M8':{'required_positions':375,'raw_PG_capacity_pass':len(side)>=375},'query210_alone_side_M8':{'required_positions':210,'raw_PG_capacity_pass':len(side)>=210}},'N_M9_guarded_centers_um':n,'WE_M8_guarded_centers_um':side})
r={'schema':'opentallas.current-native-delivery-PG-pin-capacity-screen.v1','qualified':False,'assigned':False,'adopted':False,'source_inputs':[{'commit':commit,'path':p,'sha256':hashlib.sha256(b).hexdigest()} for p,b in zip(paths,raw)],'field_sources':{'tile_query_and_dispatch':'b646b9303 bound_and_interface.json, semanticquery210 +togglecreditfault3, dispatch428','full_provenance':'5b9e9859d actualROW512/full247meta, selected128/full247meta; nativeXselect/fullfieldbinding pending'},'fields':fields,'PG':pg,'screen_assumptions':{'signal_grid_pitch_um':.08,'signal_center_min_spacing_um':.16,'edge_guard_um':1.6,'pin_half_width_um':.02,'PG_extra_clearance_um':.04,'grid_phase_um':0,'grid_qualification':'provisional signalgrid phase; actualPG phases/coreorigin measured'},'slots':rows,'summary':{'slots':len(rows),'M9_center_range':[min(x['N_M9_available_guarded_centers'] for x in rows),max(x['N_M9_available_guarded_centers'] for x in rows)],'M8_side_center_range':[min(x['WE_M8_available_guarded_centers'] for x in rows),max(x['WE_M8_available_guarded_centers'] for x in rows)],'scenario_pass_counts':{k:sum(x['scenarios'][k]['raw_PG_capacity_pass'] for x in rows) for k in rows[0]['scenarios']},'slots_with_existing_bbox_conflict':sum(bool(x['existing_bbox_conflicts']) for x in rows)},'limits':['Payload fields only; ACK/valid/reset/clock/admission overhead not all counted.','Raw PG center availability does not prove wire capacity,0.60cut,registered endpoints,pairreach,hold/setup,localOBS or technology pin rules.','M7 instruction or M6 metadata split is unqualified until actual PG/OBS/grid and native ABI bindings exist.','No dictionary149 compression/reconstruction, source/token/mode lifetime or same-face multiplexing is assumed.','Candidate frozen8e043 geometry remains unassigned and has existing collision reports; no replacement slots adopted.']}
details=[{'slot':x['slot'],'N_M9_guarded_centers_um':x.pop('N_M9_guarded_centers_um'),'WE_M8_guarded_centers_um':x.pop('WE_M8_guarded_centers_um')} for x in rows]
b=json.dumps(details,separators=(',',':')).encode();compressed=gzip.compress(b,mtime=0)
(out/'center_details.json.gz').write_bytes(compressed);r['center_details']={'path':'center_details.json.gz','sha256':hashlib.sha256(compressed).hexdigest(),'raw_sha256':hashlib.sha256(b).hexdigest(),'scope':'provisional scenario centers, not assigned pins'}
(out/'screen.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['summary']))
