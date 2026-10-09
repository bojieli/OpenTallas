#!/usr/bin/env python3
"""MD6 actual32-row A successor: model before RTL; no closure credit."""
import json,math

def model():
    r=math.ceil(129280/12);a=4*math.ceil(r/128);macros=2*a
    return dict(schema='opentallas.md6.head-binding.v1',enabled_default=False,adopted=False,PINREG_default=0,CACHE_PINREG_default=0,CACHE_PINREG_candidate=1,cache_added_payload_FF=512,cache_added_enable_FF=256,cache_added_control_FF=7,PINREG_candidates=[1,2],PINREG_added_FF=513,unconditional_PINREG2_switching_energy="unmeasured; no energy credit",
      shape=dict(vocab=129280,shards=12,assignment_status='proposed 12-shard capacity; semantic row manifest pending',max_rows_per_shard=r,A_elements_per_shard=a,rows_per_A=32,padded_rows_per_shard=a*32-r,K=256),
      MACs_per_cycle=dict(per_A=16,per_shard=16*a),compute_intensity_MAC_per_weight_byte=.5,
      ports_bytes_per_cycle=dict(local_weight_pair=32,staged_embedding_lane=32,head_logit=.125,joined_logit=.125),
      boundary_bits_per_cycle=dict(per_A_weight=256,per_A_embed=256,per_A_logit=32,die_embed_broadcast=256*a),
      replicas=dict(row_engine_per_shard=a,weight_macros_per_shard=macros,embed_capture_copies_per_shard=a,head_buffer_rows_per_A=2),
      mux_demux_fanout=dict(weight_pair_select=2,embed_beat_mux=16,embed_broadcast_recipients=a,head_FIFO_depth=2,valid_vocab_mask='global_row<129280 and localrow<VALID_ROWS',mask_FF_per_A=6,best_valid_bit=True),
      routes=dict(per_A_data_tracks_needed=544,candidate_corridor_um=32,M2_M3_pitch_um=.036,tracks_per_layer_raw=888,at70pct_tracks_per_layer=621,capacity_basis='pinnedASAP7tech1x LEF M2/M3 PITCH0.036; macroaccess/PG/routedcapacity remainunqualified',fit='544lanedata tracks below621single-layer corridor budget; actualmacroaccess andDRC required'),
      weight_storage=dict(payload_per_shard_bytes=r*512,allocated_macro_payload_bytes=macros*4096*32,
        useful_words_per_macro=256,pair_mapping='physical word =16*local_row+beat; macro=word%2; macro_addr=word//2',ROM_ECC=False),
      area=dict(weight_macros_mm2=macros*7881.4/1e6,weight_slot_at60pct_mm2=macros*7881.4/1e6/.60,
                vector_copies_bytes=a*512,engine_area=None,candidate_slots_um=[[600,600],[300,380]],candidate_slot_total_mm2=[a*.36,a*.114],measured_baseline_stdcell_um2=24017.7,measured_baseline_macro_um2=15762.7,measured_baseline_instances=168910,slot_fit=False),
      latency=dict(head_row_cadence_cycles=256,full32_measured_cycles=dict(query=9,headgo=33,firstroot=488,lastroot=8424,firsthead=501,lasthead=8437,firstjoin=685,lastjoin=8621,argmax=8622,joinIImin=256,joinIImax=256,headstall=0,headwait=0,queuehigh=1),first_root_to_last_join_cycles=8133,first_root_to_argmax_cycles=8134,cold_query_to_argmax_cycles=8613,cold_query_to_argmax_ns=8613/1.2,full32_measurement_scope='one actual released 32-row A with PINREG2 CACHE_PINREG1; external transport excluded',ragged_measured=dict(valid16=dict(firsthead=28,lastjoin=4052,argmax=7966),valid6=dict(firsthead=28,lastjoin=1492,argmax=7966),valid0=dict(firsthead=28,lasthead=7964,argmax=7966,best_valid=False,joined_rows=0),queue_highwater_max=1,head_full_cycles=0,scheduled_head_rows=32,padding_drain_after_last_head_cycles=2),external_A_input_transport_cycles=4,external_A_input_transport_scope="owned die input staging; not in this directA bench",local_weight_first_beat_cycles=5,local_weight_last_beat_cycles=20,
                   Markov_first_beat_to_result_cycles=178,head_to_join_bound_cycles=186,head_to_join_measured_cycles=184,head_to_join_measured_ns=184/1.2,
                   tail_ns_upper=186/1.2,prior_54_6ns_met=False,
                   embed_request_to_last_beat_prior_functional_cycles=22,cache_staging_cycles=2,embedding_commit_to_head_go_cycles=2,embed_physical_capture_pending=True,
                   buffer_capacity='2 head rows +1 active row; engine service186 <256 arrival'),
      timing=dict(clock_GHz=1.2,macro_clkq_SS_ps=744,capture_edges_after_read=2,
                  single_edge_macro_capture_slack_ps=833-744-25-60,minimum_SS_margin_ps=15),
      open=['embed port contextual capture closure','head +Markov SS/FF closure','full-shard capacity/fanout','final die integration'])
if __name__=='__main__':print(json.dumps(model(),indent=2))
