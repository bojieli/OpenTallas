"""Finite source-equivalent endpoint construction only; no RTL execution or native claims."""
from pathlib import Path
import json, hashlib, gzip, re
P=Path(__file__).resolve().parent
prior=json.loads((P/'prior_model.json').read_text())
L=Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM')
sha=lambda b:hashlib.sha256(b).hexdigest()
source={x.name:sha(x.read_bytes()) for x in (P/'source').iterdir()}
assert all(source[n]==h for n,h in prior['source_sha256'].items())
vp=(P/'source/ot_s81sl_vp.sv').read_text()
block=vp[vp.index('always @(posedge clk or negedge rs_c)'):vp.index('always @(posedge clk) begin')]
assert block.count('<=')==12 # six assignments each branch; cwv_c is width2
assert len(re.findall(r'negedge rs_c',vp))==1
names=['cv_c','swv_c','cwv_c[0]','cwv_c[1]','hqv_c','xrv_c','xwv_c']
bits=prior['downlink']['valid_bit_offsets_lsb']
endpoints=[]; owners=[]; ties=[]; local=[]
for k in range(5):
 root=f'lf[{k}]';vpname=root+'.u_lf.u_vp';rr=vpname+'.u_rr'
 owner=rr+'.relay_q[0][0]'
 old=[{'endpoint':vpname+'.'+n+'.RESETN','role':'existing_consumer_authority'} for n in names]
 new=[]
 for j in range(4):
  for role,bit in bits.items():
   q=f'{root}.u_dn.gd.r[{j}][{bit}]'
   d={'c_v':f'c_v_x[{k}]','sw_v':f'sw_v_x[{k}]','cw_v[0]':f'cw_v_x[{2*k}]','cw_v[1]':f'cw_v_x[{2*k+1}]','rb_v':'rb_v_x','g_v':'gv_x'}[role] if j==0 else f'{root}.u_dn.gd.r[{j-1}][{bit}]'
   consumer={'c_v':'u_vp.cv_c','sw_v':'u_vp.swv_c','cw_v[0]':'u_vp.cwv_c[0]','cw_v[1]':'u_vp.cwv_c[1]','rb_v':'u_vn.rb_v_c','g_v':'u_vs.gv_c'}[role]
   e={'source_state':q,'native_instance':None,'role':role,'leaf':k,'stage':j,'packed_bit':bit,'D_source_equation':d,'RESETN_owner':owner,'SETN_owner':f'tie_leaf{k}_new.H','CLK_source':'ot_s81sl_slice.clk','first_consumer':f'{root}.u_lf.{consumer}','native_clock_binding':None,'mapped_master':None,'proposed_equivalent_master':'DFFASRHQNx1_ASAP7_75t_R'}
   endpoints.append(e);new.append({'endpoint':q+'.RESETN','role':role})
 owners.append({'owner':owner,'native_instance':None,'D_owner':rr+'.sync_q[1]','RESETN_owner':'ot_s81sl_slice.rst_n','SETN_owner':f'tie_leaf{k}_old.H','CLK':'ot_s81sl_slice.clk','inherited_age_edges':3,'existing_D_loads':[],'existing_RESETN_loads':old,'existing_SETN_loads':[],'new_RESETN_loads':new,'total_nonclock_logical_loads':31,'physical_phase':None,'clock_reach_removal_slew':None})
 # FULL local relay D/RESETN/SETN expansion, not only proposed120.
 rststates=[rr+'.sync_q[0]',rr+'.sync_q[1]']+[rr+f'.relay_q[0][{r}]' for r in range(4)]
 for n in rststates:
  d=f'tie_leaf{k}_old.H' if n.endswith('sync_q[0]') else rr+'.sync_q[0]' if n.endswith('sync_q[1]') else rr+'.sync_q[1]'
  local.append({'state':n,'D':d,'RESETN':'ot_s81sl_slice.rst_n','SETN':f'tie_leaf{k}_old.H','CLK':'ot_s81sl_slice.clk','native_instance':None})
 for n in names:local.append({'state':vpname+'.'+n,'D':{'cv_c':'c_v','swv_c':'sw_v','cwv_c[0]':'cw_v[0]','cwv_c[1]':'cw_v[1]','hqv_c':'hq_v','xrv_c':'x_rv','xwv_c':'x_wv'}[n],'RESETN':owner,'SETN':f'tie_leaf{k}_old.H','CLK':'ot_s81sl_slice.clk','native_instance':None})
 ties += [{'owner':f'tie_leaf{k}_new.H','master':'TIEHIx1_ASAP7_75t_R','loads':[e['source_state']+'.SETN' for e in endpoints if e['leaf']==k],'total':24}, {'owner':f'tie_leaf{k}_old.H','master':'TIEHIx1_ASAP7_75t_R','loads':[n+'.SETN' for n in rststates]+[vpname+'.'+n+'.SETN' for n in names]+[rr+'.sync_q[0].D'],'total':14}]
assert len(endpoints)==len({e['source_state'] for e in endpoints})==120
assert len(local)==65 and sum(t['total'] for t in ties)==190
assert max(t['total'] for t in ties)==24
assert all(o['total_nonclock_logical_loads']==31 for o in owners)
libs={};price={}
for corner in ['TT','FF']:
 p=L/f'asap7sc7p5t_SIMPLE_RVT_{corner}_nldm_211120.lib.gz';raw=p.read_bytes();s=gzip.decompress(raw).decode();libs[corner]={'compressed_sha256':sha(raw),'decoded_sha256':sha(s.encode())}
 c=s[s.index('cell (TIEHIx1_ASAP7_75t_R)'):];c=c[:c.find('\n  cell (',1)];a=float(re.search(r'area\s*:\s*([\d.]+)',c)[1]);assert a==0.04374
 seq=prior['actual_library_masters'][corner]['DFFASRHQNx1_ASAP7_75t_R']
 q=(L/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib').read_text();q=q[q.index('cell (DFFASRHQNx1_ASAP7_75t_R)'):];q=q[:q.find('\n  cell (',1)];q=q[q.index('pin (D)'):];q=q[:q.index('}')];dcap=float(re.search(r'capacitance\s*:\s*([0-9.]+)',q)[1])
 price[corner]={'conversion_area_delta_um2':10.4976,'dedicated_ties':10,'tie_area_added_conservative_um2':10*a,'primitive_plus_dedicated_ties_added_um2':10.4976+10*a,'CLK_delta_fF':prior['variants'][-1]['liberty_arithmetic'][corner]['clock_cap_delta_fF'],'new_reset_cap_per_VP_rs_c_fF':24*seq['RESETN_fF'],'all31_reset_cap_per_VP_rs_c_fF_if_ASR_mapping':31*seq['RESETN_fF'],'new120_SETN_cap_fF':120*seq['SETN_fF'],'retied_existing65_SETN_cap_fF_if_ASR_mapping':65*seq['SETN_fF'],'sync0_D_constant_cap_per_leaf_fF_if_ASR_mapping':dcap,'old_tie_14_load_cap_per_leaf_fF_if_ASR_mapping':13*seq['SETN_fF']+dcap,'new_tie_24_load_cap_per_leaf_fF_if_ASR_mapping':24*seq['SETN_fF'],'tie_output_electrical_closure':None,'new_pg_terminals':20,'converted_ff_pg_terminals':240,'pg_count_delta_from_master_conversion':0,'post_ECO_total_parent_pg_terminals':None,'physical_wiring_CTS_PG_area':None,'whole_structural_cost':None}
# Explicitly conditional calendars; only unwrapped common source clock has dates.
calendar=[]
for k in range(5):
 for role in bits:
  if role=='c_v':publication='E5 earliest genuine CTL: input E3, classifier E4, c_v E5';p=5
  elif role=='sw_v':publication='E5 earliest CTL row write; rwr at E4; RD unpacker can publish later';p=5
  elif role=='rb_v':publication='E4 earliest local rb_v: rbv captures real x_rbv at E3';p=4
  elif role=='g_v':publication='E4 earliest local g_v: egv_c captures real eg_v at E3';p=4
  else:publication='CAP root cw_v clears from its own rs_o; earliest source output lower bound E3, exact genuine complete-row publication NULL';p=3
  calendar.append({'leaf':k,'role':role,'source_publication':publication,'common_clock_lower_bound_publication':p,'DL_stage0_capture_lower_bound':p+1,'DL_stage3_publish_lower_bound':p+4,'consumer_pin_capture_lower_bound':p+5,'native_source_publication':None,'native_consumer_clock':None,'source_clock_at_parent':'clk','relay_clock_at_parent':'clk','VP_VN_VS_clocks_at_parent':'clk','actual_hardened_phase':None})
witness=[]
old=[0]*4;candidate=[0]*4
for edge in range(5):
 witness.append({'abstract_edge':edge,'source_valid':int(edge==0),'VP_owner_high':edge>=4,'consumer_eligible':edge>=4,'original_pre_q':old[:],'candidate_pre_q':candidate[:],'original_consumer_word':bool(edge>=4 and old[3]),'candidate_consumer_word':bool(edge>=4 and candidate[3])})
 old=[int(edge==0)]+old[:-1]
 candidate=([int(edge==0)]+candidate[:-1]) if edge>=4 else [0]*4
assert witness[-1]['original_consumer_word'] and not witness[-1]['candidate_consumer_word']
out={'scope':'SOURCE PROPOSAL ONLY, no RTL implementation/execution/EDA','source_commit':'ceaed19c4','parent_sha256':source['ot_s81sl_slice.sv'],'XR_sha256':source['ot_s81sl_xr.sv'],'source_sha256':source,'prior_model_commit':'e99b83c04','parent_firstuse_commit':'edd84d4c3','capacity_provenance_only':'5975a35d7','source_driver_choice':'reuse five existing VP u_rr regional0 outputs, no new FF','authority_endpoints':endpoints,'reset_owners':owners,'complete_unchanged_local_relay_and_consumer_input_terminals':local,'ties':ties,'tie_library_sha256':libs,'cost':price,'calendar':calendar,'local_source_counts':{'authority_conversions':120,'payload_other_unreset':11760,'preexisting_consumer_ASR_equivalent':35,'preexisting_VP_relay_ASR_equivalent':30,'existing_relay_D_loads_sync0_per_leaf':1,'existing_relay_D_loads_sync1_per_leaf':4,'existing_raw_reset_RESETS_per_VP_relay':6,'new_raw_reset_loads':0,'new_release_state':0,'new_data_edges':0,'raw_parent_known_direct_reset_load_lower_bound_XR_plus_five_VP_VN_VS':96},'conditional_first_word_loss_witness_nonexecuted_not_production':witness,'upstream_root_terminal_expansion':None,'native_polarity_and_instance_join':None,'cold_fourstate_firstuse':None,'actual_parent_reset_pulse_authority':None,'structurally_complete_parent':False,'implementation_admissible':False,'verdict':'LOCAL31_LOAD_ASSIGNMENT_MODEL; FULL_PARENT_FIRST_AUTHORITY_HOLD','uplink_authority_80':'separate HOLD'}
(P/'proposal.json').write_text(json.dumps(out,indent=2)+'\n')
print('SOURCE MODEL: 120 unique endpoints, five31-load reset owners, ten ties24/14 loads, 65 preexisting local reset-state/consumer input ledgers. PASS scoped enumeration; parent HOLD.')
