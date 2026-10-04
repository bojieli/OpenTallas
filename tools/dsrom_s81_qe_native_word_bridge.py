"""Native QE callback bridge: canonical selected I7/I8 -> released raw words.

Private inherited connection, same existing wire codec; no filesystem socket,
allocator, images, activations, output oracle or numerical execution.
"""
import argparse
import hashlib
import json
import re
import socket
from pathlib import Path
import dsrom_s82_payload_interface as API
from dsrom_s82_native_word_server import serve_connection


def require(ok, message):
    if not ok:
        raise ValueError(message)


class ReleasedQeOperationWords:
    def __init__(self, execution, source, node, rank, *, fragment=0):
        require(re.fullmatch(r'L\d+\.I[78]', node) is not None, 'only actual QAL/KVAL source ops')
        require(type(rank) is int and 0 <= rank < 4, 'TP4 rank')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint required')
        resolved = execution.source.resolve(node, rank)
        dispatch = execution.dispatch(node, rank)
        require(dispatch['source_dispatch_bound'], 'canonical selected dispatch required')
        matrices = resolved['fragments']
        require(type(fragment) is int and 0 <= fragment < len(matrices), 'selected fragment')
        require(len(matrices) == len(dispatch['fragments']), 'dispatch fragment coverage')
        instruction = execution.source.nodes[node]['instruction']
        rows = 320 if node.endswith('.I7') else 128
        alias = 'wq_a' if rows == 320 else 'wkv'
        require(instruction['unit'] == 3 and instruction['qe_mode'] == 0 and
                instruction.get('qe_fp4', 0) == 0 and instruction['qe_nb'] == 160 and
                instruction['qe_nout'] == rows and sum(f['matrix']['rows'] for f in matrices) == rows,
                'full native QE source dimensions')
        self.matrix = matrices[fragment]['matrix']
        self.selected = dispatch['fragments'][fragment]
        digest = hashlib.sha256(json.dumps(self.matrix, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(self.selected['source_matrix_sha256'] == digest and self.selected['rank'] == rank and
                self.selected['stage'] == self.matrix['stage'], 'selected matrix identity')
        require(self.matrix.get('original_alias', self.matrix['alias']) == alias and
                self.matrix['format'] == 'fp8' and self.matrix['conversion'] == 'native' and
                self.matrix['K'] == 5120 and self.matrix['compiled_NP'] == 2417,
                'native S81 source codec required')
        for name, dtype in ((self.matrix['tensor'], 'F8_E4M3'),
                            (self.matrix['source_scale_tensor'], 'F8_E8M0')):
            _, _, descriptor = source.descriptor(name)
            require(descriptor['dtype'] == dtype, 'released native code/scale dtype')
        self.source, self.rank = source, rank
        self.pairs = tuple(sorted({p[1] for p in self.matrix['plans']}))
        self.source_matrix_sha256 = digest

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage, rank, macro, physical_row)), 'integer address')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'request outside selected QE source')
        word = API.matrix_word(self.matrix, self.source, rank, macro, physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
        return word

    __call__ = read


def main():
    from dsrom_s81_execution_binding import CanonicalS81Execution
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fd', type=int, required=True)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--rank', type=int, required=True)
    p.add_argument('--fragment', type=int, default=0)
    a = p.parse_args()
    source = API.Checkpoint(a.checkpoint)
    try:
        provider = ReleasedQeOperationWords(CanonicalS81Execution(a.owner), source,
                                             a.node, a.rank, fragment=a.fragment)
        with socket.socket(fileno=a.fd) as connection:
            return 0 if serve_connection(connection, provider) else 1
    finally:
        source.close()

if __name__ == '__main__':
    raise SystemExit(main())
