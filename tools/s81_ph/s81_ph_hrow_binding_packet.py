#!/usr/bin/env python3
"""Emit actual native hrow pin/source inventory without manufacturing production drivers."""
import argparse,collections,csv,gzip,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import s81_ph_hrow_native_placement as P
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint
import pinreg_audit
OUT=P.OUT/'binding_packet'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def geometry(master):
 m=P.MP[master];p=ROOT/m['evidence']
 if m['kind']=='closed_child_lef':
  t=child_lint.parse_lef(p.read_text());return {n:[dict(layer=r[0],rect_um=list(r[1:])) for r in v['rects']] for n,v in t['pins'].items()}
 d=json.load(open(p));return {n:v['boxes'] for n,v in d['pins'].items()}
def transformed(z,m,box):
 x0,y0,x1,y1=box['rect_um'];pts=[]
 for x,y in [(x0,y0),(x1,y1),(x0,y1),(x1,y0)]:
  if z['orient']=='MY':x=m['w']-x
  elif z['orient']=='MX':y=m['h']-y
  pts.append((x+z['x'],y+z['y']))
 return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
def main():
 a=argparse.ArgumentParser();a.add_argument('--contract',type=Path,default=Path('/home/ubuntu/wt/el1011-s81dieit/physical/s81_die_pins/v18/contract_trial.json'));a.add_argument('--consumed-plan',type=Path,default=Path('/home/ubuntu/wt/el1011-s81dieit/results/physical/die_iter_1012/s81/c7_native_classes_1013/plan.json.gz'));args=a.parse_args()
 d=json.load(open(P.OUT/'candidate.json'));OUT.mkdir(exist_ok=True)
 net=[];pins=[];geo={m:geometry(m) for m in {z['master'] for z in d['instances'].values()}}
 release_by={e['sink']:e['source'] for e in d['connectivity_edges'] if e['cls']=='local_reset_release'}
 for name,z in d['instances'].items():
  ma=z['master'];m=P.MP[ma]
  for pin in ['ck','rst','rn']:
   if pin not in geo[ma]:continue
   kind='reference_clock_sink' if pin=='ck' else 'global_async_reset_sink' if pin=='rst' else 'local_reset_release_driver' if ma=='dsfd_die_rstsync' else 'local_reset_release_sink'
   source='TD.ck' if pin=='ck' else 'TD.rst' if pin=='rst' else name+'.rn' if kind.endswith('driver') else release_by[name]+'.rn'
   bs=[dict(layer=b['layer'],master_rect_um=b['rect_um'],slot_rect_um=transformed(z,m,b)) for b in geo[ma][pin]]
   rect=bs[0]['slot_rect_um'];point=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2];face=m['pins'][pin]
   # Actual face is transformed by the legal orientation; no contract-face placeholder.
   x,y=point[0]-z['x'],point[1]-z['y'];f=min([(x,'W'),(y,'S'),(m['w']-x,'E'),(m['h']-y,'N')])[1]
   pins.append(dict(instance=name,master=ma,pin=pin,kind=kind,rtl_source=source,orientation=z['orient'],origin_slot_um=[z['x'],z['y']],pin_slot_um=point,pin_face=f,boxes=bs,evidence=m['evidence'],evidence_sha256=m['sha256'],global_die_coordinates=None,physical_producer_binding=None if pin in ['ck','rst'] else source))
 clocks=[p for p in pins if p['kind']=='reference_clock_sink'];reset=[p for p in pins if p['kind']=='global_async_reset_sink'];local=[p for p in pins if p['kind']=='local_reset_release_sink']
 assert len(clocks)==88 and len(reset)==61 and len(local)==27 and len(pins)==203
 masters={}
 timing_facts={}
 for ma in sorted(geo):
  m=P.MP[ma];e=dict(master=ma,instances=sum(z['master']==ma for z in d['instances'].values()),pin_evidence=m['evidence'],pin_evidence_sha256=m['sha256'],kind=m['kind'],insertion_corners=None,final_ss_lib=None,final_ff_lib=None,status='RELAY FINAL ROUTED ETMS/INSERTION PENDING')
  if ma in P.CHILDREN:
   directory=ROOT/'physical/ref_tile'/P.CHILDREN[ma]/'views'/ma;p=directory/'insertion.json';ins=json.load(open(p));e.update(insertion=ref(p),insertion_corners={c:ins[c]['boundary'] for c in ['ss','tt','ff']},final_ss_lib=ref(directory/(ma+'_ss.lib')),final_ff_lib=ref(directory/(ma+'_ff.lib')),status='CLOSED child views; parent delivery/timing not qualified')
   timing_facts[ma]={c:dict(liberty=ref(directory/(ma+'_'+c+'.lib')),pins=pinreg_audit.parse_lib(directory/(ma+'_'+c+'.lib'))['pins'],units='ps; all raw lookup values retained; original Liberty supplies axes; no load/slew interpolation assumed') for c in ['ss','ff']}
  masters[ma]=e
 contract=json.load(open(args.contract));slots=[s for s in contract['slots'] if 'hrow' in s.get('name','')];old={s.get('cell'):s for s in slots if s.get('kind')=='tile'}
 consumed=json.load(gzip.open(args.consumed_plan,'rt'));oldinst=[i for i in consumed['insts'] if 'hrow' in str(i).lower()]
 compare=[]
 for ma in P.CHILDREN:
  s=old[ma];actual=[p for p in clocks if p['master']==ma];compare.append(dict(master=ma,consumed_contract_slot=s['name'],declared_clock_entry=s['clock_entry'],actual_instance_clock_pins=[{k:p[k] for k in ['instance','pin','pin_face','pin_slot_um','boxes']} for p in actual],scalar_clock_present=True,boilerplate_face_mismatch=any(p['pin_face']!=s['clock_entry']['face'] for p in actual),boilerplate_layer_mismatch=any(b['layer']!=s['clock_entry']['layer'] for p in actual for b in p['boxes']),replaced_actual_instances=[]))
 request=dict(schema='opentallas.native_hrow_allocator_request.v1',status='REQUIRES root production source integration before tap allocation',request_id='s81-native-hrow-ut2-dist-5281a6feb',source_module='dsfd_mtp_hrow_td',parameters=d['parameters'],scope='Local slot geometry only; physical die identity/global origin/orientation not assigned',required_production_instance={'physical_die_role':None,'physical_die_identity':None,'instance_path':None,'slot_global_origin_um':None,'slot_global_orientation':None,'source_netlist_path':None,'source_netlist_sha256':None},required_reference_clock={'producer_kind':None,'source_top_port_or_external_pin':None,'source_instance':None,'source_output_pin':None,'source_net':None,'root_clock_constraint_ref':None,'domain':None,'period_ps':None,'edge_polarity':None,'phase_ps':None,'allocator_root_or_tap':None,'per_leaf_clock_delivery_ss_ff':None},required_global_reset={'producer_kind':None,'source_top_port_or_external_pin':None,'source_instance':None,'source_output_pin':None,'source_net':None,'active_polarity':'low (verified source rst_n_async/negedge rst)','assertion_delivery_bounds':None,'deassertion_delivery_bounds':None,'per_leaf_route_and_pin_load':None,'recovery_removal_and_pulse_width_qualification':None},counts={'clock_roots':88,'global_reset_sinks':61,'local_rn_drivers':27,'local_rn_loads':27,'own_relay_ff':18897,'own_reset_ff':54},provided={'pin_inventory':'physical_pins.json','replacement_mapping':'replacement_mapping.json','source_graph':'source_graph.json','geometry_candidate':str((P.OUT/'candidate.json').relative_to(ROOT)),'route_artifact':str((P.OUT/'grid_routes.json.gz').relative_to(ROOT)),'route_replay':str((P.OUT/'route_replay.json').relative_to(ROOT))},prohibited_fallbacks=['Bench clk/rst_n cannot become production sources','Destination clock pin cannot be reused as the source identity','No zero insertion/phase for missing relay exports','No period inferred from closed leaf signoff SDC','No fixed500um interpreted as actual per-pair timing budget','No physical global coordinates inferred from virtual origin0','External/top-level source allowed only with actual consumed RTL/netlist/constraint/physical pin evidence'])
 packet=dict(schema='opentallas.native_hrow_source_binding_packet.v1',status='OPEN production source driver/refclk/reset ABI; geometry stable',parameters=d['parameters'],rtl_sources={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_die.sv',ROOT/'rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv',ROOT/'rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv']},placement=ref(P.OUT/'candidate.json'),placement_commit='5281a6feb',geometry_pass=d['internal_data_geometry_pass'],route_replay=d['independent_route_replay'],production_proof=d['production_proof'],own_state={'relay_ff':18897,'reset_ff':54},pin_counts=collections.Counter(p['kind'] for p in pins),master_evidence=masters,consumed_contract=ref(args.contract),consumed_c7_plan=ref(args.consumed_plan),consumed_c7_hrow_instances=oldinst,current_native207_owner_statement='s81_die_v18 reports terminal native207 has no hrow instance, authoritative global origin, ck producer or rst producer; exact file refs requested',adoption_requested_not_completed=True,allocator_request='allocator_request.json',rc_budget_status='OPEN: final relay SS/FF ETMs and source/destination clock delivery required; no budget or frequency inferred from500um')
 graph=dict(module='dsfd_mtp_hrow_td',clock={'rtl_input':'ck','production_driver':None,'sink_pins':[p['instance']+'.ck' for p in clocks]},global_reset={'rtl_input':'rst','polarity':'active low','production_driver':None,'sink_pins':[p['instance']+'.rst' for p in reset]},local_release=[dict(driver=e['source']+'.rn',sink=e['sink']+'.rn',conditioner_inputs={'ck':'TD.ck','rst':'TD.rst'},ideal_release_edges=2,physical_recovery_removal_status='OPEN actual clock arrivals and SS/FF arcs') for e in d['connectivity_edges'] if e['cls']=='local_reset_release'],production_external_ports=['f_hp0[514:0]','f_hp1[514:0]','f_hp2[514:0]','t_hpg[2:0]','f_vrq[24:0]','t_vrq','t_vrs[1024:0]','f_clr[10:0]','t_flt[2:0]'],external_producer_consumer_binding=None)
 mapping=dict(consumed_contract_hrow_slots=slots,actual_retained_c7_instances=oldinst,clock_face_comparisons=compare,new_masters=masters,new_instance_map=d['instances'],new_clock_roots=88,new_rst_sinks=61,new_rn_links=27,default_numerical_behavior_changed=False,selected_parameters_default_off=True,logical_die_role_evidence='RTL describes primary hidden-row store; contract note says stage37..39. Exact production die identity/role must be resolved by root.')
 with gzip.open(OUT/'closed_child_ss_ff_timing_facts.json.gz','wt') as f:json.dump(timing_facts,f,separators=(',',':'))
 packet['closed_child_timing_facts']=ref(OUT/'closed_child_ss_ff_timing_facts.json.gz')
 packet['missing_final_relay_timing_masters']=[m for m in masters if m not in P.CHILDREN]
 for name in ['native207_evidence.json','native207_consumed_contract_slice.json']:
  side=OUT/name
  if side.exists():
   key='current_consumed_native207' if name=='native207_evidence.json' else 'current_consumed_native207_contract'
   packet[key]=json.loads(side.read_text());mapping[key]=json.loads(side.read_text())
 intake=OUT/'final_relay_intake.json'
 if intake.exists():
  final=json.loads(intake.read_text());packet.update(status='OPEN production source ABI; 88-instance geometry historical pending large relay successors',final_relay_intake=ref(intake),missing_final_relay_timing_masters=list(final['large_master_status']),rc_budget_status=final['actual_per_pair_rc_budget_status'])
  for ma,v in final['final_small_masters'].items():packet['master_evidence'][ma].update(status='CLOSED final relay views; historical CTS pin geometry retained separately; parent delivery/timing OPEN',final_view_record_commit=v['record_commit'],final_lef=v['final_lef'],insertion=v['insertion'],insertion_corners=v['insertion_corners'])
 packet['clock_reset_delivery_route_scope']='Data/localrn81363pairs only;88globalclockroots/61originalreset sinks require actualallocatorroutes, loads/skew and aggregatecapacity validation.'
 packet['source_binding_prerequisite']=dict(owner='root whole-native source integration',required_next='Commit actualproduction TD instance/physicaldie/realclock andresetproducer graph beforeallocator tap/phase assignment')
 for n,v in [('packet.json',packet),('physical_pins.json',pins),('allocator_request.json',request),('source_graph.json',graph),('replacement_mapping.json',mapping)]: (OUT/n).write_text(json.dumps(v,indent=1)+'\n')
 with (OUT/'physical_pins.csv').open('w') as f:
  writer=csv.writer(f);writer.writerow(['instance','master','pin','kind','rtl_source','orientation','x_slot_um','y_slot_um','face','layers','actual_pin_evidence'])
  for p in pins:writer.writerow([p['instance'],p['master'],p['pin'],p['kind'],p['rtl_source'],p['orientation'],*p['pin_slot_um'],p['pin_face'],','.join(b['layer'] for b in p['boxes']),p['evidence']])
 print(json.dumps({'pins':len(pins),'kinds':packet['pin_counts'],'old_c7_instances':len(oldinst),'clock_face_mismatch_masters':[r['master'] for r in compare if r['boilerplate_face_mismatch']]}))
if __name__=='__main__':main()
