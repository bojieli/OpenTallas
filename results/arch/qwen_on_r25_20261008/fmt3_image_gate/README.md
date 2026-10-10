# Qwen r25 fmt3 weight image gate

PASS covers a transformation of already canonical signed INT8 codes and opaque BF16 row-scale bits. It performs no quantization, norm folding or scale arithmetic. It is compatible with the opt-in registered line adapter at commit 6245cd690.

## Existing producer audit

Read source at 961688ad8:

- `tools/hdc_qwen_int8_image.py` emits TP2 canonical row-major `.npy` arrays for the previous ROM/W12 vehicle, with norm folding in its quantizer path. It does not emit r25 fmt3 issue-order lines. Its quantization/folding path cannot be adopted implicitly for this new vehicle.
- `tools/qwen_hbmacc_rt_token_w12.py` streams W12 engine words, with `WORD_BYTES = 6144 * 16`; it is not the r25 SM geometry.
- `tools/dshbm_wavepack.py` accepts BF16, FP8 and FP4 only. It reorders installed operation spans without generating a new fmt3 weight image.
- `tools/dshbm_matched_sm_seq.py::gen_op` and `tools/rtl_gpu_sm_exact.py::issue_order` define the existing BF16 lane mapping and group-slot issuer order. These are the transformation authority, alongside the actual production issuer RTL.

Therefore the r25 packing link was missing. `tools/qwen_r25_int8_image.py` now provides it without changing canonical input codes or scales.

## Literal mapping

One SM receives a contiguous equal partition of output rows. NC=8 represents independent activation columns, all receiving the same weights. It does not partition output rows. There are 32 SM replicas per die.

Production geometry is 64 BF16 lanes, eight serial ring steps, eight interleaved issuer slots. A real issue beat `(row, group, t)` carries canonical input column `(group*64 + lane)*8 + t` in lane `lane`. Group-slot scheduling iterates waves of eight `(row, group)` items, then `t`, then the real items in that wave. Padded slots consume no weight input.

Two consecutive real issue beats become one line: low 64 INT8 codes, high 64 INT8 codes, then eight zero sidecar bytes. The registered adapter widens each half exactly and sends the unchanged BF16 operands into the existing MAC tree. Row scales remain a separate little-endian BF16-bit array for SU multiplication after the FP32 sum.

## Evidence scope

All eight complete per-SM TP4 matrix shapes roundtrip: q, k, v, o, gate, up, down and head. Combined tested codes: 6,369,280 bytes. The corresponding full per-die shapes and 32-fold replica composition are recorded in `verdict.json`; the largest single tested matrix is the actual 1,187-row head partition. Additional cases cover partial groups, partial issuer waves, and both group-slot and row-slot scheduling.

The minimum RTL vehicle contains the production IL8 group-slot issuer and the real registered adapter. A 3-row, K1024 packed image is compared at each issued lane against independently generated canonical BF16 operands indexed by the issuer's actual row and x address. Source pauses exercise finite producer flow. A row-major-layout mutant must fail this comparison and does.

The emitter also tests an explicit 160-byte storage stride and preserves selected row-scale bits byte-for-byte. Response width is 136 bytes. It intentionally does not invent an installed HBM base, linked kernel PC, or source-service address mapping. Those must be bound by the actual program and service owners. Physical storage stride and HBM fetch overhead must be priced before asserting a one-byte-per-weight bandwidth result.

Reproduce with `python3 tools/test_qwen_r25_int8_image.py --out NEW_DIRECTORY`. This does not establish SS/FF timing, routing or full-token arithmetic closure.
