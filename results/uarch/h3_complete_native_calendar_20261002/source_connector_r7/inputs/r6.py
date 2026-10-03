#!/usr/bin/env python3
"""Finite prospective full-width service calendar; immutable predecessors.

Caller mapping is supplied explicitly. Directed model fixtures are not actual
accepted endpoints. Positive bounded service parameters permit model sizing
before RTL; they do not establish installed service, clocks or token rates.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/fullwidth_service_r6'
MANIFEST_PIN = '5ea012a603367933380f75e85259221d99abc12bd8a768ed41ac11918622945d'


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def inputs():
    raw = (OUT / 'input_manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_PIN, 'archive manifest pin')
    result = {}
    for name, row in json.loads(raw).items():
        data = (OUT / 'inputs' / name).read_bytes()
        require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'source pin ' + name)
        result[name] = data
    contract = json.loads(result['canonical.json'])
    require(contract['canonical_owner']['bits'] == 46 and contract['W4']['capture_bits_per_SM'] == 55, 'canonical fullwidth fields')
    return result


def owner46(physical_PC, client, original_tag, generation):
    for value, width in ((physical_PC, 7), (client, 3), (original_tag, 32), (generation, 4)):
        require(type(value) is int and 0 <= value < 1 << width, 'owner field range; original tag retained')
    require(client < 6, 'NC6 occupied KV5; no extra directory client')
    return (physical_PC << 39) | (client << 36) | (original_tag << 4) | generation


def unpack_owner(value):
    require(type(value) is int and 0 <= value < 1 << 46, 'owner46')
    return dict(physical_PC=value >> 39, client=(value >> 36) & 7,
                original_tag=(value >> 4) & 0xffffffff, generation=value & 15)


TERMS = ('grant', 'forward', 'backend_read', 'return_data', 'response_capture',
         'old_sector_read', 'merge', 'both_RF_copies',
         'common_ACK', 'identity_match', 'visibility', 'consumer',
         'child_reverse', 'parent_reverse', 'reverse_CDC', 'all_copies_drain')
SOURCE_FLOORS = dict(grant=1, forward=38, backend_read=1, return_data=38,
                     response_capture=1, old_sector_read=2, merge=1,
                     both_RF_copies=1, common_ACK=1, identity_match=1,
                     visibility=1, consumer=1, child_reverse=1,
                     parent_reverse=1, reverse_CDC=38, all_copies_drain=1)


def prospective_parameters(endpoint_bound, drain_bound):
    """Named sensitivity assumption, not a measured upper bound.

    Four receiver synchronizer edges remain explicit. Six FAST-equivalent
    edges is a conservative prospective conversion at FAST1.2/SERIAL0.9;
    installed domain pairs/reset phases remain unbound.
    """
    require(type(endpoint_bound) is int and endpoint_bound > 0 and
            type(drain_bound) is int and drain_bound > 0, 'positive service and drain bounds')
    p = dict(SOURCE_FLOORS)
    p.update(forward=44, return_data=44, backend_read=endpoint_bound,
             reverse_CDC=44, consumer=endpoint_bound,
             child_reverse=endpoint_bound, parent_reverse=endpoint_bound,
             all_copies_drain=drain_bound)
    return p


class FullWidthCalendar:
    """FIFO constructive prospective schedule over actual-sized finite pools.

    Physical PC/client has16 slots; each of32SM RF owners is held until drain.
    Deterministic source-order reservation is fair for any finite admitted DAG.
    A bound assumes downstream service as supplied, not always-ready behavior.
    No timeout or generation limit. Modulo16 reuse pays a full drain on EVERY
    transaction; source implementation of that predicate remains required.
    """
    def __init__(self, parameters, *, route='held', already_paid=None):
        require(set(parameters) == set(TERMS), 'every mandatory service term required')
        for name, value in parameters.items():
            require(type(value) is int and value >= SOURCE_FLOORS[name], 'positive source floor ' + name)
        require(route in ('held', 'elastic_proposal'), 'named route implementation')
        self.p = dict(parameters)
        self.route = route
        self.paid = {} if already_paid is None else dict(already_paid)
        self.events = []
        self.ids = set()
        self.pools = {}
        self.SM_ready = {}
        self.key_ready = {}
        self.last_generation = {}
        self.generations_seen = {}
        self.wraps = 0

    def service(self, identity, kind, ready, resource, capacity, occupancy=None):
        require(identity not in self.ids, 'duplicate emitted occurrence')
        duration = self.p[kind]
        if identity in self.paid:
            require(self.paid[identity] == dict(kind=kind, duration=duration), 'paid occurrence identity/cost mismatch')
        seats = self.pools.setdefault(resource, [0] * capacity)
        require(len(seats) == capacity, 'one resource capacity authority')
        slot = min(range(capacity), key=lambda s: (seats[s], s))
        start = max(ready, seats[slot])
        hold = duration if occupancy is None else occupancy
        require(type(hold) is int and hold > 0, 'finite positive occupancy')
        seats[slot] = start + hold
        row = dict(id=identity, kind=kind, start=start, end=start + duration,
                   resource=list(resource), seat=slot, capacity=capacity,
                   resource_release=start + hold, duration=duration,
                   origin='prospective_bounded_source_model')
        row['already_paid'] = identity in self.paid
        self.ids.add(identity)
        self.events.append(row)
        return row['end']

    def admit(self, *, occurrence, owner, SM, RF_slot, release=0):
        o = unpack_owner(owner)
        require(o['client'] < 6 and type(SM) is int and 0 <= SM < 32 and
                type(RF_slot) is int and 0 <= RF_slot < 512, 'actual-sized accepted requester/RF port fields')
        require(isinstance(occurrence, str) and occurrence and type(release) is int and release >= 0, 'source occurrence/release')
        key = (o['physical_PC'], o['client'], o['original_tag'])
        previous = self.last_generation.get(key)
        if previous is not None:
            require(o['generation'] == (previous + 1) % 16, 'source allocator modulo16 transition')
            if o['generation'] == 0:
                self.wraps += 1
        planned = [(term, occurrence + ':' + term) for term in TERMS if term not in ('backend_read', 'return_data', 'response_capture')]
        planned += [(term, occurrence + ':' + term + ':beat' + str(beat))
                    for beat in range(16) for term in ('backend_read', 'return_data', 'response_capture')]
        for term, eid in planned:
            require(eid not in self.ids, 'duplicate emitted occurrence')
            if eid in self.paid:
                require(self.paid[eid] == dict(kind=term, duration=self.p[term]), 'paid occurrence identity/cost mismatch')
        slots = self.pools.setdefault(('W2_slots', o['physical_PC'], o['client']), [0] * 16)
        slot = min(range(16), key=lambda i: (slots[i], i))
        ready = max(release, slots[slot], self.SM_ready.get(SM, 0), self.key_ready.get(key, 0))
        begin = ready
        predecessor = None
        def emit(term, dependency, identity=None, extra_dependencies=()):
            if term in ('forward', 'return_data', 'reverse_CDC'):
                direction = 'forward' if term == 'forward' else 'reverse'
                resource = ('route', o['physical_PC'], direction) if self.route == 'held' else ('elastic', SM, direction)
                capacity = 1 if self.route == 'held' else 4
                occupancy = 40 if self.route == 'held' else 1
            elif term == 'backend_read':
                resource = ('backend_PC', o['physical_PC'])
                capacity = 1
                occupancy = None
            else:
                resource = ('SM_endpoint', SM)
                capacity = 1
                occupancy = None
            eid = occurrence + ':' + term if identity is None else identity
            end = self.service(eid, term, dependency, resource, capacity, occupancy)
            self.events[-1]['depends_on'] = list(extra_dependencies)
            self.events[-1]['owner46'] = owner
            self.events[-1]['owner55'] = (owner << 9) | RF_slot
            self.events[-1]['requester_SM'] = SM
            self.events[-1]['backend_PT35'] = (o['client'] << 32) | o['original_tag']
            self.events[-1]['backend_generation4'] = o['generation']
            self.events[-1]['physical_PC'] = o['physical_PC']
            self.events[-1]['identity_is_proposed_capture_not_installed_ACK_tag'] = True
            self.events[-1]['payload_bytes'] = 32 if term in ('backend_read', 'return_data', 'response_capture') else (1024 if term in ('old_sector_read', 'both_RF_copies') else 0)
            return end, eid
        for term in ('grant', 'forward'):
            ready, predecessor = emit(term, ready, extra_dependencies=() if predecessor is None else (predecessor,))
        #128 FP32 lanes are512B: all16 sector32 returns, not one generic
        #event paying a whole RF vector. Backend beats may proceed while earlier
        #returns travel; ordered captures assemble exactly16 child sectors.
        backend_ready, backend_previous = ready, predecessor
        capture_ready, capture_previous = ready, None
        captured_ids = []
        for beat in range(16):
            backend_ready, backend_previous = emit('backend_read', backend_ready,
                occurrence + ':backend_read:beat' + str(beat), (backend_previous,))
            returned, return_id = emit('return_data', backend_ready,
                occurrence + ':return_data:beat' + str(beat), (backend_previous,))
            deps = (return_id,) if capture_previous is None else (return_id, capture_previous)
            capture_ready, capture_previous = emit('response_capture', max(returned, capture_ready),
                occurrence + ':response_capture:beat' + str(beat), deps)
            captured_ids.append(capture_previous)
        ready, predecessor = capture_ready, capture_previous
        for term in TERMS[5:]:
            ready, predecessor = emit(term, ready, extra_dependencies=(predecessor,))
        slots[slot] = ready
        self.SM_ready[SM] = ready
        self.key_ready[key] = ready
        self.last_generation[key] = o['generation']
        self.generations_seen.setdefault(key, set()).add(o['generation'])
        return dict(occurrence=occurrence, owner46=owner, owner55=(owner << 9) | RF_slot,
                    requester_SM=SM, W2_private_slot=slot, admit=begin, retire=ready,
                    original_tag=o['original_tag'], generation=o['generation'], transport_sectors32=16,
                    all_copies_drain_end=ready, ownership_origin='explicit_model_caller; accepted production adapter not supplied')

    def summary(self):
        return dict(events=len(self.events), last_retire=max(self.SM_ready.values(), default=0),
                    incrementally_paid_edges=sum(e['duration'] for e in self.events if not e['already_paid']),
                    retained_existing_edges=sum(e['duration'] for e in self.events if e['already_paid']),
                    modulo16_wraps=self.wraps, route=self.route, actual_production_calls=0,
                    cost_clock='prospective FAST-equivalent model edges; not measured hardware cycles',
                    generation_cap=None, hardware_admitted=False)


def model_outputs():
    src = inputs()
    contract = json.loads(src['canonical.json'])
    commands = json.loads(gzip.decompress(src['commands.json.gz']))
    require(len(commands['RMW']) == 288 and len(commands['shared64']) == 9216, 'retained selected command inventory')
    runs = {}
    for endpoint, drain in ((8, 8), (64, 64), (256, 256)):
        for route in ('held', 'elastic_proposal'):
            c = FullWidthCalendar(prospective_parameters(endpoint, drain), route=route)
            jobs = []
            # One continuously reused source-shaped key: no silent generation15
            # end-of-run. Controls cross three complete generation wraps, not a
            # production run cap. admit() accepts arbitrarily many transactions.
            for token in range(49):
                jobs.append(c.admit(occurrence='directed.token' + str(token),
                    owner=owner46(0, 5, 0xdeadbeef, token % 16), SM=0, RF_slot=43))
            name = route + '.endpoint' + str(endpoint) + '.drain' + str(drain)
            runs[name] = dict(parameters=c.p, summary=c.summary(), jobs=jobs, events=c.events)
    contention = {}
    for route in ('held', 'elastic_proposal'):
        c = FullWidthCalendar(prospective_parameters(8, 8), route=route)
        jobs = [c.admit(occurrence='directed.SM' + str(sm), owner=owner46(0, 5, sm, 0), SM=sm, RF_slot=43) for sm in range(32)]
        contention[route] = dict(summary=c.summary(), jobs=jobs, events=c.events)
    predecessor = json.loads(src['pipeline_model.json'])
    transport = {}
    added_bits = 0
    for direction in ('request', 'return'):
        old = predecessor['directions'][direction]
        raw = old['raw_bits_per_lane'] + 46 - 16
        coded = ((raw + 63) // 64) * 72
        delta = 32 * 38 * 4 * 2 * (coded - old['coded_bits_per_lane'])
        added_bits += delta
        transport[direction] = dict(old_raw_bits=old['raw_bits_per_lane'], raw_bits=raw,
            old_coded_bits=old['coded_bits_per_lane'], coded_bits=coded,
            cut_bits_per_SM=4*coded+8, incremental_protected_bits=delta)
    model = dict(schema='FULLWIDTH_FINITE_PAID_SERVICE_R6', canonical_contract_sha256=hashlib.sha256(src['canonical.json']).hexdigest(),
                 transport_identity_replacement=dict(directions=transport,
                    owner16_replaced_by_owner46_not_appended_twice=True,
                    source_pipeline_protected_bits=predecessor['total_pipeline_protected_bits'],
                    incremental_protected_bits=added_bits,
                    revised_pipeline_protected_bits=predecessor['total_pipeline_protected_bits']+added_bits,
                    incremental_FF_screen_mm2_ASSUMED=added_bits*.2916/.5/1e6,
                    gate_selector_clock_reset_area_not_in_FF_lower=True,
                    full_area_ports_tracks_fit_requires_Popper_join=True),
                 fields=dict(owner46=contract['canonical_owner']['layout_MSB_to_LSB'], W4_W6_bits=55, NC=6,
                             KV_client=5, CTAGW=32, PTAGW=35, backend_echo_generation_bits=4,
                             compact_required=False, new_directory_client=False),
                 W2_minimum=dict(rows_per_PC=96, PCs=128, raw_bits_per_row=38, total_raw_bits=128*96*38,
                                 protection_selector_CDC_not_in_minimum=True),
                 packet_geometry=dict(RF_vector_bytes=512, sector_bytes=32, read_return_children_per_vector=16,
                                      actual_RF_copies=2, both_copy_write_bytes=1024, old_RF_pair_capture_bytes=1024),
                 RF_capture=dict(SMs=32, raw_bits_per_SM=55, total_raw_bits=1760,
                                 common_ACKs_per_both_copy_write=1, independent_mirror_ACKs=False),
                 selected_source_inventory=dict(RMW=288, shared64=9216, source_PC_counts=dict(Qwen=1737, DS=2213),
                                                actual_caller_binding_supplied=False, actual_journal_composed=False),
                 policy=dict(finite_per_PC_per_client_slots=16, SM_owner_capacity=1, source_order_reservation=True,
                             no_same_edge_slot_reuse=True, drain_each_reuse_positive=True, generation_modulus=16,
                             drain_source_export=None, original_tags_retained=True),
                 scenarios=list(runs), production_admitted=False, prospective_model_executable=True,
                 baseline_costs_overwritten=False, whole_token_ns=None,
                 execution_scope='prospective HBM-fed partial-vector RF owner chain, not source arithmetic execution',
                 downstream_service_bounds_are_scenario_assumptions=True,
                 all_copies_drain_event_assumes_source_predicate_not_yet_implemented=True,
                 UNKNOWN=['actual C0/KV accepted caller/SM/physicalPC map', 'actual all-copy/reset quiescence implementation',
                          'installed endpoint bounds/clock pairs', 'complete whole-program movement interval join',
                          'Popper wholewidth slots/cuts/ports/area and context SSFF'])
    return {'model.json':canonical(model), 'prospective_calendars.json.gz':gzip.compress(canonical(runs),mtime=0),
            'contending_32SM_calendars.json.gz':gzip.compress(canonical(contention),mtime=0)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verify', action='store_true')
    p.add_argument('--out', type=Path, default=OUT / 'final')
    a = p.parse_args()
    data = model_outputs()
    a.out.mkdir(parents=True, exist_ok=True)
    for name, raw in data.items():
        path = a.out / name
        if a.verify:
            require(path.read_bytes() == raw, 'byte exact replay ' + name)
        else:
            require(not path.exists() or path.read_bytes() == raw, 'historical overwrite refused')
            path.write_bytes(raw)
    print('PASS prospective fullwidth finite calendar; actual caller/drain and wholeprogram UNKNOWN')


if __name__ == '__main__':
    main()
