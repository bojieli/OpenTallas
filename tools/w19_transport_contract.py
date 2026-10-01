#!/usr/bin/env python3
"""Finite GPU HBM transport analytical candidate and protocol oracle, not RTL.

W16 owns GPU compute lowering and unified critical-chain composition. This input
sizes transport only; its new commit/fence ports are not present in the source.
"""
import argparse
import ast
import hashlib
import json
import math
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUAL = 'results/uarch/w16_w19_gpu_service_gate_20261001/qualification.json'
ALLOC = 'results/rtl/w19_checkpoint_production_20261001/resident-service-candidate-r1.json'
SCOPE = 'results/quality/w16_w19_gpu_mapping_scope_20261001/gpu_scope.json'
CONTROLLER = 'rtl/hdc/kv/ot_hdc_hbm_model.sv'
CLASSES = ('weight', 'coefficient_table', 'state_read', 'state_write')


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def sizing(bandwidth=1e12, loaded_ns=500, slots=4096, region_count=133):
    if bandwidth <= 0 or loaded_ns <= 0 or slots <= 0 or region_count <= 0:
        raise ValueError('positive finite geometry required')
    region_bits = max(1, (region_count - 1).bit_length())
    # Local endpoint binds rank/stack. Keep full 27-bit physical sector and
    # full 32-bit virtual destination offset; no aperture reduction/modulo.
    fields = dict(sector=27, sectors_minus_one=4, opcode=2, service_class=2,
                  sm_owner=5, destination_byte=32, region=region_bits,
                  epoch=16, sequence=32, byte_mask=32)
    descriptor_bits = sum(fields.values())
    context_bits = descriptor_bits + 4 + 1 + 3  # received-sector bitmap, live
    write_context_bits = descriptor_bits + 1 + 11
    per_controller = dict(class_descriptor_bits=4 * 16 * descriptor_bits,
        read_context_bits=slots * context_bits,
        read_landing_bits=slots * 128 * 8,
        write_context_bits=16 * write_context_bits,
        write_payload_bits=16 * 256,
        queued_write_payload_bits=16 * 256,
        partial_sector_RMW_bits=256, RMW_lock_bits=27+4+1,
        accepted_sequence_bits=32, fence_sequence_bits=32,
        fence_epoch_and_valid_bits=17, epoch_bits=16,
        queue_pointer_bits=4 * (2 * 4 + 5),
        arbitration_bits=2)
    bits = sum(per_controller.values())
    needed = math.ceil(bandwidth * loaded_ns * 1e-9 / 128)
    return dict(classes=list(CLASSES), class_queue_depth=16, descriptor_fields=fields,
        descriptor_bits=descriptor_bits, read_context_bits=context_bits,
        read_line_slots=slots, sectors_per_line=4, write_slots=16,
        RMW_slots=1, region_bits=region_bits,
        storage_bits_per_controller=per_controller, total_storage_bits_per_controller=bits,
        total_storage_bytes_per_rank=math.ceil(bits / 8) * 4,
        total_storage_bytes_all96=math.ceil(bits / 8) * 4 * 96,
        loaded_latency_assumption_ns=loaded_ns,
        stack_bandwidth_assumption_bytes_s=bandwidth,
        bandwidth_delay_required_128B_slots=needed,
        selected_slots_cover_bandwidth_delay=slots >= needed,
        credit_bandwidth_ceiling_bytes_s=slots * 128 / (loaded_ns * 1e-9),
        scope='Necessary bandwidth-delay storage only; no scheduler/service or token latency guarantee')


def build():
    qual = json.loads((ROOT / QUAL).read_text())
    candidate = json.loads((ROOT / ALLOC).read_text())
    if qual['verdict'] != 'REFUSED_PENDING_GPU_LOWERING_AND_RESOURCES':
        raise ValueError('W16 qualification contract changed')
    if candidate['required_sector_bits_candidate'] != 27 or candidate['required_bulk_line_bits_candidate'] != 25:
        raise ValueError('accepted allocation aperture changed')
    source = (ROOT / CONTROLLER).read_text().split(');', 1)[0]
    sm = (ROOT / 'rtl/gpu/ot_gpu_bulk_copy.sv').read_text().split(');', 1)[0]
    if 'req_wstrb' in source or 'wr_done' in source or 'commit_v' in source or 'rsp_rdy' in sm:
        raise ValueError('actual source ports changed; requalify binding')
    regions = max(len(rank['regions']) for rank in candidate['ranks'])
    # Read the exact unified-model constant without importing unrelated physical
    # result loaders or running/repricing any of the four model generators.
    tree = ast.parse((ROOT / 'tools/uarch_model.py').read_text())
    latency_nodes = [n.value for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'HBM_LOADED_LAT_NS' for t in n.targets)]
    if len(latency_nodes) != 1:
        raise ValueError('unified loaded latency binding changed')
    loaded_ns = ast.literal_eval(latency_nodes[0])
    geometry = sizing(loaded_ns=loaded_ns, region_count=regions)
    return dict(schema='opentallas.w19.finite_transport_model_contract.v1',
        W16_input_ack=dict(acknowledged=True, qualification=QUAL, sha256=sha(QUAL),
            GPU_authority=SCOPE, authority_sha256=sha(SCOPE),
            dedicated_HCP=False, HC_candidate_owner='Turing',
            transport_contract_owner='W19', allocation_rebuilt=False),
        pins={p: sha(p) for p in (QUAL, ALLOC, SCOPE, CONTROLLER,
            'rtl/gpu/ot_gpu_bulk_copy.sv', 'tools/uarch_model.py',
            'tools/w19_transport_contract.py')},
        applicable_designs=dict(v41_HBM='analytical candidate', qwen_HBM='unqualified; no cost credit',
            v41_ROM='unchanged', qwen_ROM='unchanged'),
        replica_count=dict(ranks=96, controllers_per_rank=4, SMs_per_rank=32,
            SMs_per_controller=8, total_transport_endpoints=384),
        arithmetic=dict(MACs_per_cycle=0, conversions=False,
            Engram='Eight production block scales retained; current row-scale gather incompatible'),
        geometry=geometry,
        address=dict(sector_bits=27, line_bits=25, sector_bytes=32,
            stripe_bytes=128, stack='(virtual_byte // 128) % 4',
            physical_byte='region.base[stack] + (virtual_byte // 512)*128 + virtual_byte%128',
            endpoint_local_rank_and_stack=True, destination_byte_bits=32,
            modulo_or_reload=False),
        tags=dict(wire_bits=16, read_slot_bits=12,
            policy='Wire bit15 distinguishes writes. Read bits11:0 index4096 slots and bits14:12 generation; write bits3:0 index16 slots and bits14:4 generation. No live slot reuse. Generation cannot wrap before a drained epoch transition.',
            epoch_bits=16, reset='Quiesce ingress; drain descriptors, all read returns, writes and RMW locks; fence then increment epoch. Hard reset with outstanding work invalidates residence and forbids continuation.',
            duplicate='Reject duplicate/unissued sector or commit, stale epoch and out-of-range tag; do not count them as completed work'),
        protocol=dict(queue='Four 16-entry descriptor queues/controller; oldest eligible round-robin. Ownership and same-sector hazards checked before grant.',
            credit='Reserve a complete 128B landing slot before read grant; four 32B responses may arrive on different PC ports. Hold the assembled line until destination takes it.',
            SM='Existing bulk-copy response has no ready: SM destination ring credit must also be reserved before grant; no borrowed nonSM buffer or lost response.',
            writes='Whole 32B sectors only. Partial byte updates use one serialized RMW lock/controller; read old sector, merge byte mask without conversion, retain lock through externally visible commit.',
            commit='Controller emits tagged commit only after full-sector data is visible to subsequent reads; request ready and internal st_wr are not completion. Hold commit valid until ready.',
            fence='Snapshot accepted sequence at all four controllers; complete only after every earlier queued or issued operation drains, destination delivery completes, and paired code/scale writes commit. Publish logical row last.',
            compute_ready='All required staged bytes and producer fences complete before SM/GPU instruction issue; no host golden data injection'),
        source_ports=dict(controller_request_bits_per_cycle=1+1+1+27+5+16+256,
            controller_response_bits_per_cycle=32*(1+1+16+4+256),
            controller_room_bits_per_cycle=32,
            proposed_commit_bits_per_cycle=32*(1+1+16),
            proposed_fence_command_bits=1+1+16+32,
            proposed_fence_reply_bits=1+1+16,
            read_bytes_per_cycle_peak=32*32, request_write_bytes_per_cycle_peak=32,
            SM_assembled_bytes_per_cycle=128,
            existing_commit=False, existing_write_mask=False,
            existing_request_signals=['req_v','req_rdy','req_we','req_addr','req_len','req_tag','req_wdata'],
            existing_response_signals=['rsp_v','rsp_rdy','rsp_tag','rsp_beat','rsp_data'],
            proposed_signals=['commit_v[NPC]','commit_rdy[NPC]','commit_tag[NPC*16]', 'fence_v','fence_rdy','fence_tag[16]','fence_cut[32]','fence_done_v','fence_done_rdy','fence_done_tag[16]'],
            existing_SM_response_ready=False,
            note='Commit lanes mirror worst-case 32 simultaneous PC completions; these are new source-unimplemented boundary wires, not free debug-counter acknowledgments'),
        physical_model_inputs=dict(storage_implementation=None, incremental_area_mm2=None,
            landing_write_ports_per_controller=32, landing_read_ports_per_controller=1,
            context_update_ports_per_controller=32,
            multi_PC_same_line_update='Merge beat-valid updates before context write; bank collision schedule and cost pending',
            request_class_mux_inputs=4, request_SM_owner_mux_inputs=8,
            return_SM_demux_outputs=8, broadcast_rank_fence_fanout=4,
            route_tracks=None, channel_capacity_tracks=None, slot_fit=None,
            note='No existing L2/RF/shared-memory credit claimed. Turing must bind banked SRAM/update collision handling, routing layers and critical chain before unified-model readiness.'),
        critical_chain=dict(grant_pipeline_cycles=None, assembly_cycles=None,
            destination_cycles=None, write_commit_cycles=None, fence_cycles=None,
            shared_service_completed_cycles=None, full_token_composed_cycles=None),
        enabled_default=False, unified_model_composed=False, ready_to_build=False,
        actual_RTL_gate=False, full_resident_qualified=False, hardware_adopted=False,
        adopted_token_rate=None)


class Protocol:
    """Untimed finite protocol oracle; tests control invariants, not RTL or speed."""
    def __init__(self, depth=16, reads=4096, writes=16):
        if min(depth, reads, writes) <= 0 or reads > 4096 or writes > 16:
            raise ValueError('finite positive resources required')
        self.depth, self.reads, self.writes = depth, reads, writes
        self.queues = [[deque() for _ in CLASSES] for _ in range(4)]
        self.pending = {}; self.sequence = [0]*4; self.epoch = 0
        self.memory = {}; self.locks = set()
        self.read_generation = [[0]*reads for _ in range(4)]
        self.write_generation = [[0]*writes for _ in range(4)]

    def enqueue(self, stack, kind, sector, payload=None, mask=(1<<32)-1):
        if stack not in range(4) or kind not in range(4) or not 0 <= sector < (1<<27):
            raise ValueError('endpoint/class/address outside contract')
        if payload is not None and (len(payload) != 32 or kind != 3):
            raise ValueError('whole-sector write payload required')
        if kind == 3 and (payload is None or not 0 < mask < (1<<32)):
            raise ValueError('write payload/mask required')
        if kind != 3 and sector+3 >= (1<<27):
            raise ValueError('line crosses aperture')
        q = self.queues[stack][kind]
        if len(q) == self.depth:
            return False
        if self.sequence[stack] == (1<<32)-1:
            raise ValueError('sequence wrap requires drained epoch transition')
        self.sequence[stack] += 1
        q.append(dict(kind=kind, sector=sector, payload=payload, mask=mask,
                      sequence=self.sequence[stack], epoch=self.epoch))
        return True

    def issue(self, stack, kind):
        q = self.queues[stack][kind]
        if not q:
            return None
        item = q[0]; write = kind == 3
        occupied = {r['slot'] for (st, _), r in self.pending.items() if st == stack and (r['kind']==3) == write}
        generations = self.write_generation[stack] if write else self.read_generation[stack]
        slot = next((i for i,g in enumerate(generations) if i not in occupied and g < (2048 if write else 8)), None)
        tag = None if slot is None else ((0x8000 | (generations[slot]<<4) | slot) if write else ((generations[slot]<<12) | slot))
        addresses = range(item['sector'], item['sector']+(1 if write else 4))
        # Do not pass an earlier conflicting write, including queued writes.
        prior = list(self.pending.values()) + [r for qq in self.queues[stack] for r in qq]
        hazard = any(r.get('stack', stack) == stack and r is not item and
            r['sequence'] < item['sequence'] and (r['kind'] == 3 or write) and
            set(addresses).intersection(range(r['sector'], r['sector']+(1 if r['kind']==3 else 4))) for r in prior)
        rmw = write and item['mask'] != (1<<32)-1
        if tag is None or hazard or (rmw and any(s == stack for s, _ in self.locks)):
            return None
        q.popleft(); item.update(stack=stack, seen=set(), held=False, slot=slot)
        if rmw:
            self.locks.add((stack, item['sector']))
        self.pending[stack, tag] = item
        return tag

    def response(self, stack, tag, beat, data, epoch):
        item = self.pending.get((stack, tag))
        if item is None or item['kind'] == 3 or epoch != item['epoch'] or beat not in range(4) or beat in item['seen'] or len(data)!=32:
            raise ValueError('unissued/stale/duplicate sector response')
        item['seen'].add(beat)
        item.setdefault('data', {})[beat] = bytes(data)
        item['held'] = len(item['seen']) == 4

    def deliver(self, stack, tag, ready=True):
        item = self.pending.get((stack, tag))
        if item is None or item['kind'] == 3 or not item['held']:
            raise ValueError('incomplete/unissued landing')
        if not ready:
            return None
        del self.pending[stack, tag]
        self.read_generation[stack][item['slot']] += 1
        return b''.join(item['data'][i] for i in range(4))

    def commit(self, stack, tag, epoch, visible=False):
        item = self.pending.get((stack, tag))
        if item is None or item['kind'] != 3 or epoch != item['epoch'] or not visible:
            raise ValueError('unissued/stale/early write commit')
        old = self.memory.get((stack, item['sector']), bytes(32))
        self.memory[stack, item['sector']] = bytes(item['payload'][i] if item['mask'] >> i & 1 else old[i] for i in range(32))
        self.locks.discard((stack,item['sector']))
        del self.pending[stack, tag]
        self.write_generation[stack][item['slot']] += 1

    def fence(self):
        return (self.epoch, tuple(self.sequence))

    def fence_ready(self, cut):
        if cut[0] != self.epoch:
            raise ValueError('stale fence epoch')
        cut = cut[1]
        return not any(r['sequence'] <= cut[st] for (st,_),r in self.pending.items()) and not any(r['sequence'] <= cut[st] for st,qs in enumerate(self.queues) for q in qs for r in q)

    def reset_epoch(self):
        if self.pending or self.locks or any(q for qs in self.queues for q in qs):
            raise ValueError('cannot reuse tags/residence before drain')
        self.epoch = (self.epoch+1) % (1<<16)
        self.sequence = [0]*4
        self.read_generation = [[0]*self.reads for _ in range(4)]
        self.write_generation = [[0]*self.writes for _ in range(4)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--out',type=Path); group.add_argument('--check',type=Path)
    args=parser.parse_args(); data=build()
    if args.check:
        if json.loads(args.check.read_text()) != data:
            raise ValueError('contract or source pins changed')
    else:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x') as f:
            json.dump(data,f,indent=2,sort_keys=True); f.write('\n')
    print('PASS analytical transport contract; unified composition/RTL/build/adoption remain false')

if __name__=='__main__':
    main()
