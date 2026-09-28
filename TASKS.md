# OpenTallas task list

Overall progress tracker for the four designs: Qwen3-8B ROM reticle, Qwen3-8B HBM comparator, DeepSeek-V4.1-Flash ROM array, DeepSeek-V4.1-Flash HBM comparator.

Status: `[x]` done (on main, with a record), `[~]` in progress (owner and branch), `[ ]` open, `[!]` done but failed or blocked. Owners: **C** = Claude, **X** = Codex.

Status as of 2026-09-28. Figures are quoted from `docs/ARCHITECTURE_ATLAS.html` and its records; this file is a tracker, not evidence.

**The paper** is `docs/ARCHITECTURE_ATLAS.html`, available from the current main branch at https://github.com/bojieli/OpenTallas/blob/main/docs/ARCHITECTURE_ATLAS.html.

**The review** is the local, untracked `docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md`. Its findings are cross-referenced as R1–R6; the memo is not available from main.

---

## 1. Qwen3-8B on the ROM reticle (single reticle, by decision)

### Architecture and model
- [x] Top-down budget: the compute chain is at the KV floor, with 8,910 tok/s as the uncapped autoregressive target.
- [x] Speculative decoding (DFlash).
  - Acceptance is measured directly per block: τ = 2.265 at block 3.
  - Draft, verify and commit run as serial steps.
  - Design rate 13,052 tok/s.
- [x] Power, from sourced inputs.
  - Headline: DFlash on one reticle, 13,052 design rate, capped by cooling at 11,925 with the production lane (4,731 with the lane as built).
  - Power levers were evaluated and not adopted, by decision.
- [x] Prefill runs on the GPU.
  - Time to first token is 143 ms at 8K.
  - KV ingest RTL exists.
- [~] **C `claude/qwen-weight-format`**: find a weight format that passes the quality bar (≤2% perplexity rise, ≤1 point on MMLU).
  - The emulated 3.5-bit format fails, so every 3.5-bit figure has no quality-preserving format behind it yet.
- [ ] **Decision (user):** choose the weight format, then re-derive the ROM area and budget at that bit width (R4).
- [ ] Measure DFlash acceptance with the deployed arithmetic, not BF16.
- [ ] Re-price the DFlash serial step on the RTL-calibrated core (it is currently priced on the specification chain).

### RTL, all on the reduced G4/SW16 vehicle
- [x] Vector core with physical-HBM KV: an 18-step exact token run from an empty cache, with autonomous boot.
- [x] The same on the timed 4-pseudo-channel HBM model.
- [x] Matched ROM-vs-HBM-weight gate: +5.60%.
- [x] Long-context single-token gates at 256, 512, 1,024 and 2,048 positions.
- [x] Two tokens at positions 254/255.
- [x] Pressure gates, with the pressure absorbed by slack.
- [x] SFU reciprocal saturation fix (golden and RTL).
- [~] **X:** consecutive-token gate at 2047→2048 and 8K single-token gate are running; both await final source-pinned verdicts.
- [ ] **X:** queue-depth-2 pressure gate; its optional elaboration was stopped and no QD2 run is active.
- [ ] 8K in RTL: correctness, area and timing are all unproven (R1).
- [ ] Offered-load knee: KV-path headroom under sustained queue pressure (R1).
- [ ] Coupled bounded-buffer schedule across consecutive tokens at 8K (R1).

### Physical (ASAP7)
- [x] Reduced W4/G2 matvec, ROM and SRAM tile routes clean at 1.5 ns (modelled macros).
- [!] G4/W8 full route timed out during global-route hold repair after six hours; no detailed-route or extracted sign-off verdict. A limited-repair G4/W4 clock-tree diagnostic hit the buffer limit.
- [~] **X:** G4/W4 full route and split-ingress G4/W4 route remain active in global-route hold repair; a separate command-arrival clock-tree sensitivity probe is active.
- [ ] Whole-core route and compiled macros (R2).

## 2. Qwen3-8B HBM comparator (iso-area, same core)
- [x] Specification-model rate and energy ratios.
  - The 6.5× figure is uncapped and autoregressive.
  - The comparator's DFlash point is 3,762 tok/s.
- [x] Matched same-controller RTL gates (reduced vehicle): vector core +5.60%, scalar core +1.37%.
- [~] **C `claude/roofline-rebaseline`**: iso-area record still uses τ 4.1 (Table 8-9); 19 stale figures in `ANALYTICAL_REPORT.md`.
- [ ] Capped rate ratio: no record carries a cooling-capped ROM÷HBM ratio.
- [ ] Bandwidth-bound RTL comparison: the reduced workload never saturates HBM.

## 3. DeepSeek-V4.1-Flash on the ROM array

### Architecture and model
- [x] Budget model unified: official checkpoint precision, τ 5.0 (third-party V4-Pro measurement), 4 HBM stacks per die, 209 ns cable hop.
- [x] Design point with the collective levers.
  - 8,185 / 8,568 tok/s per user at 1M / 200K; 23,756 / 24,797 with MTP.
  - This is a model result using bench-measured collective tails, not chip throughput.
- [x] Power and rack.
  - Always-on link power is charged.
  - Aggregates are capped by link bandwidth.
  - ROM uses 3.2× less energy per token than the HBM comparator at batch 1.
  - Rack gates C4, C8 and C10 pass analytically.
- [x] Prefill and ingest: time to first token is 4.77 s at 1M and 0.735 s at 200K; the GPU tier sizes the system.
- [x] Whole-die assembly study (analytical).
- [~] **C `claude/v41-rederive`**: re-derive the headline with four changes:
  - charge on-die wire time;
  - check power on the hottest die;
  - apply the 0.9 capacity reserve;
  - adopt the MTP hop split of about 200 words.
- [~] **C `claude/v41-quality`**: full-model quality under the deployed arithmetic (R4). It is being relaunched under a 16 GiB memory cap.
- [~] **C `claude/v41-mtp-tau`**: find or measure MTP acceptance specific to V4.1-Flash; the current τ 5.0 is from V4-Pro.
- [ ] Unify the two V4.1 specification baselines' remaining inputs where records still differ.

### Collectives and rack (R5)
- [x] Stage bench: collective overlap measured, levers adopted, about 58% of the loss recovered.
- [x] Stage-hop lever holds under batch load.
- [x] Stimulus uniqueness is audited.
- [x] Real-core producer → collective → consumer stage (**X**): exact at link latencies 142 and 228.
  - Its collective timing matches the stub bench; the consumer adds 54–77 cycles.
- [!] Gate C7 is not met: collective overlap is only partly recovered.
- [ ] Streaming real-core consumer, and real producers for the gather and hop collectives.
- [ ] Whole-system clock demonstration.

### RTL (reduced vehicle, behavioural HBM)
- [x] Weight and index-key HBM: ten-step exact run.
- [x] Two-package array, X_HE unit only.
- [x] Two-package array, all units.
- [x] Two-user, all units.
- [!] Five-package switched array (source57): FAIL on a router flag.
- [~] **X:** corrected switched rerun (source316, three-token optimized prefix exact so far); the separate combined all-unit source972 binary is pinned and its two-user token replay is running.
- [~] **C `claude/v41x-matched-weight-ab`**: same program, weights from ROM vs from HBM; replaces the configuration-delta caveat for this bench point only.
- [~] **C `claude/v41x-die-top`**: adopted V4.1x tile and die tops.
  - KV-HBM prefetch, shared-port arbitration and staging RTL exist on the branch, but exact-token validation is still pending, so this stays staged.
  - Verify the separate KV region, write-through staging, generation-wrap protection, `K_MEM` range, maximum-descriptor case and nonzero-user-slice case in the final gate.
- [ ] Die-top exact-token test. After it passes, the atlas statement "no V4.1x tile/die exists" changes (diff to Codex first).
- [ ] Host integration for V4.1x; the `v41-rom` runtime target is historical.

### Physical (ASAP7)
- [x] Block routes: select, indexer and HCP tiles (see atlas Table 8-4).
- [~] **C `claude/px-physical`**: route the adopted collective engine `ot_rom_oneshot_die_px` at 0.92 ns.
- [~] **C `claude/v41-block-timing`**: audit of blocks against 0.92 ns, re-routes, and tighter fmax sweeps.
- [~] **C `claude/v41-missing-routes`**: routes for missing blocks (vector unit, HC projection, select, KV streamer) and placement utilisation against the 0.68 threshold.
- [~] **X:** SFU lane route.
- [ ] Tile, spine and die routes, and power-grid sign-off (need the die top).

## 4. DeepSeek-V4.1-Flash HBM comparator
- [x] Best switched comparator derived: 99 dies with 4 stacks each.
- [x] Priced by the same power model as the ROM design, including always-on links.
- [ ] Link-bandwidth cap and drafter input transfer are not applied to the comparator (both favour it; the atlas says so).
- [ ] No V4.1 HBM-comparator RTL: it is model-only.

## 5. Cross-cutting
- [x] Headline reproducibility bundle: 121 of 134 headlines bound to records, with a checker in `make check-figures` (R6).
- [ ] 13 unbound headlines.
  - Their records exist only on side branches, for example the Qwen iso-area record and the common-KV energy record.
- [ ] 63 stale source pins in RTL campaign records.
- [x] Sync-cost and power tables are sourced.
- [x] HBM energy split: die share 10.19 pJ/bit, stack share 3.45 pJ/bit.
- [x] Per-class cooling limits.
- [ ] Measured HBM3E PHY and controller energy: no source found, so the die share takes no credit.
- [~] **X:** `test_rom_collectives` record has stale RTL pins; the current-source rerun is underway after fixing its golden indexer callback signature.
- [ ] `test_hdc_package_tp`: its bench does not build on main.
- [ ] `test_hdc_host_runtime`: 20 stale input pins in a historical target (**X**).
- [ ] `runtime/abi3/builder.py`: LOOP_INDUCTION failures in `test_abi3_heterogeneous_batch_runner` (**X**).
- [ ] Ingest golden `qdq_fp4_e4m3` lacks the R-P5 saturating scale; the test is a strict xfail (**X**).
- [ ] After each atlas change lands on main, republish the paper artifact.

## Merge protocol
- Codex integrates and pushes main.
- Claude hands over fast-forward SHAs with tests and caveats through the Codex tmux pane.
- Atlas edits that overlap Codex text are sent to Codex as a diff first.

## Hosts
- Claude: ot-pve3, agidock .78, .191 and .133.
- On loan from Codex: ot-pve2 (half its cores), .16 and .39.
- Codex: ot-pve1, ot-pve2 and .114.
- Agidock `/tmp` is a 16 GB tmpfs: run one route per VM.
- The local host must keep at least 40 GiB available.
