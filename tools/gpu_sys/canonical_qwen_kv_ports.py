"""Physical KV state/payload byte services over the actual W2 sector ports.

The original BoundKVStorage client owns its metadata arithmetic. Every state
and payload byte must be read/written through these handlers; there is no
software byte dictionary or zero-fill fallback here. The actual enclosing
issuer supplies source apertures, sector routing and protected caller owners.
"""
from tools.gpu_sys.canonical_qwen_transport import KV_KINDS, TransportError, W2PrimaryPort


class KVByteHandlers:
    """Four services sharing DeliverySession's existing sequence/identity.

    authority.kv_aperture(request,region) -> (source_base,source_bytes), checked
    against the selected current native extent and actual rank/lease.
    authority.resolve_kv_sector(request,address,we) -> (W2PrimaryPort,client,
    physical_address,original_customer_tag,generation) under a real full-sector
    grant. Partial writes need that grant across both read and write; padding
    or adjacent bytes must not be invented or overwritten.
    authority.kv_owner_retained(request) observes actual matching owner state.
    This module never derives a protected owner from native PC or packs tags.
    """
    def __init__(self, authority):
        self.authority = authority
        self.stopped = False
        self.pending = None
        self.handlers = {kind: self._handler(kind) for kind in KV_KINDS}

    def _sector(self, request, address, payload=None):
        route = self.authority.resolve_kv_sector(request, address, payload is not None)
        if not isinstance(route, tuple) or len(route) != 5 or not isinstance(route[0], W2PrimaryPort):
            raise TransportError("KV sector must resolve actual W2 port and original owner")
        port, client, physical_address, tag, generation = route
        return port.sector(client, physical_address, tag, generation, write=payload)

    def _handler(self, kind):
        def transact(request):
            if self.stopped or self.pending is not None:
                raise TransportError("KV pending/faulted source; no reuse")
            self.pending = (kind, request)
            try:
                write = kind.endswith("write")
                region = "state" if kind.startswith("kv_state_") else "payload"
                rank = request["rank"]
                if type(rank) is not int or not 0 <= rank < 2:
                    raise TransportError("KV rank outside canonical source")
                base, size = self.authority.kv_aperture(request, region)
                if (type(base) is not int or type(size) is not int or base < 0 or size <= 0
                    or request.get("base") != base or request.get("bytes") != size):
                    raise TransportError("KV actual source extent mismatch")
                offset = request["offset"]
                payload = request.get("payload")
                count = len(payload) if write and type(payload) is bytes else request.get("count")
                if (type(offset) is not int or type(count) is not int or count <= 0
                    or offset < 0 or offset + count > size or (write and type(payload) is not bytes)):
                    raise TransportError("KV physical byte aperture")
                start, end = base + offset, base + offset + count
                result = bytearray()
                for sector in range(start // 32 * 32, end, 32):
                    lo, hi = max(start, sector) - sector, min(end, sector + 32) - sector
                    if write:
                        if lo == 0 and hi == 32:
                            data = payload[sector - start:sector - start + 32]
                        else:
                            # Preserve every untouched byte from actual backing
                            # SRAM/HBM, including extent padding. The source
                            # mapper must grant the whole RMW sector lifetime.
                            old = self._sector(request, sector)["payload"]
                            if type(old) is not bytes or len(old) != 32:
                                raise TransportError("KV actual partial-sector capture")
                            data = bytearray(old)
                            data[lo:hi] = payload[sector + lo - start:sector + hi - start]
                            data = bytes(data)
                        self._sector(request, sector, data)
                    else:
                        data = self._sector(request, sector)["payload"]
                        if type(data) is not bytes or len(data) != 32:
                            raise TransportError("KV actual sector capture")
                        result.extend(data[lo:hi])
                if self.authority.kv_owner_retained(request) is not True:
                    raise TransportError("KV source owner not retained")
                response = {k: request[k] for k in ("program_sha256", "source_PC", "sequence")}
                response.update(rank=rank, base=base, bytes=size, offset=offset, count=count,
                                accepted=True, fault=False, owner_retained=True,
                                reverse_validated=True)
                if write:
                    response["write_completed"] = True
                else:
                    response.update(payload=bytes(result), captured=True)
                self.pending = None
                return response
            except BaseException:
                self.stopped = True
                # The actual owner's source/RMW grants remain pending. No
                # software retirement, reset/retry, zero seed or memory clear.
                raise
        return transact
