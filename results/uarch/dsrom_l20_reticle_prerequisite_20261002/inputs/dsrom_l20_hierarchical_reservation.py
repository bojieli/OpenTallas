#!/usr/bin/env python3
"""Source-pinned first-principles reservation; no elaboration, payload or physical tool.
This is an analytical resource inventory, not a synthesizer or timing certificate.
"""
import ast,hashlib,json,math,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REAL='4e38326d6f361bc85e660f48c59c355e2bb95274'
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a'
OUT=ROOT/'results/uarch/dsrom_l20_hierarchical_reservation_20261002'
PINS={}
def raw(path,rev=REAL):
 b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
 PINS[rev+':'+path]={'commit':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
 return b

def emit(name,obj):
 b=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();p=OUT/name
 if p.exists():assert p.read_bytes()==b,'immutable evidence differs '+str(p)
 else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)

def clean(s):return re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
def value(s,e):
 s=s.strip().replace('$clog2','clog2')
 s=re.sub(r'\(([^()]*)\)\s*\?\s*([^:]+):\s*(.*)',lambda m:'('+m[2]+' if '+m[1]+' else '+m[3]+')',s)
 s=re.sub(r"(?:\d+)?'([sS]?)([dDhHbB])([0-9a-fA-F_]+)",lambda m:str(int(m[3].replace('_',''),{'d':10,'h':16,'b':2}[m[2].lower()])),s)
 return int(eval(s,{'__builtins__':{},'clog2':lambda n:math.ceil(math.log2(n)) if n>1 else 0},e))
def width(s,e):
 if not s:return 1
 a,b=s[1:-1].split(':');return abs(value(a,e)-value(b,e))+1

def census(mods,name,overrides):
 path,whole,body=mods[name];s=clean(body);e=dict(overrides)
 # Parameters/localparams for these selected control modules contain integer expressions.
 for _ in range(5):
  for declaration in re.finditer(r'\b(?:parameter|localparam)\s+(?:integer\s+)?([^;\n]+)',s):
   for term in declaration[1].split(','):
    m=re.match(r'\s*(\w+)\s*=\s*(.*)',term)
    if m and m[1] not in e:
     try:e[m[1]]=value(m[2].strip(),e)
     except (NameError,SyntaxError,TypeError,ValueError):pass
 # Localfunctions are combinational; temporary registers there are never FFs.
 s=re.sub(r'\bfunction\b.*?\bendfunction\b','',s,flags=re.S)
 seq=set()
 for assignment in re.finditer(r'<=',s):
  i=assignment.start()-1
  while i>=0 and s[i].isspace():i-=1
  if i>=0 and s[i]=='}':
   j=s.rfind('{',0,i);seq.update(re.findall(r'\b[A-Za-z_]\w*\b',s[j+1:i]));continue
  while i>=0 and s[i]==']':
   level=1;i-=1
   while i>=0 and level:
    if s[i]==']':level+=1
    if s[i]=='[':level-=1
    i-=1
   while i>=0 and s[i].isspace():i-=1
  end=i+1
  while i>=0 and (s[i].isalnum() or s[i]=='_'):i-=1
  if end>i+1:seq.add(s[i+1:end])
 fields=[];seen=set()
 for m in re.finditer(r'\boutput\s+reg\s*(signed\s+)?(\[[^\]]+\])?\s*(\w+)',s):
  if m[3] in seq:fields.append({'name':m[3],'bits':width(m[2],e),'declaration':m[0]});seen.add(m[3])
 # Body declarations only, so output port commas cannot consume subsequent input ports.
 body_only=s[s.index(');')+2:]
 for m in re.finditer(r'\breg\s*(signed\s+)?(\[[^\]]+\])?\s*([^;]+);',body_only):
  for decl in m[3].split(','):
   n=re.match(r'\s*(\w+)((?:\s*\[[^\]]+\])*)\s*$',decl)
   if not n or n[1] not in seq or n[1] in seen:continue
   count=math.prod(width(d,e) for d in re.findall(r'\[[^\]]+\]',n[2]))
   fields.append({'name':n[1],'bits':width(m[2],e)*count,'declaration':m[0].strip()});seen.add(n[1])
 return {'module':name,'source_path':path,'parameters':e,'sequential_declaration_fields':fields,'state_bits':sum(f['bits'] for f in fields),'scope':'Clock-assigned declarations; source lexical inventory, not elaboration. Generated arithmetic leaves separately priced; fields in alternative control branches conservatively retained.'}

def main():
 manifest=raw('tools/w17_current_fastpp_l20_sources.txt').decode().split();assert len(manifest)==125
 mods={};blobs={}
 for p in manifest+['rtl/hdc/v41x/ot_hdc_v41x_attn.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv']:
  s=raw(p).decode();blobs[p]=s
  for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',clean(s),re.S):mods[m[1]]=(p,s,m[0])
 unit=json.loads(raw('results/arch/arch_budget_v41.json'))['unit_areas_um2'];FF=.2916;MUX=.2;UTIL=.5
 p={'AW':30,'NW':21,'MP':1,'IH':32,'G':4,'IL':8,'W':16,'NPC':32,'WB':32,'GA':24,'HAW':30,'HW':23,'TAGW':16,'LENW':4,'BEATW':4,'DW':256,'RING':1,'RING_RSB':64,'RING_RTAIL':32,'RING_WB':32,'RING_GA':24,'SHARDED':0,'SLICE_SECTORS':0,'NL':256,'MD':128,'RL':2,'M':1,'NKT':1,'NBQ':4}
 inventories=[]
 for name,rep in [('ot_hdc_v41x_idx_kctl_ring',4),('ot_hdc_v41x_idx_kdata',4),('ot_hdc_v41x_idx_kstream_ring',4),('ot_hdc_v41x_idx_quarter_join',1),('ot_hdc_v41x_idx_pool_adapt',1),('ot_hdc_v41x_idx_pool_batch',1),('ot_hdc_v41x_idx_pool_finish',1),('ot_hdc_v41x_idx_pcol',1),('ot_hdc_v41x_idx_pool_kwr',1)]:
  row=census(mods,name,p);row['replicas']=rep;row['total_state_bits']=rep*row['state_bits'];inventories.append(row)
 # Count the wrapper and head-sum state separately from arithmetic primitives.
 wt=census(mods,'ot_hdc_v41x_wgt_tile',dict(G=4,M=1,KIND=0,LB=5,PMIN_LG=0,AW=20,NBW=14,RWW=16,EIW=9,TGW=4,RL=2,OCRED=128,POOL=1));wt['replicas']=1;wt['total_state_bits']=wt['state_bits'];inventories.append(wt)
 hs=census(mods,'ot_hdc_v41x_idx_hsum',dict(IH=32,NKT=1,NBQ=4))
 for field in hs['sequential_declaration_fields']:
  if field['name'] in ['s1','f1']:field['generate_replicas']=32;field['bits']*=32
 hs['state_bits']=sum(f['bits'] for f in hs['sequential_declaration_fields']);hs['replicas']=1;hs['total_state_bits']=hs['state_bits'];inventories.append(hs)
 explicit_delays={
 'wgt_tile_18_record_taps_95bit':18*95,
 'wgt_split_first_rows_4x33_2cycles':4*33*2,
 'wgt_red4temporal_combiners_LB5_pv_pd_pf':4*5*34,
 'hsum_32head_fault_delay3':32*3,
 'hsum_weighted_terms_8phase_skew17bit':4*17*sum([0,0,3,6,9,12,15,18]),
 'hsum_chunk_tree_fault_flags3x31':31*3,
 'hsum_valid_keep_ref_4bits_LAT31':4*31}
 kd=next(r for r in inventories if r['module']=='ot_hdc_v41x_idx_kdata')
 assert next(f['bits'] for f in kd['sequential_declaration_fields'] if f['name']=='rob')==1048576
 rob=4*32*32*1024;assert rob==4194304
 sequential=sum(r['total_state_bits'] for r in inventories)+sum(explicit_delays.values())
 # Explicit memory/address selection costs, counted once. Upper mux network
 # uses full depth; no SRAM inference, free write enables or read ports assumed.
 muxes={
 'ROB_read_one1024bit_word_each32banks_each4stacks':4*32*31*1024,
 'ROB_write_hold_select_per_stored_bit':rob,
 'ROB_fold_XOR_permutation5stages_32banks1024bit':4*5*32*1024,
 'ROB_quarterselect4choices_16keys512bit':4*3*16*512,
 'scale_buffer_read64choices_512bit_perstack':4*63*512,
 'scale_buffer_write_hold_perbit':4*64*512,
 'query_word_network32reads_128words264bit':32*127*264,
 'keywriter256producer_choices_for128slots16bit':128*255*16,
 'keywriter128slot_hold':128*16,
 'finish_metadata_head128choices2bit':127*2}
 # Active source arithmetic hierarchy. Unit measurements price primitive
 # classes only; no whole-engine/clock qualification transfer.
 arith={
 '32_blockdots':32*unit['blockdot_um2'],
 '4_chunk_chains7adds':4*7*unit['fp32_add_um2'],
 'tile_3spatial_tree_nodes_plus4x5temporal_adders':(3+4*5)*unit['fp32_add_um2'],
 'finish_32_head_products_conservative_full_FP32mul':32*unit['fp32_mul_um2'],
 'finish_32heads_chunk_and_tree31adds':31*unit['fp32_add_um2']}
 # Price explicit token/address controller arithmetic from maximum widths:
 # 32 independent generators x4stacks; each g_has 5 add/sub/compare datapaths.
 # Bit-level fulladder/compare bound assumes5twoinputmux-equivalents/bit;
 # no zero-area constant arithmetic. Separate arithmetic/control guard.
 control={
 'reader_generators_4x32x5ops30bit_5gateequiv':4*32*5*30*5*MUX,
 'reader_completion_counters4x32x32x3bit_5gateequiv':4*32*32*3*5*MUX,
 'keywriter_address_compare256x4ops30bit_5gateequiv':256*4*30*5*MUX,
 'query_native_encoder_4x32x16bit_5gateequiv':4*32*16*5*MUX,
 'ring_geometry_4x8ops30bit_5gateequiv':4*8*30*5*MUX}
 cell=sequential*FF+sum(muxes.values())*MUX+sum(arith.values())+sum(control.values())
 idx_placed=cell/UTIL/1e6
 old=json.loads((ROOT/'results/uarch/dsrom_l20_banked_collector_contract_20261002/model.json').read_text())
 orig=json.loads((ROOT/'results/uarch/dsrom_l20_mandatory_service_fixture_20261002/model.json').read_text())
 old_comp=json.loads((ROOT/'results/uarch/dsrom_attention_controller_l20_composition_20261001/model.json').read_text())
 prior39=old['state_ports_area']['full_listed_attention_service_candidate_mm2']
 # A TOPK candidate store belongs to actual X_SEL/SU, not the collector island.
 # Move accounting, preserve the charge. Legacy BF16 reencoder holds are
 # replaced ONLY in the proposed opt-in raw-producer branch; its2304bit row
 # and176sideband registers already appear in the mandatory ledger.
 arrays=old_comp['storage_bits_per_die'];moved_topk=arrays['TOPK_candidate_key_and_ID_arrays']*FF/UTIL/1e6
 obsolete_own=arrays['own_capture_and_encoder_and_encoded_buffers']*FF/UTIL/1e6
 attention_base=prior39-moved_topk-obsolete_own
 # MAC estimate contains no stationary memory; never add a hardtile outline.
 # Non-MAC control and lane combine/merge arithmetic omitted by earlier screen.
 H=16;D=512;TD=32;NL=4;NT=64
 add_counts={'QK_slice_tree_NL_H_(D/TD-1)':NL*H*(D//TD-1),
 'PV_counter_merge_NT_H_MLEV':NT*H*math.ceil(math.log2(math.ceil(640/TD)))}
 extra_arith=sum(add_counts.values())*unit['fp32_add_um2']
 tile_edge_state=NT*(1+1+2+8+512+1+1+2+576+576+2+1+528+33)
 skew_state=NT*(32*18+8*2)*sum([0,0,3,6,9,12,15,18])/8
 # Decoder bound6bitproduct +10bit exp logic and select, perTD shared64tiles.
 deq_bit_gates=NT*TD*(2*4+6*6+11*5+16*4)
 tile_control_bit_gates=NT*(TD*16*2+TD*3*8+2*32*5)
 pv_ring_bits=NT*math.ceil(math.log2(math.ceil(640/TD)))*(D//NT)*H*33
 pv_ring_hold_mux_bits=pv_ring_bits
 attention_extra=(extra_arith+pv_ring_bits*FF+pv_ring_hold_mux_bits*MUX+(tile_edge_state+skew_state)*FF+(deq_bit_gates+tile_control_bit_gates)*MUX)/UTIL/1e6
 attention=attention_base+attention_extra
 # The previous whole-MAC proxy already includes a multiply/add pipeline.
 # Retain it for32768products instead of separately charging31744tile adds.
 audit={'original_39p23175_mm2':prior39,'MAC_cell_um2':32768*unit['mac_bf16_um2'],'MAC_placed_mm2':32768*unit['mac_bf16_um2']/UTIL/1e6,
 'stationary_FF_bits_counted_once':arrays['stationary_payload'],'hardtile_outline_added_mm2':0,'hardtile_source_match':'No attn_tile physical record exists at retained revision or local reachable path; absent abstract cannot replace source inventory.',
 'SRAM_MACRO_actual':0,'NSTAGE':1,'ILV':0,'REPL':0,'PWORDS':1,'engine_stage_FF_bits':arrays['engine_stage_payload'],'optional68_stage_SRAM_macros':'not admitted; existing off-by-default synchronous macro branch changes read latency and requires its own gate',
 'banked_collector_island_gross_included_once_mm2':old['physical_proposal']['island_gross_mm2'],'banked_control_37273bits_outside_macro_gross_placed_mm2':old['state_ports_area']['new_macro_channel_and_logic_placed_candidate_mm2']-old['physical_proposal']['island_gross_mm2'],
 'TOPK_524288bits_reassigned_to_X_SEL_mm2':moved_topk,'charge_removed_from_die':False,'legacy_own_BF16_encoder_20992bits_replaced_mm2':obsolete_own,'replacement_raw_row_already_priced_bits':2304,'replacement_requires_optin_source_gate':True,
 'added_QK_PV_adder_counts':add_counts,'PV_ring_bits_additional_counted_once':pv_ring_bits,'PV_ring_hold_mux_bit_equivalents':pv_ring_hold_mux_bits,'added_arithmetic_control_boundary_placed_mm2':attention_extra,
 'attention_service_corrected_placed_proxy_mm2':attention,'scope':'Proxy cell area at50pct placement; not mapped or hardened. Model dimensions do not assert real placement or routed timing.'}
 # Retained QE and service wrappers: no inactive block-dot pruning or missing
 # DMA/control state credit. Existing payload fields are subtracted by name.
 service_inventory=[]
 overrides=dict(AW=30,NW=21,BL=16,IL=8,NBMAX=192,CHUNK8=1,MP=1,QLB=272,K=512,POS_W=21,VWA=15,HAW=30,TAGW=16,NSLOT=64,NS=4,NL=4)
 service_expected_payload={'ot_chip_v41x_ckv_sel_fetch':2304,'ot_chip_v41x_ckv_sel_ids':10752+15872,'ot_chip_v41x_ckv_stream_merge':33920+26112}
 service_extra_bits=0
 for name,payload_bits in service_expected_payload.items():
  row=census(mods,name,overrides);row['payload_bits_already_priced']=payload_bits;row['extra_control_bits']=row['state_bits']-payload_bits
  assert row['extra_control_bits']>=0
  service_extra_bits+=row['extra_control_bits'];service_inventory.append(row)
 dma=census(mods,'ot_chip_v41x_ckv_selected_dma',dict(overrides,PIPE=1));dma['replicas']=64;dma['payload_bits_already_priced']=64*2304;dma['extra_control_bits']=64*(dma['state_bits']-2304)
 assert dma['extra_control_bits']>=0
 service_extra_bits+=dma['extra_control_bits'];service_inventory.append(dma)
 qe=census(mods,'ot_hdc_v41_qe',overrides)
 qe['inactive_blockdots_not_pruned']=16
 quantizers=[census(mods,n,{}) for n in ['ot_hdc_fp4qdq','ot_hdc_actquant']]
 quantizer_delay_bits=1024*5+1024*9+2*5
 # Shared primitive fmul is counted once; no arithmetic exactness conclusion
 # is borrowed from the separately owned QDQ8 stream.
 quantizer_state=sum(q['state_bits'] for q in quantizers)+quantizer_delay_bits
 quantizer_gate_proxy=(32*14*31+32*8*24)*5*MUX
 qe_extra=((qe['state_bits']+quantizer_state)*FF+16*unit['blockdot_um2']+unit['fp32_mul_um2']+quantizer_gate_proxy)/UTIL/1e6
 # Literal conditional-writeFF arrays need holdmuxes, not free write enables.
 # PVring and collector bank FFmuxes were separately priced above.
 holds={key:arrays[key] for key in ['stationary_payload','engine_stage_payload','transposer_payload','window_stage_payload','CKV_DMA_slots_payload','IDs_table','owned_rank_ID_list']}
 missing_hold_placed=sum(holds.values())*MUX/UTIL/1e6
 service_control_extra=service_extra_bits*FF/UTIL/1e6
 attention+=qe_extra+missing_hold_placed+service_control_extra
 audit.update(service_control_extra_bits=service_extra_bits,service_control_extra_placed_mm2=service_control_extra,
 QE_full_params_state_bits=qe['state_bits'],QE_quantizer_children_state_bits=quantizer_state,QE_quantizer_children=quantizers,QE_quantizer_gate_proxy_cell_um2=quantizer_gate_proxy,QE16_blockdot_and_wrapper_additional_placed_mm2=qe_extra,
 array_conditional_write_hold_mux_bits=holds,array_hold_mux_additional_placed_mm2=missing_hold_placed,
 attention_service_corrected_placed_proxy_mm2=attention)
 fp=json.loads(raw('results/floorplan/v41_pack_refit_w18_e8p5.json'))
 # Reserve every retained region. No allocation credit from another soft region.
 residents=[{'name':r[0],'kind':r[1],'origin_um':r[2:4],'bbox_um':r[4:6],'gross_mm2':r[4]*r[5]/1e6} for r in fp['soft_regions'] if r[0].startswith('HUB_')]
 su_cell=192*unit['su_light_lane_um2']+63*unit['su_lane_um2']+unit['su_lane0_um2']
 # AdditionalTOPKcharge remains independently reserved, not assumed swallowed bySU.
 source_reservations={'attention_service':attention,'indexer_current_pooled':idx_placed,'X_SEL_TOPK_store':moved_topk,'common_controller_cut':.0824539824}
 for r in residents:
  if r['name']!='HUB_ATTENTION':source_reservations[r['name']]=r['gross_mm2']
 source_reservations['all_clock_reset_PG_hold_DFT_unallocated_die_overhead']=.125*fp['geometry']['die_mm2']
 required=attention+idx_placed+moved_topk+.0824539824
 old_att=next(r for r in residents if r['name']=='HUB_ATTENTION')
 # Explicit analytical grow option: reserve a fresh right-side column; do not
 # silently insert into field or release historical21.677 on timing evidence.
 h=old_att['bbox_um'][1];bank=old['physical_proposal']
 ox,oy=old_att['origin_um'];cw=bank['candidate_dedicated_hub_island_bbox_um'][0]
 collector_h=bank['candidate_dedicated_hub_island_bbox_um'][1]
 def grid(v):return math.ceil(v/2.16)*2.16
 def rect(name,x,y,w,height,cost,kind):
  return {'name':name,'origin_um':[x,y],'bbox_um':[w,height],'gross_mm2':w*height/1e6,'required_proxy_mm2':cost,'kind':kind}
 # Explicit adequate outline. Index andTOPKstack under the banked collector;
 # attention maintains64H16TD32 tiles in the adjacent complete rectangle.
 idx_h=grid(idx_placed*1e6/cw);select_h=grid(moved_topk*1e6/cw);cut_h=grid(.0824539824*1e6/cw)
 assert collector_h+idx_h+select_h+cut_h<=h
 attention_without_collector=attention-bank['island_gross_mm2']
 aw=grid(attention_without_collector*1e6/h);required_width=cw+aw
 components=[rect('BANKED_COLLECTOR_MACROS_AND_CLEAR20909TRACK_BAND',ox,oy,cw,collector_h,bank['island_gross_mm2'],'36SRAM_M1-M4_OBS'),
 rect('ACTUAL_POOLED_INDEXER_AND4RING_READERS',ox,oy+collector_h,cw,idx_h,idx_placed,'sourceFF+mux+arithmetic'),
 rect('X_SEL_TOPK_STORE',ox,oy+collector_h+idx_h,cw,select_h,moved_topk,'sourceFF'),
 rect('PROSPECTIVE_COMMON_CONTROLLER_CUT',ox,oy+collector_h+idx_h+select_h,cw,cut_h,.0824539824,'diagnostic_only'),
 rect('ATTENTION64TILES_STATIONARY_STAGE_PVMERGE_WINDOW_RAW_QE_SERVICE',ox+cw,oy,aw,h,attention_without_collector,'full_source_inventory_proxy')]
 for c in components:assert c['gross_mm2']+1e-9>=c['required_proxy_mm2']
 delta_w=max(0,required_width-old_att['bbox_um'][0])
 route_demand={'collector_combined':20909,'collector_read':9229,'collector_write':11680,'index_HBM_all128responses':128*(256+16+4+1+1),'index_quarter_join_to_batch':64*544+64+64+4+2,'mergedKV_to_stage':16966,'directproducer_registered_boundary':203}
 native_grid=json.loads((OUT/'grid_inputs/DS_grid.json').read_text())
 grid_layers={r['name']:r for r in native_grid['layers']}
 assert grid_layers['M2']['direction']==grid_layers['M4']['direction']=='HORIZONTAL'
 # Actual M2 has seven distinct row-offset phases in each270DBU period,
 # not an unrestricted uniform36nm plane. Reserve the worst phase loss.
 m2=next(r for r in native_grid['grids'] if r['layer']=='M2')['Y']
 periods={r[2] for r in m2};assert len(periods)==1
 period=next(iter(periods));phases={r[0]%period for r in m2}
 def clearcap(height):
  m2count=max(0,math.floor(height*1000/period)*len(phases)-len(phases))
  m4count=max(0,math.floor(height*1000/grid_layers['M4']['pitch'])-1)
  return m2count//2+m4count//2
 route_bands={}
 for name,n in route_demand.items():
  height=math.ceil(n/(.5*len(phases)/(period/1000)+.5/(grid_layers['M4']['pitch']/1000))/.024)*.024
  while clearcap(height)<n:height+=.024
  capacity=clearcap(height)
  route_bands[name]={'tracks':n,'M2_M4_clear_height_um':height,'capacity_tracks':capacity,'fits':capacity>=n,'blocking':'Fresh corridor with zero macroOBS intersections; actual DBU1000 M2 seven-phase270 pattern and M4Y48. 50pct reserved for nonsignal/PDN. Pattern extension is a candidate grid policy, not existing die routing admission.'}
 collector_extra_h=grid(max(0,route_bands['collector_combined']['M2_M4_clear_height_um']-bank['M2_M4_channel_height_um']))
 components[0]['bbox_um'][1]+=collector_extra_h
 components[0]['gross_mm2']+=cw*collector_extra_h/1e6
 for c in components[1:4]:c['origin_um'][1]+=collector_extra_h
 # Source OBS remains below the clear band; translated halo4.32 is
 # conservatively outside its floor. No tracks across a macro are credited.
 assert collector_h+collector_extra_h+idx_h+select_h+cut_h<=h
 route_rects=[];cy=oy+h
 for key in ['index_HBM_all128responses','index_quarter_join_to_batch','mergedKV_to_stage','directproducer_registered_boundary']:
  rh=grid(route_bands[key]['M2_M4_clear_height_um']);route_rects.append(rect(key+'_CLEAR_ROUTE_BAND',ox,cy,required_width,rh,0,'M2_M4_50pct_capacity'));cy+=rh
 outline_h=cy-oy;outline_area=required_width*outline_h/1e6
 route_extra=sum(c['gross_mm2'] for c in route_rects)
 total_required=outline_area
 fixed_field_loss=max(0,outline_area-old_att['gross_mm2'])
 shifted_residents=[]
 for r in residents:
  if r['name']=='HUB_ATTENTION':continue
  r=dict(r);r['origin_um']=[r['origin_um'][0]+delta_w,r['origin_um'][1]];shifted_residents.append(r)
 outline={'schema':'opentallas.dsrom.L20-source-counted-hub-outline.v1','origin_um':[ox,oy],'bbox_um':[required_width,outline_h],'gross_mm2':outline_area,'components':components,'clear_route_bands':route_rects,'other_hub_regions_preserved_and_explicitly_shifted':shifted_residents,'collector36_macro_origins':bank['proposed_macro_placements'],'collector_macro_OBS':bank['OBS_excerpt'],'source_timing_claim':False,'allocation_verdict':'PASS_COMPONENT_AREA_AND_CLEAR_CHANNEL_CAPACITY_MODEL_ONLY','physical_route_fit_verdict':'NOT_ROUTED_NOT_CERTIFIED','fixed815_field_debit_mm2':fixed_field_loss,'per_user_parallelism':{'attention_tiles':64,'index_MACs_per_cycle':1024,'HBM_reader_PC_ports':128,'collector_banks_1R1W':4,'peerTXskids':3,'selected_seats':512},'physical_obligations':'Current4096ROMelement mustreplicateinremainingfield; source-matched SSFF andproviderlatency bind endpoints beforeengineRTL. No historicalclockqualification transfer.'}
 grow_width=fp['geometry']['die_w_um']+delta_w
 grow_height=fp['geometry']['die_h_um']+(outline_h-h)
 delta_area=grow_width*grow_height/1e6-fp['geometry']['die_mm2']
 outline['grow_rectangular_die_bbox_um']=[grow_width,grow_height]
 outline['grow_rectangular_die_mm2']=grow_width*grow_height/1e6
 outline['field_preservation_obligation']='Translate right-side field/co-residents by delta_width and bottom-side field/co-residents by delta_height, then enumerate every source instance and channel. This adequate rectangular envelope is a proposal, not a legal placement receipt.'
 emit('reservation_outline.json',outline)
 unified=raw('tools/uarch_model.py',BASE).decode()
 cfg=json.loads(raw('configs/models/candidates/deepseek-v4.1-flash.json',BASE));mm=json.loads(raw('results/floorplan/v41_die_macromap_expanded_woa.json',BASE))
 totals={}
 for die in mm['layer_dies']:
  for group,v in die['macros_by_group'].items():totals[group]=totals.get(group,0)+sum(v.values())
 ns={'_V41_CFG':cfg,'_cons_nonexpert_macros':lambda:totals}
 tree=ast.parse(unified);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cons_stage_plan')
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_cons_stage_plan','exec'),ns)
 plan=ns['cons_stage_plan'];anchor=sum([13296,464,128,82]);anchor_macro=plan(28)['busiest_macros']
 footprint=416.76/7102;macro=.0150025;density_ratio=149.6/142.4
 # Same _cons_need analytical storage + existing element strip equation.
 field_base=9637*footprint;charge=max(0,.125*815-(138.836-65.001));usable=.90*(field_base-charge)
 rows=[]
 for S in range(8,90):
  pp=plan(S);equiv=anchor*pp['busiest_macros']/anchor_macro
  need=pp['payload_per_die_B']*8/75e6*density_ratio+equiv/2*(footprint-2*macro)
  rows.append({'stages':S,'TP4_layer_dies':4*S,'field_need_mm2':need,'baseline_usable_mm2':usable,'new_usable_mm2':usable-.90*fixed_field_loss,'baseline_fit':need<=usable,'new_fit':need<=usable-.90*fixed_field_loss})
 oldS=next(r['stages'] for r in rows if r['baseline_fit']);newS=next((r['stages'] for r in rows if r['new_fit']),None)
 current=json.loads(raw('results/uarch/consolidation.json',BASE))['v41_rom']
 reference=current['product']['reference_for_comparisons']
 qpitch=current['pitches']['w10b_q'];qa=math.prod(qpitch['q_um'])/1e6;ba=math.prod(qpitch['bf16_outline_um'])/1e6
 hub=current['product']['head_fit']['hub_block']
 hub_loss=(hub['block_mm2']-hub['stream_unit_ledger_mm2'])*(1+hub['switch_fraction'])
 product_usable=.9*(9931*footprint-hub_loss-max(0,.125*814.982-(118.426-64.902)))
 assembly=json.loads(raw('results/arch/v41_die_assembly.json',BASE))['ledger']['layer']
 product_rom_mm2_per_B=assembly['rom_mm2']/(cfg['checkpoint_bytes']/188)
 product_rows=[]
 for row in rows:
  pp=plan(row['stages']);pairs=anchor*pp['busiest_macros']/anchor_macro/2
  need=pp['payload_per_die_B']*product_rom_mm2_per_B*density_ratio+pairs*(qa-2*macro)+1024*(ba-qa)
  product_rows.append(dict(stages=row['stages'],need_mm2=need,baseline_usable_mm2=product_usable,new_usable_mm2=product_usable-.9*fixed_field_loss,baseline_fit=need<=product_usable,new_fit=need<=product_usable-.9*fixed_field_loss))
 product_old=next(r['stages'] for r in product_rows if r['baseline_fit'])
 product_new=next((r['stages'] for r in product_rows if r['new_fit']),None)
 assert product_old==reference['stages'], 'Product equation does not reproduce pinned reference'
 product_capacity={'pinned_reference':reference,'same_source_geometry':'W10 refit C_rotate, W10b q and 1024 BF16 columns, 4096m8; sensitivity applies same area debit, not a W18 legal-slot certificate','exact_pinned_density_mm2_per_B':product_rom_mm2_per_B,'baseline_min_stages':product_old,'new_min_stages':product_new,'added_layer_dies':4*(product_new-product_old),'new_layer_dies':4*product_new,'unchanged_head_dies':reference['head_dies'],'unchanged_table_dies':reference['table_dies'],'new_total_dies':4*product_new+reference['head_dies']+reference['table_dies'],'rows':product_rows}
 # Source-model stage/substage hop price from an identical product comparison
 # row. Expose communication sensitivity, never a new whole-token headline.
 comparable=[r for r in current['points'] if r.get('stages')==reference['stages'] and r.get('hub_block') and r.get('bf16')=='columns' and r.get('ss_wire')]
 product_capacity['retained_comparison_rows']=[{k:r.get(k) for k in ['label','stages','stage_hops','pipeline_hops_us','ar_tokens_s_b1','clock_hz']} for r in comparable]
 product_capacity['additional_stage_boundary_events']=product_new-product_old
 cp=raw('tools/decode_critical_path.py',BASE).decode();raw('tools/arch_budget_v41.py',BASE)
 tech=json.loads(raw('configs/hardware/technology.json',BASE))['links']
 cable=tech['rom_rack_cable_serdes']['hop_latency_s']['value'];ucie=tech['rom_package_ucie']['hop_latency_s']['value']
 # arch_budget_v41 binds ArrayFabric(links,2,mesh,4): TP4 spans2
 # packages; the stage traversal is2 cable hops + one UCIe fan-out.
 depth=2*cable+ucie;pkg_bw=tech['rom_board_serdes']['bytes_s']['value']*90/128;direction_bw=pkg_bw/4
 residual=4*cfg['hidden_size']*2+4*4
 bytecap=residual+1280+2048+512*2
 serialize=bytecap/direction_bw+bytecap/tech['rom_package_ucie']['bytes_s']['value']
 product_capacity['source_hop_only_price']={'fabric':'ArrayFabric(dp2,boardmesh,TP4), pinned arch_budget_v41 source','depth_s_per_stage_or_substage':depth,'payload_B_source_max':bytecap,'per_neighbour_Bps':direction_bw,'serialize_s_source_max':serialize,'extra_dependency_hops':product_new-product_old,'extra_unretimed_dependency_depth_us':(product_new-product_old)*depth*1e6,'extra_serial_issue_us_upper_for_payload_cap':(product_new-product_old)*serialize*1e6,'scope':'Conditional source-fabric service price, not sustained availability, placed endpoint, complete token repricing or historical closure. Context re-timing and overlap remain separately charged.'}

 product_capacity['latency_price']='Additional boundary events use actual fabric.hop(stage,payload,stage_index), including bytes_s and package placement; extra substage events must be regenerated from cons_stage_plan partitions. No constant serial-load multiplication or retained headline adoption.'

 # No whole-token performance fabricated. Delta stage-hop must be added to
 # current retained graph; service and physical local path receipts absent.
 latency={'source_schedule':{'QK_post_ready_cycles':2894,'PV_post_ready_cycles':3374,'banked_cold_start_per_job_cycles':4,'common_cut_per_job_cycles':2},
 'index_work_per_full64key_batch_MACs':64*32*128,'index_peak_MACs_per_cycle':1024,'index_min_issue_cycles':256,'batch_pipeline_empty_slot_conditional_cycles':392,'batch_schedule_scope':'64META+1DESC+256issue+70tail+1idle model; requires faultfree ready query,64 metadata seats and admitted complete inputbeat. Not executed or an unconditional HBM bound.','batch_META_accepted_events':64,'descriptor_events':1,'finish_hsum_fixed_depth_cycles':32,'key_completion_events_per_key':4,
 'service_guarantee':'Inputs maystall; busy admits next64keybeat onlywhenlastactualscore retires. No perfectHBM orpeer service assumption;4readerfiniteWB32 GA24 mayfillandbackpressure.',
 'growth_route_formula':'Every extra endpointdistance must use a same-load/source-layer route calibration at SS and add pipeline+CDC cycles to actual dependency events. Historical64bitwirefit not a203/34816/16966bit timing certificate.',
 'fixed_die_added_TP4_stages':product_new-product_old,'fixed_die_added_layer_dies':4*(product_new-product_old),
 'single_user_rate':'NOT_CERTIFIED: source-provider service bound + context wire/CDC delay absent. Added graph hop latency = (newS-oldS)*actualstagehop_s; no freeclock or headline performance.',
 'grow_die_count_delta_for_unchanged_field_capacity':0,'grow_die_area_delta_mm2_with_extra_route_corridors':delta_area,'grow_die_area_mm2_with_extra_route_corridors':fp['geometry']['die_mm2']+delta_area,
 'original_9537_loads_serial_multiplier':False}
 model={'schema':'opentallas.dsrom.L20-hierarchical-source-reservation.v1','source':REAL,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'status':'SOURCE_QUANTIFIED_RESERVATION_CANDIDATES_NOT_PHYSICAL_CLOSURE',
 'indexer':{'actual_parameters':p,'products_percycle':1024,'HBM_ports':128,'response_payload_Bpc_peak':4096,'join_peak_payload_Bpc':4352,'replicas':{'readers':4,'quarterjoin':1,'batch':1,'finish_inside_batch':1,'keywriterSUN256':1,'blockdots':32},'state_inventory':inventories,'explicit_delay_and_temporal_state_bits':explicit_delays,'state_bits_subtotal':sequential,'mux_bit_equivalents':muxes,'arithmetic_cell_um2':arith,'structural_adder_counts':{'chunk_chains':28,'wgt_spatial_tree':3,'wgt_temporal_combiners':20,'hsum':31},'controller_gate_proxy_cell_um2':control,'primitive_sources':'results/arch/arch_budget_v41.json; source class area proxies, not exact hierarchical timing','cell_proxy_um2':cell,'placed_proxy_mm2':idx_placed,'historical21p677_charge_replaced_by_source_ledger':True,'qualification_transfer':False,'ROB_macro_inferred':False,'OBS_index_ROB':'FF realization; no unstated memory abstract. FutureSRAMimplementation must model synchronousread andwrite strobes before replacement.'},
 'attention_audit':audit,'actual_QE_state_inventory':qe,'actual_quantizer_children_inventory':quantizers,'service_wrapper_inventory':service_inventory,'co_resident_reservations_mm2':source_reservations,'SU_N256_M64_lane_proxy_placed_mm2':su_cell/UTIL/1e6,'all_retained_hub_regions':residents,
 'refit':{'actual_retained_die_bbox_um':[fp['geometry']['die_w_um'],fp['geometry']['die_h_um']],'retained_attention_bbox':old_att,'required_attention_index_select_common_cut_mm2':required,'required_width_um_before_extra_corridors':required_width,'grow_fresh_column_width_um':delta_w,'fixed_die_field_loss_mm2_including_declared_extra_corridors':fixed_field_loss,'extra_route_corridors_mm2':route_extra,'outline_json':'reservation_outline.json','new_attention_service_index_bbox_um':[required_width,outline_h],'analytical_allocation_verdict':outline['allocation_verdict'],'capacity_equation':'distinct actual M2Y phases per270DBU plus M4Y48DBU, conservative phase loss; subtract translatedOBS+halos, reserve50pct nonsignal. Existing HBM cut capacities separately bound in actual_grid_usable_capacity.json','route_bands':route_bands,'collector_macro_OBS':bank['OBS_excerpt'],'collector_macro_placements':bank['proposed_macro_placements'],'collector_SS_remaining_route_plus_setup_ps':bank['SS_remaining_route_and_receiver_setup_ps_at1p2'],'all_co_residents_preserved':True,'new_geometry_is_analytical_proposal_not_measured':True,'slot_reservation_receipt':'reservation_outline.json is explicit analyticalallocation; no sourcehardening or physicalclosure receipt'},
 'current_product_capacity_sensitivity':product_capacity,'historical_standard_pair_field_capacity_sensitivity':{'basis':'AST of pinnedcons_stage_plan; sameanalytical75Mbit/mm2 +4096depth densityratio,50pctlogic,90pctfill,12.5pctoverhead,ringcredit; no predictiveROMdensity substitution','baseline_min_stages':oldS,'new_min_stages':newS,'rows':rows,'head_table_dies':'Unaffected by layerhub field debit; retained owners unchanged; totaldie delta shown as4*layerstage delta'},'latency':latency,
 'retained_FAILUREs':[old['original_failed_screens_preserved'],'9f9b reservation deficit retained unchanged'],
 'gate_before_collector_RTL':['Model owner reviews hierarchy/gate proxies and source exactness; no inferredSRAM/freeports','Legal freshregion allocation with existing4096row ROMelement placement andallco-residents; fixed815 alternative actual displacedfieldslots must be enumerated','Source-layer endpoint-route SSFF/OBS andfixedprovidercontract binds composed token events; noclock relaxation','Joint ownvisible/WINDOW128/selected512 andfiniteepoch/physicaldrain mandatory'],
 'four_targets':old['four_targets'],'pins':PINS,'preserved_inputs':old['preserved_inputs'],'launch_allowed':False,'engine_RTL_build_ready':False}
 emit('model.json',model)
 emit('attention_subtotal_audit.json',audit)
 print(json.dumps({'indexer_current_source_placed_proxy_mm2':idx_placed,'attention_corrected_placed_proxy_mm2':attention,'required_with_routes_mm2':total_required,'fixed_field_debit_mm2':fixed_field_loss,'baseline_stages':oldS,'new_stages':newS,'collector_GO':False}))
if __name__=='__main__':main()
