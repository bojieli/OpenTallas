# Public-reference RTL coverage campaign

**Overall status:** PASS

9 deterministic self-checking benches pass under Icarus and pinned Verilator 5.050. Native Verilator points are merged by source location and description, so repeated hierarchy instances and repeated case elaborations do not inflate the result.

## Closure

| Metric | Raw hit/total | Raw | Post-exclusion hit/total | Post-exclusion | Target | Result |
|---|---:|---:|---:|---:|---:|---|
| Line | 332/344 | 96.512% | 332/344 | 96.512% | 95.0% | PASS |
| Branch | 532/562 | 94.662% | 532/562 | 94.662% | 90.0% | PASS |
| Toggle | 28368/33292 | 85.210% | 28368/33292 | 85.210% | 85.0% | PASS |
| Must bins | 89/89 | 100.000% | 89/89 | 100.000% | 100.0% | PASS |
| FSM state bins | 28/28 | 100.000% | 28/28 | 100.000% | 100.0% | PASS |

## Simulator cases

| Case | Seed | Bins | Icarus | Verilator | Semantic match |
|---|---:|---:|---|---|---|
| `coverage_units` | `0x4356554e` | 29 | PASS | PASS | PASS |
| `coverage_control` | `0x43564354` | 15 | PASS | PASS | PASS |
| `coverage_stage_controller` | `0x5354434f` | 19 | PASS | PASS | PASS |
| `coverage_data_boundary` | `0x44415441` | 15 | PASS | PASS | PASS |
| `coverage_stage_random` | `0x53544752` | 11 | PASS | PASS | PASS |
| `fault_data_supplement` | `0x46444154` | 0 | PASS | PASS | PASS |
| `fault_link_supplement` | `0x464c4e4b` | 0 | PASS | PASS | PASS |
| `fault_ras_dft_supplement` | `0x46524153` | 0 | PASS | PASS | PASS |
| `fault_control_supplement` | `0x4643544c` | 0 | PASS | PASS | PASS |

## Per-file post-exclusion coverage

| RTL source | Line | Branch | Toggle |
|---|---:|---:|---:|
| `rtl/expert_mask_controller.sv` | 2/2 (100.000%) | 2/2 (100.000%) | 24/24 (100.000%) |
| `rtl/lib/ot_async_fifo.sv` | 8/8 (100.000%) | 10/10 (100.000%) | 1171/1192 (98.238%) |
| `rtl/lib/ot_cdc_mailbox.sv` | 6/6 (100.000%) | 12/12 (100.000%) | 330/330 (100.000%) |
| `rtl/lib/ot_crc16_ccitt.sv` | 4/4 (100.000%) | 10/10 (100.000%) | 237/238 (99.580%) |
| `rtl/lib/ot_crc32c.sv` | 4/4 (100.000%) | 10/10 (100.000%) | 397/398 (99.749%) |
| `rtl/lib/ot_reset_sync.sv` | 3/3 (100.000%) | 2/2 (100.000%) | 10/10 (100.000%) |
| `rtl/lib/ot_sync_bits.sv` | 1/1 (100.000%) | 2/2 (100.000%) | 12/12 (100.000%) |
| `rtl/lib/ot_sync_level.sv` | 6/6 (100.000%) | 4/4 (100.000%) | 18/18 (100.000%) |
| `rtl/opentallas_tile.sv` | 2/2 (100.000%) | 2/2 (100.000%) | 474/482 (98.340%) |
| `rtl/ot_bist_controller.sv` | 7/8 (87.500%) | 9/10 (90.000%) | 280/364 (76.923%) |
| `rtl/ot_cmd_frontend.sv` | 23/23 (100.000%) | 26/26 (100.000%) | 2751/3020 (91.093%) |
| `rtl/ot_credit_manager.sv` | 9/9 (100.000%) | 11/14 (78.571%) | 60/76 (78.947%) |
| `rtl/ot_csr_block.sv` | 32/32 (100.000%) | 23/24 (95.833%) | 3520/3684 (95.548%) |
| `rtl/ot_dft_controller.sv` | 4/5 (80.000%) | 10/10 (100.000%) | 61/100 (61.000%) |
| `rtl/ot_format_decode.sv` | 17/17 (100.000%) | 16/16 (100.000%) | 187/226 (82.743%) |
| `rtl/ot_hbm_frontend.sv` | 13/13 (100.000%) | 22/22 (100.000%) | 1598/2030 (78.719%) |
| `rtl/ot_numeric_dot.sv` | 7/9 (77.778%) | 9/10 (90.000%) | 331/414 (79.952%) |
| `rtl/ot_power_reset_controller.sv` | 14/16 (87.500%) | 23/26 (88.462%) | 71/86 (82.558%) |
| `rtl/ot_ras_controller.sv` | 13/13 (100.000%) | 39/42 (92.857%) | 1275/1452 (87.810%) |
| `rtl/ot_reduction_tree.sv` | 12/13 (92.308%) | 29/30 (96.667%) | 546/562 (97.153%) |
| `rtl/ot_rom_wrapper.sv` | 10/10 (100.000%) | 30/32 (93.750%) | 1019/1266 (80.490%) |
| `rtl/ot_route_mask.sv` | 16/16 (100.000%) | 24/24 (100.000%) | 762/992 (76.815%) |
| `rtl/ot_schedule_controller.sv` | 7/7 (100.000%) | 22/22 (100.000%) | 384/444 (86.486%) |
| `rtl/ot_session_table.sv` | 28/29 (96.552%) | 23/24 (95.833%) | 1108/1182 (93.739%) |
| `rtl/ot_stage_controller.sv` | 26/27 (96.296%) | 48/54 (88.889%) | 1873/1948 (96.150%) |
| `rtl/ot_stage_link_endpoint.sv` | n/a | n/a | 628/664 (94.578%) |
| `rtl/ot_stage_link_rx.sv` | 11/11 (100.000%) | 30/30 (100.000%) | 891/908 (98.128%) |
| `rtl/ot_stage_link_tx.sv` | 22/25 (88.000%) | 27/30 (90.000%) | 701/770 (91.039%) |
| `rtl/ot_stage_top.sv` | 11/11 (100.000%) | 28/30 (93.333%) | 5560/7966 (69.797%) |
| `rtl/ot_tile.sv` | 4/4 (100.000%) | 11/12 (91.667%) | 1047/1150 (91.043%) |
| `rtl/rom_mac_tile.sv` | 4/4 (100.000%) | 4/4 (100.000%) | 478/488 (97.951%) |
| `rtl/static_timeslot_switch.sv` | 3/3 (100.000%) | 7/8 (87.500%) | 224/264 (84.848%) |
| `rtl/via_mask_rom.sv` | 3/3 (100.000%) | 7/8 (87.500%) | 340/532 (63.910%) |

## Reviewed exclusions

No coverage points are excluded.

## Accounting and evidence boundary

- Raw source points: 35,252.
- Reviewed exact exclusions: 0.
- Source-deduplicated uncovered-point audit SHA-256: `57ccf63183448b3c2e3c22f05c374a0fa3db03cfb227eb8cdcd6ab41f63ccf4d`.
- Icarus array-sensitivity messages matching the plan's exact allow pattern are recorded as informational; every other warning is fatal to the campaign.
- Verilator width and lint warnings remain fatal. The only suppressions are the named timed-bench diagnostics and the separately gated full-stage SYNCASYNCNET case.
- This is public-tool logical RTL evidence. It does not establish target-node timing, power, physical fault coverage, ATPG, ROM/HBM/PHY macro behavior, package behavior, manufacturability, model numerical quality, or product-silicon signoff.
