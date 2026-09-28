# OpenTallas task list

Overall progress tracker for the four designs: Qwen3-8B ROM two-reticle package, Qwen3-8B HBM two-reticle comparator, DeepSeek-V4.1-Flash ROM array, DeepSeek-V4.1-Flash HBM comparator.

Status: `[x]` done (on main, with a record), `[~]` in progress (owner and branch), `[ ]` open, `[!]` done but failed or blocked. Owners: **C** = Claude, **X** = Codex.

Status as of 2026-09-28. Figures are quoted from `docs/ARCHITECTURE_ATLAS.html` and its records; this file is a tracker, not evidence.

**The paper** is `docs/ARCHITECTURE_ATLAS.html`, available from the current main branch at https://github.com/bojieli/OpenTallas/blob/main/docs/ARCHITECTURE_ATLAS.html.

**The review** is the local, untracked `docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md`. Its findings are cross-referenced as R1–R6; the memo is not available from main.

---

## 1. Qwen3-8B on the ROM two-reticle package

### Architecture and model
- [x] **Decision (user):** use signed INT8 weights with per-output-channel BF16 scales on two reticles in one package, split layers across UCIe, with eight HBM3E stacks and 6,144 lane groups per die. DFlash verify uses lane multiplier m=5. The HBM comparator also uses two reticles.
- [~] **C:** re-baseline area, autoregressive and DFlash rates, cooling, GPU prefill and the iso-area HBM comparator for that decision. The published single-reticle 3.5-bit numbers are superseded.
- [~] **C `claude/qwen-weight-format`**: validate the selected 8-bit format against the quality bar (≤2% perplexity rise, ≤1 point on MMLU); the emulated 3.5-bit format failed it.
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
- [~] **X:** consecutive-token gate at 2047→2048 and 8K single-token gate are running; both await final source-pinned verdicts.
- [~] **X:** two-reticle INT8 RTL integration: freeze the layer and HBM stack split, implement signed INT8 × BF16 with per-output BF16 post-accumulation scaling and a credit-controlled UCIe activation handoff, then prove the same deployed program in autoregressive m=1 and DFlash verify m=5 modes. Current G4/SW16 gates are reduced single-core evidence. Claude supplies an advisory gap/performance audit; Codex owns core, testbench and integrated RTL.
- [ ] **X:** queue-depth-2 pressure gate; its optional elaboration was stopped and no QD2 run is active.
- [ ] 8K in RTL: correctness, area and timing are all unproven (R1).
- [ ] Offered-load knee: KV-path headroom under sustained queue pressure (R1).
- [ ] Coupled bounded-buffer schedule across consecutive tokens at 8K (R1).

### Physical (ASAP7)
- [x] Reduced W4/G2 matvec, ROM and SRAM tile routes clean at 1.5 ns (modelled macros).
- [!] G4/W8 full route timed out during global-route hold repair after six hours; no detailed-route or extracted sign-off verdict. A limited-repair G4/W4 clock-tree diagnostic hit the buffer limit.
- [~] **X:** G4/W4 full route and split-ingress G4/W4 route remain active in global-route hold repair; a separate command-arrival clock-tree sensitivity probe is active.
- [ ] Whole-core route and compiled macros (R2).

## 2. Qwen3-8B HBM comparator (two reticles, iso-area, same core)
- [~] **C:** re-baseline the specification-model rate and energy ratios for the two-reticle 8-bit package. The old 6.5× and 3,762 tok/s values describe the superseded single-reticle model.
- [x] Matched same-controller RTL gates (reduced vehicle): vector core +5.60%, scalar core +1.37%.
- [~] **C `claude/roofline-rebaseline`**: iso-area record still uses τ 4.1 (Table 8-9); 19 stale figures in `ANALYTICAL_REPORT.md`.
- [ ] Capped rate ratio: no record carries a cooling-capped ROM÷HBM ratio.
- [ ] **X:** bandwidth-bound RTL comparison: the reduced workload never saturates HBM. Codex owns this after the running Qwen context gates finish.

## 3. DeepSeek-V4.1-Flash on the ROM array

### Architecture and model
- [x] Budget model unified: official checkpoint precision, τ 5.0 (third-party V4-Pro measurement), 4 HBM stacks per die, 209 ns cable hop.
- [x] Design point with the collective levers.
  - 7,009 / 7,286 tok/s per user at 1M / 200K; 21,670 / 22,532 with MTP.
  - This is a model result using bench-measured collective tails, not chip throughput.
- [x] Power and rack.
  - Always-on link power is charged.
  - Aggregates are capped by link bandwidth.
  - ROM uses 2.8× less energy per token than the HBM comparator at batch 1 in the re-derived model.
  - The hottest die needs liquid cooling at 1M batch 1 and fill, and exceeds liquid with MTP or at saturation.
  - Rack gates C4, C8 and C10 pass analytically.
- [x] Prefill and ingest: time to first token is 4.77 s at 1M and 0.735 s at 200K; the GPU tier sizes the system.
- [x] Whole-die assembly study (analytical).
- [x] **C `claude/v41-rederive`**: re-derived the headline with four changes:
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
- [~] **X (isolated wrapper)**: latest-source array-side attention KV-HBM gate, using the core `kvd_*`/`kv_ok` interface and Claude's finalized prefetch/arbiter interface; exact token, KV and VM checks are required.
- [ ] Die-top exact-token test. After it passes, the atlas statement "no V4.1x tile/die exists" changes (diff to Codex first).
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
- [ ] **X:** full V4.1 HBM-only comparator die/array RTL is unbuilt and model-only today. The existing `W_HBM=1` reduced core and two-package bench cover QE weight reads, not the modeled 99-die comparator. Codex owns this target after the adopted die interface is validated.
  - Stream the ME, QE, expert and head weight families from HBM through bounded windows while sharing HBM with attention KV and pooled index keys; first gate one matched program and exact state, then integrate the switched array.

## 5. Cross-cutting
- [x] Headline reproducibility bundle: 187 of 200 headlines bound to records, with a checker in `make check-figures` (R6).
- [ ] 13 unbound headlines.
  - Their records exist only on side branches, for example the Qwen iso-area record and the common-KV energy record.
- [ ] 63 stale source pins in RTL campaign records.
- [x] Sync-cost and power tables are sourced.
- [x] HBM energy split: die share 10.19 pJ/bit, stack share 3.45 pJ/bit.
- [x] Per-class cooling limits.
- [ ] Measured HBM3E PHY and controller energy: no source found, so the die share takes no credit.
- [x] `test_rom_collectives`: current-source rerun passes all 11 MoE, 2 tensor all-reduce and 5 KV/argmax cases; 21 input hashes are refreshed and the golden indexer callback is repaired (**X**).
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
