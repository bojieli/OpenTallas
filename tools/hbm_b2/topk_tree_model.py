#!/usr/bin/env python3
"""Pre-build structural model for the unchanged 512-record TOPK producer."""
import json


def model():
    n,w,live=64,64,36
    levels=6
    raw_mux=n*w*sum(range(1,levels+1))
    live_mux=raw_mux*live//w
    # Upper bounds on generic bit MUXes, not an ASIC sign-off prediction.
    carry_shift_mux=72*live*3
    bank_write_mux=8*8*8*live
    carry_select_mux=9*7*live
    combine_or=levels*n*live
    return dict(schema='opentallas.hbm.topk_tree_model.v1',clock_period_ps=833,
        arithmetic='bit records only; no FP operation/reduction order changes',
        ingress=dict(bits_per_cycle=2368,records_max_per_cycle=64,record_bits=64,live_record_bits=36),
        memory=dict(banks=8,words_per_bank=64,word_bits=512,writes_per_bank_per_cycle_max=1,
                    bytes_per_cycle_max=512,macro_area_um2=8*171.288*77.760),
        calendar=dict(ingest_slots=171,records_per_frame=512,emit_beats=16,flits_per_beat=4,
                      emit_interval=8,added_boot_cycles=0,added_data_cycles=0),
        boundaries=dict(public_pins_unchanged=True,off_die_output_bits=2180,valid_bits=4),
        structure=dict(tree_levels=levels,raw_tree_mux_bit_upper=raw_mux,
                       constant_pruned_tree_mux_bit_upper=live_mux,
                       carry_shift_mux_bit_upper=carry_shift_mux,
                       bank_write_mux_bit_upper=bank_write_mux,
                       carry_select_mux_bit_upper=carry_select_mux,
                       combine_or_bit_upper=combine_or,
                       logic_cell_estimate=3*(live_mux+carry_shift_mux+bank_write_mux+carry_select_mux)+combine_or,
                       estimate_scope='conservative3cells/bitMUX; actual mapping/cell400k cap still required'),
        state=dict(carry_bits=448,old_carry_bits=4608,payload_reset_loads_added=0),
        floorplan=dict(outline_um=[650.16,500.04],area_um2=650.16*500.04,
                       macro_fraction=8*171.288*77.760/(650.16*500.04)),
        qualified=False,open_gates=['full-shape mapped cells','floorplan review','TT/FF sign-off'])

if __name__=='__main__':print(json.dumps(model(),indent=2))
