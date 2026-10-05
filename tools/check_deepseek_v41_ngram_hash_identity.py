#!/usr/bin/env python3
"""Do the DEVICE's and the VENDOR's n-gram hash agree, column for column?

The Engram reads 24 rows per token out of a 384-million-row table, and the row ids
are the whole of its addressing -- a disagreement sends the two sides to different
rows at layers 1 and 14 with no error raised anywhere, which is the same shape of
failure as a dead Engram and just as silent.

Two implementations exist and both are in use.  The oracle hashes with the vendor's
``NgramHashState.forward``.  The device hashes with
``runtime.reference.engram.ngram_row_ids``, which ``runtime/sim/engines/dma.py``
imports for ``DMA.NGRAM_HASH``.  This compares them for every (engram layer, n-gram
order, hash head) column of one prompt.

Our function takes COMPRESSED ids -- the vendor maps them inside ``forward`` and the
device does it with its own ``ENGRAM_TOKEN_COMPRESS`` lookup -- so the token map is
applied here before the call, from the vendor's own table.

Pure CPU and seconds: no accelerator run, and nothing here says the engram's VALUES
agree, only that both sides address the same rows.
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/OpenTallas'); sys.path.insert(0, str(ROOT))
V41 = Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/'
           'snapshots/dba1be0a40aa45a94ad051997016db3960a90277')
OUT = Path(sys.argv[1])
WL = sys.argv[2] if len(sys.argv) > 2 else 'build/workloads/deepseek-v4.1-flash-prefix/TA-DS41-CHAT-1-P10.json'

from compiler.frontend.deepseek_v41_tokenizer import load_verified_deepseek_v41_tokenizer
from runtime.reference.deepseek_v4_oracle import OracleConfig
from runtime.reference.deepseek_v41_oracle import (
    StreamingDeepSeekV41, import_v41_vendor, _TokenizerForNgramHash)
from runtime.reference.engram import ngram_row_ids
import torch

model_mod, _k, _c, _e = import_v41_vendor(V41)
verified = load_verified_deepseek_v41_tokenizer(V41)
backend = getattr(verified, 'backend', None) or getattr(verified, '_backend', None)
tok = _TokenizerForNgramHash(backend)

# The vendor side, with its own real tables.
args = StreamingDeepSeekV41.__new__(StreamingDeepSeekV41)
cfg = json.loads((V41 / 'inference/config.json').read_text())
ModelArgs = model_mod.ModelArgs
fields = {f.name for f in __import__('dataclasses').fields(ModelArgs)}
vendor_args = ModelArgs(**{k: v for k, v in cfg.items() if k in fields})
layout = model_mod.EngramLayout.from_args(vendor_args)
with torch.device('cpu'):
    state = model_mod.NgramHashState(vendor_args, layout, tok)

wl = json.loads((ROOT / WL).read_text())
ids = [int(t) for t in (wl.get('token_ids') or wl['prompt_token_ids'])]
token_map_pre = np.asarray(state.token_map.cpu(), dtype=np.int64)
with torch.inference_mode():
    vendor = state(torch.tensor([ids], dtype=torch.long), 0)
vendor = np.asarray(vendor[0].cpu(), dtype=np.int64)   # [L, layers, cols]
compressed = [int(token_map_pre[t]) for t in ids]
print(f"vendor hash ids: shape {vendor.shape}  range [{vendor.min()}, {vendor.max()}]", flush=True)

primes = np.asarray(state.primes.cpu(), dtype=np.int64)          # [layers, orders, heads]
offsets = np.asarray(state.offsets.cpu(), dtype=np.int64)        # [layers, cols]
multipliers = np.asarray(state.multipliers.cpu(), dtype=np.int64)  # [layers, max_ngram]
token_map = np.asarray(state.token_map.cpu(), dtype=np.int64)
heads = int(vendor_args.engram_n_heads)
max_ngram = int(vendor_args.engram_max_ngram_size)
pad = int(token_map[int(vendor_args.engram_pad_id)])

rows = []
mismatch = 0
for layer_index, layer_id in enumerate(layout.layer_ids):
    for order in range(2, max_ngram + 1):
        for head in range(heads):
            #: our function takes COMPRESSED ids; the vendor maps them inside
            #: ``forward`` via ``token_map[input_ids]``, and the device does it
            #: with its own ENGRAM_TOKEN_COMPRESS lookup.
            got = ngram_row_ids(
                compressed, order=order, head=head,
                multipliers=[int(v) for v in multipliers[layer_index]],
                primes=[[int(v) for v in row] for row in primes[layer_index]],
                offsets=[int(v) for v in offsets[layer_index]],
                pad_id=pad,
                compressed_vocab_size=int(vendor_args.engram_compressed_vocab_size),
            )
            ours = [int(r['row_id']) if isinstance(r, dict) and 'row_id' in r else int(r)
                    for r in got] if got and not isinstance(got[0], dict) else \
                   [int(r.get('row_id', r.get('row', -1))) for r in got]
            column = (order - 2) * heads + head
            theirs = [int(v) for v in vendor[:, layer_index, column]]
            differ = [p for p, (a, b) in enumerate(zip(ours, theirs)) if a != b]
            if differ:
                mismatch += 1
            rows.append({'layer': int(layer_id), 'order': order, 'head': head,
                         'column': column, 'positions': len(theirs),
                         'positions_that_differ': len(differ),
                         'ours_head': ours[:4], 'vendor_head': theirs[:4]})
print(f"columns compared: {len(rows)}  columns with any disagreement: {mismatch}")
for row in rows[:6]:
    print(f"  L{row['layer']:02d} order {row['order']} head {row['head']:2d} "
          f"differ {row['positions_that_differ']}/{row['positions']}  "
          f"ours {row['ours_head']} vendor {row['vendor_head']}")
OUT.write_text(json.dumps({
    'schema': 'opentallas.probe.v41_ngram_hash_agreement.v1',
    'workload': WL, 'prompt_token_ids': ids,
    'columns': len(rows), 'columns_with_disagreement': mismatch,
    'agree': mismatch == 0, 'per_column': rows,
}, indent=1) + '\n')
print(f"\nagree: {mismatch == 0}")
