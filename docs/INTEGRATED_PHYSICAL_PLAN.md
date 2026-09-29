# Integrated floorplan and physical-composition plan (2026-09-29)

Root: Claude (`claude-main`). Codex root stopped at 06:22 UTC after publishing `4a82ce47`. Its branch `codex/publish-e2e-20260928` (`9be3f0f1`) holds three more tested commits.
Objective order is unchanged: **minimum single-user decode latency first**, then aggregate throughput from independent requests filling idle stages without hurting that latency.

## Why this plan exists

Four architectures are being compared: Qwen3-8B ROM, Qwen3-8B HBM-weight comparator, DeepSeek-V4.1 ROM array and DeepSeek-V4.1 HBM comparator. Until now each existed only as **independently verified components**: exact engines, routed microblocks and analytical die ledgers. Nobody had shown that the components compose on one die.

That means placing them together with real macro views, with routable channels between them, where the wire delay each crossing costs appears in the token schedule. Codex's last session produced only the V4.1 reservation plan (`docs/V41_PHYSICAL_FLOORPLAN.md`). That plan is geometric intent: four regions, 11 connections, no macro packing. It surfaced these blockers:

| # | Finding | Design |
|---|---|---|
| 1 | The candidate stage-17 die exceeds logical ROM capacity by 7,408,140 B, and no spill receiver is proved. Compact `wo_a` (exact, zero added cycles in the first ME test) is the lead remedy. | V4.1 ROM |
| 2 | The analytical die ledger has 8 collectives, 2 controllers and 4 routers; the die RTL instantiates 1 of each. | V4.1 ROM/HBM |
| 3 | The monolithic 40,332-pin K-arbiter strip does not converge in global placement (stopped after 20.95 h). A local per-PC partition was proposed at `796726ad`, costing ≥4 added K round-trip cycles. | V4.1 ROM/HBM |
| 4 | Shared 32-PC HBM service cannot keep the no-stall QE supplied for the 3,840-word `wq_a` operation. QE stall support exists (`9be3f0f1`); window sizing is still open. | V4.1 HBM (and ROM KV) |
| 5 | Probability preload costs 2,560 issue cycles at T640. WINDOW refill was serial; 8 credits now give 50,462 → 11,633 cycles. | V4.1 both |
| 6 | Qwen G6144 literal ports reach 3.1 Mbit, and the 4-modulo VM banking fails the traffic trace. The 8-skew-bank, 32-macro VM passes replay but has no routed steering. | Qwen both |
| 7 | Qwen m=5 reducer copies: +178.66 mm²/die against 28.01 mm² of slack, and WNS −2.8 ns pre-layout. | Qwen ROM (DFlash) |
| 8 | Qwen ROM output → first product register misses by 1,218 ps at global route. | Qwen ROM |
| 9 | Full-width Verilator elaboration needs >125 GiB, or needs hierarchy cuts or runtime composition. | both |

## Deliverable per architecture (the acceptance ladder)

Each architecture climbs the same ladder. A rung counts only with a source-pinned record and a test.

1. **Resource inventory = RTL.** One engine profile (counts, widths, memories) that the die RTL actually instantiates. Analytical ledger entries without RTL are listed as gaps, not substituted.
2. **Integer placement.** Every tensor/expert/table goes to named macros (ROM) or HBM regions. Capacity closes with no fractional bytes.
3. **Macro-packed floorplan.** Real LEF macro views (ROM/SRAM/PHY abstracts) are placed legally with halos, pin orientation, PDN straps and channels. The tool is `tools/chip_assembly` extended by per-architecture floorplan generators emitting DEF/TCL placement.
4. **Representative hardened clusters.** One of each repeated neighborhood is routed with extracted setup/hold/DRC/power at the adopted clock. For V4.1: ROM/MAC, VM+ME, attention, HBM-service local slice, index, collective. For Qwen: ROM/MAC 4×16 neighborhood, VM 8-bank, reduction, collective/UCIe. Abstracts come from `generate_abstract`.
5. **Die-level assembly.** Abstracts are placed per the floorplan, with top-level glue, channel global route, a congestion map, and inter-cluster wire delay compared with the registered-channel budgets. This is the "can it be merged" answer.
6. **Connected exact execution.** The same die composition runs a real layer, then a token, bit-exact against golden, with measured cycles.
7. **Schedule reprice.** Measured cycles plus the physical channel latencies give a token-latency schedule, an II for multi-user fill, and power/cooling. Only this rung changes a headline.

## Workstreams, owners and hosts

| WS | Owner (agent) | Scope | Hosts |
|---|---|---|---|
| W0 | root (Claude) | Reconcile Codex branches (the 3 publish commits plus isolated commits), keep main green, TASKS.md, publish, arbitrate host leases | local |
| W1 | `v41-rom-floorplan` | V4.1 ROM die: rungs 1-3. Resolve the capacity deficit (compact `wo_a` adoption vs spill), integer bank map for the busiest stage, then a macro-packed floorplan generator for the whole die with channel capacity | local, AGIdocks |
| W2 | `v41-physical-clusters` | V4.1 rung 4: harden the representative clusters, starting with the local per-PC K-arbiter partition RTL (`796726ad`) replacing the failed strip, then ROM/MAC and attention neighborhoods. Emit abstracts | ot-pve3, AGIdocks |
| W3 | `v41-die-assembly` | V4.1 ROM + HBM rung 5: die assembly from W1 floorplan and W2 abstracts. HBM comparator variant: shoreline, weight-service regions, no weight ROM. Resolve RTL count mismatch (#2) | ot-pve2 |
| W4 | `v41-connected-exec` | V4.1 rung 6: connected L0 (HBM WINDOW → attention → SU → PV → VM) in the die composition with QE stall and shared 32-PC service, then the indexed layer | ot-pve2, ot-pve1 |
| W5 | `qwen-floorplan-physical` | Qwen ROM + HBM rungs 1-5: two-reticle O4 die inventory, integer ROM image placement, macro-packed floorplan, 4×16 neighborhood and 8-bank VM routes with real producer/capture timing, then die assembly. HBM variant: 4 stacks/die shoreline and weight-stream regions | ot-pve1, AGIdocks |
| W6 | `qwen-connected-exec` | Qwen rung 6: G6144 full-shape layer-0 exact via runtime composition, then checkpoint-backed token, ROM and HBM arms | ot-pve1 |
| W7 | root + `reprice` | Rung 7, after 5/6 land: schedule reprice for all four designs; update Atlas/headlines only from exact+physical evidence | local |

Rules carried from earlier sessions:
- Long runs go in pinned clean worktrees, never in the main checkout.
- Big jobs are memory-gated: PVE1/PVE2 have 227 GB, PVE3 108 GB, AGIdocks 32 GB and at most 30 GB per job via `/tmp/claude-1000/remote_gate.sh`, local 188 GB.
- Negative verdicts are preserved.
- No constraint relaxation without pricing it.
- Stage explicit paths, never `git add -A`.
- Every landing: focused tests, then `make check-figures`, then push.

## Order of first actions

1. W0: land `codex/publish-e2e-20260928`, then sweep for tested unintegrated commits.
2. W1, W2, W5, W4 and W6 start immediately in parallel. W3 starts from the V4.1 reservation plan and existing abstracts, then consumes W1/W2 as they land.
3. Stuck jobs: the PVE2 die synth is 24 h in yosys-abc, and the PVE3 pin_q/pin_q2 global routes have run 2.6 days. W2/W3 must judge them and kill them if they are nonconverging, recording why, before reusing the hosts.
