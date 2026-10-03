#!/usr/bin/env python3
"""Sizing for the actual GO/W4/W6 hardware capture join, before adoption."""
import json
from tools.hbm_accel.txcount_price import DFF_UM2

def price():
    return {'schema':'opentallas.ha1.actual_capture_join.price.v1','status':'ESTIMATE','default_off':True,
        'context_bits':239,'owner_bits':55,'page_mask_bits':32,'page_ACK_capture_bits':32,
        'W6_visibility_capture_bits':32,'control_bits':5,'raw_bits_per_SM':395,
        'protected_words_per_SM':7,'protected_bits_per_SM':504,'SMs':64,
        'storage_cell_um2_per_SM':504*DFF_UM2,'storage_cell_um2_all64':64*504*DFF_UM2,
        'ports_bits_per_cycle':{'actual_GO':326,'W4_common_ACK':56,'actual_W6_visibility_probe':58,
            'actual_whole_producer_visibility':240,'actual_frame_retire':295,'scheduler_completion':326},
        'memory_bytes_per_cycle':0,'MACs_per_cycle':0,
        'counters':'two popcount32 equality masks; no identity-table replay or fabricated arrivals',
        'additional_storage':'no SRAM/payload storage; seven SECDED words per SM',
        'fanout':'one receiver per actual tap; output does not drive canonical retirement',
        'mux_and_comparator_cost':'ESTIMATE: 239bit tuple equality x2, owner46 equality x2, 9bit slot offsets x2, one-hot32 x2 and popcount32 x2; physical inventory pending',
        'routing_tracks':'ESTIMATE 326 GO + 56 ACK + 58 W6 + 240 producer + 295 retire +326 completion at local SM; actual channel fit unknown',
        'positive_pipeline_cycles':1,'II':'one W4 and one W6 capture per SM each cycle; no two-cycle iteration',
        'latency_composition':'actual source-selected SM/W6 + one capture edge; wire/CDC/credit/refresh unmeasured',
        'context_limits':'Euclid current issuer: one nonzero <=32page range; zeroRF/multiple output groups not inferred',
        'source_selection':'baseline W6 by default; live W6 successor opt-in only, no clock credit',
        'source_selection_64_live_extra_cell_um2':64*213*DFF_UM2,
        'retirement':'Observer context retained through actual matched FRAME retirement and dependency capture; RF source lease remains canonical',
        'adopt':False,'gain':'UNMEASURED; 47 target remains unadopted'}
if __name__=='__main__':print(json.dumps(price(),indent=2))
