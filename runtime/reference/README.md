# Independent target-format reference

This directory is outside compiler lowering and RTL. Its implementations may
share versioned interface definitions, but they do not call compiler image,
placement, microcode, schedule, or service-engine algorithms to calculate an
expected result.

`formats.py` is the first DeepSeek V4 target-precision slice. It provides exact
rational scalar semantics for:

- E2M1 values and the official low-nibble-first packed layout;
- E8M0 scales, including the reserved `0xff` poison value;
- FP8 E4M3FN classification and round-to-nearest-ties-to-even conversion;
- BF16 classification and binary32-to-BF16 conversion;
- exact IEEE binary32 decode/rounding and ordered fused-product accumulation;
- packed MXFP4 block decoding; and
- NUM-3.3 BF16 activation-block microscaling;
- 32-value MXFP4×FP8 routed block dots; and
- 128-value FP8×FP8 dense block dots.

The tests exhaust every E2M1, E8M0, E4M3FN, and BF16 code, exercise rounding,
saturation, poison, scale-selection, and packing boundaries, and compare every
E4M3FN encoding with the public RTL decoder. A separate development audit also
matched every E4M3FN, BF16, and E8M0 decode against the installed PyTorch dtype
implementation with zero differences. Binary32 tests include deterministic
round trips over 20,000 random finite encodings and cases where ordered
per-product accumulation intentionally differs from one final exact reduction.

This closes neither `M1` nor numerical qualification. Multi-block matrix
lowering, scale-tile orientation, BF16 output boundaries, all vector/attention/
routing operators, real-checkpoint known answers, layer differentials,
end-to-end logits, and task quality remain open. The earlier exact-integer
evaluator remains fixture-only evidence.

`indexing.py` independently implements the three source-constructed integer
index tensors used by `WINDOW_INDEX`, `COMPRESSED_DENSE_INDEX`, and
`DSPARK_WINDOW_INDEX`. It preserves the pinned prefill/decode branch behavior,
circular-window order, compression-completion boundary, offsets, padding, and
DSpark history/draft address split. Inputs and signed-int32 output bounds fail
closed. These structural references do not implement learned index scoring,
top-k tie order, KV mutation, sparse attention, or any service-engine lowering.

`lookup.py` implements the two pinned pure-gather paths. `TOKEN_EMBED` selects
global embedding rows while carrying BF16 as exact 16-bit encodings; this is
equivalent to the source vocabulary-shard masking and all-reduce because one
and only one shard owns a valid token. `HASH_ROUTE` selects the checkpoint's
ordered expert-ID row for each flattened token ID and intentionally preserves
duplicates. It does not implement router scoring, selected-weight gathering, or
expert dispatch.

`structural.py` implements the bit-preserving `HC_EXPAND` copy and the integer
noise-block construction that precedes `DSPARK_NOISE_EMBED`. The HC result
copies every BF16 encoding without arithmetic. The DSpark helper fixes the
current token at column zero and fills later draft columns with the pinned noise
token; its shared embedding lookup and HC expansion are already covered by the
two pure primitives above. Main-hidden projection remains a separate matrix
operator.
