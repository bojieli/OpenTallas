"""Clock-edge adapter between Dewey's real payload engine and reset-safe W2.

Claude's enclosing simulator calls before_edge(), advances the SAME controller
and W2 clock edge, then after_edge(). No clock is spawned here. The adapter
drives only payload request readiness/receipts and the selected W2 client.
No controller, memory, ready/fence oracle, arithmetic or reset is implemented.

Controller ABI: Dewey d41782e0417dd13f4befea958348dc7928342d26,
rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv
(SHA256 dc5857a61d3fdfb188888b9d8f6d30a8b4b0dbcc4afca6438c699884fe35396c).
stage_SM/shared_SM/rank are connected by the enclosing shared-service mapper;
this backend never chooses or drives a staging location. Its sector authority
must serialize other writers to the held physical K sector, including users
outside this adapter. W2 caller credit retirement is not that sector release.
"""
from dataclasses import dataclass
from tools.gpu_sys.canonical_qwen_transport import TransportError, W2PrimaryPort


@dataclass(frozen=True)
class PayloadRoute:
    port: W2PrimaryPort
    client: int
    address: int
    tag: int
    generation: int
    grant: object


class PayloadW2Adapter:
    """Hold an actual sector grant through OLD_REQ -> NEW_ACK -> reverse.

    authority.acquire_payload_sector(offer) returns None until an actual grant,
    otherwise PayloadRoute with ORIGINAL customer32/gen4/physicaladdr34.
    authority.continue_payload_rmw(grant,offer) maps the matching NEW request
    under the SAME grant. It may return None while real routing is pending.
    authority.release_payload_sector(grant,offer) returns True ONLY once its
    actual release handshake is accepted. False keeps the grant live.
    W2 port's authority.reverse_validated(client,tag,gen,we) must observe the
    exact actual reverse, never global idle/clean or a fixed elapsed delay.
    """
    def __init__(self, controller, authority, *, enabled=False):
        if not enabled or controller.parameter('ENABLE') != 1:
            raise TransportError('payload W2 adapter default off')
        for name in ('acquire_payload_sector', 'continue_payload_rmw', 'release_payload_sector'):
            if not callable(getattr(authority, name, None)):
                raise TransportError('missing actual payload sector authority ' + name)
        self.controller, self.authority = controller, authority
        self.state = 'IDLE'
        self.offer = self.route = None
        self.waiting_offer = None
        self.rmw = None
        self.data = 0
        self.capture_offer = None
        self.faulted = False
        self.event = None
        self.edge_open = False
        self.accepted = 0
        self.captured = 0
        self.reversed = 0

    @staticmethod
    def _uint(value, bits, name):
        if type(value) is not int or not 0 <= value < 1 << bits:
            raise TransportError('payload actual ' + name)
        return value

    def _offer(self):
        p = self.controller
        o = {name: p.get('payload_req_' + name) for name in
             ('write', 'sector', 'source_addr', 'data', 'rmw', 'rmw_last')}
        o.update(identity=p.get('writer_identity'), key=p.get('writer_key'))
        for name, width in (('identity', 64), ('key', 20), ('sector', 9),
                            ('source_addr', 34), ('data', 256), ('write', 1), ('rmw', 1), ('rmw_last', 1)):
            self._uint(o[name], width, name)
        if o['sector'] >= 272 or o['source_addr'] % 32:
            raise TransportError('payload source sector/address')
        if o['rmw'] != int(o['sector'] < 256):
            raise TransportError('payload K/V RMW classification')
        if o['rmw_last'] != (o['write'] if o['rmw'] else 0) or (not o['rmw'] and not o['write']):
            raise TransportError('payload OLD/NEW request classification')
        if not p.get('writer_retained'):
            raise TransportError('payload actual writer not retained')
        return o

    @staticmethod
    def _context(o):
        return tuple(o[k] for k in ('identity', 'key', 'sector', 'source_addr'))

    def _check_route(self, route):
        if not isinstance(route, PayloadRoute) or not isinstance(route.port, W2PrimaryPort) or route.grant is None:
            raise TransportError('payload must resolve actual W2 route and grant')
        p = route.port.ports
        for name, want in dict(NC=6, MAX_OUT=16, AW=34, CTAGW=32, GENW=4,
                               PTAGW=35, OPT_EXACT=1, OPT_RESET_QUARANTINE=1).items():
            if p.parameter(name) != want:
                raise TransportError('payload requires R7 reset-quarantine W2 widths/selection')
        for name, value, width in (('client', route.client, 3), ('address', route.address, 34),
                                   ('tag', route.tag, 32), ('generation', route.generation, 4)):
            self._uint(value, width, name)
        if route.client >= 6 or route.address % 32 or not 0 <= p.parameter('PC_ID') < 128:
            raise TransportError('payload physical W2 destination')
        if route.port.stopped or route.port.pending is not None:
            raise TransportError('W2 port already owned/faulted; no overlapping adapter')
        if self.rmw is not None and route.grant is not self.rmw[1]:
            raise TransportError('K RMW sector grant changed before NEW_ACK reverse')
        if self.rmw is not None:
            old = self.rmw[2]
            if (route.port is not old.port or
                    (route.client, route.address, route.tag, route.generation) !=
                    (old.client, old.address, old.tag, old.generation)):
                raise TransportError('K RMW original physical client/tag/gen/address changed')

    def _drive_request(self):
        r, o = self.route, self.offer
        p = r.port.ports
        for name, value in dict(c_req_v=1, c_req_we=o['write'], c_req_addr=r.address,
                                c_req_tag=r.tag, c_req_gen=r.generation, c_req_data=o['data'],
                                c_rsp_rdy=0, c_wr_done_rdy=0).items():
            p.set_client(r.client, name, value)
        p.settle()

    def _receipt(self, visible, reverse):
        p, o = self.controller, self.offer
        for name, value in dict(payload_valid=1, payload_identity=o['identity'], payload_key=o['key'],
                                payload_sector=o['sector'], payload_source_addr=o['source_addr'],
                                payload_write=o['write'], payload_visible=visible,
                                payload_reverse=reverse, payload_rdata=self.data).items():
            p.set(name, value)
        p.settle()

    def _fault(self):
        self.faulted = True
        self.controller.set('payload_req_ready', 0)
        self.controller.set('payload_valid', 0)
        routes = [self.route, self.rmw[2] if self.rmw else None]
        for retained in routes:
            if not isinstance(retained, PayloadRoute) or not isinstance(retained.port, W2PrimaryPort):
                continue
            p, client = retained.port.ports, retained.client
            retained.port.stopped = True
            if type(client) is int and 0 <= client < 6:
                for name in ('c_req_v', 'c_rsp_rdy', 'c_wr_done_rdy'):
                    p.set_client(client, name, 0)
        # offer/route/rmw/pending retain original accepted identities. No reset,
        # grant release, fence setting, generation reuse or external debt clear.

    def before_edge(self):
        if self.faulted or self.edge_open:
            raise TransportError('payload adapter faulted or edge not completed')
        self.edge_open = True
        self.event = None
        p = self.controller
        try:
            p.set('payload_req_ready', 0)
            p.set('payload_valid', 0)
            p.settle()
            if p.get('fault') or not p.get('por_n'):
                raise TransportError('controller fault/reset; retained external payload debt')
            retained = self.route or (self.rmw[2] if self.rmw else None)
            if retained is not None and retained.port.ports.get('fault'):
                raise TransportError('actual W2 fault/reset quarantine; retain payload debt')
            owner = self.offer or (dict(zip(('identity', 'key'), self.rmw[0][:2])) if self.rmw else None)
            if owner is not None and (not p.get('writer_retained') or
                    (p.get('writer_identity'), p.get('writer_key')) != (owner['identity'], owner['key'])):
                raise TransportError('actual payload writer changed/lost with retained sector debt')
            if not p.get('run_enable'):
                # Pause offers, not the retained sector grant or external debt.
                if self.state == 'OFFER':
                    raise TransportError('controller paused with held W2 request; retain debt')
                if self.route is not None:
                    for name in ('c_req_v', 'c_rsp_rdy', 'c_wr_done_rdy'):
                        self.route.port.ports.set_client(self.route.client, name, 0)
                return
            if self.waiting_offer is not None and (
                    not p.get('payload_req_valid') or self._offer() != self.waiting_offer):
                raise TransportError('controller request changed while awaiting actual sector grant')
            if self.state == 'IDLE' and p.get('payload_req_valid'):
                offered = self._offer()
                self.waiting_offer = dict(offered)
                if self.rmw is not None:
                    if (self._context(offered) != self.rmw[0] or not offered['rmw_last']):
                        raise TransportError('K RMW NEW request differs from retained OLD owner/sector')
                    route = self.authority.continue_payload_rmw(self.rmw[1], dict(offered))
                else:
                    if offered['rmw_last']:
                        raise TransportError('K RMW write without retained OLD sector grant')
                    route = self.authority.acquire_payload_sector(dict(offered))
                if route is not None:
                    # Retain returned grant/route even when its validation fails.
                    self.offer, self.route = offered, route
                    self._check_route(route)
                    self.offer, self.route, self.state = offered, route, 'OFFER'
                    self.waiting_offer = None
                    route.port.pending = ('payload', dict(offered), route.client, route.address, route.tag, route.generation)
            if self.state == 'OFFER':
                if not p.get('payload_req_valid') or self._offer() != self.offer:
                    raise TransportError('held controller payload request changed')
                self._drive_request()
                r = self.route
                ready = bool((r.port.ports.get('c_req_rdy') >> r.client) & 1)
                if r.port.ports.get('repair_busy') and ready:
                    raise TransportError('W2 request accepted during repair')
                p.set('payload_req_ready', int(ready))
                p.settle()
                if ready:
                    self.event = 'REQUEST'
            elif self.state == 'CAPTURE':
                r, o = self.route, self.offer
                w = r.port.ports
                stem = 'c_wr_done' if o['write'] else 'c_rsp'
                valid = bool((w.get(stem + '_v') >> r.client) & 1)
                if self.capture_offer is not None and not valid:
                    raise TransportError('held W2 completion withdrawn before capture')
                if valid:
                    tag = (w.get(stem + '_tag') >> (r.client * 32)) & 0xffffffff
                    gen = (w.get(stem + '_gen') >> (r.client * 4)) & 0xf
                    if (tag, gen) != (r.tag, r.generation):
                        raise TransportError('actual W2 completion original tag/generation mismatch')
                    if not o['write']:
                        self.data = (w.get('c_rsp_data') >> (r.client * 256)) & ((1 << 256) - 1)
                    captured = (tag, gen, self.data if not o['write'] else None)
                    if self.capture_offer is not None and captured != self.capture_offer:
                        raise TransportError('held W2 completion changed during capture backpressure')
                    self.capture_offer = captured
                    self._receipt(1, 0)
                    ready = bool(p.get('payload_ready'))
                    if w.get('repair_busy') and ready:
                        raise TransportError('W2 completion during repair')
                    w.set_client(r.client, stem + '_rdy', int(ready))
                    w.settle()
                    final = ((w.get(stem + '_v') >> r.client) & 1,
                             (w.get(stem + '_tag') >> (r.client * 32)) & 0xffffffff,
                             (w.get(stem + '_gen') >> (r.client * 4)) & 0xf)
                    if final != (1, r.tag, r.generation) or w.get('fault'):
                        raise TransportError('actual W2 completion changed before capture edge')
                    if not o['write'] and self.data != (
                            (w.get('c_rsp_data') >> (r.client * 256)) & ((1 << 256) - 1)):
                        raise TransportError('actual W2 read data changed before capture edge')
                    if ready:
                        self.event = 'CAPTURE'
            elif self.state == 'REVERSE':
                r, o = self.route, self.offer
                reverse = r.port.authority.reverse_validated(r.client, r.tag, r.generation, bool(o['write']))
                if type(reverse) is not bool:
                    raise TransportError('actual W2 reverse must be a boolean observation')
                if reverse:
                    self._receipt(0, 1)
                    if p.get('payload_ready'):
                        self.event = 'REVERSE'
            elif self.state == 'RELEASE':
                released = self.authority.release_payload_sector(self.route.grant, dict(self.offer))
                if type(released) is not bool:
                    raise TransportError('actual sector release must be a boolean handshake')
                if released:
                    self.event = 'RELEASE'
        except BaseException:
            self._fault()
            raise

    def after_edge(self):
        if self.faulted or not self.edge_open:
            raise TransportError('payload adapter has no valid sampled edge')
        self.edge_open = False
        if self.event == 'REQUEST':
            self.route.port.ports.set_client(self.route.client, 'c_req_v', 0)
            self.accepted += 1
            self.capture_offer = None
            self.state = 'CAPTURE'
        elif self.event == 'CAPTURE':
            stem = 'c_wr_done' if self.offer['write'] else 'c_rsp'
            self.route.port.ports.set_client(self.route.client, stem + '_rdy', 0)
            self.captured += 1
            self.state = 'REVERSE'
        elif self.event == 'REVERSE':
            self.reversed += 1
            self.route.port.pending = None  # Matching caller/reverse accepted.
            if self.offer['rmw'] and not self.offer['rmw_last']:
                self.rmw = (self._context(self.offer), self.route.grant, self.route)
                self.offer = self.route = None
                self.state = 'IDLE'  # Sector grant remains live, NOT released.
            else:
                self.state = 'RELEASE'
        elif self.event == 'RELEASE':
            self.offer = self.route = self.rmw = None
            self.state = 'IDLE'
        self.event = None
