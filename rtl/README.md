# Public-reference RTL inventory

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
| bounded tensor-accelerator path | `ot_ta_command_decoder.sv`, `ot_ta_dma_hbm_to_sram.sv`, `ot_bf16_add_rne.sv`, `ot_ta_add_bf16_executor.sv`, `ot_ta_add_bf16_sram_engine.sv`, `ot_ta_dma_add_sequencer.sv`, `ot_fp32_rne_pkg.sv`, `ot_fp32_rsqrt_rne.sv`, `ot_ta_rmsnorm_bf16_sram_engine.sv`, `ot_ta_dma_rmsnorm_sequencer.sv` |
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
