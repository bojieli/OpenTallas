"""Join Arendt's frozen S81 allocation to the existing source/compiler APIs.

No payload reads or arithmetic execution. Factories are supplied by the actual
caller, so this module does not import a different checkout's cached compiler.
"""
import gzip
import hashlib
import json
from pathlib import Path

CANONICAL = 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
SOURCE = 'results/uarch/dsrom_native_weight_address_join_20261002'
HASHES = {
    'inventory.json': '0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480',
    'stage_map.json': '47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815',
    'matrix_map.jsonl.gz': '985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326',
}


class CanonicalS81Execution:
    def __init__(self, owner, *, source_execution_factory=None, stage_join_factory=None):
        if source_execution_factory is None:
            from dsrom_s82_payload_interface import SourceExecution
            source_execution_factory = SourceExecution
        if stage_join_factory is None:
            from dsrom_stage_program_join import StageProgramJoin
            stage_join_factory = StageProgramJoin
        self.owner = Path(owner).resolve()
        base = self.owner / CANONICAL
        raw = {}
        for name, expected in HASHES.items():
            raw[name] = (base / name).read_bytes()
            if hashlib.sha256(raw[name]).hexdigest() != expected:
                raise ValueError(f'canonical S81 source changed: {name}')
        inventory = json.loads(raw['inventory.json'])
        stage_map = json.loads(raw['stage_map.json'])
        if (inventory['pairs_per_rank_die'], inventory['BF_dual_pairs'], inventory['TP'],
                len(stage_map['PHW_required_by_stage'])) != (2417,519,4,81):
            raise ValueError('canonical S81 geometry mismatch')
        matrices = [json.loads(line) for line in gzip.decompress(raw['matrix_map.jsonl.gz']).splitlines()]
        if len(matrices) != 46671:
            raise ValueError('canonical S81 fragment extent mismatch')
        source = self.owner / SOURCE
        demand_raw = (source / 'inputs/demand-r5.json.gz').read_bytes()
        bindings_raw = (source / 'r3/node_bindings.jsonl.gz').read_bytes()
        demand = json.loads(gzip.decompress(demand_raw))
        bindings = [json.loads(line) for line in gzip.decompress(bindings_raw).splitlines()]
        # The owner API checks literal node/template hashes and dimensions;
        # Popper's compiler supplies the same unique fragment key/CFG mapping.
        self.source = source_execution_factory(matrices, bindings, demand)
        self.stage_join = stage_join_factory(matrices, stage_map, pairs=2417,
                                             BF_pairs=519, stage_count=81)
        self.input_sha256 = {str(Path(CANONICAL)/n): hashlib.sha256(b).hexdigest()
                             for n,b in raw.items()}
        self.input_sha256.update({str(Path(SOURCE)/n): hashlib.sha256(b).hexdigest()
                                 for n,b in [('inputs/demand-r5.json.gz',demand_raw),
                                             ('r3/node_bindings.jsonl.gz',bindings_raw)]})

    def dispatch(self, node, rank, *, expert_ids=None):
        return self.stage_join.compile_operation(self.source, node, rank, expert_ids=expert_ids)

    def emit_programs(self, requests, out, *, program_address_bits=14):
        """Requests contain real source node/rank and live EIDs for expert ops.

        No cached reduced instruction widening or allocation-stage substitution.
        Caller still supplies actual context restore, input visibility, gather
        and retirement. Returned entries are the native program entry points.
        """
        dispatches = [self.dispatch(r['node'], r['rank'], expert_ids=r.get('expert_ids'))
                      for r in requests]
        return self.stage_join.emit_programs(dispatches, out,
                                             program_address_bits=program_address_bits)

    def emit_stage(self, stage, rank, out):
        return self.stage_join.emit_stage(stage, rank, out)

    def emit_nonfield_run(self, nodes, stage, rank, out):
        """Emit one consecutive literal source run on the caller's actual die.

        A run stays inside one core launch: no inserted END/reset between SU,
        HE, collective or other dependent native instructions. The caller owns
        the non-field service home and supplies that actual stage/rank.
        """
        import hdc_isa_v41 as ISA
        self.stage_join.keys(stage, rank)  # actual selected die bounds
        if not nodes or len(nodes) != len(set(nodes)):
            raise ValueError('nonempty unique source run required')
        words, records = [], []
        scope, previous = None, None
        for node in nodes:
            source = self.source.nodes[node]
            binding = self.source.bindings[node]
            if source['kind'] != 'instruction' or binding.get('address_bound'):
                raise ValueError('field/service node is not a dedicated native instruction')
            index = source['instruction_index']
            if previous is not None and (source['scope'] != scope or index != previous+1):
                raise ValueError('non-field source order must be consecutive within one scope')
            scope, previous = source['scope'], index
            instruction = source['instruction']
            if ((instruction.get('unit') == ISA.UNIT_QE and 'qe_wbase' in instruction)
                    or (instruction.get('unit') == ISA.UNIT_ME and instruction.get('me_wsrc') == 0)):
                raise ValueError('unbound field instruction needs the canonical field dispatcher')
            word = ISA.encode(full_shape=True, **{k:tuple(v) if isinstance(v,list)
                              and not k.startswith('_') else v for k,v in instruction.items()})
            if hashlib.sha256(word.to_bytes(256,'little')).hexdigest() != source['template_word_sha256']:
                raise ValueError('literal non-field source template changed')
            words.append(word)
            records.append(dict(node=node, pc=len(words)-1, instruction=instruction,
                                template_word_sha256=source['template_word_sha256']))
        if ISA.FULL_INSTR_BITS != 2048 or len(words)+1 > 1 << 14:
            raise ValueError('actual native instruction/entry capacity mismatch')
        words.append(ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31))
        out = Path(out); out.mkdir(parents=True,exist_ok=False)
        raw = ''.join(f'{word:0512x}\n' for word in words).encode()
        (out/'prog.hex').write_bytes(raw)
        entry = dict(stage=stage, rank=rank, entry=0, nodes=records,
                     instruction_bits=2048, program_sha256=hashlib.sha256(raw).hexdigest(),
                     caller_owned_service_home=True, context_restore_required=True,
                     source_input_and_output_lease_required=True,
                     context_restore_and_remote_drain_required=True,
                     native_execution_qualified=False)
        (out/'dispatch.json').write_text(json.dumps(entry,indent=2)+'\n')
        return entry

    def emit_minimum_nonfield_run(self, nodes, stage, rank, out, *, symbol="s81_native_operations"):
        """Compile literal operators for existing PrefixNativeEngine callbacks.

        This does not make a missing native provider executable. Non SU/HE
        instructions require their actual participant rather than relabelling
        one of these two engines. Existing prog.hex/dispatch.json stay the
        authority; the C++ table copies their exact 2048-bit words.
        """
        import re
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", symbol):
            raise ValueError("C++ native operation symbol required")
        for node in nodes:
            if self.source.nodes[node].get('instruction', {}).get('unit') not in (2, 5):
                raise ValueError(f"actual native nonfield provider absent for {node}")
        entry = self.emit_nonfield_run(nodes, stage, rank, out)
        words = (Path(out)/'prog.hex').read_text().splitlines()
        rows = []
        for record, text in zip(entry['nodes'], words[:-1]):
            word = int(text, 16)
            if hashlib.sha256(word.to_bytes(256, 'little')).hexdigest() != record['template_word_sha256']:
                raise ValueError('native operation differs from emitted source word')
            lanes = ','.join(f'0x{(word >> (32*k)) & 0xffffffff:08x}u' for k in range(64))
            rows.append('DsromS81PrefixOperation{%d,%d,"%s",{%s}}' % (
                record['pc'], record['instruction']['unit'], record['template_word_sha256'], lanes))
        header = ('#pragma once\n#include "s81_minimum_prefix.hpp"\n'
                  'inline std::vector<DsromS81PrefixOperation> '+symbol+'(){return {'+
                  ',\n'.join(rows)+'};}\n')
        (Path(out)/'native_operations.hpp').write_text(header)
        return entry
