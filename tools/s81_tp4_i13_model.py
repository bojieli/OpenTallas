#!/usr/bin/env python3
"""Top-down sizing before the S81 TP4 rank-aware indexed13 TX build."""
from math import ceil


def build(k=512, dense_windows=8192, slot=(626.4,561.6)):
    cache_entries=2*k
    cache_bits=2*cache_entries*36
    fifo_words=128
    fifo_bits=fifo_words*(512+8)
    idx_fifo_bits=64*(320+16)
    pipeline_bits=16*40+8*(13*36+13+3)+2048+idx_fifo_bits
    ff=cache_bits+fifo_bits+pipeline_bits
    logic_proxy=cache_entries*(20+16)+24000
    cell_proxy=ff+logic_proxy
    # Calibrated existing unified-model DFFHQNx1 proxy, not a measured fit.
    stdcell=ff*.2916+logic_proxy*.12
    dense_sram=ceil(dense_windows/1024)*172.824*41.064
    area=slot[0]*slot[1]
    emitted_words=ceil(k/13)+4  # at most four rank headers
    lookups=k
    return dict(schema='opentallas.s81.tp4.i13_model.v1', status='SIZED_BEFORE_RTL',
        clock_ps=833, macs_per_cycle=0, replicas_per_bk_partition=1,
        precision='scores16 BF16, exact original20bit index; no arithmetic/reduction reorder',
        throughput=dict(lookups_per_cycle=1,candidates_per_i13_word=13,
                        link_bits_per_cycle=276,link_beats_per_word=2,
                        i13_words_upper=emitted_words,link_beats_upper=2*emitted_words,
                        lookup_cycles=lookups,lookup_pipeline_edges=3,
                        reserved_grid_slots=640,added_rank_headers_upper=4),
        memory=dict(dense_bits=dense_windows*256, dense_read_bytes_per_cycle=32,
                    dense_write_bytes_per_cycle=32,candidate_cache_bits=cache_bits,
                    cache_entries_per_bank=cache_entries,cache_banks=2,
                    input_fifo_words=fifo_words,input_fifo_bits=fifo_bits,idx_fifo_bits=idx_fifo_bits,
                    worst_input_candidates=2*k,lookup_cache_read_bits_per_cycle=cache_entries*36,
                    cache_write_bits_per_cycle=36),
        crossing=dict(inputs=['vi276','vo276'],outputs=['lo276','st16'],
                      extra_pins=0,external_cycles=0,
                      same_pin_windows=True,signals_layers='M1-M7; clock/reset/PG M8-M9'),
        floorplan=dict(slot_um=list(slot),slot_area_um2=area,
                       native_dense_sram_area_proxy_um2=dense_sram,
                       new_data_control_ff_bits=ff,new_logic_cells_proxy=logic_proxy,
                       total_cells_proxy=cell_proxy,hard_cap_cells=400000,
                       stdcell_area_proxy_um2=stdcell,
                       free_area_after_sram_um2=area-dense_sram,
                       standard_cell_fill_proxy=stdcell/(area-dense_sram),
                       physical_status='NOT FIT/CTS/ROUTE; render channels and RAM groups after synthesis'),
        latency=dict(old_dense_slot_budget=1600,new_i13_slot_budget=640,
                     per_tp_stage_max_cycles=640+3,full_two_stage_core_cycles=2*(640+3),
                     link_plan_cycles='added from current six-lane plan, not assumed away',
                     model_admission='candidate only; measured RTL and composed schedule must replace640 before claim'),
        gates=dict(sizing=cell_proxy<=400000 and stdcell<.55*(area-dense_sram),
                   exact_rtl=False,production_throughput=False,physical=False),
        failure_policy=['tag miss faults','duplicate ID faults','out-of-order quarter faults',
                        'no host/fixture fallback','input FIFO overflow faults'])
