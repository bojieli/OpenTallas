"""ROM-only composition of selected S81 and Laplace's baseline tagged CDC."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from dsrom_s81_selected_composition import ROOT, BASE, FF50_MM2_PER_BIT, build as s81_build

INPUTS = BASE+'combined/'
OUT = 'results/uarch/dsrom_s81_selected_composition_20261003/combined_model.json'


def crossing_accept_ps(write_ps, destination_period_ps, destination_phase_ps):
    """Empty/online FIFO; accepted write -> actual receiving handshake edge.

    Coincident edges read the old Gray pointer. Then sync1, sync2, registered
    empty, and receiving acceptance occur at four strictly subsequent edges.
    Queue blocking/decoder/physical setup are additional, not included here.
    """
    if destination_period_ps <= 0 or write_ps < 0:
        raise ValueError('positive clock period and nonnegative accepted-write time required')
    edge = destination_phase_ps + math.floor((write_ps-destination_phase_ps)/destination_period_ps+1)*destination_period_ps
    if edge <= write_ps: edge += destination_period_ps
    return edge+3*destination_period_ps


def price_serial_crossings(base_us, dependent_roundtrips, clk_ps, hclk_ps, *, already_charged_cdc_us):
    """Only source-identified SERIAL dependencies; never sum all packet costs.

    The enclosing source calendar must supply the dependency count and its
    existing CDC subtotal. Replace that subtotal; preserve all other charges.
    This bounds empty/online transport only, not full-queue/backend latency.
    """
    if (type(dependent_roundtrips) is not int or dependent_roundtrips < 0 or
            min(clk_ps,hclk_ps) <= 0 or already_charged_cdc_us is None or
            not 0 <= already_charged_cdc_us <= base_us):
        raise ValueError('explicit serial dependency/clock/existing CDC price required')
    lower = 3*(clk_ps+hclk_ps)*dependent_roundtrips/1e6
    upper = 4*(clk_ps+hclk_ps)*dependent_roundtrips/1e6
    return dict(transport_lower_us=lower, transport_upper_us=upper,
        combined_empty_FIFO_lower_us=base_us-already_charged_cdc_us+lower,
        combined_empty_FIFO_upper_us=base_us-already_charged_cdc_us+upper,
        queue_ready_refresh_decoder_route_extra_us=None, measured=False, headline_rate=None)


def build(root=ROOT):
    manifest=json.loads((root/(INPUTS+'source_manifest.json')).read_text())
    src={}
    for name,pin in manifest.items():
        data=(root/(INPUTS+name)).read_bytes()
        if hashlib.sha256(data).hexdigest()!=pin['sha256']:raise ValueError('combined source changed: '+name)
        src[name]=data.decode()
    top,cdc,fifo,reset=(src[x] for x in ['ot_qwen_rom_combined_die.sv','ot_qwen_combined_hbm_cdc.sv','ot_async_fifo.sv','ot_reset_sync.sv'])
    required = [(top,'parameter integer NEAR_HBM=0'),(top,'parameter integer REAL_MEM = 1'),
        (top,'ot_qwen_combined_hbm_cdc transport('),(top,'.hclk(hclk)'),
        (top,'parameter integer ENABLE_AR256 = 1'),(top,'reg ideal_forbidden;'),
        (cdc,'NPC=32,TAGW=13,REQ_DEPTH=16,RSP_DEPTH=8'),(cdc,'BW=320,CW=360'),
        (cdc,'for(s=0;s<4;s=s+1)'),(cdc,'for(p=0;p<4*NPC;p=p+1)'),
        (fifo,'rd_empty <= rd_empty_next;'),(fifo,'assign rd_data = mem[rd_bin[ADDR_W-1:0]];'),
        (reset,'ASYNC_STAGES = 2')]
    if any(fragment not in text for text,fragment in required):
        raise ValueError('selected combined baseline source/geometry/clock FIFO semantics changed')
    req_bits, rsp_bits = 4*16*360, 128*8*360
    pointer_bits=4*8*5+128*8*4
    # Per FIFO: 6 online/rendezvous, full+empty2, two reset conditioners4,
    # overflow/underflow2 (declared source allowance; constants may synthesize).
    controls=132*14+256+6
    state=req_bits+rsp_bits+pointer_bits+controls
    declared_unused=256  # room_1/room_2 are never referenced; expose separately.
    return dict(schema='opentallas.ROM.actual-combined-source-composition.v1',
        status='SOURCE_BOUND_MODEL_COSTS_NOT_MEASURED_RATE_OR_PHYSICAL_FIT',
        selected_DS=s81_build(root),
        Qwen_baseline=dict(NEAR_HBM=0, REAL_MEM=1, clk_domain='core and actual KV service',
            hclk_domain='external HBM controllers', core_and_hclk_aliased=False,
            request_FIFO_replicas=4, request_depth=16, response_FIFO_replicas=128,
            response_depth=8, tag_bits=13, payload_padded_bits=320, coded_entry_bits=360,
            request_live_record_bits=299, response_live_record_bits=274,
            request_bytes_per_stack_per_clk=256/8,
            response_bytes_per_stack_per_hclk=32*256/8,
            request_signal_bits_per_stack_including_valid_ready=301,
            response_signal_bits_per_stack_including_valid_ready=32*(274+2),
            payload_state_bits=req_bits+rsp_bits, pointer_and_sync_bits=pointer_bits,
            reset_online_flags_fault_room_state_bits=controls, total_state_bits=state,
            unused_room_declaration_bits_not_charged=declared_unused,
            FF50_reservation_mm2=state*FF50_MM2_PER_BIT,
            source_ideal_memory_forbidden_guard_bits=1,
            baseline_CDC_and_new_ideal_guard_FF50_mm2=(state+1)*FF50_MM2_PER_BIT,
            source_ENABLE_AR256=1, new_collective_gain_credit=0,
            declared_per_rank_replicas=1, TP_rank_replicas=4,
            TP4_FIFO_replicas=4*132, TP4_state_bits=4*state,
            SECDED64_encoders=132*5, SECDED64_decoders=132*5,
            full_decoder_mux_control_area_mm2=None, actual_slot_fit=False,
            corridor_track_capacity=None, contextual_SS60_FF25=False,
            mutable_FIFO_protection_retained=True, ROM_ECC_required=False,
            empty_online_request_dest_edges_to_accept=4,
            empty_online_response_dest_edges_to_accept=4,
            pointer_synchronizer_stages=2, registered_empty_or_full_stage=1,
            return_ACK_is_actual_service_acceptance=True, FIFO_enqueue_is_write_completion=False,
            reverse_free_space_same_edge_reuse=False,
            reset_online_rendezvous_and_queued_ready_extra=None,
            actual_clock_profile=None, actual_serial_dependency_count=None,
            source_event_pricer='crossing_accept_ps; replace an explicitly enrolled existing CDC subtotal using price_serial_crossings; finite queue/ready delays remain additional.',
            near_optional_added_area_or_latency_credit=0, token_price_us=None, headline_rate=None),
        source_manifest=manifest, measured=False, adopted=False,
        double_count_rule='S81 prune-only +2.441445mm2 replaces contraction storage, roots once. Qwen CDC on baseline REAL_MEM independent of optional NEAR_HBM; replace existing crossing charge, never add per-packet delays as a serial token chain.',
        tool_sha256=hashlib.sha256((root/'tools/rom_combined_source_pricing.py').read_bytes()).hexdigest())


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify',action='store_true')
    a=ap.parse_args()
    payload=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    p=ROOT/OUT
    if a.verify:
        if p.read_text()!=payload:raise ValueError('combined price record drift')
    else:p.write_text(payload)
    print('PASS selected ROM source composition; no measured headline credit')
