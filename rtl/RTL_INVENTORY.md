# Public-reference RTL inventory

This inventory is the implementation allocation for the frozen specification.
It is intentionally separate from target-node macro collateral.  A module may
be replaced by a qualified macro only if its visible latency, ordering,
integrity, reset, poison, and test contracts remain equivalent.

| Block | RTL | Primary contract | Evidence entry |
|---|---|---|---|
| CRC/integrity | `lib/ot_crc_pkg.sv`, `lib/ot_crc16_ccitt.sv`, `lib/ot_crc32c.sv` | CRC-16/CCITT-FALSE and CRC32C traversal | DV-RAS-001 |
| Elastic/CDC | `lib/ot_skid_buffer.sv`, `lib/ot_async_fifo.sv` | stable ready/valid, Gray pointers, reset flush | DV-RESET-001 |
| Route context | `ot_route_mask.sv` | ID/range/CRC checks and duplicate suppression | DV-TILE-001 |
| Immutable ROM | `ot_rom_wrapper.sv`, `via_mask_rom.sv` | no write path, fixed latency, repair/fault status | DV-TILE-002 |
| Numeric/DV | `ot_format_decode.sv`, `ot_numeric_dot.sv`, `ot_reduction_tree.sv` | classification, signed exact order, deterministic reduction | DV-NUM-001/002 |
| Tile | `ot_tile.sv`, `opentallas_tile.sv` | route-before-activation and result alignment | DV-TILE-004 |
| Static schedule | `ot_schedule_controller.sv`, `static_timeslot_switch.sv` | shadow/active epoch commit and slot transport | DV-NOC-001 |
| Credits | `ot_credit_manager.sv` | atomic reservation and conservation | DV-NOC-004 |
| Sessions/commands | `ot_session_table.sv`, `ot_cmd_frontend.sv` | generation isolation, CRC/version/field legality | DV-CMD-001/002 |
| Stage/CSR | `ot_stage_controller.sv`, `ot_stage_top.sv`, `ot_csr_block.sv` | ordered validate/reserve/execute/commit/retire and exact CSR access | DV-STAGE-001/DV-FW-001 |
| HBM boundary | `ot_hbm_frontend.sv` | tagged out-of-order-across-tag, in-order-within-tag | DV-HBM-001 |
| Stage link | `ot_stage_link_tx.sv`, `ot_stage_link_rx.sv`, `ot_stage_link_endpoint.sv` | packet retention, CRC, duplicate/retry/abort | DV-LINK-001 |
| RAS/telemetry | `ot_ras_controller.sv` | first error, sticky poison, lossless event queue, watchdog | DV-RAS-001/002 |
| Power/reset | `ot_power_reset_controller.sv` | legal state transitions, isolation, safe shutdown | DV-POWER-001 |
| DFT/BIST | `ot_dft_controller.sv`, `ot_bist_controller.sv` | quiescent test ownership, bounded signatures and fail-closed result | DV-DFT-001 |

The inventory is a public implementation baseline, not a claim that the
4,096-tile product hierarchy, ROM density, HBM beachfront, package, or PHY has
been physically realized.  Those remain the external gates listed in the
architecture review.
