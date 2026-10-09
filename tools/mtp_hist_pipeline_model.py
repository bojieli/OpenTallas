#!/usr/bin/env python3
"""Analytical sizing before building the hist-ring registered successor."""
import json

def model():
    return dict(schema='opentallas.mtp_hist_pipeline_model.v1',
                shape=dict(TR=16,NG=4,TW=17,PW=32,PMAX=8,users_per_element=1),
                compute=dict(macs_per_cycle=0,tag_comparisons_per_cycle=1,read_outputs_per_cycle=1),
                memory=dict(token_read_bytes_per_cycle=17/8,token_write_bytes_per_cycle=17/8,tag_read_bytes_per_cycle=4,tag_write_bytes_per_cycle=4,storage_bits=16*(17+32+1)),
                boundaries=dict(write_request_bits_per_cycle=1+32+17,read_request_bits_per_cycle=1+32,commit_bits_per_cycle=1+32,result_bits_per_cycle=1+17+1+1,local_tracks_upper_bound=137,replicas=1,mux='16:1 data/tag selection before registered tag compare',demux='16 write slots from registered position',fanout='local write decode only'),
                floorplan=dict(baseline_routed_cell_area_um2=676.118,baseline_core_area_um2=1991.92,added_register_bits_upper_bound=220,predicted_cell_area_upper_um2=1000,utilization_target=0.30,predicted_core_area_upper_um2=3333.34,predicted_outline_side_um=57.74,slot_outline_side_um=100,slot_fit=True,measured_successor_area_required=True),
                latency=dict(clock_hz=1_200_000_000,old_first_read_cycles=1,new_first_read_cycles=3,added_read_cycles=2,read_stream_cycles=4,old_write_visibility_cycles=0,new_write_visibility_cycles=1,added_write_visibility_cycles=1,added_commit_visibility_cycles=1,added_error_visibility_cycles=2,rollback_data_movement_cycles=0,layer_engram_occurrences=2,per_token_upper_added_cycles=6,per_token_upper_added_ns=5.0,write_fence_requirement='A read request may follow the last accepted write immediately; the first bank read is after registered write visibility.'),
                production=dict(home='Engram hash unit, head or L1/L14 layer die per MR-3',rate_credit=False,area_credit=False,qualification='Exact and physical gates pending; one replica per concurrent user. TT setup and FF hold at >=0 ps per latest direct owner decision; SS sensitivity is reported separately.'))

if __name__=='__main__': print(json.dumps(model(),indent=2))
