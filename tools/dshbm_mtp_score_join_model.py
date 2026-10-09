"""Real stored-DLOG request/response then exact LAT3 add, before RTL."""
def model():
 return dict(schema='opentallas.dshbm.mtp.score_join.model.v1',default_enabled=False,
  macs_per_cycle=0,compute_intensity='one golden FP32 stored-logit plus Markov addition per row',
  memory_bytes_per_cycle={'stored_logit':4},boundary_bits_per_cycle={'Markov_score':122,'DLOG_response':122,'combined_score':122},
  replica_count=3072,mux_demux_fanout='one held row and one actual tagged DLOG response per SM',
  area={'new_join_flop_bits':190,'FP32_add':'existing ot_hdc_fp32_add_lat LAT3; actual separately priced operator',
        'stream_to_serial_CDC':'existing ot_s81_pulse_cdc QD64 W122: two64-entry payload arrays,15616 bits plus pointers'},
  routing_tracks_needed=487,channel_capacity='actual CP/result/VM routes pending',floorplan_slot='SM-local result epilogue unqualified',
  clock_domains={'native_score':'1.2GHz','stored_logit_add':'0.9GHz LAT3'},
  latency_cycles={'serial_row_accept':1,'DLOG_req_accept':1,'actual_DLOG_response':'provider-measured','FP32_add':3,'held_output':1},
  composed_latency='actual43-row SM stream overlapped with one-row finite DLOG/add/argmax; CDC64 can retain all43 outputs even if serial consumer pauses',
  gates=['same released43x256/native43row payload','source-pinned nonzero head logits','actual tagged response reject','operand mutation detected'],
  reset='MX1 caller drains source queues, current row/add/output, rank collector and result return before both-domain reset',
  protection='actual SRAM/HBM DLOG provider retains payload SECDED; local join/control flops have no ECC/mirrors',
  physical_qualified=False)
