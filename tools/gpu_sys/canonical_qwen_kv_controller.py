"""Seven callbacks on ot_gpu_qwen_kv_lifecycle_controller's real port object.

No writer/readers dictionary, numerical callback, backing bytes, reset/retry or
elapsed completion. Enclosing simulator owns every shared/payload/metadata/
consumer/reverse/drain authority. This object drives ONLY cmd_* and rsp_ready.
The source mapper must supply actual reserved stage and K/V apertures.
"""
import hashlib
from tools.gpu_sys.canonical_qwen_transport import TransportError, PROGRAM_SHA
from tools.gpu_sys.canonical_qwen_kv_ports import CONTROL_KINDS, CONTROL_ACKS


class KVControllerPort:
    def __init__(self, ports, authority):
        if ports.parameter('ENABLE') != 1:
            raise TransportError('KV controller must be explicitly enabled')
        if not callable(getattr(authority, 'kv_controller_source', None)):
            raise TransportError('actual KV source/stage allocation required')
        self.ports, self.authority = ports, authority
        self.pending = None
        self.stopped = False
        self.handlers = {k: self._handler(k) for k in CONTROL_KINDS}

    @staticmethod
    def _uint(value, bits, name):
        if type(value) is not int or not 0 <= value < 1 << bits:
            raise TransportError('KV actual ' + name)
        return value

    def _command(self, request, op, source, beat=0, data=0):
        p = self.ports
        layer, rank, position = request['key']
        key = layer << 14 | rank << 13 | position
        ident = request['tag'] if op < 4 else request['lease']
        self._uint(ident, 64, 'identity')
        values = dict(cmd_op=op, cmd_identity=ident, cmd_key=key,
                      cmd_producer=request.get('producer_tag', 0),
                      cmd_sequence=request['sequence'], cmd_PC=request['source_PC'],
                      cmd_consumer=int(request.get('stage') == 'PV'),
                      cmd_stage_beat=beat, cmd_stage_data=data,
                      cmd_stage_base=source['stage_base'], cmd_stage_SM=source['stage_SM'], cmd_K_base=source['K_base'],
                      cmd_V_base=source['V_base'], cmd_valid=1, rsp_ready=1)
        for name, value in values.items():
            p.set(name, value)
        accepted = False
        while True:
            p.settle()
            if p.get('fault') or p.get('rsp_fault'):
                raise TransportError('actual KV controller fault; retained debt')
            offered = not accepted and bool(p.get('cmd_ready'))
            result = None
            if p.get('rsp_valid'):
                if not accepted:
                    raise TransportError('KV unsolicited completion')
                expected = dict(rsp_op=op, rsp_identity=ident, rsp_key=key,
                                rsp_sequence=request['sequence'], rsp_PC=request['source_PC'],
                                rsp_producer=request.get('producer_tag', 0),
                                rsp_consumer=int(request.get('stage') == 'PV'), rsp_stage_beat=beat)
                if any(p.get(k) != v for k, v in expected.items()):
                    raise TransportError('KV physical completion identity mismatch')
                if op in (0, 1, 2) and not p.get('writer_retained'):
                    raise TransportError('KV physical writer lost before publication')
                result = p.get('rsp_capture').to_bytes(64, 'little') if op == 1 else b''
            p.tick()
            if offered:
                accepted = True
                p.set('cmd_valid', 0)
            if result is not None:
                p.set('rsp_ready', 0)
                return result

    def _source(self, request, needs_stage=True):
        if request.get('program_sha256') != PROGRAM_SHA:
            raise TransportError('canonical KV source program pin')
        key = request.get('key')
        if (type(key) is not list or len(key) != 3 or
            any(type(v) is not int for v in key) or
            not 0 <= key[0] < 36 or not 0 <= key[1] < 2 or not 0 <= key[2] < 8192):
            raise TransportError('canonical KV layer/rank/position')
        self._uint(request.get('sequence'), 64, 'sequence')
        pc = self._uint(request.get('source_PC'), 11, 'source PC')
        if pc >= 1737:
            raise TransportError('canonical KV source PC')
        source = self.authority.kv_controller_source(request)
        if type(source) is not dict:
            raise TransportError('actual KV source allocator')
        for name, width in (('stage_base', 10), ('stage_SM', 5), ('K_base', 34), ('V_base', 34)):
            self._uint(source.get(name), width, name)
        if (source['stage_base'] > 1008 or source['K_base'] % 32 or source['V_base'] % 32
            or (needs_stage and source.get('stage_lease_retained') is not True)
            or max(source['K_base'], source['V_base']) + 4194304 > 1 << 34
            or abs(source['K_base']-source['V_base']) < 4194304):
            raise TransportError('actual held 1024B stage / aligned K,V apertures')
        return source

    def _handler(self, kind):
        op = CONTROL_KINDS.index(kind)
        def transact(request):
            if self.stopped or self.pending is not None:
                raise TransportError('KV controller pending/faulted; no reuse')
            self.pending = (kind, request)
            try:
                source = self._source(request, needs_stage=op < 4)
                if op == 4:
                    self._uint(request.get('producer_tag'), 64, 'producer tag')
                if op == 5 and request.get('stage') not in ('SCORES', 'PV'):
                    raise TransportError('actual SCORES/PV consumer')
                if op == 2 and request.get('bytes') != 1024:
                    raise TransportError('complete actual K/V payload required')
                captured = bytearray()
                if op == 1:
                    payload, addresses = request.get('payload'), request.get('addresses')
                    if (type(payload) is not bytes or len(payload) != 128 or
                        type(addresses) is not list or len(addresses) != 128 or
                        any(type(a) is not int for a in addresses)):
                        raise TransportError('actual source 128-byte stage window')
                    pos = request['key'][2]
                    K, V = source['K_base'], source['V_base']
                    expected = [K + ((h * 512 + pos // 16) * 128 + d) * 16 + pos % 16
                                for h in range(4) for d in range(128)]
                    expected += [V + (h * 8192 + pos) * 128 + d
                                 for h in range(4) for d in range(128)]
                    starts = [i for i in range(0, 1024, 128) if expected[i:i+128] == addresses]
                    if len(starts) != 1:
                        raise TransportError('stage addresses do not resolve actual K/V source window')
                    start = starts[0] // 64
                    for j in range(2):
                        captured.extend(self._command(request, op, source, start+j,
                                        int.from_bytes(payload[j*64:(j+1)*64], 'little')))
                else:
                    self._command(request, op, source)
                # Successful hardware opcode proves the listed causal conditions;
                # no fallback authority/default ready can construct this response.
                fields = ('program_sha256', 'source_PC', 'sequence', 'key')
                response = {k: request[k] for k in fields}
                response['tag' if op < 4 else 'lease'] = request['tag' if op < 4 else 'lease']
                if op == 4:
                    response['producer_tag'] = request['producer_tag']
                if op == 5:
                    response['stage'] = request['stage']
                response.update({k: True for k in CONTROL_ACKS[kind]})
                response.update(accepted=True, fault=False)
                if op == 1:
                    response['payload_sha256'] = hashlib.sha256(captured).hexdigest()
                self.pending = None
                return response
            except BaseException:
                self.stopped = True
                raise  # Never retract accepted command, clear a lease, reset, retry.
        return transact
