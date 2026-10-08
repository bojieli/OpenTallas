"""Physical KV services matching Ampere's released 155351be5 client.

Byte reads/writes use actual W2. Seven lifecycle callbacks must use the real
writer/staging/visibility/consumer/reverse/all-copy controller, not a dictionary.
All ten operations share the existing DeliverySession sequence.
"""
import copy
import hashlib
from tools.gpu_sys.canonical_qwen_transport import TransportError, W2PrimaryPort

BYTE_KINDS = ("kv_state_write", "kv_state_read", "kv_payload_read")
CONTROL_KINDS = ("kv_begin", "kv_stage_write", "kv_commit", "kv_publish",
                 "kv_acquire", "kv_consumer_done", "kv_reader_release")
CONTROL_FIELDS = {
    "kv_begin": ("tag", "key"), "kv_stage_write": ("tag", "key"),
    "kv_commit": ("tag", "key"), "kv_publish": ("tag", "key"),
    "kv_acquire": ("lease", "key", "producer_tag"),
    "kv_consumer_done": ("lease", "key", "stage"), "kv_reader_release": ("lease", "key")}
CONTROL_ACKS = {
    "kv_begin": ("writer_retained",), "kv_stage_write": ("staged", "writer_retained"),
    "kv_commit": ("all_writes_visible", "writer_retained"),
    "kv_publish": ("published", "state_visible"), "kv_acquire": ("owner_retained",),
    "kv_consumer_done": ("consumer_accepted", "reverse_validated"),
    "kv_reader_release": ("all_consumers_accepted", "all_reverse_validated", "all_copies_drained")}


class KVByteHandlers:
    """Authority resolves actual source extent and protected sector owner.

    kv_aperture(request,"state") -> actual (base,bytes).
    kv_payload_address_valid(request,address) checks layer/rank/producer lease.
    resolve_kv_sector(request,address,we) -> (W2PrimaryPort,client,physical_addr,
    original_customer_tag,generation), with actual sector grant held across RMW.
    kv_owner_retained(request) observes the matching physical source owner.
    """
    def __init__(self, authority):
        self.authority = authority
        self.stopped = False
        self.pending = None
        self.handlers = {k: self._handler(k) for k in BYTE_KINDS}

    def _sector(self, request, address, payload=None):
        route = self.authority.resolve_kv_sector(request, address, payload is not None)
        if not isinstance(route, tuple) or len(route) != 5 or not isinstance(route[0], W2PrimaryPort):
            raise TransportError("KV sector must resolve actual W2 port and original owner")
        port, client, physical_address, tag, generation = route
        return port.sector(client, physical_address, tag, generation, write=payload)

    def _read_sector(self, request, address):
        raw = self._sector(request, address)["payload"]
        if type(raw) is not bytes or len(raw) != 32:
            raise TransportError("KV actual sector capture")
        return raw

    def _state(self, request, write):
        base, size = self.authority.kv_aperture(request, "state")
        address = request["address"]
        payload = request.get("payload")
        count = len(payload) if write and type(payload) is bytes else request.get("bytes")
        if (type(base) is not int or type(size) is not int or size <= 0 or base < 0
            or type(address) is not int or type(count) is not int or count < 0
            or address < base or address + count > base + size
            or (write and type(payload) is not bytes)):
            raise TransportError("KV physical state aperture")
        end, result = address + count, bytearray()
        for sector in range(address // 32 * 32, end, 32) if count else ():
            lo, hi = max(address, sector) - sector, min(end, sector + 32) - sector
            if write:
                if lo == 0 and hi == 32:
                    data = payload[sector - address:sector - address + 32]
                else:
                    data = bytearray(self._read_sector(request, sector))
                    data[lo:hi] = payload[sector + lo - address:sector + hi - address]
                    data = bytes(data)
                self._sector(request, sector, data)
            else:
                result.extend(self._read_sector(request, sector)[lo:hi])
        response = dict(rank=request["rank"], address=address)
        if write:
            response.update(payload_sha256=hashlib.sha256(payload).hexdigest(), visible=True)
        else:
            response.update(payload=bytes(result), captured=True)
        return response

    def _payload(self, request):
        addresses = request["addresses"]
        if (not isinstance(addresses, list) or len(addresses) > 128
            or any(type(a) is not int or a < 0 for a in addresses)):
            raise TransportError("KV source128-byte address window")
        for address in addresses:
            if self.authority.kv_payload_address_valid(request, address) is not True:
                raise TransportError("KV actual payload lease/aperture")
        result, captured = bytearray(), {}
        # Cache only returned captures inside this one held-reader RPC, never
        # a local backing dictionary or data carried across lease advance.
        for address in addresses:
            sector = address // 32 * 32
            if sector not in captured:
                captured[sector] = self._read_sector(request, sector)
            result.append(captured[sector][address % 32])
        return dict(lease=request["lease"], key=request["key"], addresses=addresses,
                    payload=bytes(result), captured=True, owner_retained=True)

    def _handler(self, kind):
        def transact(request):
            if self.stopped or self.pending is not None:
                raise TransportError("KV pending/faulted source; no reuse")
            self.pending = (kind, request)
            try:
                if type(request.get("rank")) is not int or not 0 <= request["rank"] < 2:
                    raise TransportError("KV rank outside canonical source")
                result = self._payload(request) if kind == "kv_payload_read" else self._state(request, kind.endswith("write"))
                if self.authority.kv_owner_retained(request) is not True:
                    raise TransportError("KV source owner not retained")
                result.update({k: request[k] for k in ("program_sha256", "source_PC", "sequence")})
                result.update(accepted=True, fault=False)
                self.pending = None
                return result
            except BaseException:
                self.stopped = True
                raise  # No source/RMW retirement, reset/retry or byte clear.
        return transact


class KVHandlers:
    """Enroll all ten with seven real controller functions, no synthetic ACKs."""
    def __init__(self, authority, control):
        if set(control) != set(CONTROL_KINDS) or any(not callable(control[k]) for k in CONTROL_KINDS):
            raise TransportError("all seven actual KV lifecycle handlers required")
        self.bytes = KVByteHandlers(authority)
        self.stopped = False
        self.handlers = dict(self.bytes.handlers)
        self.handlers.update({k: self._control(k, control[k]) for k in CONTROL_KINDS})

    def _control(self, kind, actual):
        def invoke(request):
            if self.stopped or self.bytes.stopped:
                raise TransportError("KV lifecycle faulted; no further grants")
            try:
                identity = copy.deepcopy({k: request[k] for k in ("program_sha256", "source_PC", "sequence") + CONTROL_FIELDS[kind]})
                payload_sha = hashlib.sha256(request["payload"]).hexdigest() if kind == "kv_stage_write" else None
                response = actual(request)
                if not isinstance(response, dict) or any(type(response.get(k)) is not type(v) or response.get(k) != v for k, v in identity.items()):
                    raise TransportError("KV actual lifecycle completion identity mismatch")
                if (response.get("accepted") is not True or response.get("fault") is not False
                    or any(response.get(k) is not True for k in CONTROL_ACKS[kind])):
                    raise TransportError("KV actual lifecycle completion missing")
                if payload_sha is not None and response.get("payload_sha256") != payload_sha:
                    raise TransportError("KV actual staged byte identity mismatch")
                return response
            except BaseException:
                self.stopped = self.bytes.stopped = True
                raise
        return invoke
