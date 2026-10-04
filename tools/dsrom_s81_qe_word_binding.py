"""Released I8 ROM callback; reuse canonical dispatch and native codec unchanged.

No activation math, allocation, socket, clock or publication authority. The
existing native participant owns input leases and accepted output visibility.
"""
import hashlib
import json
import dsrom_s82_payload_interface as API


def require(ok, message):
    if not ok:
        raise ValueError(message)


class ReleasedQeWordBinding:
    def __init__(self, execution, source, rank, dispatch):
        require(type(rank) is int and 0 <= rank < 4, 'rank outside TP4')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint required')
        resolved = execution.source.resolve('L0.I8', rank)
        fragments = resolved['fragments']
        require(dispatch['node'] == 'L0.I8' and dispatch['source_dispatch_bound'] and
                len(fragments) == len(dispatch['fragments']) == 1, 'actual I8 dispatch required')
        matrix = fragments[0]['matrix']
        selected = dispatch['fragments'][0]
        digest = hashlib.sha256(json.dumps(matrix, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(selected['source_matrix_sha256'] == digest and
                selected['stage'] == matrix['stage'] == 0 and selected['rank'] == rank and
                selected['phase'] == 1 and selected['key'] == 65536 and
                selected['cfg_logical_range'] == [25, 50], 'I8 matrix/phase/CFG mismatch')
        instruction = selected['instruction']
        expected = dict(unit=3, qe_mode=0, qe_fp4=0, qe_nb=160, qe_nout=128,
                        qe_xbase=46464, qe_obase=420096, qe_wbase=65536, qe_ind=0)
        require(all(instruction.get(k) == v for k, v in expected.items()), 'I8 literal mismatch')
        require((matrix['alias'], matrix['format'], matrix['conversion'], matrix['K'],
                 matrix['rows'], matrix['compiled_NP']) == ('wkv', 'fp8', 'native', 5120, 128, 2417),
                'native S81 KVAL source required')
        require(matrix['tensor'] == 'layers.0.attn.wkv.weight' and
                matrix['source_scale_tensor'] == 'layers.0.attn.wkv.scale', 'wrong released tensor')
        for tensor, dtype in ((matrix['tensor'], 'F8_E4M3'),
                              (matrix['source_scale_tensor'], 'F8_E8M0')):
            _, _, descriptor = source.descriptor(tensor)
            require(descriptor['dtype'] == dtype, 'non-native released dtype')
        self.matrix, self.source, self.rank = matrix, source, rank
        self.pairs = tuple(sorted({plan[1] for plan in matrix['plans']}))
        require(len(self.pairs) == 64 and 0 not in self.pairs, 'I8 active pair census')
        self.source_matrix_sha256 = digest

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage, rank, macro, physical_row)), 'integer address required')
        require(stage == 0 and rank == self.rank and macro // 4 in self.pairs,
                'unowned I8 stage/rank/pair')
        # Original inverse decoder rejects gaps, padding, wrong bank/parity and
        # wrong physical ownership. Native codec reads released codes/scales.
        word = API.matrix_word(self.matrix, self.source, rank, macro, physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
        return word

    __call__ = read
