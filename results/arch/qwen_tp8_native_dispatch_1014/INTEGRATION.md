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
