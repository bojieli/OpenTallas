#!/usr/bin/env python3
"""Finite MODEL extraction only: no RTL generation, synthesis, simulation or OpenROAD."""
import pathlib,json,gzip,hashlib,itertools,math,re
P=pathlib.Path(__file__).resolve().parent;T=P.parent/'qw_sysface_terminal_1019'
load=lambda p:json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
m=load(P/'input/original.json.gz')['modules']['qfd_sys_face'];r=load(P/'input/receipt.json')
origins={}
for name,n in m['netnames'].items():
 for i,b in enumerate(n['bits']):
  if isinstance(b,int):origins.setdefault(b,[]).append(name+(f'[{i}]' if len(n['bits'])>1 else ''))
assert m['ports']['rx_payload']['bits'][142]==184
fault=[c for c in m['cells'].values() if c['connections'].get('Q')==[5301]]
assert len(fault)==1 and fault[0]['connections']['D']==[5300] and fault[0]['type']=='$_DFF_PN0_'
assert 'u_record.u_context.fault' in origins[5301]
# Verify the actual generated 27-gate diagnostic cone without running any tools.
s=gzip.decompress((T/'source_parent.sv.gz').read_bytes()).decode().split('module sysface_safe_gate')[0]
g={}
for l in s.splitlines():
 z=re.search(r'sysface_safe_gate #\(\.ID\((\d+)\),\.KIND\((\d+)\)\) (g\d+)\((.*)\);',l)
 if z:
  p=dict(re.findall(r'\.(\w+)\(([^)]+)\)',z[4]));g[p['Y']]={'id':z[3],'kind':int(z[2]),'inputs':{k:v for k,v in p.items() if k!='Y'}}
from functools import lru_cache
@lru_cache(None)
def path(n):
 if n=='n184':return [n]
 if n not in g:return []
 q=max((path(i) for i in g[n]['inputs'].values()),key=len,default=[])
 return q+[n] if q else []
pp=path('n5300');assert len(pp)-1==27
out=[{'net':n,'gate':g.get(n),'semantic':origins.get(r['bit_origin'].get(n[1:],int(n[1:])),[])} for n in pp]
assert out==load(P/'cone_path.json')
# Exhaust source fault equation over its thirteen abstract Boolean guards.
# Sources: fault, begin, active, mismatch, slot, rx_v, structure, image,
# host_epoch_valid, retained_image_changed, head_v, stage_in_range, head_bad.
checks=0
for f,b,a,mm,sl,rv,st,im,hv,ch,head,stage,hbad in itertools.product([0,1],repeat=13):
 old=f
 if b and a:old=1
 if mm:old=1
 if sl and ((not rv) or (not st) or (not im) or a or b or f):old=1
 if hv and ch and a:old=1
 if head and stage and hbad:old=1
 new=bool(f or (b and a) or mm or (sl and ((not rv) or (not st) or (not im) or a or b)) or (hv and ch and a) or (head and stage and hbad))
 assert bool(old)==new;checks+=1
# Negated structure = nine invalid predicates. Negated image = four invalid
# predicates. Add !rx_v/native_active/program_begin = sixteen source predicates.
for b in itertools.product([0,1],repeat=16):
 assert bool(any(b)) == bool((any(b[:9])) or any(b[9:13]) or any(b[13:]));checks+=1
ends=load(T/'terminal_pg_all_endpoints.json.gz');roots=load(T/'terminal_pg_all_roots.json.gz')
layout=load(T/'placed_layout.json.gz');orr=next(c for c in layout['std_cells'] if c[0]=='core/g11451/_0_');assert orr[1]=='OR2x6_ASAP7_75t_R';or_area=(orr[5]-orr[3])*(orr[6]-orr[4])
sinks=[a for a in ends if a[0]=='core/g11451/_0_/Y'];assert len(sinks)==39
# Two deterministic proposed real publication partitions, retaining sticky path
# g5330 in group 0. Existing different publication g11452 is untouched.
sinks.sort(key=lambda a:(a[2]!='core/g5330/_0_/A',a[5],a[2]))
parts=[sinks[:20],sinks[20:]];assert [len(p) for p in parts]==[20,19]
assert len({a[2] for p in parts for a in p})==39
(P/'publication_partition.json').write_text(json.dumps({'scope':'Proposed post-map native endpoint partition; no source rewiring or native result','existing_root':'core/g11451/_0_/Y','unchanged_g11452_loads':1,'partitions':parts},indent=2)+'\n')
fp=load(T/'floorplan.json');halo=load(T/'spec.json')['route']['macro_halo_um'];assert halo==5.4
assert len(fp['blocks'])==9
for b in fp['blocks']:
 assert b['orient']=='R0'
 assert abs(b['x']/43.2-round(b['x']/43.2))<1e-8 and abs(b['y']/43.2-round(b['y']/43.2))<1e-8
# Keep the full measured macro/OBS geometry; band is strictly BELOW real 5.4 halo.
band_y=(2.16,min(b['y'] for b in fp['blocks'])-halo);assert abs(band_y[1]-37.8)<1e-8
# Native LEF obstruction and pin rectangles translated at each actual R0 macro.
macro_geometry=[]
for b in fp['blocks']:
 lef=(T/(b['master']+'.lef')).read_text();obs=lef.split('  OBS',1)[1].split('  END',1)[0];layer=None;rr=[]
 for l in obs.splitlines():
  z=re.search(r'LAYER (\w+) ;',l)
  if z:layer=z[1]
  z=re.search(r'RECT ([^;]+);',l)
  if z:
   q=list(map(float,z[1].split()));q=[q[0]+b['x'],q[1]+b['y'],q[2]+b['x'],q[3]+b['y']];rr.append({'layer':layer,'rect_um':q})
 assert rr and all(q['rect_um'][1]>band_y[1] for q in rr)
 pins=[]
 for pn,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',lef,re.S):
  role=re.search(r'USE (\w+) ;',body);role=role[1] if role else 'UNKNOWN'
  for rect in re.findall(r'RECT ([^;]+);',body):
   q=list(map(float,rect.split()));pins.append({'pin':pn,'role':role,'rect_um':[q[0]+b['x'],q[1]+b['y'],q[2]+b['x'],q[3]+b['y']]})
 macro_geometry.append({'instance':b['inst'],'native_lef_sha256':hashlib.sha256(lef.encode()).hexdigest(),'obstructions':rr,'pins':pins})
(P/'macro_geometry.json').write_text(json.dumps(macro_geometry,indent=2)+'\n')

soft=7266.0;geom=[]
for w in [302.4,324.,345.6]:
 area=(w-4.32)*(band_y[1]-band_y[0]);geom.append({'outline_um':[w,172.8],'band_xy_um':[2.16,band_y[0],w-2.16,band_y[1]],'band_area_um2':area,'existing_final_soft_occupancy':soft/area,'outline_area_delta_um2':(w-302.4)*172.8,'outline_area_delta_fraction':w/302.4-1,'full_outline_manhattan_diameter_um':w+172.8,'far_corner_to_band_center_manhattan_um':w/2+172.8-sum(band_y)/2,'whole_boundary_to_band_corner_bound_um':w-2.16+172.8-2.16,'all_endpoints_after_move':None,'clock_insertion_spread_after_move_ps':None})
# Exact context input snapshot inventory; all live inputs are captured, never
# just record/predicate while comparing against a different program epoch.
fields={'rx_record':548,'receive_slot':1,'rx_v':1,'program_begin_v':1,'program_ready':1,'installed_fusedcap':1,'program_epoch':16,'program_digest':64,'head_context_v':1,'head_stage':6,'head_token':18,'head_position':18,'native_active':1}
assert sum(fields.values())==677
state={'accepted_v':1,'host_epoch_valid':1,'host_tag':59,'host_gen':2,'host_fusedcap':1,'host_image_epoch':16,'host_image_digest':64,'fault':1};assert sum(state.values())==145
valid_copies=math.ceil(145/16);assert valid_copies==10
seq=gzip.decompress((T/'platform_seq_tt.lib.gz').read_bytes()).decode();prices={}
for c in re.split(r'(?=cell \()',seq)[1:]:
 name=c.split(')',1)[0][6:]
 if name in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R']:
  ar=float(re.search(r'area\s*:\s*([^;]+)',c)[1]);clk=next(p for p in re.split(r'(?=\n    pin \()',c)[1:] if p.startswith('\n    pin (CLK)'))
  cap=float(re.search(r'\n\s*capacitance\s*:\s*([^;]+)',clk)[1]);prices[name]={'area_um2':ar,'clock_cap_fF':cap}
ff=prices['DFFHQNx1_ASAP7_75t_R'];vf=prices['DFFASRHQNx1_ASAP7_75t_R'];newarea=677*ff['area_um2']+10*vf['area_um2'];cap=677*ff['clock_cap_fF']+10*vf['clock_cap_fF']
model={'verdict':'MODEL ONLY / production binding and native closure HOLD','frozen_source_commit':'ff05d759bd0370d41fa671b755233e91670f7fe0','real_profile_reference':'77fc3afbc (binding still missing; not inherited from generic cold fixture)','semantic_endpoint':{'native':'core/f2940.D','semantic':'u_record.u_context.fault','rx_field':'rx_payload[142] in reserved [511:142] zero test','generic_path_gates':27,'native_measured_levels':28,'native_measured_depth_ps':833.5,'native_measured_tt_setup_ps':-57.92388790837322},'age_neutral_candidate':{'default':False,'form':'balance sixteen bad-receive predicates, remove redundant sticky fault from receive bad term, balance final six fault causes','new_state_bits':0,'new_clock_pins':0,'new_reset_loads':0,'source_edges_added':0,'schedule_shift_edges':0,'exact_semantic_join_primitives':{'bad_receive_2input_OR':15,'receive_AND':1,'final_fault_2input_OR':5},'includes_existing_predicate_costs':False,'reserved_bit_abstract_path_upper_bound_levels':17,'native_logic_delta_area_fanout_and_timing':None,'four_state_equivalence':None,'note':'17 is model binary-tree gate depth from reserved bit only, not native depth or setup prediction. Other predicate/frontier paths must be checked.'},'same_edge_publication_candidate':{'new_2input_OR_publications':1,'new_state_bits':0,'new_clock_pins':0,'new_pg_terminals':2,'new_publication_loads':[20,19],'untouched_existing_publication_loads':1,'upstream_g11450_native_loads_before_after':[2,3],'upstream_fault_ff_native_loads_before_after':[5,6],'mapped_native_result':None,'conditional_same_OR2x6_bare_area_um2':or_area,'actual_mapped_added_area_um2':None,'warning':'Old g11452 equality is not proof that 39 native sinks were partitioned. Keep distinct source ownership and inspect every final native sink.'},'full_input_pipeline_fallback':{'default':False,'source_input_fields':fields,'input_snapshot_bits':677,'max_input_capture_bandwidth_bits_per_cycle':677,'native_tracks_required_and_available':None,'existing_receiver_state_bits':145,'stage_valid_kept_copies':10,'stage_valid_max_semantic_loads':15,'valid_native_select_pin_reserve_per_bit':2,'stage_valid_max_reserved_native_loads':30,'new_state_bits':687,'added_clock_pins':687,'added_async_reset_loads':10,'new_outer_state_enable_mux_bits':145,'source_edges_added':1,'first_context_accept_fault_visibility_shift_edges':1,'private_context_holdings_count':1,'scope':'Retimes all context RX inputs and all 145 state transitions; not just predicate. Does not retime auth/commit join or schedule automatically.','native_ff_prices':prices,'bare_ff_area_um2':newarea,'bare_clock_input_cap_fF':cap,'cts_wire_buffer_reset_ties_mux_area':None,'output_polarity_inversion_and_tie_cost':None,'added_2pin_native_pg_terminals':1374,'clock_energy_fJ_at_0p7V_per_cycle_access_only':cap*0.49,'new_tt_ff_setup_hold_ps':None,'production_su_token_delta_edges':None,'reset_control':'677 payload flops unreset; ten distinct valid flops reset with actual context reset. First valid update only after captured operands. Existing reset priority preserved; extra native set ties/reset leaf ownership require inventory.','critical_blocker':'Context outputs/fault/epoch invalidation now one edge later while BEGIN/native_active and all consumers remain live elsewhere. Bind producer calendar, cancellation and first-use before RTL.'},'geometry':{'measured_macro_origins':fp['blocks'],'halo_um':halo,'lower_band_y_um':band_y,'final_soft_reference_um2':soft,'warning':'Old y=41.04 band crosses the actual 5.4um SRAM halo. Correct top is37.8. Native OBS/layers and PG access still HOLD.','options':geom,'pipeline_bare_ff_only_occupancy_345p6':(soft+newarea)/geom[2]['band_area_um2'],'actual_native_pin_reach_after_relocation_um':None,'contact_pitch_nm':96,'local_contact_density_per_um':1000/96,'pg_unbound_original':29314,'ss_ff_clock_and_route_validation':None},'finite_model_checks':checks}
(P/'model.json').write_text(json.dumps(model,indent=2)+'\n')
# Hash exact preserved input identities and scripts, leaving model output hashes separate.
files=[p for p in P.rglob('*') if p.is_file() and p.name!='SHA256SUMS']
(P/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(P))+'\n' for p in sorted(files)))
print(json.dumps({'checks':checks,'new_pipeline_bits':687,'bare_ff_area_um2':newarea,'clock_fF':cap,'geometry':geom},indent=2))
