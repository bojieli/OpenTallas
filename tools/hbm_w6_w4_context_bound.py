#!/usr/bin/env python3
"""Constructor-free complete RF/W4/matcher/W6 home and cut planning screen.

No RTL synthesis, simulation or physical invocation. Geometric capacity is not
an installed slot/PG/route or loaded timing proof. Original-v1 only.
"""
import hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/hbm_W6_W4_loaded_context_20261003/r2'
R1=ROOT/'results/uarch/hbm_W6_W4_loaded_SSFF_plan_20261003/r1'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def inputs():
 out={}
 for r in json.loads((BASE/'source_pins.json').read_text()):
  raw=(BASE/r['archive']).read_bytes();need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'context source pin '+r['path']);out[r['path']]=raw
 return out

def provider_ports(text):
 header=text.split('module ot_gpu_rf_service #',1)[1].split(');',1)[0].split('(\n',1)[1];out={};d=None;t=None;w=None
 for tok in header.split(','):
  tok=tok.strip();m=re.fullmatch(r'(input|output)\s+(wire|reg)\s*(?:\[(\d+):(\d+)\]\s*)?(\w+)',tok)
  if m:d,t=m[1],m[2];w=1 if m[3] is None else abs(int(m[3])-int(m[4]))+1;n=m[5]
  else:need(d is not None and re.fullmatch(r'\w+',tok),'port declaration');n=tok
  need(n not in out,'duplicate port');out[n]=dict(direction=d,kind=t,bits=w)
 return out

def census(text):
 p=provider_ports(text);need(p['rsp_a']['bits']==4096 and p['rsp_b']['bits']==4096,'full128lane response capture')
 body=text.split('end else begin:g_identity',1)[1].split('end endgenerate',1)[0]
 expected={'read_pending':1,'prefer_write':1,'write_pending':1,'accepted_identity':55,'protected_ACK':72,'page_a':2,'page_b':2};fields={}
 for width,decl in re.findall(r'\breg\s*(\[[^]]+\])?\s*([^;]+);',body):
  bits=1
  if width:
   m=re.fullmatch(r'\[(\d+):(\d+)\]',width);need(m is not None,'bounded source width');bits=abs(int(m[1])-int(m[2]))+1
  for name in decl.split(','):
   name=name.strip();need(re.fullmatch(r'\w+',name),'bounded provider state');fields[name]=bits
 need(fields==expected,'complete RF selected state census changed')
 fields.update({k:v['bits'] for k,v in p.items() if v['kind']=='reg'})
 need(sum(fields.values())==8328,'complete128 provider FFs')
 return fields,p

def bound():
 raw=inputs();key='results/uarch/h4_hbm_pc40_physical_ack_r3_20261003/inputs/ot_gpu_rf_service.sv';fields,ports=census(raw[key].decode());m=json.loads(raw['results/uarch/h4_hbm_pc40_physical_ack_r3_20261003/model.json'])['model']
 need(m['costs']['provider_total_new_FFs']==128 and m['retained_control']['new_physical_FFs']==0 and m['W6_receiver_join']['new_coded_words']==0,'onceonly provider/padding ledger')
 macro='ot_sram_1r1w_128x256_m1_r2c2';rfdir=R1/'inputs/physical/asap7_memory_macros'/macro;lef=(rfdir/(macro+'.lef')).read_text();dim=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',lef);w,h=map(float,dim.groups());need((w,h)==(94.824,41.04),'frozen originalv1')
 # Concrete R0 planning grid with4um halo. Source site's x54nm,y270nm;
 # original RF M4 pin-centre condition intersects row grid at2160nm.
 sx=math.ceil((w+8)/.054)*.054;sy=math.ceil((h+8)/2.16)*2.16;positions=[]
 for bank in range(16):
  for copy in range(2):
   for page in range(4):
    col=bank//2;row=(bank%2)*8+copy*4+page;x=4.05+col*sx;y=4.32+row*sy
    positions.append(dict(bank=bank,copy=copy,page=page,relative_source=f'g_identity.g_page[{page}].g_bank[{bank}].u_operand_'+('a' if copy==0 else 'b'),origin_um=[x,y],orientation='R0',bbox_um=[x,y,x+w,y+h],halo_bbox_um=[x-4,y-4,x+w+4,y+h+4]))
 # Price baseline RF state/mux once in this local complete-provider context.
 # This baseline is already contained in global service envelope; do not add
 # it again to the current whole-die reservation. Cell values remain proxies.
 base_ff=8328-128;ffcell=base_ff*.2916;mux_cells=8192*3;muxcell=mux_cells*3*.3;base_footprint=(ffcell+muxcell)/.5/1e6
 controller=m['physical']['provisional_service_enclosure_mm2_per_SM'];logic_needed=controller+base_footprint
 width=825.12;logic_width=816.48;logic_y=829.44;logic_h=math.ceil(logic_needed*1e6/logic_width/2.16)*2.16;height=math.ceil((logic_y+logic_h+4)/2.16)*2.16
 need(all(r['halo_bbox_um'][0]>=0 and r['halo_bbox_um'][2]<=width and r['halo_bbox_um'][3]<logic_y-16 for r in positions),'constructive macro/logic homes')
 tracks={}
 for line in raw['/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/openRoad/make_tracks.tcl'].decode().splitlines():
  t=re.fullmatch(r'make_tracks (M[35]) -x_offset ([\d.]+) -x_pitch ([\d.]+) -y_offset ([\d.]+) -y_pitch ([\d.]+)',line)
  if t:tracks[t[1]]=(round(float(t[2])*1000),round(float(t[3])*1000))
 need(set(tracks)=={'M3','M5'},'actual preferred vertical track grids')
 counts={k:len(range(off,round(width*1000)+1,pitch)) for k,(off,pitch) in tracks.items()};capacity=sum(counts.values())//2;demand=sum(v['bits'] for v in ports.values());need(capacity>demand,'complete provider port cut must fit')
 inv=json.loads(raw['results/uarch/hbm_fullsize_inventory_20261003/model-r1.json']);old=inv['models']['Qwen']['area'];need(old['RF_already_contained_in_service_envelope'],'RF inherited envelope');perSM=old['service_envelope_mm2']/32;need(width*height/1e6<perSM,'prospective local home fits scalar envelope')
 return dict(schema='W4_W6_COMPLETE_RF_CONTEXT_BOUND_R2',source='b6d1d19f77c89e4131cbb0aca29d88fae5772b1a',SMs=32,RF_macros_per_SM=128,RF_macros_full32=4096,source_state_fields=fields,provider_ports=ports,
  FF_ledger=dict(existing_provider_FFs=base_ff,new_W4_provider_FFs=128,complete_provider_FFs=8328,full32_provider_FFs=32*8328,provider_data_capture_FFs=8192,provider_reset_FFs=136,fullSM_SIMD_shadow_FFs=0,controller_padding_newFF=0,W6_existing_FFs=144,provider_baseline_paid_once=True,actual_mapped_FFs=None),
  area=dict(baseline_provider_FF_cells_mm2_ASSUMED=ffcell/1e6,baseline_RF_fourpage_mux2_cells=mux_cells,baseline_RF_mux_cells_mm2_ASSUMED=muxcell/1e6,baseline_provider_50pct_footprint_mm2_ASSUMED=base_footprint,controller_consumer_W6_R3_enclosure_mm2_ASSUMED=controller,complete_logic_50pct_footprint_mm2_ASSUMED=logic_needed,new_W4_matcher_delta_mm2_ASSUMED=m['costs']['footprint_mm2_50pct_ASSUMED'],global_RF_macro_debit_added_again=0,global_provider_baseline_debit_added_again=0,matched_global_logic_replacement_net_mm2=None,actual_cell_net_unknown=True),
  candidate_home=dict(width_um=width,height_um=height,area_mm2=width*height/1e6,RF128_positions=positions,logic_bbox_um=[4.32,logic_y,4.32+logic_width,logic_y+logic_h],halo_um=4,macro_orientation='R0',site_x_nm=54,row_y_nm=270,legal_RF_row_step_nm=2160,source_envelope_mm2_per_SM=perSM,scalar_area_fit=True,installed_home_fit=False,full32_macros_and_logic_replicated=True,global_home_coordinates=None,protected_neighbor_scratch_L2_matrix_PG_required=True),
  channel=dict(kind='planned macro-to-controller horizontal cut using preferred verticalM3/M5 lines',width_um=width,source_track_counts=counts,policy_half_signal_tracks=capacity,other_half_PG_via_clock_and_routing_allowance=True,complete_RF_provider_port_tracks_upper=demand,extra102_identity_already_in_complete_ports=True,planning_margin_tracks=capacity-demand,cut_clear_of_planned_RF_halos=True,actual_OBS_PG_neighbor_cut_capacity=None,macro_pin_escape_qualified=False,tracks_not_throughput_measurement=True),
  clock_reset=dict(period_ns=1/1.2,SSsetup_ps=60,FFhold_ps=25,one_literal_clock_on_R3_provider_matcher_W6=True,internal_CDC_seats=0,external_CDC_drain_owner='Claude',loaded_slew_cap_skew_and_reset_tree_bound=None,source_reset_data_FFs_not_assumed=True,need_aligned_place_assert=True),
  physical_admitted=False,new_PNR=0,new_simulations=0,missing_positive_home=['Popper signed once-only complete provider/mux/FF cost and concrete home acceptance','Actual32 home coordinates/neighborhalo/siteROWS and global envelope placement census','M3/M5 planned cut actual OBS/PDN/via/clock exclusions and pin escape','Actual provider8328 FF mapped inventory and distributed bank/page mux capture endpoints','Loaded SS/FF cells, RC/pin caps/clock/reset/faultfanout timing bound'])
if __name__=='__main__':print(json.dumps(bound(),indent=2,sort_keys=True))
