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
| Production BF16 MATMUL SRAM control | `ot_fp32_rne_pkg.sv`, `ot_ta_matmul_bf16_sram_engine.sv` | Signed finite FP32 RNE accumulation over fixed `1 x 64 x 256` segments, ordered 16-bit halfword reload of FP32 state, complete-tile buffered accumulator writeback, buffered `MATMUL_FINAL` BF16 conversion/writeback, exact counters, and numeric-fault write suppression | QW-RTL-DMA-MATMUL-001 |
| Production DMA/MATMUL sequencing | `ot_ta_dma_matmul_sequencer.sv` | Exact command-3-through-34 dispatch for sixteen DMA/MATMUL pairs, strict alternating profile/order, shared SRAM ownership, stable aggregate completion, and fail-stop propagation | QW-RTL-DMA-MATMUL-001 |
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
commands spanning `node.0002`. The other 63 blocks, complete Q projection,
physical HBM/SRAM, banking, ECC, arbitration, representative layer, timing,
power/IR, and `TA-RTL-6` remain open.

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
