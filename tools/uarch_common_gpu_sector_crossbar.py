#!/usr/bin/env python3
"""Opt-in additive finite common-GPU transport model; never alters product rates.

All source inputs are read from immutable commits. Gate counts are analytical
2-input equivalents, not synthesized cells. Ready/visibility bounds are inputs,
never inferred from MAXSKIP. Run --out FILE (exclusive creation) to retain verdicts.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '4535be1001d69bc43669e0fdf0401896be4034a6'
DIR = 'results/uarch/qwen_hbm_connected_20261001/'
INPUTS = {
    'macro': ('8ddd7c50dcc1e3c24313cd87a730d0d98d30ec8b', DIR+'real_macro_ports_before_RTL.json'),
    'ports_v1': ('86c7a2ea58e9d48ab79ea95277e365b9ce1f031c', DIR+'common_GPU_WRACK_port_contract.json'),
    'ports': ('07a07ec5d5c48a6498ac8bed6f6b6abc30937858', DIR+'common_GPU_WRACK_port_contract_r2.json'),
    'ingress': (BASE, DIR+'HBM_ingress_before_RTL_r2.json'),
    'unified_model': (BASE, 'tools/uarch_model.py'),
    'publication': ('66aa67ed1', DIR+'publication_model_negative_gate.json'),
}

def sources():
    records, pins = {}, {}
    for name, (rev, path) in INPUTS.items():
        data = subprocess.check_output(['git', 'show', rev+':'+path], cwd=ROOT)
        pins[name] = dict(revision=rev, path=path, sha256=hashlib.sha256(data).hexdigest())
        if name != 'unified_model':
            records[name] = json.loads(data)
        else:
            for token in (b'DFF_UM2 = 0.2916', b'GPU_LOGIC_UTIL = 0.5', b'WIRE_REACH_SS_UM = 504.0'):
                assert token in data
    pins['generator'] = dict(path='tools/uarch_common_gpu_sector_crossbar.py',
                            sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return records, pins


def calendar(n=128, sectors=2, stall_until=0, stop=10000):
    """One bank, FIFO PC heads, age16 then RR, two reserved landing slots.

    Launch t writes at t+4 when ready. Credit returned at t+5; immutable
    reservations hold through stalls. PC heads age only on competing grants.
    Saturated aged heads use RR; blocked cycles cannot buy fairness credit.
    """
    remaining = [sectors]*n
    ages = [0]*n
    pointer = 0
    flights, releases, events = [], [], []
    available = 2
    max_reserved = 0
    for t in range(stop):
        returned = sum(x == t for x in releases)
        available += returned
        releases = [x for x in releases if x != t]
        # One physical macro write port; overdue flights preserve order.
        if flights and flights[0][0] <= t and t >= stall_until:
            _, pc, issued = flights.pop(0)
            releases.append(t+1)
            events.append(dict(cycle=t, event='macro_write', pc=pc, launch=issued))
        if available and any(remaining):
            eligible = [i for i in range(n) if remaining[i]]
            aged = [i for i in eligible if ages[i] >= 16]
            group = aged or eligible
            winner = min(group, key=lambda i: (i-pointer) % n)
            available -= 1
            remaining[winner] -= 1
            flights.append((t+4, winner, t))
            pointer = (winner+1) % n
            for i in eligible:
                ages[i] = 0 if i == winner else min(16, ages[i]+1)
            events.append(dict(cycle=t, event='reserve_launch', pc=winner))
        max_reserved = max(max_reserved, 2-available)
        assert 0 <= available <= 2
        assert len(flights)+len(releases) == 2-available
        if not any(remaining) and not flights and not releases:
            break
    writes = [e for e in events if e['event'] == 'macro_write']
    assert len({e['cycle'] for e in writes}) == len(writes)
    done = len(writes) == n*sectors
    return dict(done=done, sectors_written=len(writes), max_reserved=max_reserved,
                last_write_cycle=writes[-1]['cycle'] if writes else None,
                final_credit_cycle=t if done else None,
                first_events=events[:14], last_events=events[-6:])


def compose():
    r, pins = sources()
    macro, ingress = r['macro'], r['ingress']
    assert macro['area']['required_port_banked_macros'] == 400
    assert r['ports']['geometry']['write_transactions_per_controller'] == 4
    assert ingress['backend']['MAXSKIP'] == 16
    stacks, pcs, clients, banks = 4, 32, 36, 4
    inputs, outputs = stacks*pcs, clients*banks
    width, cwidth, depth = 312, 320, 2
    # Fully connected four-stack fabric: no omitted clients or sector banks.
    mux = {
        'local_PC32_to_each_client_sector': outputs*stacks*(pcs-1)*width,
        'four_stack_merge': outputs*(stacks-1)*width,
        'PC_two_entry_head_select': inputs*width,
        'destination_two_entry_head_select': outputs*cwidth,
        'client_patch_to_four_controllers': stacks*(clients-1)*384,
        'ACK_controller_to_every_client': clients*(stacks-1)*80,
        'four_transaction_slot_select': stacks*3*512,
        'four_ACK_slot_select': stacks*3*80,
    }
    registers = {
        'PC_landing_payload': inputs*depth*width,
        'PC_landing_control': inputs*6, # valid2, pointers2, occupancy2
        'client_sector_landing_payload': outputs*depth*cwidth,
        'client_sector_landing_control': outputs*6,
        'source_capture_pipeline': inputs*(width+1),
        'local_stack_mux_pipeline': outputs*stacks*(width+1),
        'global_mux_pipeline': outputs*(width+1),
        'destination_reservation_and_registered_credit': outputs*(2+2+1),
        'bank_RR_pointer': outputs*7,
        'PC_saturating_skip_age': inputs*5,
        'pipelined_local_select': outputs*stacks*(5+1),
        'pipelined_global_select': outputs*(2+1),
        'write_transactions': stacks*4*512,
        'ACK_reserved_slots': stacks*4*80,
        'controller_request_CDC': stacks*4*384,
        'controller_ACK_CDC': stacks*4*80,
        'consumer_completion_return_CDC': stacks*4*16,
        'CDC_pointer_synchronizers': stacks*3*(6+6+12),
        'CDC_free_running_phase': stacks*2,
    }
    gates = {
        'destination_decode_and_eligibility': inputs*outputs*(8+3),
        'RR_pointer_compare': outputs*inputs*7,
        'two_priority_prefix_passes': outputs*inputs*4,
        'aged_group_selection': outputs*inputs*2,
        'age_saturating_increment': inputs*5*5,
        'landing_FIFO_control': (inputs+outputs)*64,
        'reservation_control': outputs*64,
        'ACK_and_write_credit_control': stacks*4*128,
        'all_shared_requests_sector_lock_compare': (inputs+clients)*stacks*4*34,
    }
    # 0.2um2 per mux and per 2-input gate are explicit estimates, not closure.
    reg_bits, mux_bits, gate_eq = sum(registers.values()), sum(mux.values()), sum(gates.values())
    addition = (reg_bits*.2916+(mux_bits+gate_eq)*.2)/.5/1e6
    prior_ceiling = macro['finite_services']['credit_limited_read_service_Bpc']
    crossbar_ceiling = outputs*32*depth/5
    service = min(prior_ceiling, crossbar_ceiling, stacks*750)
    candidate_bits = outputs*(4*(cwidth+1+1+1+3+7)+3+3+1)
    candidate_gates = outputs*4*64
    candidate_mux = outputs*4*cwidth
    candidate_area = (candidate_bits*.2916+(candidate_gates+candidate_mux)*.2)/.5/1e6
    pub = r['publication']
    assert pub['candidate_storage']['total_bits'] == 32*(256*35+42+36*74)
    pub_mux = dict(row_tuple_lookup=32*255*35, reader_ticket_lookup=32*35*74,
                   one_client_request_per_bank=32*35*74)
    pub_gates = dict(row_producer_match_and_committed=32*256*(2*34+2),
                     reader_ticket_epoch_identity_match=32*36*(2*72+2),
                     descriptor_epoch_match=32*(2*16-1),
                     bitmap_and_reader_update_control=32*(256*8+36*16+128))
    pub_area = (sum(pub_mux.values())+sum(pub_gates.values()))*.2/.5/1e6
    routing = {}
    bundles = {
        'one_stack_PC_to_local_mux': pcs*(width+1)+outputs*(5+1),
        'all_stack_local_mux_to_merge': outputs*stacks*(width+1),
        'merge_to_all_client_sector_landing': outputs*(cwidth+1),
        'all_client_full_line_reads': clients*(1024+64+2),
        'client_patch_inputs': clients*(384+2),
        'controller_ACK_to_client_branches': clients*stacks*(80+2),
        'all_bank_request_grant_reservation_controls': inputs*outputs*2,
    }
    for name, tracks in bundles.items():
        routing[name] = dict(signal_tracks=tracks, channel_tracks=3200,
            corridor_width_um=64, assumed_signal_layers=4, assumed_pitch_um=.08,
            parallel_corridors_required=math.ceil(tracks/3200), single_corridor_fit=tracks <= 3200)
    normal, stalled, blocked = calendar(), calendar(stall_until=100), calendar(stop=256, stall_until=10000)
    assert normal['done'] and stalled['done'] and not blocked['done']
    assert normal['last_write_cycle'] == 640 and normal['final_credit_cycle'] == 641
    assert blocked['max_reserved'] == 2 and blocked['sectors_written'] == 0
    return dict(schema='opentallas.common-gpu-sector-crossbar-model.v1',
        status='MODEL_ONLY_FULL_ROUTING_AND_CONSUMER_COMPOSITION_BLOCKED',
        opt_in=True, default_enabled=False, adoption=False, full_token=False,
        engine_RTL_build_ready=False, physical_build_ready=False, headline=False,
        source_sha256=pins,
        geometry=dict(stacks=stacks, PCs_per_stack=pcs, Qwen_clients=clients,
            sector_banks_per_client=banks, arbiters=outputs, candidates_per_arbiter=inputs,
            PC_landing_entries=2, PC_landing_entry_bits=width,
            client_sector_landing_entries=2, client_sector_entry_bits=cwidth,
            macro_writes_per_bank_cycle=1, write_credits_per_controller=4,
            ACK_reserved_entries_per_controller=4, transaction_entry_bits=512, ACK_entry_bits=80,
            transaction_layout='384 request/state bits including data256 mask32 AW34 tag16 client6 epoch16; two64bit scheduled/visible timestamps',
            PC_layout='data256+AW34+tag16+client6=312; no publication proof in echoed tag',
            client_layout='data256+tag16+client6+epoch16+row9+sector2+control15=320',
            DeepSeek_scope='Only reusable service topology; actual client population and global publication map require owner composition'),
        compute=dict(MACs_per_cycle=0, bytes_per_sector=32,
            communication_only=True, intensity_MACs_per_byte=0),
        structure=dict(mux_2to1_bit_equivalents=mux, register_bits=registers,
            control_2input_gate_equivalents=gates,
            arbitration='One destination per PC head; per-bank saturated age16 priority, RR within eligible aged group. Reservation precedes source pop; no second selection of captured head.',
            reservation='Two credits include all in-flight and occupied destination slots. Macro write returns credit through a register one cycle later; backpressure cannot revoke a reserved slot.',
            pipeline='t reserve/capture; t+1 local32 mux register; t+2 stack4 mux register; t+3 landing; t+4 actual macro write; t+5 credit usable',
            stage_timing='Analytical four-cycle route assumes all wire segments <=504um and local mux timing closes; neither is physically proven',
            fanout=dict(PC_payload_targets=outputs, local_stack_outputs=stacks*outputs,
                per_bank_request_candidates=inputs, controller_ACK_client_targets=clients,
                no_broadcast_is_free=True)),
        area=dict(register_bits=reg_bits, mux_bit_equivalents=mux_bits, control_gate_equivalents=gate_eq,
            DFF_um2=.2916, assumed_mux_or_gate_um2=.2, logic_utilization=.5,
            additive_footprint_mm2=addition,
            prior_storage_corrected_die_mm2=macro['area']['composed_storage_corrected_die_mm2'],
            composed_die_estimate_mm2=macro['area']['composed_storage_corrected_die_mm2']+addition,
            SM_slot_fit=False, legal_floorplan=False,
            composition_policy='Conservatively add all listed costs; no subtraction from old aggregate mux/CDC allowance. Owner must prove exact resource overlap before any deduplication.',
            not_priced='Data-dependent timing, buffer cell sizing, clock tree, placement-specific additional wire registers, publication storage/lookup addon, full backing-address publication mapping, RF/vector/TP consumers'),
        publication=dict(owner='common controller publication model', admission=False,
            source='66aa67ed1:'+DIR+'publication_model_negative_gate.json',
            banks=32, rows_per_bank=256, readers_per_bank=36, descriptor_bits_per_bank=42,
            storage_bits_owner_record=373312, storage_footprint_mm2_owner_record=pub['candidate_storage']['register_footprint_mm2'],
            storage_not_recharged_here=True, mux_bit_equivalents=pub_mux, control_gate_equivalents=pub_gates,
            additional_lookup_control_footprint_mm2=pub_area,
            lookup_ports_per_bank_cycle=1, aggregate_lookup_ports_per_cycle=32,
            latency='registeredrequest decode1 + parallel row/reader equality1 + tuple/ticket mux2 + publication/reader update1 =5fast cycles before read admission; producer drain and consumer completion fences additional',
            matched_row_mux_levels=8, matched_reader_mux_levels=6,
            worst_case_client_RR_grants=36, bounded_lookup_wait_cycles_if_ready=36*5,
            serialized_port='One lookup transaction/bank per5cycles in this conservative model; 32banks/5=6.4transactions/cycle. Pipelining needs separately priced hazard/forwarding and reservation qualification.',
            tracks_per_bank=256*35+36*74+42+74+2,
            parallel_64um_corridors_per_bank=math.ceil((256*35+36*74+42+74+2)/3200),
            lookup_full_fanout='Request row/id to256tuple comparators, reader request to36ticket comparators perbank; all32banks instantiated',
            separate_addon=True, no_full_consumer_or_global_publication_admission=True,
            requirement='Owner composes finite windows with instructions and matching controller writes; echoed312bit route metadata cannot prove publication'),
        complete_known_addons=dict(frozen_die_mm2=macro['area']['composed_storage_corrected_die_mm2']+addition+pub_area+pub['candidate_storage']['register_footprint_mm2'],
            independent_route_candidate_die_mm2=macro['area']['composed_storage_corrected_die_mm2']+addition+candidate_area+pub_area+pub['candidate_storage']['register_footprint_mm2'],
            floorplan_PASS=False, timing_PASS=False),
        routing=routing,
        calendar=dict(no_stall_all_128_PC_heads_two_sectors_one_bank=normal,
            macro_ready_held_until_cycle100=stalled, indefinitely_blocked_finite_prefix=blocked,
            conditional_bound='Continuously eligible head: <=16+128 competing grants. If macro-ready gap <=H cycles, conservative grant gap <=H+5; first write <=144*(H+5)+4 fast cycles after head eligibility. Earlier PC FIFO heads each add the same bound. Bank/refresh/return latency and producer waits additional.',
            MAXSKIP16_is_not_cycle_bound=True, arbitrary_backpressure_bound=None,
            phase='Fast phase advances every cycle; serial opportunities floor(3*(t+1)/4)-floor(3*t/4), independent of valid. Each 2-flop pointer crossing allowance4 fast cycles, roundtrip8 plus <=2fast phase alignment; real CDC qualification pending.',
            serial_stall='Add actual serial consumer stalls converted by ceil(4*S/3); no finite ACK-credit rate if readiness unbounded'),
        service=dict(stack_shared_byte_budget_Bpc=750, controller_command_slots_per_cycle=1,
            mixed_command_constraint='read_bytes/1024+write_bytes/32<=1 per stack; every read/write/RMW sector also consumes the same750B/cycle bucket',
            token_bucket_capacity_B=1024, token_initial_B=0,
            finite_bucket_rule='min(1024, previous+750), subtract actual sectors; finite accumulated burst is not sustained bandwidth',
            read_ingress_upper_Bpc=4096, prior_credit_upper_Bpc=prior_ceiling,
            destination_two_credit_ceiling_Bpc=crossbar_ceiling,
            composed_upper_Bpc=service,
            single_conflicted_bank_upper_Bpc=32*2/5,
            ACK_credit_bound='Per controller writes/cycle <=min(1,750/32,4/Lack). Lack starts at reservation and includes scheduler/CWL/burst/visibility, forwardCDC, ready stall and completionCDC. RMW charges one read plus one write and holds same lock/credit. Infinite Lack gives zero guaranteed rate.',
            budget_not_double_charged='Charge backend DRAM sectors once; crossbar routing moves those bytes and constrains service without a second DRAM debit.',
            full_Qwen_transfer_only_lower_cycles=math.ceil(ingress['performance']['current_Qwen_token_HBM_bytes_per_die']/service),
            prior_transfer_only_lower_cycles=ingress['performance']['selected_transfer_lower_bound_cycles'],
            token_rate=None, speed_credit=0,
            latency_overlap='Owner replaces old3 gather cycles with4 route+1 registered credit turnaround; do not add to entire87 boundary estimate without a matched old-stage map. Conflict stalls are additional actual service cycles.'),
        separately_priced_candidate=dict(status='MODEL_CANDIDATE_NOT_ADOPTED',
            frozen_landing_entries_per_bank=2, independently_credited_route_entries_per_bank=4,
            route_entry_bits=cwidth, aggregate_capacity_per_bank=6,
            extra_register_bits=candidate_bits, extra_gate_equivalents=candidate_gates,
            extra_mux_bit_equivalents=candidate_mux, extra_footprint_mm2=candidate_area,
            candidate_die_estimate_mm2=macro['area']['composed_storage_corrected_die_mm2']+addition+candidate_area,
            stage_layout='Each of4 bank-local elastic stages has320payload+valid+reserved+registeredreturnedcredit+3occupancy+7source-ticket bits; bank aggregate adds3occupancy+3returnedcount+1valid',
            no_overlap_credit='Conservatively additional to shared local/global capture pipeline registers; no free reuse, no implicit capacity growth in frozen variant',
            pipeline='Four elastic stages and two landing slots; reserve only an actually available stage, retain packet on ready stall; stall wave propagates, global outstanding never exceeds6/bank',
            no_stall_II_cycles=1, reservation_to_macro_min_cycles=4, registered_credit_return_cycles=1,
            no_stall_all_bank_ceiling_Bpc=outputs*32,
            composed_no_stall_upper_Bpc=min(prior_ceiling,outputs*32,stacks*750),
            arbitration_and_full_fanout='Same full128PC->144bank mux/arbiters as frozen variant; no omitted client; extra144x4 elastic ready/valid/credit branches',
            extra_route_payload_track_segments=outputs*4*(cwidth+1),
            extra_handshake_credit_track_segments=outputs*4*5,
            executable_stall_calendar_owner='Ram01a0f697-9c82-7572-8900-dd7b15d59ebf',
            calendar_and_full_token_PASS=False, adoption=False, engine_RTL_build_ready=False),
        wire_depth_sensitivity=[dict(route_cycles=L, credit_turnaround_cycles=L+1,
            bank_Bpc=64/(L+1), die_all_banks_Bpc=outputs*64/(L+1),
            extra_pipeline_register_bits=outputs*(cwidth+1)*(L-4)) for L in (4,8,16,32)],
        gate_summary=dict(calendar_invariants_PASS=True, source_bound=True,
            routing_single_corridor_PASS=False, full_floorplan_PASS=False,
            controller_publication_and_consumer_calendars_PASS=False,
            contextual_SS_FF_PASS=False, exact_RTL_PASS=False))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = compose()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(area=result['area'], service=result['service']), indent=2))
