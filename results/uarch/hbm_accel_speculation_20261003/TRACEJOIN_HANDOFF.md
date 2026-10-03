# HA7 saved-trace composition and implementation handoff, 2026-10-03

Status: one completed analytical milestone, NOT ADOPTED. All accelerator figures below are conditional sensitivities, not measured full-token results. Branch `codex/ha7-hbm-accel-tracejoin-20261003`; source `e28c080706b361821eb62901244304a5e19cbb62`. Main and peer sources are unchanged. This extends inherited initial pricing `75c063d38` with NEW tools only.

| Input or delta | Result | Evidence boundary |
|---|---:|---|
| Historical AR composition | 442.14 us | replay of d2aff19ef measured components and explicit extrapolations |
| DSpark draft composition | 51.88 us | 3 stages, head, 5 serial Markov steps; shape extrapolations retained |
| P6 verify, saved greedy-path union | 700.85 us | U6=23.904, historical rounded per-layer unions |
| Saved lag-one expert reuse | 1.60438 / 6 = 26.7397% | 103,360 generated-position/layer pairs, 30 GPU traces |
| Free linear lag-one prefetch credit | 1.42523 us / +0.3234% original AR | optimistic sensitivity; below 1% gate |
| Incremental AR credit after study HA5 hide | 0 us | conditional 10.6 us hide already covers fetch; no double count |
| P6 2-stack verify exposed fetch | 105.81 vs 33.78 us | recomposed max(first access, union stream minus routed-SM work), bandwidth scaling assumed |
| P6 2-stack incremental verify + draft | +72.03 +1.81 = 73.84 us | unchanged efficiency/schedule assumed; no new RTL measurement |
| Mixed tau 3.6486, gamma5/P6, 4 stacks, 6 selectors | 608.008 us / 6000.9 tok/s | conditional study ladder; excluded from measured accelerator composition |
| Same at 2 stacks | 681.848 us / 5351.0 tok/s | conditional, -10.8294% rate vs study assumed -4% (6.8294 percentage-point difference) |
| Gamma5 selector gain, 2 vs 1 replicas | 1.3652% | ideal wave scheduling, independently preloaded candidates assumed |
| Gamma5 selector gain, 6 vs 1 replicas | 2.2962% | ideal wave scheduling, independently preloaded candidates assumed |
| Five extra selector buffers | >=4.58647 mm2 cell / >=6.55210 mm2 at util .7 | 96x512x64 bits/replica, pinned DFF 0.2916 um2; excludes logic, clocks, mux, routing |
| Six-selector ingress | 384 B/cycle / 3072 bits/cycle | six independent positions, no shared-score broadcast |

Gamma sweep: mixed_n36 and agentic_all5_n30 choose gamma5/P6; agentic_multiturn chooses gamma4/P5 on both stack counts. These cohorts are kept separate. The 120-row sweep covers gamma1..5, every replica count 1..P, 2/4 stacks and three tau sets. Two selectors are the smallest ideal P6 replication crossing the 1% model gate; that is an implementation candidate, not an adoption recommendation.

Input trace: `/tmp/claude-review-20261003/v41spec/router_full.pt`, SHA256 `ff7a232284a92ab9ed9df3942a5bb785b74dd0fa6b0a931f2dc8b77201cda027`. Each trace ledger row carries `trace_index`, `item.prompt_id`, `item.prompt_sha256`, workload, generated `[L,n)` interval, layer `[0,40)` interval, and digest of `router_idx`. The exact selection key is `router_idx[layer,position,top6]`; generated union windows start at L and end at n-P, lag-one pairs start at L+1. Prompt-region rows and cross-trace transitions are excluded. Existing `drafter_idx` call-position keys are listed per trace. No hidden-state predictor was evaluated, trained or inferred. `main_hidden` is saved data, not measured predictor recall.

Measured versus assumed: the saved GPU selections, original SM cases, selector go-to-done cycles and timing-model RTL fetch cycles are measured inputs. The W19 token is a composition, not a measured complete accelerator. R1b/R2/R3/R4/R5 transfers, shared-first overlap, proportional draft collective improvement, ideal selector waves and half-bandwidth scaling are conditional. R7a is excluded. Greedy continuation unions are proxies for verification: rejected DSpark draft positions can route differently. The mixed36 acceptance sample is not the same cohort as the router30 sample. Those limitations remain in the JSON, not hidden in the headline.

The one-stack fetch bench assumes HBM timing and controller/PHY/NoC defaults: it passes 13,720 line checks at 35 experts, request-to-done 2.6365 us, coefficient 0.07532857 us/expert. Doubling the EXPOSED fetch tail is incorrect because routed-SM work remains unchanged while the underlying stream doubles. No actual two-stack system penalty has yet been measured. Index/attention contention, refresh, finite credit loops and buffer pressure remain open.

Einstein HA5 / P-selector owner `01a101f7-ff9c-72a1-b0aa-4359f70a01da`: preserve shared expert issue-first with golden sum order; provide actual slot6 issue/drain/overlap and per-position candidate ingress/retire cycles, refresh-live. The 419-cycle select measurement begins AFTER load. A 64 B/cycle candidate input needs at least 6144 cycles (5.117952 us) per position; concurrent gather, distribution and candidate loading need measurement. Price and measure mux/demux, per-replica buffers, command fanout, corridor capacity and SS/FF in context before counting ideal wave savings. The area above is a lower bound and makes no floorplan-fit claim. No HA5 code was edited here.

Sagan DS20/union-SM owner `01a0fa84-2959-7963-b1d4-b377be694aee`: owns actual implementation exclusively. Supply per-layer P/union/bytes, first-request, first-line, final-line, routed-SM completion and exposed stall timestamps, actual 2/4-stack service and finite flow control. Replace this proxy by actual verified-and-rejected-position router unions when available. Compose successor cycles only after exact golden gate; do not relabel historical element measurements as successor measurements. HA7 builds no RTL and runs no P&R.

GPU coordination: local `qwen_rom_dspark_drafter_golden.py --device cuda` was active during this milestone. No GPU work or competing job was launched. Notes were queued successfully to Einstein and Sagan. Queueing Peirce `01a0f65d-bbf8-7172-ae4a-7a8ee4abafb7` was refused because that spawned sub-agent is unloaded; no confirmation or scheduling clearance is implied. The actual predictor experiment stays pending Claude/Peirce/dspark GPU coordination. When admitted, use local GPU only, held-out prompts and no future-token leakage, and record top6 recall, all-required-hit probability, prediction lead time, bytes wasted, finite buffering and demand-stream interference. CPU saved-selection statistics alone cannot establish predictor quality.

Replay from this sparse worktree:

```sh
python3 tools/hbm_accel_speculation_compose.py --router /tmp/claude-review-20261003/v41spec/router_full.pt --out /tmp/ha7-fresh.json
python3 tools/hbm_accel_speculation_check.py /tmp/ha7-fresh.json
```

For CPU composition without reloading torch, pass `--stats-record results/uarch/hbm_accel_speculation_20261003/final_tracejoin.json`; raw trace SHA256 is still checked. Existing outputs are never overwritten. `final_check.log` passes seven pinned replay cases and 120 accounting rows. `check_failure_r1.log` preserves the initial overly tight accounting assertion: rounded historical parts can differ by 0.01 us from rounded totals; the successor check explicitly allows 0.011 us. No numerical failure or failed RTL verdict was changed. No docs/ files were edited.
