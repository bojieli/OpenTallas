# Qwen ADD-SRAM RTL physical feasibility on public IHP SG13G2

The bounded campaign passed RTL-to-GDS feasibility for
`ot_ta_add_bf16_sram_engine` at a 20 ns target period. The retained campaign
ID is
`0af6cbe8da22330c466a5ab1fc5de9c245e97c8375cac42fb8b9451c3b40b316`.
This result applies only to the current macro-free ADD-SRAM slice. It is not a
complete Qwen layer, an SRAM-macro implementation, foundry signoff, or a power,
thermal, package, reliability, yield, or silicon result.

## Pinned flow and constraints

The flow used the public `ihp-sg13g2` platform in the ORFS image with registry
digest
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`
and image ID
`sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34`.
The retained lock binds OpenROAD `26Q3-1510-g6cb3f2b704`, Yosys `0.68+post`,
KLayout `0.30.7`, all three Liberty corners, the technology and standard-cell
LEFs, standard-cell GDS, RC extraction rules, and the platform scripts used by
the flow.

The source constraint creates a 20 ns core clock and a separate 20 ns virtual
I/O clock. It applies 1 ns input and output delays, 0.2 ns core-clock
uncertainty, 0.1 ns transition, and output load. The serialized final SDC
retains the virtual-clock association on all 598 input-delay bits and all 319
output-delay bits. An independent `check_setup -verbose` audit emitted no
missing-clock, missing-delay, or unconstrained-endpoint diagnostics.

The floorplan target was 25% core utilization with routing through Metal5. A
0.1 ns hold-repair margin was used. The first complete route without that
margin was correctly rejected: its extracted aggregate hold WNS was
-0.0248009 ns with 48 violating endpoints. The retained rerun is the repaired
`route-v6` result, not that failed attempt.

## Retained bounded result

| Check | Retained result |
|---|---:|
| Synthesized standard cells | 15,839 |
| Synthesized cell area | 231,138.7974 µm² |
| Post-route standard cells | 18,101 |
| Post-route standard-cell area | 272,410 µm² |
| Core area | 922,637 µm² |
| Die dimensions | 996.555 × 996.555 µm |
| Post-route standard-cell utilization | 29.5252% |
| Final routed wire length | 745,731 µm |
| Final vias | 119,359 |
| Aggregate extracted setup WNS / violations | +2.39413 ns / 0 |
| Aggregate extracted hold WNS / violations | +0.0608542 ns / 0 |
| OpenROAD detailed-route internal violations | 0 |
| Final antenna net / pin violations | 0 / 0 |
| KLayout LEF/GDS cell mismatch / orphan cells | 0 / 0 |

The independent single-corner extracted STA replay produced:

| Corner | Setup WNS | Hold WNS | Setup / hold violations |
|---|---:|---:|---:|
| slow, 1.08 V / 125 °C | +2.394131184 ns | +0.136462629 ns | 0 / 0 |
| typical, 1.20 V / 25 °C | +8.845883369 ns | +0.206251413 ns | 0 / 0 |
| fast, 1.32 V / -40 °C | +12.685538292 ns | +0.068813398 ns | 0 / 0 |

The flow generated nonempty DEF, GDS, ODB, SDC, SPEF, mapped Verilog, and final
Verilog artifacts. Their exact sizes and SHA-256 digests are in the retained
JSON report; the multi-megabyte implementation artifacts and raw ORFS logs are
not stored in Git.

## Structural integrity and explicit nonclaims

The bundled Kepler LEC child executable raises `SIGILL` on this host, so ORFS
LEC was disabled. A separate pinned-Yosys invocation instead elaborates and
flattens the complete source hierarchy, reads and checks the mapped netlist,
proves that both expose the expected 27-port/918-bit top interface, and finds
zero residual processes, inferred latches, or structural-check errors. This is
a post-synthesis structural-integrity gate. It is explicitly not formal or
sequential equivalence.

The ORFS report contains vectorless power observations and repeated,
corner-ambiguous power keys. No execution-derived switching activity was
supplied, so the campaign excludes those numbers. Consequently, activity-based
power, IR drop, thermal behavior, performance per watt, and `TA-PHY-7` remain
open. OpenROAD's zero internal route violations and KLayout's successful stream
merge are also not independent foundry DRC or LVS.

The complete retained boundary and the reasons for every open gate are in
[`qwen3_rtl_ihp_sg13g2_physical_campaign.json`](../results/tensor_accelerator/qwen3_rtl_ihp_sg13g2_physical_campaign.json).
The executable inputs are
[`config.mk`](../physical/ihp_sg13g2_qwen_rtl/add_sram/config.mk),
[`constraint.sdc`](../physical/ihp_sg13g2_qwen_rtl/add_sram/constraint.sdc),
and
[`toolchain.lock.json`](../physical/ihp_sg13g2_qwen_rtl/add_sram/toolchain.lock.json).

The collector can be replayed against a complete ORFS work directory with:

```sh
python3 tools/collect_qwen3_ta_rtl_physical_campaign.py \
  --run-root /path/to/orfs-work-home \
  --variant route-v6 \
  --output /path/to/new-report.json
```

It fails closed on missing or ambiguous reports, negative setup or hold slack,
unconstrained endpoints, driver violations, nonempty detailed-route DRC,
residual antenna violations, collateral drift, top-interface drift, inferred
latches, and missing final artifacts.
