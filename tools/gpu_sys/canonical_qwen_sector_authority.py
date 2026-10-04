"""Bind payload adapter authority methods to the finite physical owner ports.

No Python grant allocation, memory, ready/reverse timers or reset. A frozen
snapshot merely identifies an EXISTING hardware grant; every use resamples
grant_live/identity/phase/fault. Enclosing RTL supplies physical map + actual
prior-sector drain and gates all same-sector callers with guard_permit.
"""
from dataclasses import dataclass

from tools.gpu_sys.canonical_qwen_payload_w2 import PayloadRoute, PayloadW2Adapter
from tools.gpu_sys.canonical_qwen_transport import TransportError


FIELDS = (('identity', 64), ('key', 20), ('sector', 9), ('source_addr', 34),
          ('address', 34), ('PC', 7), ('client', 3), ('tag', 32), ('generation', 4))


def unpack_identity(bits):
    if type(bits) is not int or not 0 <= bits < 1 << 207:
        raise TransportError('actual sector grant identity width')
    values = {}
    for name, width in reversed(FIELDS):
        values[name] = bits & ((1 << width) - 1)
        bits >>= width
    return values


def source_identity(offer):
    bits = 0
    for name, width in FIELDS[:4]:
        value = offer[name]
        if type(value) is not int or not 0 <= value < 1 << width:
            raise TransportError('actual sector source ' + name)
        bits = (bits << width) | value
    return bits


@dataclass(frozen=True)
class GrantSnapshot:
    identity: int


class PhysicalSectorAuthority:
    OLD_REQ, OLD_CAP, OLD_REV, NEW_REQ, NEW_CAP, NEW_REV, RELEASE = range(1, 8)

    def __init__(self, pins, w2_ports, *, enabled=False):
        if not enabled or pins.parameter('ENABLE') != 1 or pins.parameter('IDENTW') != 207:
            raise TransportError('physical sector authority default off/width')
        self.pins, self.w2_ports = pins, dict(w2_ports)
        self.snapshot = None
        self.release_armed = False
        # Wrapped caller authorities still handle non-payload clients. This
        # path cannot invent a reverse for callers outside its hardware root.
        for PC, port in self.w2_ports.items():
            if type(PC) is not int or port.ports.parameter('PC_ID') != PC:
                raise TransportError('actual physical W2 PC binding')
            if isinstance(port.authority, _CallerAuthority):
                raise TransportError('W2 caller authority already bound')
            port.authority = _CallerAuthority(self, PC, port.authority)

    def _sample(self):
        p = self.pins
        p.settle()
        if p.get('fault') or p.get('local_reset') or not p.get('por_n'):
            raise TransportError('physical sector fault/reset; retain accepted grant')
        if not p.get('grant_live'):
            if self.snapshot is not None:
                raise TransportError('physical sector owner disappeared without accepted release')
            return None
        bits = p.get('grant_identity')
        fields = unpack_identity(bits)
        if self.snapshot is None:
            self.snapshot = GrantSnapshot(bits)
        if self.snapshot.identity != bits:
            raise TransportError('physical retained sector identity changed')
        return fields

    @staticmethod
    def _same_source(fields, offer):
        return all(fields[n] == offer[n] for n, _ in FIELDS[:4])

    def _route(self, fields):
        try:
            port = self.w2_ports[fields['PC']]
        except KeyError:
            raise TransportError('physical sector mapped to unbound W2 PC') from None
        return PayloadRoute(port, fields['client'], fields['address'], fields['tag'],
                            fields['generation'], self.snapshot)

    def acquire_payload_sector(self, offer):
        fields = self._sample()
        if fields is None:
            # Mapping and sector-clear inputs belong to enclosing PHYSICAL
            # source allocator. Only source offer + request valid are driven.
            self.pins.set('alloc_source', source_identity(offer))
            self.pins.set('alloc_rmw', offer['rmw'])
            self.pins.set('alloc_valid', 1)
            self.pins.settle()
            return None
        self.pins.set('alloc_valid', 0)
        if (not self._same_source(fields, offer) or self.pins.get('grant_rmw') != offer['rmw'] or
                self.pins.get('grant_phase') != (self.OLD_REQ if offer['rmw'] else self.NEW_REQ)):
            raise TransportError('physical initial grant source/phase mismatch')
        return self._route(fields)

    def continue_payload_rmw(self, grant, offer):
        fields = self._sample()
        if (fields is None or grant is not self.snapshot or not self._same_source(fields, offer) or
                self.pins.get('grant_rmw') != 1 or offer['rmw_last'] != 1):
            raise TransportError('physical RMW retained source mismatch')
        if self.pins.get('grant_phase') != self.NEW_REQ:
            return None
        return self._route(fields)

    def release_payload_sector(self, grant, offer):
        fields = self._sample()
        if fields is None or grant is not self.snapshot or not self._same_source(fields, offer):
            raise TransportError('physical sector release source mismatch')
        self.pins.set('release_identity', grant.identity)
        self.pins.set('release_valid', 1)
        self.pins.settle()
        self.release_armed = bool(self.pins.get('release_ready'))
        return self.release_armed

    def after_edge(self):
        # Called after SAME real clock edge as PayloadW2Adapter.after_edge.
        # Ready/valid release accepted here is the only snapshot retirement.
        if self.release_armed and self.pins.get('grant_live'):
            raise TransportError('physical release handshake did not retire owner')
        if self.pins.get('release_valid') and not self.pins.get('grant_live'):
            if (not self.release_armed or self.pins.get('fault') or
                    self.pins.get('local_reset') or not self.pins.get('por_n')):
                raise TransportError('sector disappeared/reset without actual release edge')
            self.snapshot = None
        self.release_armed = False
        self.pins.set('release_valid', 0)
        if self.pins.get('grant_live'):
            self.pins.set('alloc_valid', 0)

    def payload_reverse(self, PC, client, tag, generation, write):
        fields = self._sample()
        if fields is None or (fields['PC'], fields['client'], fields['tag'], fields['generation']) != (
                PC, client, tag, generation):
            return None  # Caller outside this root: delegate to its authority.
        # These phases are entered ONLY after matching actual reverse valid /
        # ready handshake in hardware. No global clean/drain bit substitutes.
        return self.pins.get('grant_phase') == (self.RELEASE if write else self.NEW_REQ)


class _CallerAuthority:
    def __init__(self, sector, PC, delegate):
        self.sector, self.PC, self.delegate = sector, PC, delegate

    def completion_ready(self, *args):
        return self.delegate.completion_ready(*args)

    def reverse_validated(self, client, tag, generation, write):
        reverse = self.sector.payload_reverse(self.PC, client, tag, generation, write)
        return self.delegate.reverse_validated(client, tag, generation, write) if reverse is None else reverse


class SectorBoundPayload:
    """One registration for the enclosing shared controller/W2/owner edge.

    before_edge(); enclosing_simulator.tick(); after_edge(). Never call tick
    separately on this owner, controller or W2. Existing raw pin controls are
    used; no process/clock/backend is spawned by this integration.
    """
    def __init__(self, controller, authority_pins, w2_ports, *, enabled=False):
        self.authority = PhysicalSectorAuthority(authority_pins, w2_ports, enabled=enabled)
        self.payload = PayloadW2Adapter(controller, self.authority, enabled=enabled)

    def before_edge(self):
        try:
            self.authority._sample()
            self.payload.before_edge()
        except BaseException:
            self.payload._fault()
            raise

    def after_edge(self):
        try:
            p = self.authority.pins
            if p.get('fault') or p.get('local_reset') or not p.get('por_n'):
                raise TransportError('physical sector fault at shared clock edge')
            event, offer = self.payload.event, self.payload.offer
            if event in ('REQUEST', 'CAPTURE', 'REVERSE'):
                expected = {'REQUEST':(2,5),'CAPTURE':(3,6),'REVERSE':(4,7)}[event][offer['write']]
                if not p.get('grant_live') or p.get('grant_phase') != expected:
                    raise TransportError('actual sector event not accepted at shared clock edge: '+event)
            self.authority.after_edge()
            self.payload.after_edge()
        except BaseException:
            self.payload._fault()
            raise
