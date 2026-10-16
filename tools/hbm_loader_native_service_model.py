#!/usr/bin/env python3
"""Finite endpoint sizing before RTL. No routing or production admission credit."""
import json
import math


def dispatcher_model(pc_x, *, landing_x, landing_y, station_y=50.0,
                     max_wire_span_um=100.0, channel_capacity_tracks=None):
    """Size one reserved request/reply walk from an actual selected landing.

    Coordinates are mandatory caller inputs from the selected die port inventory.
    No historical landing or generic interface budget is silently substituted.
    """
    if len(pc_x) != 32 or len(set(pc_x)) != 32:
        raise ValueError('actual 32 distinct PC station coordinates required')
    if max_wire_span_um <= 0:
        raise ValueError('positive physical relay span required')
    order = sorted(range(32), key=lambda p: pc_x[p])
    root_pc = min(order, key=lambda p: abs(pc_x[p]-landing_x))
    root_index = order.index(root_pc)
    ingress = math.ceil((abs(pc_x[root_pc]-landing_x)
                         + abs(station_y-landing_y))/max_wire_span_um)
    edges = [math.ceil((pc_x[b]-pc_x[a])/max_wire_span_um)
             for a, b in zip(order, order[1:])]
    hops = {}
    for i, p in enumerate(order):
        lo, hi = sorted((root_index, i))
        hops[str(p)] = ingress + sum(edges[lo:hi])
    stages = ingress + sum(edges)
    return dict(scope='registered native read transport model; not physical admission',
        landing_um=[landing_x, landing_y], station_y_um=station_y,
        maximum_wire_span_um=max_wire_span_um, root_PC=root_pc,
        request_bits_including_valid=52, reply_bits_including_valid=282,
        request_slots=1, reply_slots_reserved=1, MACs_per_cycle=0,
        memory_bytes_per_transaction=32, normal_K_added_cycles=0,
        physical_relay_stages=stages, relay_payload_FF=334*stages,
        native_request_hops_by_PC=hops,
        native_transport_round_trip_cycles_by_PC={p:2*h for p,h in hops.items()},
        tracks_required_before_existing_occupancy=334,
        channel_capacity_tracks=channel_capacity_tracks,
        routing_admitted=False, slot_fit='requires existing service cell/macro occupancy',
        protocol='Root reserves reply capacity before accepting; one-shot registered packet stops at selected PC held descriptor; lease admission drains normal debt; return has reserved capacity, no long ready chain',
        writes='Independent actual source2 WB transport and physical completion ledger; this read corridor gives no write routing credit',
        token_latency_credit=False, adopted=False)

def native_burst_model():
    """Bounded native burst lease sized before RTL; physical admission withheld."""
    return {'scope': 'native service burst lease before RTL; no physical/token claim',
     'default_enable_native_burst': 0,
     'sectors_min': 1,
     'sectors_max': 8,
     'MACs_per_cycle': 0,
     'compute_intensity': 0,
     'bytes_per_response_cycle': 32,
     'bytes_per_burst_max': 256,
     'request_bits': 51,
     'response_bits': 277,
     'replicas_per_stack': 32,
     'stacks_per_die': 4,
     'mux_demux': 'existing one-active-PC stack response mux; one local length check per PC',
     'register_bits_per_PC': 329,
     'incremental_register_bits_per_PC': 13,
     'normal_added_cycles': 0,
     'latency': {'request_capture': 1,
                 'first_response_capture': 1,
                 'one_burst_minimum_cycles': 'sectors + 3 without downstream PHY wait',
                 'lease_released': 'final response consumer acceptance',
                 'system_composition': '256 sectors at length8: 32 command admissions plus same 256 '
                                       'data cycles; downstream wait and dispatcher must be composed'},
     'elastic_response_depth': 1,
     'backpressure': 'PHY advances only when register empty or consumer accepts current beat',
     'identity': 'native tag and sequential beat 0..length-1 checked before PHY acceptance',
     'routing': {'request_incremental_tracks': 4,
                 'response_incremental_tracks': 0,
                 'channel_capacity': None,
                 'admitted': False},
     'area': {'incremental_FF_per_die': 1664,
              'slot_fit': 'actual lease element measurement required',
              'incremental_FF_per_die_including_boundary': 1680},
     'token_credit': False,
     'physical_admitted': False,
     'caller_address_contract': 'All requested K sectors belong to selected PC; global address '
                                'translator splits bursts at every PC boundary (mapped consecutive '
                                'groups may limit length to4).',
     'stack_boundary_length_bits': 4}

def model():
    return dict(scope='native loader sector endpoint; explicit external address translation and real service completion required',
      native_burst=native_burst_model(),
      parameters=dict(default_enable=0,native_address_bits=32,native_address_parameter_min=32,sector_bits=30,pc_bits=5,tag_bits=16,data_bits=256,stack_instances=4),
      request_bits=291,response_bits=1+5+16+4+256,
      state_bits=3,saved_request_bits=1+5+30+16+256,saved_reply_bits=256,
      flops_per_stack=3+1+5+30+16+256+256+1,
      memory_ports=dict(native=1,service=1),outstanding_per_stack=1,
      bytes_per_service_cycle=32,MACs_per_cycle=0,compute_intensity=0,
      boundaries=dict(native_request_bits=338,native_response_bits=274,service_write_request_bits=291,service_read_request_bits=51,service_response_bits=282),
      latency=dict(request_capture_cycles=1,reply_capture_cycles=1,minimum_endpoint_cycles_per_sector=3,service_cycles='measured downstream; no invented bound',token_path_added_cycles=0,token_path_condition='deployment only; runtime load conflict remains explicitly unqualified'),
      area=dict(flop_count_estimate=568,slot_fit='unqualified: service physical owner must admit'),
      routing=dict(tracks='port bits × actual routing layers and occupancy required',channel_capacity=None,qualified=False),
      mux_demux=dict(replicas=4,request_select='existing physical per-stack arbiter',response_select='single saved PC and tag; we identity'),
      invalid='misaligned/unmapped address or partial write strobe faults before acceptance; malformed/unsolicited service completion faults without loader success',
      address_mapping='external owner supplies actual byte-address→stack/PC/sector translator; endpoint never truncates native address',
      write_visibility='service response for write must originate physical k_wr_done after accepted write; request acceptance is never completion',
      production_read_lease=dict(physical_PCs=32,normal_read_beat_capacity=64,normal_write_capacity=8,read_debt_bits=7,write_debt_bits=4,native_lease_bits=2,native_address_bits=30,native_tag_bits=16,normal_request_added_cycles=0,native_request_capture_cycles=1,native_reply_capture_cycles=1,PC_write_collision="native admission waits externally proven pending WB drain plus accepted write debt0; native lease blocks normal K issue on its PC",native_response_bits=256+16+4+1,per_PC_flops=7+4+2+1+30+16+256,physical_status="requires slot placement and actual wire channel admission"),
      read_lease=dict(outstanding_per_PC=1,beat_mask_bits=16,saved_normal_tag_bits=17,native_tag_bits=16,stages=1,normal_path_added_cycles=0,normal_priority="normal valid or existing lease blocks native admission",same_PC_write_arbitration="must compose with physical WB arbiter"),
      adoption=False,physical_admitted=False)
if __name__=='__main__': print(json.dumps(model(),indent=2))
