"""Extract an earlier prior-KV prefix from a retained sequential-decode history.

No inference or current-token expected values are produced. Source and target
must share the actual prompt and embedding; retained target histories cross-check
all available layers. Full-token numerical coverage is recorded separately.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(source, reference, position, output):
    source, reference, output = map(Path, (source, reference, output))
    full = json.loads((source / 'oracle.json').read_text())
    ref = json.loads((reference / 'oracle.json').read_text())
    assert full['layers'] == 36 and full['tp'] == ref['tp'] == 4
    assert full['groups'] == ref['groups'] == 6144
    assert full['kv_format'] == ref['kv_format'] == 'fp8'
    assert full['tokens_sha256'] == ref['tokens_sha256']
    assert full['embedding_npz_sha256'] == ref['embedding_npz_sha256']
    assert full['tokens_used'][:position + 1] == ref['tokens_used'][:position + 1]
    later = min(p for p in full['positions'] if p > position)
    frame = full['per_position'][str(later)]
    target = ref['per_position'][str(position)]
    assert target['token'] == full['tokens_used'][position]
    output.mkdir(parents=True, exist_ok=False)
    history = output / 'history'
    history.mkdir()
    records = {}
    for layer in range(36):
        for rank in range(4):
            key = f'L{layer}_die{rank}'
            src = source / f'P{later}/kv_pre/{key}.npy'
            assert sha(src) == frame['kv_pre_sha256'][key], key
            words = np.load(src, allow_pickle=False)
            assert words.dtype.str == '<u4' and words.shape == (4194304,)
            # K: [head, 16-position group, dimension, position lane].
            k = words[:2097152].reshape(2, 512, 128, 16)
            group, lane = divmod(position, 16)
            k[:, group + 1:, :, :] = 0
            k[:, group, :, lane:] = 0
            # V: [head, position, dimension]. Current position is excluded.
            words[2097152:].reshape(2, 8192, 128)[:, position:, :] = 0
            checked = None
            if layer < ref['layers']:
                known = reference / f'P{position}/kv_pre/{key}.npy'
                assert sha(known) == target['kv_pre_sha256'][key], key
                assert np.array_equal(words, np.load(known, allow_pickle=False)), key
                checked = dict(path=str(known), sha256=sha(known))
            dst = history / (key + '.bin')
            words.tofile(dst)
            records[key] = dict(source=str(src), source_sha256=frame['kv_pre_sha256'][key],
                                raw=str(dst), raw_sha256=sha(dst), reference=checked)
    preload = reference / f'P{position}/x_preload.hex'
    assert sha(preload) == target['x_preload_sha256']
    record = dict(position=position, token=target['token'], layers=36,
                  source_oracle=str(source / 'oracle.json'), source_sha256=sha(source / 'oracle.json'),
                  source_position=later, reference_oracle=str(reference / 'oracle.json'),
                  reference_sha256=sha(reference / 'oracle.json'),
                  reference_layers=ref['layers'], history=records,
                  preload=dict(path=str(preload), sha256=sha(preload)),
                  scope='prior KV prefix only; no current-layer or HEAD reference generated')
    (output / 'inputs.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'prepared position={position} token={target["token"]} histories={len(records)} '
          f'reference_layers={ref["layers"]}', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--position', type=int, required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    prepare(args.source, args.reference, args.position, args.output)
