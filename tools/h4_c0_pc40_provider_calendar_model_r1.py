#!/usr/bin/env python3
"""Finite caller/source composition for existing PC40 bridge, before RTL.

This prices one reserved caller up page; actual workspace authority, route
capacity, CDC and SS/FF remain explicit build blockers. No source measurements
or historical rejected physical results are converted into admission.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/c0_pc40_provider_calendar_20261003'


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def compose():
    for row in json.loads((BASE / 'input_manifest_r1.json').read_text()):
        raw = (ROOT / row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('exact peer source model bytes')
    d = json.loads((BASE / 'inputs/Dewey_PC40_demand.json').read_text())
    p = json.loads((BASE / 'inputs/Popper_connected_r2_model.json').read_text())['model']
    if d['source_PC'] != 40 or d['parent55'] is not None or d['W2_HBM_commands'] != 0:
        raise ValueError('actual direct RF caller')
    live = d['existing_live_RF_homes']
    for sm, slot in ((0, 38), (24, 32)):
        if not any(h['rank'] == 0 and h['SM'] == sm and h['slot'] == slot
                   and h['version'] == 'Qwen.39.L0.d0.gu_post.49' for h in live):
            raise ValueError('actual gate/up source publication')
    if any(h['rank'] == 0 and h['SM'] == 0 and h['slot'] in (17, 18, 19, 20) for h in live):
        raise ValueError('named caller stage/workspace source alias')
    return dict(
        schema='C0_PC40_SOURCE_PROVIDER_CALLER_COMPOSITION_R1', default_enabled=False,
        payload_scope='actual gate first128 archived; up publication/read capture awaits existing joint integration run',
        actual_up_payload_observed=False, actual_NoC_handshake_observed=False,
        actual_RF_ACK_observed=False, constructor_free_source_capture_tests_are_payload_PASS=False,
        source_gate=dict(rank=0, SM=0, RFslot9=38, word_start=0, words=128),
        source_up=dict(rank=0, SM=24, RFslot9=32, word_start=6144, words=128),
        source_publication='Qwen.39.L0.d0.gu_post.49',
        source_dtype='F32', packing='128 little-endian U32 bitcasts per512B',
        caller_policy=dict(up_stage_RFslot9=20, up_stage_rank=0, up_stage_SM=0,
                           workspace_slots=[17,18,19], source_static_disjoint=True,
                           actual_entering_workspace_lease=False,
                           existing_native_VM_dynamic_slot20_disjointness_proved=False,
                           publication_held_until='entire PC40 SILU_GATE consumer',
                           caller_up20_held_until='final gate*inverse*up and validated reverse',
                           no_release_at_FMAX_or_FMIN=True),
        source_delivery=dict(gate_existing_bridge_read_already_paid=True,
                             added_SM24_RF_read_commands=1, RF_read_payload_bytes=512,
                             remote_up_payload_bits=4096, remote_up_payload_pages=1,
                             caller_SM0_RF20_write_commands=1, RF20_write_payload_bytes=512,
                             RF20_mirrored_write_bytes=1024, common_ACKs=1,
                             held_vectors=1, additional_RF_macros=0,
                             reserved_existing_RF_logical_bytes=512,
                             reserved_existing_RF_physical_bytes=1024,
                             final_SILU_source_read_pair_bytes=1024,
                             final_SILU_read_pair_scope='gate38/up20, charged at full caller, not this FMAX/FMIN bridge'),
        cuts=dict(up_data_bits=4096, RF20_write_bits=4096, mirrored_write_sink_bits=8192,
                  NoC_physical_link_bits=None, route_track_capacity=None,
                  minimum_payload_flits_expression='ceil(4096 / actual_NoC_link_bits)',
                  zero_delay_assumed=False, PG_and_control_tracks=None),
        replicas=dict(selected_caller=1, inventory_SMs=32,
                      simultaneous_remote_up_transfers_admitted=1,
                      RF20_reservation_bytes_at32SM=32*1024,
                      replication_does_not_imply32_independent_NoC_channels=True),
        once_only=dict(bridge_edges=p['cycles_conditional'],
                       bridge_ns=p['latency_ns_conditional'],
                       gateRF38_read='already included in Popper r2',
                       up_read_stage_ACK='additional caller prerequisite',
                       replaced_subtree=p['replaced_subtree'],
                       old_r9_RF_events='replace selected subtree once; never add its60 edges again',
                       PC39_all_SM_producer_writes='existing source debit, never recharge'),
        conditional_latency=dict(provisional_SM24_read_edges=3,
                                 provisional_RF20_write_visible_edges=2,
                                 added_fixed_stream_edges=5,
                                 streaming_GHz=1.2, serial_GHz=0.9,
                                 added_fixed_ns=5/1.2,
                                 expression='existing_PC39_ready + SM24_RF_read + finite_NoC/CDC + RF20_write/commonACK + existing_r2_117_edges; full remaining exp/reciprocal/SILU separately',
                                 complete_caller_ns=None, whole_token_ns=None,
                                 finite_service_upper_ns=None, loaded_SS_FF=False,
                                 setup_uncertainty_ps=60, hold_uncertainty_ps=25),
        area=dict(existing_RF20_reservation_not_new_macro_area=True,
                  bridge32SM_mm2_ASSUMED=p['full32SM_area_mm2_ASSUMED'],
                  new_caller_controller_and_link_cell_mm2=None,
                  collector_clock_reset_PG_slot_price=None,
                  complete_composed_area_mm2=None),
        owner55_adapter_created=False, owner55_adapter_owner='Popper',
        source_provider_owner='Ampere', calendar_owner='Dewey', fullsystem_owner='Claude',
        build_admission=False, physical_admission=False,
        blockers=['actual PC39 up page and ordered PC40 read receipt from existing integration run',
                  'source-owned entering lease including RF20 versus native VM dynamic workspace',
                  'Popper issuer binding and actual commonACK/visibility/consumer/reverse receipt',
                  'actual finite NoC link/route/cut capacity and CDC service upper bound',
                  'caller control protection, clock/reset/PG and whole latency/area composition',
                  'SS setup/FF hold in loaded context under unchanged uncertainty'])


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); args.out.write_bytes(canonical(compose()))


if __name__ == '__main__': main()
