# Public-reference RTL inventory

[Project home](../README.md) · [Documentation](../docs/README.md) ·
[Specification](../spec/README.md) · [Contributing](../CONTRIBUTING.md)

This directory is the technology-independent digital reference for the frozen
OpenTallas architecture. It is suitable for public-tool lint, simulation, formal
checks, synthesis, and methodology proxies. It is not target-node RTL signoff and
does not implement foundry ROM/SRAM, HBM/PHY, SerDes, PLL, sensor, eFuse/OTP, scan
compression, package, power-delivery, or thermal macros.

## Controlled hierarchy

| Area | Sources |
|---|---|
| stage integration | `ot_stage_top.sv`, `ot_stage_controller.sv`, `ot_tile.sv` |
| command/session/control | `ot_cmd_frontend.sv`, `ot_session_table.sv`, `ot_schedule_controller.sv`, `ot_credit_manager.sv`, `ot_csr_block.sv` |
| data and numeric path | `ot_route_mask.sv`, `ot_rom_wrapper.sv`, `via_mask_rom.sv`, `ot_format_decode.sv`, `ot_numeric_dot.sv`, `ot_reduction_tree.sv` |
| ROM read service | `rom/ot_rom_pkg.sv`, `rom/ot_rom_read_service.sv`, `rom/ot_rom_bank_array.sv` |
| bounded tensor-accelerator path | `ot_ta_command_decoder.sv`, `ot_ta_dma_hbm_to_sram.sv`, `ot_ta_dma_hbm_indexed_to_sram.sv`, `ot_bf16_add_rne.sv`, `ot_ta_add_bf16_executor.sv`, `ot_ta_add_bf16_sram_engine.sv`, `ot_ta_dma_add_sequencer.sv`, `ot_fp32_rne_pkg.sv`, `ot_fp32_rsqrt_rne.sv`, `ot_ta_rmsnorm_bf16_sram_engine.sv`, `ot_ta_dma_rmsnorm_sequencer.sv`, `ot_ta_head_rmsnorm_bf16_sram_engine.sv`, `ot_ta_dma_head_rmsnorm_sequencer.sv`, `ot_ta_rope_bf16_sram_engine.sv`, `ot_ta_dma_rope_sequencer.sv`, `ot_ta_matmul_bf16_sram_engine.sv`, `ot_ta_dma_matmul_sequencer.sv` |
| HBM and stage protocol | `ot_hbm_frontend.sv`, `ot_stage_link_tx.sv`, `ot_stage_link_rx.sv`, `ot_stage_link_endpoint.sv` |
| RAS, power, and test | `ot_ras_controller.sv`, `ot_power_reset_controller.sv`, `ot_bist_controller.sv`, `ot_dft_controller.sv` |
| CDC/protocol primitives | `lib/ot_reset_sync.sv`, `lib/ot_skid_buffer.sv`, `lib/ot_async_fifo.sv`, `lib/ot_cdc_mailbox.sv`, `lib/ot_sync_level.sv`, `lib/ot_sync_bits.sv`, and CRC helpers |
| legacy feasibility tile | `expert_mask_controller.sv`, `rom_mac_tile.sv`, `opentallas_tile.sv`, `static_timeslot_switch.sv` |

The legacy tile is retained for small synthesis/SPICE feasibility comparisons; it
is not a substitute for the controlled `ot_*` stage hierarchy.

The bounded tensor-accelerator modules are source-bound functional slices, not
the complete accelerator hierarchy. In particular, the DMA/RMSNorm campaign
executes adjacent authentic Qwen commands 1 and 2 and completes graph operation
`node.0001`, but uses behavioral HBM/SRAM and a preloaded `hidden.0` input. It
does not establish memory-macro, timing, power, complete-layer, or silicon
qualification.

The first DMA/MATMUL campaign separately executes authentic commands 3 through
34: sixteen 32,768-byte `q_proj` weight tiles cover all 4,096 K elements for the
first 64-output block. Commands 6 through 34 reload the FP32 accumulator through
ordered 16-bit halfword reads, all sixteen MATMUL commands rewrite the complete
64-lane accumulator tile, and command 34 performs the first 64 BF16 auxiliary
writes required by `MATMUL_FINAL`.

The complete Q-projection campaign extends the same synthesizable engines over
authentic commands 3 through 2,050. All 1,024 DMA/MATMUL pairs execute in
`n_tile_then_k_tile` order and write all 4,096 `layer.0.q_raw` BF16 values. The
32 MiB deployed weight slice is authenticated and streamed only into temporary
simulator inputs; it is not retained in the repository. Icarus and Verilator
match every accumulator rewrite, all aggregate counters, and the independently
checked architectural output SHA-256
`b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff`.
This completes graph operation `node.0002`, not a complete layer. HBM and SRAM
remain behavioral interfaces, and timing, power, memory-macro, and `TA-RTL-6`
gates remain open.

The complete K/V-projection campaign continues over authentic commands 2,051
through 3,074 and kernel indices 3 and 4. Its 512 DMA/MATMUL pairs consume the
same retained `attention_norm` row and stream 16 MiB of authenticated deployed
weights from immutable HBM evidence without retaining that payload. Icarus and
Verilator match every one of the 512 accumulator rewrites and all 2,048 BF16
values for graph operations `node.0003` and `node.0004`, including exact output
SHA-256 values
`dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403`
and
`b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5`.
This closes the two projection operations only. The subsequent per-head Q/K
RMSNorm operations close separately below.

The per-head RMSNorm campaign executes authentic commands 3,075 through 3,078:
two 256-byte direct DMAs stage the exact Q and K normalization weights, then two
128-wide RMSNorm commands process 32 query rows and eight key rows. The dedicated
engine preserves the independently qualified full-width RMSNorm engine and
buffers all 4,096 Q or 1,024 K outputs before its first destination write. Icarus
and Verilator match all 5,120 input and weight reads, 5,080 balanced-reduction
additions, 40 correctly rounded reciprocal square roots, and all 5,120 BF16
outputs. The Q and K output SHA-256 values are respectively
`bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c`
and
`71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66`.
This completes graph operations `node.0005` and `node.0006`. Their projection
inputs remain preloaded from independently qualified campaigns, so this is not
one connected QKV-preparation program.

The indexed RoPE campaign then executes authentic commands 3,079 and 3,080.
The first command reads a little-endian 32-bit position from SRAM, validates it
against the 8,000-row bound, selects one 512-byte row from the authenticated
4,096,000-byte HBM coefficient table, and buffers all eight HBM responses before
writing SRAM. The second command consumes `cos[128] || sin[128]`, performs the
exact BF16-bounded binary32 rotary contract for 32 query heads and eight key
heads, and buffers all 5,120 results before its first destination write.
Independent Icarus and Verilator schedules reproduce positions 0 and 7,999,
including the non-identity position-7,999 Q and K SHA-256 values
`a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d`
and
`ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858`.
Range, HBM-response, and early-terminal failures perform no coefficient or
output writes beyond the explicitly proven boundary. This closes graph
operation `node.0007` and means all QKV-preparation graph operations are
individually closed; it still does not connect the separately preloaded
projection/RMSNorm inputs into one commands-3-through-3,080 RTL program. KV
preparation, attention, state, vector kernels, complete-layer sequencing,
physical memories/interconnect, and the remaining physical gates stay open.

## The ROM read service

`rom/ot_rom_read_service.sv` turns a deployment's name for a weight -- an
`(object_id, byte_offset, byte_length)` triple -- into a physical access: which
placement resource, which row inside it, which sense granule of that row, in
what order, and whether the read is allowed at all. Every table it consults is
the compiled ROM region plan (`compiler/backends/rom/common/image.py`, published
as `notes.rom_plan` in a ROM deployment), written in over a configuration
channel.

**There is no ROM array in it.** The array sits behind the sense
request/response interface; `rom/ot_rom_bank_array.sv` is a behavioural stand-in
with no write port, and a foundry macro is what replaces it. The service
therefore establishes addressing, ordering, masking, repair translation and
operand alignment, and establishes nothing about cell area, read energy, sense
margin, wordline or bitline delay, retention or defect rate. The sense-granule
width is a declared parameter of the block, not a macro property; row
activations and sense accesses are counted and never converted into an energy.

Row redundancy is implemented and exercised. Column redundancy is **refused**: a
read reaching a resource with an activated column repair fails closed with its
own class rather than returning the unrepaired column.

The correlation campaign replays real requests through Icarus and Verilator:

```bash
make rom-service-vectors
make rom-service
make rom-service-physical
```

`docs/ROM_SERVICE_RTL.md` states what each of the three vector sets is evidence
of, including the one that is derived from the compiled plan rather than
executed, and the campaign artifact carries the claim boundary.

## Fault and containment benches

| Bench | Planned sites | Scope |
|---|---:|---|
| `test/tb_fault_data.sv` | 18 | route records, immutable ROM correction/repair, tagged HBM framing/integrity/conservation |
| `test/tb_fault_link.sv` | 15 | complete-packet receive containment, sequence/idempotence, credit, retry, timeout, abort |
| `test/tb_fault_ras_dft.sv` | 26 | RAS telemetry/poison/counters, BIST outcomes/ownership, DFT isolation and races |
| `test/tb_fault_control.sv` | 28 | power/thermal/clock response, schedule identity, session ownership, stage abort cleanup |

`../spec/fault_campaign.json` is authoritative for the exact 87 IDs, expected
observation, containment, recovery, and external gates. Run either:

```bash
make -C rtl fault-campaign
make fault-campaign
```

The runner requires Icarus/vvp and the public pinned Verilator 5.050 source build.
`../tools/bootstrap_verilator_5_050.sh` reproduces the latter. Unexpected warnings
are fatal; no width-warning or nonfatal-warning blanket suppression is used.

## Evidence boundary

Passing directed sites establishes the declared logical behavior only at the bench
parameters. Stage/reticle/pipeline constrained-random faults, reset at every phase,
functional/code/toggle/FSM coverage, target macro fault grading, scan/ATPG, physical
faults, PDK timing/power, numerical quality, and manufacturing/yield remain separate
gates in `../spec/VERIFICATION_PLAN.md`.
