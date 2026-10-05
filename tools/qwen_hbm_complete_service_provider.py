#!/usr/bin/env python3
"""Bounded Qwen sector-ACK/publication adapter model, not engine RTL.

All timestamps are supplied provider callbacks. This model never fabricates
DRAM completions, reconstructs checkpoint KV bytes, or qualifies a token clock.
Sector transaction credits and persistent reader-generation leases are distinct.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
from common_wrack_completion_calendar import FAST, SLOW, crossing, command_budget
from qwen_hbm_complete_program import compile_program

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'program': ('defc45332', 'tools/qwen_hbm_complete_program.py'),
    'packed_KV': ('8d68f3854', 'tools/qwen_hbm_complete_isa.py'),
    'corrected_stack_floor': ('df92353aa', 'tools/w13_qwen_kv_rmw_model.py'),
    'finite_join': ('2185eadf5', 'tools/w16_hbm_finite_service_join.py'),
    'callback_clock_and_budget': ('55c5b90228cea12f5a295e4b5ba162ace7de7aef', 'tools/common_wrack_completion_calendar.py'),
    'program_config': ('defc45332', 'compiler/models/qwen3-8b/config.json'),
}

def sector_descriptors(graph, instruction, position):
    """Exact masks/addresses only; no encoded byte values are reconstructed."""
    if instruction['opcode'] != 'KV_WRITE':
        raise ValueError('KV writer instruction required')
    if not 0 <= position < graph['context_capacity']:
        raise ValueError('position aperture')
    a = instruction['attributes']; die = a['die']; layer = a['layer']
    c = graph['config']; hd = c['head_dim']; heads = c['num_key_value_heads']//graph['TP']
    extents = {e['name']: e for r in graph['memory_allocation'] if r['die'] == die for e in r['extents']}
    rows = []
    for kind in ('K', 'V'):
        masks = {}
        for head in range(heads):
            for dim in range(hd):
                offset = (((head*(graph['context_capacity']//16)+position//16)*hd+dim)*16+position%16
                          if kind == 'K' else (head*graph['context_capacity']+position)*hd+dim)
                address = extents[f'L{layer}.{kind}']['base']+offset
                line = address//128; stack = line%4
                local = line//4*128+address%128
                key = stack, local//32
                masks[key] = masks.get(key, 0) | 1 << (local%32)
        for (stack, sector), mask in sorted(masks.items()):
            rows.append(dict(kind=kind, stack=stack, sector=sector, mask=mask,
                             partial=mask != 0xffffffff, ordinal=len(rows)))
    return rows

def bindings(graph):
    producers = {v: op for op in graph['instructions'] for v in op['outputs']}
    consumers = {}
    for op in graph['instructions']:
        for v in op['inputs']:
            consumers.setdefault(v, []).append(op)
    result = []
    for writer in graph['instructions']:
        if writer['opcode'] != 'KV_WRITE':
            continue
        fence, = consumers[writer['outputs'][0]]
        read, = consumers[fence['outputs'][0]]
        scores, = [x for x in consumers[read['outputs'][0]] if x['opcode'] == 'SCORES']
        pv, = [x for x in consumers[read['outputs'][1]] if x['opcode'] == 'PV']
        result.append(dict(writer=writer['id'], fence=fence['id'], read=read['id'],
                           scores=scores['id'], pv=pv['id'],
                           layer=writer['attributes']['layer'], die=writer['attributes']['die'],
                           produced_K=writer['inputs'][0], produced_V=writer['inputs'][1],
                           producer_instructions=[producers[v]['id'] for v in writer['inputs'] if v in producers]))
    return result

def model(repo=ROOT):
    graph = compile_program(); links = bindings(graph); pins = {}
    for name, (revision, path) in PINS.items():
        commit = subprocess.check_output(['git', 'rev-parse', revision], cwd=repo, text=True).strip()
        raw = subprocess.check_output(['git', 'show', commit+':'+path], cwd=repo)
        pins[name] = dict(commit=commit, path=path, sha256=hashlib.sha256(raw).hexdigest())
        if name in ('program', 'packed_KV', 'callback_clock_and_budget', 'program_config'):
            if (ROOT/path).read_bytes() != raw:
                raise ValueError('local model prerequisite differs from immutable source pin: '+name)
    demands = []
    for position in (0, 1):
        for link in links:
            rows = sector_descriptors(graph, graph['instructions'][link['writer']], position)
            reads = Counter(r['stack'] for r in rows if r['partial'])
            writes = Counter(r['stack'] for r in rows)
            commands = [reads[s]+writes[s] for s in range(4)]
            if max(commands) != 144 or sum(commands) != 528 or len(rows) != 272:
                raise ValueError('corrected actual stack floor')
            demands.append(dict(position=position, **link,
                RMW_reads_by_stack=[reads[s] for s in range(4)],
                writes_by_stack=[writes[s] for s in range(4)], commands_by_stack=commands,
                busiest_stack_command_floor=144, sector_ACKs=272,
                payload_port_bytes=16896,
                sector_descriptor_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()))
    # New publication scoreboard is explicitly additional to retained backend,
    # frontend, and 64x675-bit RMW contexts. Index fields are also additional.
    fields = dict(completion_bitmap=272, completed_sector_count=9,
                  four_slot_identities=4*(9+64+32+6+1+21+1),
                  writer_key=256+6+1+21+32+1, reader_lease_flags=3)
    context_bits = sum(fields.values()); contexts = 2
    assert context_bits == 1137
    scoreboard_bits = context_bits*contexts
    # Persistent contiguous-prefix publication is not free. All positions of
    # a layer share an epoch; append-only publication permits one high-water
    # mark per layer rather than pretending an unpriced per-token directory.
    directory_fields = dict(epoch=32, published_prefix_length=22, valid=1, reader_count=2)
    directory_bits = sum(directory_fields.values())*36*2
    ACK_fields = dict(tag=64, epoch=32, sector_ordinal=9, writer_key_SHA=256,
                      die=1, layer=6, position=21, state=3)
    credit_fields = dict(tag=64, epoch=32, sector_ordinal=9, die=1,
                         layer=6, position=21, state=2)
    ACK_bits = sum(ACK_fields.values()); credit_bits = sum(credit_fields.values())
    # Proposed four-entry CDC queues per die, priced independently of existing
    # backend event holds. Four total sector credits bound their occupancy.
    CDC_data_bits = 2*4*(ACK_bits+credit_bits)
    CDC_control_bits = 2*2*(2*3+2*2*3+4)
    mux_bits = 2*3*(272+134) + 2*36*9
    compare_bits = 2*4*(64+32+6+1+21) + 2*256
    return dict(schema='Qwen_finite_sector_ACK_publication_adapter_r1', source_pins=pins,
        encoded_program_instructions=len(graph['instructions']), bindings=links,
        writer_demands=demands, writers=144,
        topology=dict(dies=2, clients_per_die=36, SM_clients=32, vector_injector_clients=4,
                      stacks_per_die=4, shared_read_OR_write_commands_per_stack_fast_cycle=1,
                      combined_bytes_per_stack_fast_cycle=750, frontend_credits_per_stack=4,
                      live_writer_contexts_per_die=1, active_sector_slots_per_writer=4,
                      scoreboard_updates_per_die_serial_cycle=1,
                      slot_policy='Four total active sectors per die baseline; retained backend four-per-stack storage is charged independently, not subtracted.'),
        additional_storage=dict(writer_context_fields=fields, writer_context_bits=context_bits,
            writer_contexts=contexts, scoreboard_bits=scoreboard_bits,
            publication_directory_fields=directory_fields,
            publication_directory_bits=directory_bits,
            additional_CDC_data_bits=CDC_data_bits,
            additional_CDC_control_bits=CDC_control_bits,
            mux_bit_equivalents=mux_bits, comparator_bit_equivalents=compare_bits,
            conservative_register_and_logic_area_mm2=((scoreboard_bits+directory_bits+CDC_data_bits+CDC_control_bits)*.2916+(mux_bits+compare_bits)*.2)/.5/1e6,
            ABI_scope='Candidate slot tag64/epoch32/position21 per Ram; retained controller tag16 bridge and actual hardware identity ABI remain unbound.',
            area_scope='Additional first-order DFF/mux/compare estimate; Includes proposed CDC FF storage; excludes clock tree, placement, detailed CDC mux and routing. Not a slot-fit verdict.'),
        candidate_ACK_transport=dict(sector_ACK_fields=ACK_fields, sector_ACK_payload_bits=ACK_bits,
            reverse_credit_fields=credit_fields, reverse_credit_payload_bits=credit_bits,
            candidate_route_header_bits=64, lane_flit_bits=320,
            ACK_flit_floor=(ACK_bits+64+319)//320,
            reverse_credit_flit_floor=(credit_bits+64+319)//320,
            CDC_depth_per_direction_per_die=4,
            qualification='Proposed ABI/queue footprint only; actual packet header, route assignment, ready protocol and CDC implementation are not admitted.'),
        protocol=[
            'Reserve sole live writer context per die with exact encoded writer ID, epoch, position and one of36 clients.',
            'Reserve sector credit/lock before RMW read; old-sector return then actual merge result precedes WR.',
            'Backend scheduled WR and actual backing-visible callback precede reverse ACK CDC.',
            'Sector-store consumer accepts ACK, stores completion bit, retires; reverse credit CDC then releases sector credit/lock.',
            'Only all272 matching completion bits publish the writer generation; KV_FENCE consumes matching publication.',
            'KV_READ leases every requested prior/current generation; SCORES and PV result visibility and DUT retirement precede lease release.',
            'Sole writer context remains allocated until its mandatory encoded KV_READ lease was acquired and released after SCORES/PV result visibility and DUT retirement.',
            'Generation reuse requires zero readers; sector credits are not held until later attention consumers.'],
        missing_costs=dict(controller_loaded_schedule=None, forward_NoC=None, reverse_ACK_NoC=None,
            actual_CDC_provider=None, scoreboard_accept_store_retire=None, arbitration36_clients=None,
            consumer_RF_shared_issue_and_result=None, opcode_retirement=None, global_weight_KV_contention=None,
            tag64_to_controller_tag16_bridge=None, scoreboard_identity_ABI=None),
        engine_RTL_build_ready=False, whole_program_admission=False, physical_admission=False,
        full_token_cycles=None, hardware_provider_executed=False,
        encoded_KV_payload_reconstructed=False, speed_credit=0,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

class CallbackProvider:
    """Executable bounded callback validator with no automatic time advance.

    Input timestamps are exact rational picoseconds. Payload bytes are absent:
    this validates ownership and event order, not an arithmetic DUT.
    """
    def __init__(self, graph=None):
        self.graph = compile_program() if graph is None else graph
        self.links = {r['writer']: r for r in bindings(self.graph)}
        self.writers = {}; self.slots = {}; self.locks = {}; self.tags = set()
        self.commands = {0: [], 1: []}; self.scoreboard_ports = set()
        self.published = {}; self.directory = {}; self.leases = {}; self.retired = {}; self.results = {}

    @staticmethod
    def time(value):
        t = Fraction(value)
        if t < 0: raise ValueError('negative callback time')
        return t

    def retire(self, position, instruction, result_visible_ps, retire_ps):
        op = self.graph['instructions'][instruction]
        result, done = self.time(result_visible_ps), self.time(retire_ps)
        if result > done: raise ValueError('DUT retire before result visibility')
        if (position, instruction) in self.retired: raise ValueError('duplicate DUT retirement')
        for dependency in op['dependencies']:
            if (position, dependency) not in self.retired or self.retired[position, dependency] > result:
                raise ValueError('encoded instruction dependency not retired')
        if op['opcode'] in ('KV_FENCE', 'KV_READ'):
            link, = [r for r in self.links.values() if r['fence' if op['opcode']=='KV_FENCE' else 'read'] == instruction]
            key = position, link['writer']
            if key not in self.published or self.published[key] > result:
                raise ValueError('matching writer generation not published')
            if op['opcode'] == 'KV_READ' and key not in self.leases:
                raise ValueError('KV read without generation lease')
        self.results[position, instruction] = result
        self.retired[position, instruction] = done

    def begin(self, position, writer, epoch, client, reserve_ps):
        if writer not in self.links or not 0 <= epoch < 1 << 32 or not 0 <= client < 36:
            raise ValueError('writer/epoch/36-client aperture')
        if not 0 <= position < self.graph['context_capacity']:
            raise ValueError('position aperture')
        key = position, writer; link = self.links[writer]; now = self.time(reserve_ps)
        if key in self.writers: raise ValueError('generation overwrite')
        directory = self.directory.get(writer)
        if directory is not None and (directory['epoch'] != epoch or directory['prefix'] != position):
            raise ValueError('append-only same-epoch publication prefix required')
        if sum(w['die']==link['die'] and not w['released'] for w in self.writers.values()) >= 1:
            raise ValueError('finite writer contexts exhausted')
        for dependency in self.graph['instructions'][writer]['dependencies']:
            if (position, dependency) not in self.retired or self.retired[position, dependency] > now:
                raise ValueError('actual produced K/V dependencies required')
        rows = sector_descriptors(self.graph, self.graph['instructions'][writer], position)
        self.writers[key] = dict(die=link['die'], epoch=epoch, client=client,
            reserve=now, descriptors=rows, completed={}, released=False, read_acquired=False)

    def reserve_sector(self, key, ordinal, tag, reserve_ps):
        w = self.writers[key]; now = self.time(reserve_ps)
        if not 0 <= ordinal < len(w['descriptors']) or not 0 <= tag < 1 << 64:
            raise ValueError('sector/tag aperture')
        d = w['descriptors'][ordinal]; stack = w['die'], d['stack']
        lock = *stack, d['sector']; tagkey = *stack, tag
        if now < w['reserve'] or ordinal in w['completed'] or tagkey in self.tags:
            raise ValueError('sector reservation/tag reuse')
        if lock in self.locks or sum(s['stack'][0]==w['die'] for s in self.slots.values()) >= 4:
            raise ValueError('finite sector lock/credit unavailable')
        if any(s['key']==key and s['ordinal']==ordinal for s in self.slots.values()):
            raise ValueError('duplicate in-flight sector')
        self.tags.add(tagkey); self.locks[lock] = tagkey
        self.slots[tagkey] = dict(key=key, ordinal=ordinal, stack=stack, lock=lock,
            descriptor=d, reserve=now, read_return=None, merge=None, write=None,
            column=None, visible=None, accepted=None, stored=None, retired=None)
        return tagkey

    def command(self, tagkey, kind, issue_ps):
        s = self.slots[tagkey]; now = self.time(issue_ps)
        if now < crossing(s['reserve'], FAST): raise ValueError('request CDC not complete')
        if kind == 'read':
            if not s['descriptor']['partial'] or 'read' in s:
                raise ValueError('unneeded/duplicate RMW read')
        elif kind == 'write':
            if s['write'] is not None or s['descriptor']['partial'] and (s['merge'] is None or now < s['merge']+FAST):
                raise ValueError('WR before actual RMW merge or duplicate WR')
        else: raise ValueError('shared controller command kind')
        die, stack = s['stack']
        command = dict(stack=stack, kind=kind, bytes=32, issue_ps=str(now))
        command_budget(self.commands[die]+[command])
        self.commands[die].append(command); s['read' if kind=='read' else 'write'] = now

    def RMW_return_merge(self, tagkey, return_ps, merge_result_visible_ps):
        s = self.slots[tagkey]; returned = self.time(return_ps); merge = self.time(merge_result_visible_ps)
        if 'read' not in s or s['read_return'] is not None or returned < s['read'] or merge < crossing(returned, SLOW):
            raise ValueError('actual RMW return/serial merge visibility required')
        s['read_return'], s['merge'] = returned, merge

    def WR_visible(self, tagkey, column_ps, backing_visible_ps):
        s = self.slots[tagkey]; column, visible = self.time(column_ps), self.time(backing_visible_ps)
        if s['write'] is None or s['visible'] is not None or column < s['write'] or visible < column+7274:
            raise ValueError('actual scheduled WR/backing visibility required')
        s['column'], s['visible'] = column, visible

    def sector_consumer(self, tagkey, epoch, ACK_accept_ps, scoreboard_visible_ps, dut_retire_ps):
        s = self.slots[tagkey]; w = self.writers[s['key']]
        accepted, stored, done = map(self.time, (ACK_accept_ps, scoreboard_visible_ps, dut_retire_ps))
        if s['visible'] is None or epoch != w['epoch'] or s['stored'] is not None:
            raise ValueError('stale/duplicate/unwritten sector ACK')
        registered = (s['visible']//FAST+1)*FAST
        if accepted < crossing(registered, SLOW) or stored < accepted or done < stored:
            raise ValueError('ACK landing is not stored result/DUT retirement')
        if stored % SLOW or (w['die'], stored) in self.scoreboard_ports:
            raise ValueError('finite serial scoreboard port conflict')
        self.scoreboard_ports.add((w['die'], stored))
        s['accepted'], s['stored'], s['retired'] = accepted, stored, done
        w['completed'][s['ordinal']] = stored

    def release_sector(self, tagkey, credit_return_ps):
        s = self.slots[tagkey]; now = self.time(credit_return_ps)
        if s['retired'] is None or now < crossing(s['retired'], FAST):
            raise ValueError('sector credit returned before actual consumer retire/reverse CDC')
        del self.locks[s['lock']]; del self.slots[tagkey]

    def publish(self, key, epoch, publication_ps):
        w = self.writers[key]; now = self.time(publication_ps)
        if epoch != w['epoch'] or key in self.published or len(w['completed']) != len(w['descriptors']):
            raise ValueError('incomplete/stale/duplicate generation publication')
        if now < max(w['completed'].values()): raise ValueError('publication before completion-bit visibility')
        directory = self.directory.get(key[1])
        prefix = directory['prefix'] if directory else 0
        if key[0] != prefix or directory is not None and directory['epoch'] != epoch:
            raise ValueError('append-only publication cannot skip previous generation')
        self.published[key] = now
        self.directory[key[1]] = dict(epoch=epoch, prefix=prefix+1)

    def acquire_read(self, key, epoch, read_landing_ps):
        position, writer = key; w = self.writers[key]; now = self.time(read_landing_ps)
        if w['released']:
            raise ValueError('reader landing after writer context reuse/release')
        if epoch != w['epoch'] or key in self.leases:
            raise ValueError('stale/duplicate reader lease')
        directory = self.directory.get(writer)
        if directory is None or directory['epoch'] != epoch or directory['prefix'] <= position:
            raise ValueError('persistent previous/current generation unpublished')
        generations = [(p, writer) for p in range(position+1)]
        if any(k not in self.published or self.published[k] > now for k in generations):
            raise ValueError('persistent previous/current generation unpublished')
        if len(self.leases) >= 72: raise ValueError('finite reader leases exhausted')
        self.leases[key] = dict(generations=generations, landed=now)
        w['read_acquired'] = True

    def release_read(self, key, consumer_done_ps):
        link = self.links[key[1]]; lease = self.leases[key]; now = self.time(consumer_done_ps)
        for instruction in (link['scores'], link['pv']):
            if (key[0], instruction) not in self.retired or self.retired[key[0], instruction] > now:
                raise ValueError('SCORES/PV actual result and DUT retire required')
        if now < lease['landed']: raise ValueError('consumer done before landing')
        del self.leases[key]

    def release_writer_context(self, key):
        if key not in self.published or any(key in x['generations'] for x in self.leases.values()) or any(s['key']==key for s in self.slots.values()):
            raise ValueError('generation/context reused with live reader or sector transaction')
        if not self.writers[key]['read_acquired']:
            raise ValueError('mandatory encoded KV_READ lease not yet acquired/completed')
        link = self.links[key[1]]
        if any((key[0], instruction) not in self.retired for instruction in (link['read'], link['scores'], link['pv'])):
            raise ValueError('mandatory KV_READ/SCORES/PV result visibility and DUT retirement required')
        if self.writers[key]['released']:
            raise ValueError('duplicate writer context release')
        self.writers[key]['released'] = True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(model(args.repo), indent=2, sort_keys=True)+'\n')
