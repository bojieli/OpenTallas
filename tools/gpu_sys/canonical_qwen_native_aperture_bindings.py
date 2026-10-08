"""Actual held native-source authority; constructors never write pins or tick.

Install the collector and new source-bank views first. Immutable profile lookup,
actual result visibility and accepted terminal/reverse remain hardware paths.
This mixin adds the source cursor and staging-page hooks; it cannot manufacture
native_binding, profile_valid, readiness, or completion.
"""
from tools.gpu_sys.canonical_qwen_range_owner_bindings import RangeOwnerPort
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.gpu_sys.canonical_qwen_source_mapping import uint
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA


def need(ok, message):
    if not ok:
        raise TransportError(message)


class NativeWorkspaceQueryPort(RangeOwnerPort):
    """Same physical Q seat; one new sealed workspace bit, no software owner."""
    def resolve(self, tuple239, version, slot, write, *, workspace=False):
        self.physical.set('query_workspace', int(workspace))
        try:
            owner = super().resolve(tuple239, version, slot, write)
        finally:
            self.physical.set('query_workspace', 0)
        p = self.physical
        need((p.get('query_result_version'), p.get('query_result_write'),
              p.get('query_result_workspace')) == (version, int(write), int(workspace)),
             'actual query version/direction/workspace mismatch')
        return owner


class NativeApertureAuthority:
    """Compose existing RF/sector authority without replacing payload handlers.

    `authority` owns installed physical transactors. `collectors` contains all64
    actual actor components; issuer scope is observed, never copied from cmd.
    This wrapper deliberately delegates native_binding to its installed command
    provider. That provider must capture metadata using collect_aperture below,
    independent immutable profile and actual source cursor before command GO.
    """
    def __init__(self, authority, collectors):
        need(len(collectors) == 64, 'actual64 actor collector inventory')
        self.authority = authority
        self.collectors = tuple(collectors)
        self.producers = {}
        self.owners = tuple(NativeWorkspaceQueryPort(p.physical, i)
                            for i, p in enumerate(authority.owners))
        for i, p in enumerate(self.collectors):
            need(p.parameter('ENABLE') == 1 and p.parameter('ACTOR_INDEX') == i,
                 'installed enabled native collector identity')
            need(p.root is authority.RF[i].ports.root, 'one enclosing native-source clock')
            for name in ('fault', 'issuer_held_valid', 'issuer_held_tuple',
                         'issuer_held_owner', 'source_cursor_valid',
                         'source_cursor_advance_valid', 'authority_sequence',
                         'source_owner_held', 'lease_workspace'):
                p.get(name)

    def __getattr__(self, name):
        return getattr(self.authority, name)

    def _actor(self, request):
        need(request.get('program_sha256') == PROGRAM_SHA, 'canonical source pin')
        pc = uint(request.get('source_PC'), 11, 'native source PC')
        need(pc < 1737, 'native source PC range')
        live = []
        for i, p in enumerate(self.collectors):
            p.settle()
            t = p.get('issuer_held_tuple')
            if p.get('issuer_held_valid') and (t >> 164) & 2047 == pc and (t >> 30) & 63 == i:
                need(not p.get('fault') and not p.get('issuer_held_fault'), 'native issuer/collector fault')
                live.append((i, p, t, p.get('issuer_held_owner')))
        need(len(live) == 1, 'one actual held execution actor; no local-stage fallback')
        return live[0]

    def native_source_cursor(self, request):
        # Import only the selected source implementation; no legacy fallback.
        from tools.gpu_sys.canonical_qwen_native_source_cursor import SourceCursorProducer, SourceCursorBinding
        i, p, t, owner = self._actor(request)
        if i not in self.producers:
            self.producers[i] = SourceCursorProducer(p.root, p)
        return SourceCursorBinding(self.producers[i], t, owner)

    def begin_from_profile(self, request):
        """Accept the actual independent ROM profile before capturing apertures.

        Only begin_valid is a command INPUT. Profile fields are readonly ROM
        outputs; the source cursor was already loaded by the owned RPC producer.
        No command dictionary, RF-page extent or payload computes qualification.
        Returns the captured identity/shape for the command provider to verify.
        """
        _, p, t, owner55 = self._actor(request)
        seq = uint(request.get('sequence'), 64, 'owned RPC sequence')
        with p.root.lock:
            p.settle()
            need(not p.get('context_live') and p.get('source_cursor_valid')
                 and (p.get('authority_tuple'), p.get('authority_owner'),
                      p.get('authority_sequence')) == (t, owner55, seq),
                 'source cursor must precede ROM profile collection')
            p.set('begin_valid', 1)
            try:
                while True:
                    p.settle()
                    need(not p.get('fault') and p.get('source_cursor_valid')
                         and p.get('issuer_held_valid') and not p.get('issuer_held_fault')
                         and (p.get('issuer_held_tuple'), p.get('issuer_held_owner')) == (t, owner55)
                         and (p.get('authority_tuple'), p.get('authority_owner'),
                              p.get('authority_sequence')) == (t, owner55, seq),
                         'actual source scope lost before profile begin')
                    accept = bool(p.get('begin_ready'))
                    if accept:
                        need(p.get('profile_valid') and
                             (p.get('profile_tuple'), p.get('profile_PC'),
                              p.get('profile_sequence')) == (t, request['source_PC'], seq),
                             'begin requires independently selected ROM profile identity')
                        shape = uint(p.get('profile_shape'), 256, 'ROM source shape fingerprint')
                    p.tick()
                    if accept:
                        break
            finally:
                p.set('begin_valid', 0)
            p.settle()
            need(not p.get('fault') and p.get('context_live')
                 and (p.get('authority_tuple'), p.get('authority_owner'),
                      p.get('authority_sequence'), p.get('authority_shape_sha'))
                 == (t, owner55, seq, shape), 'independent ROM profile not captured')
            return dict(tuple239=t, owner55=owner55, sequence64=seq, shape_sha256=shape)

    def collect_aperture(self, request, aperture, bank, slots, version, *, workspace=False):
        """Capture actual Q identity positively, then release only the Q seat.

        Caller supplies an address request, not an authority flag. Hardware Q
        validates source role/bounds; collector validates both pages/identity.
        The coded bank B/source leases persist independently of Q consumption.
        """
        _, p, t, owner55 = self._actor(request)
        need(p.get('context_live') and p.get('authority_tuple') == t
             and p.get('authority_owner') == owner55
             and p.get('authority_sequence') == request.get('sequence'), 'held native metadata context')
        uint(aperture, 3, 'aperture'); need(aperture < 5, 'four inputs and one result')
        uint(bank, 6, 'physical operand bank'); uint(slots, 18, 'RF slot pair')
        uint(version, 11, 'source version')
        q = self.owners[bank]
        with p.root.lock:
            owner46 = q.resolve(t, version, slots & 511, aperture == 4 or workspace, workspace=workspace)
            for k, v in dict(capture_aperture=aperture, capture_bank=bank,
                             capture_slots=slots, capture_version=version,
                             capture_workspace=int(workspace), capture_valid=1).items():
                p.set(k, v)
            try:
                p.settle()
                need(p.get('capture_ready') and not p.get('fault'), 'actual Q cannot authorize aperture capture')
                p.tick(); p.set('capture_valid', 0); p.settle()
                need(not p.get('fault') and (p.get('lease_slots') >> (18*aperture)) & ((1<<18)-1) == slots
                     and (p.get('lease_owner') >> (46*aperture)) & ((1<<46)-1) == owner46,
                     'sealed aperture capture did not retain actual identity')
                q.complete_page(t, slots & 511, owner46)
            finally:
                p.set('capture_valid', 0)

    def native_input_page(self, request, operand, page):
        from tools.gpu_sys.canonical_qwen_native_rf_pump import OwnedPage
        _, p, t, owner55 = self._actor(request)
        uint(operand, 2, 'native operand'); uint(page, 1, 'native source page')
        need(p.get('context_live') and p.get('authority_tuple') == t
             and p.get('authority_owner') == owner55
             and p.get('authority_sequence') == request.get('sequence'), 'held native staging context')
        # The existing pump writes raw source bytes. It must never overwrite a
        # published readonly home; select only actual captured typed workspace.
        need((p.get('lease_workspace') >> operand) & 1, 'published source aperture is readonly; staging forbidden')
        need(not page or (p.get('lease_double') >> operand) & 1, 'logical source page not captured')
        bank = (p.get('lease_bank') >> (6*operand)) & 63
        slot = (p.get('lease_slots') >> (18*operand+9*page)) & 511
        version = (p.get('lease_version') >> (11*operand)) & 2047
        expected = (p.get('lease_owner') >> (46*operand)) & ((1<<46)-1)
        q = self.owners[bank]
        owner = q.resolve(t, version, slot, True, workspace=True)
        need(owner == expected, 'staging query does not match sealed original source owner')
        return OwnedPage(self.authority.RF[bank], q, t, slot, owner)
