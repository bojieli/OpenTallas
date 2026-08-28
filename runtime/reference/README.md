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
- packed MXFP4 block decoding; and
- NUM-3.3 BF16 activation-block microscaling.

The tests exhaust every E2M1, E8M0, E4M3FN, and BF16 code, exercise rounding,
saturation, poison, scale-selection, and packing boundaries, and compare every
E4M3FN encoding with the public RTL decoder. A separate development audit also
matched every E4M3FN, BF16, and E8M0 decode against the installed PyTorch dtype
implementation with zero differences.

This closes neither `M1` nor numerical qualification. FP32 accumulation order,
all vector/attention/routing operators, real-checkpoint known answers, layer
differentials, end-to-end logits, and task quality remain open. The earlier
exact-integer evaluator remains fixture-only evidence.
