# Actual Qwen native690 quarter ROM compilation

Compiler source step: `d5225192c`. Native consumers remain default-off. This is actual binary compilation, bit-exact reference execution of decoded binaries and N256/M64 layout/tree evidence. **It is not execution of the physical quarter RTL.** Stage harness owns the full N256/M64 real-FP quarter/finite-provider simulation using these same banks.

## Program ROM and arithmetic

`rom/Q0.hex` through `Q3.hex` contain the four independently compiled **690bit** native instruction banks; `rom/META.hex` is the actual **42bit** ROM metadata `{valid1,quarters4,window1,row0_20,rows16}`. They load directly into `ot_qwen_r25_su_program_rom` (`6411db9b1`). The dispatcher (`c17b6a4b0`) clips NIN[31:16] only for declared windows and skips windows beyond the current query valid length. All dependency edges conservatively wait for actual engine idle; no fake sequence completion or arithmetic result exists in the compiler.

| Stage | Native PC | Count | Quarter mapping |
|---|---:|---:|---|
| RMSNorm4096 | 0 | 4 | Each quarter computes the exact **full4096** square-sum and rsqrt, then publishes a disjoint1024word result; explicit BF16 output rounding |
| QK-norm128 | 4 | 6 | Two Q heads per quarter; one K head on quarters0 and1; separate Q/K gains; FP32 output |
| RoPE128 | 10 | 7 | Same head ownership; rotate_half in FP32, then only Q rounds to BF16; K remains FP32 for external FP8 append |
| SwiGLU3072 | 17 | 2 | Disjoint768elements per quarter, explicit BF16 output rounding |
| Softmax8×capacity8224 | 19 | 23 | Two heads per quarter; four2048row windows plus32row tail; causal NIN clipping at8192..8195; BF16 unnormalized exponent publication |

The model is emitted **before** compilation (`model_before_compile.json`). The conservative RMS baseline incurs **four full reductions / four rsqrts**, including **12,288 extra square elements** versus one full reduction. It preserves the exact released chunk8 order; it performs no cross-quarter partial-sum reassociation. Quarter output/selection indices are disjoint. No measured RTL cycles or speed credit are assigned.

Softmax initially fills max partials with the **finite minimum** `0xff7fffff`, and sum partials / exponent tail / published tail with +0 through real native operations reading the designated constant seat. The constant at VMword**262143** must contain protected/read-only +0. Skipped empty windows consequently cannot contribute stale data. The denominator uses explicit pairwise adds over eight leaves: four complete2048-row subtrees, the tail chunk8 and three +0 leaves. A sequential reduction over block sums would change rounding and is absent.

## Actual verification and immutable failure

The final EPYC4 admitted gate (`attempt3.log`, `gate.json`) passed **26 cases**. It reads the actual hex banks back, decodes their words, emulates the dispatcher mask/clipping, checks every instruction against the actual **N256/M64 LV6** layout, and compares complete stage tensors against the independent golden. For positive RED_SUM operations, the geometric streaming reducer model `C.unit_sum` at the selected S/vector width is also compared bitwise with canonical chunk8, including the shortened tails.

Cases cover full4096 RMS, ten128dim Q/K heads with separate gains, RoPE positions8191 through8194, all3072 SwiGLU elements, and all eight softmax heads at valid lengths8192,8193,8194,8195. Invalid score rows and initial partial/output tails contain NaNs; positive programs neither consume them nor publish nonfinite results, and all padded publication rows become +0. Mutants omit norm gains, reverse the RoPE sign, substitute sigmoid for SiLU, round exponent values before the sum, or remove both causal clipping and the empty-window skip. Every mutant is rejected.

`failed_attempt1.log` retains the initial **benchmark negative-control failure**: at8192, a purported unmasked-tail mutant still skipped the empty window, so it changed no behavior. The benchmark was fixed to remove both mechanisms for that mutant; production compiler words did not change. `attempt2.log` retains the first passing reference gate; `attempt3.log` adds the previously unresolved geometric reducer-order check. No failed verdict was overwritten.

`metadata.json` pins the compiler, gate, deterministic fixture helper, stage builders, ISA, campaign and both golden sources, along with Python/NumPy versions. The deterministic fixture API was checked for all four quarters, full RMS and all four softmax valid lengths (20 fixture cases). All work ran under remote `/srv/opentallas-scratch/admit.sh 1`; there was no new localhost compute. EPYC2 and EPYC3 unstarted admission queues were canceled only after EPYC4 admitted the replacement; their source and cancellation records remain on the respective hosts.

## Address/consumer requirements

VM addresses are **word24**, within the262144word logical allocation:

- RMS input229376, gain237568, private scalar220000+quarter, outputquarter×1024.
- QK input0, Q gain8192, K gain8320, normalized output16384; RoPE cos4096/signed sin4224, output0.
- SwiGLU gate0, up4096, output8192.
- Scores0, exponent65792, BF16 publication131584, head stride8224.
- Max partial210000+quarter×16; max210064+quarter×2; sum partial210080+quarter×16; denominator210144+quarter×2; tree temporary210160+quarter×8 and210192+quarter×4.
- Protected/read-only +0 seat262143.

p4 replays query slots **sequentially**, retaining one score/exponent/publication slot. The finite provider must supply the matching query's scores and position-specific RoPE constants when the dispatcher query changes. Declaring four complete score arrays resident would exceed VM18 and is unsupported. Scratch padding writes use capacity8224; causal valid lengths control score reads, not the ability to clear scratch padding. K/V FP8 append and PV normalization are external stage obligations.

Four N256 quarters expose up to4096operand-read bytes,1024index-read bytes,1024element-write bytes and128reduction-write bytes **per quarter per core edge**, before the finite provider's admission/serialization. These interface maxima do not establish achieved bandwidth. Four bank ROM payloads require2760bits per accepted instruction plus42metadata bits; the four4096×690 ROMs occupy11,304,960raw bits. Existing quarter/ROM/provider area, physical slots, fanout, routing and real service latency must remain priced by the parent design model; the compiler adds no physical sign-off claim.

This package provides exact actual native programs for the parent arithmetic wrapper and stage-harness service test. Protected owner73 versus hostTOKEN18 identity, bank/address translation without aliasing, write-ACK plus same-sector visibility before publication, production cycle composition, full decode integration, quality and physical qualification remain parent integration gates. No headline rate, SS/FF, DRC, IR or complete Qwen implementation claim is made.
