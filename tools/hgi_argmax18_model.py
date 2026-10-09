#!/usr/bin/env python3
"""HGI-1 argmax width/offset extension; structural sizing before RTL."""
import json

def model(lp=8, flat=7, fast=1):
    ll=(lp-1).bit_length()
    latency=flat+fast+ll+2
    return dict(schema=1, block='ot_hgi_argmax18_m', native_leaf='ot_dshbm_argmax_m',
      macs_per_cycle=0, comparisons_per_cycle=lp, memory_bytes_per_cycle=0,
      input_bits_per_cycle=lp*64+lp+3, output_bits_per_row=53,
      rank_bits=7, immediate_bits=18, product_bits=25,
      replicas_per_die=1, local_index_bits=18, latency_cycles=latency,
      added_token_cycles=0, leaf_pipeline_extra_index_flops=flat+1+lp+lp*(ll+1)+1,
      winner_value_pipeline_flops=32*(lp+lp+sum(lp>>j for j in range(ll+1))+1),
      offset_pipeline_flops=(latency-1)*25+25+1,
      offset_compute='7x18 unsigned multiply registered at row entry; parallel to native reduction',
      output_compute='25-bit unsigned sum; overflow flagged, never silently truncated',
      ds_default='GENERIC18=0; native IW17 index zero-extended; offset disabled',
      channel_tracks_required=lp*64+lp+3+7+18+21,
      channel_capacity='132um per input edge x2 layers x12bits/um=3168bits; pin-lint confirms intake',
      slot_width_um=180,slot_height_um=140,slot_area_um2=25200,
      slot_stdcell_budget_um2=11918,
      measured_mapped_stdcell_um2=5767.945, measured_mapped_cells=40040,
      measured_source='f6d441b6a',
      slot_fit='mapped area fits; routed area/DRC/timing pending',
      area_status='measured synthesis only; no routed closure claim',
      mux_cost='first-beat row offset selection; compile-time default eliminates generic logic',
      token_model='parallel offset adds zero cycles to existing head epilogue')
if __name__=='__main__': print(json.dumps(model(),indent=2))
