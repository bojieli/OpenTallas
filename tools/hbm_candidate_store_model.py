"""Prebuild sizing for finite native TP96 candidate publication storage."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    macro=json.loads((ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json').read_text())
    return dict(schema='opentallas.hbm_candidate_store_model.v1',scope='optin PATHFINDING, no adopted rate or contextual closure',
      ranks=96,quarters=4,flits_per_quarter_max=23,flits_per_rank_max=92,literal_slots_per_flit=15,
      total_flits=8832,raw_bits=8832*512,codeword_bits=576,physical_word_bits=768,
      depth_banks=70,macros_per_bank=3,actual_macros=210,unused_physical_bits=70*128*768-8832*576,
      macro='ot_sram_1r1w_128x256_m1_r2c2',macro_area_um2=macro['area']['macro_area_um2'],
      replicated_macro_area_mm2=210*macro['area']['macro_area_um2']/1e6,
      compute=dict(macs_per_cycle=0,arithmetic_reordering=False),memory=dict(payload_bytes_per_request=64,physical_bytes_per_bank_request=96,single_outstanding=True),
      boundaries=dict(input_flit_bits=545,owner_bits_default=73,owner_bits_supported=74,provider_tuple_bits=34,registered_bank_request_bits=521,registered_bank_response_bits=515),
      mux=dict(depth_bank_fanout=70,response_mux_inputs=70,provider_division='ordinal/15 and ordinal%15 registered before memory request',physical_full_store_routing='hierarchical bank placement and relay allocation pending; standalone bank route only'),
      protection=dict(payload='8 SECDED(72,64) words, held captured raw SRAM output, registered syndrome then registered correction',bank_extra_detect_only_ff_bits=0,control='plain finite transaction state; actual write ACK and publication/read fences; no control mirrors or lease framework'),
      latency=dict(write_ack_cycles=4,read_response_cycles=6,provider_overhead_cycles=2,minimum_store_flit_issue_interval_cycles=5,minimum_provider_literal_interval_cycles=8,full_padded_publication_cycles=8832*5,full_literal_provider_cycles=8832*15*8,serialized_store_service_cycles=8832*5+8832*15*8,serialized_store_service_us=(8832*5+8832*15*8)/1200,whole_token='This920us analytical store-service envelope is additive to native consumer scheduling and actual stalls, with no free overlap; measured provider gate required'),
      floorplan=dict(bank_pathfinding_um=[350,150],bank_macro_area_um2=3*macro['area']['macro_area_um2'],full_store_slot='pending die-owner real allocation'),
      publication='all96 explicit receipts; disabled-empty rank separate receipt; q3 final accepted and all SRAM positive ACKs before enabled rank published',
      adoption='full gate, real provider join, mapped metadata protection, TT/FF DRC0 and contextual budgets required')
