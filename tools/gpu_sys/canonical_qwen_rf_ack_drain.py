"""Source port map for actual W4/W6 RF/commonACK drain responders.

No byte store, clocks, timers, fake ready, software debt or native handlers.
This names the real handshake observations and gates the enclosing owner wires.
"""
from pathlib import Path
COHORT=4
FILES=('results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs/ot_gpu_w6_secded_pkg.sv',
       'rtl/model/qwen_rf_ack_drain_20261003/ot_gpu_qwen_rf_ack_drain.sv',
       'rtl/model/qwen_rf_ack_drain_20261003/ot_gpu_qwen_rf_ack_drain_join.sv')


def source_files(root):return [str(Path(root)/p) for p in FILES]


def port_bindings():
 return dict(
  cohort_index=COHORT,rank_replicas=2,SM_leaves_per_rank=32,
  actual_W4=dict(
   rf_write_accept='provider.wr_valid && provider.wr_ready',
   rf_write_owner55='{provider.wr_owner,provider.wr_addr}',
   rf_ack_valid='provider.ack_valid',rf_ack_accept='provider.ack_valid && provider.ack_ready',
   rf_ack_owner55='{provider.ack_owner,provider.ack_slot}',rf_ack_fault='provider.ack_identity_fault',
   rf_read_accept='provider.rd_valid && provider.rd_ready',rf_read_a='provider.rd_a',rf_read_b='provider.rd_b',
   rf_rsp_valid='provider.rsp_valid',rf_rsp_accept='provider.rsp_valid && provider.rsp_ready'),
  actual_W6=dict(
   w6_request_accept='fence.req_valid && fence.req_ready',w6_request_owner55='fence.req_identity',
   w6_internal_SIMD='fence.req_internal_SIMD',
   w6_host_ACK_accept='fence.host_ack_valid && fence.host_ack_ready',
   w6_SIMD_ACK_accept='fence.simd_ack_retire_valid && fence.simd_ack_retire_ready',
   w6_ACK_owner55='(fence.simd_ack_retire_valid && fence.simd_ack_retire_ready) ? fence.simd_ack_retire_identity : fence.host_ack_identity',
   w6_consumer_accept='fence.consumer_valid && fence.consumer_ready',w6_consumer_owner55='fence.consumer_identity',
   w6_child_accept='fence.child_reverse_valid && fence.child_reverse_ready',w6_child_owner55='fence.child_reverse_identity',
   w6_parent_accept='fence.parent_reverse_valid && fence.parent_reverse_ready',w6_parent_owner55='fence.parent_reverse_identity',
   w6_CDC_accept='fence.reverse_CDC_valid && fence.reverse_CDC_ready',w6_CDC_owner55='fence.reverse_CDC_identity',
   w6_retire_accept='fence.retire_valid && fence.retire_ready',w6_retire_owner55='fence.retire_identity',
   w6_local_drain_owner55='fence.drain_req_identity',
   w6_local_drain_has_owner='fence.drain_req_has_owner',
   w6_local_drain_reset_scope='fence.drain_req_reset_scope'),
  admission=dict(
   write='provider.wr_valid = selected_writer_valid && wr_permit; selected_writer_ready = provider.wr_ready && wr_permit',
   read='provider.rd_valid = selected_reader_valid && rd_permit; selected_reader_ready = provider.rd_ready && rd_permit',
   W6='fence.req_valid = actual_caller_valid && w6_permit; caller_ready = fence.req_ready && w6_permit',
   ACK='provider.ack_ready = actual_receiver_ready && rf_ack_allow',
   response='provider.rsp_ready = actual_receiver_ready && rf_rsp_allow',
   existing_returns='consumer/child/parent/reverseCDC and W6 retire remain allowed to drain old obligations, not masked by matching-new-admission stop'),
  actual_binding='wr/rd/w6 binding_valid, KV_related,identity64,key20 from retained ACTUAL issuer classification; nonKV must be classified explicitly too',
  W6_local_RF_bit='w6_local_RF_empty is W4 accepted/held-return obligations empty plus actual W6 ACK seen, excludes W6 own row; do NOT use global KV cohort response here',
  parent_hold=dict(
   df414='consumer_drain.enabled.raw[333] / exposed drain_retained: actual retained drain owner',
   Dewey_connected='kv.reader_services.release_live: actual retained reader release, not ~drained/idle',
   no_new_parent_storage=True),
  outputs='rank join drain_rsp_valid/identity64/key20/empty -> endpoint index4; hold from actual ALLcohort release owner',
  reset='por_n coordinated cold discard only; runtime rst_n faults and retains identities/hold',
  scope='source observer, not a new provider/ACK/W6 authority; original ACK_ID1/W6 sources must stay actual and enabled')
