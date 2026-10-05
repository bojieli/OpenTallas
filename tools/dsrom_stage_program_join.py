"""Source-bound ROM stage CFG, key lookup and executable fragment dispatch.

Consumes an existing authoritative allocation; does not allocate weights,
read checkpoint payloads, evaluate tensors, launch hardware or price free
transport. Missing phases/owners always refuse. Zero CFG is permitted only
for an explicitly inactive pair in a known, allocated phase.
"""
import copy
import bisect
import gzip
import hashlib
import json
import math
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _source():
    # The installed compiler owns the exact NB2/PP1 25-word format. No second
    # transcribed bit codec or numerical implementation is introduced here.
    import dsrom_full_owner_compiler as compiler
    return compiler


class StageProgramJoin:
    def __init__(self, matrices, stage_map, *, pairs, BF_pairs, stage_count):
        require((stage_count, pairs, BF_pairs) == (81, 2417, 519),
                'selected S81 NP2417/BF519 required; S82 is historical')
        self.stage_map = copy.deepcopy(stage_map)
        self.pairs, self.stages = pairs, stage_count
        phws = stage_map['PHW_required_by_stage']
        bounds, bf = stage_map['region_bounds'], stage_map['BF_site_IDs']
        require(len(phws) == stage_count and len(bounds) == 129 and
                bounds == [r*pairs//128 for r in range(129)], 'selected ragged R128 ownership')
        require(len(bf) == BF_pairs and len(set(bf)) == BF_pairs and
                all(type(p) is int and 0 <= p < pairs for p in bf), 'actual BF site census')
        dies = stage_map['rank_dies']
        require(len(dies) == 4*stage_count and
                {(d['stage'], d['rank'], d['die_id']) for d in dies} ==
                {(s, r, 4*s+r) for s in range(stage_count) for r in range(4)},
                'exact physical stage/rank assignment')
        self.by_identity, self.by_stage = {}, {s: [] for s in range(stage_count)}
        self.groups = {}
        for m in matrices:
            require(type(m['stage']) is int and 0 <= m['stage'] < stage_count and
                    m['compiled_NP'] == pairs and m['format'] in ('fp4', 'fp8', 'bf16'),
                    'matrix belongs to a different allocation')
            identity = (m['layer'], m['alias'])
            require(identity not in self.by_identity, 'duplicate matrix fragment identity')
            original = m.get('original_alias', m['alias'])
            group = self.groups.setdefault((m['layer'], original), [])
            offset = m.get('row_offset', 0)
            require(offset == sum(row['rows'] for row in group), 'fragment row gap/overlap/order')
            ordinal = len(group)
            base = _source().key_for(m['layer'], original)
            require(base & 4095 == 0 and ordinal < 4096, 'no spare low12 fragment namespace')
            key = base | ordinal
            require(0 <= key < 1 << 30, 'actual decoder key30 overflow')
            stage = m['stage']; phase = len(self.by_stage[stage])
            require(type(phws[stage]) is int and 1 <= phws[stage] <= 10 and
                    phase < 1 << phws[stage], 'source PHW phase capacity')
            # Canonical Pool.matrix has no owner override: its native address
            # API defaults to all four physical rank replicas. An explicit
            # owner override (e.g. historical multicast) remains authoritative.
            owners = m.get('physical_owner_ranks', [0, 1, 2, 3])
            require(owners and len(set(owners)) == len(owners) and
                    all(type(r) is int and 0 <= r < 4 for r in owners), 'physical owner ranks')
            require(len(m['rank_slices']) == 4 and m['rows'] > 0 and m['K'] > 0,
                    'source rank/shape metadata')
            self._validate_plans(m, bounds)
            row = dict(matrix=m, stage=stage, phase=phase, key=key,
                       key_word=(1 << 31) | ((m['format'] == 'bf16') << 30) | key,
                       identity=identity, original_alias=original, fragment_ordinal=ordinal,
                       row_offset=offset, rows=m['rows'], matrix_sha256=digest(m), owners=owners)
            self.by_identity[identity] = row; self.by_stage[stage].append(row); group.append(row)
        require(self.by_identity, 'empty source allocation')
        for stage, rows in self.by_stage.items():
            keys = [r['key_word'] for r in rows]
            require(len(keys) == len(set(keys)), 'stage decoder key collision')
        self._cfg_cache = {}

    @staticmethod
    def _validate_plans(m, bounds):
        segments = m['segments']
        require(segments and all(len(x) == 2 and all(type(v) is int for v in x)
                                and x[0] >= 0 and x[1] > 0 for x in segments),
                'source ordered K segments')
        require(segments[0][0] == 0 and segments[-1][0]+segments[-1][1] == m['K']
                and all(a[0]+a[1] == b[0] for a, b in zip(segments, segments[1:])),
                'source K segment gap/overlap')
        require(m['plans'], 'allocated matrix lacks CFG/payload plans')
        coverage = {i: [] for i in range(len(segments))}; pairs = set()
        for run in m['plans']:
            require(len(run) == 7 and all(type(x) is int for x in run), 'native plan tuple')
            si, pair, first, n, stride, start, words = run
            require(si in coverage and 0 <= pair < bounds[-1] and pair not in pairs
                    and first >= 0 and 1 <= n <= 8 and stride > 0 and
                    start >= 0 and start % 2 == 0 and start+n*words <= 8192,
                    'invalid native CFG/payload pair owner')
            pairs.add(pair)
            require(words == _source().S.seg_words(m['format'], *segments[si]),
                    'source word codec length changed')
            superrows = [first+j*stride for j in range(n)]
            region = bisect.bisect_right(bounds, pair)-1
            require(all(r % 128 == region for r in superrows), 'ragged pair/root row owner')
            coverage[si].extend(superrows)
        expected = list(range((m['rows']+1)//2))
        require(all(sorted(rows) == expected for rows in coverage.values()),
                'missing/duplicate source row tree')

    @classmethod
    def from_files(cls, matrices, stage_map, *, matrix_sha256, stage_map_sha256):
        require(hashlib.sha256(Path(matrices).read_bytes()).hexdigest() == matrix_sha256,
                'authoritative matrix archive changed')
        raw = Path(stage_map).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == stage_map_sha256,
                'authoritative stage map changed')
        with gzip.open(matrices, 'rt') as stream:
            return cls(map(json.loads, stream), json.loads(raw),
                       pairs=2417, BF_pairs=519, stage_count=81)

    def keys(self, stage, rank):
        require(type(stage) is int and stage in self.by_stage, 'unowned stage')
        require(type(rank) is int and 0 <= rank < 4, 'unowned physical rank')
        rows = self.by_stage[stage]
        return [r['key_word'] if rank in r['owners'] else 0 for r in rows] + [0]*((1 << self.stage_map['PHW_required_by_stage'][stage])-len(rows))

    def lookup(self, stage, key, *, ME):
        require(type(key) is int and 0 <= key < 1 << 30 and type(ME) is bool,
                'exact key30 and QE/ME mode required')
        require(type(stage) is int and stage in self.by_stage, 'unowned stage')
        matches = [r for r in self.by_stage[stage] if r['key'] == key
                   and (r['matrix']['format'] == 'bf16') == ME]
        require(len(matches) == 1, 'missing/ambiguous executable decoder phase')
        return matches[0]['phase']

    def cfg(self, stage, rank, pair, address):
        require(type(stage) is int and stage in self.by_stage and type(rank) is int and 0 <= rank < 4,
                'unowned physical stage/rank')
        require(type(pair) is int and 0 <= pair < self.pairs and
                type(address) is int and address >= 0, 'CFG pair/address bounds')
        phase, word = divmod(address, 25)
        require(phase < len(self.by_stage[stage]), 'missing allocated CFG phase')
        row = self.by_stage[stage][phase]; m = row['matrix']
        require(rank in row['owners'], 'multicast consumer is not field owner')
        cache_key = (stage, phase, pair)
        if cache_key not in self._cfg_cache:
            # Filter to the accepted pair without changing ordering or fields.
            runs = [r for r in m['plans'] if r[1] == pair]
            payload = _source().phase_cfg(dict(m, plans=runs), pair)
            require(len(payload) == 25 and all(type(x) is int and 0 <= x < 1 << 48 for x in payload),
                    'native CFG48 payload')
            self._cfg_cache[cache_key] = tuple(payload)
        return self._cfg_cache[cache_key][word]

    def dispatch(self, resolved, instruction, *, encode):
        """Bind a source-verified operation to actual encoded QE/ME commands.

        SourceExecution resolves live expert IDs before this call. Only weight
        key, indexed resolution and row-fragment shape/output addresses change.
        The source input/K/segments, FP rounding, predicate and waits survive.
        A failed native ME admission remains a refusal, never rewritten away.
        """
        require(resolved.get('source_identity_verified') is True, 'source verified operation required')
        f = copy.deepcopy(instruction)
        qe = f.get('unit') == 3 and 'qe_wbase' in f
        me = f.get('unit') == 1 and f.get('me_wsrc') == 0
        require(qe or me, 'dedicated non-field operator needs its own source interface')
        if me:
            from dsrom_native_weight_address_join import me_failures
            require(not me_failures(f), 'original native ME admission fails')
        original_word = encode(f)
        result = []; expected = 0
        for fragment in resolved['fragments']:
            m = fragment['matrix']; identity = (m['layer'], m['alias'])
            require(identity in self.by_identity, 'missing authoritative fragment')
            row = self.by_identity[identity]
            require(digest(m) == row['matrix_sha256'], 'fragment physical allocation changed')
            require((m['format'] == 'bf16') == me, 'source QE/ME format branch')
            require(fragment['gather_local_rows'] == [expected, expected + m['rows']] and
                    row['row_offset'] == expected, 'actual ordered gather range')
            K = f['qe_nb']*32 if qe else f['me_k']*(1 << f.get('me_split', 0))
            require(m['K'] == K and fragment['ordered_K'] == m['segments'], 'source K/tree changed')
            rank = fragment['die_id'] % 4
            require(fragment['die_id'] == 4*row['stage']+rank and rank in row['owners'],
                    'actual physical owner die')
            out = copy.deepcopy(f)
            if qe:
                out.update(qe_wbase=row['key'], qe_ind=0, qe_nout=m['rows'],
                           qe_tiles=math.ceil(m['rows']/128), qe_obase=f['qe_obase']+expected)
                changed = {'qe_wbase', 'qe_ind', 'qe_nout', 'qe_tiles', 'qe_obase'}
            else:
                require(expected % 16 == 0, 'native ME output word16 alignment')
                out.update(me_wbase=row['key'], me_nout=m['rows'],
                           me_tiles=math.ceil(m['rows']/512), me_obase=f['me_obase']+expected//16)
                changed = {'me_wbase', 'me_nout', 'me_tiles', 'me_obase'}
            require(all(out.get(k) == f.get(k) for k in set(out)|set(f) if k not in changed),
                    'arithmetic/predicate/input control changed')
            phase = self.lookup(row['stage'], row['key'], ME=me)
            word = encode(out)
            result.append(dict(stage=row['stage'], rank=rank, die_id=fragment['die_id'], phase=phase,
                               key=row['key'], instruction=out, word=word, original_word=original_word,
                               changed_fields=sorted(k for k in changed if out.get(k) != f.get(k)),
                               cfg_logical_range=[25*phase, 25*(phase+1)],
                               gather_local_rows=list(fragment['gather_local_rows']),
                               ordered_K=copy.deepcopy(m['segments']),
                               result_multicast_required=fragment['result_multicast_required'],
                               source_matrix_sha256=row['matrix_sha256']))
            expected += m['rows']
        require(result and expected == (f['qe_nout'] if qe else f['me_nout']),
                'incomplete source output coverage')
        return dict(node=resolved['node'], fragments=result, predicate=f.get('pred', 0),
                    source_dispatch_bound=True, context_restore_required=True,
                    transport_and_visibility_receipts_required=True,
                    native_execution_qualified=False, physical_qualified=False)

    def compile_operation(self, source_execution, node, rank, *, expert_ids=None):
        """Production join: literal checked source descriptor -> encoded dispatch.

        Reuses the owner's SourceExecution/EID binding and current native ISA;
        rejects an ISA/template mismatch before producing any command.
        """
        import hdc_isa_v41 as ISA
        source = source_execution.nodes[node]
        binding = source_execution.bindings[node]
        require(digest(source) == binding['source_node_semantic_sha256'],
                'literal source node changed')
        def encode(fields):
            return ISA.encode(full_shape=True, **{k: tuple(v) if isinstance(v, list)
                              and not k.startswith('_') else v for k, v in fields.items()})
        word = encode(source['instruction'])
        require(hashlib.sha256(word.to_bytes(ISA.FULL_INSTR_BITS//8, 'little')).hexdigest()
                == source['template_word_sha256'] == binding['template_word_sha256'],
                'native source decoder/template mismatch')
        resolved = source_execution.resolve(node, rank, expert_ids=expert_ids)
        return self.dispatch(resolved, source['instruction'], encode=encode)

    def emit_stage(self, stage, rank, out):
        """Write the actual host's spine_keys.hex/e<pair>.cfg.hex initializer ABI.

        All2417 pair files are emitted; known inactive pair/phase words are
        zero, while absent phases refuse. No ROM weight or VM payload is made.
        Rank-nonowner phases have invalid key entries and explicit inactive CFG
        slots, so multicast consumers cannot launch a duplicate field operation.
        """
        out = Path(out)
        keys = self.keys(stage, rank)
        out.mkdir(parents=True, exist_ok=False)
        (out/'spine_keys.hex').write_text(''.join(f'{key:08x}\n' for key in keys))
        rows = self.by_stage[stage]
        for pair in range(self.pairs):
            with (out/f'e{pair}.cfg.hex').open('x') as stream:
                for row in rows:
                    if rank not in row['owners']:
                        words = (0,)*25  # explicit allocated nonowner phase
                    else:
                        words = [self.cfg(stage, rank, pair, row['phase']*25+w) for w in range(25)]
                    stream.writelines(f'{word:012x}\n' for word in words)
            # Streaming emitter memory stays bounded to this pair's source CFG.
            self._cfg_cache.clear()
        receipt = dict(stage=stage, rank=rank, pairs=self.pairs, source_phases=len(rows),
                       PHW=self.stage_map['PHW_required_by_stage'][stage],
                       cfg_words_per_pair=25*len(rows), key_words=len(keys),
                       physical_owner_nonexecuting_phases=[r['phase'] for r in rows
                             if rank not in r['owners']],
                       source_allocation_digest=digest([r['matrix_sha256'] for r in rows]),
                       source_initializers_bound=True, native_execution_qualified=False,
                       physical_qualified=False, composed_latency=None)
        (out/'binding.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
        return receipt

    def emit_programs(self, dispatches, out, *, program_address_bits):
        """Emit actual prog.hex entries consumed by native C8 entry14 dispatch.

        Each entry contains its encoded source fragment followed by the native
        END/wait31 already used by ShapeBuilder. This does not claim that END
        drains remote transport: the parent still owes context restoration,
        destination visibility, all-copy drain and ordered row gather.
        """
        import hdc_isa_v41 as ISA
        require(type(program_address_bits) is int and 1 <= program_address_bits <= 14,
                'actual native entry14/program capacity required')
        end = ISA.encode(full_shape=True, unit=ISA.UNIT_END, wait=31)
        width = ISA.FULL_INSTR_BITS//4
        require(ISA.FULL_INSTR_BITS == 2048, 'actual FULL_SHAPE program word ABI')
        programs, entries = {}, []
        for dispatch in dispatches:
            require(dispatch.get('source_dispatch_bound') is True, 'bound source dispatch required')
            for fragment in dispatch['fragments']:
                stage, rank = fragment['stage'], fragment['rank']
                require(self.lookup(stage, fragment['key'],
                        ME=fragment['instruction']['unit'] == ISA.UNIT_ME) == fragment['phase'],
                        'program/decoder phase mismatch')
                require(self.keys(stage, rank)[fragment['phase']] & (1 << 31),
                        'program targets a multicast consumer, not physical field')
                literal = ISA.encode(full_shape=True, **{k:tuple(v) if isinstance(v, list)
                                     and not k.startswith('_') else v
                                     for k,v in fragment['instruction'].items()})
                require(literal == fragment['word'], 'encoded dispatch word changed')
                words = programs.setdefault((stage, rank), [])
                entry = len(words)
                require(entry+2 <= 1 << program_address_bits, 'native program capacity exhausted')
                words.extend((literal, end))
                entries.append(dict(node=dispatch['node'], stage=stage, rank=rank, entry=entry,
                                    phase=fragment['phase'], key=fragment['key'],
                                    gather_local_rows=fragment['gather_local_rows'],
                                    ordered_K=fragment['ordered_K'],
                                    source_matrix_sha256=fragment['source_matrix_sha256'],
                                    source_predicate=dispatch['predicate'],
                                    output_multicast=fragment['result_multicast_required']))
        require(entries, 'no actual field fragment programs')
        out = Path(out); out.mkdir(parents=True, exist_ok=False)
        hashes = {}
        for (stage, rank), words in programs.items():
            directory = out/f's{stage}_r{rank}'; directory.mkdir()
            raw = ''.join(f'{word:0{width}x}\n' for word in words).encode()
            (directory/'prog.hex').write_bytes(raw)
            hashes[f's{stage}_r{rank}/prog.hex'] = hashlib.sha256(raw).hexdigest()
        result = dict(schema='opentallas.dsrom.S81.native-fragment-program.v1',
                      entries=entries, artifacts=hashes, instruction_bits=ISA.FULL_INSTR_BITS,
                      source_fragment_words=len(entries), native_END_wait31_words=len(entries),
                      source_input_and_output_lease_required=True,
                      context_restore_and_remote_drain_required=True,
                      whole_program_calendar_qualified=False, physical_qualified=False,
                      composed_latency=None)
        (out/'dispatch.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix-map', type=Path, required=True)
    parser.add_argument('--stage-map', type=Path, required=True)
    parser.add_argument('--matrix-sha256', required=True)
    parser.add_argument('--stage-map-sha256', required=True)
    parser.add_argument('--stage', type=int, required=True)
    parser.add_argument('--rank', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    join = StageProgramJoin.from_files(args.matrix_map, args.stage_map,
                                      matrix_sha256=args.matrix_sha256,
                                      stage_map_sha256=args.stage_map_sha256)
    print(json.dumps(join.emit_stage(args.stage, args.rank, args.out), sort_keys=True))


if __name__ == '__main__':
    main()
