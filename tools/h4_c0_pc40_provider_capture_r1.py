#!/usr/bin/env python3
"""Default-off original-provider publication/read capture for the joint run.

This creates no provider, owner55 adapter, numerical prefix, or RTL. Attach
observe_publication to the existing producer observer, then use read_pair at
the existing PC40 caller before NEG/exp. Source page observations are software
provider evidence; they never stand for installed RF/NoC handshakes.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/c0_pc40_payload_lease_20261003'
VERSION = 'Qwen.39.L0.d0.gu_post.49'
HOMES = {'gate': (0, ('RF', 0, 0, 38)), 'up': (6144, ('RF', 0, 24, 32))}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def source_guard(module, store):
    row = next(x for x in json.loads((BASE / 'numeric_input_manifest_r1.json').read_text())
               if x['source_path'] == 'tools/h3_qwen_bounded_native.py')
    origin = Path(module.__file__).resolve()
    raw = origin.read_bytes()
    require(sha(raw) == row['sha256'], 'exact released provider source bytes')
    allowed = tuple(getattr(module, name) for name in ('TileWords', 'AddressedTileWords'))
    require(type(store) in allowed, 'exact original source class, no subclass/MRO exemption')
    compiled = compile(raw, str(origin), 'exec')
    cls = next(c for c in compiled.co_consts if getattr(c, 'co_name', None) == 'TileWords')
    for name in ('key', 'write', 'publish', 'read', 'read_indices', 'retire'):
        expected = next(c for c in cls.co_consts if getattr(c, 'co_name', None) == name)
        require(getattr(module.TileWords, name).__code__ == expected,
                'unchanged source method ' + name)
    if type(store) is module.AddressedTileWords:
        cls = next(c for c in compiled.co_consts if getattr(c, 'co_name', None) == 'AddressedTileWords')
        for name in ('write', 'read_indices', 'retire'):
            expected = next(c for c in cls.co_consts if getattr(c, 'co_name', None) == name)
            require(getattr(module.AddressedTileWords, name).__code__ == expected,
                    'unchanged addressed source method ' + name)
    return dict(source_path=row['source_path'], sha256=row['sha256'],
                class_name=type(store).__name__, exact_class_and_methods=True)


class PublicationCapture:
    def __init__(self, module, directory, *, enabled=False):
        require(enabled, 'provider capture default off')
        self.module = module
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.store = None
        self.record = None

    def owned_page(self, store, name):
        start, expected = HOMES[name]
        require(VERSION in store.live and VERSION in store.published, 'live held publication')
        require(store.values[VERSION]['retire_pc'] == 40, 'actual entire-PC40 publication lifetime')
        require(store.shapes[VERSION] == ((12288,), 'F32'), 'actual source tensor dtype/aperture')
        key, lane = store.key(VERSION, start, 0)
        require(key == expected and lane == 0, 'source-bound rank/SM/RF coordinate')
        require(store.owners.get(key) == VERSION, 'actual source page owner')
        copies = store.pages[key]
        require(len(copies) == 2 and all(p.dtype.name == 'uint32' and p.shape == (128,) for p in copies),
                'both full original RF page mirrors')
        raw = [p.astype('<u4', copy=False).tobytes() for p in copies]
        require(raw[0] == raw[1], 'actual source mirror bytes agree')
        return raw[0], dict(source_key=list(key), word_start=start, words=128,
                           version=VERSION, lease='value:' + VERSION,
                           published=True, owner_held=True,
                           software_mirror_sha256=[sha(x) for x in raw])

    def observe_publication(self, op, store):
        if op['pc'] != 39:
            return False
        require(self.record is None, 'capture publication exactly once')
        require(op['opcode'] == 'SCALAR_MUL' and op['writes'] == [VERSION], 'actual PC39 source producer')
        identity = source_guard(self.module, store)
        frames = {}
        for name in HOMES:
            raw, owner = self.owned_page(store, name)
            filename = name + '_publication.bin'
            (self.directory / filename).write_bytes(raw)
            frames[name] = dict(file=filename, bytes=512, sha256=sha(raw), **owner)
        # These are actual software provider owners. An independent installed
        # bridge workspace lease manager is not inferred from an empty slot.
        owners = [dict(source_key=list(k), version=v, lease='value:' + v)
                  for k, v in sorted(store.owners.items())
                  if k[0] == 'RF' and k[1] == 0 and k[2] in (0, 24)]
        self.store = store
        self.record = dict(schema='C0_PC40_ORIGINAL_PROVIDER_PUBLICATION_R1',
                           source_identity=identity, PC39_published=True,
                           frames=frames, actual_owned_RF_pages=owners,
                           publication_event_present=any(e.get('event') == 'publish' and e.get('version') == VERSION
                                                         for e in store.events),
                           selected_workspace_source_owners={str(s): store.owners.get(('RF', 0, 0, s))
                                                             for s in (17, 18, 19)},
                           installed_workspace_lease_observed=False,
                           source_write_scope='observed post-write both-mirror page state; not physical write ACK',
                           hardware_admitted=False)
        require(self.record['publication_event_present'], 'actual original publication event')
        (self.directory / 'publication.json').write_bytes(canonical(self.record))
        return True

    def read_pair(self, store):
        require(store is self.store and self.record is not None, 'same actual source store and publication')
        require(not (self.directory / 'caller_reads.json').exists(), 'ordered caller reads exactly once')
        source_guard(self.module, store)
        require((store.worker_rank, store.worker_SM) == (0, 0), 'actual caller rank0/SM0')
        result = []
        events = []
        for name, (start, _) in HOMES.items():
            before = {k: store.counters[k] for k in ('RF_read', 'source_read_payload_bits', 'NoC_source_read_bits')}
            value = store.read(VERSION, start, 128)
            require(value.dtype.name == 'float32' and value.shape == (128,), 'source actual caller F32 vector')
            raw = value.astype('<f4', copy=False).tobytes()
            owner_raw, owner = self.owned_page(store, name)
            require(raw == owner_raw and sha(raw) == self.record['frames'][name]['sha256'],
                    'caller read matches retained publication bytes')
            filename = name + '_caller.bin'
            (self.directory / filename).write_bytes(raw)
            delta = {k: store.counters[k] - before[k] for k in before}
            events.append(dict(sequence=len(events), role=name, file=filename, bytes=512,
                               sha256=sha(raw), software_provider_counter_delta=delta, **owner))
            result.append(value)
        # A prior observer may leave a source page cached: record the original
        # cache hit honestly, without asserting a new physical transaction.
        (self.directory / 'caller_reads.json').write_bytes(canonical(dict(
            schema='C0_PC40_SOURCE_ORDERED_GATE_UP_READ_R1', events=events,
            order=['gate', 'up', 'NEG', 'exp.step0 FMAX'],
            next_arithmetic_not_executed_by_capture=True, oracle_input_injection=False,
            software_provider_reads_observed=True, installed_RF_handshake_observed=False,
            installed_NoC_delivery_observed=False, source_publication_retained=True,
            source_release_inferred=False, owner55_adapter_created=False, hardware_admitted=False)))
        return tuple(result)
