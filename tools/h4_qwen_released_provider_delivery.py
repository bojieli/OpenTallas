#!/usr/bin/env python3
"""Live canonical Qwen provider delivery into the joint RTL transport.

Attach to the original released runtime before machine.run. Every immutable
byte read, RF/HBM page write/read, publication and retirement then crosses
the transport. No saved activation, numerical oracle, class replacement or
owner55 packing is used. The full-system owner supplies the RTL transport and
native instruction dispatcher; this module supplies their live source data.
"""
import argparse
import copy
import hashlib
import json
import socket
import sys
from pathlib import Path
from types import MethodType
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / 'results/uarch/c0_pc40_payload_lease_20261003/numeric_input_manifest_r1.json'
PROGRAM_SHA = 'ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354'
IMAGE_SHA = '83491cd2487ec026e86b5943e0420a4efcb6830aaf35f761e20190a469fd69e7'


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_program(native):
    require(sha(canonical(native)) == PROGRAM_SHA, 'complete canonical released program identity')
    ops = native['operations']
    require(len(ops) == 1737 and [o['pc'] for o in ops] == list(range(1737)), 'complete1737 source PCs')
    require(native['source_program']['config']['num_hidden_layers'] == 36, 'complete36 source layers')
    require(sum(o['opcode'] == 'SILU_GATE' for o in ops) == 72, 'all36layers/two-rank source SILU callers')
    return ops


def emit_program(native, path):
    """Driver input: all canonical commands/recipes/homes, no reduced model."""
    validate_program(native)
    Path(path).write_bytes(canonical(native))


def exact_module(module, source_path):
    row = next(p for p in json.loads(PINS.read_text()) if p['source_path'] == source_path)
    require(sha(Path(module.__file__).read_bytes()) == row['sha256'], 'original source module ' + source_path)


def wire_encode(value):
    if type(value) is bytes:
        return {'source_bytes_hex': value.hex()}
    if isinstance(value, (np.ndarray, np.generic)):
        array = np.asarray(value)
        return {'source_array': dict(dtype=array.dtype.str, shape=list(array.shape),
                                     bytes_hex=array.tobytes().hex())}
    if isinstance(value, dict):
        return {k:wire_encode(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [wire_encode(v) for v in value]
    return value


def wire_decode(value):
    if isinstance(value, dict):
        if set(value) == {'source_bytes_hex'}:
            return bytes.fromhex(value['source_bytes_hex'])
        if set(value) == {'source_array'}:
            row=value['source_array']
            return np.frombuffer(bytes.fromhex(row['bytes_hex']),dtype=np.dtype(row['dtype'])).reshape(row['shape']).copy()
        return {k:wire_decode(v) for k,v in value.items()}
    if isinstance(value, list):
        return [wire_decode(v) for v in value]
    return value


class UnixRTLTransport:
    """Client of the existing whole-system simulator, never a new simulator job.

    The owner implements source_page_write/read, source_publish/retire,
    immutable_source_transfer and native_primitive on its actual RTL ports.
    Reply bytes come from that simulator; this client has no execution oracle.
    """
    def __init__(self, socket_path, native_dispatch_program_sha256):
        require(native_dispatch_program_sha256 == PROGRAM_SHA, 'canonical dispatcher identity')
        self.native_dispatch_program_sha256 = native_dispatch_program_sha256
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(str(socket_path))
        self.stream = self.socket.makefile('rwb')

    def transact(self, kind, request):
        line = json.dumps(wire_encode(dict(kind=kind,request=request)),separators=(',',':')).encode() + b'\n'
        self.stream.write(line); self.stream.flush()
        reply = self.stream.readline()
        require(reply, 'actual RTL driver return, no EOF completion')
        return wire_decode(json.loads(reply))

    def close(self):
        self.stream.close(); self.socket.close()


def stop_on_fault(method):
    def guarded(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except BaseException:
            self.stopped = True
            self.pending = True
            raise
    return guarded


class ReleasedProviderDelivery:
    """One outstanding live delivery, with original runtime classes retained.

    transport.transact(kind, request) is the joint RTL driver's synchronous
    port service. It must return the same sequence/program/PC plus held-owner
    receipts and actual returned bytes. No bare valid or unit-idle predicate
    is accepted as publication/retirement. Popper owns its physical owner ABI.
    """
    def __init__(self, native_module, byte_module, machine, transport, *, enabled=False):
        require(enabled, 'released provider delivery default off')
        exact_module(native_module, 'tools/h3_qwen_bounded_native.py')
        exact_module(byte_module, 'tools/qwen_trained_byte_provider.py')
        require(type(machine) is native_module.TiledMachine, 'exact released machine class')
        require(type(machine.store) is native_module.TileWords, 'exact released source storage class')
        require(type(machine.weights) is native_module.HBMByteTileProvider, 'exact released raw-byte consumer')
        require(type(machine.weights.backend) is byte_module.TrainedByteBackend, 'exact released checkpoint backend')
        require(type(machine.vm) is native_module.NativePrimitiveVM, 'exact released native VM class')
        self.ops = validate_program(machine.native)
        self.machine = machine
        self.store = machine.store
        self.backend = machine.weights.backend
        require(sha((self.backend.directory / 'manifest.json').read_bytes()) == IMAGE_SHA,
                'qualified released checkpoint images')
        require(not self.store.live and not self.backend.active, 'attach before any source run')
        self.transport = transport
        self.sequence = 0
        self.pending = False
        self.stopped = False
        self.attached = False
        self.counts = {}
        self.original = {}
        self.native_module = native_module
        self.actual_read_cache = None

    def exchange(self, kind, **payload):
        require(not self.pending and not self.stopped, 'one live delivery, fault blocks further grants')
        pc = self.machine.current_pc
        request = dict(program_sha256=PROGRAM_SHA, source_PC=pc, sequence=self.sequence, **payload)
        self.sequence += 1
        self.pending = True
        try:
            response = self.transport.transact(kind, request)
            require(isinstance(response, dict), 'joint RTL response object')
            for k in ('program_sha256', 'source_PC', 'sequence'):
                require(response.get(k) == request[k], 'matched current RTL delivery ' + k)
            require(response.get('accepted') is True and response.get('fault') is False,
                    'actual accepted fault-free delivery')
            self.counts[kind] = self.counts.get(kind, 0) + 1
            return response
        except BaseException:
            self.stopped = True
            # Retain pending debt after fault. No implicit reuse/rearm.
            raise
        finally:
            if not self.stopped:
                self.pending = False

    def page_record(self, key, version):
        require(self.store.owners.get(key) == version, 'current source publication owner')
        copies = self.store.pages[key]
        raw = copies[0].astype('<u4', copy=False).tobytes()
        require(len(raw) == 512 and all(p.astype('<u4', copy=False).tobytes() == raw for p in copies),
                'source page size and RF mirrors')
        return dict(source_key=list(key), version=version, lease='value:' + version,
                    mirrors=len(copies), payload_sha256=sha(raw), payload=raw)

    def checked_owner(self, response, record):
        for key in ('source_key', 'version', 'lease'):
            require(response.get(key) == record[key], 'actual held publication ' + key)
        require(response.get('owner_retained') is True, 'hold source owner')

    @stop_on_fault
    def write(self, version, start, values):
        self.actual_read_cache = None
        self.original['write'](version, start, values)
        keys = set()
        for rank in sorted({h['rank'] for h in self.store.values[version]['homes']}):
            for word in range(start, start + np.size(values)):
                keys.add(self.store.key(version, word, rank)[0])
        for key in sorted(keys):
            record = self.page_record(key, version)
            response = self.exchange('source_page_write', **record)
            self.checked_owner(response, record)
            require(response.get('payload_sha256') == record['payload_sha256'] and
                    response.get('visible_copies') == record['mirrors'], 'actual all-copy write ACK')

    @stop_on_fault
    def read_indices(self, version, indices):
        expected = self.original['read_indices'](version, indices)
        indexes = np.asarray(indices, dtype=np.int64).reshape(-1)
        rank = self.store.rank(version)
        coordinates = [self.store.key(version, int(i), rank) for i in indexes]
        words = []
        for key, lane in coordinates:
            record = self.page_record(key, version)
            cache = getattr(self, 'actual_read_cache', None)
            if cache is not None and cache[:2] == (key, version):
                require(sha(cache[2]) == record['payload_sha256'], 'held actual source capture cache')
                words.append(np.frombuffer(cache[2], dtype='<u4')[lane])
                continue
            request = {k: v for k, v in record.items() if k != 'payload'}
            response = self.exchange('source_page_read', **request,
                                     destination_rank=self.store.worker_rank,
                                     destination_SM=self.store.worker_SM,
                                     remote=(key[1], key[2]) != (self.store.worker_rank, self.store.worker_SM))
            self.checked_owner(response, record)
            raw = response.get('payload')
            require(type(raw) is bytes and len(raw) == 512 and sha(raw) == record['payload_sha256'],
                    'actual returned source page bytes')
            require(response.get('captured') is True, 'actual caller page capture')
            self.actual_read_cache = (key, version, raw)
            words.append(np.frombuffer(raw, dtype='<u4')[lane])
        bits = np.array(words, dtype=np.uint32)
        returned = bits.view(np.float32) if expected.dtype == np.float32 else bits
        require(returned.dtype == expected.dtype and returned.tobytes() == expected.tobytes(),
                'native caller input bit exact against current source publication')
        return returned.copy()

    @stop_on_fault
    def publish(self, version, value=None):
        keys = sorted(k for k, v in self.store.owners.items() if v == version)
        owners = [self.page_record(k, version) for k in keys]
        request = dict(version=version, lease='value:' + version,
                       source_pages=[{k:v for k,v in r.items() if k != 'payload'} for r in owners],
                       source_control=value if not keys else None,
                       retire_PC=self.store.values[version]['retire_pc'])
        response = self.exchange('source_publish', **request)
        require(response.get('version') == version and response.get('lease') == request['lease']
                and response.get('all_writes_visible') is True and response.get('owner_retained') is True,
                'source publication after actual all-copy visibility')
        self.original['publish'](version, value)

    @stop_on_fault
    def retire(self, pc):
        versions = sorted(v for v in self.store.live if self.store.values[v]['retire_pc'] == pc)
        if versions:
            response = self.exchange('source_retire', versions=versions,
                                     leases=['value:' + v for v in versions], retire_PC=pc)
            require(response.get('versions') == versions and response.get('all_consumers_accepted') is True
                    and response.get('all_reverse_validated') is True and response.get('all_copies_drained') is True,
                    'source retirement waits actual consumer/reverse/all-copy drain')
        self.original['retire'](pc)
        self.actual_read_cache = None

    @stop_on_fault
    def immutable_read(self, request):
        source = self.original['read_tile_bytes'](request)
        response = self.exchange('immutable_source_transfer', source_request=copy.deepcopy(request),
                                 source_payloads=source['payloads'])
        for key in ('provider_ref', 'lease', 'state', 'reverse_grant_ACK'):
            require(response.get(key) == source[key], 'actual immutable source return ' + key)
        require(response.get('payloads') == source['payloads'], 'released checkpoint returned bytes bit exact')
        return {k: response[k] for k in source}

    @stop_on_fault
    def primitive(self, op, args, attrs=None, shape=None):
        """Send actual typed source operands to Dewey/Popper's native dispatcher.

        The original source VM still controls SSA/rounding order. Its arithmetic
        primitive is replaced by the RTL response, with no software fallback.
        No output expectation is used as an execution operand.
        """
        require(op in self.native_module.COMMON_NATIVE and all(np.size(x) <= 128 for x in args),
                'source primitive and bounded native operands')
        frame = sys._getframe(1)
        while frame is not None and frame.f_code != self.native_module.NativePrimitiveVM.run_qwen.__code__:
            frame = frame.f_back
        require(frame is not None, 'original source recipe caller')
        node = frame.f_locals['node']
        nodes = frame.f_locals['nodes']
        templates = [name for name, code in self.machine.native['microcode'].items() if code is nodes]
        require(len(templates) == 1, 'exact original full recipe object')
        operands = []
        for value in args:
            array = np.asarray(value)
            require(array.dtype.kind in 'fiu' and array.dtype.itemsize in (1, 4, 8), 'actual source arithmetic ABI')
            raw = array.astype(array.dtype.newbyteorder('<'), copy=False).tobytes()
            operands.append(dict(dtype=array.dtype.str, shape=list(array.shape), payload=raw))
        at = {} if attrs is None else attrs
        arrays = [np.asarray(x) for x in args]
        types = {'F32': '<f4', 'U32': '<u4', 'I64': '<i8'}
        if op in ('FADD','FMUL','SQRT','DIV','FMAX','FMIN','BITCAST_F','I2F','LDEXP','FP8_UNPACK'):
            output_dtype = '<f4'
        elif op == 'BITCAST_U' or op.startswith('FCMP_'):
            output_dtype = '<u4'
        elif op in ('IOTA', 'F2I'):
            output_dtype = '<i8'
        elif op == 'FP8_PACK':
            output_dtype = '|u1'
        elif op == 'CONST':
            output_dtype = types[at['dtype']]
        elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
            wide = at.get('dtype') == 'I64' or (at.get('dtype') != 'U32' and any(x.dtype == np.int64 for x in arrays))
            output_dtype = '<i8' if wide else '<u4'
        elif op == 'SELECT':
            output_dtype = types[at['dtype']] if at.get('dtype') in types else np.result_type(arrays[1], arrays[2]).str
        else:
            require(arrays, 'source data movement dtype')
            output_dtype = arrays[0].dtype.str
        response = self.exchange('native_primitive', template=templates[0],
                                 ordered_step=frame.f_locals['pc'], source_node=copy.deepcopy(node),
                                 lowered_primitive=op, attrs={} if attrs is None else copy.deepcopy(attrs),
                                 explicit_shape=shape, source_result_dtype=output_dtype, operands=operands)
        require(response.get('template') == templates[0] and response.get('ordered_step') == frame.f_locals['pc']
                and response.get('lowered_primitive') == op, 'matched actual native source instruction')
        require(response.get('native_completion_accepted') is True and response.get('reverse_validated') is True,
                'held native result/validated reverse')
        dtype = np.dtype(response['dtype'])
        require(dtype.str == output_dtype, 'actual source-derived native result ABI')
        dimensions = response['shape']
        require(all(type(n) is int and n >= 0 for n in dimensions), 'actual result shape')
        count = int(np.prod(dimensions)) if dimensions else 1
        require(count <= 128 and type(response['payload']) is bytes
                and len(response['payload']) == count * dtype.itemsize, 'actual finite native response')
        if shape is not None:
            require(dimensions == shape, 'explicit source result shape')
        elif op in ('FADD','FMUL','SQRT','DIV','FMAX','FMIN','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE',
                    'BITCAST_U','BITCAST_F','I2F','F2I','LDEXP','FP8_PACK','FP8_UNPACK',
                    'SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD','SELECT','COPY'):
            require(dimensions == list(np.broadcast_shapes(*(a.shape for a in arrays))),
                    'actual source operand broadcast shape')
        result = np.frombuffer(response['payload'], dtype=dtype).reshape(dimensions).copy()
        vm = self.machine.vm
        vm.counts[op] += 1; vm.word_counts[op] += result.size
        return result

    def attach(self):
        require(not self.attached, 'attach live provider once')
        if __package__:
            from .h4_qwen_released_kv_delivery import KVStorageDelivery
        else:
            from h4_qwen_released_kv_delivery import KVStorageDelivery
        kv_client = KVStorageDelivery(self)
        for name in ('write', 'read_indices', 'publish', 'retire'):
            require(name not in self.store.__dict__, 'no predecessor instance hook')
            self.original[name] = getattr(self.store, name)
        require('read_tile_bytes' not in self.backend.__dict__, 'no predecessor byte hook')
        require('primitive' not in self.machine.vm.__dict__, 'no predecessor native dispatcher hook')
        self.original['read_tile_bytes'] = self.backend.read_tile_bytes
        for name in ('write', 'read_indices', 'publish', 'retire'):
            handler = getattr(self, name)
            def forward(instance, *args, _handler=handler, **kwargs):
                return _handler(*args, **kwargs)
            setattr(self.store, name, MethodType(forward, self.store))
        def immutable_forward(instance, request):
            return self.immutable_read(request)
        self.backend.read_tile_bytes = MethodType(immutable_forward, self.backend)
        def primitive_forward(instance, op, args, attrs=None, shape=None):
            return self.primitive(op, args, attrs, shape)
        self.machine.vm.primitive = MethodType(primitive_forward, self.machine.vm)
        self.kv_client = kv_client.attach()
        self.attached = True
        return self

    def run_full_token(self, token, position, observer=None):
        require(self.attached, 'live provider delivery attached')
        # Arithmetic instruction enrollment remains the native dispatcher
        # owner's job. Never advertise a software VM as the integrated run.
        require(self.transport.native_dispatch_program_sha256 == PROGRAM_SHA,
                'full canonical native RTL dispatcher must be connected')
        if __package__:
            from .h4_qwen_released_kv_delivery import KVStorageDelivery
        else:
            from h4_qwen_released_kv_delivery import KVStorageDelivery
        require(type(getattr(self,'kv_client',None)) is KVStorageDelivery
                and self.kv_client.installed_on(self.machine.memory,self.transport),
                'actual KV byte/control client installed, not a transport marker')
        self.machine.current_pc = -1
        result = self.machine.run(token, position, observer=observer)
        require(len(self.machine.done) == 1737 and not self.pending and not self.stopped
                and not self.kv_client.held_writers and not self.kv_client.held_readers,
                'all1737 source commands and live deliveries complete')
        return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--emit-program', type=Path, required=True)
    args = parser.parse_args()
    from h4_c0_source_operand_views_r1 import source_contract
    native, _ = source_contract()
    emit_program(native, args.emit_program)
    print('emitted complete canonical1737 source program,36layers; no numerical execution')


if __name__ == '__main__': main()
