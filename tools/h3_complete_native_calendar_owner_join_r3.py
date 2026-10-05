#!/usr/bin/env python3
"""Execute emitted movement commands through Popper's retained owner endpoint.

This additive connector delegates byte movement and ownership to SelectedEndpoint.
Completion capture has a preallocated slot, independent of consumer readiness.
It is a software port driver; no new hardware owner or timing is qualified.
"""
import argparse
from collections import Counter, deque
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3'
PINS = {
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/Goodall_requirements.json': 'bf94c549f58901af3bdb816e90aa622730454b8e03122058481f90178d9ef980',
    'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz': 'ff789c0c464b6a13b96f197a10004bd79c0b478f9932404c1bfe25e30dd3aabc',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/DS_chain_boundaries.json': '69d671da20cd9793d7a9c407564e2a48683944969e8957b4392a713df96fe547',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/V1_serialized_owner.py': 'bcbc01538348a37609451307816471a702482dc551b6917fc66ae8ef3ccc2cda',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/hbm_gpu.json': '80afd828f1eb6898b808fbe9471f8500a25e147f527e94832dfa557acdca0731',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/codex_notes.txt': 'f9ef2c698f3d9fa5992823d8d2fab13899e16f7a1a01a895bba45ae3c73ac099',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/dependency_fields.json': '4d88b003fc730ded5fab4abe7fc8c6903f1ae647a8504e01cfaefca1b800a069',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/zero_classification.json': '5cbd5556118befd8ce10a8d43272b56bda0a6a0a9740953d9da50788e97b4e39',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/KV_current_plan.json.gz': 'ba50d70cfcb2c4d73eff56a707bf4d99470681de06117d428c15af2eb962801a',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/KV_current_owner.py': '019b08bdca39d3c9c851d9139e0de0d247beff72265b2dd9fcc57a6c425f0547',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/C0_owner_addressed.py': 'af25f5fcec8730db28f3a988877364601823e2a13605257bfe07e3f4bf641528',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/fifo2.sv': 'a424d37ec80d6c3cc326bf067b26849bcb43ef9f620a90f8d34a900fe6933903',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/uarch_model.py': '2da5b6d90adfbeb58ca9355db636835205bf6953328a247bf709c6ab93260c45',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/audit.md': '0ebd61f798c21f4295a7f5aee063e31ebcfcbd8033c750e4c373f080c4bf299f',
    'results/uarch/h3_complete_native_calendar_20261002/production_owner_join_r3/inputs/audit.json': '44f4e634232e79776704d4efc0bbd10015f51e5ceca58b579745ca8710880fab',
    'tools/h4_hbm_atomic_source_g0.py': '3d76eacbd22a39745af395db77215fd19468dd26b233465dee5e49c6b822121b',
    'tools/h4_hbm_selected_cache_rmw.py': '04f271fa5a647e7132a2bd36f6c764cb5fe440e18cec7c096c9c860be3e50ade',
    'tools/h3_complete_native_calendar_grants_r1.py': '4bbd9ce96f4cf0afef069d6b0a94379d04a0e054e337477d125ed6cf999d6dbd',
    'results/uarch/h4_hbm_selected_cache_rmw_20261002/selected_r4/commands.json.gz': '9f8c0fbf277c3405f09444efa7a592496b6c92761cc9c8c9fa22da9af41f5464',
}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def source_module(path, expected):
    source = ROOT / path
    if sha(source.read_bytes()) != expected:
        raise ValueError('retained endpoint source pin: ' + path)
    # Enroll only a private root+hash namespace so inspect.getsource(class) can
    # resolve the retained file. Never replace a canonical module or function.
    import sys
    namespace = 'owner_join_r3_' + expected[:12] + '_' + sha(str(source.resolve()).encode())[:12]
    cached = sys.modules.get(namespace)
    if cached is not None:
        if Path(cached.__file__).resolve() != source.resolve():
            raise ValueError('private retained module origin mismatch')
        return cached
    spec = importlib.util.spec_from_file_location(namespace, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[namespace] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[namespace]
        raise
    return module

def sources():
    popper = source_module('tools/h4_hbm_selected_cache_rmw.py', PINS['tools/h4_hbm_selected_cache_rmw.py'])
    grants = source_module('tools/h3_complete_native_calendar_grants_r1.py', PINS['tools/h3_complete_native_calendar_grants_r1.py'])
    path = 'results/uarch/h4_hbm_selected_cache_rmw_20261002/selected_r4/commands.json.gz'
    raw = (ROOT / path).read_bytes()
    if sha(raw) != PINS[path]:
        raise ValueError('retained emitted movement command archive pin')
    commands = json.loads(gzip.decompress(raw))
    return popper, grants, commands, sha(raw)

class ProductionOwnerJoin:
    """One real SelectedEndpoint and one completion slot per admitted SM.

    Public operations drive the retained owner FSM, never a second owner model.
    Physical ACKs carry no full owner field: the connector retains source identity
    from request acceptance. Tokens identify that retained context in receipts.
    Exact completion tokens cannot retroactively authenticate an untagged wire;
    production requires the connected source owner gate and actual SRAM receipts.
    """
    def __init__(self):
        popper, self.grants, commands, archive_sha = sources()
        self.atomic = source_module('tools/h4_hbm_atomic_source_g0.py', PINS['tools/h4_hbm_atomic_source_g0.py'])
        self.endpoint = popper.SelectedEndpoint(commands)
        self.bindings = self.grants.compile_commands(commands, archive_sha)
        self.ledger = self.grants.CausalGrantLedger(self.bindings)
        self.commands = self.endpoint.commands
        self.pending = {}; self.live = {}; self.requested = set(); self.drain_gates = {}
        self.events = Counter(); self.last_edge = {}
        self.retired_tokens = set()
        self.child_to_command = {}
        self.parent_to_command = {}
        for p in self.bindings['parents'].values():
            first = p['children'][0]
            command = p['id'] if p['scope'] == 'actual_all96_PC0_RMW' else first
            self.parent_to_command[p['id']] = command
            for child in p['children']:
                self.child_to_command[child] = command if p['scope'] == 'actual_all96_PC0_RMW' else child
        self.command_to_parent = {c: self.bindings['children'][child]['parent'] for child, c in self.child_to_command.items()}

    def receipt(self, command_id, *, lease):
        """Shape helper only; caller must obtain lease from entering provider.

        It does not invent a provider lease or assert production ownership.
        """
        c = self.commands[command_id]
        source_lease = c['version'] if c['kind'] == 'RF_partial_RMW' else c['source_tile_lease']
        return dict(generation=c['generation'], die=c['die'], SM=c['SM'],
                    provider_reference=c['provider_reference'], lease=lease, live=True,
                    outer_owner=c['outer_owner'], source_lease=source_lease,
                    command_sha256=sha(canonical(c)))

    def submit(self, command_id, *, receipt):
        p = self.bindings['parents'][self.command_to_parent[command_id]]
        if self.parent_to_command[p['id']] != command_id:
            raise ValueError('first emitted parent child required')
        c = self.commands[command_id]
        if (not isinstance(receipt, dict) or type(receipt.get('lease')) is not int
                or not 0 < receipt['lease'] < 2**64
                or receipt != self.receipt(command_id, lease=receipt['lease'])):
            raise ValueError('exact entering source owner/version/lease/reference required')
        if p['id'] in self.requested:
            raise ValueError('duplicate or retired source contender')
        key = (c['die'], c['SM'])
        self.pending.setdefault(key, deque()).append((p['id'], dict(receipt)))
        self.requested.add(p['id']); self.events['submitted'] += 1

    def _event(self, parent, name, *, edge, origin, **kw):
        p = self.bindings['parents'][parent]
        row = dict(parent=parent, binding_sha256=p['binding_sha256'], owner=p['owner'], lease=p['lease'],
                   domain='H1_streaming', edge=edge, origin=origin, event=name, accepted=True)
        row.update(kw)
        return row

    def admit_next(self, *, die, SM, edge, origin, drain_pins=None):
        key = (die, SM)
        if key in self.live:
            return None
        queue = self.pending.get(key, ())
        # A finite source DAG, no repeated synthetic request injection. Queue order
        # is emitted order among eligible queued parents, not elapsed-cycle proof.
        candidate = next(((p, r) for p, r in queue
                          if set(self.bindings['parents'][p]['dependencies']) <= self.ledger.retired), None)
        if candidate is None:
            return None
        parent, receipt = candidate; command = self.parent_to_command[parent]
        bare = {k: v for k, v in receipt.items() if k not in ('source_lease', 'command_sha256')}
        # Preflight immutable source identity/dependencies before either mutation.
        if key in self.endpoint.live or parent in self.ledger.retired:
            raise ValueError('Popper owner already live or retired')
        if origin not in ('endpoint_trace', 'directed_verifier_control') or type(edge) is not int or edge < self.ledger.last_edge.get(tuple(self.bindings['parents'][parent]['resource']), -1):
            raise ValueError('source admission origin/edge')
        if drain_pins is None:
            self.events['admission_wait_missing_source_pins'] += 1
            return None
        p = self.bindings['parents'][parent]
        if isinstance(p['owner'], list):
            ticket = tuple(p['owner'])
        else:
            if origin != 'directed_verifier_control':
                raise ValueError('retained shared journal has no complete C0 sequence; production drain owner UNKNOWN')
            # Shared journal fixture has tile ownership but no complete C0 sequence.
            # Do not manufacture production sequence from its source tile ordinal.
            ticket = (p['owner']['generation'], p['PC'], p['owner']['tile'], die, SM)
        gate = self.drain_gates.setdefault(key, self.atomic.DrainGate())
        if gate.phase == 'idle': gate.request(ticket)
        if gate.owner != ticket: raise ValueError('pending drain belongs to different source contender')
        if not gate.sample(drain_pins):
            self.events['admission_wait_prior_sinks'] += 1
            return None
        self.endpoint.acquire(command, lease=receipt['lease'], owner_receipt=bare)
        self.ledger.observe(self._event(parent, 'parent_grant', edge=edge, origin=origin))
        queue.remove(candidate)
        token = sha(canonical(dict(parent=parent, receipt=receipt)))
        self.live[key] = dict(parent=parent, receipt=receipt, token=token, origin=origin,
                              active=None, held=None, child_consumed=False, child_tokens=set())
        self.events['admitted'] += 1
        return token

    def _owner(self, key, token):
        x = self.live.get(key)
        if x is None or token != x['token']:
            raise ValueError('wrong or stale source full-owner/lease token')
        return x

    def issue(self, *, die, SM, token, edge, payload=None):
        key = (die, SM); x = self._owner(key, token); p = self.bindings['parents'][x['parent']]
        state = self.ledger.live[p['id']]
        if x['active'] is not None or x['held'] is not None or state['next_child'] >= len(p['children']):
            raise ValueError('one preallocated child/completion seat; parent still held')
        child = p['children'][state['next_child']]; d = self.bindings['children'][child]
        command = self.child_to_command[child]; c = self.commands[command]
        phase = self.endpoint.live[key]['phase']
        names = {'READ_ISSUE': 'read_child_accept', 'WRITE_ISSUE': 'write_child_accept',
                 'READBACK_ISSUE': 'readback_child_accept', 'SHARED_ISSUE': 'shared_child_accept'}
        if phase == 'NEXT_CHILD':
            r = self.receipt(command, lease=x['receipt']['lease'])
            bare = {k: v for k, v in r.items() if k not in ('source_lease', 'command_sha256')}
            self.endpoint.acquire(command, lease=r['lease'], owner_receipt=bare)
            phase = self.endpoint.live[key]['phase']
        if phase not in names or type(edge) is not int or edge < self.ledger.last_edge.get(tuple(p['resource']), -1):
            raise ValueError('emitted child source phase/edge')
        # The retained endpoint returns the actual merged RF write bits; shared
        # source write bytes are supplied by the producer, never a golden callback.
        if c['kind'] == 'RF_partial_RMW' and d['write']:
            if payload is not None: raise ValueError('RF write must use retained source merge result')
            output = self.endpoint.live[key]['merged']
        else:
            if not d['write'] and payload is not None:
                raise ValueError('read bytes must come from exact SRAM bank captures')
            output = payload
        self.endpoint.event(command, lease=x['receipt']['lease'], event=names[phase], payload=payload)
        self.ledger.observe(self._event(p['id'], 'child_issue', edge=edge, origin=x['origin'],
                            child=child, source_command_sha256=d['source_command_sha256'],
                            provider_reference=d['provider_reference'], valid=True, ready=True))
        child_token = sha(canonical(dict(owner_token=token, child=child,
                                        command_sha256=d['source_command_sha256'])))
        x.update(active=child, child_token=child_token, child_consumed=False,
                 issued_payload=output, captured_bank_words={})
        self.events['child_issued'] += 1
        return dict(child=child, completion_token=child_token, source_command_sha256=d['source_command_sha256'],
                    provider_reference=d['provider_reference'], expected_SRAMs=d['expected_SRAMs'],
                    write=d['write'], payload=output, parent_owner_token=token)

    def merge(self, *, die, SM, token, payload):
        x = self._owner((die, SM), token)
        if x['active'] is not None or x['held'] is not None:
            raise ValueError('read ACK/child reverse before retained merge')
        result = self.endpoint.event(self.parent_to_command[x['parent']], lease=x['receipt']['lease'],
                                     event='merge_register', payload=payload)
        self.events['source_merge'] += 1
        return result

    def observe_SRAM(self, *, die, SM, token, completion_token, event):
        x = self._owner((die, SM), token)
        if x['active'] is None or completion_token != x['child_token']:
            raise ValueError('wrong-owner or stale completion generation/child')
        if event.get('event') not in ('SRAM_accept', 'SRAM_capture', 'child_ACK') or event.get('child') != x['active']:
            raise ValueError('actual active SRAM acceptance/commonACK event required')
        d = self.bindings['children'][x['active']]
        bank = tuple(event.get('SRAM', []))
        if event['event'] == 'SRAM_capture' or (event['event'] == 'SRAM_accept' and d['write']):
            data = event.get('data')
            if type(data) is not bytes or len(data) != 32:
                raise ValueError('exact32B SRAM word receipt bytes required')
            if d['write']:
                if list(bank) not in d['expected_SRAMs']:
                    raise ValueError('exact source write SRAM bank')
                offset = bank[1]*32 if d['kind'] == 'RF' else d['expected_SRAMs'].index(list(bank))*32
                if data != x['issued_payload'][offset:offset+32]:
                    raise ValueError('SRAM accepted bytes must match retained source write/merge bits')
        self.ledger.observe(event)
        if event['event'] == 'SRAM_capture':
            x['captured_bank_words'][bank] = event['data']

    def capture_completion(self, *, die, SM, token, completion_token, payload=None):
        key = (die, SM); x = self._owner(key, token)
        if x['active'] is None or completion_token != x['child_token'] or completion_token in x['child_tokens']:
            raise ValueError('wrong-owner/stale/duplicate completion token')
        active = self.ledger.live[x['parent']]['child']
        if x['held'] is not None or not active or not active.get('ACK_accepted'):
            raise ValueError('resolved common SRAM ACK and reserved completion capture seat required')
        d = self.bindings['children'][x['active']]
        required = 0 if d['write'] else (1024 if d['kind'] == 'RF' else 64)
        if (required and (type(payload) is not bytes or len(payload) != required)) or (not required and payload is not None):
            raise ValueError('exact retained source ACK payload width')
        if not d['write']:
            expected = [tuple(bank) for bank in d['expected_SRAMs']]
            if set(x['captured_bank_words']) != set(expected):
                raise ValueError('every exact bank capture must supply source response bytes')
            captured = b''.join(x['captured_bank_words'][bank] for bank in expected)
            if payload != captured:
                raise ValueError('completion payload must equal all exact source SRAM captures')
        x['held'] = dict(completion_token=completion_token, payload=payload)
        self.events['completion_captured'] += 1

    def consume_completion(self, *, die, SM, token, ready):
        key = (die, SM); x = self._owner(key, token)
        if type(ready) is not bool: raise ValueError('explicit source consumer ready')
        if x['held'] is None: raise ValueError('matching completion capture required')
        if not ready:
            self.events['completion_backpressured'] += 1
            return None
        command = self.child_to_command[x['active']]
        phase = self.endpoint.live[key]['phase']
        names = dict(READ_ACK='read_ACK_consume', WRITE_ACK='write_ACK_consume',
                     READBACK_ACK='readback_ACK_consume', SHARED_ACK='shared_ACK_consume')
        if phase not in names: raise ValueError('retained endpoint completion phase')
        # Flags are derived from the ledger's exact two-copy common ACK, not
        # caller assertions or two independently fabricated host ACK pins.
        result = self.endpoint.event(command, lease=x['receipt']['lease'], event=names[phase],
                                     payload=x['held']['payload'], copy0=True, copy1=True)
        x['child_tokens'].add(x['child_token']); x.update(held=None, child_consumed=True)
        self.events['completion_consumed'] += 1
        return result

    def reverse_child(self, *, die, SM, token, completion_token, edge):
        key = (die, SM); x = self._owner(key, token)
        if not x['child_consumed'] or x['held'] is not None or completion_token != x['child_token']:
            raise ValueError('held completion/consumer or stale child reverse')
        phase = self.endpoint.live[key]['phase']
        names = dict(READ_REVERSE='read_child_reverse', WRITE_REVERSE='write_child_reverse',
                     READBACK_REVERSE='readback_child_reverse', SHARED_REVERSE='shared_child_reverse')
        if phase not in names: raise ValueError('retained endpoint child reverse phase')
        self.ledger.observe(self._event(x['parent'], 'child_reverse', edge=edge, origin=x['origin'], child=x['active']))
        self.endpoint.event(self.child_to_command[x['active']], lease=x['receipt']['lease'], event=names[phase])
        x.update(active=None, child_consumed=False); self.events['child_reverse'] += 1

    def visibility(self, *, die, SM, token, edge):
        x = self._owner((die, SM), token)
        if self.endpoint.live[die, SM]['phase'] != 'CONSUMER':
            raise ValueError('retained source children/readback not complete')
        self.ledger.observe(self._event(x['parent'], 'visibility_fence', edge=edge, origin=x['origin']))
        self.events['visibility'] += 1

    def consumer(self, *, die, SM, token, edge):
        key = (die, SM); x = self._owner(key, token)
        if self.endpoint.live[key]['phase'] != 'CONSUMER': raise ValueError('matching retained source consumer')
        self.ledger.observe(self._event(x['parent'], 'consumer', edge=edge, origin=x['origin']))
        command = self.child_to_command[self.bindings['parents'][x['parent']]['children'][-1]]
        self.endpoint.event(command, lease=x['receipt']['lease'], event='parent_consumer_accept')
        self.events['consumer'] += 1

    def reverse(self, *, die, SM, token, edge, CDC_receipt, drain_pins=None):
        key = (die, SM); x = self._owner(key, token)
        if (x['active'] is not None or x['held'] is not None or self.endpoint.live[key]['phase'] != 'PARENT_REVERSE'
                or not isinstance(CDC_receipt, dict)
                or set(CDC_receipt) != {'token','sender_domain','sender_edge','receiver_domain','receiver_edge'}
                or CDC_receipt['token'] != token or not CDC_receipt['sender_domain'] or not CDC_receipt['receiver_domain']
                or any(type(CDC_receipt[k]) is not int or CDC_receipt[k] < 0 for k in ('sender_edge','receiver_edge'))
                or CDC_receipt['receiver_domain'] != 'H1_streaming' or CDC_receipt['receiver_edge'] != edge):
            raise ValueError('matching source consumer, held sinks and explicit reverse CDC receipt')
        if (not isinstance(drain_pins, dict) or set(drain_pins) != set(self.atomic.DrainGate.SIGNALS)
                or any(type(v) is not bool for v in drain_pins.values())
                or any(drain_pins[n] for n in self.atomic.DrainGate.REQUESTS)
                or not all(drain_pins[n] for n in ('host_rd_ready','host_wr_ready','scratch_ready'))
                or any(drain_pins[n] for n in ('host_rsp_valid','host_ack_valid','simd_done','scratch_done'))):
            raise ValueError('actual individual completion sinks must drain before owner retirement')
        if self.drain_gates[key].phase != 'owned':
            raise ValueError('actual source drain owner still pending')
        self.ledger.observe(self._event(x['parent'], 'reverse', edge=edge, origin=x['origin']))
        command = self.child_to_command[self.bindings['parents'][x['parent']]['children'][-1]]
        self.endpoint.event(command, lease=x['receipt']['lease'], event='parent_reverse_lease_grant')
        gate = self.drain_gates[key]
        gate.release(gate.owner, all_completion_sinks_drained=True, reverse_grant=True)
        self.retired_tokens.add(token); del self.live[key]; self.events['parent_reverse'] += 1

    def summary(self):
        return dict(schema='HBM_POPPER_OWNER_COMPLETION_BINDING_R3', events=dict(self.events),
                    pending_parents=sum(len(v) for v in self.pending.values()),
                    live_SM_owners=len(self.live), held_completions=sum(x['held'] is not None for x in self.live.values()),
                    Popper_live_owners=len(self.endpoint.live), Popper_completed_commands=len(self.endpoint.completed),
                    SRAM_ledger=self.ledger.summary(), hardware_qualified=False,
                    production_physical_calls_closed=0, installed_owner_bridge=False,
                    HBM_command_inventory_bound=False, whole_token_latency=None,
                    C0_V1_I64_RF_mirror_provider_cost_recharged=False)

def directed_idle_pins(atomic):
    """Only verifier fixtures: no production always-ready service credit."""
    pins = {name: False for name in atomic.DrainGate.SIGNALS}
    for name in ('host_rd_ready','host_wr_ready','scratch_ready'): pins[name] = True
    return pins

def run_control():
    """All retained commands; opaque fixtures, never production payload proof."""
    join = ProductionOwnerJoin()
    tape = []
    original_observe = join.ledger.observe
    def observe(event):
        original_observe(event)
        record = dict(event)
        if 'data' in record:
            record['data_sha256'] = sha(record.pop('data'))
        tape.append(record)
    join.ledger.observe = observe  # Private instance only; pinned globals unchanged.
    for ordinal, p in enumerate(join.bindings['parents'].values()):
        command = join.parent_to_command[p['id']]
        # This is explicitly a directed fixture lease, not entering checkpoint
        # lease evidence. Production callers must pass their actual owner receipt.
        join.submit(command, receipt=join.receipt(command, lease=ordinal+1))
    edges = Counter()
    peak = 0
    while any(join.pending.values()):
        progress = False
        for die, SM in list(join.pending):
            token = join.admit_next(die=die, SM=SM, edge=edges[die,SM], origin='directed_verifier_control',drain_pins=directed_idle_pins(join.atomic))
            if token is None:
                continue
            progress = True; peak = max(peak, len(join.live))
            key = dict(die=die, SM=SM, token=token)
            x = join.live[die,SM]; p = join.bindings['parents'][x['parent']]
            edges[die,SM] += 1
            for child in p['children']:
                c = join.commands[join.child_to_command[child]]
                if join.endpoint.live[die,SM]['phase'] == 'MERGE':
                    join.merge(**key, payload=b'\x00\x00\xc0\x7f'*c['active_words'])
                d = join.bindings['children'][child]
                write_payload = bytes(range(64)) if d['kind']=='shared64' and d['write'] else None
                desc = join.issue(**key, edge=edges[die,SM], payload=write_payload)
                if not d['write']:
                    if d['kind']=='RF':
                        read_payload = (join.endpoint.live[die,SM]['merged']*2 if 'readback_pair' in child else bytes(range(256))*4)
                    else:
                        read_payload = bytes(range(64))
                for bank in d['expected_SRAMs']:
                    kw = dict(child=child, SRAM=bank, write=d['write'])
                    if d['write']:
                        kw['data'] = desc['payload'][bank[1]*32:bank[1]*32+32]
                    event = join._event(p['id'], 'SRAM_accept', edge=edges[die,SM], origin=x['origin'], **kw)
                    join.observe_SRAM(**key, completion_token=desc['completion_token'], event=event)
                edges[die,SM] += 1
                if not d['write']:
                    for index, bank in enumerate(d['expected_SRAMs']):
                        event = join._event(p['id'], 'SRAM_capture', edge=edges[die,SM], origin=x['origin'],
                                            child=child, SRAM=bank, data=read_payload[index*32:index*32+32])
                        join.observe_SRAM(**key, completion_token=desc['completion_token'], event=event)
                    edges[die,SM] += 1
                event = join._event(p['id'], 'child_ACK', edge=edges[die,SM], origin=x['origin'], child=child,valid=True,ready=True)
                join.observe_SRAM(**key, completion_token=desc['completion_token'], event=event)
                join.capture_completion(**key, completion_token=desc['completion_token'], payload=None if d['write'] else read_payload)
                # Every completion is captured while its next consumer is held.
                join.consume_completion(**key, ready=False)
                join.consume_completion(**key, ready=True)
                edges[die,SM] += 1
                join.reverse_child(**key, completion_token=desc['completion_token'], edge=edges[die,SM]); edges[die,SM] += 1
            join.visibility(**key, edge=edges[die,SM]); edges[die,SM] += 1
            join.consumer(**key, edge=edges[die,SM]); edges[die,SM] += 1
            join.reverse(**key, edge=edges[die,SM], CDC_receipt=dict(token=token, sender_domain='CORE',sender_edge=17,
                         receiver_domain='H1_streaming',receiver_edge=edges[die,SM]),drain_pins=directed_idle_pins(join.atomic));edges[die,SM]+=1
        if not progress:
            raise ValueError('source DAG continuation deadlock; preserve unresolved requests')
    result = join.summary()
    if (result['pending_parents'] or result['live_SM_owners'] or result['held_completions'] or result['Popper_live_owners']
            or result['SRAM_ledger']['physical_credit_debt'] or len(join.endpoint.completed)!=9504):
        raise ValueError('complete selected-owner control must retire every source child/parent')
    result.update(source_sha256=PINS, tested_parent_commands=352, tested_child_commands=10080,
                  tested_RF_RMW_parents=288, tested_shared64_children=9216,
                  all_selected_commands_replayed=True, sequential_control_peak_owned_SMs=peak,
                  fixture_lease_and_payloads=True, production_checkpoint_used=False,
                  program_physical_service_scope='DS retained all96 PC0 partial RMW; PC10 rank0 directed shared journal; not complete2213/1737 PC service',
                  H1_untagged_ACK_identity='retained sole accepted context; endpoint connection not installed',
                  source_offsets_are_not_backpressure_upper=True,
                  software_control_edge_ordinals_not_hardware_cycles=True,
                  missing=['current whole-program emitted contender/home/lease directory',
                           'installed atomic owner gate and HBM transport tag mapping',
                           'actual entering checkpoint lease and payload binding',
                           'bounded consumer/reverse/CDC/backend service and contextual SS/FF'],
                  incremental_physical_cost=None, interval_cost_mutation_performed=False)
    return result, tape

def reconcile_event_costs(nodes, *, program_sha256, positive_terms, retained_intervals, reuse_bindings, geometry):
    """Every exact node is paid positively or resolves a paid retained interval.

    Empty receipts mean UNKNOWN, never zero. A native execution frontier cannot
    be paid by a generic endpoint term: it needs its source-native recipe interval.
    This accounts by clock domain only; it does not schedule or convert to ns.
    """
    if len(program_sha256)!=64 or not geometry:
        raise ValueError('pinned program and actual port geometry required')
    by_id={node['id']:node for node in nodes}
    if len(by_id)!=len(nodes) or any(key not in by_id for key in reuse_bindings):
        raise ValueError('exact unique source movement node inventory')
    known=Counter(); missing=Counter(); reused=Counter(); identities=set()
    for node in nodes:
        phase=node['phase']; binding=reuse_bindings.get(node['id'])
        if binding is not None:
            if set(binding)!={'interval_id','interval_sha256','event_key'}:
                raise ValueError('exact retained interval receipt')
            interval=retained_intervals.get(binding['interval_id'])
            if interval is None or sha(canonical(interval))!=binding['interval_sha256']:
                raise ValueError('unresolved existing paid interval')
            event=interval['paid_events'].get(binding['event_key'])
            if (interval['program_sha256']!=program_sha256 or interval['geometry']!=geometry
                    or event is None or event['source_node_sha256']!=sha(canonical(node))
                    or event['phase']!=phase or type(event['cycles']) is not int or event['cycles']<=0
                    or not event['clock_domain'] or len(interval['source_sha256'])!=64):
                raise ValueError('paid interval source instruction/span/phase/geometry mismatch')
            identity=(binding['interval_id'],binding['event_key'])
            if identity in identities:raise ValueError('one paid event cannot cover multiple costs')
            identities.add(identity);reused[phase]+=1
            continue
        term=positive_terms.get(phase)
        if term is None:
            missing[phase]+=1
            continue
        if phase=='existing_native_calendar_frontier':
            raise ValueError('source-native recipe interval required; generic endpoint cost forbidden')
        if (set(term)!={'cycles','clock_domain','evidence_kind','source_sha256','geometry'}
                or type(term['cycles']) is not int or term['cycles']<=0
                or term['evidence_kind'] not in ('explicit_provisional_parameter','source_bound','measured_context_SS_FF')
                or term['geometry']!=geometry or not term['clock_domain']
                or len(term['source_sha256'])!=64):
            raise ValueError('positive explicitly sourced matching-geometry endpoint cost required')
        known[term['clock_domain']]+=term['cycles']
    return dict(status='UNKNOWN_UNPAID_SOURCE_EVENTS' if missing else 'ALL_EVENTS_ACCOUNTED_SOURCE_SCOPE_ONLY',
                source_events=len(nodes),missing_by_phase=dict(missing),reused_paid_events=dict(reused),
                incremental_known_edges_by_domain=dict(known),
                complete_incremental_edges_by_domain=None if missing else dict(known),
                automatic_zero_reuse=False,hardware_qualified=False,whole_token_ns=None)


def compile_current_metadata(plan):
    """Current Popper six-write metadata source order, distinct from old R1.

    Source read/write primitives remain opaque. This graph adds no native
    arithmetic event and never treats the existing RF write count as zero.
    """
    nodes=[];groups=set()
    def add(key, phase, deps, **fields):
        row=dict(id=key,phase=phase,dependencies=list(deps),**fields)
        nodes.append(row);return key
    for group in plan['groups']:
        key=tuple(group['key'])
        if key in groups or len(group['producer_vectors'])!=8 or len(group['metadata_writes'])!=6:
            raise ValueError('current72 groups/eight sourceRF vectors/six metadata writes')
        groups.add(key);prefix='Qwen.current_metadata.'+'.'.join(map(str,key));ACKs=[]
        for index,vector in enumerate(group['producer_vectors']):
            if vector['physical_mirrors']!=2 or not 0<=vector['RF_slot']<512 or not 0<=vector['SM']<32:
                raise ValueError('concrete current source two-copy RF producer home')
            common=dict(vector=index,die=group['die'],SM=vector['SM'],RF_slot=vector['RF_slot'],
                        provider_ref=vector['provider_ref'],version=vector['version'],source_birth_PC=vector['source_birth_PC'],
                        source_vector_sha256=sha(canonical(vector)))
            write=add(prefix+f'.v{index}.write','RF_both_copy_write', ['Qwen.PC%d.native'%vector['source_birth_PC']],
                      input_bytes=512,physical_write_bytes=1024,**common)
            ACKs.append(add(prefix+f'.v{index}.commonACK','RF_common_ACK',[write],ACK_pins=1,required_bank_go_observations=32,**common))
        previous=None;publish=None;reader=None;SCORES=None;PV=None
        for ordinal,op in enumerate(group['metadata_writes']):
            expected=('begin_header','commit_bitmap','commit_record','acquire_record','SCORES_record','PV_record')[ordinal]
            if op['ordinal']!=ordinal or op['operation']!=expected or op['address']%32 or not 0<op['mask']<2**32:
                raise ValueError('current source bitmap-before-record exact metadata identity')
            deps=ACKs if previous is None else [previous]
            if ordinal==3:
                publish=add(prefix+'.publish','KV_state_record_bitmap_fence',[previous],writer_exclusion=True)
                reader=add(prefix+'.acquire','KV_reader_acquire',[publish],reader_lease=group['reader_lease'])
                deps=[reader]
            if ordinal==4:
                SCORES=add(prefix+'.SCORES','KV_SCORES_consumer',[previous],reader_lease=group['reader_lease']);deps=[SCORES]
            if ordinal==5:
                PV=add(prefix+'.PV','KV_PV_consumer',[previous],reader_lease=group['reader_lease']);deps=[PV]
            for phase in ('KV_metadata_grant','KV_metadata_old_capture','KV_metadata_mask_merge','KV_metadata_write_visible','KV_metadata_consumer','KV_metadata_reverse'):
                previous=add(prefix+f'.m{ordinal}.'+phase,phase,deps,die=group['die'],ordinal=ordinal,
                             address=op['address'],byte_mask=op['mask'],patch_hex=op['patch_hex'],
                             provider_ref=op['provider_ref'],source_operation=op['operation'],
                             source_operation_sha256=sha(canonical(op)),old_valid_capture_required=op['old_valid_capture_required'])
                deps=[previous]
        add(prefix+'.reverse','KV_parent_reverse',[previous],reader_lease=group['reader_lease'])
    if len(groups)!=72:raise ValueError('all72 current source groups required')
    ids={n['id']for n in nodes};ordered=set()
    for n in nodes:
        if any(dep in ids and dep not in ordered for dep in n['dependencies']):
            raise ValueError('current source metadata topology')
        ordered.add(n['id'])
    return dict(schema='QWEN_CURRENT_POPPER_METADATA_SOURCE_BINDING_R3',nodes=nodes,
                phase_counts=dict(Counter(n['phase']for n in nodes)),source_groups=72,
                metadata_source_writes=432,source_RF_producer_vectors=576,source_combined_ACKs=576,
                old_R1_metadata_writes=144,old_R1_record_before_bitmap_not_adopted=True,
                source_metadata_order='begin header -> bitmap -> producer record -> acquire record -> SCORES record -> PV record',
                old_metadata_subgraph_replacement_required=True,old_payload_subgraph_reuse_unverified=True,
                source_metadata_bus_observed=plan['metadata_bus_observed'],production_consumer_receipts=plan['production_consumer_receipts'],
                actual_complete_owner_bridge=False,physical_costs=None,hardware_qualified=False)


BOUNDARY_PHASES = ('owner_admission','SRAM_acceptance','common_ACK','visibility',
                   'consumer','reverse','CDC_request','CDC_return','CDC_reverse',
                   'backend_wait','credit_return_wait')

def price_ds_boundaries(snapshot, profiles, clocks_hz):
    """Explicit configured endpoint cycles; never CPU ticks or inferred zero.

    Every boundary needs its source-resolved repetitions and every hold term.
    Output is a conditional additive chain estimate, never a production rate.
    Existing barrier remains paid; no owner/ACK overlap credit is inferred.
    """
    from fractions import Fraction
    rows=snapshot['boundaries'];ids={r['id'] for r in rows}
    if len(ids)!=len(rows) or any(k not in ids for k in profiles):
        raise ValueError('exact source critical-path boundary inventory')
    missing=Counter();delta_us=Fraction(0);domain_edges=Counter()
    for row in rows:
        profile=profiles.get(row['id'],{})
        if any(k not in BOUNDARY_PHASES for k in profile):raise ValueError('unknown boundary service term')
        for phase in BOUNDARY_PHASES:
            term=profile.get(phase)
            if term is None:
                missing[phase]+=1;continue
            if (set(term)!={'cycles','repetitions','clock_domain','source_sha256','evidence_kind','unit'}
                    or type(term['cycles'])is not int or term['cycles']<=0
                    or type(term['repetitions'])is not int or term['repetitions']<=0
                    or term['unit']!='configured_endpoint_cycles' or len(term['source_sha256'])!=64
                    or term['evidence_kind'] not in ('explicit_provisional_parameter','source_bound','measured_context_SS_FF')):
                raise ValueError('positive source repetitions/configured endpoint cycles; unknown is None')
            frequency=clocks_hz.get(term['clock_domain'])
            if type(frequency)is not int or frequency<=0:raise ValueError('explicit configured clock frequency required')
            cycles=term['cycles']*term['repetitions'];domain_edges[term['clock_domain']]+=cycles
            delta_us+=Fraction(cycles*1000000,frequency)
    complete=not missing
    base=Fraction(str(snapshot['baseline_exact_T_us']))
    return dict(schema='DS_CHAIN_BOUNDARY_CONDITIONAL_PRICE_R3',boundaries=len(rows),missing_terms_by_boundary=dict(missing),
                configured_known_edges_by_domain=dict(domain_edges),known_additive_service_us=float(delta_us),
                conditional_complete_service_us=float(delta_us) if complete else None,
                conditional_AR_total_us=float(base+delta_us) if complete else None,
                conditional_AR_rate= float(Fraction(1000000)/(base+delta_us)) if complete else None,
                actual_native_PC_boundary_join_complete=all(r['native_PC_join']is not None for r in rows),
                physical_admission=False,headline_replacement_allowed=False,production_rate=None,
                existing_barrier_receipt_preserved=True,unverified_overlap_credit=False,
                CPU_ticks_converted=False,MTP_iteration=False,measured_acceptance_assumed=False)


def ds_boundary_model(snapshot):
    from fractions import Fraction
    nb=len(snapshot['boundaries']);clock=Fraction(str(snapshot['baseline_clock_hz']));base=Fraction(str(snapshot['baseline_exact_T_us']))
    sensitivity=[]
    for cycles in (1,2,5,8,12,26,50):
        delta=Fraction(nb*cycles*1000000)/clock
        sensitivity.append(dict(uniform_cycles_per_boundary=cycles,conditional_delta_us=float(delta),
            conditional_AR_T_us=float(base+delta),conditional_AR_rate=float(Fraction(1000000)/(base+delta)),
            rate_loss_percent=float(100*delta/(base+delta)),scope='uniform sensitivity at legacy analytical clock; not actual configured endpoint service'))
    threshold=base/Fraction(99)/(Fraction(nb*1000000)/clock)
    return dict(schema='DS_BOUNDARY_HEADLINE_CONSUMER_DELTA_R3',source_boundary_census_sha256=sha(canonical(snapshot)),
        source_boundaries=nb,baseline_design=snapshot['baseline_design'],baseline_exact_T_us=snapshot['baseline_exact_T_us'],
        verified_published_baseline=snapshot['baseline_published_row'],baseline_clock_hz=snapshot['baseline_clock_hz'],
        missing_headline_terms=list(BOUNDARY_PHASES),current_complete_service=price_ds_boundaries(snapshot,{},{}),
        uniform_sensitivity=sensitivity,one_percent_rate_loss_uniform_cycles_threshold=float(threshold),
        headline_consumer='tools/uarch_model.py:v41_hbm_chain; missing owner/commonACK/visibility/reverse/CDC/stall phases',
        baseline_native_chain_is_AR_not_MTP=True,local_chat_or_pooled_acceptance_used=False,
        current_headline_modified=False,docs_modified=False,endpoint_cycles_not_measured_context=True,
        source_boundaries_are_not_a_full_native_PC_or_primitive_mapping=True)


def join_goodall_consumer_spans(requirements, native, plan, *, directory_sha256):
    """Resolve position-zero active words through retained r17 concrete homes.

    Source binding is independent of issued-SM or endpoint timing observations.
    No full-context allocation is charged as a position-zero payload transfer.
    """
    if requirements['directory_sha256'] != directory_sha256:
        raise ValueError('Goodall producer directory hash mismatch')
    config=native['source_program']['config']; TP=native['source_program']['TP']
    if (TP,config['num_attention_heads'],config['num_key_value_heads'],config['head_dim'])!=(2,32,8,128):
        raise ValueError('actual 16Q/4KV/head128 per-rank geometry required')
    operands={o['version']:o for o in native['operands']}
    plans={tuple(g['key']):g for g in plan['groups']}
    groups=[]; seen=set()
    for group in requirements['groups']:
        key=tuple(group['key'])
        if key in seen or key not in plans or key[2]!=0:
            raise ValueError('duplicate/unbound or non-position-zero production group')
        seen.add(key); rank=key[1]; current=plans[key]; chains=[]
        for expected,opcode in zip(group['source_consumer_chain'],('SCORES','EXP_SUM','PV'),strict=True):
            op=native['operations'][expected['pc']]
            if expected['opcode']!=opcode or any(op[k]!=expected[k] for k in ('pc','opcode','reads','writes','dependencies')):
                raise ValueError('actual native consumer instruction/version/dependency mismatch')
            contract=op['calendar_export']['provider_resource_contract']
            if (contract['SMs_per_rank'],contract['RF_slots_per_SM'],contract['RF_reads_bits'],contract['RF_mirrored_write_bits'])!=(32,512,8192,4096):
                raise ValueError('actual32SM SIMD128 RF port inventory required')
            recipe=op['loop_program']
            chains.append(dict(**expected,native_instruction_sha256=sha(canonical(op)),
                source_loop_program=recipe,kernel_templates_sha256=sha(canonical(native['microcode'])),
                active_primitive_repetitions=None,arithmetic_endpoint_receipt=None))
        active=[]; derived_sectors=set()
        for version in (chains[0]['reads'][1],chains[2]['reads'][1]):
            operand=operands[version]
            if operand['home_partition']!='block=global_word//256;SM=block%32;local=(block//32)*256+global_word%256':
                raise ValueError('retained native source address recipe mismatch')
            homes={h['SM']:h for h in operand['homes'] if h['rank']==rank}
            if len(homes)!=32 or sum(h['word_count']for h in homes.values())!=4194304:
                raise ValueError('allocated cache inventory mismatch')
            spans=[]
            for SM in (0,1):
                h=homes[SM]; home=h['home']
                if home['class']!='spill':raise ValueError('active native cache home must be spill')
                base=home['global_byte_base']
                for local in range(0,256,8):
                    derived_sectors.add((version,SM,base+4*local,h['provider_ref']))
                spans.append(dict(SM=SM,global_word_first=SM*256,local_word_first=0,words=256,
                    address=base,bytes=1024,sector32_transactions=32,provider_ref=h['provider_ref'],
                    lease=operand['lease'],release_after=operand['release_after'],source_home_sha256=sha(canonical(h))))
            inv=group['version_home_inventory'][version]
            if inv['allocated_words']!=4194304:raise ValueError('Goodall allocated extent mismatch')
            active.append(dict(version=version,allocated_words=4194304,allocated_bytes=16777216,
                active_FP32_words=512,active_FP32_bytes=2048,active_U8_bytes=512,
                sector32_transactions=64,active_SMs=[0,1],spans=spans))
        source_sectors={(x['version'],x['SM'],x['address'],x['provider_ref'])for x in current['decoded_sectors']}
        if source_sectors!=derived_sectors:raise ValueError('active decoded sector source address/ref mismatch')
        for vector in current['producer_vectors']:
            operand=operands[vector['version']]
            matches=[h for h in operand['homes']if h['rank']==rank and h['SM']==vector['SM'] and h['provider_ref']==vector['provider_ref']]
            if len(matches)!=1:raise ValueError('producer RF home/ref mismatch')
            home=matches[0]['home']
            if home['class']!='RF' or not home['slot_first']<=vector['RF_slot']<home['slot_first']+home['vectors'] or vector['physical_mirrors']!=2:
                raise ValueError('producer both-RF slot/mirror mismatch')
        groups.append(dict(key=list(key),consumer_chain=chains,active_cache_mapping=active,
            source_producer_vectors=current['producer_vectors'],decoded_sector32_transactions=128,
            K_partial_old_capture_transactions=group['partial_sectors'],
            V_full_sector_transactions=group['full_sectors'],
            producer_common_ACK_observed=False,issuing_SM_observed=None,
            source_address_binding=True,actual_issuer_receipt=False))
    if len(groups)!=72 or seen!=set(plans):raise ValueError('complete72 group binding required')
    return dict(schema='QWEN_SOURCE_BOUND_ACTIVE_CONSUMER_SPANS_R3',groups=groups,
        group_count=72,native_consumer_instructions=216,
        geometry=dict(query_heads_per_rank=16,KV_heads_per_rank=4,head_dim=128,SIMD=128,SMs=32,TP=2),
        decoded_sector32_transactions=9216,producer_RF_vectors=576,physical_RF_mirrors=2,
        old_K_tail_capture_transactions=18432,unwritten_old_K_tail_bytes=552960,
        metadata_contract_conflict=dict(Goodall_required='record_before_bitmap',
            current_Popper_source='bitmap_before_record',resolved=False,
            adoption_allowed=False,action='producer/consumer owners must agree exact source publication contract'),
        representative_gate=dict(scope='one actual layer/rank position-zero full-geometry chain',
            endpoint_cost_profiles=None,active_arithmetic_repetitions=None,
            inputs='actual checkpoint query and prepack operands; source-captured initialized old tails',
            required_receipts=['producer bothRF commonACK','native FP8 packing','old-sector capture',
                'backend visibility','child consumption','validated reverse','metadata publication',
                'SCORES_EXP_SUM_PV arithmetic source steps','output publication','parent reverse'],
            archive_harness_completion_credit=False,ready_for_full_token_RTL=False),
        hardware_qualified=False,whole_token_ns=None)


def current_consumer_join():
    def load(path):
        raw=(ROOT/path).read_bytes()
        if sha(raw)!=PINS[path]:raise ValueError('current consumer source pin: '+path)
        return json.loads(gzip.decompress(raw)if path.endswith('.gz')else raw)
    requirements=load(OUT+'/inputs/Goodall_requirements.json')
    native=load('results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz')
    plan=load(OUT+'/inputs/KV_current_plan.json.gz')
    manifest=json.loads((ROOT/'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1_inputs/manifest.json').read_bytes())
    # Compare against the retained Popper directory bytes, not the packet itself.
    directory=manifest['directory.json.gz']['sha256']
    if sha((ROOT/'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1_inputs/directory.json.gz').read_bytes())!=directory:
        raise ValueError('retained Popper producer directory source pin')
    return join_goodall_consumer_spans(requirements,native,plan,directory_sha256=directory)


def composition_model():
    import ast
    archive=ROOT/OUT/'inputs'
    for name in ('audit.json','audit.md','uarch_model.py','fifo2.sv','C0_owner_addressed.py','KV_current_owner.py','KV_current_plan.json.gz','zero_classification.json','dependency_fields.json','codex_notes.txt','hbm_gpu.json','V1_serialized_owner.py','DS_chain_boundaries.json'):
        path=archive/name
        if sha(path.read_bytes())!=PINS[str(path.relative_to(ROOT))]:
            raise ValueError('coordinated audit/model source pin')
    audit=json.loads((archive/'audit.json').read_bytes())
    classification=json.loads((archive/'zero_classification.json').read_bytes())
    boundary_snapshot=json.loads((archive/'DS_chain_boundaries.json').read_bytes())
    constants={}
    for n in ast.parse((archive/'uarch_model.py').read_bytes()).body:
        if isinstance(n,ast.Assign):
            for target in n.targets:
                if isinstance(target,ast.Name) and target.id in ('DFF_UM2','GPU_LOGIC_UTIL'):
                    constants[target.id]=ast.literal_eval(n.value)
    fifo=(archive/'fifo2.sv').read_text()
    if 'mem[0:1]' not in fifo or 'reg [1:0] wb,wg,rb,rg,rgw1,rgw2,wgr1,wgr2' not in fifo:
        raise ValueError('literal two-entry Gray FIFO storage source changed')
    # Full owner fields from R2; no narrowing and no existing-storage reuse credit.
    owner_bits=324; SMs=32; banks=4*8; PCs=128; clients=6; credits=16
    widths=dict(request=32+256+35+owner_bits+2,response=256+35+owner_bits+1,
                write_completion=35+owner_bits+1,reverse=35+owner_bits+1)
    reservations=dict(SM_and_bank_owners=(SMs+banks)*owner_bits,
                      accepted_PC_contexts=PCs*clients*credits*owner_bits,
                      CDC_FIFO_payload_and_control=PCs*(2*sum(widths.values())+4*26),
                      held_SM_completion_payload_and_valid=SMs*(1024*8+2))
    total=sum(reservations.values());native=ROOT/'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1/final_causal/Qwen_KV_finite_DAG.json.gz'
    dag=json.loads(gzip.decompress(native.read_bytes()))
    manifest=json.loads((ROOT/'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1_inputs/manifest.json').read_bytes())
    native_program_sha=manifest['Qwen_tiled.json.gz']['sha256']
    current_metadata=compile_current_metadata(json.loads(gzip.decompress((archive/'KV_current_plan.json.gz').read_bytes())))
    current_costs=reconcile_event_costs(current_metadata['nodes'],program_sha256=native_program_sha,positive_terms={},retained_intervals={},reuse_bindings={},geometry='comparator_sector32_shared64_RFtwo_copies')
    costs=reconcile_event_costs(dag['nodes'],program_sha256=native_program_sha,positive_terms={},retained_intervals={},reuse_bindings={},geometry='comparator_sector32_shared64_RFtwo_copies')
    steps=[
        dict(id='M0',owner='Popper/calendar',action='Prioritize exact329 DS critical-path boundary owner/ACK/CDC/stall pricing with price_ds_boundaries; freeze selected owner, PC completion and CDC port inventory; source-pin the current model and bind exact native/RF/provider paid interval receipts.',delivered='R3 actual SelectedEndpoint and DrainGate composition; every per-bank byte checked; unreceipted prices UNKNOWN'),
        dict(id='M1',owner='Popper/calendar',action='Common-ACK successor for C0/V1: register full accepted owner, derive both-copy go observations, consume one commonACK; reject two timed mirror ACK prices and remove default zero stalls.',inputs=['current C0/V1 emitted command identity','actual H1 write_go/ACK traces','paid RF/C0/V1 interval map'],gate='actual owner trace parity, wrong generation/lease, duplicate ACK, held-ready; once-only cost replacement'),
        dict(id='M2',owner='Popper/calendar',action='Model one all-class rotating SM/bank owner gate and exact accepted PC tag/gen/direction table, held completion storage and fault admission; bind C0/SIMD/matrix/KV/L2 actual contender DAG.',inputs=['installed physical rank/SM/bank homes','whole-program source contender/lease journal','backend accepted tag provenance'],gate='finite capacity, alias and premature reuse rejection; actual finite contender exhaustion or priced fair successor; complete gate/mux/fanout/cuts/context area'),
        dict(id='M3',owner='Popper/Kepler/calendar',action='Join old-sector validity/capture, masked KV writes, writer exclusion and metadata visibility to the same owner; implement generic L2 word service software driver over existing source BankFence.',inputs=['actual entering checkpoint sector bytes/validity','all72 observed Qwen groups','actual L2 bank reservation','21 positive KV phase terms or exact paid receipts'],gate='18432 old partial-K captures and all39168 sector child reverses; reference-order metadata fence resolved with producer before adoption; no invented full-valid sector'),
        dict(id='M4',owner='Popper/calendar',action='Price request/return/write-completion/reverse CDC FIFO and reset/clock bridges in actual comparator context; source-map both-domain receipts before enabling any RTL.',inputs=['selected widths and2-entry depth here','actual domain/clock/reset configuration','finite sender/receiver sink and credit terms'],gate='capacity/backpressure/reverse trace plus actual context SS/FF/ports/routing; no software tick conversion'),
        dict(id='M5',owner='Sagan/Kepler/calendar',action='Replay actual full native program movement journal through the selected owners; prove actual retirement/aging and reconcile old intervals once before composing complete token calendar.',inputs=['DS2213/Qwen1737 source-native recipe expansions','actual owner/ref/span and issued-SM journals','M1..M4 admitted costs'],gate='all PC/micro-op source resolution, common ACK, causal visibility/consume/reverse, finite global/rank resources; every unbound term remains UNKNOWN'),
        dict(id='M6',owner='Popper/parent; Claude independently W1 only',action='Only after full selected owner sizing and CDC/port/cut/latency composition, prepare default-off W2..W13 RTL successors only after model gates; Claude owns independent W1 disabled-output hygiene.',inputs=['M0..M5 complete reviewed model'],gate='originals immutable; opt-in zero; correct ENABLE0/1 lint; golden exact/context SSFF; measured gain before adoption'),
    ]
    return dict(schema='HBM_COORDINATED_OWNER_COMPLETION_IMPLEMENTATION_MODEL_R3',audit_main=audit['main'],audit_sha256=sha((archive/'audit.json').read_bytes()),
                source_pins=PINS,model_before_RTL=True,RTL_build_allowed=False,
                selected_scope='actual96 PC0 partialRF publications; retained directed PC10 rank0 shared; no whole-comparator owner bridge',
                source_program_counts=dict(DeepSeek=2213,Qwen=1737),
                Qwen_KV_native_program_sha256=native_program_sha,Qwen_KV_DAG_sha256=sha(native.read_bytes()),
                Qwen_KV_historical_cost_reconciliation=costs,
                current_metadata_binding={k:v for k,v in current_metadata.items()if k!='nodes'},
                Goodall_consumer_binding={k:v for k,v in current_consumer_join().items()if k!='groups'},
                current_metadata_cost_reconciliation=current_costs,
                KV_phase_costs_missing=21,structural_retire_and_native_interval_receipts_missing=True,
                audited_zero_classification=[dict(id=row['id'],classification=row['classification'],where=row['where'])for row in classification['zeros']],
                audit_correction='No flagged zero changes a current headline/gate. Missing DS chain owner/ACK/CDC/stall terms are the headline omission. C0 serialized timing already charges ACK once; HDC PC reference is not installed comparator.',
                headline_consumer_omission='tools/uarch_model.py:v41_hbm_chain has no complete owner/commonACK/visibility/reverse/CDC/stall term',
                DS_chain_boundary_pricing=ds_boundary_model(boundary_snapshot),
                source_common_ACK=dict(RF_copies=2,banks_per_copy=16,write_go_shared=True,host_ACK_pins=1,
                                       C0_V1_protocol_shape_two_calls_requires_common_ACK_adapter=True,
                                       C0_V1_serialized_time_already_charged_once=True,
                                       two_independent_ACK_latency_charge_not_adopted=True,source_ACK_tags_present=False,
                                       R3_receipt_token_is_retained_context_not_wire_authentication=True),
                r14_default_off=dict(commit_ready_implicit=True,commit_r_undriven=True,source_modified=False,owner='Claude independent W1',gate='separate pinned default-off hygiene successor; no ENABLE1 timing credit'),
                owner_candidate=dict(installed=False,selected_hardware_field_spec_complete=False,
                    sizing_scope='untrimmed software-key conservative reference envelope, not minimal physical owner design',
                    one_bit_generation_or_16bit_tag_reduction_adopted=False,entry_bits=owner_bits,SM_owners=SMs,bank_owners=banks,
                    accepted_PC_contexts=PCs*clients*credits,reservation_bits=reservations,total_additional_register_bits=total,
                    all_storage_reuse_uncredited=True,dictionary_and_combinational_logic_area=None,
                    DFF_um2_assumed=constants['DFF_UM2'],utilization_assumed=constants['GPU_LOGIC_UTIL'],
                    register_cell_area_um2_assumed=total*constants['DFF_UM2'],
                    register_footprint_mm2_assumed=total*constants['DFF_UM2']/constants['GPU_LOGIC_UTIL']/1e6,
                    Qwen_PC_geometry_source='HDC ROM-core bench reference only; not comparator connection',DS_shared_PC_geometry='UNBOUND_DO_NOT_INHERIT_QWEN',adopted=False),
                boundaries=dict(CDC_bits_per_word=widths,CDC_FIFO_depth_each=2,CDC_control_bits_per_fifo=26,
                    CDC_channels_per_PC=4,CDC_PC_replicas=PCs,
                    source_RF_read_bits_per_SM=8192,source_RF_write_input_bits_per_SM=4096,
                    source_RF_written_bits_both_copies=8192,source_shared_transaction_bits=512,
                    SM_replicas_per_die=SMs,RF_BANK_replicas_per_SM=32,
                    source_existing_data_port_reuse_receipt=None,new_shared_data_crossbar_credited=False,
                    mux_demux_and_fanout_area=None,full_tracks_and_channel_fit=None,
                    contextual_clock_reset_and_SS_FF=None,complete_latency_by_domain=None),
                finite_waits=dict(backend_gap=None,credit_return=None,consumer=None,reverse=None,CDC=None,
                    actual_program_priority_starvation_reachable=None,
                    selected_control_finite_exhaustion_is_not_production_fairness=True),
                implementation_steps=steps,full_owner_bridge=False,zero_placeholder_adopted=False,
                TP96_literal64B_geometry_to_wide_product_rate=False,whole_token_ns=None,hardware_qualified=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--skip-r1-replay', action='store_true', help='R3-only replay; default also selects committed R1 final_causal explicitly')
    args = parser.parse_args()
    if not args.skip_r1_replay:
        import subprocess
        import sys
        subprocess.run([sys.executable, str(ROOT/'tools/h3_complete_native_calendar_grants_r1.py'),
                        '--out', str(ROOT/'results/uarch/h3_complete_native_calendar_20261002/causal_grants_r1/final_causal'), '--verify'], check=True)
    result, tape = run_control()
    outputs = {'active_consumer_binding.json.gz':gzip.compress(canonical(current_consumer_join()),mtime=0),
               'summary.json': json.dumps(result, sort_keys=True, indent=2).encode()+b'\n',
               'SRAM_control_events.json.gz': gzip.compress(canonical(tape), mtime=0),
               'composition_model.json':json.dumps(composition_model(),sort_keys=True,indent=2).encode()+b'\n',
               'current_metadata_binding.json.gz':gzip.compress(canonical(compile_current_metadata(json.loads(gzip.decompress((ROOT/OUT/'inputs/KV_current_plan.json.gz').read_bytes())))),mtime=0)}
    base = ROOT/OUT
    for name, raw in outputs.items():
        path = base/name
        if args.verify:
            if path.read_bytes()!=raw: raise ValueError('source-owner control replay changed: '+name)
        else:
            base.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes()!=raw: raise ValueError('historical output overwrite refused: '+name)
            path.write_bytes(raw)
    print('PASS Popper selected-owner composition352 parents/10080 children; production physical service UNKNOWN')

if __name__ == '__main__':
    main()
