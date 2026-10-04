"""Bind functional RTL to fullwidth/source model and corrected reset-pin screen."""
import argparse,json,math,hashlib
from pathlib import Path
import ds_mtp_tokx_enrollment_model as T
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/rtl/ds_mtp_accept_20261003'
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hdc/ot_hdc_accept.sv',
'rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv',
'rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_source_holders.sv',
'rtl/test/ds_mtp_accept_20261003/tb.sv']
def tree(sinks,leaf_fanout):
 n=math.ceil(sinks/leaf_fanout);levels=[n]
 while n>1:n=math.ceil(n/8);levels.append(n)
 return levels

def model():
 m=T.model();facts=json.loads((T.L.OUT/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json').read_text())['facts']
 context=json.loads((OUT/'inputs/Maxwell94ac_containment.json').read_text())
 assert context['clock_reset_load_union']['leaf_protected_FF']==2016
 ff=facts['DFFASRHQNx1_ASAP7_75t_R'];buf=facts['BUFx4_ASAP7_75t_R']
 cap=ff['FF']['pins']['RESETN']['cap_fF'];limit=5.76
 old=tree(2016,8);new=tree(2016,7);extra=sum(new)-sum(old);assert extra==41 and cap*8>limit and cap*7<=limit
 body=m['kernel_composition']['gross_cell_body_um2']+extra*buf['SS']['area_um2']
 return dict(schema='DS_MTP_PROTECTED_ACCEPT_RTL_PREPARATION_R1',base='7b4509c23a8a67891f250bef78d7459e6050883c',
 default_enable=False,NSLOT=8,NW=21,scalar_K512_changed=False,source_assignments={'leaf_codewords':24,'caller_codewords':4,'bits_per_word':72,'physical_state_budget_bits':2016,'raw_leaf_and_caller_bits':716},
 source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
 reset_reconciliation={'Maxwell_source':'94ac6b0ef7d306860e060effa8080b70a3daf7c3','FF_RESETN_fF':cap,'selected_limit_fF':limit,'old8pin_fF':cap*8,'new7pin_fF':cap*7,'clock_levels':old,'reset_levels':new,'old_clock_reset_buffers':578,'new_clock_reset_buffers':sum(old)+sum(new),'added_BUFF4_minimum':extra,'additional_body_um2':extra*buf['SS']['area_um2'],'old578_charged_once':True,'wire_sites_and_actual_clock_tree':None,'pin_only_minimum_not_physical_closure':True},
 costs={'gross_body_um2':body,'gross50pct_mm2':body/.5/1e6,'matched_old_debit_or_net':None,'leaf_rectangle_request_um':[128,191.7],'spare_geometric_um2':128*191.7-body/.5,'slot_assigned':False},
 ports={'prior_leaf_union':636,'actual_leaf_caller_bad_internal_wire':1,'leaf_with_caller_fault_cut':637,'producer_named_cuts':[52,52],'internal_fault_wire_adds_no_state':'jointguard gate already priced; addone track ifsourceholderfault crosses physical leaf boundary','actual_legal_channel_capacity':None},
 timing={'accept_to_guarded_done_edges':3,'extra_codec_stages':0,'nominal_model_clock_GHz':.9,'functional_fixture_period_ns':10,'fixture_clock_not_SS_FF_qualification':True,'SS_setup_ps':60,'FF_hold_ps':25,'loaded_codec_cones_proven':False,'stage_extension':'price additional codedword/cell/cut/clock edges before RTL change'},
 reset_contract={'cold_rst_n':'external allcopies-fenced power-on only; not a runtime erase interface','runtime_rearm':'fence_rearm only idle+admission stopped+matchinglease+63receipts; owned debt refused preserving encodedrecords','externally_false_cold_fence_detected_by_kernel':False,'sourceprovider_reset_drain_qualification':False},
 component_gate={'source_greedy_oracle':'unchanged ot_hdc_accept NSLOT8/NW21; active slots plus prefix/n/bonus, unused source stale slots excluded','source_origin_inputs':'acceptedproducer command and echoed terminal supplied by fixture; actual native origin echo adapter uninstalled','full_drafter_or_acceptance':False,'AR_MTP_or_HBM_rate':None,'conditional_tau_adopted':False,'HBM_service_ACK_terms_unchanged':True},
 admission={'functional_component_assignment':'parentexplicit, after corrected minimum reset ledger bound','physical_or_P_and_R':False,'Arch_full_reset_reprice_and_wire_sites_pending':True,'Maxwell_selected_S58_PAR2_stage_rank_shard_map':None,'scalar_protected_RTL':False})
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();data=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();dest=a.out or OUT/'preparation.json'
 if a.verify:assert dest.read_bytes()==data;print('PASS corrected minimum reset ledger and exact source preparation')
 else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);print(dest)
if __name__=='__main__':main()
