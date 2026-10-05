"""Before-RTL sizing of source-connected W4/W6 RF/commonACK drain leaves."""
import ast
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PINS=(
 'tools/uarch_model.py',
 'results/uarch/h4_hbm_pc40_physical_ack_r3_20261003/inputs/ot_gpu_rf_service.sv',
 'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_gpu_rf_visibility_fence_w6.sv',
 'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_gpu_w6_secded_pkg.sv')

def constant(name):
 for n in ast.parse((ROOT/'tools/uarch_model.py').read_text()).body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):return ast.literal_eval(n.value)
 raise ValueError('unified constant missing')

def model():
 leaf_bits=141+104+147+86+1
 root_bits=84+32+32+1+1+1
 leaf_words=(leaf_bits+63)//64;root_words=(root_bits+63)//64
 # Reuse actual RF SRAM, W4 accepted55/protected72, W6 retained144. New
 # protection stores KV association only; original source states NOT added again.
 cmp_leaf=55+5*55+3*20+84+55
 leaf_gates=leaf_words*1536+cmp_leaf*5+leaf_bits*8+2048
 root_gates=root_words*1536+32*84*5+root_bits*8+2048
 leaf_cell=leaf_words*72*constant('DFF_UM2')+leaf_gates*.0648
 root_cell=root_words*72*constant('DFF_UM2')+root_gates*.0648
 return dict(schema='RF-commonACK-source-drain-r1',
  source=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in PINS],
  organization=dict(ranks=2,SMs_per_rank=32,leaves=64,roots=2,
   per_source_port='one serialized W4 paired-read/write receipt and one W6 owner, exactly actual source capacity'),
  storage=dict(leaf_raw_bits=leaf_bits,leaf_words=leaf_words,leaf_protected_FF=leaf_words*72,
   root_raw_bits=root_bits,root_words=root_words,root_protected_FF=root_words*72,
   all_new_protected_FF=64*leaf_words*72+2*root_words*72,
   existing_W4_W6_RF_storage_reused=True,new_SRAM_macros=0,new_payload_bytes=0),
  ports=dict(leaf_observation=['W4 read accepted/paired-response taken','W4 write accepted/owner55ACK taken',
     'W6 req accepted','W6 host/SIMD ACK accepted','W6 consumer/child/parent/reverseCDC accepted','W6 retire accepted'],
   leaf_register_write_ports='one composed8codedword next-state update; concurrent read/W6 observations retained',
   root_register_write_ports='one composed3codedword update with32parallel child reply matches'),
  boundaries_bits=dict(source_KV_binding_each=86,W4_write_identity=55,W4_paired_read_address=18,
   W4_ACK_identity=55,W6_identity=55,W6_local_drain_source=55+2,cohort_request=84+1,cohort_response=84+2,
   rank_leaf_multicast=32*(84+1),rank_leaf_return=32*(84+2)),
  compute=dict(MACs_per_cycle=0,new_memory_bytes_per_cycle=0,arithmetic='none'),
  mux_demux=dict(leaf_compare_bits=cmp_leaf,root_compare_bits=32*84,
   leaf_state_mux_bits=leaf_bits*2,root_state_mux_bits=root_bits*2,
   root_identity_fanout=32,source_admission_permits=['matching-key RF read','matching-key RF write','matching-key W6 request']),
  area=dict(leaf_NAND_equivalent_ASSUMED=leaf_gates,root_NAND_equivalent_ASSUMED=root_gates,
   leaf_cell_mm2_ASSUMED=leaf_cell/1e6,root_cell_mm2_ASSUMED=root_cell/1e6,
   full_two_rank_50pct_footprint_mm2_ASSUMED=2*(64*leaf_cell+2*root_cell)/1e6,
   net_debit='new association/receipt observer only; no double charge of RF SRAM, W4/W6 original protected state'),
  routing=dict(placement='one leaf beside each existing RF/W6 SM port; one32leaf join at each rank KV controller',
   source_control_bits=86*3+55*7+18+85+86,leaf_root_fanout=32,channel_capacity=None,physical_fit=False),
  clock=dict(domain='same source SM streaming clock; root same enrolled controller edge',
   prospective_ns=1/1.2,setup_uncertainty_ps=constant('UNCERTAINTY_PS'),hold_uncertainty_ps=25,
   additional_CDC='none; any unlike clock enrollment requires separately priced CDC, not combinational crossdomain wires',SSFF=False),
  latency=dict(leaf_request_capture_edges=1,leaf_matching_empty_response_after_capture_min_edges=1,
   leaf_response_capture_edges=1,leaf_release_edges=1,
   root_request_capture_edges=1,root_leaf_request_edges=1,root_leaf_response_capture_edges=1,
   root_response_edges=1,root_release_edges=1,
   eligibility_wait='actual W4/W6 capture and retained reverse+retire; never a timer',
   contender_bound=None,whole_token=None,
   composed_min_root_request_to_cohort_reply_edges=5,
   per_token72reader_drains_min_control_edges=72*5,
   same_min_edges_ns_ASSUMED=72*5/1.2,
   once_only_calendar_keys=['RFcohort.request','RFcohort.leaf.request','RFcohort.leaf.receipts-retired',
      'RFcohort.leaf.response','RFcohort.root.response','RFcohort.release'],
   overlap='observe existing W4/W6 events; their service/reverse latency is NOT charged a second time'),
  safety=dict(quiesce='on offered/retained matching KEY, block matching NEW admission; permit old receipt/reverse retirement',
   association='KV_related and identity64/key20 from actual issuer binding; unrelated classification must also be source-valid, never default false',
   drain='response ONLY from accepted request plus empty matching retained receipt obligations; no provider idle/phaseIDLE/allff',
   runtime_reset='retain accepted receipt identities/fault/quiesce; only coordinated cold POR may discard',
   W6_retire='actual W6 normal retire PLUS observed matching ACK, consumer, child,parent,reverseCDC handshakes',
   no_circular_local_drain='separate w6_local_RF_empty observes W4 receipts only plus matched ACK seen; W6 own retained row is NOT its physical RF cohort',
   local_RF_tap_new_bits=1,
   cold_boot_RF_bit='actual W6 retained no-owner RESET scope plus observed W4 receipts/returns empty; no constant clean' ),
  qualification=dict(functional_source=True,connected_runtime=False,physical=False,headline=False))

if __name__=='__main__':print(json.dumps(model(),sort_keys=True,indent=2))
