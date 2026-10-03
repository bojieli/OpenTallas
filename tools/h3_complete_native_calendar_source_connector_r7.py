#!/usr/bin/env python3
"""Prospective connected R14/W2/W4/W6 model with source-preserved identities.

Actual R14 bypasses W2, truncates backend generation, and retires early.
This executable successor models the necessary connection/quarantine, not
installed hardware. Inputs are frozen archives; numerical conversion and
production caller/drain exporters remain separate integration obligations.
"""
import argparse
import ast
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/h3_complete_native_calendar_20261002/source_connector_r7'
PIN = '757ea4ca16ca738dbe6c93ad70649fa396a049381b96a368d4eb52f1ba8c7328'


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sources():
    raw = (OUT / 'input_manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PIN, 'connector manifest pin')
    result = {}
    for name, row in json.loads(raw).items():
        data = (OUT / 'inputs' / name).read_bytes()
        require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], 'source pin ' + name)
        result[name] = data
    return result


SRC = sources()
spec = importlib.util.spec_from_file_location('private_connector_r7_r6', OUT / 'inputs/r6.py')
R6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R6)
body = [n for n in ast.parse(SRC['physical.py']).body if isinstance(n, ast.FunctionDef) and n.name == 'physical']
require(len(body) == 1, 'exact source address function')
namespace = {}
exec(compile(ast.Module(body=body, type_ignores=[]), str(OUT / 'inputs/physical.py'), 'exec'), namespace)


def physical(byte):
    require(type(byte) is int and byte >= 0, 'source positive byte aperture')
    p = namespace['physical'](byte)
    local = p['local_sector31'] * 32 + p['byte_in_sector']
    require((local // 128) * 512 + p['stack'] * 128 + local % 128 == byte, 'source inverse address')
    return dict(p, physical_PC=p['stack'] * 32 + p['PC'])


def split_frame(base):
    require(type(base) is int and base >= 0 and base % 512 == 0, 'source aligned RF512B frame')
    children = []
    for first in range(0, 16, 4):
        rows = [physical(base + 32 * beat) for beat in range(first, first + 4)]
        require(len({r['physical_PC'] for r in rows}) == 1 and len({r['stack'] for r in rows}) == 1, 'source stripe/hash run')
        children.append(dict(first=first, sectors=4, byte=base + first * 32,
            stack=rows[0]['stack'], physical_PC=rows[0]['physical_PC'], local_sector=rows[0]['local_sector31']))
    return children


DRAIN_DEBTS = ('native_ingress', 'W2_reserved_held_terminal', 'provider_backend_pending',
               'R14_lookup_held_return', 'metadata_transport_queues', 'RF_both_copy_common_ACK',
               'visibility_consumer_reader', 'child_parent_reverse', 'forward_return_reverse_CDC')
DRAIN_DOMAINS = ('R14_CORE', 'W10_FAST', 'RF_leaf')

LEGACY = dict(die=1, stack=2, sector=34, producer=64, transport=32,
              caller=16, provider_class=6, IRSslot=5, IRSserial=32)


def field(value, width):
    require(type(value) is int and 0 <= value < 1 << width, 'preserved identity field')
    return value


def source_meta92(child_owner, SM, RF_slot, parent_ref):
    R6.unpack_owner(child_owner)
    return (child_owner << 46) | (field(SM, 5) << 41) | (field(RF_slot, 9) << 32) | field(parent_ref, 32)


class ConnectorOwners:
    """Stateful prospective source connector; opaque byte execution only.

    Physical context/sidecar retained under the SAME index. Return acceptance
    cannot release the physical tag. No source/native64 field is narrowed.
    Installed accepted allocation/ACK/drain ports do not exist in this class.
    """
    def __init__(self, parent_capacity=32, *, die=0):
        require(type(parent_capacity) is int and parent_capacity > 0, 'explicit proposed directory capacity')
        field(die,1)
        self.die = die
        self.capacity = parent_capacity
        self.parents = {}
        self.children = {}
        self.contexts = {}
        self.logical_keys = set()
        self.local_W2_keys = set()
        self.backend_history = {}
        self.epochs = {d:0 for d in DRAIN_DOMAINS}
        self.reset_blocked = False
        self.fault = False

    def bind_parent(self, *, ref, native, owner46, SM, RF_slot, base, expected=0xffff, origin='host'):
        require(origin in ('host','internal_SIMD'), 'distinct source ACK origins')
        field(ref, 32); o = R6.unpack_owner(owner46); field(SM, 5); field(RF_slot, 9)
        require(not self.reset_blocked and not self.fault, 'new grants blocked on reset/fault')
        require(ref not in self.parents and len(self.parents) < self.capacity and o['client'] < 6, 'finite live parent/NC6 scope')
        require(isinstance(native, dict) and {'owner64', 'generation64', 'program_PC', 'rank', 'SM', 'versions', 'home', 'lease'} <= native.keys(), 'actual native descriptor identity/versions/home/lease')
        field(native['owner64'], 64); field(native['generation64'], 64)
        require(native['SM'] == SM and native['versions'] and native['home'] and native['lease'], 'bound requester/home/lease')
        field(native['program_PC'], 12)
        require(type(native['rank']) is int and native['rank'] == self.die, 'r17 source die1; no DS/TP4 address transfer')
        require(type(expected) is int and 0 < expected <= 0xffff, 'exact expected frame sectors')
        split_frame(base)
        self.parents[ref] = dict(native=json.loads(json.dumps(native)), owner55=(owner46 << 9) | RF_slot,
            owner46=owner46, SM=SM, RF_slot=RF_slot, base=base, expected=expected, captured={}, prior=None,
            children=set(), tickets={}, staging_active=None, staging_mode=False, origin=origin, phase='COLLECT', child_reverse=set(), image=None, epoch_reset=False)

    def begin_fragment(self, ref, index, *, source_fragment_sequence64):
        p=self.parents[ref];field(source_fragment_sequence64,64)
        require(p['phase']=='COLLECT' and not self.fault and not self.reset_blocked and
                type(index) is int and 0<=index<8 and index not in p['tickets'] and p['staging_active'] is None,
                'source one-fragment staging credit; retained8 tickets not RF retirement credit')
        require((p['expected'] & (3<<(2*index)))!=0, 'actual expected64B fragment')
        p['staging_mode']=True;p['staging_active']=index
        p['tickets'][index]=dict(source_fragment_sequence64=source_fragment_sequence64,
            parent_reference=ref,sectors=(2*index,2*index+1),store_ACK=False,credit_released=False,
            native_identity=p['native'])

    def stage_store_ACK(self, ref, index, payload64):
        p=self.parents[ref];ticket=p['tickets'].get(index)
        require(ticket is not None and p['staging_active']==index and not ticket['store_ACK'] and
                type(payload64) is bytes and len(payload64)==64 and
                all(i in p['captured'] for i in ticket['sectors']) and
                payload64==b''.join(p['captured'][i] for i in ticket['sectors']),
                'both32B children durably captured in retained assembly; matching64B staging consumer')
        ticket['store_ACK']=True

    def release_staging_credit(self, ref, index):
        p=self.parents[ref];ticket=p['tickets'][index]
        require(not self.fault and p['phase']=='COLLECT' and p['staging_active']==index and
                ticket['store_ACK'] and not ticket['credit_released'], 'staging capture ACK before continued source admission')
        ticket['credit_released']=True;p['staging_active']=None
        #Only producer staging credit returns. Both physical sector tags, full
        #metadata/tickets and parent/reader lease remain until RF/reverse/drain.

    def allocate_child(self, *, ref, owner46, first, sectors, tag12, backend_gen4, context_index, legacy, direction=False):
        p = self.parents.get(ref); o = R6.unpack_owner(owner46)
        require(p is not None and p['phase'] == 'COLLECT' and not self.reset_blocked and not self.fault, 'live accepting parent')
        require(direction is False, 'minimal C0/KV_read; backing-visible write adapter still unbound')
        require(type(first) is int and type(sectors) is int and 0 <= first < 16 and sectors == 1 and first + sectors <= 16, 'frozen W2 sector: R14 LEN1 BEAT0; LEN>1 mapping not implemented')
        require(not p['staging_mode'] or p['staging_active']==first//2, 'child belongs to live64B staging fragment')
        rows = [physical(p['base'] + 32 * i) for i in range(first, first + sectors)]
        require(len({r['physical_PC'] for r in rows}) == 1 and o['physical_PC'] == rows[0]['physical_PC'], 'actual translated PC; low7 is not physical mapping')
        require(o['client'] < 6 and o['client'] == ((p['owner46'] >> 36) & 7) and o['generation'] == p['owner46'] & 15, 'source client/generation bound to parent, original child tag independent')
        field(tag12, 12); field(backend_gen4, 4); field(context_index, 7)
        require(set(legacy) == set(LEGACY), 'full legacy identity192 preserved')
        for name, width in LEGACY.items():
            field(legacy[name], width)
        require(legacy['stack'] == rows[0]['stack'] and legacy['sector'] == rows[0]['local_sector31'] and legacy['die'] == p['native']['rank'], 'legacy source address/rank')
        require(all(p['expected'] & (1 << i) for i in range(first, first + sectors)), 'child span within expected frame')
        token = (backend_gen4 << 12) | tag12
        key = (legacy['stack'], token); physical_slot = (legacy['stack'], tag12)
        context = (legacy['stack'], o['physical_PC'] % 32, context_index)
        logical = (o['physical_PC'], o['client'], o['original_tag'], o['generation'], False)
        require(not any((s, t & 4095) == physical_slot for s, t in self.children) and key not in self.children and context not in self.contexts, 'physical tag/context quarantined until reverse and drain')
        require(logical not in self.logical_keys, 'unique W2 full logical read key')
        require(sum(k[:2] == logical[:2] for k in self.local_W2_keys) < 16, 'W2 aggregate perPC/client16; SM does not multiply credits')
        previous = self.backend_history.get(physical_slot)
        require(previous is None or backend_gen4 == (previous + 1) % 16, 'independent backend modulo16 allocator after quiescence')
        meta = source_meta92(owner46, p['SM'], p['RF_slot'], ref)
        self.children[key] = dict(ref=ref, owner46=owner46, meta92=meta, legacy=dict(legacy), first=first,
            sectors=sectors, seen=set(), reverse=set(), context=context, logical=logical, direction=False)
        self.contexts[context] = key; self.logical_keys.add(logical); self.local_W2_keys.add(logical); p['children'].add(key)
        return dict(allocated_tag12=tag12, backend_generation4=backend_gen4, backend_token16=token,
                    source_meta92=meta, parent55=p['owner55'], child_owner46=owner46,
                    legacy_identity192=dict(legacy), direction=False, R14_LEN=1, R14_BEAT=0,
                    parent_reference=ref, origin='prospective_atomic_allocator; actual accepted endpoint missing')

    def capture(self, *, die, stack, backend_token16, source_meta92, beat, legacy, payload, payload_format='opaque_FP32_U32'):
        c = self.children.get((stack, backend_token16))
        valid = (die == self.die and c is not None and source_meta92 == c['meta92'] and type(beat) is int and 0 <= beat < c['sectors'] and beat not in c['seen'])
        if valid:
            expected = dict(c['legacy'], sector=c['legacy']['sector'] + beat)
            valid = legacy == expected and type(payload) is bytes and len(payload) == 32 and payload_format == 'opaque_FP32_U32'
        if not valid:
            self.fault = True
            raise ValueError('exact full16 echo/meta/legacy/beat/typed payload; unmatched return cannot release')
        p = self.parents[c['ref']]; index = c['first'] + beat
        require(index not in p['captured'] and p['phase'] == 'COLLECT', 'duplicate/late frame sector')
        c['seen'].add(beat); p['captured'][index] = payload
        self.local_W2_keys.remove(c['logical']) #accepted one-sector held W2 terminal; physical quarantine remains
        return p['owner55']  #from prebound parent, NEVER the last child owner

    def preserved_RF_read(self, ref, pair):
        p = self.parents[ref]
        require(p['phase'] == 'COLLECT' and p['prior'] is None and type(pair) is bytes and len(pair) == 1024 and pair[:512] == pair[512:], 'exact both-copy source old-tail capture; no invented zero')
        p['prior'] = pair[:512]

    def frame(self, ref):
        p = self.parents[ref]
        mask = sum(1 << i for i in p['captured'])
        require(mask == p['expected'], 'all bound sector children captured')
        require(p['expected'] == 0xffff or p['prior'] is not None, 'partial cannot become a zero-filled whole RF vector')
        image = bytearray(p['prior']) if p['prior'] is not None else bytearray()
        if p['expected'] == 0xffff:
            image = bytearray(b''.join(p['captured'][i] for i in range(16)))
        else:
            for index, data in p['captured'].items():
                image[index*32:(index+1)*32] = data
        require(len(image) == 512, 'source RF4096 exact assembly')
        return bytes(image)

    def write_both_copies(self, ref, owner55):
        p = self.parents[ref]
        require(not self.fault and owner55 == p['owner55'] and p['phase'] == 'COLLECT', 'bound parent55 at actual proposed RF writer')
        p['image'] = self.frame(ref); p['phase'] = 'ACK'
        return (p['image'], p['image'])

    def common_ACK(self, ref, owner55, *, origin='host'):
        require(origin == self.parents[ref]['origin'], 'host/internal SIMD ACK port cannot retire other origin')
        self.advance(ref, owner55, 'ACK', 'VISIBLE')

    def visible(self, ref, owner55):
        self.advance(ref, owner55, 'VISIBLE', 'CONSUMER')

    def consume(self, ref, owner55):
        self.advance(ref, owner55, 'CONSUMER', 'REVERSE')

    def advance(self, ref, owner55, before, after):
        p = self.parents[ref]
        require(not self.fault and p['owner55'] == owner55 and p['phase'] == before, 'same parent55 causal commonACK/visibility/consumer')
        p['phase'] = after

    def child_reverse(self, *, die, stack, backend_token16, source_meta92, beat, owner55, direction=False):
        c = self.children.get((stack, backend_token16))
        p = None if c is None else self.parents[c['ref']]
        if (die != self.die or c is None or p['phase'] != 'REVERSE' or p['owner55'] != owner55 or c['meta92'] != source_meta92 or
                type(beat) is not int or beat not in c['seen'] or beat in c['reverse'] or direction is not c['direction'] or self.fault):
            self.fault = True
            raise ValueError('validated matching full16 child reverse after consumer; no credit release')
        c['reverse'].add(beat)

    def parent_reverse_CDC(self, ref, owner55):
        p = self.parents[ref]
        require(p['phase'] == 'REVERSE' and owner55 == p['owner55'] and not self.fault and
                all(len(self.children[k]['reverse']) == self.children[k]['sectors'] for k in p['children']), 'all child reverse then bound parent reverse CDC')
        p['phase'] = 'DRAIN'

    def prospective_drain_receipt(self, ref):
        p=self.parents[ref]
        require(p['phase']=='DRAIN','parent reverse/CDC before quiescence observation')
        return dict(parent_reference=ref,parent55=p['owner55'],die=self.die,
                    backend_tokens=sorted([list(k) for k in p['children']]),
                    epochs=dict(self.epochs),zero_debts={k:0 for k in DRAIN_DEBTS},
                    origin='prospective_fixture_only_not_installed_source')

    def release_after_model_drain(self, ref, *, positive_wait_edges, receipt):
        p = self.parents[ref]
        require(p['phase'] == 'DRAIN' and not self.fault and type(positive_wait_edges) is int and positive_wait_edges > 0, 'positive quiescence wait; no source early ore release')
        expected=self.prospective_drain_receipt(ref)
        require(type(receipt) is dict and canonical(receipt)==canonical(expected),
                'matched DIE/parent/backend16/current domains and all9 debt counters; no local-empty shortcut')
        for key in p['children']:
            c = self.children.pop(key); self.contexts.pop(c['context']); self.logical_keys.remove(c['logical'])
            self.backend_history[(key[0], key[1] & 4095)] = key[1] >> 12
        del self.parents[ref]
        #This transition assumes source-owned all-copy/reset proof. It is NOT
        #an installed predicate or authorization to flush real queues/reset.

    def begin_reset(self):
        self.reset_blocked = True
        self.epochs={k:v+1 for k,v in self.epochs.items()}
        #No parent, slot, physical tag, SRAM bytes or logical key is freed.


class ConnectorCalendar:
    """Paid prospective source service composition, never128 free PC services.

    One physical command bus/stack and one held tag-owner engine/stack.
    CORE/client edge costs use an EXPLICIT prospective ratio to FAST; outputs
    retain native edge counts. No measured clocks or PHY cost claimed.
    """
    def __init__(self, endpoint_bound, drain_bound, *, CORE_to_FAST=(4, 3), route='held', already_paid=None):
        field(endpoint_bound, 32); require(endpoint_bound > 0 and type(drain_bound) is int and drain_bound > 0, 'positive endpoint/drain assumptions')
        numerator, denominator = CORE_to_FAST
        require(type(numerator) is int and type(denominator) is int and numerator > 0 and denominator > 0, 'explicit prospective clock ratio')
        self.core = lambda n: math.ceil(n * numerator / denominator)
        self.ratio = CORE_to_FAST
        self.engine = R6.FullWidthCalendar(R6.prospective_parameters(endpoint_bound, drain_bound), route=route, already_paid=already_paid)
        self.engine.p.update(reverse_sector_wire=44, fragment_credit_reserve=1, stage_store_ACK=1, stage_credit_return=1, child_tuple_assign=1, W2_write_terminal=self.core(3), W2_reserve=self.core(1), R14_allocate=self.core(1), command_bus=self.core(1),
            R14_return_arb=self.core(7), R14_lookup=self.core(12), metadata_join=self.core(1),
            W2_restore=self.core(2), held_return=endpoint_bound, R14_reverse_lookup=self.core(12))
        self.W6 = json.loads(SRC['W6_model.json'])
        for b in self.W6['boundaries']:
            self.engine.p['W6_'+b['name']] = b['candidate_minimum_edges']
        self.route = route
        self.parents_ready = {}
        self.jobs = []

    def schedule(self, *, name, base, SM, parent55, bindings, release=0):
        stripes = split_frame(base)
        children = [dict(first=i,sectors=1,byte=base+32*i,stack=physical(base+32*i)['stack'],
                         physical_PC=physical(base+32*i)['physical_PC'],local_sector=physical(base+32*i)['local_sector31']) for i in range(16)]
        require(type(bindings) is list and len(bindings)==16 and len({(r['legacy_identity192']['stack'],r['backend_token16']) for r in bindings})==16, 'bound sixteen distinct child allocations required')
        for child,binding in zip(children,bindings):
            meta=binding['source_meta92'];owner=R6.unpack_owner(binding['child_owner46'])
            require(binding['R14_LEN']==1 and binding['R14_BEAT']==0 and binding['parent55']==parent55 and
                    owner['physical_PC']==child['physical_PC'] and meta>>46==binding['child_owner46'] and
                    (meta>>41)&31==SM and meta&0xffffffff==binding['parent_reference'] and
                    binding['backend_token16']==(binding['backend_generation4']<<12)|binding['allocated_tag12'], 'full source child/meta/parent/frame allocation binding')
        e = self.engine; ready = max(release, self.parents_ready.get(SM, 0)); begin = ready
        before = None
        def event(kind, start, resource, dependencies=(), suffix='', capacity=1, occupancy=None, binding=None):
            identity = name + ':' + kind + suffix
            end = e.service(identity, kind, start, resource, capacity, occupancy)
            row = e.events[-1]; row.update(depends_on=list(dependencies), parent55=parent55, requester_SM=SM)
            if binding is not None:
                row.update(child_owner46=binding['child_owner46'], source_meta92=binding['source_meta92'],
                           backend_token16=binding['backend_token16'], legacy_identity192=binding['legacy_identity192'],
                           source_allocation_origin=binding['origin'], direction=binding['direction'], R14_LEN=1, R14_BEAT=0)
            if kind in ('R14_lookup', 'R14_reverse_lookup', 'R14_return_arb', 'W2_restore'):
                row['native_CORE_or_client_edges'] = {'R14_lookup':12,'R14_reverse_lookup':12,'R14_return_arb':7,'W2_restore':2}[kind]
                row['conversion_origin'] = 'prospective supplied ratio; actual connected clock pair UNKNOWN'
            return end, identity
        ready, before = event('grant', ready, ('parent_allocator',), ())
        captures = []; live_child_contexts = []
        for child,binding in zip(children,bindings):
            if child['first']%2==0:
                ready,before=event('fragment_credit_reserve',ready,('source_fragment_credit',SM),(before,),'.fragment'+str(child['first']//2))
            ready_child,assigned=event('child_tuple_assign',ready,('source_child_allocator',),(before,),'.sector'+str(child['first']),binding=binding)
            stack = child['stack']; pc = child['physical_PC']; local = pc % 32
            ready_child, source_event = event('W2_reserve', ready_child, ('W2_request_lookup', pc), (assigned,), '.child'+str(child['first']),occupancy=self.core(2),binding=binding)
            ready_child, source_event = event('forward', ready_child, ('W10_forward',stack,local), (source_event,), '.child'+str(child['first']), occupancy=40 if self.route=='held' else 1,binding=binding)
            ready_child, source_event = event('R14_allocate', ready_child, ('tag_owner_engine',stack), (source_event,), '.child'+str(child['first']),binding=binding)
            ready_child, source_event = event('command_bus', ready_child, ('command_bus',stack), (source_event,), '.child'+str(child['first']),binding=binding)
            live_child_contexts.append(dict(stack=stack,PC=pc,begin=ready_child))
            backend_ready, backend_event = ready_child, source_event
            for beat in range(child['sectors']):
                suffix='.sector'+str(child['first']+beat)
                backend_ready, backend_event = event('backend_read',backend_ready,('backing_bus',stack),(backend_event,),suffix,binding=binding)
                arb, arb_id = event('R14_return_arb',backend_ready,('return_arb',stack),(backend_event,),suffix,binding=binding)
                hold=e.p['R14_lookup']+e.p['metadata_join']+e.p['W2_restore']+e.p['held_return']
                out, lookup_id = event('R14_lookup',arb,('tag_owner_engine',stack),(arb_id,),suffix,occupancy=hold,binding=binding)
                out, join_id = event('metadata_join',out,('sidecar_join',stack),(lookup_id,),suffix,binding=binding)
                out, match_id = event('W2_restore',out,('W2_read_lookup',pc),(join_id,),suffix,occupancy=self.core(2),binding=binding)
                out, held_id = event('held_return',out,('held_acceptance',stack),(match_id,),suffix,binding=binding)
                out, route_id = event('return_data',out,('W10_return',stack,local),(held_id,),suffix,occupancy=40 if self.route=='held' else 1,binding=binding)
                deps=(route_id,) if not captures else (route_id,captures[-1][1])
                captured, cap_id = event('response_capture',max(out,captures[-1][0] if captures else 0),('assembler',SM),deps,suffix,binding=binding)
                e.events[-1]['sector_index']=child['first']+beat;e.events[-1]['payload_bytes']=32
                captures.append((captured,cap_id))
            if child['first']%2==1:
                ready,before=event('stage_store_ACK',captured,('assembly_store_ACK',SM),tuple(i for _,i in captures[-2:]),'.fragment'+str(child['first']//2))
                ready,before=event('stage_credit_return',ready,('source_fragment_credit',SM),(before,),'.fragment'+str(child['first']//2))
        ready, before = max(t for t,_ in captures), captures[-1][1]
        #Frame assembly joins EVERY child capture even with reordered returns.
        dependencies=tuple(i for _,i in captures)
        for term in ('old_sector_read','merge','both_RF_copies','common_ACK'):
            ready,before=event(term,ready,('RF_endpoint',SM),dependencies)
            dependencies=(before,)
        for term in ('W6_ACK_to_visible','W6_visible_to_consumer','consumer','W6_consumer_to_child_reverse'):
            ready,before=event(term,ready,('W6_endpoint',SM),(before,))
        for child,binding in zip(children,bindings):
            stack=child['stack']
            for beat in range(child['sectors']):
                suffix='.sector'+str(child['first']+beat)
                ready,before=event('reverse_sector_wire',ready,('W10_return',stack,child['physical_PC']%32),(before,),suffix,occupancy=40 if self.route=='held' else 1,binding=binding)
                ready,before=event('R14_reverse_lookup',ready,('tag_owner_engine',stack),(before,),suffix,binding=binding)
                ready,before=event('child_reverse',ready,('reverse_match',stack),(before,),suffix,binding=binding)
        ready,before=event('W6_child_to_parent_reverse',ready,('W6_endpoint',SM),(before,))
        ready,before=event('parent_reverse',ready,('parent_reverse',SM),(before,))
        ready,before=event('W6_parent_to_reverse_CDC',ready,('W6_endpoint',SM),(before,))
        ready,before=event('reverse_CDC',ready,('reverse_CDC',SM),(before,),occupancy=40 if self.route=='held' else 1)
        for term in ('W6_reverse_CDC_to_drain_request','W6_drain_request_to_allcopies'):
            ready,before=event(term,ready,('W6_endpoint',SM),(before,))
        ready,before=event('all_copies_drain',ready,('quiescence',SM),(before,))
        for term in ('W6_allcopies_to_retire','W6_retire_to_new_accept'):
            ready,before=event(term,ready,('W6_endpoint',SM),(before,))
        self.parents_ready[SM]=ready
        for row in live_child_contexts:row['end']=ready
        job=dict(name=name,parent55=parent55,SM=SM,begin=begin,retire=ready,
                 children=children,bindings=bindings,physical_context_quarantine=live_child_contexts, R14_LEN=1, R14_BEAT=0)
        self.jobs.append(job)
        return job


def model_outputs():
    costs=json.loads(SRC['costs.json']); require(costs['pipeline_two_seats_38stages_144lanes_increment_bits']==144*38*2*72*2, 'exact W10 delta')
    runs={}
    lifecycle=[]
    for bound in (8,64,256):
        for route in ('held','elastic_proposal'):
            c=ConnectorCalendar(bound,bound,route=route)
            owners=ConnectorOwners()
            for sm in range(4):
                parent=R6.owner46(7,5,0xfeedbeef+sm,6);parent55=(parent<<9)|43
                ref=100+sm
                native=dict(owner64=(1<<63)+17+sm,generation64=(1<<63)+25,program_PC=9,rank=0,SM=sm,
                    versions=['directed.native.version'],home='directed.retained.home',lease='directed.reader.lease')
                owners.bind_parent(ref=ref,native=native,owner46=parent,SM=sm,RF_slot=43,base=0)
                bindings=[]
                for fragment in range(8):
                    owners.begin_fragment(ref,fragment,source_fragment_sequence64=sm*8+fragment)
                    for sector in (fragment*2,fragment*2+1):
                        p=physical(sector*32)
                        legacy=dict(die=0,stack=p['stack'],sector=p['local_sector31'],producer=(1<<63)+101,
                            transport=sm*16+sector,caller=sector,provider_class=2,IRSslot=5,IRSserial=sm+1)
                        b=owners.allocate_child(ref=ref,owner46=R6.owner46(p['physical_PC'],5,0xabcde000+sm*16+sector,6),
                            first=sector,sectors=1,tag12=sm*16+sector,backend_gen4=10,
                            context_index=sm*4+sector%4,legacy=legacy)
                        bindings.append(b)
                        result=owners.capture(die=0,stack=legacy['stack'],backend_token16=b['backend_token16'],
                            source_meta92=b['source_meta92'],beat=0,legacy=legacy,payload=bytes([sm*16+sector])*32)
                        require(result==parent55,'stable parent not last child')
                    owners.stage_store_ACK(ref,fragment,b''.join(bytes([sm*16+i])*32 for i in (fragment*2,fragment*2+1)))
                    owners.release_staging_credit(ref,fragment)
                    require(len(owners.children)==2*(fragment+1),'stage credit is NOT physical tag retirement')
                c.schedule(name='directed.SM'+str(sm),base=0,SM=sm,parent55=parent55,bindings=bindings)
                pair=owners.write_both_copies(ref,parent55)
                owners.common_ACK(ref,parent55);owners.visible(ref,parent55);owners.consume(ref,parent55)
                for b in bindings:
                    owners.child_reverse(die=0,stack=b['legacy_identity192']['stack'],backend_token16=b['backend_token16'],
                        source_meta92=b['source_meta92'],beat=0,owner55=parent55)
                require(len(owners.children)==16,'physical quarantine retained until parent reverse and drain')
                owners.parent_reverse_CDC(ref,parent55)
                owners.release_after_model_drain(ref,positive_wait_edges=bound,receipt=owners.prospective_drain_receipt(ref))
                lifecycle.append(dict(scenario=route+'.bound'+str(bound),SM=sm,parent_reference=ref,parent55=parent55,
                    native=native,children=bindings,frame_sha256=hashlib.sha256(pair[0]).hexdigest(),
                    retained_fragment_tickets=len(owners.parents[ref]['tickets']) if ref in owners.parents else 8,
                    staging_credit_returned_before_RF_ACK=True,physical_reverse_deferred=True,
                    both_copy_images_identical=pair[0]==pair[1],local_W2_keys=len(owners.local_W2_keys),
                    physical_contexts_after_positive_drain=len(owners.contexts),actual_endpoint_trace=False))
            runs[route+'.bound'+str(bound)]=dict(jobs=c.jobs,events=c.engine.events,
                last_retire=max(c.parents_ready.values()),parameters=c.engine.p,
                CORE_to_FAST=list(c.ratio),origin='prospective source-connected control, not installed endpoint trace')
    w2=json.loads(SRC['W2_composition.json'])
    require(w2['p_wr_done_ready_required'] and w2['chosen_endpoint_contract']['R14_LEN6_value_for_this_minimum_sector_route']==1, 'current frozen W2 endpoint')
    w6=json.loads(SRC['W6_model.json']);w6_connector=json.loads(SRC['W6_connector.json'])
    require(w6['table']['raw_bits_per_SM']==71 and w6['table']['protected_bits_per_SM']==144, 'frozen W6 retained state')
    source_fragment=json.loads(SRC['atomic_owner_contract.json'])
    require(source_fragment['provider_fragment_credit']==1 and source_fragment['max_provider_fragments_per_command']==64,'source credit1/max64')
    model=dict(schema='SOURCE_CONNECTOR_FINITE_MODEL_R7',connector_commit='1bfbbda5afeafde216ab5c6d79dd3b72efaa2800',
        actual_route_bypasses_W2=True,proposed_route_inserts_W2_on_real_path=True,
        fields=dict(child_owner46=46,SM=5,RF_slot=9,parent_ref=32,source_meta92=92,backend_token16=16,
                    producer_gen4_independent_of_backend_gen4=True,parent55_from_boundref_not_lastchild=True,
                    legacy_identity192_unchanged=True,source_provider_class6_not_client3=True,NC=6,KV_client5=True,new_seventh_client=False),
        drain_interface_spec=dict(debt_counters=list(DRAIN_DEBTS),domains=list(DRAIN_DOMAINS),
            epochs='matched retained reset cohort per domain; no local counter clear',
            release='stop new grants, all expected sector data captured, both-copy/commonACK and consumer accepted, all child/parent reverse accepted, all9 transport/source debt counters zero, matched current cohort, positive wait then atomic metadata/tag release',
            retained_quarantine_rows_not_counted_as_inflight_transport_copies=True,
            source_endpoint_installation=False,source_predicate_generation_requires_real_exports=True),
        source_fragment_join=dict(source_credit=1,source_max_fragments=64,fragment_bytes=64,frame_bytes=512,
            retained_fragment_tickets_per_frame=8,retained_sector_identities_per_frame=16,
            proposed_stage_credit_release='after64B retained assembly store and matched staging consumerACK',
            physical_reverse='deferred through RF/commonACK/consumer/parent/reverseCDC/source drain',
            actual_native_provider_event_adapter_installed=False, credit_held_to_RF_ACK_deadlock=True),
        allocator_lower_inventory=dict(parent_rows=32,parent_row_raw=139,sector_rows=512,sector_row_raw=174,
            sector_row_protected=216,counter_banks=5,counter_bits=36,parentref_counter_bits=32,
            gross_raw_bits=32*139+512*174+5*36+32,
            gross_protected_bits=32*216+512*216+5*72+72,
            net_overlap_with_R14_meta92_and_W4_parent55=None,
            full_native_private_context_not_priced_in_lower=True,RF_assembly_not_recharged=True),
        conservative_whole_command_inventory=json.loads(SRC['Russell_allocator_r3.json'])['allocator_mapping_state_inputs'],
        prospective_full32SM_parent_model=json.loads(SRC['W5_W10_parent_model.json']),
        one_frame_lower_is_not_whole_command_capacity=True,
        W6_component=w6, W6_connector=w6_connector,
        W6_local_edges_counted_once=sum(b['candidate_minimum_edges'] for b in w6['boundaries']),
        W6_local_control_edges_separate_from_W10_envelope_travel=True,
        unproved_CDC_overlap_not_deducted=True,
        reverse_packet_raw_bits=363, reverse_packet_protected_bits=432,
        missing_ports=dict(native_caller='accepted tag/client/SM/parentref descriptor allocator',
            R14_acceptance='atomic accepted_valid/allocated_tag12/backendgen4/context_index',
            backing='full16 command/read return and held p_wr_done_v/r; physical write visibility',
            W2='PTAG39+physicalPC/direction/restored data held valid/ready',
            RF='bound parent55 at write_go; host commonACK separate internalSIMD ACK',
            staging='retained64B stage_store_v/r + stage_consumerACK + stagingcredit return; physicalreverse deferred',
            W6='57bit held visibility/consumer/reverse;57bit drainrequest and66bit allcopies response',
            reset_CDC='source-owned nine debt classes, both CDC endpoints/reset epochs'),
        W2_composition=w2, p_wr_done_ready_REQUIRED=True, older_pulse_only_contract_superseded=True,
        W2_LEN1_BEAT0=True, LEN_gt1_unimplemented_unpriced=True,
        W2_gross_cost_not_net_increment=True, matched_prior_W2_debit=None,
        W2_local_credit_may_retire_at_held_client_terminal_but_physical_quarantine_remains=True,
        DIE_scope_preserved_external_to_owner46=True, STACK_scope_preserved=True,
        cost_inputs=costs,W10_missing_sideband_raw_bits=50,
        arithmetic_occurrences_not_recharged=True,
        W10_increment_replaces_its_own_144lane_basis=True,R6_128lane_increment_not_added=True,
        logical_sidecar_bits=1572864,physical_sidecar_macro_bits=4194304,additional_macros=128,
        second_CAM_added=False,RF_assembler_data_bits=131072,RF_mask_bits=512,
        original_RF_macro_area_recharged=False,tagowner_lookup_CORE_edges=12,return_arb_CORE_edges=7,
        physical_command_buses=4,free_128PC_backend_parallelism=False,
        source_address_scope='archived Qwen r17 die1/fourstack map only; DS/TP4 source adapter UNKNOWN',
        software_native64_not_truncated=True,physical_tags_quarantined_until_reverseCDC_and_drain=True,
        backend_full16_echo_installed=False,physical_tag_early_retirement_corrected_in_model_only=True,
        prospective_params_are_positive_assumptions=True,whole_token_ns=None,actual_production_calls=0,
        source_PC_domains=dict(Qwen=1737,DS=2213),whole_program_composed=False,hardware_admitted=False,
        UNKNOWN=['actual accepted native caller/client/SM/tag/gen/ref directory allocator',
                 'full16 command/backing/provider echo installation; W2 insertion and quarantine source implementation',
                 'typed KV codec/conversion and exact partial RF source producer join',
                 'actual all-copy reset/drain/CDC epochs and source waits',
                 'complete W10/sidecar/selector/codec/macro/ports/cuts/clock physical fit',
                 'whole-program actual movement/journal enrollment'])
    return {'model.json':canonical(model),'calendars.json.gz':gzip.compress(canonical(runs),mtime=0),
            'ownership_lifecycle.json':canonical(lifecycle)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path,default=OUT/'run_r4');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    for name,raw in model_outputs().items():
        path=a.out/name
        if a.verify:require(path.read_bytes()==raw,'byte exact connector replay '+name)
        else:
            require(not path.exists() or path.read_bytes()==raw,'historical overwrite refused');path.write_bytes(raw)
    print('PASS source-connected prospective model; actual caller/full16/drain/codec/wholeprogram UNKNOWN')


if __name__=='__main__':main()
