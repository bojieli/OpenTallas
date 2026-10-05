"""Enclosing pin/clock owner and all-sixteen-handler canonical Qwen server.

Attach the actual compiled pin_driver.cpp through inherited pipes. No simulator
is launched or reset here. The source owner supplies the real issuer/native
mapper; unavailable ports/handlers are refused, never replaced with defaults.
The socket consumes the unchanged complete1737 client's wire protocol.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import threading

from tools.gpu_sys.canonical_qwen_transport import ALL_KINDS, TransportError, UnixDeliveryServer
from tools.gpu_sys.canonical_qwen_rf_ports import RFPageHandlers
from tools.gpu_sys.canonical_qwen_kv_ports import KVHandlers
from tools.gpu_sys.canonical_qwen_kv_controller import KVControllerPort
from tools.gpu_sys.canonical_qwen_sector_authority import SectorBoundPayload

PORTBOOK = Path(__file__).resolve().parents[2] / 'rtl/model/qwen_hbm_integrated_20261003/ports.json'
NATIVE_KINDS = ('source_publish', 'source_retire', 'immutable_source_transfer', 'native_primitive')
PARAMETERS = {
    'sector': dict(ENABLE=1, IDENTW=207), 'kv': dict(ENABLE=1), 'native': dict(ENABLE=1),
    'sm': dict(ENABLE=1, ACK_ID=1),
    'w2': dict(NC=6, MAX_OUT=16, AW=34, CTAGW=32, GENW=4, PTAGW=35,
               OPT_EXACT=1, OPT_RESET_QUARANTINE=1),
}


class EnclosingPins:
    """One synchronous owner of a pre-existing actual RTL pin driver.

    GET samples actual signals; SET refuses output pins and out-of-width values.
    EDGE advances every instantiated streaming-domain component together.
    Every payload hook surrounds that one edge. A failed hook/RPC retains debt,
    marks the session stopped and cannot silently run the next clock.
    Parameters are supplied by the compiled driver's HELLO, not assumed here.
    """
    def __init__(self, reader, writer, *, portbook=PORTBOOK):
        self.reader, self.writer = reader, writer
        self.book = json.loads(Path(portbook).read_text())
        self.hooks = []
        self.edge_open = self.stopped = False
        self.edges = 0
        self.lock = threading.RLock()
        hello = self._rpc('HELLO')
        expected = 'ot_gpu_qwen_hbm_integrated ENABLE=1 SM=64 W2=128'
        if hello != expected:
            self.stopped = True
            raise TransportError('compiled actual topology/opt-in differs: '+hello)

    def _rpc(self, command):
        with self.lock:
            if self.stopped:
                raise TransportError('enclosing RTL pin session stopped; no retry')
            try:
                self.writer.write(command + '\n')
                self.writer.flush()
                result = self.reader.readline()
                if not result.endswith('\n') or result.startswith('ERR '):
                    raise TransportError('actual pin driver failure: '+result.rstrip())
                return result.rstrip('\n')
            except BaseException:
                self.stopped = True
                raise

    def _pin(self, name):
        try:
            return self.book['pins'][name]
        except KeyError as exc:
            raise TransportError('unconnected/unknown actual pin '+name) from exc

    def get(self, name):
        self._pin(name)
        raw = self._rpc('GET '+name)
        try:
            value = int(raw, 16)
        except ValueError as exc:
            self.stopped = True
            raise TransportError('invalid actual pin reply') from exc
        if not 0 <= value < 1 << self._pin(name)['bits']:
            self.stopped = True
            raise TransportError('actual pin reply exceeds port width')
        return value

    def set(self, name, value):
        p = self._pin(name)
        if name == 'stream_clk' or p['direction'] != 'input':
            raise TransportError('output/owned-clock pin cannot be driven '+name)
        if type(value) is not int or not 0 <= value < 1 << p['bits']:
            raise TransportError('input pin width '+name)
        if self._rpc('SET '+name+' '+format(value, 'x')) != 'OK':
            self.stopped = True
            raise TransportError('actual pin write refused')

    def settle(self):
        if self._rpc('EVAL') != 'OK':
            self.stopped = True
            raise TransportError('actual settle refused')

    def add_edge_hook(self, hook):
        if self.edge_open or self.hooks or self.stopped:
            raise TransportError('hook registration before traffic; one registration only')
        if not all(callable(getattr(hook, n, None)) for n in ('before_edge', 'after_edge')):
            raise TransportError('both actual edge hook methods required')
        if self.edges:
            # Source owner's cold boot may need real clock edges before payload
            # pumping. Register only on actual locally empty controllers. This
            # is not an all-copy fence or a warm-reset permission.
            if (not self.get('kv_idle') or self.get('sector_grant_live') or
                self.get('sector_fault') or self.get('w2_idle') != (1 << 128)-1):
                raise TransportError('cannot enroll payload hook with accepted local debt')
        self.hooks.append(hook)

    def tick(self):
        with self.lock:
            if self.edge_open or self.stopped:
                raise TransportError('recursive/stopped clock; no second clock owner')
            self.edge_open = True
            try:
                for hook in self.hooks:
                    hook.before_edge()
                self.settle()
                if self._rpc('EDGE') != 'OK':
                    raise TransportError('actual edge refused')
                self.edges += 1
                for hook in self.hooks:
                    hook.after_edge()
                self.settle()
            except BaseException:
                self.stopped = True
                raise
            finally:
                self.edge_open = False

    def component(self, block, index=0, *, aliases=None):
        return ComponentPins(self, block, index, aliases=aliases)


class ComponentPins:
    """Exact bit slice of one real instance, sharing the enclosing clock.

    SM index = rank*32+SM. W2 index = physical PC (0..127). No source mapping
    is inferred from this numerical index. aliases can adapt existing RF APIs
    to full-SM host ports without bypassing the RTL service arbitration.
    """
    def __init__(self, root, block, index, *, aliases=None):
        if block not in PARAMETERS or type(index) is not int:
            raise TransportError('actual component identity')
        self.root, self.block, self.index = root, block, index
        self.aliases = dict(aliases or {})
        count = {'sector': 1, 'kv': 1, 'native': 1, 'sm': 64, 'w2': 128}[block]
        if not 0 <= index < count:
            raise TransportError('actual instance out of range')

    def _pin(self, name):
        target = self.block+'_'+self.aliases.get(name, name)
        p = self.root._pin(target)
        return target, p, p.get('leaf_bits', p['bits'])

    def get(self, name):
        target, _, width = self._pin(name)
        return (self.root.get(target) >> (self.index*width)) & ((1 << width)-1)

    def set(self, name, value):
        target, p, width = self._pin(name)
        if p['direction'] != 'input' or type(value) is not int or not 0 <= value < 1 << width:
            raise TransportError('actual component input/width '+name)
        # This is a pin packing RMW, not data storage or a hardware grant.
        with self.root.lock:
            packed = self.root.get(target)
            mask = ((1 << width)-1) << (self.index*width)
            self.root.set(target, (packed & ~mask) | (value << (self.index*width)))

    def set_client(self, client, name, value):
        widths = dict(c_req_v=1, c_req_we=1, c_req_addr=34, c_req_tag=32,
                      c_req_gen=4, c_req_data=256, c_rsp_rdy=1, c_wr_done_rdy=1)
        if self.block != 'w2' or type(client) is not int or not 0 <= client < 6 or name not in widths:
            raise TransportError('actual NC6 client input')
        width = widths[name]
        if type(value) is not int or not 0 <= value < 1 << width:
            raise TransportError('actual NC6 client width')
        with self.root.lock:
            packed = self.get(name)
            mask = ((1 << width)-1) << (client*width)
            self.set(name, (packed & ~mask) | (value << (client*width)))

    def parameter(self, name):
        if name == 'PC_ID' and self.block == 'w2':
            return self.index
        try:
            return PARAMETERS[self.block][name]
        except KeyError as exc:
            raise LookupError(name) from exc

    def settle(self):
        self.root.settle()

    def tick(self):
        self.root.tick()


RF_HOST_ALIASES = dict(rd_valid='host_rd_valid', rd_ready='host_rd_ready',
    rd_a='host_a', rd_b='host_b', rsp_valid='host_rsp_valid', rsp_ready='host_rsp_ready',
    rsp_a='host_rsp_a', rsp_b='host_rsp_b', wr_valid='host_wr_valid', wr_ready='host_wr_ready',
    wr_addr='host_dst', wr_data='host_wdata', wr_owner='host_owner', ack_valid='host_ack_valid',
    ack_ready='host_ack_ready', ack_owner='host_ack_owner', ack_slot='host_ack_slot', ack_identity_fault='identity_fault')


def build(pins, authority, native_handlers, w2_ports, *, enabled=False):
    """Compose actual RF, KV, payload and native owners; refuse missing work.

    Claude supplies four native handlers backed by his actual dispatcher/issuer.
    Sagan authority implements acquire/continue/release on physical grant pins.
    Dewey/Popper hardware connects shared/state/consumer/drain to this top. The
    authority must resolve RFPorts on selected SM host ports with real grants.
    This function neither boots/reset-enrolls hardware nor invents those owners.
    """
    if not enabled or not isinstance(pins, EnclosingPins):
        raise TransportError('actual enclosing canonical simulator is default off')
    if set(native_handlers) != set(NATIVE_KINDS) or any(not callable(v) for v in native_handlers.values()):
        raise TransportError('all four actual native/source handlers required')
    controller = KVControllerPort(pins.component('kv'), authority)
    payload = SectorBoundPayload(pins.component('kv'), pins.component('sector'), w2_ports, enabled=True)
    kv = KVHandlers(authority, controller.handlers)
    rf = RFPageHandlers(authority)
    handlers = dict(native_handlers, source_page_write=rf.source_page_write,
                    source_page_read=rf.source_page_read, **kv.handlers)
    if set(handlers) != set(ALL_KINDS):
        raise TransportError('complete canonical client requires exactly sixteen handlers')
    pins.add_edge_hook(payload)
    return dict(handlers=handlers, pins=pins, payload=payload, controller=controller,
                rf=rf, kv=kv)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable-canonical-qwen', action='store_true', required=True)
    p.add_argument('--socket', type=Path, required=True)
    p.add_argument('--pin-read-fd', type=int, required=True)
    p.add_argument('--pin-write-fd', type=int, required=True)
    p.add_argument('--bindings', required=True, help='module:factory(pins) -> authority,native_handlers; actual source mapper')
    args = p.parse_args()
    reader = os.fdopen(os.dup(args.pin_read_fd), 'r')
    writer = os.fdopen(os.dup(args.pin_write_fd), 'w')
    server = None
    try:
        pins = EnclosingPins(reader, writer)
        module, name = args.bindings.split(':', 1)
        bound = getattr(importlib.import_module(module), name)(pins)
        runtime = build(pins, bound['authority'], bound['native_handlers'], bound['w2_ports'], enabled=True)
        server = UnixDeliveryServer(args.socket, runtime['handlers'], require_kv=True)
        print('Actual canonical1737 sixteen-handler socket: '+str(args.socket), flush=True)
        server.serve_once()
    finally:
        if server is not None:
            server.close()
        reader.close()
        writer.close()


if __name__ == '__main__':
    main()
