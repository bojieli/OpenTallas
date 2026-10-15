#!/usr/bin/env python3
"""Export exact selected BF pair words using the existing checkpoint codec.

No unselected ROM words are filled or claimed. Rows are sparse native physical
coordinates; a bench must load only the addressed words on the actual masters.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s82_payload_interface as API


class Fragment:
    """Exact raw-source bytes; reject every coordinate outside collected range."""
    def __init__(self, root):
        self.root = root
        self.receipt = json.loads((root/'fragment.json').read_text())
        self.read_bytes = 0
        self.tables = {}
        for tensor, row in self.receipt['tensors'].items():
            raw = (root/row['file']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('raw source fragment hash mismatch')
            self.tables[tensor] = (row, raw)
    def descriptor(self, tensor):
        return None, None, self.tables[tensor][0]['descriptor']
    def element(self, tensor, row, col=0):
        meta, raw = self.tables[tensor]
        columns = meta['descriptor']['shape'][-1]
        offset = row*columns+col-meta['first_element']
        if not 0 <= offset < len(raw):
            raise ValueError('source coordinate outside exact fragment')
        self.read_bytes += 1
        return raw[offset]
    def close(self):
        pass


def collect_fragment(checkpoint, output):
    if checkpoint.resolve().name != API.SNAPSHOT:
        raise ValueError('released checkpoint revision required')
    source = API.Checkpoint(checkpoint)
    output.mkdir(parents=True, exist_ok=False)
    tensors = {}
    try:
        for tensor, size in [('layers.0.attn.wo_a.weight', 8192),
                             ('layers.0.attn.wo_a.scale', 128)]:
            descriptor = source.descriptor(tensor)[2]
            expected = ([8192,4096], 'F8_E4M3') if tensor.endswith('weight') else ([256,128], 'F8_E8M0')
            if (descriptor['shape'], descriptor['dtype']) != expected:
                raise ValueError('actual source descriptor changed')
            raw = source.raw(tensor, 0, size)
            name = tensor.rsplit('.',1)[1]+'.bin'
            (output/name).write_bytes(raw)
            tensors[tensor] = dict(file=name, sha256=hashlib.sha256(raw).hexdigest(),
                first_element=0, descriptor=descriptor,
                source_shard=source.index[tensor])
        proof = dict(snapshot=API.SNAPSHOT, checkpoint=str(checkpoint.resolve()),
            index_sha256=hashlib.sha256((checkpoint/'model.safetensors.index.json').read_bytes()).hexdigest(),
            tensors=tensors, bytes_collected=source.read_bytes)
        (output/'fragment.json').write_text(json.dumps(proof,indent=2)+'\n')
        return proof
    finally:
        source.close()


def export(bundle, checkpoint, output, *, fragment=None):
    receipt = json.loads((bundle/'receipt.json').read_text())
    for name in ['matrix.json', 'weight_coordinates.json']:
        if hashlib.sha256((bundle/name).read_bytes()).hexdigest() != receipt['files'][name]:
            raise ValueError('programme source hash mismatch: '+name)
    matrix = json.loads((bundle/'matrix.json').read_text())
    if checkpoint.resolve().name != API.SNAPSHOT:
        raise ValueError('released checkpoint revision required')
    source = Fragment(fragment) if fragment is not None else API.Checkpoint(checkpoint)
    coordinates = json.loads((bundle/'weight_coordinates.json').read_text())
    output.mkdir(parents=True, exist_ok=False)
    try:
        # Verify actual tensor descriptors before any payload export.
        descriptors = {name:source.descriptor(name)[2] for name in
            (matrix['tensor'], matrix['source_scale_tensor'])}
        words = []
        for coordinate in coordinates:
            macro, row = coordinate['macro'], coordinate['physical_row']
            word = API.matrix_word(matrix, source, receipt['rank'], macro, row)
            if word >> 256:
                raise ValueError('BF payload unexpectedly uses padding bits')
            words.append(dict(macro=macro, physical_row=row, word=f'{word:069x}'))
        if len({(w['macro'], w['physical_row']) for w in words}) != len(words):
            raise ValueError('duplicate source weight word')
        raw = ''.join(f"{w['macro']} {w['physical_row']} {w['word']}\n" for w in words).encode()
        (output/'native_words.txt').write_bytes(raw)
        proof = dict(schema='s81.canonical_bf_source_weights.v1',
            snapshot=API.SNAPSHOT, checkpoint=str(checkpoint.resolve()),
            programme_receipt_sha256=hashlib.sha256((bundle/'receipt.json').read_bytes()).hexdigest(),
            source_codec_sha256=hashlib.sha256(Path(API.__file__).read_bytes()).hexdigest(),
            source_descriptors=descriptors, raw_fragment=None if fragment is None else source.receipt, stage=receipt['stage'], rank=receipt['rank'],
            phase=receipt['phase'], pair=receipt['pair'], native_word_count=len(words),
            source_bytes_read=source.read_bytes, payload_sha256=hashlib.sha256(raw).hexdigest(),
            padding_bits_zero=True, absent_words='unwritten/unqualified',
            numerical_gate=False, physical_macro_mutation_gate=False)
        (output/'receipt.json').write_text(json.dumps(proof, indent=2)+'\n')
        return proof
    finally:
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--fragment', type=Path)
    parser.add_argument('--collect-fragment', action='store_true')
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.collect_fragment:
        result = collect_fragment(args.checkpoint, args.output)
    else:
        if args.bundle is None:
            parser.error('--bundle required for export')
        result = export(args.bundle, args.checkpoint, args.output, fragment=args.fragment)
    print(json.dumps(result, indent=2))
