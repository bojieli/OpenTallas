#!/usr/bin/env python3
"""Necessary bounds and source-shaped eight-SM PV tree alternatives.

This model is deliberately not a native or physical PASS. Actual32SM packed
publication and the proven native SRAM layout fix every volume and pairing.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from attention_calendar import ROOT,P


def build():
    sources=[P/'ot_hgi_coll_pring_static.sv',P/'ot_hgi_coll_reduce_static.sv',
             Path('rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_leafh.sv'),
             Path('rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_be.sv'),
             Path('rtl/hbm_accel/sm/static/ot_smh_static_front.sv')]
    area=36.72**2
    stages=[
      dict(name='quadrant_bit0',replicas=4*8,lanes=8,scalar_adders=256,
           peer='q xor1',tx_bits_per_quad=2048,heads_kept='h%2 == q%2'),
      dict(name='quadrant_bit1',replicas=4*8,lanes=4,scalar_adders=128,
           peer='q xor2',tx_bits_per_quad=1024,heads_kept='h==q within KV group'),
      dict(name='block_slot',replicas=4*8,lanes=4,scalar_adders=128,
           initiation_interval=2),
      dict(name='SM_bit0',replicas=4*4,lanes=4,scalar_adders=64,
           pairing=[[0,1],[2,3],[4,5],[6,7]],initiation_interval=2),
      dict(name='SM_bit1',replicas=4*2,lanes=4,scalar_adders=32,
           pairing=[[[0,1],[2,3]],[[4,5],[6,7]]],initiation_interval=2),
      dict(name='SM_bit2',replicas=4,lanes=4,scalar_adders=16,
           pairing=[[[[0,1],[2,3]],[[4,5],[6,7]]]],initiation_interval=2)]
    assert sum(x['scalar_adders'] for x in stages)==624
    nodes=[];edges=[]
    for q in range(4):
      for sm in range(8):
        nodes.append(dict(name=f'q{q}.sm{sm}.stager',kind='two64x512_native_SRAM',
                          parent=f'q{q}',logical_SM=8*q+sm,replicas=1,physical_family='common_SM_stager'))
        for stage in ('A','B','slot'):
          lanes=8 if stage=='A' else 4
          nodes.append(dict(name=f'q{q}.sm{sm}.{stage}',kind='LAT8_scalar_adder_group',
                            lanes=lanes,scalar_master='ot_hgi_coll_pring_static_add_lane',
                            raw_closed_leaf_area_um2=lanes*area,placement_not_granted=True))
        edges.extend([
          dict(src=f'q{q}.sm{sm}.producer',dst=f'q{q}.sm{sm}.stager',bits=269,
               includes='rv1,rrow12,rdata256',kind='fixed_publication',actual_producer_join=False),
          dict(src=f'q{q}.sm{sm}.stager',dst=f'q{q}.sm{sm}.A',bits=512,kind='native_read',II=1),
          dict(src=f'q{q}.sm{sm}.stager',dst=f'q{q^1}.sm{sm}.A',bits=256,kind='quad_bit0',II=1),
          dict(src=f'q{q}.sm{sm}.A',dst=f'q{q}.sm{sm}.B',bits=128,kind='local_keep',II=1),
          dict(src=f'q{q}.sm{sm}.A',dst=f'q{q^2}.sm{sm}.B',bits=128,kind='quad_bit1',II=1),
          dict(src=f'q{q}.sm{sm}.B',dst=f'q{q}.sm{sm}.slot',bits=128,kind='block_slot_pair',II=1)])
      for level,pairs in enumerate((4,2,1)):
        for pair in range(pairs):
          name=f'q{q}.tree{level}.{pair}'
          nodes.append(dict(name=name,kind='LAT8_scalar_adder_group',lanes=4,
                            raw_closed_leaf_area_um2=4*area,placement_not_granted=True))
          for side in range(2):
            src=f'q{q}.sm{2*pair+side}.slot' if level==0 else f'q{q}.tree{level-1}.{2*pair+side}'
            edges.append(dict(src=src,dst=name,bits=128,kind='ordered_SM_tree',II=2))
      edges.append(dict(src=f'q{q}.tree2.0',dst=f'q{q}.VM_SU_PV_input',bits=128,II=2,
                        kind='two_noncontiguous_dimension_pairs',
                        remaining='actual VM sector packing/address writes and SU read calendar'))
    alternatives=[
      dict(name='SM_local_stagers_distributed_tree',status='structural candidate, not qualified',
           placement='stager beside each producer; A/B and local tree stages near incident link endpoints',
           benefit='short producer wires, distributed traffic',
           cost='512bit local stager outputs and eight distributed peer lanes; all relay and tree legs charged'),
      dict(name='central_attention_island',status='structural candidate, not qualified',
           placement='all32 SM/cache/stagers plus four ordered trees in one coherent region',
           benefit='short critical gather, quad exchange and tree legs',
           cost='must relocate every VM/SFU/DMA/SU/PHY/programme/clock/PG incident edge; not a COLL-only translation'),
      dict(name='COLL_adjacent_stagers',status='structural candidate, not qualified',
           placement='32common stager leaves near four collective trees; preserve existing SM homes',
           benefit='long producer trunks are269bits rather than512bit gather trunks',
           cost='producer relay latency enters block-ready; 32source trunks and HBM/service adjacencies remain real')]
    return dict(schema='hcoll-eight-SM-concurrent-source-capacity-v1',
       verdict='MODEL_AND_REQUIRED_GRAPH_ONLY',
       source_binding={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
       shape=dict(tokens=8192,SM=32,quadrants=4,SM_per_quad=8,KV_groups=2,query_heads_per_KV=4,
                  block_rows=128,block_slots_per_SM=2,head_dimensions=128,output_FP32_words=1024),
       actual_layout=dict(publication='lane2h+half=head h,dim=rrow+64half,rrow0..63',
                         SRAM='512bits={publication_beat_odd,publication_beat_even}',
                         row_sequence='slot0pair0,slot1pair0,...slot0pair31,slot1pair31',
                         native_reads_per_SM_per_KV=64,total_native_reads=4096,
                         fixed_stream_input_edges=128,publication_edges_per_SM_all_KV=256),
       arithmetic=dict(FP32_adds=63*1024,current96_lane_ideal_floor=672,
                       ring8_lanes_per_quad_cross_phase_floor=1536,
                       current16_vector_lanes_per_quad_only_floor=1008,
                       new_scalar_adders=624,raw_reused_adder_footprint_mm2=624*area/1e6,
                       added_vs96_raw_footprint_mm2=(624-96)*area/1e6),
       transport=dict(per_quad_A_sent_FP32_words=8192,per_quad_B_sent_FP32_words=4096,
                      A_FP32_words_per_quad_edge=64,B_FP32_words_per_quad_edge=32,
                      A_raw_data_bits_per_direction=2048,B_raw_data_bits_per_direction=1024,
                      source_native_SRAM_data_bits_per_quad_edge=4096,
                      metadata_reset_clock_PG_not_included_in_data_bits=True),
       static_latency=dict(stages=stages,FP32_latency=8,link_A_registered_edges=2,link_B_registered_edges=2,
                           proposed_first_output_edge=52,proposed_last_output_edge=178,
                           source_bank_request_to_first_input_edges=4,
                           proposed_last_from_first_bank_request_edge=182,
                           scope='derived cycle contract, must be measured on literal native RTL; no physical relay assumption',
                           reference_merge_edges=318,reference_times_1p05=333.9,
                           residual_for_real_relays_writes_and_extra_faces_edges=333.9-182),
       cost_limits=dict(unit=0.05,design=0.15,status='native full-token delta unmeasured; no acceptance or repricing'),
       dedicated_stager=dict(macros_die=64,macro_shape='64x512',raw_macro_area_mm2=0.85243871232,
                             status='primary structural allocation; physical grant and raw-row source profile pending'),
       graph=dict(nodes=nodes,edges=edges),alternatives=alternatives,
       remaining=['actual624adder native proof and fixed slot mutants','actual32SM raw SRAM producer binding',
                  'current source-bound pin/clock geometry with every incident edge','actual VM/SU final writes and read slots',
                  'TTsetup FFhold DRC0 physical proof; SS sensitivity only','measured full-shape token throughput against immutable price'])


if __name__=='__main__':
    print(json.dumps(build(),indent=2))
