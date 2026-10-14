# TP8 native whole-layer integration contract

Status: source-derived integration candidate; no whole-layer RTL or token pass.

The accepted candidate image contains 27 instructions, TP8, GT3072, four Q heads and one KV head per die, 56,816 VM elements and a 2,097,152-element layer KV window. Its SHA256 is `120b42a583db68fb9faaa32d2076f1515d5c07e41787bf47533a1d230b4d1903`. Source profile is original committed `14065c8c7`; the full profile and original hex are retained byte-for-byte. Defaults GT6144 and historical programs remain untouched.

| PC | Actual operation | Required provider | Encoded dependency |
|---|---|---|---|
| 0 | hidden sum of squares | SU64 | own provider ready |
| 1 | QKV projection | ROM_matvec | own provider ready |
| 2 | hidden reciprocal RMS | SU64 | wait_su=1 |
| 3 | V scale and cache write | SU64_and_native_KV_formatter | barrier=1 |
| 4 | QK scale and sums of squares | SU64 | own provider ready |
| 5 | QK reciprocal RMS | SU64 | wait_su=1 |
| 6 | QK weighted normalization | SU64 | wait_su=1 |
| 7 | Q lower RoPE | SU64 | wait_su=1 |
| 8 | K lower RoPE and cache write | SU64_and_native_KV_formatter | own provider ready |
| 9 | Q upper RoPE | SU64 | own provider ready |
| 10 | K upper RoPE and cache write | SU64_and_native_KV_formatter | own provider ready |
| 11 | QK scores and row maxima | native_attention_QK | wait_su=1 |
| 12 | scaled exponentials and ordered Z reduction | SU64 | wait_me=1 |
| 13 | PV weighted sum | native_attention_PV | wait_su=1 |
| 14 | Z reciprocal | SU64 | own provider ready |
| 15 | attention normalization | SU64 | barrier=1 |
| 16 | O projection | ROM_matvec | chase=1, chase_n=8 |
| 17 | O all-reduce fence | TP8_collective | barrier=1 |
| 18 | attention residual and hidden sum of squares | SU64 | own provider ready |
| 19 | gate/up projection | ROM_matvec | chase=1, chase_n=64 |
| 20 | post-attention reciprocal RMS | SU64 | wait_su=1 |
| 21 | gate/up scale | SU64 | barrier=1 |
| 22 | SiLU times up | SU64 | wait_su=1 |
| 23 | down projection | ROM_matvec | chase=1, chase_n=24 |
| 24 | down all-reduce fence | TP8_collective | barrier=1 |
| 25 | MLP residual and hidden sum of squares | SU64 | own provider ready |
| 26 | layer completion fence | layer_completion | barrier=1 |

## Integration gaps that must refuse execution

- ROM NK tiles have no native KV arithmetic provider: their wrapper ties global KV input to zero. PCs11/13 must never issue into that path in native mode.
- Native attention currently proves component QK/exp/Z/RZ and PV/finalizer pieces. It does not expose the complete separate instruction effects required by PCs11/12/13/14/15. A fused final normalized result is not a substitute for separately executed S/M, exponentials/Z, ATT, RZ and ATTN effects. Either expose these exact provider stages, or produce a new explicitly lowered program and prove the changed instruction contract against actual immutable inputs. Do not skip accepted instruction bits and call them executed.
- The published native profile is shape-only. Its weights and coefficient/RoPE payloads, actual VM producer/consumer binding, native attention service, memory arbiter and complete stage wrapper are not validated together.
- KV formatter drained must mean receiver commit, including the partial V sector flush. QUEUE empty or emitted packet count cannot release QK/PV or layer completion.
- Collective source must bind the real TP8 posted/credited return semantics and actual 256-word T1 destination. Starting the next segment before all receiver VM writes commit is forbidden.
- The image does not contain embedding or vocabulary head; a layer pass cannot be labeled a token pass.

## Controller and clock integration

The new standalone `ot_qwen_tp8_me_provider_dispatch` is off by default. Native mode routes WSRC1 only when `native_contract_ready` asserts a complete separate QK/PV service contract. WSRC0 reaches the ROM provider. One operation is admitted at a time in this candidate; any resulting throughput cost is UNMEASURED. Ready, idle, progress and fault must describe the same accepted provider. Progress ownership is latched at acceptance and retained when NEXT changes WSRC. Both providers must drain before a native-mode next operation. Default mode preserves ROM ready/idle behavior.

Actual split seam: command380 WSRC bit55, GO bit0. Return95 READY bit0, IDLE bit1, PROGRESS bits93:78, FAULT bit94. The controller issuing head and its local tree shadow must receive the same selected return before their existing DUC stations. The shadow local clock enable must derive from that same provider state. Standalone router insertion alone does not finish this clock/control integration. No production split source is modified by this candidate.

## Required measurements

Source-pinned integration must observe every accepted instruction, actual operand read and destination commit, ordered K/V publication and collective return, all drain/fence states, and start-to-completion cycles. Mutants must corrupt actual data/tag/order or premature commit visibility and fail an observable arithmetic or ownership check. Complete one native layer against immutable operands/golden before composing whole-token timing. No price or ledger change is authorized by this component.

## Component verification

Admitted ot-run unit `oth-ubuntu-211669-1791954818` on ot-agidock128, 2GB/1thread: Icarus compiled actual router and test, positive printed DISPATCH_PASS; mutant selecting progress from NEXT rather than accepted provider failed the explicit in-flight progress assertion. Outer receipt exit0 means the expected mutant failure was checked. This proves the control seam component only.


## Explicit fused candidate

`fused_candidate.hex` is a NEW 23-instruction candidate image, SHA256 `e2bb5da6b0a56b0e632b85afc279dc36416d3a1104982a2529c8ea8329ae6649`. It replaces original PCs11–15 with one explicitly interpreted WSRC1 fused native request. The actual native service must execute QK/scale/exp/Z/PV/reciprocal/normalization in canonical S128/PV256 order. Request Q element base13696, output ATTN element base50672, 512 lossless FP32 outputs. No original 27-word whole-layer execution claim follows from this lowering. Every retained instruction remains byte-identical except O projection, whose obsolete SU chase becomes a full barrier on actual native destination commits. Collective segment starts become0/14/21; kind/count/destination fields are preserved.

The source-derived alias check enumerates active retained SU operands, ROM matrix X and output accesses, reduction writes and collective accesses. It finds no remaining program consumer or writer of removed S/M/Z/RZ/ATT intermediates. It rejects actual later rawATT and denominator-Z access mutations. This does not prove the absence of external host/debug readers: those must be prohibited or bound explicitly before capability admission.

The native service contract transports32 Q words of512bits from QR (head=beat//8, dim0=16*(beat%8)), retaining FP32 until BF16 RNE inside the consumer. Position>8191 is rejected. Epoch16/layer6 identifies32 addressed result beats, each16 FP32 values. The registered `ot_qwen_tp8_attn_vm_commit` bridge holds each word through VM write readiness and matching receiver commit before taking the next word. It reports done only after all32 commits. This conservative one-word-at-a-time bridge has no qualified throughput or physical view. Integrating VM must supply real commit acknowledgments; never synthesize them from kernel output handshakes.

Admitted ot-run unit `oth-ubuntu-227215-1791955264` on ot-agidock128 (2GB/1thread) passed32 exact registered payload/address/tag observations under delayed VM readiness/commits. Wrong epoch on final beat was refused after31 actual commits and kept completion closed. An intentional mutant counting VM request issue as commit failed the observed issue-versus-commit assertion. Three lightweight lowering tests passed, including retained-byte/segment preservation and two forbidden-intermediate alias failures. These are component and program-contract results; the actual native kernel, Q VM reader, K/V landing, result VM receiver and whole-layer execution remain to be composed.


The dispatcher exports `descriptor_native` (NEXT wake identity) and `accepted_provider_native` (last accepted operation status ownership). The native/ROM request pulses identify exact acceptance. Tree-local predictor and issuing head must consume both metadata signals aligned to the corresponding existing command/return station epochs; the router does not itself implement the split's DCU/DUC transport. Metadata assertions passed admitted unit `oth-ubuntu-236401-1791955386`.
