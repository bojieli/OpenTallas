"""Actual W4 ACK_ID1 source-page transactors for the canonical Qwen server.

Ports: get(name), set(name,value), settle(), tick(), parameter(name). tick
advances an actual RF clock edge, settle/get sample before that edge. The
enclosing simulator supplies the shared-port arbiter and real owner authority;
this module does not allocate owners, access SRAM internals or reset a job.
"""
import hashlib

from tools.gpu_sys.canonical_qwen_transport import TransportError


class RFPorts:
    def __init__(self, ports):
        if ports.parameter("ACK_ID") != 1:
            raise TransportError("canonical RF requires actual ACK_ID1 provider")
        self.ports = ports
        self.pending = None
        self.stopped = False

    def _begin(self, slot, owner):
        if self.stopped or self.pending is not None:
            raise TransportError("RF pending/faulted owner; no reuse")
        if type(slot) is not int or not 0 <= slot < 512:
            raise TransportError("RF physical slot outside 512")
        if type(owner) is not int or not 0 <= owner < (1 << 46):
            raise TransportError("RF owner outside actual46 bits")
        self.pending = (slot, owner)

    def _fault(self):
        if self.ports.get("ack_identity_fault"):
            raise TransportError("actual RF identity protection fault")

    def _stop(self):
        self.stopped = True
        for name in ("wr_valid", "rd_valid", "ack_ready", "rsp_ready"):
            self.ports.set(name, 0)

    def write(self, slot, owner, payload):
        if type(payload) is not bytes or len(payload) != 512:
            raise TransportError("RF write requires actual4096-bit page")
        self._begin(slot, owner)
        p = self.ports
        try:
            p.set("wr_addr", slot)
            p.set("wr_owner", owner)
            p.set("wr_data", int.from_bytes(payload, "little"))
            p.set("wr_valid", 1)
            p.set("ack_ready", 0)
            while True:
                p.settle()
                self._fault()
                accepted = bool(p.get("wr_ready"))
                p.tick()
                if accepted:
                    break
            p.set("wr_valid", 0)
            while True:
                p.settle()
                self._fault()
                if p.get("ack_valid"):
                    actual = (p.get("ack_slot"), p.get("ack_owner"))
                    if actual != (slot, owner):
                        raise TransportError("RF held ACK slot/owner mismatch")
                    p.set("ack_ready", 1)
                    p.settle()
                    # Ready may affect enclosing arbitration. Resample the
                    # held tuple before the edge that actually consumes it.
                    self._fault()
                    if not p.get("ack_valid") or (p.get("ack_slot"), p.get("ack_owner")) != actual:
                        raise TransportError("RF ACK changed before acceptance")
                    p.tick()
                    p.set("ack_ready", 0)
                    self.pending = None
                    return actual
                p.tick()
        except BaseException:
            self._stop()
            raise

    def read(self, slot, owner):
        self._begin(slot, owner)
        p = self.ports
        try:
            p.set("rd_a", slot)
            p.set("rd_b", slot)
            p.set("rd_valid", 1)
            p.set("rsp_ready", 0)
            while True:
                p.settle()
                self._fault()
                accepted = bool(p.get("rd_ready"))
                p.tick()
                if accepted:
                    break
            p.set("rd_valid", 0)
            while True:
                p.settle()
                self._fault()
                if p.get("rsp_valid"):
                    a, b = p.get("rsp_a"), p.get("rsp_b")
                    if a != b or type(a) is not int or not 0 <= a < (1 << 4096):
                        raise TransportError("RF actual mirror read disagreement/width")
                    p.set("rsp_ready", 1)
                    p.settle()
                    self._fault()
                    if not p.get("rsp_valid") or (p.get("rsp_a"), p.get("rsp_b")) != (a, b):
                        raise TransportError("RF held capture changed before acceptance")
                    p.tick()
                    p.set("rsp_ready", 0)
                    self.pending = None
                    return a.to_bytes(512, "little")
                p.tick()
        except BaseException:
            self._stop()
            raise


class RFPageHandlers:
    """Server's two RF handlers using the actual enclosing issuer/lease owner.

    authority.resolve_source(request,write) returns (RFPorts, owner46) after
    acquiring the real shared-port grant for source_key's rank/SM/slot.
    authority.source_owner_retained(request,owner46) observes that exact live
    owner; no callback may create a success from a software dictionary.
    Port-grant release is owner-managed separately from source-lease retirement.
    """
    def __init__(self, authority):
        self.authority = authority
        self.stopped = False

    def _page(self, request, write):
        if self.stopped:
            raise TransportError("RF handler faulted; no further grants")
        try:
            key = request["source_key"]
            if (not isinstance(key, list) or len(key) != 4 or key[0] != "RF"
                or any(type(n) is not int for n in key[1:])
                or not 0 <= key[1] < 2 or not 0 <= key[2] < 32 or not 0 <= key[3] < 512):
                raise TransportError("source page is not an actual canonical RF home")
            if request["mirrors"] != 2:
                raise TransportError("actual RF has two operand mirrors")
            ports, owner = self.authority.resolve_source(request, write)
            if not isinstance(ports, RFPorts):
                raise TransportError("issuer must resolve actual RF port transactor")
            if write:
                payload = request["payload"]
                if hashlib.sha256(payload).hexdigest() != request["payload_sha256"]:
                    raise TransportError("source page write payload identity")
                ports.write(key[3], owner, payload)
            else:
                payload = ports.read(key[3], owner)
                if hashlib.sha256(payload).hexdigest() != request["payload_sha256"]:
                    raise TransportError("actual RF captured source page identity")
            if self.authority.source_owner_retained(request, owner) is not True:
                raise TransportError("actual source owner was not retained")
            result = {k: request[k] for k in ("program_sha256", "source_PC", "sequence",
                                             "source_key", "version", "lease", "payload_sha256")}
            # These successes follow actual RF write/capture acceptance above.
            # They are not publication, global retirement or reverse receipts.
            result.update(accepted=True, fault=False, owner_retained=True)
            if write:
                result["visible_copies"] = 2  # ACK_ID1 ACK follows both SRAM write edges.
            else:
                result.update(payload=payload, captured=True)
            return result
        except BaseException:
            self.stopped = True
            raise

    def source_page_write(self, request):
        return self._page(request, True)

    def source_page_read(self, request):
        return self._page(request, False)
