"""Borrowed released source words for any canonically selected QE/ME fragment.

No allocator/checkpoint constructor, host matmul, activation oracle or fallback
expert. The caller supplies the existing execution/checkpoint and actual EIDs.
Use the existing dsrom_s82_native_word_server.serve_connection wire protocol.
"""
import hashlib
import json
import dsrom_s82_payload_interface as API


def require(ok, message):
    if not ok:
        raise ValueError(message)


class ReleasedSelectedFieldWords:
    def __init__(self, execution, checkpoint, node, rank, *, fragment=0, expert_ids=None):
        require(type(rank) is int and 0 <= rank < 4, 'actual TP4 rank')
        require(checkpoint.root.resolve().name == API.SNAPSHOT, 'borrowed released checkpoint')
        resolved = execution.source.resolve(node, rank, expert_ids=expert_ids)
        dispatch = execution.dispatch(node, rank, expert_ids=expert_ids)
        require(resolved['source_identity_verified'] and dispatch['source_dispatch_bound'],
                'actual source matrix/dispatch required')
        require(len(resolved['fragments']) == len(dispatch['fragments']) and
                type(fragment) is int and 0 <= fragment < len(resolved['fragments']),
                'complete dispatch and exact selected fragment')
        matrix = resolved['fragments'][fragment]['matrix']
        selected = dispatch['fragments'][fragment]
        digest = hashlib.sha256(json.dumps(matrix, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(digest == selected['source_matrix_sha256'] and selected['rank'] == rank and
                selected['stage'] == matrix['stage'] and matrix['compiled_NP'] == 2417,
                'actual S81 source owner/allocation identity')
        instruction = selected['instruction']
        qe = instruction['unit'] == 3 and instruction.get('qe_mode') == 0
        me = instruction['unit'] == 1 and instruction.get('me_wsrc') == 0
        require(qe or me, 'native field weight operator only; quantizer/KV remain separate')
        require((matrix['format'] == 'bf16') == me and 0 < matrix['K'] <= 6144 and
                0 < matrix['rows'] < 65536, 'actual selected source codec/geometry')
        self.source, self.matrix, self.rank = checkpoint, matrix, rank
        self.pairs = frozenset(plan[1] for plan in matrix['plans'])
        self.selected = selected
        self.source_matrix_sha256 = digest
        # For an expert node source.resolve enforces six distinct ascending live
        # EIDs and exact selector slot. No exp0/local-stage fallback exists here.
        self.expert_ids = None if expert_ids is None else tuple(expert_ids)

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage, rank, macro, physical_row)),
                'integer actual native coordinates')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'request outside selected actual source fragment')
        word = API.matrix_word(self.matrix, self.source, rank, macro, physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native274 source word')
        return word

    __call__ = read
