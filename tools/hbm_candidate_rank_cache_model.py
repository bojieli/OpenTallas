"""Pre-RTL proposal: retain corrected candidate flits across native TP96 interleave."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    ranks=96;flits=8832;slots=15;ff_area=.2916
    per_rank_bits=512+7+1
    extra_ff=ranks*per_rank_bits+6*512
    mux_bit_count=6*15*512+5*512+14*34
    cache_hit_ii=5;cache_miss_ii=9
    read_cycles=flits*(cache_miss_ii+(slots-1)*cache_hit_ii)
    base=flits*slots*8;publication=flits*5
    return dict(schema='opentallas.hbm_candidate_rank_cache_proposal.v1',status='MODEL/PROPOSAL ONLY; Claude review before RTL/route, no measured adoption',
      production_schedule=dict(contract='valid block_id%96 must equal rank; ascending canonical block order',
        dense_native_read_rank_sequence='0..95 repeatedly; each rank ordinal increments once per sweep',
        source='rtl/hbm_accel/index/ot_hbm_index_global_order.sv',
        source_sha256=hashlib.sha256((ROOT/'rtl/hbm_accel/index/ot_hbm_index_global_order.sv').read_bytes()).hexdigest()),
      alternatives=dict(single_flit=dict(data_bits=512,rank_bits=7,flit_tag_bits=7,valid_bits=1,
        native_dense_hits=0,claim='reject15x reuse claim; rank switching defeats single-line reuse'),
        rank_local96=dict(entries=96,corrected_payload_bits=49152,flit_tag_bits=672,valid_bits=96,
          extra_group_capture_ff_bits=3072,extra_ff_bits=extra_ff,holding_line_bits=512,
          holding_line_source='reuse existing payload_q after publication; no concurrent write/read',
          read_bank_operations_max=8832,instead_of=132480,
          read_traffic_reduction_ratio=15,control='plain finite valid/tag/request stage, no mirrors/TMR/controlECC/epoch/lease extension',
          invalidation='all valid cleared on actual new publication/reset/retirement/fault; entry replaced on flit tag miss; other rank requests retain independent rank-local seats',
          CE='decode/CE event once on real SRAM fill response; cache-hit rsp_ce0; never count CE again for14remaining slots',
          UE='do not install cache; preserve actual bank poison/fault and no publication/read success',
          valid_padding='all15 literal slots retained; lv0 never collapsed; last uses actual published extent',
          port_cuts='6 groups×16rank rows: registered16:1 local512b selection, registered6:1 group selection, registered15:1 tuple extraction; plain credits/one outstanding'),
        streamed_batch=dict(golden_order='may not emit15tuples ofrank0 before next rank; valid native IDs interleave96ways',
          required_retained_bits_at_15x_reuse=96*512,
          conclusion='batching across96ranks requires same retained flits or equivalent SRAM; no lower-storage speed claim without actual sparse/gap schedule proof')),
      area=dict(ff_area_um2_proxy=extra_ff*ff_area,ff_area_basis='unified DFFHQNx1 proxy0.2916um2; not mapped area',
        bit_muxes=mux_bit_count,mux_area_um2_proxy=mux_bit_count*.2,mux_basis='unified assumed0.2um2 per bit2to1mux',
        data_logic_proxy_um2=extra_ff*ff_area+mux_bit_count*.2,
        extra_placement_proxy_mm2_55pct=(extra_ff*ff_area+mux_bit_count*.2)/.55/1e6,
        slot_proposal='6 registered16-rank groups, each100x100um; context placement/CTS/hub-layer review required',
        added_macros=0,existing_payload_macros=210),
      bandwidth=dict(bank_payload_bytes_per_miss=64,bank_raw_bytes_per_miss=96,
        full_bank_payload_read_bytes=flits*64,baseline_full_bank_payload_read_bytes=flits*slots*64,
        group_output_bits_per_transfer=512,groups=6,global_selected_group_bits=512,
        tuple_output_bits=34,memory_port_outstanding=1,compute_macs_per_cycle=0),
      latency=dict(cache_hit_min_interval_cycles=cache_hit_ii,cache_miss_min_interval_cycles=cache_miss_ii,
        full_provider_cycles=read_cycles,baseline_full_provider_cycles=base,
        publication_cycles_unchanged=publication,total_store_service_cycles=publication+read_cycles,
        total_store_service_us=(publication+read_cycles)/1200,baseline_store_service_us=(publication+base)/1200,
        saved_store_service_us=(base-read_cycles)/1200,
        scope='analytical dense/maxpadded envelope; actual sparse ordering, invalid slots and stalls must be measured; native consumer scheduling remains additive; no overlap credit'),
      gate=dict(required=['full15slot exact includinglv0/finalextent','actual96rank interleave andtag transitions','empty disabled receipts and enabled allpadding','heldresponse stalls/reset/retire fence','realmacro CE once andUE quarantine','same-source staleflit tag mutant must FAIL'],
        baseline_preservation='existing bankPASS/mutantFAIL and fullstore730gate continue unchanged',
        physical='bank macro/wrapper unchanged; added rank-cache groups require Claude structural review before RTL and routes'))
