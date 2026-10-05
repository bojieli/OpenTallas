#!/usr/bin/env python3
"""Producer payload -> actual allocation -> owned wire -> credit -> drain join.

Opt-in analytical/functional adapter. No hardware admission or synthetic final
qualification. The r14 owned return changes identity.sector to base+beat;
the immutable allocation identity remains separately retained. Current r14
has only one request data256, so heterogeneous writes require LEN=1.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from qwen_rom_persistent_kv_g0 import Owner, ROOT
from qwen_rom_kv_identity_binding import unpack, validate, reverse_credit
from qwen_rom_kv_production_join import Receipts, RefillJoin, producer_write_plan, contract


class CausalJoin:
    def __init__(self, residence_sectors=16):
        self.residence = RefillJoin(residence_sectors)
        self.ledger = Receipts()
        self.pending, self.allocations, self.reads = {}, {}, {}
        self.completed = 0

    def submit(self, producer):
        owner = producer.owner
        if any(o.rank == owner.rank for o in self.pending):
            raise ValueError('one pending producer row per rank; drain before reuse')
        plan = producer_write_plan(producer, self.residence)
        requests = {(r['endpoint'], r['die'], r['stack'], r['sector']): r
                    for r in plan['requests']}
        self.pending[owner] = dict(requests=requests, leased=set(),
                                  program_sha256=plan['program_sha256'])
        return plan

    def expect_reads(self, owner, pc, keys, provider):
        """Actual descriptor demand and actual32B state callback, never zeros."""
        keys = set(keys)
        if not 0 <= pc < 4096 or len(self.reads)+len(keys) > 2048:
            raise ValueError('finite declared read demand')
        data = {}
        for key in keys:
            if (len(key) != 4 or key[:2] != (owner.rank>>1, owner.rank&1)
                    or not 0 <= key[2] < 4 or not 0 <= key[3] < 703125000):
                raise ValueError('read home')
            bound = (owner, pc, key)
            if bound in self.reads:
                raise ValueError('duplicate unretired read demand')
            value = provider(owner, key)
            if not isinstance(value, bytes) or len(value) != 32:
                raise ValueError('actual read state absent')
            data[bound] = value
        self.reads.update(data)

    def apply(self, event):
        """Input identity is literal current wire identity, not normalized data.

        ALLOC is immutable base. RETURN/ACQUIRE/DRAIN/CREDIT/GRANT_CONSUMED
        retain sector=base+beat in identity. WRITE_COMMAND/BACKING LEN1 retain
        that same sector. RETIRE explicitly refers to immutable allocation base.
        CREDIT additionally carries reverse_wire_hex, exactly404 source bits.
        """
        e = dict(event)
        owner = Owner(**e['owner'])
        word = int(e['identity'], 16)
        wire = validate(word, e['endpoint'], owner, e['producer_pc'])
        slot = (e['endpoint'], wire['die'], e['stack'], e['physical_tag'])
        if e['event'] == 'allocate':
            keys = [(e['endpoint'], wire['die'], e['stack'], wire['sector']+b)
                    for b in range(e['sectors'])]
            if e['write']:
                if e['sectors'] != 1:
                    raise ValueError('current r14 write data256 requires LEN1')
                if owner not in self.pending:
                    raise ValueError('allocation has no accepted producer row')
                pending = self.pending[owner]
                for key in keys:
                    request = pending['requests'].get(key)
                    if (request is None or key in pending['leased'] or
                            request['producer_pc'] != e['producer_pc'] or
                            bytes.fromhex(request['payload_hex']) != bytes.fromhex(e['payload_hex'])):
                        raise ValueError('allocation does not match producer PC/home/payload')
            elif any((owner, e['producer_pc'], k) not in self.reads for k in keys):
                raise ValueError('allocation has no actual descriptor/state read demand')
            self.ledger.apply(e)
            self.allocations[slot] = dict(identity=word, owner=owner, keys=keys,
                                          pc=e['producer_pc'], write=e['write'])
            if e['write']:
                self.pending[owner]['leased'].update(keys)
            return
        if slot not in self.allocations:
            raise ValueError('wire receipt lacks retained allocation')
        allocation = self.allocations[slot]
        base = unpack(allocation['identity'])
        beat = e.get('beat')
        if e['event'] == 'retire':
            if word != allocation['identity']:
                raise ValueError('retirement does not name immutable allocation')
        else:
            if not isinstance(beat, int) or not 0 <= beat < len(allocation['keys']):
                raise ValueError('wire beat bounds')
            expected = dict(base, sector=base['sector']+beat)
            if wire != expected or e['sector'] != expected['sector']:
                raise ValueError('literal owned identity differs from allocated base+beat')
            if e['event'] == 'credit':
                actual = int(e['reverse_wire_hex'], 16)
                expected_wire = reverse_credit(word, e['physical_tag'], beat, int(allocation['write']))
                if actual != expected_wire:
                    raise ValueError('reverse ACK wire404 identity/tag/beat/write mismatch')
            if e['event'] == 'return' and not allocation['write']:
                bound = (owner, e['producer_pc'], allocation['keys'][beat])
                if bytes.fromhex(e['payload_hex']) != self.reads[bound]:
                    raise ValueError('read returned payload differs from actual declared state')
            # Normalize only after proving every literal wire field. The ledger
            # carries immutable request identity; original wire remains in input.
            e['identity'] = hex(allocation['identity'])
        self.ledger.apply(e)
        if e['event'] == 'retire':
            if allocation['write']:
                pending = self.pending[owner]
                for key in allocation['keys']:
                    del pending['requests'][key]
                    pending['leased'].remove(key)
                if not pending['requests']:
                    # Closed K data may release only after all planned writes
                    # have backing/credit/grant/tag retirement receipts.
                    if owner in self.residence.tails and len(self.residence.tails[owner][1]) == 16:
                        self.residence.retire_k(owner, self.residence.closed_k(owner))
                    del self.pending[owner]
                    self.completed += 1
            else:
                for key in allocation['keys']:
                    del self.reads[owner, allocation['pc'], key]
            del self.allocations[slot]

    def debts(self):
        return dict(pending_producer_rows=len(self.pending), live_allocations=len(self.allocations),
                    pending_read_sectors=len(self.reads),
                    planned_write_sectors=sum(len(p['requests']) for p in self.pending.values()),
                    completed_rows=self.completed, physical_build_ready=False)


def receipt(parent_ref):
    """Exact dependency receipt; unavailable inputs block rather than zero-fill."""
    parent = subprocess.check_output(['git','rev-parse',parent_ref],cwd=ROOT,text=True).strip()
    source = contract()
    pins = {}
    for path, expected in source['source_sha256'].items():
        data = subprocess.check_output(['git','show',parent+':'+path],cwd=ROOT)
        digest = hashlib.sha256(data).hexdigest()
        pins[path] = dict(parent_sha256=digest, received_sha256=expected,
                          same_as_received=digest == expected)
    reset_paths = ['tools/qwen_rom_reset_context_g0.py','tools/uarch_model_qwen_reset.py',
                   'results/uarch/qwen_rom_reset_producer_g0_20261002/model-r5.json']
    reset = {p:hashlib.sha256(subprocess.check_output(['git','show',parent+':'+p],cwd=ROOT)).hexdigest()
             for p in reset_paths}
    control = dict(
        allocation={'path':'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
                    'anchor':'if(av&&ar)', 'requires':'Export immutable identity192/base/LEN and actual allocated_tag12 at handshake.'},
        returned_identity={'path':'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
                    'anchor':"output_reg.id.sector<=restored.sector+34'(beat_saved)",
                    'requires':'Retain base allocation; every owned/reverse receipt identity must carry base+beat, all other identity fields unchanged.'},
        tag_retirement={'path':'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
                    'anchor':'live[tag_saved]<=0',
                    'requires':'Final PC output acceptance is not consumer drain/credit/grant retirement.'},
        reverse={'path':'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
                    'anchor':'if(!credit_we)begin credit_match=1',
                    'requires':'Validate literal404bit credit against actual tag/identity/beat/write and consumed return before grant.'},
        write_payload={'path':'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
                    'anchor':'data:accepted.data',
                    'requires':'Current data256 is one sector; LEN1 heterogeneous writes. No fabricated per-beat write port.'},
        producer_visibility={'path':'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
                    'anchor':".kv_write_drained(1'b1)",
                    'requires':'Actual visibility/drain provider must replace fixture constants through a model-admitted successor.'})
    for item in control.values():
        lines = subprocess.check_output(['git','show',parent+':'+item['path']],cwd=ROOT,text=True).splitlines()
        hits = [n for n,line in enumerate(lines,1) if item['anchor'] in line]
        if not hits:
            raise ValueError('parent source anchor changed: '+item['anchor'])
        item['lines'] = hits
    r8 = json.loads((ROOT/'results/uarch/qwen_rom_persistent_kv_g0_20261002/contract_r8.json').read_text())
    resources = r8['candidate_resources']
    tail = source['physical_context']
    return dict(schema='opentallas.qwen-rom-kv-causal-dependency-receipt.v1',
        status='BLOCKED_ACTUAL_PRODUCER_PROVIDER_POLICY_AND_PHYSICAL_SLOT',
        implementation_predecessor='22ec26bd2db8446546f4848cc8c2dd79e8cf5209',
        implementation_source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
          for p in ['tools/qwen_rom_kv_causal_join.py','tests/test_qwen_rom_kv_causal_join.py',
                    'tools/qwen_rom_kv_production_join.py','tools/qwen_rom_kv_identity_binding.py',
                    'tools/qwen_rom_persistent_kv_g0.py']},
        inspected_parent=parent, parent_source_pins=pins, reset_extension_pins=reset,
        anchors=control,
        causal_API='CausalJoin.submit(actual_ProducerJoin); expect_reads(owner,issued_pc,homes,actual32Bprovider); apply(literal_wire_event); debts()',
        input_receipts=source['receipt_schema'],
        wire_rules=dict(allocation='immutable identity192 sector=burst base',
          beat_receipts='identity192 sector=base+beat, beat5 and tag12 must match retained allocation',
          reverse_ack='credit event additionally carries reverse_wire_hex; exact404bit packing including reserved zeros',
          write='LEN1; payload must equal canonical actual producer row at pinned home and issued PC',
          read='Declared descriptor sector demand + actual state callback required; returned bytes must match',
          retire='Immutable base identity; backing/returns, reader drain, accepted credit, consumed grant all required'),
        peers={
          'Euclid':dict(required=['Actual selected stage image bytes/SHA and TP4 parameters',
                'Accepted SU issue PC/ticket and domain/cycle, every KV lane address24/value32',
                'Accepted K/V descriptor coordinates and consumer acquire/drain',
                'Actual initial persistent prefix, open-tail and window state provider'],
                blocker='Current wrapper hard-wires kv_ok and drained; capture contains no KV payload/program images. No actual persistent producer receipt supplied.'),
          'Kepler':dict(required=['Handshake allocation tag/base/LEN receipt',
                'WR command/backing receipts with exact producer-bound payload',
                'Owned returns with literal rewritten identity; actual404bit reverse credit and consumed grant',
                'Per-beat reader drain and tag quarantine until retirement'],
                observation='Use existing hierarchical av/ar/allocated_tag and return/credit/grant signals or a retained source journal; no new engine RTL before full service model admission.',
                blocker='Actual r14 early-free/unvalidated-read-credit path unchanged; allocation receipt not exported. Current write data port only supports heterogeneous LEN1. Unsafe source traces must fail, not be repaired by fabricated ACKs.'),
          'Ampere':dict(required=['Per-domain physical reset release/readiness receipt with held-tag/credit drain',
                'Actual controller/tail/assembly macro instances, pin/OBS/halo/PG/clock reservations',
                'Chosen service slot outline and routed boundary capacities',
                'SS60ps/FF25ps contextual timing and complete control/mux/CDC area'],
                blocker='Reset composition retains prior cold r8 contract; current_slot_fit and channel_capacity are null. Tail addition and causal obligations not yet joined.'),
          'Russell':dict(required=['Bind supplied producer/state/descriptor receipts to one explicitly selected persistent policy',
                'Timed finite calendar across shared ports/channels, assembly, return, ACK and drain',
                'Replace existing KV/HBM read charge once, explicitly price writes/CDC/tail/mux/control and single-user latency'],
                blocker='Cannot select or qualify actual production policy without source-owned payload/state/descriptor and safe provider receipts. Cold reference is not production.')},
        physical_service_slot=dict(service_SRAM_macros_per_rank=4*resources['actual_service_macro_count_per_stack'],
          tail_SRAM_macros_per_rank=tail['banks_per_rank'],
          service_and_tail_SRAM_macros_per_rank=4*resources['actual_service_macro_count_per_stack']+tail['banks_per_rank'],
          new_tail_clock_macro_pins_per_rank=tail['banks_per_rank'],
          reset_composition='Existing384 service macro clocks/rank remain charged once. '
                            'Add128 tail macro clocks/rank and actual owner/CDC/control sinks; '
                            'the streaming startup price is once, never a per-layer refill.',
          service_and_tail_macro_area_mm2_per_rank=resources['actual_service_macro_area_mm2_per_rank']+tail['macro_area_mm2_per_rank'],
          assembly_logic_area_lower_bound_mm2_per_rank=resources['assembly_area_lower_bound_mm2'],
          inherited_slot_mm2_per_stack=resources['inherited_service_slot_mm2_per_stack'],
          inherited_slot_is_current_fit=False, complete_area_mm2=None, slot_fit=None,
          channel_capacity=None, single_user_latency=None,
          tail_geometry=tail,
          limits='Tail row mapping sizes one active user/epoch per rank. Multiple users, old-epoch retention, protection and complete slot cost are not admitted.',
          boundary_bits_per_edge=resources['boundary_tracks']),
        production_policy_selected=False, physical_build_ready=False, new_numerical_positions=0,
        cold_calendar=dict(parent_verified=True,cycles=387403068,selected_policy=False),
        delivery='COMMITTED_FOR_PARENT_RELAY_NO_PEER_MESSAGE_TRANSPORT_EXPOSED')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--parent-ref',required=True)
    p.add_argument('--result',required=True)
    args=p.parse_args()
    result=receipt(args.parent_ref)
    with Path(args.result).open('x') as f:
        json.dump(result,f,indent=2); f.write('\n')


if __name__ == '__main__':
    main()
