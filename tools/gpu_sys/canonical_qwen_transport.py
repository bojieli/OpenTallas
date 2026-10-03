"""Persistent canonical Qwen delivery server, opt-in and without a simulator launcher.

Run from the repository root with ``python3 -m tools.gpu_sys.canonical_qwen_transport``.
The simulator supplies the sixteen handlers for a complete token; each must wait for its actual
owner/ACK/consumer/reverse acceptance before returning. This adapter never
creates successful acknowledgements, evaluates arithmetic, or replaces memory.
The pipe mode attaches inherited control pipes of an already-running simulator.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import socket

from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA, wire_decode, wire_encode

KINDS = ("source_page_write", "source_page_read", "source_publish", "source_retire",
         "immutable_source_transfer", "native_primitive")
KV_KINDS = ("kv_state_read", "kv_state_write", "kv_begin", "kv_stage_write",
            "kv_commit", "kv_publish", "kv_acquire", "kv_payload_read",
            "kv_consumer_done", "kv_reader_release")
ALL_KINDS = KINDS + KV_KINDS
IDENTITY = ("program_sha256", "source_PC", "sequence")


class TransportError(RuntimeError):
    pass


class W2PrimaryPort:
    """Sector transactor on the actual NC6 primary's client ports.

    Claude's simulator port object implements get(name), set_client(client,
    name,value), settle(), tick() and parameter(name). tick advances one W2
    clock edge; get/settle sample combinational offers BEFORE that edge.
    The caller authority implements completion_ready(client,tag,generation,we)
    and reverse_validated(client,tag,generation,we) from actual downstream
    capture/reverse ports. No default ready/clean/fence or elapsed completion.
    Provider ports (including p_wr_done_ready), fences and repair_busy remain
    connected in the enclosing RTL. Addresses/tags come from its real mapper.
    """
    def __init__(self, ports, authority):
        self.ports, self.authority = ports, authority
        self.pending = None
        self.stopped = False
        required = dict(NC=6, MAX_OUT=16, AW=34, CTAGW=32, GENW=4, PTAGW=35, OPT_EXACT=1, OPT_RESET_QUARANTINE=1)
        try:
            matches = all(ports.parameter(k) == v for k, v in required.items())
        except LookupError as exc:
            raise TransportError("W2 reset-safe parameter interface missing") from exc
        if not matches:
            raise TransportError("W2 actual NC6 widths/opt-in differ")
        if not 0 <= ports.parameter("PC_ID") < 128:
            raise TransportError("W2 physical PC identity out of range")
        for name in ("completion_ready", "reverse_validated"):
            if not callable(getattr(authority, name, None)):
                raise TransportError("missing actual W2 caller authority " + name)

    def sector(self, client, address, tag, generation, write=None):
        if self.stopped or self.pending is not None:
            raise TransportError("W2 pending/faulted; no owner reuse")
        for name, value, width in (("client", client, 3), ("address", address, 34),
                                   ("tag", tag, 32), ("generation", generation, 4)):
            if type(value) is not int or not 0 <= value < (1 << width):
                raise TransportError("invalid W2 " + name)
        if client >= 6 or address % 32:
            raise TransportError("W2 client or 32B sector alignment")
        if write is not None and (type(write) is not bytes or len(write) != 32):
            raise TransportError("W2 write requires actual 256-bit sector")
        we = write is not None
        p = self.ports
        self.pending = (client, address, tag, generation, we)
        try:
            p.set_client(client, "c_req_v", 1)
            p.set_client(client, "c_req_we", int(we))
            p.set_client(client, "c_req_addr", address)
            p.set_client(client, "c_req_tag", tag)
            p.set_client(client, "c_req_gen", generation)
            p.set_client(client, "c_req_data", int.from_bytes(write, "little") if we else 0)
            accepted = False
            result = None
            vname = "c_wr_done_v" if we else "c_rsp_v"
            tname = "c_wr_done_tag" if we else "c_rsp_tag"
            gname = "c_wr_done_gen" if we else "c_rsp_gen"
            rname = "c_wr_done_rdy" if we else "c_rsp_rdy"
            while result is None:
                ready = self.authority.completion_ready(client, tag, generation, we)
                if type(ready) is not bool:
                    raise TransportError("W2 capture authority must return actual boolean")
                p.set_client(client, rname, int(ready))
                p.settle()
                if p.get("fault"):
                    raise TransportError("actual W2 fault; pending owner retained")
                req_edge = not accepted and bool((p.get("c_req_rdy") >> client) & 1)
                valid = bool((p.get(vname) >> client) & 1)
                if p.get("repair_busy") and (req_edge or (valid and ready)):
                    raise TransportError("W2 normal acceptance during actual repair")
                if valid:
                    returned_tag = (p.get(tname) >> (32 * client)) & 0xffffffff
                    returned_gen = (p.get(gname) >> (4 * client)) & 0xf
                    if (returned_tag, returned_gen) != (tag, generation):
                        raise TransportError("W2 completion tag/generation mismatch")
                    if not accepted:
                        raise TransportError("W2 completion before actual request acceptance")
                    if ready:
                        bits = (p.get("c_rsp_data") >> (256 * client)) & ((1 << 256) - 1)
                        result = dict(client=client, tag=returned_tag, generation=returned_gen,
                                      write=we, payload=None if we else bits.to_bytes(32, "little"))
                p.tick()
                if req_edge:
                    accepted = True
                    p.set_client(client, "c_req_v", 0)
            p.set_client(client, rname, 0)
            # Local completion is not the real reverse/consumer release. Wait
            # for the caller's matching authority; never read a global clean
            # bit or set reverse_fenced/provider_fenced/reset_fenced here.
            while True:
                reverse = self.authority.reverse_validated(client, tag, generation, we)
                if type(reverse) is not bool:
                    raise TransportError("W2 reverse authority must return actual boolean")
                p.settle()
                if p.get("fault"):
                    raise TransportError("actual W2 fault before reverse acceptance")
                if reverse:
                    break
                p.tick()
            self.pending = None
            return result
        except BaseException:
            self.stopped = True
            # Stop only this client's new offers; do not rearm, reset, clean
            # any debt, alter provider/fence ports or signal a simulator job.
            p.set_client(client, "c_req_v", 0)
            p.set_client(client, "c_rsp_rdy", 0)
            p.set_client(client, "c_wr_done_rdy", 0)
            raise


def encode(message):
    return json.dumps(wire_encode(message), separators=(",", ":"), allow_nan=False).encode() + b"\n"


def decode(line):
    if not line or not line.endswith(b"\n"):
        raise TransportError("simulator/driver EOF or incomplete reply")
    return wire_decode(json.loads(line))


class SimulatorPipes:
    """Attach existing simulator RPC pipes; never spawn, retry or terminate it.

    Input: one Ampere wire-encoded {kind,request} JSON line per command.
    Output: one wire-encoded reply object with matched identity and actual
    completion fields. Diagnostics belong on the simulator's separate stderr.
    Descriptors are duplicated so closing this adapter preserves owner handles.
    """
    def __init__(self, read_fd, write_fd):
        self.reader = os.fdopen(os.dup(read_fd), "rb")
        self.writer = os.fdopen(os.dup(write_fd), "wb", buffering=0)
        self.stopped = False
        self.handlers = {kind: self._handler(kind) for kind in ALL_KINDS}

    def _handler(self, kind):
        def transact(request):
            if self.stopped:
                raise TransportError("simulator pipe session faulted; no retry")
            try:
                raw = encode(dict(kind=kind, request=request))
                # Unbuffered pipe writes can be short for full checkpoint pages.
                view = memoryview(raw)
                while view:
                    n = self.writer.write(view)
                    if not n:
                        raise TransportError("simulator input pipe closed")
                    view = view[n:]
                return decode(self.reader.readline())
            except BaseException:
                self.stopped = True
                raise
        return transact

    def close(self):
        self.reader.close()
        self.writer.close()


class DeliverySession:
    """One synchronous caller with retained failure debt, no implicit rearm."""
    def __init__(self, handlers, *, require_kv=False):
        # Six-handler sessions exist only for component fixtures. A complete
        # token and any backend enrolling KV must provide its entire lifecycle.
        kinds = ALL_KINDS if require_kv or any(k in handlers for k in KV_KINDS) else KINDS
        missing = [kind for kind in kinds if not callable(handlers.get(kind))]
        if missing:
            raise TransportError("missing simulator handlers: " + ", ".join(missing))
        self.handlers = {kind: handlers[kind] for kind in kinds}
        self.sequence = 0
        self.stopped = False
        self.pending = None

    def transact(self, message):
        if self.stopped:
            raise TransportError("delivery session faulted; no further grants")
        self.pending = message
        try:
            if not isinstance(message, dict) or set(message) != {"kind", "request"}:
                raise TransportError("expected delivery kind/request")
            kind, request = message["kind"], message["request"]
            if kind not in self.handlers or not isinstance(request, dict):
                raise TransportError("unknown delivery kind or invalid request")
            if request.get("program_sha256") != PROGRAM_SHA:
                raise TransportError("noncanonical/reduced Qwen dispatcher")
            if type(request.get("sequence")) is not int or request["sequence"] != self.sequence:
                raise TransportError("duplicate/out-of-order delivery sequence")
            if type(request.get("source_PC")) is not int or not -1 <= request["source_PC"] < 1737:
                raise TransportError("source PC outside canonical1737")
            # Identity snapshot predates peer invocation; handler mutation must
            # not retag a late completion into a new source owner.
            identity = {k: request[k] for k in IDENTITY}
            reply = self.handlers[kind](request)
            if not isinstance(reply, dict):
                raise TransportError("simulator reply is not an object")
            if any(type(reply.get(k)) is not type(identity[k]) or reply.get(k) != identity[k] for k in IDENTITY):
                raise TransportError("simulator completion identity mismatch")
            if reply.get("accepted") is not True or reply.get("fault") is not False:
                raise TransportError("simulator completion rejected or faulted")
            self.sequence += 1
            self.pending = None
            return reply
        except BaseException:
            self.stopped = True
            # Keep pending source/lease debt for the simulator owner. No release
            # callback, current-clean substitution or reset is issued here.
            raise

    def serve(self, stream):
        while True:
            line = stream.readline()
            if not line:
                return  # Caller EOF is not a token PASS or an RTL drain.
            message = None
            try:
                message = decode(line)
                reply = self.transact(message)
                stream.write(encode(reply))
                stream.flush()
            except Exception as exc:
                self.stopped = True
                request = message.get("request", {}) if isinstance(message, dict) else {}
                if not isinstance(request, dict):
                    request = {}
                # An error reply is explicitly negative, never an ACK receipt.
                error = {k: request.get(k) for k in IDENTITY}
                error.update(accepted=False, fault=True, error=str(exc))
                try:
                    stream.write(encode(error))
                    stream.flush()
                finally:
                    raise


class UnixDeliveryServer:
    """One existing simulator/canonical caller pair, no listener reconnect loop."""
    def __init__(self, path: Path, handlers, *, require_kv=False):
        self.session = DeliverySession(handlers, require_kv=require_kv)
        self.path = Path(path)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.inode = None
        try:
            # Bind refuses existing sockets/files instead of stealing an active
            # owner's endpoint. Only this newly created endpoint is removed.
            self.listener.bind(str(self.path))
            self.inode = self.path.stat().st_ino
            self.path.chmod(0o600)
            self.listener.listen(1)
        except BaseException:
            self.close()
            raise

    def serve_once(self):
        connection, _ = self.listener.accept()
        with connection, connection.makefile("rwb") as stream:
            self.session.serve(stream)

    def close(self):
        self.listener.close()
        if self.inode is not None:
            try:
                if self.path.lstat().st_ino == self.inode:
                    self.path.unlink()
            except FileNotFoundError:
                pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--enable-canonical-qwen", action="store_true", required=True)
    p.add_argument("--socket", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backend", help="module:factory returning actual simulator handlers dict")
    mode.add_argument("--simulator-read-fd", type=int)
    p.add_argument("--simulator-write-fd", type=int)
    a = p.parse_args()
    pipes = None
    if a.backend:
        if a.simulator_write_fd is not None:
            p.error("write-fd belongs to pipe mode")
        module, factory = a.backend.split(":", 1)
        handlers = getattr(importlib.import_module(module), factory)()
    else:
        if a.simulator_write_fd is None:
            p.error("pipe mode requires --simulator-write-fd")
        pipes = SimulatorPipes(a.simulator_read_fd, a.simulator_write_fd)
        handlers = pipes.handlers
    server = None
    try:
        server = UnixDeliveryServer(a.socket, handlers, require_kv=True)
        print(f"Canonical1737 delivery socket ready: {a.socket}", flush=True)
        server.serve_once()
    finally:
        if server is not None:
            server.close()
        if pipes is not None:
            pipes.close()


if __name__ == "__main__":
    main()
