"""Four source RPC bodies over held hardware ports, with no arithmetic fallback.

`native_factory(authority, contexts)` is the compose ABI. The physical provider
supplies `native_binding(kind, request)` to select *installed* ports, never to
compute a reply. Bindings below carry source routing metadata, not grants.
No constructor clocks, writes, allocates leases or installs a second TC set.
The fixed-instruction primitive port is intentionally not a claim that the
current PC40 fragment implements the complete native instruction set.
"""
from dataclasses import dataclass
from math import prod
from tools.gpu_sys.canonical_qwen_transport import TransportError, W2PrimaryPort
from tools.gpu_sys.canonical_qwen_service_calendar import PROGRAM_SHA, canonical, sha

KINDS = ('source_publish', 'source_retire', 'immutable_source_transfer', 'native_primitive')
DTYPES = {'<f4': (0, 4), '<u4': (1, 4), '<i8': (2, 8), '|u1': (3, 1)}


def need(ok, message):
    if not ok:
        raise TransportError(message)


def uint(n, width, label):
    need(type(n) is int and 0 <= n < 1 << width, label + ' width')
    return n


@dataclass(frozen=True)
class SourceRange:
    """Offer to existing protected range-owner RTL; READY proves its legality."""
    index: int
    tuple239: int
    owner55: int
    version: str


@dataclass(frozen=True)
class RetiredRange:
    index: int
    session64: int
    owner55: int
    version: str


@dataclass(frozen=True)
class ImmutableSector:
    port: W2PrimaryPort
    client: int
    address: int
    tag: int
    generation: int
    offset: int
    length: int


@dataclass(frozen=True)
class ImmutableBinding:
    # One ordered tuple per source byte_range; multiple sector slices per tuple.
    ranges: tuple


@dataclass(frozen=True)
class PrimitiveBinding:
    """Installed specialized source instruction endpoint, not a result callback.

    RTL must expose NATIVE_RPC_ABI=1 and immutable INSTRUCTION_SHA256. The hash
    binds template/node/lowered opcode/attrs/input shapes/types/result shape.
    Its operands are streamed verbatim in 32B beats. Its result and matching
    reverse are held outputs, with full PC11/sequence64 identity.
    No such general endpoint is assumed installed by this module.
    """
    ports: object
    instruction_sha256: str
    result_shape: tuple


def descriptor(request, result_shape):
    return dict(template=request['template'], ordered_step=request['ordered_step'],
                source_node=request['source_node'], lowered_primitive=request['lowered_primitive'],
                attrs=request['attrs'], explicit_shape=request['explicit_shape'],
                operands=[dict(dtype=o['dtype'], shape=o['shape']) for o in request['operands']],
                source_result_dtype=request['source_result_dtype'], result_shape=list(result_shape))


class NativeHandlers:
    def __init__(self, authority, contexts):
        self.authority, self.contexts = authority, tuple(contexts)
        need(len(self.contexts) == 64, 'sole compose64 contexts required')
        self.root = self.contexts[0].root
        need(all(c.root is self.root and (c.rank, c.SM) == divmod(i, 32)
                 for i, c in enumerate(self.contexts)), 'exact physical context order/root')
        need(callable(getattr(authority, 'native_binding', None)),
             'physical provider native_binding selector not installed')
        self.native = authority.canonical_native
        need(sha(canonical(self.native)) == PROGRAM_SHA, 'canonical1737 program hash')
        self.placement = authority.RF.placement
        self.busy = False
        self.stopped = False

    def handlers(self):
        return {kind: (lambda request, k=kind: self.exchange(k, request)) for kind in KINDS}

    def exchange(self, kind, r):
        need(not self.stopped and not self.busy, 'native debt/fault retained; no reentrant reuse')
        need(r.get('program_sha256') == PROGRAM_SHA, 'canonical program identity')
        uint(r.get('source_PC'), 11, 'source PC')
        need(r['source_PC'] < 1737, 'source PC aperture')
        uint(r.get('sequence'), 64, 'source sequence')
        self.busy = True
        try:
            result = getattr(self, kind)(r)
            result.update({k: r[k] for k in ('program_sha256', 'source_PC', 'sequence')})
            result.update(accepted=True, fault=False)
            self.busy = False
            return result
        except BaseException:
            # Accepted physical debt remains held. No reset, lease deletion,
            # retry or admission of a later RPC after a mismatch.
            self.stopped = True
            raise

    def _range_port(self, index):
        uint(index, 6, 'physical SM')
        port = self.authority.RF.owners[index].physical
        need(port.root is self.root, 'range owner must use sole enclosing clock')
        need(port.parameter('ENABLE') == 1 and port.parameter('SM_INDEX') == index,
             'installed enabled source-owner identity')
        return port

    def _offer(self, p, values, valid, ready, check=None):
        for name, value in values.items(): p.set(name, value)
        p.set(valid, 1)
        try:
            while True:
                p.settle()
                need(not p.get('fault'), 'actual source owner fault; retained debt')
                if check: check(p)
                accepted = bool(p.get(ready))
                self.root.tick()
                if accepted: break
        finally:
            p.set(valid, 0)

    def source_publish(self, r):
        version = r['version']
        need(r['lease'] == 'value:' + version, 'source publication lease')
        homes = {i: h for (v, rank, sm), h in self.placement.rf.items()
                 if v == version for i in (rank * 32 + sm,)}
        # The RF range-owner has no control/VM publication port. Empty controls
        # are a real missing endpoint, never implicitly visible.
        need(homes, 'control/VM publication endpoint not installed')
        expected = {('RF', h.rank, h.sm, slot) for h in homes.values()
                    for slot in range(h.first, h.end)}
        pages = r['source_pages']
        need(len(pages) == len(expected) and {tuple(p['source_key']) for p in pages} == expected,
             'complete actual publication source spans')
        need(all(p['version'] == version and p['lease'] == r['lease'] for p in pages),
             'publication page version/lease')
        need(all(h.retire == r['retire_PC'] and h.birth in (-1, r['source_PC']) for h in homes.values()),
             'source publication lifetime')
        bindings = self.authority.native_binding('source_publish', r)
        need(isinstance(bindings, tuple) and len(bindings) == len(homes)
             and all(isinstance(b, SourceRange) for b in bindings)
             and {b.index for b in bindings} == set(homes), 'complete physical publication group')
        for b in bindings:
            h = homes[b.index]
            t = uint(b.tuple239, 239, 'producer tuple')
            o = uint(b.owner55, 55, 'original producer owner')
            need(b.version == version and ((t >> 19) & 2047) == self.placement.version_ids[version]
                 and ((t >> 164) & 2047) == r['source_PC']
                 and ((t >> 30) & 63) == b.index
                 and ((t >> 10) & 511) == h.first and (t & 1023) == h.end,
                 'literal source producer group tuple')
            p = self._range_port(b.index)
            mask = (1 << (h.end - h.first)) - 1
            self._offer(p, dict(publish_tuple=t, publish_owner=o, publish_page_mask=mask),
                        'publish_valid', 'publish_ready',
                        lambda p: need(p.get('held_session') == t >> 175, 'publication session'))
        # Actual publish_ready requires protected all-page ACK bitmap AND
        # producer_visible; no host-side ACK counter pays this boundary.
        return dict(version=version, lease=r['lease'], all_writes_visible=True, owner_retained=True)

    def source_retire(self, r):
        versions = r['versions']
        need(isinstance(versions, list) and versions == sorted(set(versions))
             and r['leases'] == ['value:' + v for v in versions]
             and r['retire_PC'] == r['source_PC'], 'source retirement identity/order')
        expected = {(v, rank * 32 + sm) for v, rank, sm in self.placement.rf if v in versions}
        need(expected and all(any(v == x[0] for x in expected) for v in versions),
             'control/VM retirement endpoint not installed')
        bindings = self.authority.native_binding('source_retire', r)
        need(isinstance(bindings, tuple) and len(bindings) == len(expected)
             and all(isinstance(b, RetiredRange) for b in bindings)
             and {(b.version, b.index) for b in bindings} == expected,
             'all physically retained retirement rows required')
        for b in bindings:
            h = self.placement.rf[b.version, b.index // 32, b.index % 32]
            need(h.retire == r['retire_PC'], 'compiled last-consumer retirement PC')
            p = self._range_port(b.index)
            session = uint(b.session64, 64, 'retirement session')
            self._offer(p, dict(source_native_retire_session=session,
                               source_native_retire_version=self.placement.version_ids[b.version],
                               source_native_retire_owner=uint(b.owner55, 55, 'retirement owner')),
                        'source_native_retire_valid', 'source_native_retire_ready',
                        lambda p: need(p.get('held_session') == session, 'retirement session'))
        # The selected RTL's release_legal requires producer frame retirement
        # and every declared consumer terminal + reverse, not just counts.
        return dict(versions=versions, all_consumers_accepted=True,
                    all_reverse_validated=True, all_copies_drained=True)

    def immutable_source_transfer(self, r):
        source = r['source_request']
        need(source.get('lease_state') == 'visible', 'compiled immutable backing lifetime')
        b = self.authority.native_binding('immutable_source_transfer', r)
        need(isinstance(b, ImmutableBinding) and len(b.ranges) == len(source['byte_ranges']),
             'exact immutable byte-range binding')
        payloads = []
        for span, sectors in zip(source['byte_ranges'], b.ranges):
            need(isinstance(sectors, tuple) and sectors, 'finite actual W2 sector route')
            raw = bytearray()
            cursor = span['address']
            for s in sectors:
                need(isinstance(s, ImmutableSector) and isinstance(s.port, W2PrimaryPort),
                     'installed W2 sector transactor required')
                need(s.port.ports.root is self.root, 'immutable shared clock owner')
                need(type(s.offset) is int and type(s.length) is int and 0 <= s.offset < 32
                     and 0 < s.length <= 32 - s.offset and s.address + s.offset == cursor,
                     'source sector slice coverage/order')
                result = s.port.sector(s.client, s.address, s.tag, s.generation)
                raw.extend(result['payload'][s.offset:s.offset + s.length])
                cursor += s.length
            need(len(raw) == span['bytes'], 'complete source byte span')
            payloads.append(bytes(raw))
        # Expected checkpoint payload is a comparison only, never read as
        # execution data. W2.sector waits real consumer readiness and reverse.
        need(payloads == r['source_payloads'], 'physical immutable bytes differ from source checkpoint')
        return dict(provider_ref=source['provider_ref'], lease=source['lease'],
                    state='visible', reverse_grant_ACK=True, payloads=payloads)

    def native_primitive(self, r):
        code = self.native['microcode'].get(r['template'])
        step = r['ordered_step']
        need(type(step) is int and isinstance(code, list) and 0 <= step < len(code)
             and code[step] == r['source_node'], 'literal native template/node reference')
        need(r['template'] in self.native['operations'][r['source_PC']]['kernels'],
             'template not bound to actual source PC')
        abi = self.native['tile_kernel_ABI'][r['template']]['steps'][step]
        need(r['lowered_primitive'] in abi['native_steps'], 'source instruction lowering binding')
        need(r['source_result_dtype'] in DTYPES, 'exact result dtype; no I64 narrowing')
        args = r['operands']
        need(isinstance(args, list) and len(args) <= 4, 'finite four-operand endpoint')
        for a in args:
            need(a['dtype'] in DTYPES and isinstance(a['shape'], list)
                 and all(type(n) is int and n >= 0 for n in a['shape']), 'typed source operand')
            count = prod(a['shape'])
            need(len(a['shape']) <= 8 and count <= 128 and type(a['payload']) is bytes
                 and len(a['payload']) == count * DTYPES[a['dtype']][1], 'source operand span')
        b = self.authority.native_binding('native_primitive', r)
        need(isinstance(b, PrimitiveBinding), 'installed native instruction endpoint missing')
        shape = list(b.result_shape)
        need(len(shape) <= 8 and all(type(n) is int and 0 <= n < 1 << 32 for n in shape)
             and prod(shape) <= 128, 'finite result shape')
        need(r['explicit_shape'] is None or r['explicit_shape'] == shape, 'explicit source shape')
        fingerprint = sha(canonical(descriptor(r, shape)))
        need(b.instruction_sha256 == fingerprint, 'instruction/attrs/typed-span source binding')
        p = b.ports
        need(p.root is self.root and p.parameter('NATIVE_RPC_ABI') == 1
             and p.parameter('INSTRUCTION_SHA256') == int(fingerprint, 16),
             'actual source-specialized engine contract; not PC40 fragment')
        for name in ('fault', 'cmd_ready', 'operand_ready', 'result_valid', 'result_PC',
                     'result_sequence', 'result_dtype', 'result_bytes', 'result_data',
                     'reverse_valid', 'reverse_PC', 'reverse_sequence'):
            p.get(name)
        seq, PC = r['sequence'], r['source_PC']
        self._offer(p, dict(cmd_PC=PC, cmd_sequence=seq, cmd_operands=len(args)), 'cmd_valid', 'cmd_ready')
        for index, a in enumerate(args):
            for offset in range(0, len(a['payload']), 32):
                part = a['payload'][offset:offset + 32]
                self._offer(p, dict(operand_index=index, operand_offset=offset,
                            operand_bytes=len(part), operand_data=int.from_bytes(part, 'little')),
                            'operand_valid', 'operand_ready')
        size = prod(shape) * DTYPES[r['source_result_dtype']][1]
        p.set('result_ready', 0)
        while True:
            p.settle(); need(not p.get('fault'), 'native engine fault retains source debt')
            if p.get('result_valid'):
                need((p.get('result_PC'), p.get('result_sequence'), p.get('result_dtype'), p.get('result_bytes'))
                     == (PC, seq, DTYPES[r['source_result_dtype']][0], size), 'held native result identity/dtype/span')
                bits = uint(p.get('result_data'), 8192, 'actual result bits')
                need(bits < 1 << (8 * size), 'native result nonzero outside accepted span')
                payload = bits.to_bytes(size, 'little')
                p.set('result_ready', 1)
                try:
                    p.settle()
                    need(p.get('result_valid') and p.get('result_data') == bits
                         and (p.get('result_PC'), p.get('result_sequence'),p.get('result_dtype'),p.get('result_bytes'))
                         == (PC,seq,DTYPES[r['source_result_dtype']][0],size), 'result stable at actual capture')
                    self.root.tick()
                finally:
                    p.set('result_ready', 0)
                break
            self.root.tick()
        p.set('reverse_ready', 0)
        while True:
            p.settle(); need(not p.get('fault'), 'native reverse fault retains source debt')
            if p.get('reverse_valid'):
                need((p.get('reverse_PC'), p.get('reverse_sequence')) == (PC,seq), 'matched native reverse identity')
                p.set('reverse_ready',1)
                try:
                    p.settle()
                    need(p.get('reverse_valid') and (p.get('reverse_PC'),p.get('reverse_sequence')) == (PC,seq),
                         'reverse stable at actual acceptance')
                    self.root.tick()
                finally:
                    p.set('reverse_ready',0)
                break
            self.root.tick()
        return dict(template=r['template'], ordered_step=step, lowered_primitive=r['lowered_primitive'],
                    native_completion_accepted=True, reverse_validated=True,
                    dtype=r['source_result_dtype'], shape=shape, payload=payload)


def native_factory(authority, contexts):
    return NativeHandlers(authority, contexts).handlers()
