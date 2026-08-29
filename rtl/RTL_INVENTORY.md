# Public-reference RTL inventory

This inventory is the implementation allocation for the frozen specification.
It is intentionally separate from target-node macro collateral.  A module may
be replaced by a qualified macro only if its visible latency, ordering,
integrity, reset, poison, and test contracts remain equivalent.

| Block | RTL | Primary contract | Evidence entry |
|---|---|---|---|
| CRC/integrity | `lib/ot_crc_pkg.sv`, `lib/ot_crc16_ccitt.sv`, `lib/ot_crc32c.sv` | CRC-16/CCITT-FALSE and CRC32C traversal | DV-RAS-001 |
| Elastic/CDC/RDC | `lib/ot_skid_buffer.sv`, `lib/ot_async_fifo.sv`, `lib/ot_cdc_mailbox.sv`, `lib/ot_sync_level.sv`, `lib/ot_sync_bits.sv`, `lib/ot_reset_sync.sv` | stable ready/valid, Gray pointers, closed-loop mailbox, qualified levels, coupled flush, synchronous reset release, online rendezvous | DV-RESET-001/DV-STATIC-001 |
| Route context | `ot_route_mask.sv` | ID/range/CRC checks and duplicate suppression | DV-TILE-001 |
| Immutable ROM | `ot_rom_wrapper.sv`, `via_mask_rom.sv` | no write path, fixed latency, repair/fault status | DV-TILE-002 |
| Numeric/DV | `ot_format_decode.sv`, `ot_numeric_dot.sv`, `ot_reduction_tree.sv` | classification, signed exact order, deterministic reduction | DV-NUM-001/002 |
| Tile | `ot_tile.sv`, `opentallas_tile.sv` | route-before-activation and result alignment | DV-TILE-004 |
| Static schedule | `ot_schedule_controller.sv`, `static_timeslot_switch.sv` | fully rewritten shadow bank, typed schedule-ID/epoch atomic commit, and slot transport | DV-NOC-001 |
| Credits | `ot_credit_manager.sv` | atomic reservation and conservation | DV-NOC-004 |
| Sessions/commands | `ot_session_table.sv`, `ot_cmd_frontend.sv` | generation/transaction ownership, position/image/context/epoch/schedule validation, CRC/version/field legality | DV-CMD-001/002, DV-SESSION-001 |
| Production tensor commands | `ot_ta_command_decoder.sv` | Registered admission of the 64-byte ABI 2.0–2.5 record, four-byte-per-cycle IEEE CRC32 with fixed 15-cycle admission latency, opcode/engine/minor/field/index checks, and deterministic error priority | QW-RTL-CMD-001 |
| Production BF16 residual add | `ot_bf16_add_rne.sv`, `ot_ta_add_bf16_executor.sv` | Command-decoded, backpressured `ADD_BF16` execution with exact external-SRAM byte addresses, RNE arithmetic, retirement counters, saturation, and fail-closed arithmetic faults | QW-RTL-ADD-001 |
| Production ADD SRAM control | `ot_ta_add_bf16_sram_engine.sv` | One-outstanding-read operand fetch, finite-only writeback retirement, exact transaction counters, stable completion, and fault write suppression | QW-RTL-ADD-SRAM-001 |
| Production direct DMA | `ot_ta_dma_hbm_to_sram.sv` | One-outstanding 64-byte HBM request/response, four 16-byte SRAM writes per response, exact byte/transaction accounting, response-error fail-closed completion | QW-RTL-DMA-001 |
| Production DMA/ADD sequencing | `ot_ta_dma_add_sequencer.sv` | One-command-at-a-time dispatch, monotonic submitted indices, shared SRAM write ownership, stable aggregate counters, explicit last-command completion, and fail-stop error handling | QW-RTL-DMA-ADD-001 |
| Production RMSNorm arithmetic and SRAM control | `ot_fp32_rne_pkg.sv`, `ot_fp32_rsqrt_rne.sv`, `ot_ta_rmsnorm_bf16_sram_engine.sv` | Finite FP32 RNE arithmetic, correctly rounded reciprocal square root, canonical 4,096-element balanced reduction, complete-pass buffered writeback, exact SRAM counters, and numeric-fault write suppression | QW-RTL-DMA-RMS-001 |
| Production DMA/RMSNorm sequencing | `ot_ta_dma_rmsnorm_sequencer.sv` | Adjacent authentic command-1/command-2 dispatch, monotonic indices, shared SRAM ownership, stable aggregate completion, and fail-stop propagation | QW-RTL-DMA-RMS-001 |
| Production per-head RMSNorm arithmetic and SRAM control | `ot_fp32_rne_pkg.sv`, `ot_fp32_rsqrt_rne.sv`, `ot_ta_head_rmsnorm_bf16_sram_engine.sv` | Exact 128-element balanced reduction over as many as 32 rows, independent correctly rounded reciprocal square roots, BF16 normalization and weighting boundaries, complete-operation buffered writeback, exact SRAM counters, and numeric-fault write suppression | QW-RTL-HEAD-RMS-001 |
| Production DMA/per-head-RMSNorm sequencing | `ot_ta_dma_head_rmsnorm_sequencer.sv` | Exact four-command Q-weight-DMA/Q-RMS/K-weight-DMA/K-RMS dispatch, kernel/profile enforcement, monotonic indices, unique terminal command, shared SRAM ownership, stable aggregate completion, and fail-stop propagation | QW-RTL-HEAD-RMS-001 |
| Production indexed HBM-to-SRAM DMA | `ot_ta_dma_hbm_indexed_to_sram.sv` | Little-endian 32-bit SRAM index fetch, 8,000-row bounds enforcement, overflow-safe row selection, complete-row HBM buffering before SRAM replacement, exact counters, and response-error atomicity | QW-RTL-ROPE-001 |
| Production BF16 RoPE arithmetic and SRAM control | `ot_fp32_rne_pkg.sv`, `ot_ta_rope_bf16_sram_engine.sv` | Exact `cos[128] || sin[128]` consumption, half-vector rotation, independently BF16-rounded products, signed binary32 addition, signed-zero canonicalization, complete Q/K output buffering, and exact SRAM/arithmetic counters | QW-RTL-ROPE-001 |
| Production indexed-DMA/RoPE sequencing | `ot_ta_dma_rope_sequencer.sv` | Exact command-3,079/3,080 dispatch, kernel/profile enforcement, unique terminal command, shared SRAM ownership, stable aggregate completion, and fail-stop propagation | QW-RTL-ROPE-001 |
| Production BF16 MATMUL SRAM control | `ot_fp32_rne_pkg.sv`, `ot_ta_matmul_bf16_sram_engine.sv` | Signed finite FP32 RNE accumulation over fixed `1 x 64 x 256` segments, ordered 16-bit halfword reload of FP32 state, complete-tile buffered accumulator writeback, buffered `MATMUL_FINAL` BF16 conversion/writeback, exact counters, and numeric-fault write suppression | QW-RTL-DMA-MATMUL-001 |
| Production DMA/MATMUL sequencing | `ot_ta_dma_matmul_sequencer.sv` | Parameter-bounded first-through-final dispatch for complete 32-command output blocks across as many as three exact adjacent kernel-index ranges, strict alternating profile/order, shared SRAM ownership, stable aggregate completion, and fail-stop propagation | QW-RTL-DMA-MATMUL-001/QW-RTL-Q-PROJ-001/QW-RTL-KV-PROJ-001 |
| Stage/CSR | `ot_stage_controller.sv`, `ot_stage_top.sv`, `ot_csr_block.sv` | ordered validate/reserve/execute/commit/retire, complete service metadata, coherent diagnostic snapshot, lossless RW1C clear, single-dispatch schedule CDC, watchdog escalation, and explicit AON integration sidebands | DV-STAGE-001/DV-FW-001/DV-RESET-001 |
| HBM boundary | `ot_hbm_frontend.sv` | tagged out-of-order-across-tag, in-order-within-tag | DV-HBM-001 |
| Stage link | `ot_stage_link_tx.sv`, `ot_stage_link_rx.sv`, `ot_stage_link_endpoint.sv` | packet retention, CRC, duplicate/retry/abort | DV-LINK-001 |
| RAS/telemetry | `ot_ras_controller.sv` | first error, sticky poison, lossless event queue, watchdog | DV-RAS-001/002 |
| Power/reset | `ot_power_reset_controller.sv` | legal state transitions, isolation, safe shutdown | DV-POWER-001 |
| DFT/BIST | `ot_dft_controller.sv`, `ot_bist_controller.sv` | quiescent test ownership, bounded signatures and fail-closed result | DV-DFT-001 |

The inventory is a public implementation baseline, not a claim that the
4,096-tile product hierarchy, ROM density, HBM beachfront, package, or PHY has
been physically realized.  Those remain the external gates listed in the
architecture review.

`spec/clock_reset_crossings.json` classifies all 76 `ot_stage_top` ports and maps
all 12 current CDC/RDC instances. `spec/rtl_waivers.json` is the only accepted
static-waiver source; the campaign fails an unowned, ambiguous, stale, or expired
entry.

QW-RTL-CMD-001 is retained as campaign
`a058f6ce18a22a8d43625a4013f892e74464135d03406512b24fa190309277a5`.
The decoder consumes four bytes per cycle and resolves the 60-byte protected
payload after exactly 15 CRC cycles. Icarus and Verilator both admit one
authentic record for each of the 12 production opcodes and reject seven
directed corruptions. The vectors bind to the 924,386-command Qwen program with SHA-256
`f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec`.
This evidence covers record admission only: it does not execute a kernel or
layer, correlate architectural counters, establish timing, or close
`TA-RTL-6`.

QW-RTL-ADD-001 is retained as vector set
`e625aabe70b198319b76f8928d0b99ffe88d6d9e846eb8e0ddaeb3ba72eb7413`
and campaign
`c6cd95aec4f868f24f7738126a5f293db1b5d81cb481cb04eb7f00dfa790bd9d`.
It executes all 4,096 operand pairs from authentic layer-0 operation
`node.0011`, command index 5,131, and checks the exact
`layer.0.post_attention` payload SHA-256
`f872ce6f57ca36a30edf6abccfa2877bbb7234a905fe9e1417d99ea89ee79ec3`.
Icarus and Verilator independently reproduce every value and byte address under
input and output backpressure, the completion and saturation counters, 20
directed rounding/subnormal/saturation/error cases with commuted operands,
130,560 finite-encoding identities, and two executor fault paths. This is one
complete arithmetic command at an external SRAM ready/valid boundary. It does
not instantiate or exercise a memory macro, execute a complete Qwen layer,
establish timing or performance, or close `TA-RTL-6`.

QW-RTL-ADD-SRAM-001 is retained as campaign
`7e96454558f15a9c992d5f04a3478d20b656107fdc576e2e4f3b22f4dc8c7b59`.
The same authentic vector set executes through a single ordered read channel
and a backpressured write channel in Icarus and Verilator. Each replay checks
8,192 exact 16-bit read transactions, 4,096 exact write transactions, all
addresses and values, completion stability, and architectural byte/count
totals under request stalls, write stalls, and variable read-response latency.
Two arithmetic-fault replays each retire after two reads and prove zero SRAM
writes. The SRAM contents are behavioral campaign models: ECC, banking,
arbitration, DMA, HBM, and a qualified physical memory macro do not execute.
No cycle, timing, performance, complete-layer, or `TA-RTL-6` claim follows.

QW-RTL-DMA-001 is retained as vector set
`98806ae5e1b8f3dbe1e516084b099a5f592f98acf6adb74edb0198d82ae10216`
and campaign
`033c073ff5c3cfede3d95364a857ff7ebb23d2c39c6d7d8e483c7df20f55b17d`.
It executes authentic command index 1 and moves the exact 8,192-byte layer-0
input-normalization weight payload from HBM address 1,244,659,712 to SRAM
address 2,097,152. Icarus and Verilator each check 128 ordered 64-byte HBM
transactions and 512 ordered 16-byte SRAM writes under request stalls,
writeback stalls, and variable HBM response latency. One injected HBM response
error proves fail-closed completion with zero SRAM writes. HBM responses and
SRAM contents are behavioral campaign models. HBM PHY/package behavior,
production ECC/retry, physical SRAM, arbitration, multi-command scheduling,
timing, performance, complete-layer execution, and `TA-RTL-6` remain open.

QW-RTL-DMA-ADD-001 is retained as vector set
`575ddc7ba55ddc76deec04f5747c661b7646baec13020ee29bb572d3f543cd3d`
and campaign
`6df5e663467f84893f3a92eaf01f3dc398a58cedfde134d66ceff4791991516d`.
Icarus and Verilator each execute two unchanged Qwen command records through a
single sequencing boundary. The authentic command-1 DMA writes its 8,192-byte
checkpoint payload to SRAM address 2,097,152; the authentic command-5,131 ADD
then consumes that exact SRAM range as its right operand and writes 4,096
independently calculated BF16 results. Aggregate completion reconciles 128 HBM
requests, 512 DMA writes, 8,192 ADD reads, 4,096 ADD writes, 4,096 elements,
and all byte totals. CRC corruption, an HBM response failure, and a
non-monotonic submitted index each stop the program before successor activity.
Both records come from the frozen Qwen program, but they are intentionally
composed across intervening operations to test the shared-memory dependency;
the campaign is therefore not a graph-valid Qwen operation sequence or a
complete layer. Behavioral HBM/SRAM, banking, ECC, arbitration, a program
header/body CRC, COMPLETE-command handling, timing, and `TA-RTL-6` remain open.

QW-RTL-DMA-RMS-001 is retained as vector set
`ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81`
and campaign
`5868f7e4e0f4b80f74ec968a2a538380ac5409ffb45b9cc3e49a719b57247ae6`.
It executes adjacent authentic Qwen command 1 and command 2. The DMA stages the
exact 8,192-byte `model.layers.0.input_layernorm.weight` payload, then the new
RMSNorm engine consumes it with the preloaded authentic `hidden.0` embedding
row and produces the complete `node.0001` output. The output payload SHA-256 is
`976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58`,
the mean-square binary32 code is `0x3a5bf2ca`, and the inverse-RMS code is
`0x420a0297`, matching independent exact-scalar and optimized implementations.

Icarus and Verilator each pass 17,000 deterministic arithmetic-oracle cases,
then reconcile 128 HBM requests, 512 DMA writes, 4,096 input reads, 4,096
weight reads, and 4,096 delayed output writes. Seven fail-stop cases cover CRC,
HBM response, order, input nonfinite/overflow, and weight nonfinite/overflow
failures. Numeric faults perform no destination writes because the entire
output row is validated before writeback begins. This closes one complete
graph-valid RMSNorm operation only. `hidden.0` is behaviorally preloaded;
embedding command 0, physical HBM/SRAM, banking, ECC, arbitration, program
authentication/`COMPLETE`, a representative layer, timing, activity-derived
power/IR, and `TA-RTL-6` remain open.

QW-RTL-DMA-MATMUL-001 is retained as vector set
`4fe481b232112fe5b494cab1ca4445159b91a512a524471bee18267fe5525129`
and campaign
`c0dba5230a77daa1eecab33aa43960b2e41f198cd453e6ef139653ef1a14a298`.
It executes authentic Qwen commands 3
through 34. Sixteen DMAs stage 524,288 bytes of `q_proj` weights, and sixteen
MATMUL commands consume the complete 4,096-element retained `attention_norm`
row. Non-init commands reload 64 FP32 accumulators through two ordered 16-bit
reads per lane; every command rewrites the complete accumulator tile; command
34 buffers and writes 64 final BF16 values. Both simulators first check 20,000
general signed FP32 additions, then reconcile all HBM/SRAM transactions and
arithmetic events under stalls.

Eight fail-stop cases cover CRC, HBM response, order, nonfinite input/weight/
accumulator state, and multiply/add overflow. A failing command emits no
destination writes, and the reload fault preserves the prior retired tile.
This completes all K tiles for one of 64 output blocks, or 32 of the 2,048
commands spanning `node.0002`. It remains the independently retained arithmetic
and fail-stop boundary for the generalized engine. Complete Q projection closes
separately in QW-RTL-Q-PROJ-001 below.

QW-RTL-Q-PROJ-001 is retained as vector set
`32dbdaa446fc4192f31a0a26394e04094e74c6459858d8a6b0135c11fc9e324b`
and campaign
`af8c787f6c6995527ca0b75ab813b06f9ed05f9c18066ccf3e05ea1fa4d69603`.
It executes every authentic production command from 3 through 2,050: 1,024
alternating DMA/MATMUL pairs, 64 output blocks, all 16 K tiles per block, and
all 4,096 BF16 values of graph operation `node.0002`. The immutable 32 MiB
deployed weight slice has SHA-256
`27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b`;
it is authenticated from the pinned HBM shard and staged only in temporary
campaign directories, not retained as repository payload.

Icarus and Verilator each reconcile 524,288 HBM requests/responses, 2,097,152
DMA writes, 122,880 FP32 halfword reload reads, 262,144 input reads, 16,777,216
weight reads, products, and ordered additions, 65,536 FP32 accumulator writes,
and 4,096 BF16 writes with zero saturation. Both match every retained
intermediate accumulator tile and the final `layer.0.q_raw` payload SHA-256
`b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff`,
which is bound to the full-model simulator event and independently checked
row-major reference. An early terminal assertion on command 3 fails before any
HBM or SRAM activity. The first-block campaign continues to supply eight
numeric, CRC, HBM, order, and reload fail-stop cases plus 20,000 signed-FP32
differential cases.

This completes one authentic Q-projection graph operation, not a complete
layer or `TA-RTL-6`. The input `attention_norm` row remains behaviorally
preloaded. Physical HBM/SRAM, banking, ECC, arbitration, program authentication
and `COMPLETE`, per-head Q/K RMSNorm, RoPE, attention, vector, state, and layer
sequencing, characterized timing, activity-derived power/IR, thermal, foundry,
package, reliability, yield, and silicon remain open. K and V projections close
separately in QW-RTL-KV-PROJ-001 below.

QW-RTL-KV-PROJ-001 is retained as vector set
`ee711ae0b31985d0215b9f0c14233c3a2cb0cade3f79809bfc00493d369d5873`
and campaign
`584e0f388d6295a3abc5d6d6f96e5f32500b493bf81d6a7b09d51b112a735894`.
It executes every authentic command from 2,051 through 3,074: 256
DMA/MATMUL pairs and 16 output blocks for each of `node.0003` K projection and
`node.0004` V projection. The two deployed 8 MiB weight payloads have SHA-256
`0460b9a479fbccdcebf61c86d0dc6eb068be781c51f7b247ed191774db2c28e8`
and
`2b82652e5d6446530230f86a685ef547ba9e94f613c2d2d42ab3388dd7271b1c`.
They are streamed from the pinned HBM shard into temporary campaign storage;
the repository retains hashes and arithmetic oracles, not raw weights.

Icarus and Verilator each reconcile 262,144 HBM requests/responses, 1,048,576
DMA writes, 61,440 accumulator halfword reload reads, 131,072 input reads,
8,388,608 weight reads, products, and ordered additions, 32,768 FP32
accumulator writes, and 2,048 BF16 writes with zero saturation. All 512
intermediate accumulator tiles have aggregate SHA-256
`a1c2f04da9b9059abf17fb048a6a7ffda68b243b9ec7fe0ac8bebe516ac81f69`.
The K and V output hashes are respectively
`dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403`
and
`b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5`,
matching the full-model simulator events and independent row-major reference.
An early terminal marker on command 2,051 fails before HBM or SRAM activity.

This closes two additional authentic projection operations, not complete QKV
preparation, a layer, or `TA-RTL-6`. The Q and K per-head RMSNorm operations,
RoPE, KV preparation, attention, state, vector kernels, program authentication,
physical memories/interconnect, and all characterized physical claims remain
open.

QW-RTL-HEAD-RMS-001 is retained as vector set
`9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791`
and campaign
`d7153d61372e1470310e578d71fda690ccda2fe361a30386399a60d6f0b36c37`.
It executes authentic commands 3,075 through 3,078 and completes graph
operations `node.0005` and `node.0006`: direct DMA of the 128-element Q weight,
32-by-128 Q per-head RMSNorm, direct DMA of the 128-element K weight, and
8-by-128 K per-head RMSNorm. The compact retained artifact authenticates the
combined 512-byte weight payload as
`8de1e5fb0a491567ccbb301547a3ef8d4c826f702cab737dd6eeb3a216017dd1`.

Icarus and Verilator each reconcile eight HBM requests, 32 DMA writes, 5,120
input reads, 5,120 weight reads, 5,080 balanced-reduction additions, 40
correctly rounded reciprocal square roots, and 5,120 output writes. Both match
the complete Q output SHA-256
`bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c`
and K output SHA-256
`71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66`
with zero normalization or output saturation. The engine validates and buffers
the complete multi-row result before writeback; an early-terminal case proves
program-order fail-stop before successor activity. Pinned Yosys 0.68 reports
zero structural problems, and both simulator front ends are warning-free.

This closes the two per-head RMSNorm graph operations only. Q and K projection
inputs remain behaviorally preloaded from independently qualified campaigns;
HBM and SRAM remain behavioral interfaces. The separate RoPE closure follows
below.

QW-RTL-ROPE-001 is retained as vector set
`7a55f9aba5c3e329e571e2a5564beeb666964cd774a868d5ba448470574206d7`
and campaign
`1706f1e27f36411a30e621c2acbefc979f7719d694357d25eba1920d7109c754`.
It executes authentic command 3,079, `DMA_HBM_INDEXED_TO_SRAM`, followed by
authentic command 3,080, `ROPE_BF16`, and completes graph operation
`node.0007`. The DMA reads two 16-bit SRAM responses at addresses 4 and 6 to
form the little-endian position, bounds it below 8,000, and selects a 512-byte
row from HBM table address 16,384,425,984. The complete 4,096,000-byte table is
authenticated as
`82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9`
inside the immutable 1 GiB shard
`4cc984816239b7b9215743b405300e1ecfe26ac1bb62177f2874c20b3889b62b`;
only two compact coefficient rows are retained.

Both simulators execute position 0 and the maximum legal position 7,999 under
independent HBM, SRAM-read, and SRAM-write schedules. Per successful program
they reconcile two index reads, eight 64-byte HBM requests/responses, 32
coefficient writes, 256 coefficient reads, 4,096 Q reads, 1,024 K reads, 5,152
total writes, 10,240 multiplications, 5,120 additions, and 5,120 exact outputs
with zero multiplication or addition saturation. Position 0 is a genuine
identity row and matches Q/K input hashes
`bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c`
and
`71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66`.
Position 7,999 prevents an identity-only implementation from passing and
matches Q/K output hashes
`a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d`
and
`ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858`.

Three fail-stop cases cover an early terminal marker, out-of-range position
8,000, and an HBM error on the fourth burst. The range case performs no HBM
request or write; the HBM case buffers successful bursts but performs no
coefficient write, proving row-replacement atomicity. Icarus observes 37,707
cycles and Verilator 43,445 cycles under their distinct deterministic
schedules; these are control-correlation observations, not characterized
performance. The strict 95-schema inventory and source-hash-bound campaign
preserve the exact claim boundary.

This makes the Q, K, and V projections, Q/K per-head RMSNorm, and RoPE graph
operations individually closed. It does not claim one connected
commands-3-through-3,080 RTL program: projection and normalized inputs remain
preloaded from separately qualified campaigns. KV state preparation, attention,
state and vector kernels, program authentication, physical memories/interconnect,
a representative complete RTL layer, timing, activity-derived power/IR, and
`TA-RTL-6` remain open.

The bounded IHP SG13G2 physical campaign for
`ot_ta_add_bf16_sram_engine` is retained as
`0af6cbe8da22330c466a5ab1fc5de9c245e97c8375cac42fb8b9451c3b40b316`.
At a 20 ns target, `route-v6` has +2.39413 ns aggregate extracted setup WNS,
+0.0608542 ns aggregate extracted hold WNS, zero timing and driver violations,
zero internal detailed-route and residual antenna violations, and 18,101
post-route standard cells in a 922,637 µm² core. Independent extracted STA is
positive for both setup and hold at slow, typical, and fast corners. This is
macro-free open-PDK feasibility for the ADD-SRAM slice only: the SRAM is still
external, the structural netlist audit is not formal equivalence, and no
execution-derived power/IR, thermal, foundry DRC/LVS, package, reliability,
yield, or silicon claim follows. See
[`QWEN3_RTL_IHP_PHYSICAL.md`](../docs/QWEN3_RTL_IHP_PHYSICAL.md) for the exact
flow lock, retained measurements, rejected predecessor, and open gates.
