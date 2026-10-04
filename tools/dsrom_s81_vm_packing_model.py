"""Prospective finite W11 field-write gear/owner composition; no HDL admission."""
from pathlib import Path
import json, math, hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_s81_native_vm_ports_20261004'

def coded(n):
    # Explicit candidate: independent extended-Hamming(72,64) words; padding
    # checked. This is a storage debit, not a proven decoder/cell implementation.
    return 72*math.ceil(n/64)

def calendar(offset):
    # Units 1/3 ns: fast period3; slow period4. Four fast vectors/block.
    # Last capture publishes only after four slow periods. The next slow edge
    # launches 2,1,1 frames. Slot release reaches fast owner after two fast
    # periods. No decoder completion or macro visibility inferred here.
    blocks=[]
    for k in range(32):
        begin=12*k;close=begin+9
        first=offset+4*(math.floor((close+16-offset)/4)+1)
        launches=[first,first+4,first+8]
        release=3*(math.floor((launches[-1]+6)/3)+1)
        blocks.append(dict(block=k,begin=begin,close=close,launch_edges=launches,
                           frames_per_launch=[2,1,1],captured_release=release))
    peak=max(sum(b['begin']<=t<b['captured_release'] for b in blocks) for t in range(400))
    return dict(slow_offset=offset,peak_live_superframes=peak,blocks=blocks)

def build():
    prior=json.loads((BASE/'r2/model.json').read_text())
    calendars=[calendar(i) for i in range(4)]
    depth=max(x['peak_live_superframes'] for x in calendars)
    packet=136;roots=128;frame_raw=4*roots*packet
    launch_delays=[(b['launch_edges'][[0,0,1,2][f]]-(b['begin']+3*f))/3 for c in calendars for b in c['blocks'] for f in range(4)]
    frame_coded=4*roots*coded(packet)
    # Two explicit 1024-lane E routes; one32-bit lane already charged by W11.
    route_raw=(2*packet-32)*1024*16
    route_coded=(2*coded(packet)-32)*1024*16
    mux=(2*packet-32)*1024*10
    owner=256*4*coded(65)
    reservation=256*coded(17)
    receipt=256*coded(74)
    # Commit aggregation by current root/phase; up to16 counts/root/slow edge.
    count=roots*coded(5)
    # Captured full phase owner shared by each registered count vector.
    ack=(count+coded(57))*5
    # Explicit bounded ring pointers+valid+quarantine; no payload hidden here.
    ring_control=coded(2*math.ceil(math.log2(depth))+depth+1)
    ff=depth*frame_coded+route_coded+owner+reservation+receipt+ack+ring_control
    comb_area=mux*.0878/1e6
    ff_area=ff*.2952/1e6
    return dict(schema='dsrom.s81.W11.packing_owner.prospective.v1',
      predecessor_sha256=hashlib.sha256((BASE/'r2/model.json').read_bytes()).hexdigest(),
      generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      clocks=dict(fast_GHz=1.2,slow_GHz=.9,setup_SS_ps=60,hold_FF_ps=25),
      finite_capture=dict(raw_packet_bits=packet,codeword_bits=coded(packet),frames_per_superframe=4,
        superframe_raw_bits=frame_raw,superframe_coded_bits=frame_coded,
        ring_depth_derived=depth,calendars=calendars,
        proof_scope='Ideal related-clock edge calendar only;4slow publication +2fast return explicitly selected. Actual reset skew/synchronizers/loaded paths require ownership review.',
        no_ready=True,preGO_reserve_ring_and_banks_and_route=True),
      latency=dict(packet_capture_to_slow_launch_min_ns=min(launch_delays),
        packet_capture_to_slow_launch_max_ns=max(launch_delays),
        coded_check_completion_not_zero_ns=None,
        empty_queue_tail_upper_excluding_codec_ns=max(launch_delays)+18/.9+5/1.2,
        depth4_tail_upper_excluding_codec_ns=max(launch_delays)+21/.9+5/1.2,
        full_phase_consumer_deadline_ns=None),
      ports=dict(slow_max_vector_frames_per_edge=2,route_instances=2,reused_existing_instances=1,
        aggregate_slow_packet_bits=2*roots*packet,group_max_records_per_edge=4,
        bank_K=4,bank_WQD=4,macro_write_rows_per_bank_edge=1,read_replicas=6,
        all_six_write_enables_required=True),
      coded_state=dict(frame_ring=depth*frame_coded,route_delta=route_coded,
        shadow_bank_owner=owner,bank_reservation=reservation,registered_commit_receipt=receipt,
        count_return_pipeline=ack,ring_control=ring_control,total_added_FF_floor=ff,
        candidate_codec='72/64 SECDED with padding checks; mutable data and ownership, not removed ROM ECC'),
      loaded_control=dict(bank_row_comparisons_per_edge=256*4*4,
        new_target_priority_depth_min=2,row_equal_bits=8,
        field_mask_bits_per_row=8,shared_context_fanout=1024,
        count_return_bits_per_edge=roots*5+57,
        scalar_ACK_pulse_insufficient=True,clock_reset_load_area_included=False,
        codec_decode_encode_gate_area_included=False,codec_loaded_latency_edges=None,
        addressed_seal_and_expected_slot_compare_not_priced=True,
        prospective_codec_latency_sensitivity_edges=[2,4,8],
        added_codec_roundtrip_ns_sensitivity=[2*n/.9 for n in (2,4,8)]),
      cost=dict(mux_bit_cells_floor=mux,unprotected_route_delta_FF=route_raw,
        added_cell_mm2_floor=ff_area+comb_area,added_placement_mm2_floor_at50pct=2*(ff_area+comb_area),
        excludes=['codec logic/check/scrub repair','scatter steering','bank merge/priority/control','CDC packing/metadata decode logic','loaded clock/reset buffers','absolute consumer deadline and GO wait'],
        original_r2_floor_superseded_not_summed=True,SRAM_count_change=0),
      admission=dict(storage_reservation_only_is_not_port_admission=True,
        actual_macro_owner_take_separate_from_macro_visible=True,
        completion='All bank word debts matched to old held context57+row8+mask8; count captured across reverse CDC, zero source/ring/route/bank/reverse debt before retire.',
        warm_reset='Quarantine retains every accepted debt and frame; only coordinated all-copy cold fence clears.',
        gate='Freeze atomic bank and gear/route seats BEFORE source GO; competing writer arbitration is mandatory.',
        decoder_fault='No unchecked bank write; retain exact packet, reject corrupt identity/padding and quarantine. Corrector queue/service not priced or enrolled.',
        codec_area_and_loaded_timing_missing=True,physical_provider_clock_binding_missing=True,
        physical_or_RTL_admission=False),
      proposed_source_ownership=dict(Nash='disjoint admission/bank-owner/positive receipt control after joint approval',
        Arch='actual source GO, native VM ports and context completion binding',
        Maxwell='physical slot, loaded codec/control/clock and two-route budget',
        CDC_route_owner='Unassigned; explicit owner agreement required before RTL'),
      RTL_written=False,job_launched=False)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    x=build();a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'depth':x['finite_capture']['ring_depth_derived'],'coded':x['coded_state'],'cost':x['cost']},indent=2))
