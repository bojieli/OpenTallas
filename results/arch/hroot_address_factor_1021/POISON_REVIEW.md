# Exact source poison review before any gate

Candidate source commit aa6cd99fb, current receipt tip168f13428, production file rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv SHA256 b49162d88eb2f47e1dfee5c9036ac08a20ffe9b0796b70a89bb3cb2f0d5d1d63. ROOT review of this actual source is required before gates. This document grants no qualification.

Each replaced original32-bit arithmetic boundary uses the following actual mechanism:

```verilog
poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
af_add32 = p[0] ^ {g[5][30:0],1'b0} ^ {32{poison}};
// af_mul3 / af_mul5 compute their original-operand poison separately:
af_mul3 = af_add32(s,c) ^ {32{poison}};
af_mul5 = af_add32(s2,c2) ^ {32{poison}};
```

For fully known binary operands each reduction has a known result, its self-XOR is0, and the poison contributes0. For an operand containing any X/Z the reduction-XOR isX, self-XOR remainsX, OR leavesX, and every result bit XOR X isX. Original Verilog32-bit +,-,* also return allX when an arithmetic operand contains X/Z. Thus this restores their pessimism at the operator boundary; it does not assume undefined state away. In particular zero times an unknown operand remains allX, rather than becoming a convenient knownzero. The decrement remains one32-bit addition with constantFFFFFFFF, followed by the unchanged source bitwise row mask. That subsequent bitwise mask may determine knownzero bits exactly as before. No mask is applied to observed outputs and no valid-only address equivalence is substituted for raw addresses.

The partial-product expressions a & {32{b[i]}} are the binary multiplication terms. They are not don't-care constraints. Their possible local X optimism is overridden by poison from the ORIGINAL product operands, at the same product boundary as the source. Original comparisons and ternaries remain intact, including conditional bitwise merge under X. Original width32, wrap, unsignedness and final AW!=32 fallback expressions are retained. Helpers add no state, clocks, reset, initialization, latency or source-cell attributes.

This is RTL simulator semantics. Binary synthesis is expected to constant-fold each self-XOR and poison to0. No claim of an actual measured production fold is made until the fresh mapped netlist/log supplies the observation; mapping r2 is pending. The emitted native gate model may propagate partially known state differently from original RTL arithmetic. Matching RTL X pessimism and proving binary arithmetic cannot establish mapped-cell cold/reset convergence, metastability behavior, or whole-state equivalence. No poison logic supplies physical initialization.

Evidence so far: source-extracted universal binary helper proofs with arbitrary binary operands for add/mul3/mul5 PASS; explicit wrong-carry mutant rejected. Corrected4-state fixture restores known operands before each X/Z bit injection and passed6168 comparisons including carry/wrap, zero, one, alternating and1024 random known pairs. These vectors are bounded examples, not exhaustive four-state/whole-state or initialization proof. The operator-level reasoning above is subject to ROOT source review. First full actual-production address projection timed out at240s; it is inconclusive. Adaptive shared-node proof and new source-specific native copy/cold obligations are separately pending. Old source receipts cannot fill these gaps.

Measured production mapping update:18 named procedural `.poison` aliases are assigned1'hx in the final mapped Verilog, not literal0. Exact escaped-token connectivity checks show each appears only in its wire declaration and assignment LHS, with zero RHS/cell-pin uses. They are dead temporary aliases; this observation does not depend on assuming a signal with an X driver is harmless. Do not report named aliases as measured constant0. The binary self-XOR identity is the source-level reason the active arithmetic needs no poison hardware. Exact source/mapped SHA, every alias/use and full warning logs are sealed in sealed_packet/native_candidate/.

Same exact frozen-original synthesis baseline has576 warnings; candidate608. Pairing after generated-ID/source-line normalization finds no missing baseline warning and exactly32 extra af_add32 g/p array lowering warnings. Both have544 identical w2-bit driver warning headers,9 identical loop-temp latch headers and2 constant-driver conflict headers. The warned .w2, ob, oh and g_qp.l tokens have zero occurrences in BOTH emitted mapped netlists; full logs preserve the original diagnostics. This is a narrow connectivity/source comparison, not a general permission to ignore synthesis warnings or a mapped-cell cold proof.

The source-bound compositional binary projection now passes:16 helper-lemma applications, each pinned to the universally proved arithmetic fixtures, followed by Yosys equivalence of all320 extracted raw address bits versus frozen actual production expressions over arbitrary state cutpoints. Both earlier240s direct SAT inconclusives remain. The lowered composition vehicle is proof-only and never shipping RTL. Fresh canonical native census passes91,045 roots max32; conditional primitive/pin certificate and454-cohort D-congruence are separately scoped. Whole selected-wrapper binding and source-specific bounded cold evidence remain pending.
