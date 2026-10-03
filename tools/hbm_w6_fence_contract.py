#!/usr/bin/env python3
"""W6 prospective contract/golden only. No engine RTL or production adapter.

Fixture widths/cycles are not an F0 ABI or unified-model price. Completion
identities must originate at W4/W2 acceptance, not be inferred from a bare ACK.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '103d3ec89373119898c5662d490676f6ff8ab570'
PIN_PATHS = (
    'rtl/gpu/ot_gpu_rf_service.sv',
    'rtl/gpu/ot_gpu_rf_visibility_fence.sv',
    'rtl/gpu/ot_gpu_full_sm_service.sv',
    'tools/uarch_model.py',
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


@dataclass(frozen=True)
class FixtureLayout:
    owner_tag: int = 16
    generation: int = 8
    reset_epoch: int = 8
    rank: int = 2
    sm: int = 5
    domain: int = 3

    def __post_init__(self):
        require(all(type(v) is int and v > 0 for v in asdict(self).values()), 'positive fixture field widths')

    @property
    def identity_bits(self):
        return sum(asdict(self).values())


@dataclass(frozen=True)
class Identity:
    owner_tag: int
    generation: int
    reset_epoch: int
    rank: int
    sm: int
    domain: int

    def validate(self, layout):
        for k, width in asdict(layout).items():
            v = getattr(self, k)
            require(type(v) is int and 0 <= v < 2**width, 'identity field bounds: ' + k)


class FenceGolden:
    """One-credit finite reference, explicitly enabled; clock edges are logical.

    Reset cancels control debt without clearing SRAM or qualifying its contents.
    Epoch wrap/reuse is forbidden. An additive external drain/rekey protocol is
    required before exhaustion; this reference does not invent that protocol.
    """
    def __init__(self, *, enabled=False, layout=None):
        self.enabled = enabled
        self.layout = layout or FixtureLayout()
        self.edge = 0
        self.epoch = 0
        self.active = None
        self.phase = 'IDLE'
        self.last_edge = -1
        self.highest_generation = -1
        self.mirrors = set()
        self.trace = []
        self.resetting = False
        self.exhausted = False
        self.held = None

    def tick(self, n=1):
        require(type(n) is int and n > 0, 'positive elapsed reference edges')
        self.edge += n

    def _identity(self, identity):
        require(self.enabled and not self.resetting and not self.exhausted, 'disabled/reset/exhausted')
        identity.validate(self.layout)
        require(identity == self.active and identity.reset_epoch == self.epoch, 'stale/foreign identity')

    def _record(self, event, **fields):
        self.trace.append(dict(edge=self.edge, event=event,
                               identity=asdict(self.active) if self.active else None, **fields))

    def issue(self, identity, *, path, address, data, read_origin=None):
        require(self.enabled and not self.resetting and not self.exhausted, 'disabled/reset/exhausted')
        identity.validate(self.layout)
        require(self.phase == 'IDLE' and self.active is None, 'one outstanding owner credit')
        require(self.edge > self.last_edge, 'positive release-to-source edge')
        require(identity.reset_epoch == self.epoch and identity.generation > self.highest_generation, 'stale/reused generation')
        require(path in ('C0', 'KV_READ'), 'supported initial path')
        size = 512 if path == 'C0' else 32
        limit = 512 if path == 'C0' else 2**34
        require(type(address) is int and 0 <= address < limit, 'aligned vector/sector address')
        require(type(data) is bytes and len(data) == size, 'full RF128 vector / KV32B sector bytes')
        if path == 'KV_READ':
            require(read_origin is not None and set(read_origin) == {'identity', 'sector', 'version', 'payload_sha256'}, 'positive source read origin required')
            require(read_origin['identity'] == asdict(identity) and read_origin['sector'] == address and
                    type(read_origin['version']) is int and read_origin['version'] >= 0 and
                    read_origin['payload_sha256'] == hashlib.sha256(data).hexdigest(), 'read origin identity/version/payload')
        else:
            require(read_origin is None, 'C0 has no KV origin')
        self.active = identity
        self.highest_generation = identity.generation
        self.path, self.address, self.data = path, address, data
        self.read_version = None if read_origin is None else read_origin['version']
        self.mirrors = set()
        self.phase = 'COMPLETION'
        self.last_edge = self.edge
        self._record('source_accept', path=path, address=address, payload_sha256=hashlib.sha256(data).hexdigest())

    def mirror_write(self, identity, *, copy, address, data):
        self._identity(identity)
        require(self.path == 'C0' and self.phase == 'COMPLETION', 'mirror before common ACK only')
        require(type(copy) is int and copy in (0, 1) and copy not in self.mirrors, 'duplicate/missing mirror')
        require(type(address) is int and type(data) is bytes and address == self.address and data == self.data, 'mirror address/payload')
        require(self.edge > self.last_edge, 'positive source-to-write edge')
        self.mirrors.add(copy)
        self._record('mirror_write', copy=copy)
        self.write_edge = self.edge

    def complete(self, identity, *, address, data, kind, ready=True, read_version=None):
        self._identity(identity)
        require(self.phase == 'COMPLETION', 'duplicate/out-of-order completion')
        require(type(address) is int and type(data) is bytes and address == self.address and data == self.data, 'completion payload/address identity')
        if self.path == 'C0':
            require(kind == 'W4_COMMON_MIRROR_ACK' and self.mirrors == {0, 1} and read_version is None, 'actual both-copy common ACK required')
            require(self.edge > self.write_edge, 'positive mirrored-write to visible ACK edge')
        else:
            require(kind == 'W2_VERSIONED_READ_CAPTURE' and type(read_version) is int and read_version == self.read_version, 'exact versioned service read completion')
            require(self.edge > self.last_edge, 'positive read accept-to-capture edge')
        require(type(ready) is bool, 'ready is boolean')
        packet = ('completion', identity, address, data, kind, read_version)
        require(self.held is None or self.held == packet, 'completion changed under backpressure')
        if not ready:
            self.held = packet
            self._record('completion_stall', kind=kind)
            return False
        self.held = None
        self.phase = 'VISIBILITY'
        self.last_edge = self.edge
        self._record('completion_accept', kind=kind)
        return True

    def offer(self, identity, *, event, data=None, ready=True, reverse=None):
        self._identity(identity)
        phases = {'visibility': ('VISIBILITY', 'CONSUMER'),
                  'consumer': ('CONSUMER', 'REVERSE'),
                  'reverse': ('REVERSE', 'RETIRE'),
                  'retire': ('RETIRE', 'IDLE')}
        require(event in phases, 'unknown boundary')
        before, after = phases[event]
        require(self.phase == before and self.edge > self.last_edge, 'ordered positive boundary edge')
        require(type(ready) is bool, 'ready is boolean')
        if event in ('visibility', 'consumer'):
            require(type(data) is bytes and data == self.data and reverse is None, 'exact held consumer payload')
        elif event == 'reverse':
            require(data is None and reverse is not None and set(reverse) == {
                'identity', 'sender_domain', 'receiver_domain', 'sender_epoch', 'receiver_epoch',
                'sender_edge', 'receiver_edge'}, 'exact qualified reverse schema')
            require(all(type(reverse[k]) is int for k in ('sender_domain', 'receiver_domain', 'sender_epoch', 'receiver_epoch')) and
                    reverse['identity'] == asdict(identity) and
                    reverse['sender_domain'] == identity.domain and reverse['receiver_domain'] == identity.domain and
                    reverse['sender_epoch'] == self.epoch and reverse['receiver_epoch'] == self.epoch,
                    'reverse domain/reset epoch identity')
            require(type(reverse['sender_edge']) is int and type(reverse['receiver_edge']) is int and
                    self.last_edge < reverse['sender_edge'] < reverse['receiver_edge'] <= self.edge,
                    'positive consumer/return/receive edges')
        else:
            require(data is None and reverse is None, 'retire carries identity only')
        packet = (event, identity, data, json.dumps(reverse, sort_keys=True))
        require(self.held is None or self.held == packet, 'payload/identity changed under backpressure')
        if not ready:
            self.held = packet
            self._record(event + '_stall')
            return False
        self.held = None
        self._record(event + '_accept')
        self.phase, self.last_edge = after, self.edge
        if event == 'retire':
            self.active = None
        return True

    def reset_assert(self):
        self._record('reset_cancel')
        self.active, self.held = None, None
        self.phase, self.mirrors, self.resetting = 'IDLE', set(), True
        self.last_edge = self.edge
        self.highest_generation = -1
        if self.epoch + 1 >= 2**self.layout.reset_epoch:
            self.exhausted = True
        else:
            self.epoch += 1

    def reset_release(self, *, common_reset_drained):
        require(self.resetting and common_reset_drained is True, 'actual common-reset/drain prerequisite')
        # True is a directed fixture input, never a synthesized hardware receipt.
        self.resetting = False
        self._record('reset_release_fixture')


def proposal():
    fields = FixtureLayout()
    i = fields.identity_bits
    boundaries = [
        ('owner_source_to_latch', 'W2', 'identity + addr + mode + optional KV_version(F0) + valid/ready', i + 34 + 1 + 2, 512),
        ('both_mirrors_to_common_ACK', 'W4', 'identity + vector_addr + valid/ready', i + 9 + 2, 0),
        ('completion_to_visibility', 'W6', 'identity + vector_or_sector_addr + optional KV_version(F0) + valid/ready', i + 34 + 2, 512),
        ('visibility_to_consumer_accept', 'W6', 'identity + address + optional KV_version(F0) + valid/ready', i + 34 + 2, 512),
        ('consumer_to_reverse_send', 'W6', 'identity + CDC source/destination epochs/domains + valid/ready', i + 2*(fields.reset_epoch + fields.domain) + 2, 0),
        ('reverse_receive_to_retire', 'W6', 'identity + valid/ready', i + 2, 0),
    ]
    return dict(
        schema='opentallas.hbm.W6.fence-prospective-contract.v1', source_base=BASE,
        default_enabled=False, engine_RTL_written=False, engine_RTL_ready=False,
        status='CONTRACT_GOLDEN_READY_F0_MODEL_AND_W4_W2_BINDINGS_PENDING',
        scope='one complete C0 transaction then one versioned KV-read transaction; golden reference only',
        original_source_pins={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PIN_PATHS},
        golden_fixture_fields=asdict(fields), fixture_identity_bits=i,
        fixture_fields_are_F0=False, production_field_widths=None, KV_version_width=None,
        state_transition_table=[['IDLE', 'source_accept', 'COMPLETION'],
            ['COMPLETION', 'both_actual_mirror_writes_then_common_ACK_OR_versioned_read_capture', 'VISIBILITY'],
            ['VISIBILITY', 'visible_valid_and_ready', 'CONSUMER'],
            ['CONSUMER', 'consumer_valid_and_ready', 'REVERSE'],
            ['REVERSE', 'qualified_matching_return_valid_and_ready', 'RETIRE'],
            ['RETIRE', 'retire_valid_and_ready', 'IDLE'],
            ['any', 'common_reset_assert', 'reset_cancel_debt_block_until_source_drain']],
        read_version_rule='KV source completion echoes exact latched published version in addition to request generation; consumer packet retains that version; F0 freezes width',
        owner_identity_origin='must be latched at actual service request handshake and echoed by actual completion source; no inferred tag from bare host_ack_valid',
        geometry=dict(RF_vectors=512, SIMD_lanes=128, lane_bits=32, operand_copies=2,
                      RF_pages=4, banks_per_page_per_copy=16, physical_RF_macros=128,
                      RF_vector_bytes=512, mirrored_write_bytes=1024, KV_sector_bytes=32),
        queue=dict(owner_slots=1, outstanding_completion=1, visibility_lease=1,
                   consumer_debt=1, reverse_debt=1, reuse='strictly increasing generation for this single slot in each reset epoch; no generation/epoch wrap without separately qualified drain/rekey',
                   backpressure='stable tagged payload; keep owner/table credit until matching reverse then retirement'),
        boundary_model_requests=[dict(name=n, owner=o, control_formula=f, fixture_control_bits_excluding_unfrozen_KV_version=b,
            payload_bits_per_cycle_candidate=d*8, total_bits_per_cycle=None,
            positive_cycles_required=True, production_cycles=None, control_bits_per_cycle=None,
            candidate_peak_payload_bytes_per_cycle=d, routing_tracks=None, channel_capacity=None,
            CDC='common domain in fixture only; F0 bind actual domains/epochs and positive crossing costs')
            for n, o, f, b, d in boundaries],
        storage_model_request=dict(identity_latch_bits='sum(F0 identity widths)',
            table_entries=1, per_entry='generation high-water + identity + address + KV_version + phase + copy_done[2] + validity/lease/reverse flags + CDC debt',
            payload='prefer retained source lease; if source cannot hold, charge full512B RF or32B KV landing explicitly',
            fanout='identity comparators at completion/visibility/consumer/reverse/retire plus32 selected bank controls; price buffers/muxes',
            replica_count='bind full Qwen/DS SM inventory in unified model, no undersized physical scope',
            area_um2=None, slot_um=None, routing_tracks=None, latency_token_cycles=None, MACs_per_cycle=0,
            port_budget='one owner request/edge; C0 logical512B write,1024B mirrored writes,2x512B operand read; KV32B sector response; all metadata widths priced on every transfer',
            payload_mux='if shared C0/KV landing, include full-width select and256bit-to4096bit slice enables; never price as free',
            area_policy='no numerical area estimate without F0 widths and unified-model cell/replica/context mapping'),
        prerequisite_owners={'F0': 'Russell field freeze', 'unified_full_model': 'Popper',
                             'W4': 'Euclid common mirrored ACK', 'W2': 'Nash exact service completion'},
        prerequisite_pins={k: None for k in ('F0_fields', 'priced_unified_model', 'W4_common_ACK', 'W2_service_completion')},
        RTL_gate='exact F0 pins + positive per-boundary cycles/ports/bits/tracks/replicas/fanout/area/slot/token model; then default-off additive source and actual source handshake bench',
        actual_bench_required=['source request latch; both write-copy ports; common tagged ACK',
            'consumer actual valid/ready; retained payload before/after stalls',
            'real reverse CDC sender/receiver reset epochs and source domains',
            'stale/duplicate/foreign generation and reset during every held phase',
            'C0 full128-lane RF readback and then versioned KV sector read with positive old origin'],
        golden_times_are_physical_ticks=False, physical_qualified=False,
        whole_program_qualified=False, original_432_production_events='UNKNOWN',
        SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
        macro_write_CLKtoQ_SS='UNKNOWN; behavioral mirror edge insufficient',
        no_R3_owner_ledger_modification=True,
    )


def finite_bench():
    g = FenceGolden(enabled=True)
    for path, address, data in [('C0', 511, bytes(range(256))*2), ('KV_READ', 2**34-1, bytes(range(32)))]:
        ident = Identity(7, 1 if path == 'C0' else 2, 0, 0, 0, 1)
        origin = None if path == 'C0' else dict(identity=asdict(ident), sector=address, version=3,
                                                payload_sha256=hashlib.sha256(data).hexdigest())
        g.issue(ident, path=path, address=address, data=data, read_origin=origin)
        g.tick()
        if path == 'C0':
            for copy in (0, 1):
                g.mirror_write(ident, copy=copy, address=address, data=data)
            g.tick()
        g.complete(ident, address=address, data=data, kind='W4_COMMON_MIRROR_ACK' if path=='C0' else 'W2_VERSIONED_READ_CAPTURE', read_version=None if path=='C0' else 3)
        for event in ('visibility', 'consumer'):
            g.tick()
            g.offer(ident, event=event, data=data, ready=False)
            g.tick(2)
            g.offer(ident, event=event, data=data)
        sender = g.edge+1
        g.tick(2)
        reverse = dict(identity=asdict(ident), sender_domain=1, receiver_domain=1,
                       sender_epoch=0, receiver_epoch=0, sender_edge=sender, receiver_edge=g.edge)
        g.offer(ident, event='reverse', reverse=reverse)
        g.tick()
        g.offer(ident, event='retire')
        g.tick()
    return dict(status='PASS_FINITE_GOLDEN_C0_THEN_KV_READ_ONLY', trace=g.trace,
                engine_RTL_executed=False, hardware_qualification=False, expected_transactions=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    for name, data in [('contract.json', proposal()), ('finite_golden.json', finite_bench())]:
        with (args.out/name).open('x') as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write('\n')
