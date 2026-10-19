#!/usr/bin/env python3
"""Model-only mixed dense/attention context and native compiler timing contract.
No compiler, issuer, frontend, or application RTL changes are implemented here.
"""
from __future__ import annotations
import json

ISSUER_COMMIT = '825607a54'
ISSUER_MAIN = '944bbb859'
ISSUER_SHA256 = '6acb3e9d66d70ceb211c86a317868e10bb15716787fdf9b3815a08b57d407d07'


def context_model(class_source='mode197', landing_bits=2, queue_depth=4):
    assert class_source in ('mode197', 'explicit200')
    assert landing_bits == 2 and queue_depth == 4
    explicit = class_source == 'explicit200'
    issuer_bits = 2 * int(explicit) + 2 * queue_depth + 1
    return dict(
        status='PROPOSED; root decision before RTL', class_source=class_source,
        source_freshness=dict(issuer_commit=ISSUER_COMMIT, main_commit=ISSUER_MAIN,
                              issuer_sha256=ISSUER_SHA256, ID_COHORT=1,
                              retained='cohort validation, freshness clear, layer/id predicates and fixed-slot faults'),
        descriptor=dict(width_bits=256, class_bit=200 if explicit else 197,
                        class_meaning='1 attention converter consumes, 0 dense packet consumes',
                        reserved_zero='231:201' if explicit else '231:200',
                        identity_bits='239:232', magic_bits='255:240',
                        programme_payload_change_bits=0, descriptor_count_change=0),
        issuer=dict(a_p_bits_before=200, a_p_bits_after=201 if explicit else 200,
                    start_go_queue_before=110, start_go_queue_after=111,
                    class_queue_bit=110, queue_slots_each=4,
                    s_ent_bits_before=110, s_ent_bits_after=111,
                    added_source_ff=issuer_bits),
        context=dict(svg_before=46, svg_after=47, class_bit=46,
                     lower_46_bits='unchanged', xc_bits=5,
                     xc_reserved_check_change=explicit),
        banked_token=dict(before=108, after=109, context_bits='89:43',
                          pc_bits='10:0', ordinal_bits='42:11', iteration_bits='105:90',
                          last_iteration_bit=106, last_word_bit=107, valid_bit=108,
                          padded_width_before=108, padded_width_after=112,
                          ring_count=3, ring_slots_each=4,
                          added_semantic_ring_bits=12, added_ring_source_ff=54,
                          added_other_context_source_ff=8,
                          added_semantic_total_bits=20, added_allocated_source_ff=62,
                          mapped_delta='OPEN; constants may map away, phase replicas require census'),
        command=dict(internal_envelope_before=83, internal_envelope_after=84,
                     external_sm_command_bits=83, packet_bits=1099,
                     stages='class joins word at R; C class follows same word; then existing native d1/d2 envelope',
                     PREL0='select R class', PREL1='select C class',
                     extra_source_ff_with_native_cache=4,
                     extra_pipeline_edges=0,
                     checker='mask dense-check bit25 iff command-associated class=1; packet-valid/tag checks always active',
                     prohibition='no live-descriptor selection and no separate long flag shift chain'),
        source_ff_delta_banked_native=issuer_bits + 62 + 4,
        macros_added=0, programme_store_words_added=0, ingress_edges_added=0,
        pins=dict(issuer_to_feed_context_bits_added=1, external_sm_pins_added=0,
                  each_existing_svg_token_lane_bits_added=1),
        physical='OPEN: kept control copies, reset ownership, mapped fanout/reach/clock and wrapper audits',
        compiler='mode197: write mode4/6/7 in attention descriptor even with mrel0; verify every literal magic word has the descriptor class; expose and price every required GO split for a mixed-class programme',
        coexistence='a dense descriptor, attention descriptor and dense descriptor must retain each word class through intervening idle and retire tails')


def timing_profile(*, native_landing=False, native_return=False,
                   native_cache_safe=False, banked_calendar=False):
    calendar_extra = 2 * int(banked_calendar)
    command_only_extra = 2 * int(native_cache_safe)
    command_extra = calendar_extra + command_only_extra
    native_capture_stream_edges = (3 * 1024 + 833 - 1) // 833
    native_base = native_capture_stream_edges + 2 + 2 + 3
    native_padding = native_base * int(native_landing) + 7 * int(native_return) + 4 * int(native_cache_safe)
    return dict(native_landing=native_landing, native_return=native_return,
                native_cache_safe=native_cache_safe, banked_calendar=banked_calendar,
                read_admission_calibration=7,
                calendar_extra=calendar_extra,
                command_extra=command_extra,
                programme_done_extra=calendar_extra,
                residual_completion_tail=command_only_extra,
                go_to_read_pin=6 + calendar_extra,
                go_to_read_capture=6 + calendar_extra + command_only_extra,
                go_to_packet_and_command=7 + command_extra,
                native_padding=native_padding,
                native_padding_terms=dict(hbm_capture_edges=3,hbm_period_ps=1024,stream_period_ps=833,
                    capture_stream_edges=native_capture_stream_edges,reserve_edges=2,completion_edges=2,read_edges=3,
                    native_base=native_base,regional_added_edges=7,cache_allowance_edges=4),
                selected_return_leaf_read_to_return_edges=8,selected_drain_metadata_delay=8,
                historical_attention_reference_bias=1,
                historical_first_reference='rc0 + FIRST_GO + 8; preserve exactly at default0',
                first_reference='legacy reference + native_padding, subject to previous actual tail and x-load constraints',
                go_at='(first_reference - rc0) - 7; never subtract command_extra here',
                actual_command='first_reference + command_extra + programme_word_index',
                actual_read_pin='first_reference - 1 + calendar_extra + programme_word_index',
                actual_last_command='first_reference + word_count - 1 + command_extra',
                final_drain='END = last_actual_command + DRAIN; if anchored to actual programme_done instead, add only residual_completion_tail, never double-charge it',
                next_go='max(previous_go + previous_words + BUSY + calendar_extra + residual_completion_tail, fetch admission constraints)',
                external_xw='retain source-relative x-load slots; schedule each op against previous ACTUAL tail, no overlap with old consumer',
                req_lead=8, probability_pread_lead=3,
                req_pread_rule='unchanged fields and intra-calendar offsets; shift whole command calendar only',
                lockstep='XC must match calendar_extra and command_only_extra of SVG; metadata class rides the same command envelope',
                hardware_flags='physical RTL parameters/defines must match this profile; model arguments alone do not enable hardware',
                claim='model only; existing storage-only attention receipts unchanged')


def model():
    return dict(preferred=context_model(), fallback=context_model('explicit200'),
                class_guard=dict(sites=['post-mrel XC command','assembled SM command'],
                    rule='every A2 word requires aligned context_valid, mode!=3 and mode[2]==descriptor_class',
                    command_envelope_with_explicit_valid=85,
                    added_svg_valid_ff=4, added_xc_class_ff=4, added_xc_valid_ff=4, added_guard_sticky_ff=2,
                    complete_banked_native_source_ff_delta=89,
                    note='existing aligned valid may be reused only after source audit; no new command edge'),
                timing=dict(storage=timing_profile(),
                            native_cache_proven=timing_profile(native_landing=True, native_return=True, native_cache_safe=True),
                            banked_native_proposed=timing_profile(native_landing=True, native_return=True, native_cache_safe=True, banked_calendar=True)),
                gates_before_adoption=['root ABI/model decision', 'same-vehicle alternating dense/attention/dense exact+mutants',
                                      'XW47 core and application context exact+census',
                                      'native frontend/reset/physical closure', 'mixed die writer/descriptor composition and throughput'])


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
