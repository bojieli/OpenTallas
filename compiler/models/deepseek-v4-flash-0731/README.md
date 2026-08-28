# Official DeepSeek V4 Flash compiler target

`checkpoint_source.json` binds the public
`deepseek-ai/DeepSeek-V4-Flash-0731` release at immutable Git revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. It records the SHA-256 and exact
byte size of all 48 safetensors shards and all 26 non-shard files, including the
checkpoint index. The values were reconciled against the pinned Hugging Face
Git/LFS objects and the already governed inventory in
`data/inventory/deepseek-v4-flash-0731.json`.

The compiler never executes release Python as remote code. Those files are
content-bound semantic references for an independently implemented front end.
Once a complete local snapshot exists, `lock-checkpoint` streams and validates
every byte, every header, all 72,317 tensor assignments, and the declared
166,878,536,440 payload bytes before emitting a lock.

This source contract establishes checkpoint identity and loadability. It does
not claim operator-complete inference, numeric equivalence, compiled scheduling,
RTL execution, or performance closure; those remain separate end-to-end gates.

`config.json` is a byte-identical committed copy of the official root config,
not a hand-transcribed approximation. The graph adapter checks its hash against
the source contract, expands the exact 43 main layers and three checkpoint-backed
DSpark stages, and derives all 72,317 tensor names, dtypes, shapes, scale pairs,
and semantic roles. Its independently header-derived tensor-structure digest is
`18285fe60ca3655be488bbabb88b59489b8ee03cff7fc4f4729424051ca83e0e`.

The root config's `num_nextn_predict_layers: 1` conflicts with the three `mtp.*`
namespaces, three trailing compression-ratio entries, and the official inference
config's `n_mtp_layers: 3`. The adapter preserves the root value and records the
three-stage resolution as an explicit source adaptation; it does not silently
equate these fields.

`inference_config.json` is likewise a byte-identical committed copy of the
official local-inference config. It is retained separately because it supplies
the explicit `n_mtp_layers: 3` used by `model.py`. The graph adapter locks the
hashes of `inference/config.json`, `model.py`, `kernel.py`, `convert.py`, and
`generate.py`; it imports none of them. Source anchors in the operator ledger
refer to named functions in these immutable files.

The official `encoding/encoding_dsv4.py` is also treated as a content-pinned
semantic source, never imported as checkpoint code. The independent compiler
adapter reproduces its four published valid fixtures byte-for-byte and replaces
assertions and permissive fallbacks with explicit validation errors. This is a
host protocol result, not evidence that model operators or speculative decoding
are executable.
