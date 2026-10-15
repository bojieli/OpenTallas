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


def export(bundle, checkpoint, output):
    receipt = json.loads((bundle/'receipt.json').read_text())
    for name in ['matrix.json', 'weight_coordinates.json']:
        if hashlib.sha256((bundle/name).read_bytes()).hexdigest() != receipt['files'][name]:
            raise ValueError('programme source hash mismatch: '+name)
    matrix = json.loads((bundle/'matrix.json').read_text())
    if checkpoint.resolve().name != API.SNAPSHOT:
        raise ValueError('released checkpoint revision required')
    source = API.Checkpoint(checkpoint)
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
            source_descriptors=descriptors, stage=receipt['stage'], rank=receipt['rank'],
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
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.bundle, args.checkpoint, args.output), indent=2))
