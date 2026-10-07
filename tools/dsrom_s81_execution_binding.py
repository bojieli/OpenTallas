"""Join Arendt's frozen S81 allocation to the existing source/compiler APIs.

No payload reads or arithmetic execution. Factories are supplied by the actual
caller, so this module does not import a different checkout's cached compiler.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path

CANONICAL = 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
SOURCE = 'results/uarch/dsrom_native_weight_address_join_20261002'
HASHES = {
    'inventory.json': '0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480',
    'stage_map.json': '47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815',
    'matrix_map.jsonl.gz': '985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326',
}


# OT_DSROM_S81_RELEASE=20261007: the bf_merge_ksplit released binding (Claude bf-double, owner-adopted 2026-10-07;
# tools/dsrom_bf_double_alloc.py --shared --pbf 2304 --ksplit gate, mixed-slot die: 2,304 pairs, 512 BF = 4 a region,
# 77 stages).  Default: the 20261004 binding the pinned evidence was built on.
RELEASES = {
    '20261004': dict(dir=CANONICAL, hashes=HASHES, pairs=2417, bf=519, stages=81, matrices=46671),
    '20261007': dict(dir='results/uarch/dsrom_s81_released_binding_20261007/canonical',
                     hashes='manifest.json', pairs=2304, bf=512, stages=77, matrices=None),
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
        rel = RELEASES[os.environ.get('OT_DSROM_S81_RELEASE', '20261004')]
        canonical = rel['dir']
        base = self.owner / canonical
        hashes = rel['hashes'] if isinstance(rel['hashes'], dict) else \
            json.loads((base / rel['hashes']).read_text())['sha256']
        raw = {}
        for name, expected in hashes.items():
            raw[name] = (base / name).read_bytes()
            if hashlib.sha256(raw[name]).hexdigest() != expected:
                raise ValueError(f'canonical S81 source changed: {name}')
        inventory = json.loads(raw['inventory.json'])
        stage_map = json.loads(raw['stage_map.json'])
        geo = (inventory.get('pairs_per_rank_die', inventory.get('pairs_bf_stage')),
               inventory.get('BF_dual_pairs', inventory.get('BF_pairs_TP4', 0) // max(1, 4 * inventory['stages'])),
               inventory['TP'], len(stage_map['PHW_required_by_stage']))
        if geo != (rel['pairs'], rel['bf'], 4, rel['stages']):
            raise ValueError(f'canonical S81 geometry mismatch {geo}')
        matrices = [json.loads(line) for line in gzip.decompress(raw['matrix_map.jsonl.gz']).splitlines()]
        if rel['matrices'] is not None and len(matrices) != rel['matrices']:
            raise ValueError('canonical S81 fragment extent mismatch')
        source = self.owner / SOURCE
        demand_raw = (source / 'inputs/demand-r5.json.gz').read_bytes()
        bindings_raw = (source / 'r3/node_bindings.jsonl.gz').read_bytes()
        demand = json.loads(gzip.decompress(demand_raw))
        bindings = [json.loads(line) for line in gzip.decompress(bindings_raw).splitlines()]
        # The owner API checks literal node/template hashes and dimensions;
        # Popper's compiler supplies the same unique fragment key/CFG mapping.
        self.source = source_execution_factory(matrices, bindings, demand)
        self.stage_join = stage_join_factory(matrices, stage_map, pairs=rel['pairs'],
                                             BF_pairs=rel['bf'], stage_count=rel['stages'])
        self.input_sha256 = {str(Path(canonical)/n): hashlib.sha256(b).hexdigest()
                             for n,b in raw.items()}
        self.input_sha256.update({str(Path(SOURCE)/n): hashlib.sha256(b).hexdigest()
                                 for n,b in [('inputs/demand-r5.json.gz',demand_raw),
                                             ('r3/node_bindings.jsonl.gz',bindings_raw)]})

    def target_source_nodes(self, layers, *, position, include_head=True):
        """Complete source-order scopes for the DS1M native caller.

        This selects no activations/history and executes no control branches.
        Fences and control nodes remain in the sequence; the caller must use
        their existing native completion paths, not discard them as non-math.
        Dynamic expert dispatch still goes through dispatch at its real issue.
        """
        if type(position) is not int or position != 1048575:
            raise ValueError('DS target caller requires position1048575')
        if (not layers or any(type(x) is not int or not 0 <= x < 40 for x in layers)
                or list(layers) != sorted(set(layers))):
            raise ValueError('ordered distinct source layers0..39 required')
        if type(include_head) is not bool:
            raise ValueError('explicit head selection required')
        scopes = list(layers) + (['head'] if include_head else [])
        result = []
        for scope in scopes:
            selected = [n for n in self.source.nodes.values() if n['scope'] == scope]
            instructions = [n for n in selected if n['kind'] == 'instruction']
            if (not instructions or [n['instruction_index'] for n in instructions]
                    != list(range(len(instructions)))):
                raise ValueError('source scope has missing/reordered instruction')
            result.extend(n['id'] for n in selected)
        return tuple(result)

    def target_native_operation(self, node, *, position, native_units, dynamic=None):
        """One literal operation for the existing PrefixNativeEngine path.

        Field nodes use dispatch instead; native dynamic selectors must be
        actual captured values. No instruction is widened or re-encoded with
        guessed runtime selectors. Control/fences require their real caller.
        """
        import hdc_isa_v41 as ISA
        if type(position) is not int or position != 1048575:
            raise ValueError('DS target caller requires position1048575')
        source = self.source.nodes[node]
        if source['kind'] != 'instruction' or self.source.bindings[node].get('address_bound'):
            raise ValueError('use actual field dispatcher or fence consumer')
        instruction = source['instruction']
        if instruction['unit'] not in native_units:
            raise ValueError('actual native operator provider absent')
        word = ISA.encode(full_shape=True, **{k:tuple(v) if isinstance(v,list)
                          and not k.startswith('_') else v for k,v in instruction.items()})
        if hashlib.sha256(word.to_bytes(256,'little')).hexdigest() != source['template_word_sha256']:
            raise ValueError('target literal source template changed')
        producer = (int(node[4:]) if node in {f'L0.I{i}' for i in range(7)}
                    else 9 + list(self.source.nodes).index(node))
        if producer >= 1 << 14:
            raise ValueError('publication producer entry14 exhausted')
        return dict(index=producer, unit=instruction['unit'],
                    template_sha256=source['template_word_sha256'],
                    instruction=tuple((word >> (32*k)) & 0xffffffff for k in range(64)),
                    output_extents=minimum_vm_extents(instruction,dynamic=dynamic))

    def target_required_bindings(self, layers, *, position, include_head=False):
        """Literal node census used by the factory, including sideband producers.

        A field actor and a quantizer share ISA unit3 but are different native
        providers. Unit presence alone must never admit a complete program.
        Instructions are retained verbatim so runtime dynamic operands still
        require their real captured source values.
        """
        result = []
        for node in self.target_source_nodes(layers, position=position,
                                             include_head=include_head):
            source = self.source.nodes[node]
            instruction = source.get('instruction', {})
            unit = instruction.get('unit')
            if source['kind'] != 'instruction':
                provider = source['kind']
            elif unit == 3:
                mode = instruction.get('qe_mode', 0)
                provider = {0:'field', 1:'qdq8-window', 2:'qdq8-index',
                            3:'qdq4e-ckv'}[mode]
            else:
                provider = {0:'control', 1:'matrix', 2:'su', 4:'xu',
                            5:'he', 6:'collective'}[unit]
            result.append(dict(node=node, kind=source['kind'], unit=unit,
                               provider=provider, instruction=instruction,
                               template_sha256=source.get('template_word_sha256')))
        return tuple(result)

    def require_target_bindings(self, layers, bindings, *, position,
                                include_head=False):
        """Fail closed before issue if any selected native node is unbound.

        Bindings map exact source node to its provider kind. This is a source
        enrollment check, not a claim of execution, visibility or timing.
        """
        required = self.target_required_bindings(layers, position=position,
                                                 include_head=include_head)
        expected = {r['node']:r['provider'] for r in required}
        missing = [n for n in expected if n not in bindings]
        wrong = [n for n in expected if n in bindings and bindings[n] != expected[n]]
        extra = [n for n in bindings if n not in expected]
        if missing or wrong or extra:
            raise ValueError(f'native target bindings missing={missing} '
                             f'wrong_provider={wrong} outside_selected_program={extra}')
        return required

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

    def emit_current_stage_candidate(self, out, *, stage=37, layer=20,
                                     expert_ids_by_node=None, context=None, calendar_pricer=None):
        from dsrom_s81_source_plan_emit import emit_current_stage_candidate
        return emit_current_stage_candidate(self, out, stage=stage, layer=layer,
            expert_ids_by_node=expert_ids_by_node, context=context, calendar_pricer=calendar_pricer)

    def emit_candidate_dispatch(self, candidate, context, out, *, layers=None,
                                expert_ids_by_node=None, include_fields=True, endpoint_map=None, fragment_endpoints=None):
        """Compile inactive owner-assignment mechanics using these source objects.

        No allocation/model replay, candidate adoption, numerical execution or
        invented service home. Actual EIDs are required before expert emission.
        """
        from dsrom_s81_source_plan_emit import emit_candidate_dispatch
        return emit_candidate_dispatch(self, candidate, context, out, layers=layers,
            expert_ids_by_node=expert_ids_by_node, include_fields=include_fields,
            endpoint_map=endpoint_map, fragment_endpoints=fragment_endpoints)

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

    def emit_minimum_nonfield_run(self, nodes, stage, rank, out, *, symbol="s81_native_operations", native_units=(2, 5), dynamic_by_node=None):
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
            if self.source.nodes[node].get('instruction', {}).get('unit') not in native_units:
                raise ValueError(f"actual native nonfield provider absent for {node}")
        entry = self.emit_nonfield_run(nodes, stage, rank, out)
        words = (Path(out)/'prog.hex').read_text().splitlines()
        rows, enrolled = [], []
        dynamic_by_node = {} if dynamic_by_node is None else dynamic_by_node
        source_order = list(self.source.nodes)
        for record, text in zip(entry['nodes'], words[:-1]):
            word = int(text, 16)
            if hashlib.sha256(word.to_bytes(256, 'little')).hexdigest() != record['template_word_sha256']:
                raise ValueError('native operation differs from emitted source word')
            lanes = ','.join(f'0x{(word >> (32*k)) & 0xffffffff:08x}u' for k in range(64))
            node = record['node']
            producer = int(node[4:]) if node in {f'L0.I{i}' for i in range(7)} else 9+source_order.index(node)
            if producer >= 1 << 14:
                raise ValueError('existing publication producer entry14 exhausted')
            ranges = minimum_vm_extents(record['instruction'], dynamic=dynamic_by_node.get(node))
            if producer >= 9:
                pairs = ','.join('{%du,%du}' % tuple(r) for r in ranges)
                enrolled.append('pub.enroll_literal(%du,{%s});' % (producer,pairs))
            rows.append('DsromS81PrefixOperation{%d,%d,"%s",{%s}}' % (
                producer, record['instruction']['unit'], record['template_word_sha256'], lanes))
        header = ('#pragma once\n#include "s81_minimum_prefix.hpp"\n#include "s81_prefix_publication.hpp"\n'
                  'inline std::vector<DsromS81PrefixOperation> '+symbol+'(){return {'+
                  ',\n'.join(rows)+'};}\n'
                  'inline void '+symbol+'_enroll(dsrom_s81_minimum::PrefixPublication& pub){'+
                  ''.join(enrolled)+'}\n')
        (Path(out)/'native_operations.hpp').write_text(header)
        return entry


def minimum_vm_extents(instruction, *, dynamic=None, tp=4):
    """Actual scalar output addresses of the literal native instruction.

    No values/acceptance are produced. Dynamic selectors require their actual
    captured values, and KV writes retain their separate native publication.
    Duplicate scalar strobes in one instruction require a supported native
    rewrite path; they are refused rather than silently coalesced.
    """
    dynamic = {} if dynamic is None else dynamic
    def integer(value, label):
        if type(value) is not int or value < 0:
            raise ValueError(f'captured nonnegative integer required: {label}')
        return value
    def f(name):
        return integer(instruction.get(name, 0), name)
    def d(name):
        selector = instruction.get(name, 0)
        if selector == 0:
            return 0
        if selector not in dynamic:
            raise ValueError(f'actual captured dynamic value required: {name}')
        return integer(dynamic[selector], name)
    addresses = set()
    def add(address):
        if not 0 <= address < 1 << 19 or address in addresses:
            raise ValueError('out-of-range or duplicate literal VM output')
        addresses.add(address)
    unit = f('unit')
    if unit == 2:
        no, ni = f('su_nout')+d('su_d_nout'), f('su_nin')+d('su_d_nin')
        if no * ni > 1 << 19:
            raise ValueError('native output enumeration exceeds VM aperture')
        output_base = f('o_base')+d('o_d')
        if f('dst') == 1:
            for outer in range(no):
                for inner in range(ni):
                    add(output_base+outer*f('o_so')+inner*f('o_si'))
        if f('red') or f('red_tree'):
            for outer in range(1 if f('red_whole') or f('red_tree') else no):
                add(f('r_base')+outer*f('r_so'))
    elif unit == 3:
        count = f('qe_nout') if f('qe_mode') == 0 else 32*f('qe_nb')
        for row in range(count):
            add(f('qe_obase')+d('qe_d_obase')+row)
    elif unit == 5:
        for row in range(f('he_nout')):
            add(f('he_obase')+row)
    elif unit == 4:
        if f('xu_op') not in (0, 1):
            raise ValueError('actual EHASH/EGATHER output provider required')
        count = 16 if f('xu_op') == 1 else f('xu_k')+d('xu_d_k')
        for row in range(count):
            add(f('xu_dst')+row)
    elif unit == 6:
        if type(tp) is not int or tp != 4 or f('coll_op') not in (0, 1):
            raise ValueError('actual selected TP4 collective output provider required')
        count = f('coll_n')*(tp if f('coll_op') == 1 else 1)
        for row in range(count):
            add(f('coll_dst')+row)
    else:
        raise ValueError('actual ME/control output extent binding required')
    ranges = []
    for address in sorted(addresses):
        if ranges and ranges[-1][0]+ranges[-1][1] == address:
            ranges[-1][1] += 1
        else:
            ranges.append([address, 1])
    return ranges
