"""Before-build sizing for the real fixed-slot VM -> original SM activation producer."""
import json


def model():
    positions, k, lane_blocks, c, column_bits, beat_bits = 8, 5120, 4, 8, 3152, 2048
    groups = k // (lane_blocks*c*32)
    addresses = groups*c
    pairs = addresses//2
    waves = positions*lane_blocks*pairs
    beats_per_address = (positions*column_bits+beat_bits-1)//beat_bits
    return dict(schema='opentallas.hbm.vm-sm-activation-static-model.v1', adopted=False,
        source_scope='Actual fixed-cycle two-AQ12 rawFP8code+exponent, real SRAM fragments and programme, actual VM RG2; original SM pins unchanged',
        native_shape=dict(P=positions,K=k,NC=8,SUB=4,fmt=1,blocks32=positions*k//32,
                          source_FP32_words=positions*k,source_sectors=positions*k//8,
                          source_bytes=positions*k*4,fragment_addresses=addresses,
                          fragment_bits=positions*column_bits,meaningful_FP8_bits_per_address=positions*lane_blocks*266,
                          beats_per_address=beats_per_address,xwrite_beats=addresses*beats_per_address),
        compute=dict(quantizers=2,FP32_words_per_edge=64,quantizer_raw_output_bits=266,
                     VM_issue_edges=waves,VM_sectors_per_edge=8,request_bits=136,response_bits=2056,
                     AQ_sample_to_output_NBA=17,AQ_sample_to_downstream_capture=18,
                     quantizer_clock_roots_each=3,nominal_AQ_FF_each=dict(core=2597,delay=11264,encode=6019)),
        storage=dict(code_macros=16,code_macro='ot_sram_1r1w_32x128_m1',code_bits=16*32*128,
                     meaningful_code_buffer_bits=2*2*8*4*256,exponent_FF_bits=2*2*8*4*10,
                     epoch_FF_bits=2*2*8*4*21,valid_FF_bits=2*2*8*4,
                     programme_macros=1,programme_macro='ot_sram_1r1w_1024x256_m2_r2c2',programme_payload_bits=44),
        replicas=dict(component_producer=1,original_XWRITE_destinations=32,
                      broadcast='32SM fanout needs actual fixed-stage registered transport/geometry; component pin stream does not qualify that graph',
                      alternative_four_SID='comparativeonly; same2AQ can select staticallyscheduled quarter percolumn; no phantom4portSM'),
        clocks=dict(programme=1,control=1,AQ=6,code_quarters=4,total=12,
                    relation='all actual entries same functional compiler edge, die phi-R; no asynchronous waiver'),
        schedule=dict(pair_read_edges=32,pair_emit_edges=26,pair_period=32,
                      buffers=2,code_commit_after_first_programme_output=29,
                      first_emit_programme_ordinal=61,emit_to_XWRITE_NBA_edges=6,
                      first_xwrite_after_start=71,predicted_last_xwrite_after_start=704,
                      predicted_last_SM_capture_after_start=705,measurement_required=True),
        compiler=dict(target=126,read_group=2,native_SID=0,read_base_alignment_words=64,
                      profile='contiguousSID0 v1; preserve calleraddress andbounds; no releasedactivationbase/globaltimestamp invented',
                      fields='readV1,sector16,buffer1,column3,lane2,emitV1,emitBuffer1,address7,group4,last1,readQID2,pairEpoch5'),
        model_cost_status='Added latency and MACRO/pin/clock area must be composed with immutable fullSM budget; no repricing or source-only qualification',
        evidence_input='40,960 external SeedX FP32 words, SHA8139fc833a6f006d35e7b416c58ce216864c6510dffba907d57bfd828f0acfae; not released activation replay')


def four_sid_comparison():
    return dict(schema='opentallas.hbm.vm-sm-activation-four-sid-proposal.v1',adopted=False,
        baseline='contiguous singleSID0 source→actual2AQ/fragmentSRAM→same520XWRITEbeats',
        candidate_layout='logicalcolumn p -> q=p%4, localcolumn=p//4; four explicit SID-local bases; localFP32word=base[q]+localcolumn*K+feature',
        actual_source_resource='GLU output WG0 perQ; dedicatedSM readgroup2 perQ, existinggroups time-shared by compiler only; no new physicalSRAMports or SMports',
        versioning='separate descriptor/profile and emitted perQ calendars; originalsingleSID MDESC unchanged',
        desired_GLU_reservations='four quarters WG0 on exact actual256laneproducer output edges; timestamps pending; currentSU/SFU/HCWG0 conflict census missing, cannot grant',
        actual_competitors=dict(SW=['SU/SFU/HC WG0','Quant125 WG1'],SE=['SU/SFU/HC WG0'],
                                NW=['SU/SFU/HC WG0','CP WG1','Quant48 WG2'],NE=['SU/SFU/HC WG0','ATT WG1','HC WG2']),
        consumer='one originalNC8/SUB4 XWRITE2048/addr7/group7 input. TwoAQ reuse keeps640VMwaveedges;4Q topology avoids crossSID copies but does not multiply quantizer throughput.',
        physical_required='four realRQ136/RR2056 legs, pin registered ingress and static quarterselector, actual fixed perQ relay latency andclockroots; ordered arrivals scheduled not response-arbitrated',
        unresolved=['actualGLU epoch/write timestamps','source K/P/stride matching3072GLU versus5120component','allWG0 producer conflict trace','actual fourSID allocator','ingress reach/fixed relay edges','full kernel immutable price'],
        throughput='Do not use131edge old estimate. OwnerconservativeGLU134 before programme/store/drain, nearSU130 conditional; no native price claim')


if __name__ == '__main__': print(json.dumps(dict(primary=model(),comparison=four_sid_comparison()),indent=2))
