"""Preworker READY transport for existing L20 raw source providers; no math."""
import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path
from dsrom_s82_native_word_server import serve_connection
from dsrom_s81_qe_native_word_bridge import ReleasedQeOperationWords, require
from dsrom_L20_native_me_matrix_provider import ReleasedMeMatrixWords
from dsrom_s81_execution_binding import CanonicalS81Execution
import dsrom_s82_payload_interface as API
from dsrom_checkpoint import Checkpoint


class ReleasedL20HeWords:
    def __init__(self, execution, source, rank):
        require(0 <= rank < 4 and source.root.resolve().name == API.SNAPSHOT,
                'actual TP4 released HE source')
        self.source, self.rank = source, rank
        self.tensors = ('layers.20.hc_attn_fn', 'layers.20.hc_ffn_fn')
        pins = []
        for node, tensor in zip(('L20.I1', 'L20.I78'), self.tensors):
            require(execution.source.nodes[node]['instruction']['unit'] == 5,
                    'actual L20 HE operation required')
            _, _, desc = source.descriptor(tensor)
            require(desc['dtype'] == 'F32' and desc['shape'] == [24, 20480],
                    'released HE F32[24,20480] required')
            execution.target_native_operation(node, position=1048575, native_units={5})
            pins.append(hashlib.sha256(json.dumps(execution.source.nodes[node],
                sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.digest = hashlib.sha256(''.join(pins).encode()).hexdigest()

    def read(self, ffn, rank, line_lo, line_hi):
        require(ffn in (0, 1) and rank == self.rank, 'unowned HE source')
        line = line_lo | (line_hi << 32)
        require(0 <= line < 61440, 'HHW8 line bounds')
        # Existing HHW8 order: row*320*8 + run*8 + term, lane=chunk.
        # Exact pack_he_fp32 inverse: col=64*run+8*lane+term.
        word, term = divmod(line, 8)
        row, run = divmod(word, 320)
        raw = b''.join(self.source.raw(self.tensors[ffn],
                      (row*20480+64*run+8*lane+term)*4, 4)
                      for lane in range(8))
        return int.from_bytes(raw, 'little')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fd', type=int, required=True)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--kind', choices=('field', 'me', 'he'), required=True)
    p.add_argument('--node', default='')
    p.add_argument('--source-sha', default='')
    p.add_argument('--rank', type=int, required=True)
    p.add_argument('--fragment', type=int, default=0)
    p.add_argument('--native-pp-word-order', action='store_true')
    a = p.parse_args()
    require(not a.native_pp_word_order or a.kind == 'field', 'PP order is a field-only binding')
    source = Checkpoint(a.checkpoint)
    try:
        execution = CanonicalS81Execution(a.owner)
        if a.kind == 'he':
            require(not a.node and not a.source_sha and a.fragment == 0,
                    'HE fixed actual I1/I78 source enrollment')
            provider = ReleasedL20HeWords(execution, source, a.rank)
            digest, read = provider.digest, provider.read
        else:
            require(a.node.startswith('L20.'), 'actual L20 node required')
            digest = execution.source.bindings[a.node]['source_node_semantic_sha256']
            require(a.source_sha == digest, 'source node SHA mismatch')
            require(execution.source.bindings[a.node]['selector_slot'] is None,
                    'dynamic actor must use delayed capture transport')
            raw = ReleasedQeOperationWords(execution, source, a.node, a.rank,
                                          fragment=a.fragment, native_pp=a.native_pp_word_order)
            if a.kind == 'field':
                require(execution.source.nodes[a.node]['instruction']['unit'] == 3,
                        'static field requires mode0 QE')
                read = raw.read
            else:
                provider = ReleasedMeMatrixWords(execution, source, a.node, a.rank,
                                                 fragment=a.fragment, raw_provider=raw)
                read = provider.raw_decoder_word
        with socket.socket(fileno=a.fd) as connection:
            # Only after opening/indexing the checkpoint and validating source.
            connection.sendall(struct.pack('<I', 0) + bytes.fromhex(digest) + struct.pack('<I', 1))
            return 0 if serve_connection(connection, read) else 1
    finally:
        source.close()


if __name__ == '__main__':
    raise SystemExit(main())
