#!/usr/bin/env python3
"""Fail-closed physical address/dispatch contract and exact finite-hop calendar.

Contract validation and analytical event accounting only; no RTL/product PASS.
"""
import argparse
from collections import deque
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HZ = {'stream': 1200000000, 'serial': 900000000}
TICKS = {'stream': 3, 'serial': 4}  # common 3.6 GHz timeline, no float conversion


def finite_calendar(bits, beat_bits, capacity, latency_ticks, source_domain, dest_domain,
                    dest_stalls=(), deadline_ticks=1000000, wire_bits=None):
    if any(type(x) is not int or x <= 0 for x in (bits, beat_bits, capacity)):
        raise ValueError('positive integer payload/beat/capacity required')
    if type(latency_ticks) is not int or latency_ticks < 0:
        raise ValueError('nonnegative priced transport/CDC latency required')
    if source_domain not in TICKS or dest_domain not in TICKS:
        raise ValueError('unpriced clock domain')
    stalls = set(dest_stalls)
    if any(type(t) is not int or t < 0 or t % TICKS[dest_domain] for t in stalls):
        raise ValueError('stalls must lie on destination edges')
    if wire_bits is None:wire_bits=beat_bits
    if type(wire_bits) is not int or wire_bits<=0:raise ValueError("positive aggregate physical wire bits required")
    count = (bits + beat_bits - 1) // beat_bits
    next_offer_tick=0
    pending = deque()
    sent = received = high = blocked = 0
    records = []
    for tick in range(deadline_ticks + 1):
        # Registered storage: accept-before-offer, never same-edge cut-through.
        if tick % TICKS[dest_domain] == 0 and tick not in stalls:
            if pending and pending[0][0] <= tick:
                release, seq, offered = pending.popleft()
                if seq != received:
                    raise ValueError('packet beat ordering changed')
                records.append(dict(sequence=seq, source_tick=offered, destination_tick=tick,
                                    valid_bits=min(beat_bits, bits - seq * beat_bits),
                                    serialized_source_edges=(min(beat_bits,bits-seq*beat_bits)+wire_bits-1)//wire_bits))
                received += 1
        if tick % TICKS[source_domain] == 0 and tick>=next_offer_tick and sent < count:
            if len(pending) < capacity:
                valid=min(beat_bits,bits-sent*beat_bits)
                chunks=(valid+wire_bits-1)//wire_bits
                final_wire_tick=tick+(chunks-1)*TICKS[source_domain]
                pending.append((final_wire_tick + latency_ticks, sent, tick))
                next_offer_tick=tick+chunks*TICKS[source_domain]
                sent += 1
                high = max(high, len(pending))
            else:
                blocked += 1
        if received == count:
            ns = Fraction(tick * 5, 18)
            return dict(beats=count, final_valid_bits=bits-(count-1)*beat_bits,
                        high_water_beats=high, blocked_source_edges=blocked,
                        completed_tick=tick, completed_ns_exact=[ns.numerator, ns.denominator],
                        beat_calendar=records,
                        aggregate_wire_bits_per_source_cycle=wire_bits,
                        scope='analytical registered finite queue with explicit serializer; provided latency includes transport/CDC, no RTL timing proof')
    raise ValueError('finite-hop calendar deadline exceeded')


def hop_wire_bits(h):
    # boundary_bits_per_cycle is EACH replica's source-clock physical port width.
    if h.get('boundary_capacity_units')!='bits_per_source_cycle_per_replica':
        raise ValueError('hop boundary capacity per-replica units unbound')
    replicas=h['replicas'];port=h['boundary_bits_per_cycle'];beat=h['beat_bits']
    if any(type(x) is not int or x<=0 for x in (replicas,port,beat)):
        raise ValueError('positive integer port/replica/beat widths required')
    aggregate=replicas*port
    serializer=h.get('serializer')
    if serializer is not None:
        if serializer.get('mode')!='stripe_across_replicas_low_bits_first':
            raise ValueError('explicit serializer replica/order policy required')
        lane=serializer.get('lane_bits_per_replica')
        if type(lane) is not int or lane<=0 or lane>port:
            raise ValueError('serializer lane exceeds per-replica physical port')
        wire=lane*replicas
    else:
        if beat>aggregate:raise ValueError('beat exceeds aggregate physical port without serializer')
        wire=beat
    rate=h.get('routing_bits_per_track_per_source_cycle')
    tracks=h.get('routing_tracks');channel=h.get('channel_capacity_tracks')
    if any(type(x) is not int or x<=0 for x in (rate,tracks,channel)):
        raise ValueError('route width/track units unbound')
    if tracks>channel or aggregate>tracks*rate:
        raise ValueError('aggregate physical ports exceed bound route capacity')
    return wire

def validate(plan, root=ROOT):
    errors = []
    model = plan.get('model', {})
    if model.get('status') != 'EXECUTABLE_PHYSICAL_MAPPING_PRICED':
        errors.append('W16 executable mapping/pricing absent; coarse owner is insufficient')
    pins = model.get('source_sha256', {})
    if 'tools/uarch_model.py' not in pins:
        errors.append('unified model pin missing')
    for name, expected in pins.items():
        p = root / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            errors.append('source identity mismatch: ' + name)
    stages = model.get('physical_stages', [])
    ids = [s.get('id') for s in stages]
    if not stages or len(set(ids)) != len(ids):
        errors.append('explicit unique physical stage inventory required')
    for s in stages:
        if type(s.get('pairs_per_rank')) is not int or s['pairs_per_rank'] <= 0:
            errors.append('physical pair-slot capacity unbound')
    if plan.get('host_activation_arithmetic') is not False or plan.get('host_activation_gather') is not False:
        errors.append('host activation arithmetic/gather forbidden')
    if plan.get('dut_lifetime') != 'persistent_per_physical_stage_and_rank':
        errors.append('persistent stage/rank DUT required')
    mapping = plan.get('rom_addresses', [])
    if not mapping:
        errors.append('tensor/scale/metadata ROM addresses unbound')
    occupied = {}
    for row in mapping:
        required = ('tensor', 'complete_payload_sha256', 'scale_metadata_sha256', 'rows', 'cols',
                    'stage', 'rank', 'pair', 'logical_bank', 'logical_first', 'logical_count',
                    'format', 'golden_order', 'program_sha256', 'phase_key')
        if any(k not in row for k in required):
            errors.append('incomplete ROM tensor/address/program binding')
            continue
        if row['stage'] not in ids or type(row['rank']) is not int or not 0 <= row['rank'] < 4:
            errors.append('ROM stage/rank outside physical inventory')
        capacity = next((s.get('pairs_per_rank', 0) for s in stages if s.get('id') == row['stage']), 0)
        if type(row['pair']) is not int or not 0 <= row['pair'] < capacity:
            errors.append('ROM pair outside modeled slot capacity')
        for k in ('complete_payload_sha256', 'scale_metadata_sha256', 'program_sha256'):
            value = row[k]
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                errors.append('complete hash binding invalid: ' + k)
        if row['logical_bank'] not in (0, 1):
            errors.append('logical bank must retain bank0/b identity')
        start, count = row['logical_first'], row['logical_count']
        if type(start) is not int or type(count) is not int or start < 0 or count <= 0 or start + count > 8192:
            errors.append('ROM logical range outside 2x4096 physical rows')
            continue
        key = tuple(row[k] for k in ('stage', 'rank', 'pair', 'logical_bank'))
        for lo, hi in occupied.setdefault(key, []):
            if start < hi and lo < start + count:
                errors.append('overlapping ROM range')
        occupied[key].append((start, start+count))
        physical = row.get('physical', {})
        if physical != {'parity': 'logical_address%2', 'row': 'logical_address//2', 'rows_per_macro': 4096}:
            errors.append('PP physical parity/row binding absent or changed')
    lookup = plan.get('selected_expert_owner', [])
    selected = plan.get('selected_experts', [])
    if not lookup or not selected:
        errors.append('selected-expert owner/program lookup unbound')
    for selection in selected:
        matches = [x for x in lookup if x.get('layer') == selection.get('layer')
                   and x.get('expert') == selection.get('expert')]
        if len(matches) != 1 or matches[0].get('stage') not in ids:
            errors.append('selected-expert owner ambiguous or missing')
        else:
            tensors = matches[0].get('tensors', [])
            if not tensors or any(not any(r.get('stage') == matches[0]['stage'] and r.get('tensor') == t
                                           for r in mapping) for t in tensors):
                errors.append('selected owner has incompletely addressed tensors')
    hops = model.get('hops', [])
    if not hops:
        errors.append('finite hardware hop model unbound')
    for h in hops:
        required = ('source_stage', 'destination_stage', 'payload_bits', 'beat_bits', 'capacity_beats',
                    'latency_ticks', 'source_domain', 'dest_domain', 'boundary_bits_per_cycle',
                    'routing_tracks', 'channel_capacity_tracks', 'area_mm2', 'replicas', 'golden_join_order',
                    'boundary_capacity_units','routing_bits_per_track_per_source_cycle')
        if any(k not in h for k in required):
            errors.append('hop calendar/ports/route/area/replica accounting incomplete')
            continue
        if h['source_stage'] not in ids or h['destination_stage'] not in ids:
            errors.append('hop endpoints outside physical inventory')
        if h['routing_tracks'] > h['channel_capacity_tracks']:
            errors.append('hop exceeds channel capacity')
        if any(type(h[k]) is not int or h[k] <= 0 for k in ('replicas', 'boundary_bits_per_cycle')):
            errors.append('hop replica/port capacity unbound')
        if h['area_mm2'] <= 0 or h['routing_tracks'] <= 0:
            errors.append('hop area/tracks unpriced')
        try:
            finite_calendar(h['payload_bits'], h['beat_bits'], h['capacity_beats'],
                            h['latency_ticks'], h['source_domain'], h['dest_domain'],wire_bits=hop_wire_bits(h))
        except ValueError as e:
            errors.append(str(e))
    return errors


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    p = json.loads(a.plan.read_text())
    errors = validate(p)
    calendars = []
    if not errors:
        for h in p['model']['hops']:
            calendars.append(finite_calendar(h['payload_bits'], h['beat_bits'], h['capacity_beats'],
                h['latency_ticks'], h['source_domain'], h['dest_domain'], h.get('destination_stalls', []),wire_bits=hop_wire_bits(h)))
    result = dict(status='BLOCKED_UNBOUND_OR_INVALID' if errors else 'ANALYTICAL_CONTRACT_CHECK_ONLY',
                  errors=errors, calendars=calendars, RTL_exact=False, launch_allowed=False, adopt=False)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    raise SystemExit(bool(errors))
