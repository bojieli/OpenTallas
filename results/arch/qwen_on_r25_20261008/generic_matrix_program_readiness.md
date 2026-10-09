# Qwen matrix and row-scale program readiness — 2026-10-09

The latest owner instruction selects one generic HBM accelerator for Qwen3-8B and DeepSeek-V4.1 Flash. Qwen-specific native SM dispatcher work is stopped. This stream added no such dispatcher RTL or build. Existing fmt3 conversion/packing evidence and three advancing physical jobs remain useful evidence and are preserved. Generic interface v0.9 is not yet published. Its proposed `review_queue/hbm-iface.md` was absent at the instructed shared path when checked; no new interface schema, opcode or entry address is inferred here.

This is a source and arithmetic inventory for program lowering, not an installed program or execution verdict.

| Graph family | Native matrix components | Rows per TP4 die | K | Invocations per AR token |
|---|---|---|---|---|
| qkv | q, k, v | 1024, 256, 256 | 4096 | 36 family launches; 108 component operations |
| o | o | 4096 | 1024 | 36 |
| gu | gate, up | 3072, 3072 | 4096 | 36 family launches; 72 component operations |
| down | down | 4096 | 3072 | 36 |
| head | head | 37984 | 4096 | 1 |

There are 253 matrix component operations per AR token. The existing physical SM study partitions each component into 32 equal contiguous row ranges; its NC8 columns are independent activation vectors, not output-row partitions. These are existing-study geometry facts, not an assignment of the unpublished generic accelerator's resources.

The exact arithmetic source is `tools/hdc_golden.py` (`to_bf16`, `mul`, `add`) plus `tools/hdc_golden_v41.py:csum`. Signed INT8 codes are converted exactly to BF16 values; activations are BF16-rounded at the declared graph boundary. FP32 products are summed in contiguous chunks of eight, sequentially from +0 within each chunk, then in the adjacent-pair tree padded with +0 to a power of two. The row scale remains a separate FP32 multiply by the released BF16 scale after the raw sum. Use these golden functions and their zero/rounding policy directly, rather than a BLAS reduction or fused product/scale.

Row-scale qkv consumes 1536 raw values, preserving q[0:1024], k[1024:1280] and v[1280:1536]. Row-scale gu consumes 6144 values split into gate/up halves. Row-scale o and down each consume 4096 values **after** the canonical TP4 collective `add(add(rank0,rank1),add(rank2,rank3))`. Parent owns head-scale lowering for 37984 raw logits. Scale artifact bits are opaque uint16 BF16, preserved byte-for-byte. No norm folding, applying a norm scalar after a matvec, or multiplication before collective reduction is authorized.

The existing image producer is `tools/qwen_r25_int8_image.py`, with exact roundtrip/operand gates in `tools/test_qwen_r25_int8_image.py`. Its existing front ABI packs two consecutive actual IL8 group-slot issuer beats into each line, low half first: `k=(g*64+lane)*8+t`, 128 signed code bytes plus eight zero sidecar bytes. Transport stride136 or160 is explicit. Packer output intentionally leaves installed storage base and linked entry PC unresolved. Reuse canonical codes/scales; a future generic lowering must produce the format required by the published interface and must not treat this historical front layout as the new interface.

Existing native mechanism: `rtl/hbm_accel/sm/ot_hbm_accel_smh.sv` accepts start/op, descriptor and x-write ports and emits raw `rv/rrow/rdata[255:0]`, busy/arrive/released/fault. It has no instruction PC. The separate `ot_hbm_accel_simt_sm` TC instruction path instantiates `ot_gpu_sm`, so assigning an SM instruction PC does not bind the physical smh producer. The previous source investigation found this distinction before implementing any new hardware. Existing CP SU addresses are CP dispatch names, not SM instruction addresses.

Existing evidence: all256 signed conversions and minimum protocol/issuer gates PASS; full eight component shapes roundtrip PASS; actual IL8 full-shape issue timing PASS for both adapter pipeline settings; missing-module-free full source elaboration PASS. These do not qualify native SM matrix numerical completion, result publication, collective input, row-scale execution, or generic program installation. Those remain OPEN until actual generic interface lowering executes and compares every produced result, with wrong-layout/order/scale negative controls and real completion/drain gating.

Before implementation, bind published v0.9 program format, real matrix dtype/order, canonical image addressing and allocator translation, activation/result address conventions, finite producer/consumer flow, completion semantics, and the row-scale consumer interface. Price memory traffic, arithmetic issue work, communication boundaries and serial-chain latency in the unified model before a new build. No Qwen-specific hardware or new structural physical route is launched by this inventory.
