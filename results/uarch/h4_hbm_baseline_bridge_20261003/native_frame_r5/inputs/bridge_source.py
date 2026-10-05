#!/usr/bin/env python3
"""W5 owned gate and W10 addressed fabric model; no endpoint RTL emitted."""
import argparse,hashlib,json,math,collections
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003/w5_w10_r4'
PIN='96d1b4f84f93bd3c48f91a5f4c7897ba40f9419a04435b951c6e6c11d95cabe5'
def require(x,msg):
 if not x:raise ValueError(msg)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def inputs():
 raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'hard manifest pin');out={}
 for r in json.loads(raw)['inputs']:
  p=(BASE/r['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive origin');v=p.read_bytes();require(len(v)==r['bytes'] and hashlib.sha256(v).hexdigest()==r['sha256'],'exact input');out[p.name]=v
 return out
def protected(n):return math.ceil(n/64)*72
def physical(byte):
 """Exact retained r17 address translation; never alter payload low bits."""
 require(type(byte)is int and 0<=byte<4*20250000000,'global HBM address aperture')
 local=(byte//512)*128+byte%128;sector=local//32
 require(sector<2**31,'retained local sector aperture')
 stack=(byte//128)%4;pc=((sector>>2)^(sector>>7)^(sector>>12))&31
 return dict(stack=stack,local_sector=sector,physical_PC=stack*32+pc,byte_in_sector=local%32)
def inverse_address(address):
 require(set(address)=={'stack','local_sector','physical_PC','byte_in_sector'},'exact address descriptor')
 require(all(type(v)is int for v in address.values()) and 0<=address['stack']<4 and 0<=address['byte_in_sector']<32,'lossless address fields')
 local=address['local_sector']*32+address['byte_in_sector'];byte=(local//128)*512+address['stack']*128+local%128
 require(physical(byte)==address,'hash/PC agreement, not address-bit rewrite')
 return byte

class BankedSwitch:
 """Candidate conventional crossbar arbitration, one accepted beat/output.

 Bounded directed model, not source fairness qualification. Each input holds
 one destination until acceptance; accepted output beats retain parent owner.
 """
 def __init__(self,ni=36,no=32):
  require(type(ni)is int and 1<=ni<=36 and type(no)is int and 1<=no<=32,'finite switch ports');self.ni=ni;self.no=no;self.head=[0]*no
 def step(self,requests,ready):
  require(len(ready)==self.no and all(type(r)is bool for r in ready),'actual output ready')
  for i,r in requests.items():require(type(i)is int and 0<=i<self.ni and set(r)=={'destination','payload','owner'} and type(r['destination'])is int and 0<=r['destination']<self.no and r['owner'],'source packet/destination/owner')
  accepted={}
  for output in range(self.no):
   if not ready[output]:continue
   winner=next((i for k in range(self.ni) for i in [(self.head[output]+k)%self.ni] if i in requests and requests[i]['destination']==output),None)
   if winner is not None:accepted[winner]=requests[winner];self.head[output]=(winner+1)%self.ni
  return accepted
class NativeCaller:
 """Executable prospective adapter: actual accepted SM port, r14 hash, owner46.

 Read-only baseline. A tile's byte addresses and original child tags come from
 the accepted issuer, not home-SM guesses. No numerical callback. Backend
 gen4 echo is a required successor port, not a claim about installed r14.
 """
 def __init__(self,SM):
  require(type(SM)is int and 0<=SM<32,'actual accepted SM port');self.SM=SM;self.live=None;self.last_generation=None
 def accept(self,model,kind,base,tags,generation,RFslot,parent):
  require(self.live is None and model in ('Qwen','DeepSeek') and kind in ('C0','KV_read'),'one owned tile and selected models/operators')
  require(type(base)is int and base%32==0,'sector aligned real issuer address')
  require(type(generation)is int and 0<=generation<16,'separate source generation4')
  require(self.last_generation is None or generation==(self.last_generation+1)%16,'generation modulo16 after all-copy drain')
  require(set(parent)=={'reference32','owner46','native_owner64','native_generation64','format','legacy'},'pre-bound native-to-parent directory row, no truncated native identity')
  require(all(type(parent[k])is int and 0<=parent[k]<2**w for k,w in (('reference32',32),('owner46',46),('native_owner64',64),('native_generation64',64))),'lossless bound native and hardware fields')
  require(parent['format']=='raw_U32_frame' or kind=='C0' and parent['format']=='shared64_bytes','codec must precede RF deposition; no raw FP8 as F32')
  require(parent['owner46']&15==generation and parent['owner46']>>36&7==(0 if kind=='C0' else 5),'bound parent source client/gen')
  legacy=parent['legacy'];widths={'die':1,'producer':64,'transport':32,'caller':16,'client':6,'irs_slot':5,'irs_serial':32}
  require(set(legacy)==set(widths) and all(type(legacy[k])is int and 0<=legacy[k]<2**w for k,w in widths.items()),'unchanged actual r14 legacy requester fields')
  n=2 if kind=='C0' else 16
  require(len(tags)==n and all(type(t)is int and 0<=t<2**32 for t in tags) and len(set(tags))==n,'unchanged unique accepted original child tags32')
  require(kind=='C0' or type(RFslot)is int and 0<=RFslot<512,'actual RFslot9')
  require(kind!='C0' or type(RFslot)is int and 0<=RFslot<1024,'actual shared10 destination in parent directory')
  children=[]
  for i,tag in enumerate(tags):
   addr=physical(base+32*i);client=0 if kind=='C0' else 5
   owner=(addr['physical_PC']<<39)|(client<<36)|(tag<<4)|generation
   children.append(dict(R14_LEN6=1,R14_BEAT5=0,index=i,byte=base+32*i,owner46=owner,client=client,originaltag32=tag,generation4=generation,**addr))
  require(parent['owner46']>>39 in {ch['physical_PC'] for ch in children},'pre-bound parent anchor must be an actual frame PC')
  for child in children:child['legacy_identity192']=dict(legacy,stack=child['stack'],sector=child['local_sector'])
  for child in children:child['meta92']=(child['owner46']<<46)|(self.SM<<41)|((RFslot if kind=='KV_read' else 0)<<32)|parent['reference32']
  self.live=dict(parent=dict(parent),model=model,kind=kind,children=children,data={},phase='assembly',RFslot9=RFslot,physical_tags={})
  return children
 def returned(self,index,owner46,wiretag16,echo_generation4,data,meta92,legacy_identity192):
  require(self.live is not None and self.live['phase']=='assembly','held assembly owner')
  require(type(index)is int and 0<=index<len(self.live['children']),'real child index')
  c=self.live['children'][index]
  require(owner46==c['owner46'] and type(echo_generation4)is int and 0<=echo_generation4<16 and meta92==c['meta92'] and legacy_identity192==c['legacy_identity192'],'restored original owner and explicit backend generation echo')
  require(type(wiretag16)is int and 0<=wiretag16<65536 and wiretag16>>12==echo_generation4,'full16 backend token: independent backend gen4 + physical12')
  require(index not in self.live['data'] and isinstance(data,bytes) and len(data)==32,'single exact32B owned return')
  key=(c['stack'],wiretag16&4095)
  require(key not in self.live['physical_tags'],'physical tag retained until reverse, no early reuse')
  self.live['physical_tags'][key]=index;self.live['data'][index]=data
  if len(self.live['data'])==len(self.live['children']):self.live['phase']='local_write'
 def assembled(self):
  require(self.live is not None and self.live['phase']=='local_write','all child bytes before write')
  return b''.join(self.live['data'][i] for i in range(len(self.live['children'])))
 def capture_identity(self):
  require(self.live is not None,'live bound parent')
  return (self.live['parent']['owner46']<<(9 if self.live['kind']=='KV_read' else 10))|self.live['RFslot9']
 def advance(self,event,owner_capture):
  require(self.live is not None and owner_capture==self.capture_identity(),'retained assembly parent owner46 on actual accepted SM port')
  ack='both_shared_bank_ACK' if self.live['kind']=='C0' else 'common_RF_ACK55'
  chain={'local_write':ack,'visible':'metadata_visible','consumer':'actual_consumer','reverse':'matched_reverse_CDC'}
  require(chain.get(self.live['phase'])==event,'writeACK -> visible -> consumer -> reverse exact order')
  self.live['phase']={'local_write':'visible','visible':'consumer','consumer':'reverse','reverse':'drain'}[self.live['phase']]
 def retire(self,copies):
  fields={'provider','assembler','RF_ACK','visible','consumer','child_reverse','parent_reverse','forward_CDC','reverse_CDC'}
  require(self.live is not None and self.live['phase']=='drain' and set(copies)==fields,'all named source copies, not local outstanding count')
  require(all(type(v)is int and v==0 for v in copies.values()),'all-copy emptiness before modulo reuse')
  self.last_generation=self.live['children'][0]['generation4'];self.live=None

def CDC_pair(receipt,authority):
 require(set(receipt)=={'sender_domain','receiver_domain','sender_edge','receiver_edge','token'} and set(authority)=={'sender_domain','receiver_domain','token'},'paired source CDC ABI')
 require(all(receipt[k]==authority[k] for k in authority),'actual source sender/receiver domains and owner token, not arbitrary nonempty strings')
 require(all(type(authority[k])is str and authority[k] for k in authority),'nonempty frozen port/domain authority required')
 require(all(type(receipt[k])is int and receipt[k]>=0 for k in ('sender_edge','receiver_edge')),'actual domain edge ordinals')
 return dict(source_pair_matched=True,physical_wait_upper=None,hardware_admitted=False)
def overlap(a,b,guard=0):
 return a[0]<b[2]+guard-1e-6 and b[0]<a[2]+guard-1e-6 and a[1]<b[3]+guard-1e-6 and b[1]<a[3]+guard-1e-6

def selected_context(scene,name):
 """Explicit paid enlargement of retained inter-SM cuts, inside same die.

 Body and macro shapes are unchanged. Source placements get exact offsets;
 no source ODB/RTL admission is inferred. Transport shares one finite packet
 bus per named corridor; independently queued issuers are serialized at ingress.
 """
 import copy
 m=copy.deepcopy(scene['models'][name]);xs=sorted(set(p['bbox_um'][0] for p in m['SM_placements']));ys=sorted(set(p['bbox_um'][1] for p in m['SM_placements']))
 moves=[]
 for p in m['SM_placements']:
  col=xs.index(p['bbox_um'][0]);row=ys.index(p['bbox_um'][1]);dx=64*(col-3.5) if name=='Qwen' else (-64*(4-col) if col<4 else 64*(col-3));dy=48*(row-1.5) if name=='Qwen' else 0
  for key in ('bbox_um','retained_actual_body_bbox_um'):p[key]=[v+(dx if i%2==0 else dy) for i,v in enumerate(p[key])]
  p['service_origin_um']=[p['service_origin_um'][0]+dx,p['service_origin_um'][1]+dy]
  moves.append(dict(SM=p['SM'],offset_um=[dx,dy],macro_and_local_service_offsets_identical=True))
 # Relocate external array-edge private guides, retaining their layer sets
 # and real L2-end x anchors. These are explicit prospective guide rectangles.
 for r in m['retained_nonSM_reservations']:
  if r['name'].startswith('private_'):
   r['source_bbox_um']=list(r['bbox_um']);box=r['bbox_um'];left='_s0_' in r['name'] or '_n0_' in r['name'];dx=-224 if left else 224
   if r['name'].endswith('vertical'):
    box[0]+=dx;box[2]+=dx
    if '_s' in r['name']:box[1]-=48;box[3]-=72
    else:box[1]+=24;box[3]+=48
   else:
    box[0 if left else 2]+=dx
    dy=(-48 if '_s' in r['name'] else 48) if r['name'].endswith('escape') else (-72 if '_s' in r['name'] else 24)
    box[1]+=dy;box[3]+=dy
   r['relocation_required']=True;r['actual_implementation_bound']=False
 m['selected_source_offsets']=moves
 m['selected_context_conflicts']=[dict(SM=p['SM'],obstacle=r['name']) for p in m['SM_placements'] for r in m['retained_nonSM_reservations'] if overlap(p['bbox_um'],r['bbox_um'])]
 cuts=[]
 for c in m['corridor_cuts']:
  extra=64 if c['axis']=='X' else (48 if name=='Qwen' else 0)
  extra_tracks=0;guard=0
  for layer,v in c['layers'].items():
   pitch=v['pitch_DBU']/1000
   extra_tracks+=math.floor(extra/pitch*.5)
   if extra:guard+=math.ceil(2*2.088/pitch)
  cuts.append(dict(owner=c['owner'],axis=c['axis'],source_bbox_um=c['bbox_um'],
   selected_added_span_um=extra,source_layers=c['layers'],source_signal_capacity_tracks=c['signal_capacity_tracks'],
   retained_tracks=c['demand_tracks'],new_packet_and_owner_tracks=1397,
   added_halfreserve_tracks=extra_tracks,new_parent_ring_end_guard_tracks=guard,
   margin_tracks=c['signal_capacity_tracks']+extra_tracks-guard-c['demand_tracks']-1397,
   source_clock_PG_50pct_reserve_retained=True,PDN_actual_build_credit=False,
   bus_ownership='one shared registered packet bus, RR bounded issuer grants; not36 independent bundles'))
 m['selected_cuts']=cuts
 return m

def floorplan(scene,name):
 """Selected additive reservations inside the unchanged complete die.

 Slots are checked against all retained SM/service/PHY/L2/hub/private-route
 rectangles. Route *cuts* are explicitly separate from slot-area admission.
 """
 m=selected_context(scene,name);slots=[]
 if name=='Qwen':
  origins=[(25900+1900*x,2620+1850*y) for y in range(11) for x in range(3)][:32]
 else:
  origins=[(900+2100*x,2450) for x in range(12)]
  origins += [(9950+2100*x,y+1850*r) for y in (4320,17560) for r in range(2) for x in range(5)]
 obstacles=[dict(name='SM'+str(s['SM']),bbox_um=s['bbox_um']) for s in m['SM_placements']]+m['retained_nonSM_reservations']
 conflicts=[];die=m['complete_die_um'];max_hops=0
 for i,(x,y) in enumerate(origins):
  box=[x,y,x+(1600 if name=='Qwen' else 1800),y+1550];require(box[2]<die[0]-20 and box[3]<die[1]-20,'selected die bounds')
  for o in obstacles:
   if overlap(box,o['bbox_um'],2.088):conflicts.append(dict(slot=i,obstacle=o['name']))
  sm=m['SM_placements'][i];start=[sm['service_origin_um'][0],sm['service_origin_um'][1]];finish=[x+(800 if name=='Qwen' else 900),y+775]
  distance=abs(start[0]-finish[0])+abs(start[1]-finish[1]);L2=[r for r in m['retained_nonSM_reservations'] if r['name'].startswith('l2_')]
  tail=max(abs(finish[0]-(r['bbox_um'][0]+r['bbox_um'][2])/2)+abs(finish[1]-(r['bbox_um'][1]+r['bbox_um'][3])/2) for r in L2)
  hops=math.ceil((distance+tail)/504)+4;max_hops=max(max_hops,hops)
  slots.append(dict(SM=i,bbox_um=box,caller_source_um=start,adapter_center_um=finish,
   direct_L1_um=distance,L2_tail_max_L1_um=tail,minimum_pipeline_hops=hops,clock_route_buffer_count_min=math.ceil(distance/8),
   routing_path_is_not_admitted=True))
 return dict(slots=slots,count=len(slots),reserved_area_mm2=32*(1600 if name=='Qwen' else 1800)*1550/1e6,
  complete_die_um=die,retained_context_occupied_mm2=m['area']['complete_reserved_occupancy_mm2'],
  complete_context_plus_new_slots_mm2=m['area']['complete_reserved_occupancy_mm2']+32*(1600 if name=='Qwen' else 1800)*1550/1e6,
  die_area_mm2=m['area']['die_mm2'],obstacle_conflicts=conflicts,area_reservation_geometry_pass=not conflicts and not m['selected_context_conflicts'],
  max_caller_to_adapter_hops=max_hops,parent_ring_guard_um=2.088,
  selected_context_conflicts=m['selected_context_conflicts'],
  selected_private_guides=[r for r in m['retained_nonSM_reservations'] if r['name'].startswith('private_')],
  selected_source_offsets=m['selected_source_offsets'],selected_corridor_cuts=m['selected_cuts'],
  selected_corridor_single_bus_screens_pass=all(c['margin_tracks']>=0 for c in m['selected_cuts']),
  constructive_route_cut_assignment=None,route_admission=False)

def episode(n,hops,backend_ns=549.149,contenders=36,hold_edges=8,CORE_period_ns=1.0):
 """Prospective bounded read-tile service; source mapper remains serialized.

 The bound assumes each competing tile has <=16 children; grants round robin
 in the proposed successor, accepted eligibility every bounded backend service
 interval, <=hold_edges held sink edges. It is conditional, not installed rate.
 """
 require(0<n<=16 and contenders>=1 and backend_ns>0 and hold_edges>=1 and CORE_period_ns>0,'positive finite model assumptions')
 # 7 source return-arb edges +12 owner-lookup +1 held-output capture +1
 # accept. Price CORE at1ns as a provisional parameter; not source-qualified.
 stages=dict(caller_decode_FAST=2,forward_FAST=hops,request_CDC_CORE=2,allocation_CORE=2,
  backend_service_ns=backend_ns,source_return_mapper_CORE=7,source_owner_lookup_CORE=12,W2_match_hold_CORE=2,W2_request_selection_CORE=1,parent_lookup_CORE=2,
  owned_capture_CORE=1,return_CDC_FAST=2,reverse_route_FAST=hops,
  assembly_FAST=2,local_write_FAST=1,common_ACK_FAST=2,visible_FAST=2,
  consumer_FAST=hold_edges,reverse_CDC_CORE=2,all_copy_barrier_CORE=2,reverse_grant_CORE=1)
 fast=sum(v for k,v in stages.items() if k.endswith('_FAST'))/1.2
 core=sum(v for k,v in stages.items() if k.endswith('_CORE'))*CORE_period_ns
 service=backend_ns+(21+2+2+2+1)*CORE_period_ns+hold_edges/1.2
 ahead=(contenders-1)*16
 wait=ahead*service
 return dict(stages=stages,CORE_period_ns_provisional=CORE_period_ns,FAST_period_ns_target=1/1.2,
  accepted_children=n,max_competing_children_ahead=ahead,grant_wait_upper_ns_assumed=wait,
  uncontended_tile_upper_ns_assumed=n*service+fast+core,
  contended_tile_upper_ns_assumed=wait+n*service+fast+core,
  reuse_wait_upper_ns_assumed=contenders*16*service+fast+core+4*CORE_period_ns+4/1.2,whole_token_ns=None,
  actual_contender_calendar_bound=False,installed_physical_bound=False)

def outputs():
 src=inputs();f0=json.loads(src['F0.json']);canonical_contract=json.loads(src['canonical.json']);scene=json.loads(src['scene.json'])
 require(canonical_contract['canonical_owner']['bits']==46 and canonical_contract['W4']['capture_bits_per_SM']==55,'canonical parent fullwidth46/55')
 require('NC=6' in src['system.sv'].decode() and 'return_arb==6' in src['provider.sv'].decode(),'actual NC6 and selected serialized r14 successor')
 require('remaining_PC' in src['tag_owner.sv'].decode() and 'req.id' in src['tag_owner.sv'].decode(),'actual private identity restoration')
 require('CORE=F(1000)' in src['native_provider.py'].decode(),'source preset CORE1000ps; not clock closure')
 require('byte//512' in src['microvm.py'].decode(),'DS addressed shared stripe source')
 plans={name:floorplan(scene,name) for name in ('Qwen','DeepSeek')}
 hops=max(p['max_caller_to_adapter_hops'] for p in plans.values())
 W2=json.loads(src['W2_composition.json']);require(W2['p_wr_done_ready_required'] and W2['W2_model_costs']['full_wrapper_variant']['NC']==6,'latest W2 full NC6 held ready freeze')
 W2gross=W2['W2_model_costs']['full_wrapper_variant']['gross128PC50pct_slot_mm2_ASSUMED']
 # Source identity192, native request455 / return465 remain intact. Fullwidth
 # generation4 and physicalPC7 are separate sidebands, not overwritten IDs.
 connector=json.loads(src['connector_costs.json']);require(connector['sidecar_source_metadata_bits']==92,'source meta92 freeze')
 req=protected(455+92);ret=protected(465+92+4)
 # Minimal selected path: four stack endpoints, 32 per-SM endpoints. Header
 # and payload are conservatively charged together; no seven-client table.
 lanes=36;pipeline_bits=hops*lanes*2*(req+ret+protected(7))
 pipeline_gates=2*pipeline_bits+2*hops*lanes*768
 pipeline_area=(pipeline_bits*.2916+pipeline_gates*.3)/.5/1e6
 # 2 complete512B assembly seats/SM, 16 children/seat, independent fullowner
 # plus physical16 and beat5, original source requester retained at realSMport.
 assembly_bits=32*2*(protected(4096)+16*protected(46+16+5+1)+protected(32))
 gate_bits=32*2*protected(46+9+6+9)
 W4_bits=32*2*protected(55) # leaf + SIMD, gen already inside owner46
 W6_bits=32*protected(55+9)
 # Per physical-tag explicit generation retention, reverse-held validity and
 # matched child generation. Existing owner192 macros are not charged twice.
 tag_extension_bits=4*4096*protected(92+4+1+1)
 parent_row_fields=dict(native_owner64=64,native_generation64=64,programPC12=12,rank1=1,SM5=5,parent_capture55=55,
  versions_witness_ptr64=64,homeid32=32,readerlease64=64,frame_mask16=16,format8=8,provider_producer64=64,transport32=32,caller16=16,provider_class6=6,shared_slot10=10,irs_slot5=5,irs_serial32=32)
 parent_directory_bits=64*protected(sum(parent_row_fields.values()))
 FIFOs=36*2*(16*(req+ret)+2*protected(50))
 decode_xor_gates=32*(5*2+34);decode_regs=32*protected(34+7+1)
 new_bits=pipeline_bits+assembly_bits+gate_bits+W4_bits+W6_bits+tag_extension_bits+FIFOs+decode_regs+parent_directory_bits
 switch_gates=4*31*req*2+32*3*ret*2
 control_gates=2*(assembly_bits+gate_bits+W4_bits+W6_bits+tag_extension_bits+FIFOs+parent_directory_bits)+switch_gates+decode_xor_gates
 nonpipe_area=((new_bits-pipeline_bits)*.2916+control_gates*.3)/.5/1e6
 # Conservative keep all non-pipeline predecessor costs, replace pipeline
 # once; source return/command logic is retained rather than optimistically free.
 retained_area=f0['F0_allocations']['Qwen']['candidate_complete_bridge_screen_upper_mm2']-f0['pipeline']['pipeline_FF_control_footprint_mm2_ASSUMED']
 source_cap=f0['clock']['worst_source_SS_FF_CLK_capacitance_ff'];buf_area=f0['clock']['buffer_TT_geometric_area_um2']
 repeats=sum(s['clock_route_buffer_count_min'] for p in plans.values() for s in p['slots'])
 tree_buffers=math.ceil(new_bits/24)+math.ceil(new_bits/24**2)+math.ceil(new_bits/24**3)
 clock_area=(tree_buffers+repeats)*buf_area/.5/1e6
 W4_ACK=json.loads(src['W4_ACK_price.json']);require(W4_ACK['SMs']==32,'actual W4 common ACK mismatch price')
 W4_match_area=W4_ACK['footprint_delta_um2_ASSUMED']/1e6
 total_area=retained_area+pipeline_area+nonpipe_area+clock_area+W4_match_area
 for p in plans.values():
  p.update(complete_bridge_upper_mm2_ASSUMED=total_area,area_margin_mm2=p['reserved_area_mm2']-total_area-W2gross,
   full_slot_area_screen_pass=p['area_reservation_geometry_pass'] and total_area+W2gross<=p['reserved_area_mm2'],
   per_slot_service_allocation_mm2=p['reserved_area_mm2']/32,
   declared_reserve_for_PG_clock_OBS_tracks=0.5,
   signal_track_demand_per_SM=req+ret+55+46,
   corridor300um_M7_M9_halfreserve_capacity=math.floor(300/.064*.5)+math.floor(300/.080*.5),
   exact_PG_via_clock_cut_exclusion_binding=None,
   retained_corridor_additive_cut_screens=[dict(owner=c['owner'],source_capacity=c['signal_capacity_tracks'],retained_demand=c['demand_tracks'],
    new_single_adapter_bundle_demand=req+ret+55+46,margin_after_single_bundle=c['signal_capacity_tracks']-c['demand_tracks']-req-ret-55-46)
    for c in scene['models'][next(name for name,v in plans.items() if v is p)]['corridor_cuts']])
 examples=[dict(byte=b,translated=physical(b),incompatible_old_low7_PC=(b//32)&127) for b in (0,128,512,16384,33554432)]
 e={name:{kind:episode(2 if kind=='C0' else 16,p['max_caller_to_adapter_hops']) for kind in ('C0','KV_read')} for name,p in plans.items()}
 CORE_sensitivity=[episode(16,hops,CORE_period_ns=p) for p in (1/1.2,1.0,1/0.9,2.0)]
 sensitivity=[dict(backend_ns=b,eligible_contenders=c,hold_edges=w,**episode(16,hops,b,c,w)) for b,c,w in ((549.149,1,8),(549.149,36,8),(1098.298,36,32),(549.149,36,128))]
 model=dict(schema='HBM_W5_W10_FULLWIDTH_R14_CALLER_MODEL_R4',source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},
  status='PROSPECTIVE_COMPONENT_MODEL_ROUTING_ADMISSION_PENDING',hardware_admitted=False,engine_build_allowed=False,
  selected_path=dict(provider='22539 W1-corrected ot_hbm_r14_stack_provider successor',PC_service_W2_wrapper_on_critical_path=True,current_installed_route_bypasses_W2=True,
   W2_responsibility='r14 tag_owner exact immutable restoration and successor gen4 echo/reverse-held physical tag',
   NC=6,KV_client=5,C0_client_proposed=0,directory_client_added=False,
   path=['accepted perSM C0/KV read issuer','stripe/hash adapter','four r14 stack request endpoints','32PC queues/stack','one commandbus/stack',
    'r14 serial returnarb7','private identity lookup12','W2 logical matched held completion2','perSM assembly','RF55 commonACK or shared64 bothACK','W6 consumer','matched reverse CDC','allcopy drain'],
   assembly_parent_owner='pre-bound parent directory55, child meta92 parentref32; never first/last child recomputation',
   RF512B_assembly_children=16,C0_shared64B_assembly_children=2,
   minimum_sector_route_R14_LEN6=1,minimum_sector_route_R14_BEAT5=0,p_wr_done_ready_required_even_readonly_wrapper=True,
   semantic_WRvisibility_not_admitted=True,
   read_only=True,original_tag32_unchanged=True,backend_wiretag16_unchanged=True,explicit_gen4_backend_echo_successor_required=True,
   source_physical_tag_reclamation_must_move_from_owned_accept_to_matched_reverse=True,
   no_descriptor_fetch_in_minimal_read_path='issuer supplies already compiled sector addresses; immutable homes remain compiler witness',
   runtime_dynamic_descriptor_paths_not_admitted=True,
   DS_source_address_binding='archived shared SectorProvider logs exact fourstack stripe; DS PC hash selected r14 successor, physical validation pending',
   C0_client0_source_adapter_to_be_installed=True),
  canonical=dict(owner_bits=46,fields={'PC':7,'client':3,'originaltag':32,'generation':4},RF_ACK_bits=55,
   generation_in_owner_not_double_charged=True,requester_SM='real perSM accepted port',backend_original_private_identity_bits=192),
  translation=dict(examples=examples,PC_sideband_not_low7_address=True,overwrite_address_for_dispatch=False,
   XOR_decode_gate_equivalents_ASSUMED=decode_xor_gates,capture_bits=decode_regs,latency_FAST_edges=2),
  resource_ledger=dict(MACs_added=0,replicas_SM=32,stacks=4,request_boundary_bits=req,return_boundary_bits=ret,
   W2_bound_composition=W2,
   W2_gross_bound_mm2_unreconciled=W2gross,W2_matched_old_debit_mm2=None,W2_net_increment_mm2=None,
   F0_once_only_rule='F0old - exact matched oldW2 debit + grossNC6; no unrelated private context subtraction',
   W2_gross_is_not_blindly_charged=True,
   physical_area_reservation_upper_with_unreconciled_gross=total_area+W2gross,
   pipeline_seats=2,pipeline_II_candidate=1,pipeline_hops_L1_lower_screen=hops,pipeline_physical_detour_upper_unbound=True,pipeline_protected_bits=pipeline_bits,
   assembly_bits=assembly_bits,W5_owner_bits=gate_bits,W4_leaf_plus_SIMD_bits=W4_bits,W4_ACK_match_price=W4_ACK,W4_ACK_match_area_mm2=W4_match_area,W6_bits=W6_bits,
   same_CAM_index_meta92_backendgen4_lifetime_control_bits=tag_extension_bits,
   sidecar_realization='protected FF upper substitute; source128x256 macro alternative not debited',
   sidecar_no_second_CAM=True,parent_directory_rows=64,parent_directory_fields=parent_row_fields,parent_directory_bits=parent_directory_bits,
   parent_directory_ports={'allocate':1,'assembly_parent_read':1,'reverse_update':1},parent_lookup_CORE_edges=2,FIFO_bits=FIFOs,
   full_new_protected_bits=new_bits,retained_predecessor_nonpipeline_area_mm2=retained_area,
   pipeline_area_mm2_ASSUMED=pipeline_area,other_new_area_mm2_ASSUMED=nonpipe_area,clock_area_mm2_TT_screen=clock_area,
   complete_service_area_upper_mm2_ASSUMED=total_area,mux_gate_equivalents_ASSUMED=switch_gates,
   FF_clock_load_ff_ASSUMED=new_bits*source_cap,clock_tree_buffer_count=tree_buffers,route_repeater_count=repeats,
   SRAM_ports_added=0,identity_retention_read_write_ports_perSM=[1,1],assembly_ports_perSM=[1,1],
   original_RF_shared_L2_macros_retained=True,old_source_costs_not_zeroed=True),
  ports=dict(stack_request_B_per_CORE_edge=32,stack_shared_command_count_per_CORE_edge=1,
   stack_serial_return_B_per_CORE_edge_upper=32/21,fourstack_return_B_per_CORE_edge_upper=128/21,
   W4_RF_write_B=512,C0_shared_write_B=64,RF_owner_wires=55,W6_owner_wires=55,
   pipeline_II1_does_not_qualify_provider_roof=True,CORE_period_ns_assumed=1.0,FAST_target_ns=1/1.2,
   hypothetical_parallel_provider_upgrade_not_in_baseline=True),
  floorplan=plans,finite_episodes=e,sensitivity=sensitivity,CORE_clock_sensitivity=CORE_sensitivity,
  local_component_build_scope=dict(parent_route_qualification_not_prerequisite=True,
   earliest_RTL_candidate='default-off accepted perSM read issuer/stripe/hash translator and owner46 child assembler',
   selected_blocks=['W2 r14 private owner gen4/deferred tag reuse successor','W4 RF55 held ACK','W6 same55 visible/consumer/reverse'],
   parent_composed_build_remains_pending_route_cuts=True,
   local_prebuild_gate='owner resource/port/timing/reset model admission, not installed parent hardware'),
  bounded_eligibility_assumptions=dict(route_hops_is_L1_screen_not_routed_upper=True,requesters=36,requester_scope='proposed32SM one-owned-tile gates plus4 source nonSM ingress; not emitted-program contender proof',
   max_tile_children=16,larger_operations='mandatory tiled issuer backpressure and chunk loop, not a documented-operation size cap',proposed_round_robin=True,
   each_eligible_request_gets_service_within_backend_bound=True,backend_bound_ns=549.149,
   sink_hold_bound_FAST_edges=8,source_continuous_priority_is_not_assumed_fair=True,
   actual_emitted_Dewey_contender_validation_pending=True,miss_cost_if_runtime_directory_enabled=f0['runtime_directory']['Qwen']['profile']),
  reuse=dict(generation_bits=4,arbitrary_program_or_generation_cap=False,all_copy_names=['provider','assembler','RF_ACK','visible','consumer','child_reverse','parent_reverse','forward_CDC','reverse_CDC'],
   reuse_only_after_allcopies_and_reverse_CDC=True,reset_requires_paired_backend_flush_not_local_reset=True,
   prospective_reset_drain_positive_ns=episode(16,hops)['reuse_wait_upper_ns_assumed'],reset_receipt_source_implementation_pending=True),
  clock=dict(FAST_hz=1200000000,CORE_period_ns_provisional=1,CORE_preset_origin='archived native_provider.py CORE=F(1000); software sizing preset, no SS/FF claim',SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
   analytical_wire_reach_um=504,source_clock_branch_limit_um=8,SS_FF_qualification=False),
  remaining_before_composed_build=['exact new routes and PG/via/OBS cut exclusions','source-bound reset/drain handshake ports',
   'actual native C0/client0 and KV/client5 issuer body installation','exact oldW2 debit and W6 component price reconcile once; RFACK c4c794 included','Dewey selected calendar eligibility assumptions validate'],
  whole_token_ns=None,all_four_headlines_UNKNOWN=True)
 return {'model.json':canonical(model),'directed_replay.json':canonical(dict(translations=examples,switch=directed_switch(),native_callers=directed_callers()))}

def directed_callers():
 out=[];zeros=dict.fromkeys(('provider','assembler','RF_ACK','visible','consumer','child_reverse','parent_reverse','forward_CDC','reverse_CDC'),0)
 for model in ('Qwen','DeepSeek'):
  for kind in ('C0','KV_read'):
   a=NativeCaller(17);payload=None
   for token in range(33): # exercised two wraps, no runtime cap in adapter
    n=2 if kind=='C0' else 16;c=a.accept(model,kind,33554432,list(range(token*n,token*n+n)),token%16,12,dict(reference32=token,owner46=(5<<36 if kind=='KV_read' else 0)|(123<<4)|(token%16),native_owner64=2**40+token,native_generation64=token,format='raw_U32_frame' if kind=='KV_read' else 'shared64_bytes',legacy=dict(die=0,producer=2**48+token,transport=0xabcdef01,caller=17,client=2 if kind=='KV_read' else 8,irs_slot=1,irs_serial=token)))
    for child in reversed(c):a.returned(child['index'],child['owner46'],child['index'],0,bytes([child['index']])*32,child['meta92'],child['legacy_identity192'])
    payload=a.assembled();a.advance('both_shared_bank_ACK' if kind=='C0' else 'common_RF_ACK55',a.capture_identity())
    for event in ('metadata_visible','actual_consumer','matched_reverse_CDC'):a.advance(event,a.capture_identity())
    a.retire(zeros)
   out.append(dict(model=model,kind=kind,tokens=33,wraps=2,assembled_bytes=len(payload),payload_sha256=hashlib.sha256(payload).hexdigest(),actual_hardware=False))
 return out
def directed_switch():
 s=BankedSwitch(36,32);grants=[]
 for i in range(36):
  rows={j:dict(destination=7,payload=bytes([j])*32,owner='owner'+str(j)) for j in range(36)}
  accepted=s.step(rows,[True]*32);require(len(accepted)==1,'hot PC serializes onegrant');grants.extend(accepted)
 require(grants==list(range(36)),'directed all eligible 36way RR order')
 return dict(hot_PC_grants=grants,grant_edges=36,candidate_only=True,installed_fairness_credit=False)
def verify_manifest():
 root=Path(__file__).resolve().parents[1]
 manifest=json.loads((BASE/'artifact_manifest.json').read_bytes())
 for row in manifest['artifacts']+manifest['source_pins']:
  path=(root/row['path']).resolve();require(path.is_relative_to(root),'manifest path scope')
  raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'],'artifact/source hash '+row['path'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
 if a.verify:verify_manifest()
 for n,v in outputs().items():
  if a.verify:require((BASE/n).read_bytes()==v,'exact W5/W10 replay '+n)
  else:
   require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True);(a.output/n).write_bytes(v)
 print('PASS fullwidth r14 caller/model replay; prospective bounds only; routing/build admission pending')
if __name__=='__main__':main()
