#!/usr/bin/env python3
"""94 exact source ABI pins/88 reserved slots; new geometry is intentionally null."""
from pathlib import Path
import json,hashlib,gzip,re,collections,sys,argparse
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/hier_contract'));import child_lint
sys.path.insert(0,str(Path(__file__).resolve().parent));from s81_ph_hrow_reset_classify import blocks
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
G=R/'results/arch/s81_hrow_reset_ack_1014/source_ack_graph.json';C=R/'results/arch/s81_hrow_native_placement_1013/r4_edge60_chunk4/candidate.json';g=json.loads(G.read_text());c=json.loads(C.read_text())
def ref(p):return {'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
# Source pin is an actual named module output, distinct from internal witness ACK.
pins=[]
for n in g['nodes']:
 helper=n['path'].replace('.','/');inst=helper.removesuffix('/u_ack_c').removesuffix('/u_ack').removesuffix('/g_ack')
 if n['port']=='rst_ack_leaf' and n['bit']>=33:inst='u_hub'
 assert inst in c['instances'],inst
 z=c['instances'][inst];hubbit=n['bit']-33 if inst=='u_hub' else None
 pin='rst_ack'+(f'[{hubbit}]' if hubbit is not None else '')
 pins.append(dict(parent_port=n['port'],parent_bit=n['bit'],instance=inst,master=z['master'],source_module_pin=inst+'/'+pin,witness_module_pin=helper+'/ack',source_clock_pin=inst+'/ck',epoch_input_pin=inst+('/reset_epoch_n' if n['port']=='rst_ack_relay' else '/rst'),final_local_states=n['local_release'],actual_clock_driver=None,actual_reset_driver=None,reserved_slot=z,source_nominal_ff=2,actual_mapped_ack_ff=None,actual_pin_rectangles=None,actual_pin_layers=None,eligible_for_routing=False))
assert len(pins)==94 and len({x['source_module_pin'] for x in pins})==94
master_reps=collections.Counter(z['master'] for z in c['instances'].values());ackcount=collections.Counter(z['master'] for z in pins)
# Count historical mapped standard-cell sequential state from real final netlists
# and exact Liberty ff/latch groups. SRAM macro bits are separately retained.
base=R/'results/arch/s81_hrow_native_placement_1013/reset_classification';fresh=R/'results/arch/s81_hrow_native_placement_1013/r4_actual_final/reset_classification';seq=set();libs=[]
for p in sorted(base.glob('*_RVT_SS.lib.gz')):
 libs.append(ref(p))
 for name,body,_ in blocks(gzip.open(p,'rt').read(),'cell'):
  if list(blocks(body,'ff')) or list(blocks(body,'latch')):seq.add(name)
files={p.name.removesuffix('.gz').removesuffix('_6_final.v'):p for d in [base,fresh] for p in list(d.glob('*_6_final.v'))+list(d.glob('*_6_final.v.gz'))}
masters={};nominal={'dsfd_hrow_r2079':2079,'dsfd_hrow_r1025':1025,'dsfd_hrow_r23':23,'dsfd_hrow_r15':15,'dsfd_die_rstsync':2}
for m,reps in sorted(master_reps.items()):
 md=c['masters'][m];lep=R/md['evidence'];lef=child_lint.parse_lef(lep.read_text());face=collections.Counter()
 for pin,d in lef['pins'].items():
  for layer,x0,y0,x1,y1 in d['rects']:
   x=(x0+x1)/2;y=(y0+y1)/2;nearest=min({'W':x,'E':md['w']-x,'S':y,'N':md['h']-y},key=lambda f:{'W':x,'E':md['w']-x,'S':y,'N':md['h']-y}[f]);face[nearest]+=1
 count=None;evidence=None;types={}
 if m in files:
  p=files[m];text=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text();types=dict(collections.Counter(t for t,_,body in re.findall(r'^\s*(\w+)\s+(\\\S+|[\w$]+)\s+\((.*?)\);',text,re.M|re.S) if t in seq and re.search(r'\.\w+\s*\(',body)));count=sum(types.values());evidence=ref(p)
 kit=('hrow5_'+m.rsplit('_',1)[-1]+('_cx' if m in ['dsfd_mtp_hrow_cbe','dsfd_mtp_hrow_cbw'] else '')) if m.startswith('dsfd_mtp') else m+'_m5';spec=R/'physical/ref_tile'/kit/'spec.json'
 receipt=a.out/'base_spec_receipts'/(kit+'.json')
 if receipt.exists():spec=receipt
 add_per=ackcount[m]//reps
 ackface=min(['N','S','W','E'],key=lambda f:face[f]);opposite={'N':'S','S':'N','W':'E','E':'W'}
 masters[m]=dict(replicas=reps,ack_ports_per_instance=add_per,nominal_added_ack_ff_per_instance=2*add_per,nominal_added_ack_ff_total=2*ackcount[m],historical_source_nominal_parent_ff_per_instance=nominal.get(m),historical_actual_mapped_sequential_cells=count,historical_actual_mapped_cell_types=types,historical_final_netlist=evidence,successor_actual_mapped_sequential_cells=None,successor_actual_ack_ff=None,successor_clock_sink_count=None,source_clock_sink_estimate=None if count is None else count+2*add_per,retained_outline_um=[md['w'],md['h']],outline_fit_status='reserved geometry, successor utilization/CTS/pin-access unmeasured',historical_lef=ref(lep),historical_contact_face_counts=dict(face),proposed_ack_face=ackface,proposed_raw_epoch_face=opposite[ackface] if m.startswith('dsfd_hrow_r') else None,actual_new_contacts=None,existing_kit_spec=ref(spec) if spec.exists() else None,successor_kit_name=kit+'_ack1',successor_params={'RESET_ACK':1} if m=='dsfd_die_rstsync' else {},successor_defines=['OT_HROW_RESET_ACK'],source_compilation=list(dict.fromkeys((json.loads(spec.read_text())['sources'] if spec.exists() else [])+['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv'])),gate_launch_owner='s81_vmfe_misc_2240',gate_launch_status='REQUEST: separate successor kits/source binding/pin constraints required; no inherited CLOSED qualification')
# Reviewable separate successor specs. Never mutate old CLOSED kit directories.
proposals=a.out/'successor_specs';proposals.mkdir(exist_ok=True)
for m,d in masters.items():
 if not d['existing_kit_spec']:continue
 original=R/d['existing_kit_spec']['path'];s=json.loads(original.read_text());s['name']=d['successor_kit_name'];s['sources']=d['source_compilation'];s['defines']=list(dict.fromkeys(s.get('defines',[])+['OT_HROW_RESET_ACK']));s['params'].update(d['successor_params']) if 'params' in s else s.update(params=d['successor_params'])
 s['pins'].setdefault(d['proposed_ack_face'],[]).append('rst_ack')
 if d['proposed_raw_epoch_face']:
  s['pins'].setdefault(d['proposed_raw_epoch_face'],[]).append('reset_epoch_n');s['reset_ports']=list(dict.fromkeys(s.get('reset_ports',[])+['reset_epoch_n']))
 s['job'].update(owner='Codex:s81_vmfe_misc_2240',branch='codex/s81-vmfe-misc-2240',tag='ack1',views_to='physical/ref_tile/'+s['name']+'/views',record_to='results/rtl/ref_tile/'+s['name'],purpose='Source-candidate genuine consumer reset ACK successor. Old CLOSED master untouched. Pin/contact/ownstate/clock/reset receipts and parent replay required; no native driver inferred.')
 s['job'].pop('benches',None);s['job']['benched_by']='results/arch/s81_hrow_reset_ack_1014/proof.json'
 s['structural_change']='Dedicated default-off OT_HROW_RESET_ACK. Actual consumer-local epoch witnesses; nominal +'+str(d['nominal_added_ack_ff_per_instance'])+' FF. New mapped counts, SS/FF timing, physical pins, clock/reset load pending.'
 (proposals/(s['name']+'.json')).write_text(json.dumps(s,indent=2)+'\n');d['proposed_successor_spec']=ref(proposals/(s['name']+'.json'))
newreset=[dict(instance=x['instance'],master=x['master'],source_pin=x['epoch_input_pin'],parent_source='TD.rst',production_source=None,actual_rectangles=None) for x in pins if x['parent_port']=='rst_ack_relay']
packet=dict(schema='s81.hrow94.physical_ack_candidate.v1',source_commit=g['source_commit'],imported_source_commit='bd7d09141',imported_proof_commit='7f2c2d184',source_graph=ref(G),reserved_data_placement=ref(C),strict_historical_data_candidate='81,363 bit pairs,<=500um geometry,every represented edge/cut<=.60; no actual RC qualification',source_ack_outputs=94,physical_child_instances=88,new_raw_epoch_inputs=27,total_added_signal_contacts=121,historical_raw_reset_pin_endpoints=61,successor_raw_reset_pin_endpoints=88,price=g['price'],new_mapped_ack_ff=None,nominal_ack_ff=188,masters=masters,ack_pin_inventory='ack_pins.json',new_raw_reset_inventory='new_epoch_pins.json',production_instance=None,global_origin=None,clock_source=None,clock_phase=None,reset_source=None,startup_receipt_consumer=None,startup_receipt_routes=None,required_receipts=['source-bound successor synthesis netlist + exact cell Liberty count for each of9 masters','successor gate/CTS ODB pin rectangles for all94 ACK +27 epoch input contacts, actual CK/RN/rawRST capacitance and mapped clock-sink counts','legal pin-access and unchanged/moved old contacts explicitly rebind81,363 data pairs; added121 contacts cannot inherit old replay','SS setup / FF hold for ACK output + raw-epoch async recovery/removal/pulsewidth; retain raw ETM labels and mapped cell arcs','successor final LEF/SSFF ETM/insertion/netlist/source hashes/clock constraints for9 masters','actual production TD instance/global transform, named refclk/reset producer output/net/phase and perleaf clock/reset route arrivals','genuine startup controller placement: synchronize each94 ACK individually before reduction and combine actual C/E/D readiness','route94 ACK +27 new epoch nets and existing clock/reset traffic; redo all cuts<=.60 and every pair RC budget; successor reach remainsNULL'],qualification='OPEN source candidate; historical CLOSED preserved; no native producer or phase inferred')
for name,data in [('packet.json',packet),('ack_pins.json',pins),('new_epoch_pins.json',newreset)]: (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'ack_outputs':len(pins),'instances':len(c['instances']),'new_epoch_pins':len(newreset),'mapped_historical':{m:d['historical_actual_mapped_sequential_cells'] for m,d in masters.items()},'nominal_added_ff':188,'new_mapped_ff':None},indent=2))
