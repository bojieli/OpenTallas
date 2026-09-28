# OpenTallas task list

Overall progress tracker for the four designs: Qwen3-8B ROM two-reticle package, Qwen3-8B HBM two-reticle comparator, DeepSeek-V4.1-Flash ROM array, DeepSeek-V4.1-Flash HBM comparator.

Status: `[x]` completed at the evidence scope stated on that line, `[~]` in progress (owner and branch), `[ ]` open, `[!]` attempted but failed or blocked. Publication to main is stated separately where pending. Owners: **C** = Claude, **X** = Codex.

Status as of 2026-09-28. Figures are quoted from `docs/ARCHITECTURE_ATLAS.html` and its records; this file is a tracker, not evidence.

**The paper** is `docs/ARCHITECTURE_ATLAS.html`, available from the current main branch at https://github.com/bojieli/OpenTallas/blob/main/docs/ARCHITECTURE_ATLAS.html.

**The review** is the local, untracked `docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md`. Its findings are cross-referenced as R1–R6; the memo is not available from main.

---

## 1. Qwen3-8B on the ROM two-reticle package

### Architecture and model
- [x] **Decision (user):** use signed INT8 weights with per-output-channel BF16 scales on two reticles in one package, eight HBM3E stacks and 6,144 lane groups per die. The O4 rate model uses TP-2 across every layer; DFlash verify uses lane multiplier m=5. The HBM comparator also uses two reticles.
- [x] **C:** O4 advisory RTL gap audit and per-block AR/DFlash requirements are in `docs/ARCH_QWEN3_O4_RTL_SPEC.md`. It shows a best contiguous cut below the TP-2 O4 rates and flags FP32 golden partials versus BF16-priced UCIe traffic; neither is a package RTL pass.
- [x] **C `claude/qwen-o4`**: the two-reticle INT8 baseline, liquid-cooled power scenarios, GPU comparison, prefill, matched HBM comparator and full-model 8-bit quality pass are in this worktree from `206f980b`, awaiting commit. The corrected model charges five post-scale cycles to every INT8 and KV-sourced matvec: 100,169 cycles, 10,968 AR / 18,720 DFlash tok/s. Full INT8 TP-2 RTL remains open.
- [x] **C `claude/qwen-weight-format`**: the exact signed-INT8/BF16-row-scale contract mode and full-model result from `c8f3808e` are in this worktree. INT8 with FP8 E4M3 KV passes the pre-set quality rule: WikiText-2 PPL −1.59% at 2K and −1.03% at 8K, MMLU −0.5 point; 960 sampled real rows are bit-exact to the post-sum-scale contract. The quantizer uses RTN with a per-row MSE clip. The measured 3.5-bit option failed the rule.
- [x] The earlier DFlash acceptance was measured per block in BF16; draft, verify and commit were serialized in that model. This is historical evidence, not a two-reticle rate.
- [x] GPU prefill and KV ingest RTL exist for the earlier reduced vehicle; reprice time to first token for the two-reticle package.
- [ ] Measure DFlash acceptance with the deployed arithmetic, not BF16.
- [ ] Re-price DFlash and autoregressive serial steps on the two-reticle RTL-calibrated core, including the UCIe handoff.

### RTL, all on the reduced G4/SW16 vehicle
- [x] Vector core with physical-HBM KV: an 18-step exact token run from an empty cache, with autonomous boot.
- [x] The same on the timed 4-pseudo-channel HBM model.
- [x] Matched ROM-vs-HBM-weight gate: +5.60%.
- [x] Long-context single-token gates at 256, 512, 1,024 and 2,048 positions.
- [x] Two tokens at positions 254/255.
- [x] Pressure gates, with the pressure absorbed by slack.
- [x] SFU reciprocal saturation fix (golden and RTL).
- [x] Consecutive-token 2047→2048 reduced-core gate: two exact tokens with timed physical HBM KV, zero logit/VM/KV/physical-byte mismatches and cross-token V reads (**X**).
- [~] **X:** 8K single-token reduced-core gate is still running on ot-pve2 (PID 2165760 at the 2026-09-28 audit, about 6 h CPU). The separate Codex audit found 117 GB free, empty stdout/stderr, no exit code, and a binary matching the manifest; all eight image hashes and 36 source pins match the pinned HEAD, while three differ from this dirty shared worktree. Do not relaunch or claim a verdict. After exit, collect in a clean detached HEAD worktree with the model symlink using `tools/rtl_hdc_qwen_context_8192_collect.py`.
- [x] **X:** format-neutral, backpressured logical two-reticle exchange handoff passes a source-pinned two-user randomized gate: four tagged exchanges, 536 exact beats including a 16 KiB vector, one abort and bounded stalls. This is a worktree result awaiting commit; it does not establish UCIe PHY timing or the full TP-2 schedule.
- [~] **X:** two-reticle INT8 RTL integration: the matrix engine masks unused groups for non-power-of-two G, and a G=6/S=4 gate passes. Signed INT8 matrix ROM decoding, BF16 per-row scales after the FP32 K-split tree, scale address timing, writeback and argmax pass focused RTL tests. The reduced-image writer uses the deployed W8 quantizer and verifies matrix code/scale addresses. A separate INT8 embedding bank and BF16 row-scale ROM now write one reduced 128-element embedding row to FP32 VM bit-exactly (128 writes, eight code-word reads, one scale read); full-model bank layout and exact AR m=1/DFlash m=5 token gates remain open, as does the norm-folded TP-2 golden order. The drafter program must issue S=4,096 (16 rounds, 640 engine cycles for its 2,048 × 20,480 slice) to match the golden; the old S=1,024 rule is numerically different. The INT8 engine also delays KV-sourced matvec outputs by five unity-scale cycles, which must be charged in the O4 rate model. Current gates remain reduced-core evidence. Claude supplies advisory numerics and performance requirements; Codex owns core, testbench and integrated RTL.
- [ ] **X:** queue-depth-2 pressure gate; its optional elaboration was stopped and no QD2 run is active.
- [ ] 8K in RTL: correctness, area and timing are all unproven (R1).
- [ ] Offered-load knee: KV-path headroom under sustained queue pressure (R1).
- [ ] Coupled bounded-buffer schedule across consecutive tokens at 8K (R1).

### Physical (ASAP7)
- [x] Reduced W4/G2 matvec, ROM and SRAM tile routes clean at 1.5 ns (modelled macros).
- [!] G4/W8 and baseline G4/W4 full routes timed out during global-route hold repair after six hours; neither has detailed-route or extracted sign-off evidence. A limited-repair G4/W4 clock-tree diagnostic hit the buffer limit.
- [!] Explicit-arrival G4/W4 CTS probe completed with setup and hold violations under an assumed 0.75–1.15 ns external input-arrival contract; this contract is not yet validated at the package boundary.
- [~] **X:** split-ingress G4/W4 route remains active in global-route hold repair; a separate explicit-arrival full-route follow-up is active.
- [ ] Whole-core route and compiled macros (R2).

## 2. Qwen3-8B HBM comparator (two reticles, iso-area, same core)
- [x] **C `claude/qwen-o4`**: the matched two-reticle specification model gives 881 AR / 2,651 DFlash tok/s for the HBM comparator, or 12.5× / 7.1× ROM speed and 13.3× batch-one energy advantage in scenario B. These are model comparisons pending full INT8 TP-2 RTL.
- [x] Matched same-controller RTL gates (reduced vehicle): vector core +5.60%, scalar core +1.37%.
- [~] **C `claude/roofline-rebaseline`**: iso-area record still uses τ 4.1 (Table 8-9); 19 stale figures in `ANALYTICAL_REPORT.md`.
- [x] **X `dd0127b9`:** batch-one AR cooling-capped ROM÷HBM ratios are now source-pinned in `results/arch/qwen3_budget.json`: scenario A 9.1123× liquid / 9.9345× air; production B 12.4536× liquid / 14.6392× air. The isolated record and focused test are applied to this worktree, awaiting main merge. A capped DFlash comparison is still open because the HBM comparator lacks a capped speculative point.
- [ ] **X:** bandwidth-bound RTL comparison: the reduced workload never saturates HBM. Codex owns this after the running Qwen context gates finish.

## 3. DeepSeek-V4.1-Flash on the ROM array

### Architecture and model
- [x] **C `claude/v41-rebalance` @ `9599493a`:** the shared worktree Atlas and records now use measured V4.1-Flash τ = 3.65, S14/S13/S12 layer-20 scan helpers, and layer-2/8/14 MTP helpers. The 1M model rates are 7,049 AR / 15,890 MTP tok/s; all modeled points fit liquid, but the narrowest sweep margin is only 1.61 W (472.95 vs 474.56 W at 899K MTP batch 1). The switched helper exchange and engage policy need RTL proof. These changes await commit.
- [x] Design point with the collective levers.
  - 7,049 / 7,286 tok/s per user at 1M / 200K without MTP; 15,890 tok/s with MTP at 1M using τ = 3.65.
  - This is a model result using bench-measured collective tails, not chip throughput.
- [x] Power and rack.
  - Always-on link power is charged.
  - Aggregates are capped by link bandwidth.
  - ROM uses 2.8× less energy per token than the HBM comparator at batch 1 in the re-derived model.
  - The stage helpers bring the hottest modeled die under the liquid limit across the evaluated operating points; the narrowest reported margin is 1.61 W.
  - Rack gates C4, C8 and C10 pass analytically.
- [x] Prefill and ingest: time to first token is 4.77 s at 1M and 0.735 s at 200K; the GPU tier sizes the system.
- [x] Whole-die assembly study (analytical).
- [x] **C `claude/v41-rederive`**: re-derived the headline with four changes:
  - charge on-die wire time;
  - check power on the hottest die;
  - apply the 0.9 capacity reserve;
  - adopt the MTP hop split of about 200 words.
- [x] **C `claude/v41-quality`**: full-model deployment arithmetic passes the pre-registered quality rule at 2K context (16 WikiText-2 windows and 200 MMLU questions); record and tool are in the worktree awaiting commit. The full-width Engram per-32-block scale bug Claude identified in the golden is fixed with a regression test, and the reduced four-token oracle still passes.
- [x] **C `claude/v41-mtp-tau`**: the on-policy greedy measurement (τ = 3.65, 95% CI 3.50–3.84) and MTP propagation are in the shared Atlas and records, awaiting commit.
- [~] A separate Codex instance completed the read-only V4.1 baseline audit against `claude/v41-rebalance` @ `9599493a`: the inherited requirement headline says 10 HBM stacks per layer package, whereas the adopted design uses 4 per die, 8 per layer package. The 2.714 GB per-die value is ROM capacity and remains correct. Claude owns the model fix on `claude/v41-baseline-fix`, including occupancy-basis and ladder-table reconciliation.

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
- [x] Corrected switched source316 O1-all and independent O1-rest runs both pass: five packages, two users, four exact tokens, zero logit/KV/VM/state mismatches; historical X_HE-only and behavioral memories (**X**).
- [~] **X:** source316 O0 replay remains active; the separate combined all-unit source972 binary is pinned and its two-user token replay is running.
- [x] **C `claude/v41x-matched-weight-ab`**: the reduced two-package all-unit same-program A/B passes both arms exactly: ROM 1,006,625 cycles, QE weight-HBM 1,283,915 (+27.55%); the difference is accounted for by weight-supply stalls. Record and seven passing tests are in the worktree from `0f8c08ac`, awaiting commit. This is a reduced-bench cycle result, not chip throughput.
- [x] **C `claude/v41x-die-top` @ `4f6deda5`**: adopted V4.1x tile and die tops with frozen KV prefetch interface at `142e85a9` are imported into this worktree, awaiting commit. The die smoke passes one reduced exact token with HBM-backed attention KV, whole VM and KV readback, and 240 attention operations; 449,701 cycles versus 438,968 for the current-source single-token HBM gate. Prefetch bench passes 38 operations including shared indexer traffic and generation wrap. Package controller/router/collective ports remain lint/elaboration only, HBM is behavioural, and no die route exists. The Atlas now states this limited die-top evidence.
- [~] **X (isolated wrapper)**: latest-source array-side attention KV-HBM gate, using the core `kvd_*`/`kv_ok` interface and Claude's finalized prefetch/arbiter interface; exact token, KV and VM checks are required.
- [x] Die-top reduced exact-token test passed on `claude/v41x-die-top`; its RTL, source-pinned record and corrected Atlas wording are now in this worktree, awaiting commit.
- [ ] **X:** host integration for V4.1x after the adopted die exact-token gate; the `v41-rom` runtime target is historical.

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
- [x] Link-bandwidth cap and drafter input transfer are applied to the comparator in the re-derived model.
- [~] **X:** full V4.1 HBM-only comparator die/array RTL remains unbuilt and model-only at the 99-die scale. The existing `W_HBM=1` reduced core and two-package bench cover QE weight reads. In an isolated Codex branch, a bounded HBM weight window has passed unit RTL tests and a reduced ME-weight descriptor/issue path has been wired for one L0.router bank; its exact single-token gate is pending local memory headroom. This is a first consumer, not a full comparator die.
  - Stream the ME, QE, expert and head weight families from HBM through bounded windows while sharing HBM with attention KV and pooled index keys; first gate one matched program and exact state, then integrate the switched array.

## 5. Cross-cutting
- [x] Headline reproducibility bundle: 204 of 204 headlines bound to records and 409 of 409 printed occurrences agreeing after the H200 FP8 calibration. The focused model/prose suite passes 135 tests. The refreshed bundle and census pass `make check-figures` against the writable local handoff commit, which tracks the Qwen quality and die-top records. Those records remain untracked in the main checkout's index because this sandbox cannot write its `.git`; merge and push the handoff commit to publish them.
- [ ] The bundle reports 88 stale source pins, including historical pins inherited from main and campaigns affected by current core/golden changes. The headline gate accepts them because none is newly stale relative to its baseline; source-pinned RTL campaign reruns remain needed for final evidence freshness.
- [x] The shared Atlas and records now print V4.1 MTP using the measured on-policy τ = 3.65 and rebalanced-stage rates; these changes await commit.
- [x] Sync-cost and power tables are sourced.
- [x] HBM energy split: die share 10.19 pJ/bit, stack share 3.45 pJ/bit.
- [x] Per-class cooling limits.
- [ ] Measured HBM3E PHY and controller energy: no source found, so the die share takes no credit.
- [x] `test_rom_collectives`: current-source rerun passes all 11 MoE, 2 tensor all-reduce and 5 KV/argmax cases; 21 input hashes are refreshed and the golden indexer callback is repaired (**X**).
- [x] **X:** Qwen TP-2 scalar package gate passes all 18 reduced steps bit-exactly in the ISA golden and two-die RTL: generated tokens 1073/382/93, zero logit/KV/VM mismatches, 315,465 cycles, and 33 current source pins (`results/rtl/hdc_package_tp2_smoke.json`). The package testbench now writes masked row maxima to VM and addresses its full 32,768-word per-die ROM; its C++ harness supplies the Verilator time callback. This establishes the TP-2 topology only. The adopted O4 signed-INT8 vector-core AR/DFlash gates remain open with the Qwen integration agent, and the historical four-die campaign still needs repinning.
- [~] `test_hdc_host_runtime`: 20 stale input pins in a historical target (separate Codex instance, isolated worktree; Claude's `claude/repin-stale` leaves it alone).
- [x] **X `57563a38`:** `runtime/abi3/builder.py` validates LOOP_INDUCTION selector liveness when operators are emitted. The isolated fix is applied to this shared worktree; 160 focused tests passed on its branch, and the local builder/heterogeneous runner tests pass. Awaiting handoff merge to main.
- [x] **X `5d39d684`:** ingest golden `qdq_fp4_e4m3` now saturates the R-P5 scale at FP8 E4M3 maximum 448, and the former strict xfail passes. The isolated fix is applied to this shared worktree while preserving the V4.1 Engram edits; `test_kv_ingest_ref` and `test_hdc_golden_v41` pass together. Awaiting handoff merge to main.
- [ ] After each atlas change lands on main, republish the paper artifact.

## Merge protocol
- Codex integrates the shared worktree and pushes main from a writable Git session. This sandbox can edit the worktree but cannot write its `.git` directory or reach the Git remote; the current integrated snapshot is committed in the local handoff clone `/tmp/opentallas-current-handoff` for a writable session to merge and push. Do not infer publication from worktree-only `[x]` entries.
- Claude hands over fast-forward SHAs with tests and caveats through the Codex tmux pane.
- Atlas edits that overlap Codex text are sent to Codex as a diff first.

## Hosts
- Claude: ot-pve3, agidock .78, .191 and .133.
- On loan from Codex: ot-pve2 (half its cores), .16, .39 and .114. Claude may use up to two on-disk routes per agidock VM while preserving memory and disk headroom; release .114 when Codex needs it.
- Codex: ot-pve1 and ot-pve2.
- Agidock `/tmp` is a 16 GB tmpfs; place concurrent route scratch on disk, not in `/tmp`.
- The local host must keep at least 40 GiB available.
